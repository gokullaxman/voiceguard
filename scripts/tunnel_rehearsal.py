"""
VoiceGuard Tunnel Rehearsal Script (Step 4).
Label: "TUNNEL TEST, simulated Twilio client, not a live call"

Validates the full telephony and streaming pipeline through the public tunnel:
1. Correctly signed POST to {PUBLIC_BASE_URL}/voice -> 200 + TwiML with wss:// and stream token.
2. wss:// streaming of data/phone_simulated/live_05_sim.wav to /twilio-ws, printing per-window
   band and decision, and confirming the dashboard-ws receives the same windows.
3. Wrong signature POST -> 403 Forbidden through the tunnel.
4. Verify data/audit/live_windows.jsonl logged scores-only lines for this Call SID,
   and execute scripts/summarize_live_call.py.
"""

import os
import sys
import time
import json
import base64
import re
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Optional, Dict, Any, List

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
import asyncio
import websockets
from twilio.request_validator import RequestValidator
from dotenv import dotenv_values

from server.telephony import encode_pcm_to_ulaw
from scripts.summarize_live_call import summarize_call

DEFAULT_AUDIO = Path("data/phone_simulated/live_05_sim.wav")
AUDIT_LOG_PATH = Path("data/audit/live_windows.jsonl")


def load_audio_frames(audio_path: Path) -> List[str]:
    """Loads audio, resamples to 8kHz, converts to G.711 mu-law 20ms frames, base64 encodes."""
    audio, sr = sf.read(str(audio_path), dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    if sr != 8000:
        audio_8k = resample_poly(audio, up=1, down=sr // 8000)
    else:
        audio_8k = audio

    pcm_8k = np.clip(audio_8k * 32767.0, -32768, 32767).astype(np.int16)
    frame_samples = 160  # 20ms at 8kHz

    frames = []
    for i in range(0, len(pcm_8k) - frame_samples + 1, frame_samples):
        chunk = pcm_8k[i:i + frame_samples]
        ulaw_bytes = encode_pcm_to_ulaw(chunk)
        b64 = base64.b64encode(ulaw_bytes).decode("ascii")
        frames.append(b64)
    return frames


async def stream_audio_and_listen_dashboard(
    twilio_ws_url: str,
    dashboard_ws_url: str,
    call_sid: str,
    stream_sid: str,
    stream_token: str,
    frames: List[str]
) -> Dict[str, Any]:
    """Connects to dashboard-ws and twilio-ws, streams frames, collects scored windows."""
    dashboard_windows = []
    stream_events = []

    headers = {"ngrok-skip-browser-warning": "true"}

    async def dashboard_listener():
        try:
            async with websockets.connect(
                dashboard_ws_url,
                additional_headers=headers,
                close_timeout=5
            ) as ws:
                while True:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=12.0)
                        if isinstance(msg, str):
                            data = json.loads(msg)
                            if data.get("call_sid") == call_sid:
                                dashboard_windows.append(data)
                    except asyncio.TimeoutError:
                        break
                    except Exception:
                        break
        except Exception as e:
            print(f"Dashboard listener error: {e}")

    async def twilio_streamer():
        # Brief pause to let dashboard subscriber connect first
        await asyncio.sleep(0.5)
        try:
            async with websockets.connect(
                twilio_ws_url,
                additional_headers=headers,
                close_timeout=5
            ) as ws:
                # 1. Send start
                start_msg = {
                    "event": "start",
                    "start": {
                        "callSid": call_sid,
                        "streamSid": stream_sid,
                        "customParameters": {
                            "token": stream_token
                        }
                    }
                }
                await ws.send(json.dumps(start_msg))

                # Wait for connected ack
                ack = await asyncio.wait_for(ws.recv(), timeout=5.0)
                stream_events.append(ack)

                # 2. Stream audio frames
                for idx, payload in enumerate(frames):
                    media_msg = {
                        "event": "media",
                        "streamSid": stream_sid,
                        "media": {
                            "payload": payload
                        }
                    }
                    await ws.send(json.dumps(media_msg))
                    await asyncio.sleep(0.015)  # 15ms pace per 20ms frame

                # Wait a moment for final scoring to complete
                await asyncio.sleep(1.5)

                # 3. Send stop
                stop_msg = {
                    "event": "stop",
                    "streamSid": stream_sid
                }
                await ws.send(json.dumps(stop_msg))
                await asyncio.sleep(0.5)
        except Exception as e:
            print(f"Twilio streamer error: {e}")

    # Run streamer and dashboard listener concurrently
    listener_task = asyncio.create_task(dashboard_listener())
    await twilio_streamer()
    await listener_task

    return {
        "dashboard_windows": dashboard_windows,
        "stream_events": stream_events
    }


def run_tunnel_rehearsal():
    print("=" * 80)
    print("TUNNEL TEST, simulated Twilio client, not a live call")
    print("=" * 80)

    # 0. Check PUBLIC_BASE_URL and auth token
    env_vals = dotenv_values(".env") if os.path.exists(".env") else {}
    public_base_url = env_vals.get("PUBLIC_BASE_URL", os.getenv("PUBLIC_BASE_URL", "")).strip().rstrip("/")
    auth_token = env_vals.get("TWILIO_AUTH_TOKEN", os.getenv("TWILIO_AUTH_TOKEN", "")).strip()

    if not public_base_url or "xxxxxxxx" in public_base_url.lower():
        print("SKIPPED: PUBLIC_BASE_URL is empty or placeholder in .env")
        return False

    if not auth_token or auth_token == "rehearsal_auth_token_32_bytes_ok":
        print("SKIPPED: real TWILIO_AUTH_TOKEN required")
        return False

    # Check if tunnel is reachable
    try:
        health_req = urllib.request.Request(
            f"{public_base_url}/health",
            headers={"ngrok-skip-browser-warning": "true"}
        )
        with urllib.request.urlopen(health_req, timeout=5) as resp:
            if resp.status != 200:
                print(f"SKIPPED: Tunnel health check returned HTTP {resp.status}")
                return False
    except Exception as e:
        print(f"SKIPPED: Tunnel unreachable at {public_base_url}: {e}")
        return False

    test_passed = [False, False, False, False]
    call_sid = f"CA_rehearsal_{int(time.time())}"
    stream_sid = f"MZ_{int(time.time())}"

    # -------------------------------------------------------------------------
    # TEST 1: Signed POST to {PUBLIC_BASE_URL}/voice
    # -------------------------------------------------------------------------
    print("\n--- TEST 1: Signed Webhook POST to /voice ---")
    webhook_url = f"{public_base_url}/voice"
    form_params = {
        "CallSid": call_sid,
        "From": "+15550001",
        "To": "+15550002"
    }
    validator = RequestValidator(auth_token)
    signature = validator.compute_signature(webhook_url, form_params)

    body_bytes = urllib.parse.urlencode(form_params).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=body_bytes,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "x-twilio-signature": signature,
            "ngrok-skip-browser-warning": "true"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status_code = resp.status
            content = resp.read().decode("utf-8")

        print(f"Response status: {status_code}")
        token_match = re.search(r'<Parameter name="token" value="([^"]+)"', content)
        has_wss = "wss://" in content
        stream_token = token_match.group(1) if token_match else None

        if status_code == 200 and has_wss and stream_token:
            print("TwiML verification: PASS (contains wss:// stream URL and valid token)")
            test_passed[0] = True
        else:
            print(f"TwiML verification: FAIL (status={status_code}, has_wss={has_wss}, has_token={bool(stream_token)})")
    except Exception as e:
        print(f"Test 1 failed with exception: {e}")
        return False

    # -------------------------------------------------------------------------
    # TEST 2: Stream audio over wss:// and confirm dashboard windows
    # -------------------------------------------------------------------------
    print("\n--- TEST 2: WebSocket Streaming & Window Scoring ---")
    parsed = urllib.parse.urlparse(public_base_url)
    host = parsed.netloc or parsed.path
    if "://" in host:
        host = host.split("://", 1)[1]
    host = host.rstrip("/")

    twilio_ws_url = f"wss://{host}/twilio-ws"
    dashboard_ws_url = f"wss://{host}/dashboard-ws"

    frames = load_audio_frames(DEFAULT_AUDIO)
    print(f"Loaded {len(frames)} 20ms frames from {DEFAULT_AUDIO}")

    results = asyncio.run(
        stream_audio_and_listen_dashboard(
            twilio_ws_url=twilio_ws_url,
            dashboard_ws_url=dashboard_ws_url,
            call_sid=call_sid,
            stream_sid=stream_sid,
            stream_token=stream_token,
            frames=frames
        )
    )

    dash_windows = results.get("dashboard_windows", [])
    print(f"Dashboard-ws received {len(dash_windows)} window score event(s):")
    for w in dash_windows:
        w_idx = w.get("window", w.get("window_index"))
        band = w.get("band", w.get("risk_band"))
        decision = w.get("decision")
        risk = w.get("risk", w.get("risk_score"))
        scores = w.get("detector_scores", {})
        speaker = scores.get("speaker_sim", w.get("speaker_sim"))
        replay = scores.get("replay_prob", w.get("replay_prob"))
        risk_str = f"{risk:.4f}" if isinstance(risk, (int, float)) else str(risk)
        speaker_str = f"{speaker:.4f}" if isinstance(speaker, (int, float)) else str(speaker)
        replay_str = f"{replay:.4f}" if isinstance(replay, (int, float)) else str(replay)
        print(f"  Window {w_idx}: band={band}, decision={decision}, risk={risk_str}, speaker_sim={speaker_str}, replay_prob={replay_str}")

    if len(dash_windows) >= 1:
        print("WebSocket streaming & dashboard broadcast: PASS")
        test_passed[1] = True
    else:
        print("WebSocket streaming & dashboard broadcast: FAIL (0 windows received on dashboard)")

    # -------------------------------------------------------------------------
    # TEST 3: Wrong signature gets 403 Forbidden
    # -------------------------------------------------------------------------
    print("\n--- TEST 3: Invalid Signature Rejection ---")
    bad_req = urllib.request.Request(
        webhook_url,
        data=body_bytes,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "x-twilio-signature": "invalid_wrong_signature_12345",
            "ngrok-skip-browser-warning": "true"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(bad_req, timeout=10) as resp:
            bad_status = resp.status
    except urllib.error.HTTPError as e:
        bad_status = e.code
    except Exception as e:
        bad_status = -1
        print(f"Unexpected error: {e}")

    print(f"Wrong signature HTTP status: {bad_status}")
    if bad_status == 403:
        print("Invalid signature rejection: PASS (HTTP 403 returned)")
        test_passed[2] = True
    else:
        print(f"Invalid signature rejection: FAIL (expected 403, got {bad_status})")

    # -------------------------------------------------------------------------
    # TEST 4: Audit log verification & summarize_live_call.py
    # -------------------------------------------------------------------------
    print("\n--- TEST 4: Audit Log Verification & Call Summary ---")
    audit_lines = []
    if AUDIT_LOG_PATH.exists():
        with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if call_sid in line:
                    try:
                        audit_lines.append(json.loads(line))
                    except Exception:
                        pass

    score_lines = [l for l in audit_lines if l.get("event") == "window_score"]
    print(f"Found {len(score_lines)} scores-only window record(s) in {AUDIT_LOG_PATH} for {call_sid}")

    # Check for secret leaks or raw audio in logged records
    no_leaks = True
    for l in audit_lines:
        s = json.dumps(l)
        if "audio" in s or "base64" in s or auth_token in s:
            no_leaks = False

    if score_lines and no_leaks:
        print("Audit logging verification: PASS (scores-only recorded, no secrets or raw audio)")
        test_passed[3] = True
    else:
        print(f"Audit logging verification: FAIL (score_lines={len(score_lines)}, no_leaks={no_leaks})")

    print("\n--- Executing summarize_live_call.py ---")
    summary = summarize_call(call_sid, log_path=AUDIT_LOG_PATH)
    if summary:
        print(f"Call summary generated successfully:")
        print(f"  Call SID: {call_sid}")
        print(f"  Total Windows: {summary.get('windows_count')}")
        print(f"  Band Counts: {summary.get('band_counts')}")
        print(f"  Primary Driver: {summary.get('driver')}")
        print(f"  Safety Actions: {summary.get('actions')}")

    # Final gate determination
    all_passed = all(test_passed)
    print("\n" + "=" * 80)
    print(f"TUNNEL REHEARSAL GATE: {'PASS' if all_passed else 'FAIL'}")
    print(f"Sub-checks: Test1={test_passed[0]}, Test2={test_passed[1]}, Test3={test_passed[2]}, Test4={test_passed[3]}")
    print("=" * 80)
    return all_passed


if __name__ == "__main__":
    success = run_tunnel_rehearsal()
    sys.exit(0 if success else 1)
