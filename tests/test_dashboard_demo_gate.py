"""
Step 2 Gate Integration Test: Dashboard WebSocket Demo Stream and Audit Verification.

Verifies:
1. Messages arriving over /dashboard-ws during a demo run contain the label 'SIMULATION, not a live call'.
2. Synthetic spoof score is absent / strictly reported as 'OFF (domain shift, see limitations)' with no numeric spoof score.
3. Telemetry analytics / window event counts match the cryptographic audit records logged during the demo.
"""

import asyncio
import json
import pytest
from starlette.testclient import TestClient

from server.app import app, demo_runner, audit_logger
from server.demo import SIMULATION_LABEL


@pytest.fixture
def client():
    return TestClient(app)


def test_dashboard_ws_demo_messages_and_audit_alignment(client):
    """
    Connects to /dashboard-ws, runs a demo scenario through the real pipeline,
    and asserts SIMULATION label, no spoof score, and exact match with audit records.
    """
    received_messages = []

    # Connect WebSocket
    with client.websocket_connect("/dashboard-ws") as ws:
        # Run demo scenario at accelerated speed for fast deterministic test execution
        scenario_id = "live_01"
        result = asyncio.run(demo_runner.run_scenario_stream(
            scenario_id=scenario_id,
            action_sensitivity="balance_check",
            speed=50.0  # fast execution
        ))

        call_sid = result["call_sid"]
        windows_count = result["total_windows"]
        assert windows_count > 0, "Demo scenario must produce scored windows"

        # Receive WebSocket messages corresponding to scored windows
        for _ in range(windows_count):
            raw_text = ws.receive_text()
            msg = json.loads(raw_text)
            received_messages.append(msg)

    # 1. Assert all WebSocket messages carry the SIMULATION label
    assert len(received_messages) == windows_count
    for msg in received_messages:
        assert msg.get("simulation_label") == SIMULATION_LABEL, (
            f"Expected label '{SIMULATION_LABEL}', got '{msg.get('simulation_label')}'"
        )
        assert msg.get("call_sid") == call_sid

        # 2. Assert no spoof score is broadcast (strictly marked OFF)
        assert "spoof_prob" not in msg, "spoof_prob must be removed from root message"
        det_scores = msg.get("detector_scores", {})
        assert "spoof_prob" not in det_scores, "spoof_prob must be removed from detector_scores"
        assert det_scores.get("spoof") == "OFF (domain shift, see limitations)", (
            f"Expected 'OFF (domain shift, see limitations)', got {det_scores.get('spoof')}"
        )

    # 3. Verify analytics counts match audit records
    r_audit = client.get(f"/audit?limit=50")
    assert r_audit.status_code == 200
    all_audits = r_audit.json()

    # Filter audit entries for this specific demo call_sid
    demo_audits = [rec for rec in all_audits if rec.get("call_sid") == call_sid]
    assert len(demo_audits) == windows_count, (
        f"Audit count mismatch: {len(demo_audits)} audit records vs {windows_count} WS events"
    )

    # Compare each window's risk and decision between WS message and audit log
    for idx, (ws_msg, audit_rec) in enumerate(zip(received_messages, demo_audits)):
        assert abs(ws_msg["risk"] - audit_rec["risk"]) < 1e-4, (
            f"Window {idx+1} risk mismatch: WS={ws_msg['risk']} vs Audit={audit_rec['risk']}"
        )
        assert ws_msg["band"] == audit_rec["band"], (
            f"Window {idx+1} band mismatch: WS={ws_msg['band']} vs Audit={audit_rec['band']}"
        )
        assert audit_rec["context"].get("simulation") is True
        assert audit_rec["context"].get("simulation_label") == SIMULATION_LABEL
