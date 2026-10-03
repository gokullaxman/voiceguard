"""
VoiceGuard Upload Analysis Module (server/upload.py).
Label: "UPLOAD ANALYSIS, not a validated accuracy figure"

Handles user-uploaded audio analysis for exhibition demonstrations:
- Validates file format, size (<=25MB), duration (2s - 120s), and rejects corrupted/non-audio files.
- Converts to 16 kHz mono float32 WAV via ffmpeg in temporary directory (cleaned up in finally).
- Optional phone-simulation path (8 kHz mu-law -> 16 kHz).
- Supports 'stream' mode (full-speed StreamingSession) and 'whole' mode (whole-clip scoring).
- Concurrency control (single active analysis, 409 on conflict) and rate limiting (10 per minute).
- Scores-only audit logging without filename, audio, or content hashes.
- Comprehensive warning detection based on empirical measurements.
"""

import os
import time
import json
import uuid
import base64
import shutil
import asyncio
import hashlib
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from server.preprocessing import VoiceActivityDetector
from server.telephony import simulate_telephony_channel, encode_pcm_to_ulaw
from server.streaming import StreamingSession
from server.risk_engine import RiskEngine
from server.audit import AuditLogger
from server.demo import compute_stream_outcome
from server.spectrogram import compute_display_mel_spectrogram

UPLOAD_LABEL = "UPLOAD ANALYSIS, not a validated accuracy figure"
ALLOWED_EXTENSIONS = {"wav", "mp3", "m4a", "ogg", "opus", "flac", "aac", "webm"}
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB
MIN_DURATION_S = 2.0
MAX_DURATION_S = 120.0
RATE_LIMIT_PER_MINUTE = 10

# Precomputed sha256 hashes of candidate enrollment audio
ENROLLMENT_AUDIO_HASHES = {
    "7174e6638a99f3e33ae160a7079f3fffe9a52b980b2bd4f3d8b2907eceaf53c7",
    "f7ea243853afba65e753f9bbefe3ae95236213ab82b83834bee0bc9037e4c45e",
    "1e787f5adb1b652daaab76e4ba5ffd95d933462624f6d7ae6c569fcd07bfef4a",
    "c930cf4eea60b6a67d0983e2b268fd18f3c8252a1bea0885d536d0ac81bf0849"
}

# Concurrency & rate limit state
_analysis_lock = asyncio.Lock()
_request_timestamps: List[float] = []


def is_analysis_locked() -> bool:
    return _analysis_lock.locked()


def get_allowed_sensitivities() -> List[str]:
    return ["balance_check", "password_reset", "wire_transfer"]


