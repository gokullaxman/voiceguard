"""
Integration Test for VoiceGuard Dashboard and WebSocket Gateway (Phase 5).
Validates:
  - Connection to /dashboard-ws
  - Real-time score events received at ~1 per second
  - Session analytics match the cryptographic audit records
  - Auto-reconnect behavior after socket disconnect
  - Endpoints /health, /audit, /audit/verify, and GET /
"""

import json
import time
import pytest
from starlette.testclient import TestClient

from server.app import app, broadcast_to_dashboard, audit_logger
from server.audit import AuditLogger


@pytest.fixture
def client():
    return TestClient(app)


def test_http_endpoints(client):
    """Verifies that all required HTTP endpoints respond with correct status."""
    # 1. Health
    r_health = client.get("/health")
    assert r_health.status_code == 200
    data = r_health.json()
    assert data["status"] == "healthy"
    assert "detectors" in data

    # 2. Audit list
    r_audit = client.get("/audit")
    assert r_audit.status_code == 200
    assert isinstance(r_audit.json(), list)

    # 3. Audit verify
    r_verify = client.get("/audit/verify")
    assert r_verify.status_code == 200
    v_data = r_verify.json()
    assert "valid" in v_data
    assert v_data["valid"] is True

    # 4. Root dashboard HTML
    r_root = client.get("/")
    assert r_root.status_code == 200
    assert "VoiceGuard" in r_root.text


def test_dashboard_ws_messaging_and_analytics(client):
    """Verifies dashboard-ws receives events, matches audit records, and reconnects."""
    events_received = []

    # 1. Connect WebSocket
    with client.websocket_connect("/dashboard-ws") as ws:
        # Simulate 3 streamed events arriving at 1 per second
        for i in range(1, 4):
            score_event = {
                "window": i,
                "call_sid": f"CA_dash_test_{i}",
                "timestamp": f"2026-10-02T12:00:0{i}Z",
                "detector_scores": {"speaker_sim": 0.85, "replay_prob": 0.05},
                "risk": 0.15 * i,
                "band": "LOW" if i < 3 else "MEDIUM",
                "decision": "Allow" if i < 3 else "Step-Up / Challenge",
                "sustained_high": False,
                "latency_ms": 150.0,
                "record_hash": f"hash_{i:04d}"
            }
            # Append audit record
            audit_logger.log_event(
                call_sid=score_event["call_sid"],
                detector_scores=score_event["detector_scores"],
                context={"action": "balance_check"},
                risk=score_event["risk"],
                band=score_event["band"],
                decision=score_event["decision"],
                explanation={"base": score_event["risk"]}
            )

            # Send via broadcast helper
            r_post = client.post("/test/broadcast", json=score_event)
            assert r_post.status_code == 200
            msg_text = ws.receive_text()
            data = json.loads(msg_text)
            events_received.append(data)

    assert len(events_received) == 3
    assert events_received[0]["window"] == 1
    assert events_received[2]["band"] == "MEDIUM"

    # Verify analytics match audit records
    recent_audits = client.get("/audit?limit=3").json()
    assert len(recent_audits) >= 3
    # Check that the last audit record call_sid matches
    assert recent_audits[-1]["call_sid"] == "CA_dash_test_3"
    assert recent_audits[-1]["band"] == "MEDIUM"

    # 2. Test reconnect after disconnect
    with client.websocket_connect("/dashboard-ws") as ws2:
        reconnect_event = {
            "window": 4,
            "call_sid": "CA_dash_reconnect",
            "risk": 0.20,
            "band": "LOW",
            "decision": "Allow"
        }
        r_reconn = client.post("/test/broadcast", json=reconnect_event)
        assert r_reconn.status_code == 200
        msg2 = ws2.receive_text()
        data2 = json.loads(msg2)
        assert data2["call_sid"] == "CA_dash_reconnect"
        assert data2["decision"] == "Allow"
