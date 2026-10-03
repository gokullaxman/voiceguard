"""
Unit and Integration Tests for Sustained Evidence Rules (Phase 4 / Step 4).
Validates:
  - Single HIGH window triggers nothing (no action trigger, decision is Monitoring)
  - N consecutive HIGH windows triggers Block action
  - N consecutive MEDIUM windows triggers Step-Up action
  - MEDIUM then LOW resets streak to 0
  - HIGH then MEDIUM resets high streak to 0
  - Duplicate triggers are idempotent (only fires once)
  - No actions after termination (frames dropped, scoring returns None)
"""

import pytest
from server.risk_engine import SustainedEvidence
from server.streaming import StreamingSession


def test_single_high_window_triggers_nothing():
    """A single high-risk window must not trigger any action."""
    sustained = SustainedEvidence(consecutive_required=3, medium_threshold=0.30, high_threshold=0.60)
    res = sustained.evaluate_window(0.85)

    assert res["band"] == "HIGH"
    assert res["action_trigger"] is None
    assert "Monitoring" in res["decision"]
    assert res["is_sustained_high"] is False


def test_n_consecutive_high_windows_block():
    """N consecutive high-risk windows must trigger the block action on the Nth window."""
    sustained = SustainedEvidence(consecutive_required=3, medium_threshold=0.30, high_threshold=0.60)

    # Window 1
    w1 = sustained.evaluate_window(0.75)
    assert w1["action_trigger"] is None

    # Window 2
    w2 = sustained.evaluate_window(0.80)
    assert w2["action_trigger"] is None

    # Window 3 -> N qualifying windows reached
    w3 = sustained.evaluate_window(0.85)
    assert w3["action_trigger"] == "block"
    assert w3["is_sustained_high"] is True
    assert "Block" in w3["decision"]


def test_n_consecutive_medium_windows_step_up():
    """N consecutive medium-risk windows must trigger step-up on the Nth window."""
    sustained = SustainedEvidence(consecutive_required=3, medium_threshold=0.30, high_threshold=0.60)

    # Windows 1 and 2
    assert sustained.evaluate_window(0.45)["action_trigger"] is None
    assert sustained.evaluate_window(0.50)["action_trigger"] is None

    # Window 3
    w3 = sustained.evaluate_window(0.55)
    assert w3["action_trigger"] == "step_up"
    assert w3["is_sustained_medium"] is True
    assert "Step-Up" in w3["decision"]


def test_medium_then_low_resets_streak():
    """Dropping from MEDIUM to LOW resets the qualifying streak."""
    sustained = SustainedEvidence(consecutive_required=3, medium_threshold=0.30, high_threshold=0.60)

    # 2 medium windows
    assert sustained.evaluate_window(0.40)["medium_count"] == 1
    assert sustained.evaluate_window(0.45)["medium_count"] == 2

    # Drop to LOW
    w_low = sustained.evaluate_window(0.20)
    assert w_low["band"] == "LOW"
    assert w_low["medium_count"] == 0
    assert w_low["action_trigger"] is None
    assert w_low["decision"] == "Allow"

    # Next medium starts at 1, not 3
    w_next = sustained.evaluate_window(0.40)
    assert w_next["medium_count"] == 1
    assert w_next["action_trigger"] is None


def test_high_then_medium_resets_high_streak():
    """Transition from HIGH to MEDIUM resets the high streak while keeping medium active."""
    sustained = SustainedEvidence(consecutive_required=3, medium_threshold=0.30, high_threshold=0.60)

    # 2 high windows
    sustained.evaluate_window(0.70)
    sustained.evaluate_window(0.75)
    assert sustained.high_count == 2

    # Transition to medium (0.45)
    w_med = sustained.evaluate_window(0.45)
    assert w_med["band"] == "MEDIUM"
    assert w_med["high_count"] == 0  # reset high
    assert w_med["medium_count"] == 3  # 3rd consecutive non-low window -> triggers step-up
    assert w_med["action_trigger"] == "step_up"


def test_duplicate_triggers_are_idempotent():
    """Subsequent qualifying windows after an action trigger must not refire the same action."""
    sustained = SustainedEvidence(consecutive_required=3, medium_threshold=0.30, high_threshold=0.60)

    # Trigger step-up on 3rd window
    sustained.evaluate_window(0.40)
    sustained.evaluate_window(0.45)
    w3 = sustained.evaluate_window(0.50)
    assert w3["action_trigger"] == "step_up"

    # 4th and 5th medium windows should NOT fire step_up again
    w4 = sustained.evaluate_window(0.50)
    assert w4["action_trigger"] is None

    w5 = sustained.evaluate_window(0.55)
    assert w5["action_trigger"] is None


def test_no_actions_after_termination():
    """Once terminated, session drops incoming frames and scoring returns None."""
    session = StreamingSession(call_sid="CA_test_term_idempotent", use_spoof=False)
    session.terminated = True

    # Attempt to ingest
    import base64
    b64_dummy = base64.b64encode(b"\x00" * 320).decode("ascii")
    session.ingest_twilio_payload(b64_dummy)
    assert session.audio_buffer.total_samples_received == 0

    # Attempt to score
    res = session.score_current_window()
    assert res is None
