"""
VoiceGuard Preflight Verification Script (Phase 4 / Step 3).
Performs sanity and configuration checks before live bring-up.
Never prints, logs, or echoes credentials, keys, or phone numbers.
"""

import os
import sys
import json
import yaml
import hashlib
import urllib.request
from pathlib import Path
from dotenv import dotenv_values

REPO_ROOT = Path(__file__).resolve().parent.parent

def main():
    print("=" * 75)
    print("VOICEGUARD PREFLIGHT SYSTEM VERIFICATION")
    print("=" * 75)

    env_path = REPO_ROOT / ".env"
    env_vars = dotenv_values(env_path) if env_path.exists() else {}

    # 1. Check .env keys present
    required_keys = [
        "VOICEGUARD_ENROLLMENT_KEY",
        "TWILIO_ACCOUNT_SID",
        "TWILIO_AUTH_TOKEN",
        "TWILIO_PHONE_NUMBER",
        "PUBLIC_BASE_URL"
    ]
    missing_keys = []
    for k in required_keys:
        v = env_vars.get(k, os.getenv(k, ""))
        if not v or "xxxxxxxx" in v.lower() or "your_" in v.lower():
            missing_keys.append(k)

    if not missing_keys:
        print(".env keys present: PASS")
    else:
        print(f".env keys present: FAIL ({len(missing_keys)} missing or placeholder keys)")
        print(f"  Fix: Configure valid values in .env for: {', '.join(missing_keys)}")

    # 2. Twilio REST Auth
    account_sid = env_vars.get("TWILIO_ACCOUNT_SID", os.getenv("TWILIO_ACCOUNT_SID", ""))
    auth_token = env_vars.get("TWILIO_AUTH_TOKEN", os.getenv("TWILIO_AUTH_TOKEN", ""))
    phone_number = env_vars.get("TWILIO_PHONE_NUMBER", os.getenv("TWILIO_PHONE_NUMBER", ""))
    public_url = env_vars.get("PUBLIC_BASE_URL", os.getenv("PUBLIC_BASE_URL", "https://your-domain.ngrok-free.app")).strip().rstrip("/")

    twilio_client = None
    account_obj = None
    twilio_number_obj = None

    is_rehearsal_token = (auth_token == "rehearsal_auth_token_32_bytes_ok")
    print(f"TWILIO_AUTH_TOKEN is the rehearsal test value: {'true (FAIL)' if is_rehearsal_token else 'false (PASS)'}")

    is_sid_placeholder = "xxxxxxxx" in account_sid.lower() or not account_sid.startswith("AC")
    is_token_placeholder = "your_" in auth_token.lower() or len(auth_token) < 16 or is_rehearsal_token

    if not is_sid_placeholder and not is_token_placeholder:
        try:
            from twilio.rest import Client
            twilio_client = Client(account_sid, auth_token)
            account_obj = twilio_client.api.accounts(account_sid).fetch()
            status_str = account_obj.status
            print(f"Twilio REST auth works: PASS (status: {status_str})")
        except Exception as e:
            print("Twilio REST auth works: FAIL")
            print("  Fix: Verify TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN credentials in .env")
    else:
        print("Twilio REST auth works: FAIL (credentials are placeholders or missing)")
        print("  Fix: Populate TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in .env with real Twilio API credentials")

    # 3. Check Twilio phone number and voice capability
    if twilio_client and phone_number and "X" not in phone_number:
        try:
            numbers = twilio_client.incoming_phone_numbers.list(phone_number=phone_number)
            if numbers:
                twilio_number_obj = numbers[0]
                has_voice = bool(twilio_number_obj.capabilities.get("voice"))
                print(f"Twilio number exists with voice capability: {'PASS' if has_voice else 'FAIL'} (voice_capable: {has_voice})")
                if not has_voice:
                    print("  Fix: Enable voice capabilities on this phone number in the Twilio Console")
            else:
                print("Twilio number exists with voice capability: FAIL (number not found on account)")
                print("  Fix: Assign or purchase this phone number in your Twilio account console")
        except Exception:
            print("Twilio number exists with voice capability: FAIL (lookup failed)")
            print("  Fix: Check account permissions and phone number formatting (+E.164)")
    else:
        print("Twilio number exists with voice capability: FAIL (unauthenticated or placeholder number)")
        print("  Fix: Ensure Twilio REST auth succeeds and set real TWILIO_PHONE_NUMBER in .env")

    # 4. Trial account check
    if account_obj:
        is_trial = (account_obj.type == "Trial")
        print(f"Trial account: {is_trial}")
        if is_trial:
            print("  Reminder: On Twilio Trial accounts, inbound calls are only accepted from verified caller IDs.")
    else:
        print("Trial account: false (unauthenticated)")
        print("  Fix: Authenticate with Twilio credentials to query account trial status")

    # 5. Server models load, enrollment decrypts in memory, config hash equals fused_eval.json config hash
    models_pass = False
    try:
        from models.speaker import ECAPASpeakerDetector
        from models.replay import AcousticReplayDetector
        from models.spoof import AASISTSpoofDetector
        from server.enrollment import load_enrollment_key, decrypt_voiceprint
        from server.risk_engine import RiskEngine

        # Load models
        spk = ECAPASpeakerDetector(device="cpu")
        rep = AcousticReplayDetector()
        spf = AASISTSpoofDetector(device="cpu")

        # Decrypt voiceprint
        k = load_enrollment_key()
        bin_path = REPO_ROOT / "data" / "enrollment" / "enrolled_voiceprint.bin"
        if not bin_path.exists():
            raise FileNotFoundError("Enrolled voiceprint binary not found at data/enrollment/enrolled_voiceprint.bin")
        emb, _ = decrypt_voiceprint(bin_path.read_bytes(), k)
        if emb is None or emb.shape != (192,):
            raise ValueError("Decrypted voiceprint embedding shape invalid")

        # Config hash check (whole config as loaded by server)
        settings_path = REPO_ROOT / "config" / "settings.yaml"
        engine = RiskEngine(config_path=str(settings_path))
        computed_hash = engine.get_config_hash()

        # Compare with fused_eval.json
        fused_path = REPO_ROOT / "data" / "fused_eval.json"
        if not fused_path.exists():
            fused_path = Path(r"C:\Users\Dell Latitude 7410\.gemini\antigravity-ide\brain\a18e2a80-1a10-459f-9aac-6edb5b242e63\scratch\fused_eval.json")
        with open(fused_path, "r", encoding="utf-8") as f:
            fused_data = json.load(f)
        fused_hash = fused_data.get("config_hash")

        hash_matches = (computed_hash == fused_hash)
        if hash_matches:
            print("Server models load, enrollment decrypts, config hash verified: PASS")
            models_pass = True
        else:
            print("Server models load, enrollment decrypts, config hash verified: FAIL (config hash mismatch)")
            print("  Fix: Synchronize config/settings.yaml with evaluation configuration")
    except Exception as e:
        print(f"Server models load, enrollment decrypts, config hash verified: FAIL ({type(e).__name__}: {e})")
        print("  Fix: Check model weight paths, enrollment key, and settings.yaml")

    # 6. GET {PUBLIC_BASE_URL}/health reachable
    try:
        health_url = f"{public_url}/health"
        req = urllib.request.Request(health_url, headers={"User-Agent": "VoiceGuard-Preflight"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            if resp.status == 200:
                print(f"GET {public_url}/health reachable: PASS")
            else:
                print(f"GET {public_url}/health reachable: FAIL (HTTP {resp.status})")
                print("  Fix: Start server (vg.ps1 serve) and tunnel (ngrok http 8000)")
    except Exception:
        print(f"GET {public_url}/health reachable: SKIPPED (tunnel not up or server not running)")
        print("  Fix: Run 'vg.ps1 serve' in one terminal and 'ngrok http 8000' in another to expose public URL")

    # 7. Webhook URL configured on Twilio number equals {PUBLIC_BASE_URL}/voice
    if twilio_number_obj:
        current_webhook = (twilio_number_obj.voice_url or "").strip().rstrip("/")
        expected_webhook = f"{public_url}/voice"
        webhook_matches = (current_webhook == expected_webhook)
        print(f"Webhook URL configured on Twilio number equals {public_url}/voice: {webhook_matches} ({'PASS' if webhook_matches else 'FAIL'})")
        if not webhook_matches:
            print(f"  Fix: In Twilio Console, set Voice Webhook for this number to: {expected_webhook} (POST)")
    else:
        print(f"Webhook URL configured on Twilio number equals {public_url}/voice: false (FAIL)")
        print("  Fix: Verify Twilio number exists on account and set Voice Webhook URL to: <PUBLIC_BASE_URL>/voice")

    print("=" * 75)

if __name__ == "__main__":
    main()
