"""
Unit and Integration Tests for VoiceGuard Streaming Pipeline (server/streaming.py).
Validates:
  - Mu-law frame decoding and rolling buffer ingestion
  - Window extraction and buffer bounding
  - Disconnect and termination handling
  - Action dispatch integration (mock step-up and block triggers)
  - Audit chain generation from streaming events
"""

import os
import base64
import numpy as np
import pytest

from server.telephony import encode_pcm_to_ulaw
from server.streaming import AudioRollingBuffer, StreamingSession
from server.audit import AuditLogger
from server.responses import TwilioActionDispatcher


def test_audio_rolling_buffer():
    """Verifies that the rolling buffer correctly appends and caps audio length."""
    buf = AudioRollingBuffer(max_seconds=1.0, sr=16000)  # 16,000 samples max
    assert buf.total_samples_received == 0
    assert buf.get_window(16000) is None

    # Append 8000 samples (0.5s)
    c1 = np.ones(8000, dtype=np.float32) * 0.5
    buf.append(c1)
    assert buf.total_samples_received == 8000
    assert buf.get_window(16000) is None
    assert len(buf.get_available_audio()) == 8000

    # Append another 12000 samples (total 20,000 samples, buffer should keep last 16,000)
    c2 = np.ones(12000, dtype=np.float32) * 0.9
    buf.append(c2)
    assert buf.total_samples_received == 20000
    w = buf.get_window(16000)
    assert w is not None
    assert len(w) == 16000
    # Last 12000 should be 0.9, first 4000 should be 0.5
    assert np.allclose(w[:4000], 0.5)
    assert np.allclose(w[4000:], 0.9)


def test_streaming_session_ingest_and_score(tmp_path):
    """Verifies end-to-end streaming ingestion, scoring, and audit chain creation."""
    log_path = str(tmp_path / "stream_audit.jsonl")
    audit_logger = AuditLogger(log_path=log_path)
    session = StreamingSession(
        call_sid="CA_stream_test_01",
        use_spoof=False,
        audit_logger=audit_logger
    )

    # Generate 150 frames of 20 ms audio (3.0s total at 8 kHz = 24,000 samples = 48,000 samples at 16 kHz)
    t = np.linspace(0, 20 / 1000, 160, endpoint=False, dtype=np.float32)
    synthetic_pcm_8k = ((0.4 * np.sin(2 * np.pi * 300 * t) + 0.2 * np.sin(2 * np.pi * 600 * t) + 0.1 * np.sin(2 * np.pi * 900 * t)) * 32767).astype(np.int16)
    ulaw_bytes = encode_pcm_to_ulaw(synthetic_pcm_8k)
    b64_payload = base64.b64encode(ulaw_bytes).decode("ascii")

    for _ in range(150):
        session.ingest_twilio_payload(b64_payload)

    # Score current window
    res = session.score_current_window()
    assert res is not None
    assert res["call_sid"] == "CA_stream_test_01"
    assert "risk" in res
    assert res["band"] in ["LOW", "MEDIUM", "HIGH"]
    assert res["latency_ms"] >= 0.0

    # Verify audit chain
    is_valid, err, count = audit_logger.verify_chain(log_path)
    assert is_valid is True
    assert count == 1


def test_disconnect_and_termination_handling():
    """Verifies that a terminated session ignores subsequent frames and scoring calls."""
    session = StreamingSession(call_sid="CA_term_test")
    session.terminated = True

    # Attempt to ingest
    initial_samples = session.audio_buffer.total_samples_received
    synthetic_pcm_8k = (np.zeros(160)).astype(np.int16)
    ulaw_bytes = encode_pcm_to_ulaw(synthetic_pcm_8k)
    b64_payload = base64.b64encode(ulaw_bytes).decode("ascii")

    session.ingest_twilio_payload(b64_payload)
    assert session.audio_buffer.total_samples_received == initial_samples

    # Attempt to score
    res = session.score_current_window()
    assert res is None


def test_action_dispatcher():
    """Verifies action dispatcher triggers step-up and termination."""
    dispatcher = TwilioActionDispatcher()
    call_sid = "CA_action_test"

    step_up = dispatcher.trigger_step_up(call_sid)
    assert step_up["action"] == "step_up_otp"
    assert step_up["call_sid"] == call_sid

    term = dispatcher.terminate_call(call_sid)
    assert term["action"] == "terminate_call"
    assert term["call_sid"] == call_sid
    assert len(dispatcher.mock_actions) == 2
