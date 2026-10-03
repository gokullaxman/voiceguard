"""
VoiceGuard Live Call Diagnostics (Phase 4 / Step 5).
Appends scores-only JSON lines to data/audit/live_windows.jsonl.
Never logs raw audio, audio payloads, TWILIO credentials, or phone numbers.
"""

import os
import json
import time
import threading
from typing import Dict, Any, Optional

DEFAULT_DIAGNOSTICS_PATH = "data/audit/live_windows.jsonl"
_diag_lock = threading.Lock()


class LiveDiagnosticsLogger:
    def __init__(self, log_path: str = DEFAULT_DIAGNOSTICS_PATH):
        self.log_path = log_path
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def _append(self, data: Dict[str, Any]):
        with _diag_lock:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(data) + "\n")

    def log_window_score(
        self,
        call_sid: str,
        window: int,
        speaker_sim: Optional[float],
        replay_prob: Optional[float],
        risk: float,
        band: str,
        decision: str,
        action_trigger: Optional[str],
        speech_fraction: float,
        buffer_rms_dbfs: float,
        timestamp: Optional[float] = None
    ):
        """Logs one scores-only JSON line per window."""
        record = {
            "event": "window_score",
            "timestamp": timestamp or time.time(),
            "call_sid": call_sid,
            "window": int(window),
            "speaker_sim": round(speaker_sim, 4) if speaker_sim is not None else None,
            "replay_prob": round(replay_prob, 4) if replay_prob is not None else None,
            "risk": round(risk, 4),
            "band": str(band),
            "decision": str(decision),
            "action_trigger": str(action_trigger) if action_trigger else None,
            "speech_fraction": round(speech_fraction, 4),
            "buffer_rms_dbfs": round(buffer_rms_dbfs, 2)
        }
        self._append(record)

    def log_frame_stat(
        self,
        call_sid: str,
        frame_index: int,
        payload_len: int,
        decoded_samples: int,
        sample_rate: int = 16000,
        timestamp: Optional[float] = None
    ):
        """Logs metadata stats for the first 5 frames only; no audio content."""
        record = {
            "event": "frame_stat",
            "timestamp": timestamp or time.time(),
            "call_sid": call_sid,
            "frame_index": int(frame_index),
            "payload_len": int(payload_len),
            "decoded_samples": int(decoded_samples),
            "sample_rate": int(sample_rate)
        }
        self._append(record)

    def log_lifecycle_event(
        self,
        event_name: str,
        call_sid: str,
        duration_seconds: Optional[float] = None,
        timestamp: Optional[float] = None
    ):
        """Logs stream lifecycle event (stream_started, stream_stopped, disconnect)."""
        record = {
            "event": event_name,
            "timestamp": timestamp or time.time(),
            "call_sid": call_sid,
        }
        if duration_seconds is not None:
            record["duration_seconds"] = round(duration_seconds, 2)
        self._append(record)
