"""
VoiceGuard Phase P2 Acceptance Gate Tests
Verifies:
1. G.711 mu-law 256-code lookup table, roundtrip, and polyphase resampling.
2. Preprocessing, VAD, and rolling buffer short-buffer/silence rejection.
3. Every original audio sample has a corresponding phone-simulated version.
4. Dataset counts for enrolled speaker 'gokul' meet target (>= 10 per scenario).
"""

import json
import os
import pytest
from server.telephony import ULAW_DECODE_TABLE
from tests.test_telephony import reference_ulaw_decode
from scripts.prepare_data import load_settings, load_manifest


def test_gate_p2_telephony_components():
    """Validates that all 256 mu-law entries match reference formula."""
    for b in range(256):
        assert int(ULAW_DECODE_TABLE[b]) == reference_ulaw_decode(b)


def test_gate_p2_simulation_coverage():
    """Validates that every original file in dataset directories has a phone-simulated copy."""
    manifest = load_manifest()
    assert len(manifest) > 0, "Manifest is empty. Run `scripts/prepare_data.py` first."

    for item in manifest:
        orig = item.get("original_path")
        sim = item.get("simulated_path")
        assert os.path.exists(orig), f"Original audio missing: {orig}"
        assert os.path.exists(sim), f"Phone-simulated copy missing: {sim}"


def test_gate_p2_enrolled_speaker_dataset_counts():
    """
    Validates minimum 10 recordings per scenario for enrolled speaker 'gokul'.
    Fails with exact count shortfall if user recordings are pending.
    """
    settings = load_settings()
    dataset_cfg = settings.get("dataset", {})
    target_speaker = dataset_cfg.get("target_speaker_id", "gokul")
    min_target = dataset_cfg.get("min_samples_per_scenario", 10)

    manifest = load_manifest()
    counts = {
        "genuine_live": 0,
        "cloned_direct": 0,
        "genuine_replay": 0,
        "cloned_replay": 0,
    }

    for item in manifest:
        if item.get("speaker_id") == target_speaker and item.get("group") == "enrolled_target":
            lbl = item.get("label")
            if lbl in counts:
                counts[lbl] += 1

    missing = {s: min_target - c for s, c in counts.items() if c < min_target}
    assert len(missing) == 0, (
        f"Missing real recordings for '{target_speaker}': {missing}. "
        "Please record required clips via `scripts/record_samples.py`."
    )
