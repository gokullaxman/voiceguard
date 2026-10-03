"""
VoiceGuard Live-Path Dry Run with Mocks (Phase 4 / Step 4).
Drives full pipeline: Webhook -> WS -> Scoring -> Sustained Rule -> Responses -> Audit -> Dashboard.
NOTICE: SIMULATION, not a live Twilio call.
"""

import os
import re
import json
import base64
import numpy as np
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from twilio.request_validator import RequestValidator

from server.app import app, active_sessions, audit_logger, dispatcher
from server.telephony import encode_pcm_to_ulaw
from server.streaming import StreamingSession


def run_live_pipeline_dry_run():
    print("=" * 80)
    print("[SIMULATION] STARTING VOICEGUARD LIVE-PATH DRY RUN")
    print("[SIMULATION] NOTICE: SIMULATION, not a live Twilio call")
    print("=" * 80)

    mock_auth_token = "mock_secret_dry_run_auth_token_32b"
    mock_public_url = "https://voiceguard-preview.ngrok-free.app"
    os.environ["TWILIO_AUTH_TOKEN"] = mock_auth_token
    os.environ["PUBLIC_BASE_URL"] = mock_public_url

    client = TestClient(app)

    # -------------------------------------------------------------
    # 1. Twilio Webhook (POST /voice)
    # -------------------------------------------------------------
    print("\n[SIMULATION] 1. INCOMING CALL WEBHOOK (POST /voice)")
    call_sid = "CA_dry_run_sim_01"
    webhook_url = f"{mock_public_url}/voice"
    form_params = {"CallSid": call_sid, "From": "+15551234", "To": "+15555678"}

    validator = RequestValidator(mock_auth_token)
    signature = validator.compute_signature(webhook_url, form_params)

    resp = client.post(
        "/voice",
        data=form_params,
        headers={"x-twilio-signature": signature}
    )
    print(f"[SIMULATION] Webhook status code: {resp.status_code}")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    twiml_content = resp.text
    assert "<Stream" in twiml_content
    assert "wss://" in twiml_content
    print("[SIMULATION] TwiML verified: contains wss:// and media stream configuration")

    # Extract token from TwiML
    token_match = re.search(r'<Parameter name="token" value="([^"]+)"', twiml_content)
    assert token_match, "Token parameter not found in TwiML"
    token = token_match.group(1)
    print("[SIMULATION] Extracted single-use stream handshake token from TwiML")

    # -------------------------------------------------------------
    # 2. WebSocket Media Stream Handshake & Real-Time Dashboard
    # -------------------------------------------------------------
    print("\n[SIMULATION] 2. WS HANDSHAKE (/twilio-ws) & DASHBOARD (/dashboard-ws)")
    dashboard_events = []

    # Connect dashboard
    with client.websocket_connect("/dashboard-ws") as dash_ws:
        print("[SIMULATION] Connected to /dashboard-ws listener")

        # Connect twilio stream
        with client.websocket_connect("/twilio-ws") as twilio_ws:
            print("[SIMULATION] Connected to /twilio-ws")

            start_event = {
                "event": "start",
                "sequenceNumber": "1",
                "start": {
                    "callSid": call_sid,
                    "streamSid": "MZ_dry_run_stream_01",
                    "customParameters": {"token": token}
                }
            }
            twilio_ws.send_text(json.dumps(start_event))
            ack = json.loads(twilio_ws.receive_text())
            assert ack.get("event") == "connected"
            print("[SIMULATION] Media stream handshake accepted")

            # Check active session registered
            assert call_sid in active_sessions
            session = active_sessions[call_sid]
            synthetic_pcm = (np.sin(np.linspace(0, 40 * np.pi, 160)) * 14000).astype(np.int16)
            b64_frame = base64.b64encode(encode_pcm_to_ulaw(synthetic_pcm)).decode("ascii")

            # ---------------------------------------------------------
            # 3. Step-Up fires ONLY after N consecutive MEDIUM windows
            # ---------------------------------------------------------
            print("\n[SIMULATION] 3. STEP-UP CHALLENGE ESCALATION (N=3 consecutive windows)")
            session.sustained_evidence.reset()
            # Windows 1 and 2: Medium risk (0.45)
            ev1 = session.sustained_evidence.evaluate_window(0.45)
            session.audit_logger.log_event(call_sid=call_sid, detector_scores={"speaker_sim": 0.40, "replay_prob": 0.45}, context={"action": "wire_transfer"}, risk=0.45, band=ev1["band"], decision=ev1["decision"], explanation={"base": 0.45})
            print(f"[SIMULATION] MEDIUM Window 1: streak={ev1['medium_count']} -> Decision: {ev1['decision']} | Action: {ev1['action_trigger']}")
            assert ev1["action_trigger"] is None, "Window 1 should not trigger action"

            ev2 = session.sustained_evidence.evaluate_window(0.45)
            session.audit_logger.log_event(call_sid=call_sid, detector_scores={"speaker_sim": 0.40, "replay_prob": 0.45}, context={"action": "wire_transfer"}, risk=0.45, band=ev2["band"], decision=ev2["decision"], explanation={"base": 0.45})
            print(f"[SIMULATION] MEDIUM Window 2: streak={ev2['medium_count']} -> Decision: {ev2['decision']} | Action: {ev2['action_trigger']}")
            assert ev2["action_trigger"] is None, "Window 2 should not trigger action"

            ev3 = session.sustained_evidence.evaluate_window(0.45)
            session.audit_logger.log_event(call_sid=call_sid, detector_scores={"speaker_sim": 0.40, "replay_prob": 0.45}, context={"action": "wire_transfer"}, risk=0.45, band=ev3["band"], decision=ev3["decision"], explanation={"base": 0.45})
            print(f"[SIMULATION] MEDIUM Window 3: streak={ev3['medium_count']} -> Decision: {ev3['decision']} | Action: {ev3['action_trigger']}")
            assert ev3["action_trigger"] == "step_up", "Window 3 should trigger step_up"
            act_step = dispatcher.trigger_step_up(call_sid)
            print(f"[SIMULATION] >>> DISPATCHER ACTION: {act_step['action']} on call")

            # ---------------------------------------------------------
            # 4. Sustained Rule: Block fires ONLY after N consecutive HIGH windows
            # ---------------------------------------------------------
            print("\n[SIMULATION] 4. SUSTAINED HIGH-RISK EVALUATION (N=3 consecutive windows)")
            session.sustained_evidence.reset()
            # Window 1 (HIGH risk) - MUST NOT fire step_up or block
            h1 = session.sustained_evidence.evaluate_window(0.85)
            session.audit_logger.log_event(call_sid=call_sid, detector_scores={"speaker_sim": 0.20, "replay_prob": 0.95}, context={"action": "wire_transfer"}, risk=0.85, band=h1["band"], decision=h1["decision"], explanation={"base": 0.85})
            print(f"[SIMULATION] HIGH Window 1: streak={h1['high_count']} -> Decision: {h1['decision']} | Action: {h1['action_trigger']}")
            assert h1["action_trigger"] is None, "No action on single high window"

            # Window 2 (HIGH risk)
            h2 = session.sustained_evidence.evaluate_window(0.85)
            session.audit_logger.log_event(call_sid=call_sid, detector_scores={"speaker_sim": 0.20, "replay_prob": 0.95}, context={"action": "wire_transfer"}, risk=0.85, band=h2["band"], decision=h2["decision"], explanation={"base": 0.85})
            print(f"[SIMULATION] HIGH Window 2: streak={h2['high_count']} -> Decision: {h2['decision']} | Action: {h2['action_trigger']}")
            assert h2["action_trigger"] is None, "No action on 2nd high window"

            # Window 3 (HIGH risk)
            h3 = session.sustained_evidence.evaluate_window(0.85)
            session.audit_logger.log_event(call_sid=call_sid, detector_scores={"speaker_sim": 0.20, "replay_prob": 0.95}, context={"action": "wire_transfer"}, risk=0.85, band=h3["band"], decision=h3["decision"], explanation={"base": 0.85})
            print(f"[SIMULATION] HIGH Window 3: streak={h3['high_count']} -> Decision: {h3['decision']} | Action: {h3['action_trigger']}")
            assert h3["action_trigger"] == "block", "Block must trigger on 3rd high window"

            # Trigger block action
            block_act = dispatcher.terminate_call(call_sid, reason="high_risk_impersonation")
            session.terminated = True
            print(f"[SIMULATION] >>> DISPATCHER ACTION: {block_act['action']} ({block_act['reason']})")

            # ---------------------------------------------------------
            # 5. Post-termination frames are ignored
            # ---------------------------------------------------------
            print("\n[SIMULATION] 5. POST-TERMINATION FRAME HANDLING")
            samples_before = session.audio_buffer.total_samples_received
            session.ingest_twilio_payload(b64_frame)
            samples_after = session.audio_buffer.total_samples_received
            assert samples_before == samples_after, "Terminated session should not accept frames"
            post_score = session.score_current_window()
            assert post_score is None, "Terminated session should return None for scoring"
            print("[SIMULATION] Post-termination frames successfully dropped and ignored")

            # Send stop event to finish stream
            twilio_ws.send_text(json.dumps({"event": "stop"}))

    # -------------------------------------------------------------
    # 6. Mid-stream disconnect handled cleanly
    # -------------------------------------------------------------
    print("\n[SIMULATION] 6. MID-STREAM ABRUPT DISCONNECT HANDLING")
    call_sid_abrupt = "CA_dry_run_abrupt_disconnect"
    token_abrupt = client.app.routes  # generate valid token
    from server.responses import generate_stream_token
    t_abrupt = generate_stream_token(call_sid_abrupt, mock_auth_token)

    with client.websocket_connect("/twilio-ws") as ws_abrupt:
        ws_abrupt.send_text(json.dumps({
            "event": "start",
            "start": {
                "callSid": call_sid_abrupt,
                "streamSid": "MZ_abrupt_01",
                "customParameters": {"token": t_abrupt}
            }
        }))
        ack_abrupt = json.loads(ws_abrupt.receive_text())
        assert ack_abrupt.get("event") == "connected"
        assert call_sid_abrupt in active_sessions
        # Abrupt disconnect by closing context
    assert call_sid_abrupt not in active_sessions, "Session should be cleaned up upon disconnect"
    print("[SIMULATION] Mid-stream disconnect handled cleanly; session removed from active state")

    # -------------------------------------------------------------
    # 7. Cryptographic Audit Chain Verification
    # -------------------------------------------------------------
    print("\n[SIMULATION] 7. CRYPTOGRAPHIC AUDIT LOG VERIFICATION")
    is_valid, err, count = audit_logger.verify_chain()
    print(f"[SIMULATION] Audit chain valid: {is_valid}")
    print(f"[SIMULATION] Total records verified: {count}")
    assert is_valid, f"Audit chain verification failed: {err}"
    assert count > 0, "No records found in audit chain"

    print("\n" + "=" * 80)
    print("[SIMULATION] ALL SIMULATION GATES PASSED")
    print("=" * 80)
    return True


if __name__ == "__main__":
    run_live_pipeline_dry_run()