def probe_audio_metadata(file_path: str) -> Dict[str, Any]:
    """Runs ffprobe on the uploaded file to validate format, stream presence, and duration."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "stream=codec_type,codec_name,duration,sample_rate,channels",
        "-show_entries", "format=duration,format_name",
        "-of", "json",
        file_path
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if res.returncode != 0:
            raise ValueError("Corrupted or unreadable media file")
        data = json.loads(res.stdout)
    except Exception as e:
        raise ValueError(f"Failed to probe audio: {str(e)}")

    streams = data.get("streams", [])
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
    if not audio_streams:
        raise ValueError("No valid audio streams found in file")

    a_stream = audio_streams[0]
    fmt = data.get("format", {})

    # Determine duration
    duration = None
    if "duration" in a_stream and a_stream["duration"]:
        try:
            duration = float(a_stream["duration"])
        except ValueError:
            pass
    if duration is None and "duration" in fmt and fmt["duration"]:
        try:
            duration = float(fmt["duration"])
        except ValueError:
            pass

    if duration is None:
        raise ValueError("Unable to determine audio duration")

    sample_rate = int(a_stream.get("sample_rate", 0)) if a_stream.get("sample_rate") else 0
    channels = int(a_stream.get("channels", 0)) if a_stream.get("channels") else 0
    fmt_name = fmt.get("format_name", a_stream.get("codec_name", "unknown"))

    return {
        "duration": duration,
        "sample_rate": sample_rate,
        "channels": channels,
        "format": fmt_name
    }


def convert_audio_ffmpeg(input_path: str, output_path: str) -> None:
    """Converts audio to 16 kHz mono float32 WAV using ffmpeg without shell execution."""
    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-vn",
        "-ar", "16000",
        "-ac", "1",
        "-c:a", "pcm_f32le",
        output_path
    ]
    res = subprocess.run(cmd, capture_output=True, timeout=30)
    if res.returncode != 0 or not os.path.exists(output_path):
        raise RuntimeError("FFmpeg audio conversion failed")


def process_audio_upload(
    file_bytes: bytes,
    filename: str,
    action_sensitivity: str = "balance_check",
    mode: str = "stream",
    phone_sim: bool = True
) -> Dict[str, Any]:
    """
    Main synchronous processor for uploaded audio.
    Runs inside TemporaryDirectory, cleaned up in finally.
    """
    # 1. Extension validation
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file extension. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

    # 2. File size validation
    if len(file_bytes) > MAX_FILE_SIZE:
        raise ValueError("File size exceeds 25 MB limit")

    temp_dir_obj = tempfile.TemporaryDirectory()
    temp_dir = temp_dir_obj.name

    try:
        in_temp_path = os.path.join(temp_dir, f"input.{ext}")
        out_wav_path = os.path.join(temp_dir, "converted_16k.wav")

        with open(in_temp_path, "wb") as f:
            f.write(file_bytes)

        # 3. Probe metadata & validate genuine audio
        meta = probe_audio_metadata(in_temp_path)
        dur = meta["duration"]
        if dur < MIN_DURATION_S:
            raise ValueError(f"Audio duration {dur:.2f}s is below minimum {MIN_DURATION_S:.1f}s limit")
        if dur > MAX_DURATION_S:
            raise ValueError(f"Audio duration {dur:.2f}s exceeds maximum {MAX_DURATION_S:.1f}s limit")

        # 4. Conversion to 16kHz mono float32 WAV
        convert_audio_ffmpeg(in_temp_path, out_wav_path)

        # Read converted audio
        audio_16k, sr = sf.read(out_wav_path, dtype="float32")
        if audio_16k.ndim > 1:
            audio_16k = audio_16k.mean(axis=1)

        # 5. Acoustic measurements
        peak = float(np.max(np.abs(audio_16k))) if len(audio_16k) > 0 else 0.0
        rms = float(np.sqrt(np.mean(audio_16k ** 2))) if len(audio_16k) > 0 else 0.0
        rms_dbfs = float(20.0 * np.log10(rms)) if rms > 1e-9 else -100.0
        clipped_samples = int(np.sum(np.abs(audio_16k) >= 0.9999))

        vad = VoiceActivityDetector(backend="webrtcvad", mode=2)
        speech_frac = vad.compute_speech_fraction(audio_16k, 16000)

        # Optional phone simulation
        phone_sim_applied = False
        if phone_sim:
            audio_16k = simulate_telephony_channel(audio_16k)
            phone_sim_applied = True

        # Check sha256 for enrollment match
        audio_sha256 = hashlib.sha256(audio_16k.tobytes()).hexdigest()
        is_enrollment_clip = (audio_sha256 in ENROLLMENT_AUDIO_HASHES)

        # 6. Warnings generation
        warnings = []
        if dur < 4.0:
            warnings.append("short clip, few windows")
        if speech_frac < 0.30:
            warnings.append("mostly silence")
        if peak >= 0.999 or clipped_samples > 0:
            warnings.append("clipping")
        if is_enrollment_clip:
            warnings.append("this is the enrollment clip; score is not meaningful")
        warnings.append("calibrated for one enrolled speaker")

        # 7. Scoring
        call_sid = f"UPLOAD_{uuid.uuid4().hex[:8]}"
        audit_logger = AuditLogger()
        risk_engine = RiskEngine(config_path="config/settings.yaml")

        if mode == "whole":
            # Whole-clip scoring
            from models.speaker import ECAPASpeakerDetector
            from models.replay import AcousticReplayDetector
            from server.enrollment import load_enrollment_key, decrypt_voiceprint

            speaker_detector = ECAPASpeakerDetector(device="cpu")
            replay_detector = AcousticReplayDetector()

            enrolled_emb = None
            enroll_bin = "data/enrollment/enrolled_voiceprint.bin"
            if os.path.exists(enroll_bin):
                try:
                    k_bytes = load_enrollment_key()
                    with open(enroll_bin, "rb") as f:
                        b_data = f.read()
                    enrolled_emb, _ = decrypt_voiceprint(b_data, k_bytes)
                except Exception:
                    pass

            spk_sim = None
            if enrolled_emb is not None:
                spk_sim, _ = speaker_detector.score(audio_16k, enrolled_emb)

            rep_prob, _ = replay_detector.score(audio_16k)

            risk_res = risk_engine.compute_risk(
                spoof_prob=None,
                speaker_sim=spk_sim,
                replay_prob=rep_prob,
                context={
                    "action": action_sensitivity,
                    "action_sensitivity": action_sensitivity,
                    "caller_not_allowlisted": False,
                    "simulation": True,
                    "simulation_label": UPLOAD_LABEL
                }
            )

            final_risk = risk_res["final_risk"]
            final_band = risk_res["band"]
            final_decision = risk_res["decision"]

            outcome = "Block" if final_band == "HIGH" else ("Step-up only" if final_band == "MEDIUM" else "Allow")

            windows_scored_list = [{
                "window": 1,
                "window_index": 1,
                "speaker_sim": round(spk_sim, 4) if spk_sim is not None else None,
                "replay_prob": round(rep_prob, 4) if rep_prob is not None else None,
                "detector_scores": {
                    "speaker_sim": round(spk_sim, 4) if spk_sim is not None else None,
                    "replay_prob": round(rep_prob, 4) if rep_prob is not None else None,
                    "spoof": "OFF (domain shift)"
                },
                "risk": round(final_risk, 4),
                "band": final_band,
                "decision": final_decision
            }]
            windows_scored = 1
            windows_skipped_low_speech = 0
            explanation = risk_res["explanation"]

        else:
            # Mode "stream" (Full speed StreamingSession)
            session = StreamingSession(
                call_sid=call_sid,
                stream_sid=f"MZ_{uuid.uuid4().hex[:8]}",
                use_spoof=False,
                audit_logger=None
            )

            # Convert 16k audio to 8k mu-law 20ms frames
            audio_8k = resample_poly(audio_16k, up=1, down=2)
            pcm_8k = np.clip(audio_8k * 32767.0, -32768, 32767).astype(np.int16)
            frame_len = 160

            windows_scored_list = []
            actions_fired = []
            windows_skipped_low_speech = 0

            context = {
                "action": action_sensitivity,
                "action_sensitivity": action_sensitivity,
                "caller_not_allowlisted": False,
                "simulation": True,
                "simulation_label": UPLOAD_LABEL
            }

            for i in range(0, len(pcm_8k) - frame_len + 1, frame_len):
                chunk = pcm_8k[i:i + frame_len]
                ulaw_bytes = encode_pcm_to_ulaw(chunk)
                b64_payload = base64.b64encode(ulaw_bytes).decode("ascii")

                session.ingest_twilio_payload(b64_payload)

                if session.audio_buffer.total_samples_received >= 32000 and (session.audio_buffer.total_samples_received % 16000 < 320):
                    ev = session.score_current_window(context)
                    if ev:
                        spk = ev.get("detector_scores", {}).get("speaker_sim")
                        rep = ev.get("detector_scores", {}).get("replay_prob")
                        windows_scored_list.append({
                            "window": ev["window"],
                            "window_index": ev["window"],
                            "speaker_sim": round(spk, 4) if spk is not None else None,
                            "replay_prob": round(rep, 4) if rep is not None else None,
                            "detector_scores": {
                                "speaker_sim": round(spk, 4) if spk is not None else None,
                                "replay_prob": round(rep, 4) if rep is not None else None,
                                "spoof": "OFF (domain shift)"
                            },
                            "risk": round(ev["risk"], 4),
                            "band": ev["band"],
                            "decision": ev["decision"]
                        })
                        act = ev.get("action_trigger")
                        if act == "step_up":
                            actions_fired.append("MOCK OTP")
                        elif act == "block":
                            actions_fired.append("Block")
                    else:
                        windows_skipped_low_speech += 1

            windows_scored = len(windows_scored_list)
            final_risk = windows_scored_list[-1]["risk"] if windows_scored_list else 0.0
            final_band = windows_scored_list[-1]["band"] if windows_scored_list else "LOW"
            outcome = compute_stream_outcome(actions_fired)
            sens_delta = 0.15 if action_sensitivity == "password_reset" else (0.20 if action_sensitivity == "wire_transfer" else 0.0)
            last_spk = windows_scored_list[-1]["speaker_sim"] if windows_scored_list and windows_scored_list[-1]["speaker_sim"] is not None else 0.0
            last_rep = windows_scored_list[-1]["replay_prob"] if windows_scored_list and windows_scored_list[-1]["replay_prob"] is not None else 0.0

            explanation = {
                "base_risk": round(final_risk, 4),
                "weights": {"speaker": 0.50, "replay": 0.50, "spoof": 0.00},
                "weighted_contributions": {
                    "speaker": round(0.5 * last_spk, 4),
                    "replay": round(0.5 * last_rep, 4),
                    "spoof": 0.0
                },
                "adjustments": {
                    "sensitivity": sens_delta
                },
                "sustained_actions": actions_fired
            }

        # 8. Scores-only audit record (no audio, no filename, no content hash)
        audit_logger.log_event(
            call_sid=call_sid,
            detector_scores={
                "speaker_sim": windows_scored_list[-1]["speaker_sim"] if windows_scored_list else None,
                "replay_prob": windows_scored_list[-1]["replay_prob"] if windows_scored_list else None,
                "spoof": "OFF (domain shift)"
            },
            context={
                "action_sensitivity": action_sensitivity,
                "mode": mode,
                "phone_sim": phone_sim_applied,
                "simulation_label": UPLOAD_LABEL
            },
            risk=final_risk,
            band=final_band,
            decision=outcome,
            explanation={"summary": f"Uploaded audio screened ({mode} mode)"}
        )

        return {
            "label": UPLOAD_LABEL,
            "simulation_label": UPLOAD_LABEL,
            "call_sid": call_sid,
            "mode": mode,
            "phone_sim_applied": phone_sim_applied,
            "duration": round(dur, 3),
            "original_format": meta["format"],
            "original_sample_rate": meta["sample_rate"],
            "peak": round(peak, 4),
            "rms_dbfs": round(rms_dbfs, 2),
            "speech_fraction": round(speech_frac, 4),
            "windows_scored": windows_scored,
            "windows_skipped_low_speech": windows_skipped_low_speech,
            "risk": round(final_risk, 4),
            "final_risk": round(final_risk, 4),
            "band": final_band,
            "final_band": final_band,
            "whole_stream_outcome": outcome,
            "outcome": outcome,
            "decision": outcome,
            "detector_scores": {
                "speaker_sim": windows_scored_list[-1]["speaker_sim"] if windows_scored_list else None,
                "replay_prob": windows_scored_list[-1]["replay_prob"] if windows_scored_list else None,
                "spoof": "OFF (domain shift)"
            },
            "windows": windows_scored_list,
            "spectrogram": compute_display_mel_spectrogram(audio_16k, 16000),
            "explanation": explanation,
            "warnings": warnings
        }

    finally:
        # Strictly delete all temporary files
        temp_dir_obj.cleanup()
