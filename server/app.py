"""
VoiceGuard Telephony and Streaming Server (Phase 4).
FastAPI application handling Twilio Voice webhooks, media stream WebSockets,
dashboard WebSocket broadcasts, and audit verification endpoints.
"""

import os
import json
import asyncio
import time
from urllib.parse import urlparse
from typing import Dict, Any, List, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response, UploadFile, File, Form
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from twilio.request_validator import RequestValidator

from server.telephony import decode_twilio_payload
from server.streaming import StreamingSession
from server.audit import AuditLogger
from server.responses import (
    generate_twiml_stream,
    generate_stream_token,
    validate_and_consume_stream_token,
    TwilioActionDispatcher,
)
from server.diagnostics import LiveDiagnosticsLogger
from server.demo import DemoRunner, DEMO_SCENARIOS, SIMULATION_LABEL

app = FastAPI(title="VoiceGuard Streaming Security Gateway", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active state
active_sessions: Dict[str, StreamingSession] = {}
active_stream_sids: Set[str] = set()
dashboard_subscribers: Set[WebSocket] = set()
audit_logger = AuditLogger()
dispatcher = TwilioActionDispatcher()
diagnostics_logger = LiveDiagnosticsLogger()
bad_signature_count: int = 0


async def broadcast_to_dashboard(message: Dict[str, Any]):
    """Broadcasts real-time risk event to connected web dashboard clients."""
    if not dashboard_subscribers:
        return
    payload = json.dumps(message)
    dead_clients = set()
    for ws in dashboard_subscribers:
        try:
            await ws.send_text(payload)
        except Exception:
            dead_clients.add(ws)
    dashboard_subscribers.difference_update(dead_clients)


demo_runner = DemoRunner(broadcast_callback=broadcast_to_dashboard)


def get_public_base_url() -> str:
    """Dynamically resolves PUBLIC_BASE_URL from os.environ or .env."""
    if "PUBLIC_BASE_URL" in os.environ:
        return os.environ["PUBLIC_BASE_URL"].strip().rstrip("/")
    from dotenv import dotenv_values
    if os.path.exists(".env"):
        val = dotenv_values(".env").get("PUBLIC_BASE_URL")
        if val:
            return val.strip().rstrip("/")
    return ""


@app.get("/health")
async def health_check():
    """Health endpoint returning booleans and non-secret status flags only."""
    from server.risk_engine import RiskEngine
    from dotenv import dotenv_values

    env_vals = dotenv_values(".env") if os.path.exists(".env") else {}
    public_url = get_public_base_url()
    public_base_url_set = bool(public_url and "your-" not in public_url and "xxxxxxxx" not in public_url)

    dry_mode = dispatcher.dry_mode

    engine = RiskEngine(config_path="config/settings.yaml")
    spoof_enabled = bool(engine.config.get("detectors", {}).get("spoof", {}).get("enabled", False))
    config_hash = engine.get_config_hash()
    live_config_hash = engine.get_live_config_hash("config/live.yaml")

    enrollment_loaded = False
    bin_path = "data/enrollment/enrolled_voiceprint.bin"
    if os.path.exists(bin_path):
        try:
            from server.enrollment import load_enrollment_key, decrypt_voiceprint
            k = load_enrollment_key()
            with open(bin_path, "rb") as f:
                bdata = f.read()
            emb, _ = decrypt_voiceprint(bdata, k)
            enrollment_loaded = bool(emb is not None and emb.shape == (192,))
        except Exception:
            enrollment_loaded = False

    sid = env_vals.get("TWILIO_ACCOUNT_SID", os.getenv("TWILIO_ACCOUNT_SID", ""))
    tok = env_vals.get("TWILIO_AUTH_TOKEN", os.getenv("TWILIO_AUTH_TOKEN", ""))
    twilio_credentials_present = bool(
        sid and tok and sid.startswith("AC") and "xxxx" not in sid.lower() and len(tok) >= 16 and "your_" not in tok.lower()
    )

    models_loaded = True
    try:
        replay_exists = os.path.exists("models/artifacts/replay.joblib") or os.path.exists("models/artifacts/replay_classifier.joblib")
        if not replay_exists or not os.path.exists("models/artifacts/AASIST.pth"):
            models_loaded = False
    except Exception:
        models_loaded = False

    return {
        "status": "healthy",
        "service": "VoiceGuard Gateway",
        "public_base_url_set": public_base_url_set,
        "dry_mode": dry_mode,
        "spoof_enabled": spoof_enabled,
        "config_hash": config_hash,
        "live_config_hash": live_config_hash,
        "enrollment_loaded": enrollment_loaded,
        "twilio_credentials_present": twilio_credentials_present,
        "models_loaded": models_loaded,
        "detectors": {
            "spoof": spoof_enabled,
            "speaker": True,
            "replay": True
        },
        "active_calls": len(active_sessions)
    }


@app.post("/voice")
async def voice_webhook(request: Request):
    """Twilio incoming voice webhook returning TwiML stream connection."""
    global bad_signature_count

    signature = request.headers.get("x-twilio-signature")
    if not signature:
        bad_signature_count += 1
        return Response(content="Forbidden: Missing signature header", status_code=403)

    if "TWILIO_AUTH_TOKEN" in os.environ:
        auth_token = os.environ["TWILIO_AUTH_TOKEN"].strip()
    else:
        from dotenv import dotenv_values
        env_vals = dotenv_values(".env") if os.path.exists(".env") else {}
        auth_token = env_vals.get("TWILIO_AUTH_TOKEN", "").strip()
    if not auth_token:
        bad_signature_count += 1
        return Response(content="Forbidden: Auth token not configured", status_code=403)

    public_base_url = get_public_base_url()
    if not public_base_url:
        import logging
        logging.getLogger("voiceguard.server").error("PUBLIC_BASE_URL is empty or not configured; rejecting voice webhook")
        return Response(content="Service Unavailable: PUBLIC_BASE_URL not configured", status_code=503)

    from urllib.parse import parse_qs
    body_bytes = await request.body()
    body_text = body_bytes.decode("utf-8", errors="replace")
    parsed_qs = parse_qs(body_text, keep_blank_values=True)
    params = {k: v[0] if v else "" for k, v in parsed_qs.items()}

    validator = RequestValidator(auth_token)
    webhook_url = f"{public_base_url}/voice"
    if not validator.validate(webhook_url, params, signature):
        bad_signature_count += 1
        return Response(content="Forbidden: Invalid signature", status_code=403)

    call_sid = params.get("CallSid") or f"CA_{os.urandom(16).hex()}"
    token = generate_stream_token(call_sid, auth_token)

    parsed = urlparse(public_base_url)
    host = parsed.netloc or parsed.path
    if "://" in host:
        host = host.split("://", 1)[1]
    host = host.rstrip("/")
    stream_url = f"wss://{host}/twilio-ws"

    twiml = generate_twiml_stream(stream_url, token=token)
    return Response(content=twiml, media_type="application/xml")


@app.websocket("/twilio-ws")
async def twilio_websocket_endpoint(websocket: WebSocket):
    """
    Twilio Media Stream WebSocket receiver.
    Parses media frames, buffers audio, scores windows, and handles action triggers.
    """
    await websocket.accept()
    session: StreamingSession = None
    call_sid = "unknown"
    stream_sid = None
    start_time = None
    frame_count = 0

    try:
        while True:
            text_data = await websocket.receive_text()
            data = json.loads(text_data)
            event_type = data.get("event")

            if event_type == "start":
                start_data = data.get("start", {})
                call_sid = start_data.get("callSid")
                stream_sid = start_data.get("streamSid")
                custom_params = start_data.get("customParameters", {})
                token = custom_params.get("token") or start_data.get("token")

                if not call_sid or call_sid == "unknown":
                    await websocket.close(code=1008)
                    return

                if not stream_sid:
                    await websocket.close(code=1008)
                    return

                if call_sid in active_sessions or stream_sid in active_stream_sids:
                    await websocket.close(code=1008)
                    return

                is_valid, reason = validate_and_consume_stream_token(token, call_sid)
                if not is_valid:
                    await websocket.close(code=1008)
                    return

                active_stream_sids.add(stream_sid)
                start_time = time.time()
                diagnostics_logger.log_lifecycle_event("stream_started", call_sid=call_sid, timestamp=start_time)

                session = StreamingSession(
                    call_sid=call_sid,
                    stream_sid=stream_sid,
                    use_spoof=False,
                    audit_logger=audit_logger
                )
                active_sessions[call_sid] = session
                await websocket.send_text(json.dumps({"event": "connected"}))

            elif event_type == "media":
                if session and not session.terminated:
                    media_data = data.get("media", {})
                    payload = media_data.get("payload", "")
                    session.ingest_twilio_payload(payload)

                    frame_count += 1
                    if frame_count <= 5:
                        import base64
                        decoded_len = (len(base64.b64decode(payload)) * 2) if payload else 0
                        diagnostics_logger.log_frame_stat(
                            call_sid=call_sid,
                            frame_index=frame_count,
                            payload_len=len(payload),
                            decoded_samples=decoded_len,
                            sample_rate=16000,
                            timestamp=time.time()
                        )

                    if session.audio_buffer.total_samples_received >= 32000 and (session.audio_buffer.total_samples_received % 16000 < 640):
                        score_event = session.score_current_window()
                        if score_event:
                            await broadcast_to_dashboard(score_event)

                            trigger = score_event.get("action_trigger")
                            if trigger == "block" or score_event["decision"].startswith("Block"):
                                dispatcher.terminate_call(call_sid, reason="high_risk_impersonation")
                                session.terminated = True
                                await websocket.close()
                                break
                            elif trigger == "step_up" or (score_event["decision"].startswith("Step-Up") and "Awaiting" not in score_event["decision"]):
                                dispatcher.trigger_step_up(call_sid)

            elif event_type == "stop":
                duration = (time.time() - start_time) if start_time else 0.0
                diagnostics_logger.log_lifecycle_event("stream_stopped", call_sid=call_sid, duration_seconds=duration, timestamp=time.time())
                break

    except WebSocketDisconnect:
        pass
    finally:
        duration = (time.time() - start_time) if start_time else 0.0
        diagnostics_logger.log_lifecycle_event("disconnect", call_sid=call_sid, duration_seconds=duration, timestamp=time.time())
        if call_sid in active_sessions:
            del active_sessions[call_sid]
        if stream_sid and stream_sid in active_stream_sids:
            active_stream_sids.remove(stream_sid)


@app.websocket("/dashboard-ws")
async def dashboard_websocket_endpoint(websocket: WebSocket):
    """Dashboard real-time telemetry stream."""
    await websocket.accept()
    dashboard_subscribers.add(websocket)
    try:
        while True:
            # Keepalive / ping
            await websocket.receive_text()
    except WebSocketDisconnect:
        dashboard_subscribers.discard(websocket)


@app.get("/audit")
async def get_audit_records(limit: int = 50):
    """Returns recent audit log records."""
    records = []
    if os.path.exists(audit_logger.log_path):
        with open(audit_logger.log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line.strip()))
    return records[-limit:]


