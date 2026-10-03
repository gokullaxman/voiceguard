"""
Test that audio clips give the identical outcome across all three streaming execution paths:
(1) scripts/eval_streaming.py stream_clip()
(2) server/demo.py DemoRunner.run_scenario_stream()
(3) server/upload.py /analyze/upload endpoint
"""

import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from server.app import app
from server.demo import DemoRunner
from scripts.eval_streaming import stream_clip

@pytest.mark.anyio
async def test_clip_outcome_identical_across_all_three_paths():
    client = TestClient(app)
    runner = DemoRunner()

    clip_id = "live_02"
    group = "genuine_live"
    sim_path = "data/phone_simulated/live_02_sim.wav"
    orig_path = "data/genuine/live_02.wav"

    # 1. Path (a): eval_streaming
    clip_meta = {"clip_id": clip_id, "label": group, "simulated_path": sim_path}
    res_eval = stream_clip(clip_meta)
    outcome_eval = res_eval["outcome"]

    # 2. Path (b): demo runner
    res_demo = await runner.run_scenario_stream(clip_id, speed=50.0)
    outcome_demo = res_demo["outcome"]

    # 3. Path (c): upload endpoint
    with open(orig_path, "rb") as f:
        file_bytes = f.read()

    resp = client.post(
        "/analyze/upload",
        files={"file": (os.path.basename(orig_path), file_bytes, "audio/wav")},
        data={"action_sensitivity": "balance_check", "mode": "stream", "phone_sim": "true"}
    )
    assert resp.status_code == 200
    up_data = resp.json()
    outcome_upload = up_data.get("outcome") or up_data.get("whole_stream_outcome")

    # Assert all three paths agree on outcome and per-window count
    assert outcome_eval == outcome_demo, f"eval ({outcome_eval}) != demo ({outcome_demo})"
    assert outcome_demo == outcome_upload, f"demo ({outcome_demo}) != upload ({outcome_upload})"
    assert outcome_eval == "Allow"

    # Assert per-window count and risks match
    assert len(res_demo["windows"]) == 5
    assert len(up_data["windows"]) == 5
    for w_demo, w_up in zip(res_demo["windows"], up_data["windows"]):
        assert w_demo["band"] == w_up["band"]
        assert round(w_demo["risk"], 2) == round(w_up["risk"], 2)

