"""
Tests for Twilio Webhook Signature Validation, Media Stream Handshake,
and Public URL TwiML Configuration (Phase 4 / Step 1 & 2).
"""

import os
import json
import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from twilio.request_validator import RequestValidator

from server.app import app, bad_signature_count
from server.responses import generate_stream_token, stream_tokens_registry


@pytest.fixture
def mock_auth_env(monkeypatch):
    """Sets a known auth token and public base url for deterministic tests."""
    mock_token = "mock_secret_auth_token_32_bytes_ok"
    mock_public_url = "https://voiceguard-demo.ngrok-free.app"
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", mock_token)
    monkeypatch.setenv("PUBLIC_BASE_URL", mock_public_url)
    return {
        "auth_token": mock_token,
        "public_url": mock_public_url
    }


def test_valid_signature_accepted(mock_auth_env):
    """Tests that a correctly signed POST /voice webhook is accepted with 200 OK."""
    client = TestClient(app)
    auth_token = mock_auth_env["auth_token"]
    public_url = mock_auth_env["public_url"]

    validator = RequestValidator(auth_token)
    params = {"CallSid": "CA_test_valid_01", "From": "+15550001", "To": "+15550002"}
    webhook_url = f"{public_url}/voice"
    signature = validator.compute_signature(webhook_url, params)

    response = client.post(
        "/voice",
        data=params,
        headers={"x-twilio-signature": signature}
    )

    assert response.status_code == 200
    assert "application/xml" in response.headers["content-type"]
    assert "<Response>" in response.text
    assert "<Stream" in response.text
    assert "<Parameter name=\"token\"" in response.text


def test_invalid_signature_rejected(mock_auth_env):
    """Tests that an incorrectly signed POST /voice webhook returns 403 Forbidden."""
    client = TestClient(app)
    params = {"CallSid": "CA_test_invalid_01"}
    response = client.post(
        "/voice",
        data=params,
        headers={"x-twilio-signature": "bogus_invalid_signature_string"}
    )
    assert response.status_code == 403


def test_missing_signature_header_rejected(mock_auth_env):
    """Tests that a request missing X-Twilio-Signature returns 403 Forbidden."""
    client = TestClient(app)
    params = {"CallSid": "CA_test_missing_01"}
    response = client.post("/voice", data=params)
    assert response.status_code == 403


def test_differing_host_signature_rejected(mock_auth_env):
    """Tests that a signature computed for a different host is rejected with 403 Forbidden."""
    client = TestClient(app)
    auth_token = mock_auth_env["auth_token"]
    params = {"CallSid": "CA_test_diff_host_01"}
    # Signature signed for different host
    different_host_url = "https://different-host.ngrok-free.app/voice"
    validator = RequestValidator(auth_token)
    signature = validator.compute_signature(different_host_url, params)

    response = client.post(
        "/voice",
        data=params,
        headers={"x-twilio-signature": signature}
    )
    assert response.status_code == 403


def test_empty_public_base_url_returns_503(monkeypatch):
    """Tests that an empty PUBLIC_BASE_URL returns 503 Service Unavailable."""
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "mock_secret_auth_token_32_bytes_ok")
    monkeypatch.setenv("PUBLIC_BASE_URL", "")
    client = TestClient(app)
    params = {"CallSid": "CA_test_empty_base"}
    response = client.post(
        "/voice",
        data=params,
        headers={"x-twilio-signature": "any_signature"}
    )
    assert response.status_code == 503
    assert "Service Unavailable" in response.text


def test_twiml_public_url_wss_and_no_secrets(mock_auth_env):
    """
    Verifies that generated TwiML:
    - Derives stream URL from PUBLIC_BASE_URL
    - Uses wss://, never ws://
    - Contains no secret values or credentials
    """
    client = TestClient(app)
    auth_token = mock_auth_env["auth_token"]
    public_url = mock_auth_env["public_url"]

    validator = RequestValidator(auth_token)
    params = {"CallSid": "CA_test_twiml_secrets"}
    webhook_url = f"{public_url}/voice"
    signature = validator.compute_signature(webhook_url, params)

    response = client.post(
        "/voice",
        data=params,
        headers={"x-twilio-signature": signature}
    )
    assert response.status_code == 200
    content = response.text

    # Stream url check
    assert 'url="wss://voiceguard-demo.ngrok-free.app/twilio-ws"' in content
    # Strict wss:// enforcement: ensure no plain ws:// exists
    without_wss = content.replace("wss://", "")
    assert "ws://" not in without_wss

    # Ensure no secrets leaked in TwiML
    assert auth_token not in content
    assert os.getenv("VOICEGUARD_ENROLLMENT_KEY", "NON_EXISTENT_KEY") not in content
    assert "AC" not in content  # No Account SID leaked


def test_ws_handshake_valid_and_replayed_token_rejected(mock_auth_env):
    """
    Tests WS /twilio-ws handshake:
    - Valid token and callSid succeeds
    - Replayed token is rejected on second connection attempt
    """
    client = TestClient(app)
    call_sid = "CA_test_ws_token_01"
    token = generate_stream_token(call_sid, mock_auth_env["auth_token"])

    # 1. First connection: valid token -> handshake accepted
    with client.websocket_connect("/twilio-ws") as ws:
        start_msg = {
            "event": "start",
            "sequenceNumber": "1",
            "start": {
                "callSid": call_sid,
                "streamSid": "MZ_test_stream_01",
                "customParameters": {"token": token}
            }
        }
        ws.send_text(json.dumps(start_msg))
        # Connection should stay open; send stop event cleanly
        ws.send_text(json.dumps({"event": "stop"}))

    # 2. Second connection attempt with REPLAYED token: must be rejected
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/twilio-ws") as ws2:
            replay_msg = {
                "event": "start",
                "sequenceNumber": "1",
                "start": {
                    "callSid": call_sid,
                    "streamSid": "MZ_test_stream_02",
                    "customParameters": {"token": token}
                }
            }
            ws2.send_text(json.dumps(replay_msg))
            # Next receive should fail or socket close
            ws2.receive_text()
    assert exc_info.value.code == 1008


def test_ws_handshake_missing_call_sid_rejected(mock_auth_env):
    """Verifies that start event without callSid is rejected."""
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/twilio-ws") as ws:
            msg = {
                "event": "start",
                "sequenceNumber": "1",
                "start": {
                    "streamSid": "MZ_test_stream_no_call_sid",
                    "customParameters": {"token": "some_token"}
                }
            }
            ws.send_text(json.dumps(msg))
            ws.receive_text()
    assert exc_info.value.code == 1008


def test_ws_handshake_unknown_token_rejected(mock_auth_env):
    """Verifies that an unknown / unissued token is rejected."""
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/twilio-ws") as ws:
            msg = {
                "event": "start",
                "sequenceNumber": "1",
                "start": {
                    "callSid": "CA_test_unknown_token",
                    "streamSid": "MZ_test_stream_unknown",
                    "customParameters": {"token": "fake_token_not_registered"}
                }
            }
            ws.send_text(json.dumps(msg))
            ws.receive_text()
    assert exc_info.value.code == 1008
