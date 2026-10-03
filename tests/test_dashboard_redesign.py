"""
Tests for Step 5 Dashboard Redesign:
- The served HTML contains the SIMULATION banner
- The three-row detector list
- The disclaimer line: "Suspicious means the system is unsure or alarmed, not that the clip is proven fake. Allow does not prove the clip is genuine."
- The "display only" spectrogram label
- None of the forbidden strings:
    "Voice Cloning Detected", "Evidence-Ready", "Temporal break", "splice", "Voice synthesis detection"
- The spectrogram response has no audio samples
- /config/public contains no .env value
- The dashboard-ws and upload responses still contain no spoof number.
"""

import io
import os
import json
import pytest
import soundfile as sf
import numpy as np
from fastapi.testclient import TestClient
from dotenv import dotenv_values

from server.app import app

client = TestClient(app)


def test_dashboard_served_html_elements_and_forbidden_strings():
    resp = client.get("/")
    assert resp.status_code == 200
    html = resp.text

    # 1. SIMULATION banner
    assert "SIMULATION, not a live call" in html

    # 2. Three-row detector list
    assert "Speaker match" in html
    assert "Replay probability" in html
    assert "Synthetic speech (SPOOF)" in html
    assert "OFF, domain shift" in html

    # 3. Disclaimer line
    assert "Suspicious means the system is unsure or alarmed, not that the clip is proven fake. Allow does not prove the clip is genuine." in html

    # 4. Mel-spectrogram display only label
    assert "Mel-spectrogram (display only, not the model input)" in html

    # 5. Forbidden strings check
    forbidden_strings = [
        "Voice Cloning Detected",
        "Evidence-Ready",
        "Temporal break",
        "splice",
        "Voice synthesis detection"
    ]
    html_lower = html.lower()
    for s in forbidden_strings:
        assert s.lower() not in html_lower, f"Forbidden string '{s}' found in dashboard HTML"


def test_spectrogram_response_has_no_audio_samples():
    resp = client.get("/demo/spectrogram/live_01")
    assert resp.status_code == 200
    data = resp.json()

    assert "mel_matrix" in data
    assert "n_mels" in data
    assert data["n_mels"] <= 64
    assert data["n_frames"] <= 300

    # Ensure no audio samples exist in response
    forbidden_keys = {"audio", "pcm", "samples", "raw_audio", "waveform", "bytes"}
    for k in forbidden_keys:
        assert k not in data, f"Key '{k}' must not be present in spectrogram response"

    # Ensure matrix values are int8
    for row in data["mel_matrix"]:
        for val in row:
            assert isinstance(val, int)
            assert -128 <= val <= 127


def test_public_config_contains_no_env_values():
    resp = client.get("/config/public")
    assert resp.status_code == 200
    data = resp.json()

    assert "a" in data
    assert "b" in data
    assert "bands" in data
    assert "sustained_evidence" in data

    # Check against .env values
    if os.path.exists(".env"):
        env_dict = dotenv_values(".env")
        for k, v in env_dict.items():
            if v and len(str(v).strip()) > 3:
                # Value must not appear anywhere in public config json
                val_str = str(v).strip()
                assert val_str not in json.dumps(data), f"Secret from .env key '{k}' found in /config/public!"


def test_upload_and_ws_contain_no_spoof_number():
    # 1. Upload test
    sr = 16000
    t = np.linspace(0, 2.5, int(sr * 2.5), endpoint=False)
    audio = (0.2 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    buf = io.BytesIO()
    sf.write(buf, audio, sr, format="WAV")
    buf.seek(0)

    resp = client.post(
        "/analyze/upload",
        files={"file": ("test.wav", buf.read(), "audio/wav")},
        data={"action_sensitivity": "balance_check", "mode": "stream", "phone_sim": "true"}
    )
    assert resp.status_code == 200
    up_data = resp.json()

    # Check root and detector_scores for spoof number
    assert "spoof_prob" not in up_data
    if "detector_scores" in up_data:
        spoof_val = up_data["detector_scores"].get("spoof")
        assert not isinstance(spoof_val, (int, float)), f"Spoof score must not be numeric: {spoof_val}"

    # Check per-window detector scores
    for w in up_data.get("windows", []):
        assert "spoof_prob" not in w
        if "detector_scores" in w:
            sp = w["detector_scores"].get("spoof")
            assert not isinstance(sp, (int, float))

    # Check spectrogram is in upload response and contains no audio samples
    assert "spectrogram" in up_data
    spec = up_data["spectrogram"]
    assert "mel_matrix" in spec
    assert "audio" not in spec
