"""
Step 2 Gate: Test that the dashboard contains the required upload card,
fixed disclaimer text, and that the upload response and rendered text
contain the label and strictly no numeric spoof score.
"""

import io
import json
import pytest
import soundfile as sf
import numpy as np
from fastapi.testclient import TestClient
from server.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_dashboard_renders_upload_card_and_fixed_disclaimer(client):
    response = client.get("/")
    assert response.status_code == 200
    html = response.text

    # 1. Analyse card header
    assert "Analyse an audio file" in html

    # 2. Fixed disclaimer text under result
    assert "UPLOAD ANALYSIS" in html

    # 3. Spoof card text "OFF (domain shift, see limitations)" is removed from upload panel
    assert "OFF (domain shift, see limitations)" not in html

    # 4. JSON download button present
    assert "Download result as JSON" in html

    # 5. Check no expected-vs-actual line inside upload panel
    upload_panel_start = html.find('class="card upload-panel"')
    upload_panel_end = html.find('class="grid"', upload_panel_start)
    assert upload_panel_start != -1 and upload_panel_end != -1
    upload_section_html = html[upload_panel_start:upload_panel_end]
    assert "Expected:" not in upload_section_html
    assert "Expected vs" not in upload_section_html


def test_upload_response_contains_label_and_no_spoof_number(client):
    # Create valid synthetic 2.5s 16kHz WAV
    sr = 16000
    t = np.linspace(0, 2.5, int(sr * 2.5), endpoint=False)
    audio = (0.25 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    buf = io.BytesIO()
    sf.write(buf, audio, sr, format="WAV")
    buf.seek(0)

    files = {"file": ("test_gate.wav", buf.read(), "audio/wav")}
    data = {
        "action_sensitivity": "balance_check",
        "mode": "stream",
        "phone_sim": "true",
    }

    resp = client.post("/analyze/upload", data=data, files=files)
    assert resp.status_code == 200
    payload = resp.json()

    # 1. Label check
    assert payload.get("label") == "UPLOAD ANALYSIS, not a validated accuracy figure"

    # 2. Spoof check: exactly "OFF (domain shift)" string in off mode, or calibrated experimental, NOT a raw spoof_prob
    scores = payload.get("detector_scores", {})
    assert "spoof_prob" not in scores
    if "spoof" in scores:
        assert scores.get("spoof") == "OFF (domain shift)"
    else:
        assert "spoof_calibrated_experimental" in scores or "spoof_calibrated_experimental" in payload

    # 3. Verify in all window outputs that raw spoof_prob is not present
    windows = payload.get("windows", [])
    for win in windows:
        w_scores = win.get("detector_scores", {})
        assert "spoof_prob" not in w_scores
        if "spoof" in w_scores:
            assert w_scores.get("spoof") == "OFF (domain shift)"
        else:
            assert "spoof_calibrated_experimental" in w_scores or "spoof_calibrated_experimental" in win

    # 4. Verify explanation has no spoof score or weight
    exp = payload.get("explanation", {})
    wc = exp.get("weighted_contributions", {})
    assert wc.get("spoof") == 0.0

    # 5. Check no audio bytes in response
    resp_text = json.dumps(payload)
    assert "riff" not in resp_text.lower()
    assert "wav" not in resp_text.lower() or "original_format" in resp_text
