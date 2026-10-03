"""
Test for Step 1 Gate: Unified Expectation and Match Logic.
Verifies:
1. Outcome definition from whole-stream actions:
   - Allow: no action fired
   - Step-up only: step_up fired, no block
   - Block: block fired
2. Expectation definition:
   - genuine_live: Allow
   - cloned_direct, genuine_replay, cloned_replay: Not Allow (Step-up or Block)
3. Match definition:
   - Match = (genuine and outcome is Allow) or (attack and outcome is Step-up only or Block)
   - live_01 and live_02 style cases: genuine + step_up = MISMATCH (discrepancy: "false step-up")
   - attack + allow = MISMATCH (discrepancy: "missed")
"""

import pytest
from server.demo import (
    compute_stream_outcome,
    evaluate_scenario_match,
    DEMO_SCENARIOS,
    DemoRunner
)


def test_compute_stream_outcome():
    # Allow: no action fired
    assert compute_stream_outcome([]) == "Allow"
    assert compute_stream_outcome(["None"]) == "Allow"

    # Step-up only: step_up fired, no block
    assert compute_stream_outcome(["MOCK OTP"]) == "Step-up only"
    assert compute_stream_outcome(["step_up"]) == "Step-up only"
    assert compute_stream_outcome(["MOCK OTP", "MOCK OTP"]) == "Step-up only"

    # Block: block fired (regardless of earlier step_up)
    assert compute_stream_outcome(["Block"]) == "Block"
    assert compute_stream_outcome(["MOCK OTP", "Block"]) == "Block"
    assert compute_stream_outcome(["Block", "MOCK OTP"]) == "Block"


def test_evaluate_scenario_match_genuine():
    # Genuine + Allow -> Match
    res_allow = evaluate_scenario_match("genuine_live", "Allow")
    assert res_allow["expected"] == "Allow"
    assert res_allow["match"] is True
    assert res_allow["discrepancy"] is None

    # Genuine + Step-up only -> Mismatch ("false step-up") [e.g. live_01, live_02]
    res_stepup = evaluate_scenario_match("genuine_live", "Step-up only")
    assert res_stepup["expected"] == "Allow"
    assert res_stepup["match"] is False
    assert res_stepup["discrepancy"] == "false step-up"

    # Genuine + Block -> Mismatch ("false block")
    res_block = evaluate_scenario_match("genuine_live", "Block")
    assert res_block["expected"] == "Allow"
    assert res_block["match"] is False
    assert res_block["discrepancy"] == "false block"


def test_evaluate_scenario_match_attacks():
    attack_groups = ["cloned_direct", "genuine_replay", "cloned_replay"]

    for grp in attack_groups:
        # Attack + Step-up only -> Match
        res_stepup = evaluate_scenario_match(grp, "Step-up only")
        assert res_stepup["expected"] == "Not Allow (Step-up or Block)"
        assert res_stepup["match"] is True
        assert res_stepup["discrepancy"] is None

        # Attack + Block -> Match
        res_block = evaluate_scenario_match(grp, "Block")
        assert res_block["expected"] == "Not Allow (Step-up or Block)"
        assert res_block["match"] is True
        assert res_block["discrepancy"] is None

        # Attack + Allow -> Mismatch ("missed")
        res_allow = evaluate_scenario_match(grp, "Allow")
        assert res_allow["expected"] == "Not Allow (Step-up or Block)"
        assert res_allow["match"] is False
        assert res_allow["discrepancy"] == "missed"


def test_demo_scenarios_expectations_structure():
    """Verify that all allowlisted scenarios in demo.py use the unified expectation definition."""
    for sc_id, sc in DEMO_SCENARIOS.items():
        if sc["group"] == "genuine_live":
            assert sc["expected_outcome"] == "Allow"
        else:
            assert sc["expected_outcome"] == "Not Allow (Step-up or Block)"


@pytest.mark.anyio
async def test_live_01_and_live_02_style_mismatch():
    """
    Tests live_01 streaming execution through DemoRunner.
    live_01 triggers early MOCK OTP step-up action.
    Under Step 1 rules, genuine_live + Step-up must evaluate to match=False and discrepancy='false step-up'.
    """
    runner = DemoRunner()
    res = await runner.run_scenario_stream("live_01", speed=100.0)

    assert res["scenario_id"] == "live_01"
    assert res["final_band"] == "LOW"  # Final band settled at LOW
    assert res["outcome"] == "Step-up only"  # Whole-stream outcome
    assert res["expected_outcome"] == "Allow"
    assert res["match"] is False  # Genuine + Step-up = MISMATCH
    assert res["discrepancy"] == "false step-up"
