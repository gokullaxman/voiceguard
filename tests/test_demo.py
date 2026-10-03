"""
Unit tests for Demo Mode Runner (server/demo.py and /demo endpoints).
Tests allowlist rejection (400), single-demo conflict (409),
full streaming execution of genuine and cloned_replay scenarios with mock actions,
and verifies SIMULATION labeling and spoof score suppression.
"""

import pytest
import asyncio
from fastapi.testclient import TestClient

from server.app import app, demo_runner
from server.demo import DEMO_SCENARIOS, SIMULATION_LABEL, DemoRunner

client = TestClient(app)


def test_get_demo_scenarios_returns_allowlist_with_simulation_label():
    resp = client.get("/demo/scenarios")
    assert resp.status_code == 200
    data = resp.json()
    assert data["simulation_label"] == "SIMULATION, not a live call"
    scenarios = data["scenarios"]
    assert len(scenarios) == 9

    scenario_ids = [s["id"] for s in scenarios]
    assert "live_01" in scenario_ids
    assert "clone_replay_01" in scenario_ids

    for s in scenarios:
        assert s["source"] == "from the evaluation set"
        assert s["expected_outcome"] in ("Allow", "Not Allow (Step-up or Block)")
        assert s["simulation_label"] == "SIMULATION, not a live call"


def test_demo_run_allowlist_rejection():
    """Unallowlisted scenario IDs must be rejected with 400."""
    resp = client.post("/demo/run", json={"scenario_id": "malicious_or_unknown_clip"})
    assert resp.status_code == 400
    data = resp.json()
    assert "error" in data
    assert data["simulation_label"] == "SIMULATION, not a live call"


def test_single_running_demo_returns_409():
    """Starting a second demo while one is running must return 409 Conflict."""
    # Mock is_running to True
    original_is_running = demo_runner.is_running
    demo_runner.is_running = lambda: True
    demo_runner.current_scenario_id = "live_01"
    try:
        resp = client.post("/demo/run", json={"scenario_id": "live_01"})
        assert resp.status_code == 409
        data = resp.json()
        assert "Another demo scenario is already running" in data["error"]
        assert data["simulation_label"] == "SIMULATION, not a live call"
    finally:
        demo_runner.is_running = original_is_running
        demo_runner.current_scenario_id = None


@pytest.mark.anyio
async def test_full_run_genuine_and_cloned_replay_scenarios():
    """Runs genuine_live (live_01) and cloned_replay (clone_replay_01) through real pipeline."""
    runner = DemoRunner()

    events_live = []
    # 1. Run genuine_live at high simulation speed
    res_live = await runner.run_scenario_stream(
        scenario_id="live_01",
        action_sensitivity="balance_check",
        speed=100.0,
        on_window=lambda ev: events_live.append(ev)
    )

    assert res_live["simulation_label"] == "SIMULATION, not a live call"
    assert res_live["scenario_id"] == "live_01"
    assert res_live["total_windows"] >= 1
    assert len(events_live) == res_live["total_windows"]

    for ev in events_live:
        assert ev["simulation_label"] == "SIMULATION, not a live call"
        # Synthetic spoof must be OFF string, not a float score
        assert ev["spoof_status"] == "OFF (domain shift, see limitations)"
        assert "spoof_prob" not in ev
        assert ev["detector_scores"]["spoof"] == "OFF (domain shift, see limitations)"
        # Check scores-only
        assert "audio" not in ev
        assert "raw_pcm" not in ev

    # 2. Run cloned_replay at high simulation speed
    events_replay = []
    res_replay = await runner.run_scenario_stream(
        scenario_id="clone_replay_01",
        action_sensitivity="balance_check",
        speed=100.0,
        on_window=lambda ev: events_replay.append(ev)
    )

    assert res_replay["simulation_label"] == "SIMULATION, not a live call"
    assert res_replay["scenario_id"] == "clone_replay_01"
    assert res_replay["total_windows"] >= 1

    for ev in events_replay:
        assert ev["simulation_label"] == "SIMULATION, not a live call"
        assert ev["spoof_status"] == "OFF (domain shift, see limitations)"
        assert "spoof_prob" not in ev


def test_demo_audio_endpoint():
    """Verifies audio player endpoint serves allowlisted audio only."""
    # Allowlisted audio
    r_ok = client.get("/demo/audio/live_01")
    assert r_ok.status_code == 200
    assert r_ok.headers["content-type"] in ("audio/wav", "audio/x-wav")
    assert len(r_ok.content) > 1000

    # Unallowlisted audio
    r_bad = client.get("/demo/audio/forbidden_clip")
    assert r_bad.status_code == 400