@app.get("/audit/verify")
async def verify_audit_chain():
    """Cryptographically verifies the audit log hash chain."""
    is_valid, err, count = audit_logger.verify_chain()
    return {
        "valid": is_valid,
        "records_verified": count,
        "error": err
    }


@app.get("/demo/scenarios")
async def get_demo_scenarios():
    """Returns allowlisted demo scenarios sourced from manifest.json."""
    return {
        "simulation_label": SIMULATION_LABEL,
        "scenarios": demo_runner.get_scenarios()
    }


@app.post("/demo/run")
async def run_demo_endpoint(request: Request):
    """Starts streaming an allowlisted demo scenario in a background task."""
    try:
        body = await request.json()
    except Exception:
        body = {}

    scenario_id = body.get("scenario_id")
    if not scenario_id or scenario_id not in DEMO_SCENARIOS:
        return JSONResponse(
            status_code=400,
            content={
                "error": f"Invalid or unallowlisted scenario_id: {scenario_id}. Must be one of: {list(DEMO_SCENARIOS.keys())}",
                "simulation_label": SIMULATION_LABEL
            }
        )

    if demo_runner.is_running():
        return JSONResponse(
            status_code=409,
            content={
                "error": "Another demo scenario is already running.",
                "current_scenario": demo_runner.current_scenario_id,
                "simulation_label": SIMULATION_LABEL
            }
        )

    action_sensitivity = body.get("action_sensitivity", "balance_check")
    speed = float(body.get("speed", 1.0))

    try:
        res = await demo_runner.start(
            scenario_id=scenario_id,
            action_sensitivity=action_sensitivity,
            speed=speed
        )
        return res
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Failed to start demo: {str(e)}",
                "simulation_label": SIMULATION_LABEL
            }
        )


