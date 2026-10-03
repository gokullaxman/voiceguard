"""
Unit Tests for VoiceGuard Risk Engine and Sustained Evidence (Phase 3 Step 7).
Validates:
  - Contributions sum to base
  - Band boundaries (LOW, MEDIUM, HIGH)
  - Renormalization when a detector is None
  - Adjustments do not alter the base risk
  - Sustained evidence suppresses single noisy windows
  - NaN and out-of-range rejection
"""

import pytest
import math
from server.risk_engine import RiskEngine, SustainedEvidence


@pytest.fixture
def engine():
    return RiskEngine()


def test_contributions_sum_to_base(engine):
    """Verifies that the individual weighted detector contributions sum exactly to the base risk."""
    res = engine.compute_risk(spoof_prob=0.20, speaker_sim=0.60, replay_prob=0.10)
    contrib_sum = sum(res["contributions"].values())
    assert abs(contrib_sum - res["base_risk"]) < 1e-4


def test_band_boundaries(engine):
    """Verifies band thresholds: <0.30 LOW, 0.30-0.60 MEDIUM, >0.60 HIGH."""
    # Low: all zeros
    r_low = engine.compute_risk(spoof_prob=0.10, speaker_sim=0.80, replay_prob=0.10)
    assert r_low["final_risk"] < 0.30
    assert r_low["band"] == "LOW"
    assert r_low["decision"] == "Allow"

    # Medium: exactly around 0.40 - 0.55 under production calibration
    r_med = engine.compute_risk(spoof_prob=0.50, speaker_sim=0.37, replay_prob=0.50)
    assert 0.30 <= r_med["final_risk"] <= 0.60
    assert r_med["band"] == "MEDIUM"
    assert r_med["decision"] == "Step-Up / Challenge"

    # High: high risk inputs
    r_high = engine.compute_risk(spoof_prob=0.90, speaker_sim=0.10, replay_prob=0.90)
    assert r_high["final_risk"] > 0.60
    assert r_high["band"] == "HIGH"
    assert r_high["decision"] == "Block / Terminate"


def test_renormalization_missing_detector(engine):
    """Verifies that dropping a detector renormalizes active weights to 1.0 and names missing detectors."""
    # Drop spoof
    res = engine.compute_risk(spoof_prob=None, speaker_sim=0.75, replay_prob=0.80)
    assert "spoof" in res["missing_detectors"]
    # Remaining weights: speaker (0.30) + replay (0.30) -> each 0.50
    assert res["normalized_weights"]["speaker"] == 0.50
    assert res["normalized_weights"]["replay"] == 0.50
    assert sum(res["normalized_weights"].values()) == 1.0
    contrib_sum = sum(res["contributions"].values())
    assert abs(contrib_sum - res["base_risk"]) < 1e-4


def test_adjustments_do_not_alter_base(engine):
    """Verifies that additive context adjustments affect final risk but leave base risk unaltered."""
    res_no_ctx = engine.compute_risk(spoof_prob=0.20, speaker_sim=0.75, replay_prob=0.10)
    res_with_ctx = engine.compute_risk(
        spoof_prob=0.20,
        speaker_sim=0.75,
        replay_prob=0.10,
        context={"action": "wire_transfer", "caller_not_allowlisted": True}
    )

    # Base risk must be identical
    assert res_no_ctx["base_risk"] == res_with_ctx["base_risk"]
    # Final risk must reflect the additions
    assert res_with_ctx["total_adjustments"] == 0.35  # 0.20 (wire) + 0.15 (not allowlisted)
    expected_final = min(1.0, res_no_ctx["base_risk"] + 0.35)
    assert abs(res_with_ctx["final_risk"] - expected_final) < 1e-4
    assert res_with_ctx["adjustments"]["action_sensitivity"]["label"] == "unvalidated design values"


def test_sustained_evidence_suppresses_single_noisy_window():
    """Verifies that a single high-risk window does not trigger sustained escalation."""
    sustained = SustainedEvidence(consecutive_required=3, threshold=0.60)

    # Window 1: normal
    assert sustained.add_window(0.20) is False
    # Window 2: transient spike (HIGH)
    assert sustained.add_window(0.85) is False
    # Window 3: back to normal -> resets counter
    assert sustained.add_window(0.25) is False

    # Now provide 3 consecutive qualifying windows
    assert sustained.add_window(0.70) is False  # 1
    assert sustained.add_window(0.75) is False  # 2
    assert sustained.add_window(0.80) is True   # 3 -> Escalation triggered!


def test_nan_and_out_of_range_rejection(engine):
    """Verifies that NaN, Inf, and out-of-range inputs raise ValueError."""
    with pytest.raises(ValueError, match="NaN or Inf"):
        engine.compute_risk(spoof_prob=float("nan"))

    with pytest.raises(ValueError, match="NaN or Inf"):
        engine.compute_risk(speaker_sim=float("inf"))

    with pytest.raises(ValueError, match="out of range"):
        engine.compute_risk(spoof_prob=1.5)

    with pytest.raises(ValueError, match="out of range"):
        engine.compute_risk(speaker_sim=-2.0)
