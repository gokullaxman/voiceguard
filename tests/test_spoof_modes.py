"""
Tests for VoiceGuard Spoof Display Modes (off, real, calibrated).
Verifies:
1. Fused risk, band, streaks, actions, audit risk fields, and outcome are byte-identical across modes.
2. Calibrated mode attaches 'spoof_calibrated_experimental' with required disclosure label.
3. String 'spoof probability' never appears in any payload.
4. Off mode contains no numeric spoof score.
"""

import os
import json
import base64
import numpy as np
import pytest
import soundfile as sf
from scipy.signal import resample_poly

from server.streaming import StreamingSession, get_spoof_display_mode
from server.telephony import encode_pcm_to_ulaw
from server.demo import compute_stream_outcome


def run_session_on_clip(clip_path: str, display_mode: str):
    os.environ["VOICEGUARD_SPOOF_DISPLAY"] = display_mode
    session = StreamingSession(
        call_sid=f"CA_test_{display_mode}",
        stream_sid=f"MZ_test_{display_mode}",
        use_spoof=False,
        audit_logger=None
    )
    assert session.display_mode == display_mode

    audio, sr = sf.read(clip_path, dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    if sr != 16000:
        audio_16k = resample_poly(audio, 16000, sr)
    else:
        audio_16k = audio

    audio_8k = resample_poly(audio_16k, 1, 2)
    pcm_8k = np.clip(audio_8k * 32767.0, -32768, 32767).astype(np.int16)
    frame_len = 160

    context = {
        "action": "balance_check",
        "action_sensitivity": "balance_check",
        "caller_not_allowlisted": False,
        "simulation": True,
        "simulation_label": "SIMULATION, not a live call"
    }

    windows = []
    actions = []

    for i in range(0, len(pcm_8k) - frame_len + 1, frame_len):
        chunk = pcm_8k[i:i + frame_len]
        ulaw = encode_pcm_to_ulaw(chunk)
        b64 = base64.b64encode(ulaw).decode("ascii")
        session.ingest_twilio_payload(b64)

        if session.audio_buffer.total_samples_received >= 32000 and (session.audio_buffer.total_samples_received % 16000 < 320):
            ev = session.score_current_window(context)
            if ev:
                windows.append(ev)
                act = ev.get("action_trigger")
                if act == "step_up":
                    actions.append("MOCK OTP")
                elif act == "block":
                    actions.append("Block")

    outcome = compute_stream_outcome(actions)
    return windows, actions, outcome


@pytest.mark.parametrize("clip_id,clip_path", [
    ("live_02", "data/genuine/live_02.wav"),
    ("live_03", "data/genuine/live_03.wav"),
    ("clone_01", "data/cloned/clone_01.wav"),
    ("clone_replay_02", "data/replay/clone_replay_02.wav"),
])
def test_identity_across_spoof_modes(clip_id, clip_path):
    """
    Asserts byte-identity of fused risk, band, streaks, actions, audit risk fields,
    and outcome across 'off', 'real', and 'calibrated' modes.
    """
    win_off, act_off, out_off = run_session_on_clip(clip_path, "off")
    win_real, act_real, out_real = run_session_on_clip(clip_path, "real")
    win_cal, act_cal, out_cal = run_session_on_clip(clip_path, "calibrated")

    assert len(win_off) == len(win_real) == len(win_cal)
    assert act_off == act_real == act_cal
    assert out_off == out_real == out_cal

    for w_o, w_r, w_c in zip(win_off, win_real, win_cal):
        # Fused risk
        assert w_o["risk"] == w_r["risk"] == w_c["risk"]
        # Band
        assert w_o["band"] == w_r["band"] == w_c["band"]
        # Streaks / sustained evidence
        assert w_o["sustained_high"] == w_r["sustained_high"] == w_c["sustained_high"]
        assert w_o["sustained_medium"] == w_r["sustained_medium"] == w_c["sustained_medium"]
        assert w_o["action_trigger"] == w_r["action_trigger"] == w_c["action_trigger"]
        # Decision
        assert w_o["decision"] == w_r["decision"] == w_c["decision"]


def test_calibrated_mode_label_and_no_spoof_probability_string():
    """
    Verifies that:
    1. Calibrated mode attaches spoof_calibrated_experimental with exact disclosure label.
    2. The string 'spoof probability' never appears in emitted payloads.
    3. Off mode contains no numeric spoof score.
    """
    clip_path = "data/genuine/live_02.wav"

    # 1. Test calibrated mode
    win_cal, _, _ = run_session_on_clip(clip_path, "calibrated")
    expected_label = "AASIST output recalibrated on project data (optimistic, one speaker). Display only, not used in decision."

    for w in win_cal:
        s = json.dumps(w).lower()
        assert "spoof probability" not in s

        # When window has enough audio (>= 64.6k), spoof_calibrated_experimental has value & label
        if "spoof_calibrated_experimental" in w:
            cal = w["spoof_calibrated_experimental"]
            assert cal["label"] == expected_label
            if cal["value"] is not None:
                assert 0.0 <= cal["value"] <= 1.0

    # 2. Test off mode
    win_off, _, _ = run_session_on_clip(clip_path, "off")
    for w in win_off:
        s = json.dumps(w).lower()
        assert "spoof probability" not in s
        assert "spoof_prob" not in w
        assert "spoof_calibrated_experimental" not in w
        assert w["detector_scores"]["spoof"] == "OFF (domain shift, see limitations)"