@app.post("/demo/stop")
async def stop_demo_endpoint():
    """Cancels currently running demo scenario."""
    res = await demo_runner.stop()
    return res


@app.get("/demo/status")
async def demo_status_endpoint():
    """Returns current demo running status."""
    return {
        "is_running": demo_runner.is_running(),
        "current_scenario": demo_runner.current_scenario_id,
        "current_call_sid": demo_runner.current_call_sid,
        "simulation_label": SIMULATION_LABEL
    }


@app.get("/demo/audio/{scenario_id}")
async def get_demo_audio(scenario_id: str):
    """Serves demo audio file for browser playback from allowlist only."""
    if scenario_id not in DEMO_SCENARIOS:
        return JSONResponse(
            status_code=400,
            content={
                "error": f"Scenario {scenario_id} not in allowlist",
                "simulation_label": SIMULATION_LABEL
            }
        )
    sc = DEMO_SCENARIOS[scenario_id]
    file_path = sc["file_path"]
    if not os.path.exists(file_path):
        return JSONResponse(
            status_code=404,
            content={
                "error": "Audio file not found",
                "simulation_label": SIMULATION_LABEL
            }
        )
    return FileResponse(file_path, media_type="audio/wav")


@app.get("/config/public")
async def get_public_config():
    """
    Returns public operational parameters: speaker map (a, b), band thresholds, and sustained window requirement.
    Contains no secrets or .env values.
    """
    import yaml
    from server.risk_engine import RiskEngine
    engine = RiskEngine(config_path="config/settings.yaml")
    cfg = engine.config
    spk_map = cfg.get("speaker_mapping", {})
    bands = cfg.get("bands", {})
    sustained = cfg.get("sustained_evidence", {})
    return {
        "a": round(float(spk_map.get("a", 0.3364)), 4),
        "b": round(float(spk_map.get("b", 0.4169)), 4),
        "calibration_label": "mapped with a fixed linear map fit on evaluation data, not a calibrated probability",
        "bands": {
            "low_max": float(bands.get("low_max", 0.30)),
            "medium_max": float(bands.get("medium_max", 0.60))
        },
        "sustained_evidence": {
            "consecutive_windows_required": int(sustained.get("consecutive_windows_required", 3))
        }
    }


