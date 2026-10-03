"""
Unit and integration tests for Live-Call Diagnostics and Safety Behavior (Steps 5 & 6).
Verifies:
- live_windows.jsonl schema and data integrity
- first 5 frames stats logging
- lifecycle event logging
- privacy & secret hygiene: NO raw audio, NO TWILIO credentials, NO phone numbers in diagnostics
- trial message / silence suppression (speech_fraction gating) preserves sustained-evidence safeguards
- dry_mode logging vs non-dry mode idempotent dispatch
"""

import os
import re
import json
import pytest
from unittest.mock import MagicMock
import numpy as np

from server.diagnostics import LiveDiagnosticsLogger
from server.responses import TwilioActionDispatcher
from server.streaming import StreamingSession
from scripts.summarize_live_call import summarize_call


@pytest.fixture
def tmp_diag_file(tmp_path):
    log_file = tmp_path / "live_windows.jsonl"
    return str(log_file)


def test_diagnostics_logger_schema_and_contents(tmp_diag_file):
    """Verifies that window scores, frame stats, and lifecycle events match schema."""
    logger = LiveDiagnosticsLogger(log_path=tmp_diag_file)
    call_sid = "CA_test_diag_01"

    # 1. Lifecycle start
    logger.log_lifecycle_event("stream_started", call_sid=call_sid, timestamp=1000.0)

    # 2. First 5 frames
    for i in range(1, 6):
        logger.log_frame_stat(
            call_sid=call_sid,
            frame_index=i,
            payload_len=216,
            decoded_samples=320,
            sample_rate=16000,
            timestamp=1000.0 + i * 0.02
        )

    # 3. Window scores
    logger.log_window_score(
        call_sid=call_sid,
        window=1,
        speaker_sim=0.68,
        replay_prob=0.02,
        risk=0.15,
        band="LOW",
        decision="Allow",
        action_trigger=None,
        speech_fraction=0.85,
        buffer_rms_dbfs=-22.4,
        timestamp=1001.0
    )
    logger.log_window_score(
        call_sid=call_sid,
        window=2,
        speaker_sim=0.35,
        replay_prob=0.88,
        risk=0.75,
        band="HIGH",
        decision="Monitoring (Awaiting Sustained High Evidence)",
        action_trigger=None,
        speech_fraction=0.92,
        buffer_rms_dbfs=-18.1,
        timestamp=1001.5
    )

    # 4. Lifecycle stop & disconnect
    logger.log_lifecycle_event("stream_stopped", call_sid=call_sid, duration_seconds=5.25, timestamp=1005.25)
    logger.log_lifecycle_event("disconnect", call_sid=call_sid, duration_seconds=5.25, timestamp=1005.26)

    # Read records
    with open(tmp_diag_file, "r", encoding="utf-8") as f:
        lines = [json.loads(line.strip()) for line in f if line.strip()]

    assert len(lines) == 1 + 5 + 2 + 2  # 10 records total

    w1 = [r for r in lines if r.get("event") == "window_score" and r.get("window") == 1][0]
    assert w1["call_sid"] == call_sid
    assert w1["speaker_sim"] == 0.68
    assert w1["replay_prob"] == 0.02
    assert w1["risk"] == 0.15
    assert w1["band"] == "LOW"
    assert w1["speech_fraction"] == 0.85
    assert w1["buffer_rms_dbfs"] == -22.4

    f1 = [r for r in lines if r.get("event") == "frame_stat" and r.get("frame_index") == 1][0]
    assert f1["payload_len"] == 216
    assert f1["decoded_samples"] == 320
    assert f1["sample_rate"] == 16000
    assert "audio" not in f1

    stop_ev = [r for r in lines if r.get("event") == "stream_stopped"][0]
    assert stop_ev["duration_seconds"] == 5.25


