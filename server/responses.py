"""
VoiceGuard Twilio Responses and Action Dispatcher (Phase 4).
Handles TwiML generation, DTMF OTP step-up challenge flows,
and call termination via Twilio REST API with mock fallback.
Never prints or logs API credentials.
"""

import os
import hmac
import hashlib
import time
from typing import Dict, Any, Optional

# In-memory registry of short-lived tokens for media stream handshakes
# Format: token -> {"call_sid": str, "created_at": float, "ttl": int, "used": bool}
stream_tokens_registry: Dict[str, Dict[str, Any]] = {}


def generate_stream_token(call_sid: str, secret: Optional[str] = None, ttl: int = 120) -> str:
    """Generates a cryptographic HMAC-SHA256 short-lived token tied to call_sid."""
    sec = (secret or os.getenv("TWILIO_AUTH_TOKEN") or "default_voiceguard_stream_secret").encode("utf-8")
    ts = int(time.time())
    nonce = os.urandom(8).hex()
    msg = f"{call_sid}:{ts}:{nonce}".encode("utf-8")
    sig = hmac.new(sec, msg, hashlib.sha256).hexdigest()
    token = f"{ts}.{nonce}.{sig}"
    stream_tokens_registry[token] = {
        "call_sid": call_sid,
        "created_at": ts,
        "ttl": ttl,
        "used": False
    }
    return token


def validate_and_consume_stream_token(token: str, call_sid: str, secret: Optional[str] = None) -> tuple[bool, str]:
    """
    Validates token:
    - Must exist in stream_tokens_registry
    - Must match call_sid
    - Must not be expired
    - Must not be replayed (already used)
    Returns (is_valid, reason).
    """
    if not token or token not in stream_tokens_registry:
        return False, "unknown_or_missing_token"

    entry = stream_tokens_registry[token]
    if entry["used"]:
        return False, "token_replayed"

    if entry["call_sid"] != call_sid:
        return False, "call_sid_mismatch"

    now = time.time()
    if now - entry["created_at"] > entry.get("ttl", 120):
        return False, "token_expired"

    entry["used"] = True
    return True, "valid"


def generate_twiml_stream(stream_url: str, token: Optional[str] = None) -> str:
    """Generates TwiML connecting the call to the WebSocket media stream."""
    # Enforce wss://, never ws://
    if stream_url.startswith("ws://"):
        stream_url = "wss://" + stream_url[len("ws://"):]
    elif not stream_url.startswith("wss://"):
        stream_url = "wss://" + stream_url.lstrip("http://").lstrip("https://").lstrip("/")

    token_param = f'        <Parameter name="token" value="{token}" />\n' if token else ""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Thank you for calling. Your call is screened by VoiceGuard for security.</Say>
    <Connect>
        <Stream url="{stream_url}">
{token_param}        </Stream>
    </Connect>
</Response>"""


def generate_twiml_otp_challenge() -> str:
    """Generates TwiML prompting the caller for a DTMF OTP code."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Gather numDigits="4" timeout="10" action="/voice/otp-verify" method="POST">
        <Say>Security check. Please enter the four-digit one-time passcode sent to your device.</Say>
    </Gather>
    <Say>We did not receive your input. Disconnecting for security.</Say>
    <Hangup/>
</Response>"""


def generate_twiml_terminate(reason: str = "security") -> str:
    """Generates TwiML cleanly terminating the call upon high risk detection."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Call rejected by VoiceGuard security due to suspected voice impersonation.</Say>
    <Hangup/>
</Response>"""


class TwilioActionDispatcher:
    """
    Interface for dispatching actions (continue, step-up, terminate) to Twilio.
    Supports dry mode (live.dry_mode) and idempotent execution.
    Never prints or logs credentials.
    """
    def __init__(self, dry_mode: Optional[bool] = None, twilio_client: Any = None):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.mock_actions: list = []
        self._sent_actions: set = set()

        if dry_mode is not None:
            self.dry_mode = dry_mode
        else:
            env_dry = os.getenv("LIVE_DRY_MODE")
            if env_dry is not None:
                self.dry_mode = env_dry.strip().lower() in ("true", "1", "yes")
            else:
                self.dry_mode = self._load_dry_mode_from_config()

        self.twilio_client = twilio_client
        if not self.dry_mode and self.twilio_client is None and self.account_sid and self.auth_token:
            try:
                from twilio.rest import Client
                self.twilio_client = Client(self.account_sid, self.auth_token)
            except Exception:
                self.twilio_client = None

    def _load_dry_mode_from_config(self) -> bool:
        try:
            import yaml
            for path in ("config/live.yaml", "config/settings.yaml"):
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        cfg = yaml.safe_load(f) or {}
                    if "live" in cfg and "dry_mode" in cfg["live"]:
                        return bool(cfg["live"]["dry_mode"])
        except Exception:
            pass
        return True

    def trigger_step_up(self, call_sid: str) -> Dict[str, Any]:
        action_key = (call_sid, "step_up_otp")
        if self.dry_mode:
            import logging
            logging.getLogger("voiceguard.responses").info(f"[DRY MODE] trigger_step_up for {call_sid} logged only; not sent to Twilio.")
            action_record = {"action": "step_up_otp", "call_sid": call_sid, "status": "dry_mode_logged", "sent": False}
            self.mock_actions.append(action_record)
            return action_record

        if action_key in self._sent_actions:
            return {"action": "step_up_otp", "call_sid": call_sid, "status": "already_sent", "sent": False}
        self._sent_actions.add(action_key)

        action_record = {"action": "step_up_otp", "call_sid": call_sid, "status": "initiated", "sent": True}
        if self.twilio_client is not None:
            try:
                self.twilio_client.calls(call_sid).update(twiml=generate_twiml_otp_challenge())
            except Exception as e:
                import logging
                logging.getLogger("voiceguard.responses").error(f"Failed to dispatch step-up: {e}")
        self.mock_actions.append(action_record)
        return action_record

    def terminate_call(self, call_sid: str, reason: str = "high_risk_impersonation") -> Dict[str, Any]:
        action_key = (call_sid, "terminate_call")
        if self.dry_mode:
            import logging
            logging.getLogger("voiceguard.responses").info(f"[DRY MODE] terminate_call ({reason}) for {call_sid} logged only; not sent to Twilio.")
            action_record = {"action": "terminate_call", "call_sid": call_sid, "reason": reason, "status": "dry_mode_logged", "sent": False}
            self.mock_actions.append(action_record)
            return action_record

        if action_key in self._sent_actions:
            return {"action": "terminate_call", "call_sid": call_sid, "reason": reason, "status": "already_sent", "sent": False}
        self._sent_actions.add(action_key)

        action_record = {"action": "terminate_call", "call_sid": call_sid, "reason": reason, "status": "completed", "sent": True}
        if self.twilio_client is not None:
            try:
                self.twilio_client.calls(call_sid).update(status="completed")
            except Exception as e:
                import logging
                logging.getLogger("voiceguard.responses").error(f"Failed to dispatch terminate: {e}")
        self.mock_actions.append(action_record)
        return action_record