@app.get("/demo/spectrogram/{scenario_id}")
async def get_demo_spectrogram(scenario_id: str):
    """
    Returns downsampled int8 mel-spectrogram matrix for allowlisted demo clip.
    Contains NO raw audio samples.
    """
    import soundfile as sf
    from scipy.signal import resample_poly
    from server.spectrogram import compute_display_mel_spectrogram

    if scenario_id not in DEMO_SCENARIOS:
        return JSONResponse(
            status_code=400,
            content={
                "error": f"Scenario {scenario_id} not in allowlist",
                "simulation_label": SIMULATION_LABEL
            }
        )
    sc = DEMO_SCENARIOS[scenario_id]
    file_path = sc["file_path"]
    if not os.path.exists(file_path):
        return JSONResponse(
            status_code=404,
            content={
                "error": "Audio file not found",
                "simulation_label": SIMULATION_LABEL
            }
        )
    audio, sr = sf.read(file_path, dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != 16000:
        audio_16k = resample_poly(audio, up=16000, down=sr)
    else:
        audio_16k = audio
    spec = compute_display_mel_spectrogram(audio_16k, 16000)
    spec["scenario_id"] = scenario_id
    spec["simulation_label"] = SIMULATION_LABEL
    return spec



@app.post("/test/broadcast")
async def test_broadcast_endpoint(event: Dict[str, Any]):
    """Test helper to broadcast events to connected dashboard websockets."""
    await broadcast_to_dashboard(event)
    return {"status": "broadcasted"}


@app.post("/analyze/upload")
async def analyze_upload_endpoint(
    file: UploadFile = File(...),
    action_sensitivity: str = Form("balance_check"),
    mode: str = Form("stream"),
    phone_sim: bool = Form(True)
):
    """
    Analyzes uploaded audio file for synthetic deepfakes, replay attacks, and speaker matching.
    Label: "UPLOAD ANALYSIS, not a validated accuracy figure"
    """
    from server.upload import (
        process_audio_upload,
        get_allowed_sensitivities,
        UPLOAD_LABEL,
        _analysis_lock,
        _request_timestamps,
        RATE_LIMIT_PER_MINUTE
    )

    # 1. Action sensitivity validation
    allowed_sensitivities = get_allowed_sensitivities()
    if action_sensitivity not in allowed_sensitivities:
        return JSONResponse(
            status_code=400,
            content={
                "error": f"Invalid action_sensitivity '{action_sensitivity}'. Allowed: {', '.join(allowed_sensitivities)}",
                "simulation_label": UPLOAD_LABEL
            }
        )

    # 2. Mode validation
    if mode not in ("stream", "whole"):
        return JSONResponse(
            status_code=400,
            content={
                "error": f"Invalid mode '{mode}'. Allowed modes: 'stream', 'whole'",
                "simulation_label": UPLOAD_LABEL
            }
        )

    # 3. Rate limiting (10 per minute)
    now = time.time()
    _request_timestamps[:] = [t for t in _request_timestamps if now - t < 60.0]
    if len(_request_timestamps) >= RATE_LIMIT_PER_MINUTE:
        return JSONResponse(
            status_code=429,
            content={
                "error": "Rate limit exceeded. Maximum 10 upload analyses per minute.",
                "simulation_label": UPLOAD_LABEL
            }
        )

    # 4. Concurrency check (single analysis at a time -> 409)
    if _analysis_lock.locked():
        return JSONResponse(
            status_code=409,
            content={
                "error": "Another audio analysis is currently in progress. Please wait.",
                "simulation_label": UPLOAD_LABEL
            }
        )

    # Read uploaded bytes
    file_bytes = await file.read()

    try:
        async with _analysis_lock:
            _request_timestamps.append(now)
            loop = asyncio.get_running_loop()
            res = await loop.run_in_executor(
                None,
                process_audio_upload,
                file_bytes,
                file.filename or "uploaded.wav",
                action_sensitivity,
                mode,
                phone_sim
            )
            return res
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={
                "error": str(e),
                "simulation_label": UPLOAD_LABEL
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Audio processing error: {str(e)}",
                "simulation_label": UPLOAD_LABEL
            }
        )


@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serves the security monitoring dashboard HTML."""
    html_path = "dashboard/index.html"
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>VoiceGuard Gateway Running</h1><p>Dashboard UI at /dashboard</p>"