def test_diagnostics_privacy_and_secret_hygiene(tmp_diag_file, monkeypatch):
    """
    Asserts that the diagnostics log contains NONE of:
    - Raw audio arrays or audio bytes
    - TWILIO values (Account SID, Auth Token, API keys)
    - Phone numbers (e.g. +1..., +91...)
    """
    test_sid = "FAKE_SID_FOR_TESTS"
    test_token = "99887766554433221100aabbccddeeff"
    test_phone = "+15551234567"

    monkeypatch.setenv("TWILIO_ACCOUNT_SID", test_sid)
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", test_token)

    logger = LiveDiagnosticsLogger(log_path=tmp_diag_file)
    logger.log_lifecycle_event("stream_started", call_sid="CA_safe_test")
    logger.log_frame_stat("CA_safe_test", 1, 216, 320, 16000)
    logger.log_window_score(
        call_sid="CA_safe_test",
        window=1,
        speaker_sim=0.7,
        replay_prob=0.01,
        risk=0.1,
        band="LOW",
        decision="Allow",
        action_trigger=None,
        speech_fraction=0.8,
        buffer_rms_dbfs=-20.0
    )

    with open(tmp_diag_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify no secrets in file
    assert test_sid not in content
    assert test_token not in content
    assert test_phone not in content

    # Verify no phone number patterns
    phone_pattern = re.compile(r"\+[0-9]{9,15}")
    assert not phone_pattern.search(content)

    # Verify no audio arrays or byte dumps
    assert "pcm" not in content.lower()
    assert "data:audio" not in content


def test_summarize_live_call_script(tmp_diag_file):
    """Tests that summarize_call correctly identifies risk driver and band distribution."""
    from pathlib import Path
    logger = LiveDiagnosticsLogger(log_path=tmp_diag_file)
    call_sid = "CA_replay_attack_summary"

    logger.log_lifecycle_event("stream_started", call_sid=call_sid, timestamp=10.0)
    for w in range(1, 4):
        logger.log_window_score(
            call_sid=call_sid,
            window=w,
            speaker_sim=0.70,     # Strong speaker similarity (low speaker risk)
            replay_prob=0.95,     # High replay probability (replay drove risk)
            risk=0.85,
            band="HIGH",
            decision="Block",
            action_trigger="block" if w == 3 else None,
            speech_fraction=0.88,
            buffer_rms_dbfs=-18.0
        )
    logger.log_lifecycle_event("stream_stopped", call_sid=call_sid, duration_seconds=4.5)

    summary = summarize_call(call_sid, log_path=Path(tmp_diag_file))
    assert summary is not None
    assert summary["windows_count"] == 3
    assert summary["band_counts"]["HIGH"] == 3
    assert summary["band_counts"]["LOW"] == 0
    assert "replay_prob" in summary["driver"]
    assert summary["call_duration"] == 4.5


def test_speech_fraction_suppression_and_safeguards():
    """
    Verifies that windows with speech_fraction < threshold return None (waiting for speech)
    and do not increment or reset sustained evidence.
    """
    session = StreamingSession(call_sid="CA_test_silence", use_spoof=False)
    session.min_speech_fraction = 0.30

    # Feed 2 seconds of pure silence
    silence = np.zeros(32000, dtype=np.float32)
    session.audio_buffer.append(silence)

    # Attempt scoring on silence
    res = session.score_current_window()
    assert res is None  # Suppressed due to low speech fraction
    assert session.window_index == 0  # No window scored
    assert session.sustained_evidence.high_count == 0  # Safeguards untouched


def test_dry_mode_logs_and_sends_nothing():
    """Tests that dry_mode=True logs the action and calls no Twilio client methods."""
    mock_twilio_client = MagicMock()
    dispatcher = TwilioActionDispatcher(dry_mode=True, twilio_client=mock_twilio_client)

    step_up_res = dispatcher.trigger_step_up("CA_dry_01")
    assert step_up_res["action"] == "step_up_otp"
    assert step_up_res["status"] == "dry_mode_logged"
    assert step_up_res["sent"] is False

    block_res = dispatcher.terminate_call("CA_dry_01", reason="high_risk_impersonation")
    assert block_res["action"] == "terminate_call"
    assert block_res["status"] == "dry_mode_logged"
    assert block_res["sent"] is False

    # Assert client was never called
    mock_twilio_client.calls.assert_not_called()


def test_non_dry_mode_sends_once_idempotent():
    """Tests that dry_mode=False dispatches once to Twilio client and is idempotent on repeat."""
    mock_twilio_client = MagicMock()
    mock_call = MagicMock()
    mock_twilio_client.calls.return_value = mock_call

    dispatcher = TwilioActionDispatcher(dry_mode=False, twilio_client=mock_twilio_client)

    # First dispatch: sent=True
    r1 = dispatcher.trigger_step_up("CA_live_01")
    assert r1["sent"] is True
    assert r1["status"] == "initiated"
    mock_twilio_client.calls.assert_called_once_with("CA_live_01")
    mock_call.update.assert_called_once()

    # Second dispatch for same call: idempotent (sent=False)
    r2 = dispatcher.trigger_step_up("CA_live_01")
    assert r2["sent"] is False
    assert r2["status"] == "already_sent"
    # Still called only once
    assert mock_call.update.call_count == 1
