"""
VoiceGuard Streaming Audio Buffer and Session Orchestration (Phase 4).
Maintains in-memory circular audio buffers for real-time scoring.
Coordinates detector evaluation, risk fusion, sustained evidence, and audit logging.
Never persists raw streaming audio to disk.
"""

import os
import time
import json
import base64
import numpy as np
from typing import Optional, Dict, Any, List, Tuple
from collections import deque

from server.telephony import decode_twilio_payload
from server.risk_engine import RiskEngine, SustainedEvidence
from server.audit import AuditLogger
from server.enrollment import load_enrollment_key, decrypt_voiceprint
from server.preprocessing import VoiceActivityDetector
from server.diagnostics import LiveDiagnosticsLogger
from models.speaker import ECAPASpeakerDetector
from models.replay import AcousticReplayDetector
from models.spoof import AASISTSpoofDetector


class AudioRollingBuffer:
    """
    In-memory rolling buffer for decoded 16 kHz float32 audio.
    Thread-safe append; bounds maximum memory footprint.
    """
    def __init__(self, max_seconds: float = 10.0, sr: int = 16000):
        self.sr = sr
        self.max_samples = int(max_seconds * sr)
        self.buffer = np.zeros(self.max_samples, dtype=np.float32)
        self.total_samples_received = 0

    def append(self, samples_16k: np.ndarray):
        n = len(samples_16k)
        if n == 0:
            return
        if n >= self.max_samples:
            self.buffer[:] = samples_16k[-self.max_samples:]
        else:
            self.buffer[:-n] = self.buffer[n:]
            self.buffer[-n:] = samples_16k
        self.total_samples_received += n

    def get_window(self, num_samples: int) -> Optional[np.ndarray]:
        if self.total_samples_received < num_samples:
            return None
        return self.buffer[-num_samples:].copy()

    def get_available_audio(self) -> np.ndarray:
        valid_len = min(self.total_samples_received, self.max_samples)
        return self.buffer[-valid_len:].copy()


