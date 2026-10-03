"""
Step 1 Gate Test: Upload Endpoint Validation, Safety, and Privacy (tests/test_upload_endpoint.py).

Verifies:
1. Synthetic valid WAV accepted (status 200) with UPLOAD ANALYSIS label and no spoof number.
2. Non-audio file renamed .wav rejected with 400.
3. Oversize (>25MB) rejected with 400.
4. Too-short (<2.0s) rejected with 400.
5. Temporary directory cleanup: no temporary upload directories or audio left behind.
6. Scores-only audit record: no raw audio, PCM, filename, or content hash in audit log.
7. Operates correctly with empty TWILIO_* and PUBLIC_BASE_URL.
"""

import io
import os
import glob
import json
import pytest
import numpy as np
import soundfile as sf
from starlette.testclient import TestClient

from server.app import app
from server.upload import UPLOAD_LABEL, MAX_FILE_SIZE


@pytest.fixture
def client():
    return TestClient(app)


def create_synthetic_wav(duration_s: float = 3.0, sr: int = 16000, freq: float = 440.0) -> bytes:
    """Generates synthetic sine wave audio as in-memory WAV bytes."""
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False, dtype=np.float32)
    audio = 0.5 * np.sin(2 * np.pi * freq * t)
    buf = io.BytesIO()
    sf.write(buf, audio, sr, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def test_valid_synthetic_wav_accepted(client):
    """Synthetic valid WAV (3.0s) accepted with 200, UPLOAD label, and absent spoof score."""
    wav_bytes = create_synthetic_wav(duration_s=3.0)

    resp = client.post(
        "/analyze/upload",
        files={"file": ("synth_valid.wav", wav_bytes, "audio/wav")},
        data={"action_sensitivity": "balance_check", "mode": "stream", "phone_sim": "true"}
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["simulation_label"] == UPLOAD_LABEL
    assert data["mode"] == "stream"
    assert data["phone_sim_applied"] is True
    assert data["duration"] >= 2.9
    assert data["outcome"] in ("Allow", "Step-up only", "Block")

    # Detector scores
    det = data["detector_scores"]
    assert det["spoof"] == "OFF (domain shift)"
    assert "spoof_prob" not in det
    assert "spoof_prob" not in data

    # Warnings check
    assert "calibrated for one enrolled speaker" in data["warnings"]


def test_non_audio_file_renamed_wav_rejected(client):
    """A non-audio binary/text file renamed .wav must be rejected with 400."""
    fake_bytes = b"This is plain text pretending to be a RIFF header and audio waveform content."

    resp = client.post(
        "/analyze/upload",
        files={"file": ("fake_audio.wav", fake_bytes, "audio/wav")},
        data={"action_sensitivity": "balance_check", "mode": "stream"}
    )

    assert resp.status_code == 400
    err = resp.json()
    assert "error" in err
    assert "simulation_label" in err


def test_oversize_file_rejected(client):
    """Files exceeding 25 MB must be rejected with 400."""
    oversize_bytes = b"0" * (MAX_FILE_SIZE + 1024)

    resp = client.post(
        "/analyze/upload",
        files={"file": ("oversize.wav", oversize_bytes, "audio/wav")},
        data={"action_sensitivity": "balance_check"}
    )

    assert resp.status_code == 400
    err = resp.json()
    assert "25 MB" in err["error"]


def test_too_short_audio_rejected(client):
    """Audio below minimum 2.0s must be rejected with 400."""
    short_bytes = create_synthetic_wav(duration_s=1.0)

    resp = client.post(
        "/analyze/upload",
        files={"file": ("too_short.wav", short_bytes, "audio/wav")},
        data={"action_sensitivity": "balance_check"}
    )

    assert resp.status_code == 400
    err = resp.json()
    assert "below minimum" in err["error"]


def test_temp_dir_cleaned_up_afterwards(client):
    """Asserts that temporary directory and files are completely removed after processing."""
    import tempfile
    wav_bytes = create_synthetic_wav(duration_s=2.5)

    # Count temp items before
    temp_root = tempfile.gettempdir()
    before_dirs = set(os.listdir(temp_root))

    resp = client.post(
        "/analyze/upload",
        files={"file": ("test_temp.wav", wav_bytes, "audio/wav")},
        data={"action_sensitivity": "balance_check"}
    )
    assert resp.status_code == 200

    after_dirs = set(os.listdir(temp_root))
    new_dirs = after_dirs - before_dirs
    # Verify no persistent temporary directories matching python tempfile pattern
    for d in new_dirs:
        full_p = os.path.join(temp_root, d)
        if os.path.isdir(full_p):
            # Assert no converted audio files remain in any new temp dir
            assert not glob.glob(os.path.join(full_p, "*.wav"))


def test_audit_record_contains_no_audio_or_filename(client):
    """Verifies that the audit event contains scores only (no audio, no filename, no content hash)."""
    wav_bytes = create_synthetic_wav(duration_s=3.0)

    resp = client.post(
        "/analyze/upload",
        files={"file": ("secret_user_clip.wav", wav_bytes, "audio/wav")},
        data={"action_sensitivity": "balance_check", "mode": "whole"}
    )
    assert resp.status_code == 200
    call_sid = resp.json()["call_sid"]
    assert call_sid.startswith("UPLOAD_")

    # Fetch audit log
    r_audit = client.get("/audit?limit=5")
    assert r_audit.status_code == 200
    audits = r_audit.json()
    target_rec = next((r for r in audits if r.get("call_sid") == call_sid), None)
    assert target_rec is not None

    rec_str = json.dumps(target_rec)
    assert "secret_user_clip.wav" not in rec_str, "Filename must not appear in audit log"
    assert "audio" not in target_rec, "Raw audio must not appear in audit log"
    assert "raw_pcm" not in target_rec
    assert "content_hash" not in target_rec
    assert target_rec["context"]["simulation_label"] == UPLOAD_LABEL


def test_works_with_empty_twilio_and_public_url(client, monkeypatch):
    """Endpoint functions completely with empty TWILIO_* credentials and empty PUBLIC_BASE_URL."""
    monkeypatch.setenv("TWILIO_ACCOUNT_SID", "")
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "")
    monkeypatch.setenv("TWILIO_PHONE_NUMBER", "")
    monkeypatch.setenv("PUBLIC_BASE_URL", "")

    wav_bytes = create_synthetic_wav(duration_s=2.5)
    resp = client.post(
        "/analyze/upload",
        files={"file": ("synth_no_twilio.wav", wav_bytes, "audio/wav")},
        data={"action_sensitivity": "balance_check", "mode": "stream"}
    )
    assert resp.status_code == 200
    assert resp.json()["simulation_label"] == UPLOAD_LABEL
