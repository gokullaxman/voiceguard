"""
VoiceGuard GoLive Tunnel Helper Script (Step 2).
Queries local ngrok API (http://127.0.0.1:4040/api/tunnels) for the active HTTPS tunnel.
Updates PUBLIC_BASE_URL in .env without a trailing slash, preserving all other lines and keys.
Outputs the exact webhook URL to paste into Twilio.
Optionally updates Twilio incoming phone number configuration when --set-webhook is passed.
Never prints or logs secrets, credentials, or phone numbers.
"""

import os
import sys
import json
import argparse
import urllib.request
from pathlib import Path
from typing import Optional, Any

NGROK_API_URL = "http://127.0.0.1:4040/api/tunnels"
DEFAULT_ENV_PATH = Path(".env")


def get_active_ngrok_url(api_url: str = NGROK_API_URL) -> Optional[str]:
    """Queries ngrok local API for the active HTTPS tunnel URL."""
    try:
        req = urllib.request.Request(api_url, headers={"User-Agent": "VoiceGuard-GoLive"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            tunnels = data.get("tunnels", [])
            # Prioritize HTTPS tunnel
            for t in tunnels:
                if t.get("proto") == "https":
                    url = t.get("public_url", "").strip().rstrip("/")
                    if url:
                        return url
            # Fallback to any available tunnel with a public_url
            for t in tunnels:
                url = t.get("public_url", "").strip().rstrip("/")
                if url:
                    return url
    except Exception:
        return None
    return None


def validate_twilio_credentials(
    account_sid: str,
    auth_token: str,
    phone_number: str
) -> tuple[bool, str]:
    """Validates Twilio credential formats and checks for placeholder/test values."""
    if not account_sid:
        return False, "TWILIO_ACCOUNT_SID is missing in .env"
    if not account_sid.startswith("AC"):
        return False, "TWILIO_ACCOUNT_SID does not start with AC"
    if "xxxx" in account_sid.lower():
        return False, "TWILIO_ACCOUNT_SID contains placeholder characters"
    if len(account_sid) != 34 or not all(c in "0123456789abcdefABCDEF" for c in account_sid[2:]):
        return False, "TWILIO_ACCOUNT_SID must be AC followed by 32 hex characters"

    if not auth_token:
        return False, "TWILIO_AUTH_TOKEN is missing in .env"
    if auth_token == "rehearsal_auth_token_32_bytes_ok":
        return False, "TWILIO_AUTH_TOKEN is the rehearsal test value"
    if "your_" in auth_token.lower() or "xxxx" in auth_token.lower() or len(auth_token) < 16:
        return False, "TWILIO_AUTH_TOKEN is placeholder or invalid length"

    if not phone_number:
        return False, "TWILIO_PHONE_NUMBER is missing in .env"
    if not phone_number.startswith("+") or not phone_number[1:].isdigit():
        return False, "TWILIO_PHONE_NUMBER must be in E.164 format starting with + and digits"

    return True, "valid"


def update_env_file(new_url: str, env_path: Path = DEFAULT_ENV_PATH) -> bool:
    """Writes PUBLIC_BASE_URL into .env without trailing slash; preserves all other lines byte-for-byte."""
    clean_url = new_url.strip().rstrip("/")
    if not env_path.exists():
        env_path.write_bytes(f"PUBLIC_BASE_URL={clean_url}\n".encode("utf-8"))
        return True

    raw_bytes = env_path.read_bytes()
    crlf = b"\r\n" in raw_bytes
    nl = b"\r\n" if crlf else b"\n"

    # Split preserving trailing newline structure
    has_trailing_nl = raw_bytes.endswith(nl)
    lines = raw_bytes.split(nl)
    if has_trailing_nl and lines and lines[-1] == b"":
        lines = lines[:-1]

    found = False
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(b"PUBLIC_BASE_URL=") or stripped.startswith(b"PUBLIC_BASE_URL ="):
            new_lines.append(f"PUBLIC_BASE_URL={clean_url}".encode("utf-8"))
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"PUBLIC_BASE_URL={clean_url}".encode("utf-8"))

    result_bytes = nl.join(new_lines)
    if has_trailing_nl:
        result_bytes += nl

    env_path.write_bytes(result_bytes)
    return True


def update_twilio_webhook(
    public_base_url: str,
    env_path: Path = DEFAULT_ENV_PATH,
    twilio_client: Optional[Any] = None
) -> bool:
    """Updates the voice_url of TWILIO_PHONE_NUMBER using Twilio REST client."""
    from dotenv import dotenv_values
    env_vals = dotenv_values(env_path) if env_path.exists() else {}
    account_sid = env_vals.get("TWILIO_ACCOUNT_SID", os.getenv("TWILIO_ACCOUNT_SID", "")).strip()
    auth_token = env_vals.get("TWILIO_AUTH_TOKEN", os.getenv("TWILIO_AUTH_TOKEN", "")).strip()
    phone_number = env_vals.get("TWILIO_PHONE_NUMBER", os.getenv("TWILIO_PHONE_NUMBER", "")).strip()

    webhook_url = f"{public_base_url.rstrip('/')}/voice"

    if twilio_client is None:
        is_valid, reason = validate_twilio_credentials(account_sid, auth_token, phone_number)
        if not is_valid:
            print(f"Twilio webhook update: FAILED ({reason})")
            return False
        try:
            from twilio.rest import Client
            twilio_client = Client(account_sid, auth_token)
        except Exception:
            print("Twilio webhook update: FAILED (client initialization error)")
            return False

    try:
        numbers = twilio_client.incoming_phone_numbers.list(phone_number=phone_number)
        if not numbers:
            print("Twilio webhook update: FAILED (phone number not found on account)")
            return False
        sid = numbers[0].sid
        twilio_client.incoming_phone_numbers(sid).update(voice_url=webhook_url, voice_method="POST")
        print("Twilio webhook update: SUCCESS")
        return True
    except Exception as e:
        print("Twilio webhook update: FAILED (Twilio REST API error)")
        return False


def main():
    parser = argparse.ArgumentParser(description="VoiceGuard GoLive Tunnel Setup")
    parser.add_argument("--set-webhook", action="store_true", help="Automatically configure webhook on Twilio number")
    parser.add_argument("--api-url", default=NGROK_API_URL, help="ngrok local API URL")
    parser.add_argument("--env-file", default=str(DEFAULT_ENV_PATH), help="Path to .env file")
    args = parser.parse_args()

    env_path = Path(args.env_file)
    active_url = get_active_ngrok_url(args.api_url)

    if not active_url:
        print("ngrok not running: start it with: ngrok http 8000")
        sys.exit(1)

    # 1. Write PUBLIC_BASE_URL into .env without trailing slash
    update_env_file(active_url, env_path=env_path)

    # 2. Print the new URL and the exact webhook URL
    print(f"Active public tunnel URL: {active_url}")
    print(f"Webhook URL to paste into Twilio: {active_url}/voice, method POST")
    print("Server dynamically re-reads PUBLIC_BASE_URL on incoming requests; restart is not required.")

    # 3. Optional --set-webhook
    if args.set_webhook:
        update_twilio_webhook(active_url, env_path=env_path)


if __name__ == "__main__":
    main()