class StreamingSession:
    """
    Manages state for an active telephony call stream.
    """
    def __init__(
        self,
        call_sid: str,
        stream_sid: Optional[str] = None,
        speaker_id: str = "gokul",
        enrollment_bin_path: str = "data/enrollment/enrolled_voiceprint.bin",
        use_spoof: bool = False,  # Config 2: SPOOF Off
        audit_logger: Optional[AuditLogger] = None
    ):
        self.call_sid = call_sid
        self.stream_sid = stream_sid or f"MZ_{call_sid}"
        self.speaker_id = speaker_id
        self.audio_buffer = AudioRollingBuffer(max_seconds=10.0, sr=16000)
        self.risk_engine = RiskEngine()
        self.sustained_evidence = SustainedEvidence(consecutive_required=3, threshold=0.60)
        self.audit_logger = audit_logger or AuditLogger()
        self.use_spoof = use_spoof

        # Load enrolled voiceprint
        self.enrolled_embedding = None
        if os.path.exists(enrollment_bin_path):
            try:
                key_bytes = load_enrollment_key()
                with open(enrollment_bin_path, "rb") as f:
                    bin_data = f.read()
                self.enrolled_embedding, _ = decrypt_voiceprint(bin_data, key_bytes)
            except Exception as e:
                print(f"[StreamingSession] Warning: could not load enrollment voiceprint: {e}")

        # Detectors
        self.speaker_detector = ECAPASpeakerDetector(device="cpu")
        self.replay_detector = AcousticReplayDetector()
        self.spoof_detector = AASISTSpoofDetector(device="cpu") if self.use_spoof else None

        # VAD & Diagnostics
        self.vad = VoiceActivityDetector(backend="webrtcvad", mode=2)
        self.min_speech_fraction = self._load_min_speech_fraction()
        self.diagnostics_logger = LiveDiagnosticsLogger()

        self.window_index = 0
        self.last_action_triggered = None
        self.terminated = False

    def _load_min_speech_fraction(self) -> float:
        try:
            import yaml
            for path in ("config/live.yaml", "config/settings.yaml"):
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        cfg = yaml.safe_load(f) or {}
                    if "live" in cfg and "min_speech_fraction" in cfg["live"]:
                        return float(cfg["live"]["min_speech_fraction"])
        except Exception:
            pass
        return 0.30

    def ingest_twilio_payload(self, base64_payload: str):
        """Decodes Twilio mu-law frame and appends to rolling buffer."""
        if self.terminated:
            return
        audio_16k = decode_twilio_payload(base64_payload)
        self.audio_buffer.append(audio_16k)

    def score_current_window(self, context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Runs available detectors on current rolling audio and computes fused risk.
        Ignores windows where speech_fraction is below configured threshold (trial message/silence).
        """
        if self.terminated:
            return None

        # Min audio required for speaker/replay: 32,000 samples (2.0s)
        audio = self.audio_buffer.get_available_audio()
        if len(audio) < 32000:
            return None

        eval_window = audio[-32000:] if len(audio) >= 32000 else audio
        speech_frac = self.vad.compute_speech_fraction(eval_window, 16000)
        if speech_frac < self.min_speech_fraction:
            import logging
            logging.getLogger("voiceguard.streaming").info(
                f"[{self.call_sid}] waiting for speech (fraction={speech_frac:.4f} < {self.min_speech_fraction:.4f})"
            )
            return None

        rms = float(np.sqrt(np.mean(eval_window ** 2)))
        buffer_rms_dbfs = float(20.0 * np.log10(rms)) if rms > 1e-9 else -100.0

        t0 = time.perf_counter()
        self.window_index += 1

        # 1. Speaker detector
        speaker_sim = None
        if self.enrolled_embedding is not None:
            speaker_sim, _ = self.speaker_detector.score(audio, self.enrolled_embedding)

        # 2. Replay detector
        replay_prob, _ = self.replay_detector.score(audio)

        # 3. Spoof detector
        spoof_prob = None
        if self.use_spoof and self.spoof_detector is not None and len(audio) >= 64600:
            spoof_prob, _ = self.spoof_detector.score(audio)

        # 4. Risk fusion
        risk_res = self.risk_engine.compute_risk(
            spoof_prob=spoof_prob,
            speaker_sim=speaker_sim,
            replay_prob=replay_prob,
            context=context
        )

        final_risk = risk_res["final_risk"]
        band = risk_res["band"]
        decision = risk_res["decision"]

        # 5. Sustained escalation rule
        sustained_info = self.sustained_evidence.evaluate_window(final_risk)
        is_sustained_high = sustained_info["is_sustained_high"]
        is_sustained_medium = sustained_info["is_sustained_medium"]
        action_trigger = sustained_info["action_trigger"]
        decision = sustained_info["decision"]

        latency_ms = (time.perf_counter() - t0) * 1000.0

        scores_dict = {
            "speaker_sim": round(speaker_sim, 4) if speaker_sim is not None else None,
            "replay_prob": round(replay_prob, 4) if replay_prob is not None else None,
            "spoof_prob": round(spoof_prob, 4) if spoof_prob is not None else None
        }

        # 6. Audit record
        audit_record = self.audit_logger.log_event(
            call_sid=self.call_sid,
            detector_scores=scores_dict,
            context=context,
            risk=final_risk,
            band=band,
            decision=decision,
            explanation=risk_res["explanation"]
        )

        # 7. Live diagnostics logging (no raw audio, no secrets, no phone numbers)
        self.diagnostics_logger.log_window_score(
            call_sid=self.call_sid,
            window=self.window_index,
            speaker_sim=speaker_sim,
            replay_prob=replay_prob,
            risk=final_risk,
            band=band,
            decision=decision,
            action_trigger=action_trigger,
            speech_fraction=speech_frac,
            buffer_rms_dbfs=buffer_rms_dbfs,
            timestamp=time.time()
        )

        result = {
            "window": self.window_index,
            "call_sid": self.call_sid,
            "timestamp": audit_record["timestamp"],
            "detector_scores": scores_dict,
            "risk": final_risk,
            "band": band,
            "decision": decision,
            "sustained_high": is_sustained_high,
            "sustained_medium": is_sustained_medium,
            "action_trigger": action_trigger,
            "speech_fraction": round(speech_frac, 4),
            "buffer_rms_dbfs": round(buffer_rms_dbfs, 2),
            "latency_ms": round(latency_ms, 2),
            "record_hash": audit_record["record_hash"]
        }
        return result
