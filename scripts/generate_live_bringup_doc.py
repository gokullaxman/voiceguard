"""
Script to generate docs/LIVE_BRINGUP.md (Phase 4 / Step 5).
Generates comprehensive runbook for live telephony bring-up.
"""

from pathlib import Path

def generate_runbook():
    doc_path = Path("docs/LIVE_BRINGUP.md")
    doc_path.parent.mkdir(parents=True, exist_ok=True)

    content = """# VoiceGuard Live Telephony Bring-Up Runbook

This runbook provides end-to-end operational instructions for bringing the VoiceGuard real-time telephony security gateway online with live Twilio media streams.

---

## 1. Prerequisites and Environment Setup

Ensure all dependencies, virtual environments, and configuration placeholders are initialized:

```powershell
# Open PowerShell in the project root
cd "C:\\Users\\Dell Latitude 7410\\Downloads\\expo"

# 1. Sync environment and dependencies
.\\scripts\\vg.ps1 setup

# 2. Verify all automated tests pass before live connection
.\\scripts\\vg.ps1 test
```

---

## 2. Server and Tunnel Bring-Up

VoiceGuard requires an exposed public HTTPS/WSS endpoint so Twilio can send incoming voice webhooks and establish bidirectional WebSockets.

### Step 2.1: Start the VoiceGuard Telephony Gateway
In **Terminal 1**, launch the Uvicorn server:
```powershell
.\\scripts\\vg.ps1 serve
```
*The gateway will listen on `http://0.0.0.0:8000` with WebSockets active at `/twilio-ws` and `/dashboard-ws`.*

### Step 2.2: Establish the Public Tunnel
In **Terminal 2**, start an ngrok or Cloudflare tunnel pointing to port 8000:
```powershell
# Using ngrok:
ngrok http 8000

# OR using Cloudflare Tunnel:
cloudflared tunnel --url http://localhost:8000
```
Note the assigned public HTTPS URL (e.g., `https://your-domain.ngrok-free.app`).

### Step 2.3: Update Configuration (.env)
Update `.env` with the assigned public URL and Twilio credentials (do not commit `.env`):
```powershell
# Example PowerShell helper to update PUBLIC_BASE_URL in .env:
(Get-Content .env) -replace '^PUBLIC_BASE_URL=.*', 'PUBLIC_BASE_URL=https://your-domain.ngrok-free.app' | Set-Content .env
```

---

## 3. Twilio Telephony Webhook Configuration

Configure your Twilio incoming phone number to direct incoming voice calls to VoiceGuard.

### Option A: Via Twilio Console (Web UI)
1. Log in to [Twilio Console](https://console.twilio.com/).
2. Navigate to **Phone Numbers** -> **Manage** -> **Active Numbers**.
3. Click your configured Twilio phone number.
4. Under **Voice Configuration**:
   - **A Call Comes In**: Select `Webhook`.
   - **URL**: Enter `https://your-domain.ngrok-free.app/voice` (Replace with your actual public URL).
   - **HTTP Method**: Select `HTTP POST`.
5. Click **Save Configuration**.

### Option B: Via Twilio CLI
```powershell
# Update voice webhook URL using Twilio CLI:
twilio phone-numbers:update "+1XXXXXXXXXX" --voice-url "https://your-domain.ngrok-free.app/voice" --voice-method POST
```

---

## 4. Run Preflight System Verification

Before placing real phone calls, execute the automated preflight check:

```powershell
.\\scripts\\vg.ps1 preflight
```

### Preflight Checklist Verification Table
| Check Item | Target State | Resolution if FAIL |
| :--- | :--- | :--- |
| **.env keys present** | `PASS` | Add missing keys to `.env` |
| **Twilio REST auth** | `PASS (status: active)` | Verify `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` |
| **Phone number voice capability** | `PASS (voice_capable: True)` | Ensure phone number has voice enabled in Twilio Console |
| **Trial account notice** | `Trial account: true/false` | If true, verified caller ID is required |
| **Server models & enrollment** | `PASS` | Check voiceprint `.bin` and `settings.yaml` hash |
| **Health endpoint** | `PASS` | Verify `vg.ps1 serve` and tunnel are running |
| **Webhook URL match** | `PASS` | Ensure Twilio Console voice URL matches `PUBLIC_BASE_URL/voice` |

---

## 5. Live Test Call and Monitoring

### Step 5.1: Open Security Operations Dashboard
Open Google Chrome or Edge and navigate to:
```text
http://localhost:8000/
```
Observe that the dashboard shows:
- **Status Indicator**: Connected (Green badge)
- **Active Detector Config**: Config 2 (SPOOF Off: SPEAKER + REPLAY)
- **Cryptographic Audit Chain**: Valid

### Step 5.2: Placing the Test Call
1. Dial your Twilio phone number from a mobile phone (or verified caller phone if on trial account).
2. The caller will hear: *"Thank you for calling. Your call is screened by VoiceGuard for security."*
3. Speak normally for 5-10 seconds to accumulate audio frames.

### Step 5.3: What to Watch on the Dashboard
- **Frame Counter**: Ramping up at ~50 frames per second (20 ms G.711 mu-law chunks).
- **Latency**: Window evaluation latency reported between 80 ms - 200 ms.
- **Scores**: Speaker similarity and replay probability plotted in real time.
- **Risk Score & Band**: Gauge displaying fused risk (`LOW` band for legitimate caller).

---

## 6. Three-Run Rehearsal Protocol

Execute the 3 standardized verification scenarios and capture screen recordings for audit compliance:

```
[Screen Recording Setup]
Start screen recording (OBS Studio or Windows Game Bar: Win + Alt + R).
Position the browser dashboard on the left half and server terminal on the right half.
```

### Rehearsal 1: Legitimate Live Call (Allow Path)
- **Action**: Legitimate enrolled speaker calls the Twilio number and speaks normally.
- **Expected Result**: Fused risk remains below `0.30` (`LOW` band). Decision is `Allow`. Call continues uninterrupted.
- **Dashboard Telemetry**: Green risk gauge; no step-up or termination triggered.

### Rehearsal 2: High Sensitivity / Borderline Call (Step-Up Path)
- **Action**: Caller performs high-risk transaction (e.g. wire transfer context).
- **Expected Result**: Contextual elevation triggers `MEDIUM` risk band (`0.30 - 0.60`).
- **Dashboard Telemetry**: Yellow alert badge; system triggers DTMF OTP challenge prompt.

### Rehearsal 3: Impersonation Attack / Replay (Block Path)
- **Action**: Playback pre-recorded speech or direct clone through high-quality speaker next to caller mic.
- **Expected Result**: Acoustic replay detector triggers high probability. Risk enters `HIGH` band (`> 0.60`).
- **Sustained Rule**: After 3 consecutive HIGH windows, system executes `Block (Sustained Impersonation Attack)`.
- **Termination**: VoiceGuard immediately executes REST call termination. Caller is disconnected.

---

## 7. Troubleshooting Guide

### Issue 1: ngrok URL Changed
- **Symptom**: `404 Not Found` or `Preflight SKIPPED`.
- **Cause**: ngrok free tier assigns a new URL on each restart.
- **Fix**: Update `PUBLIC_BASE_URL` in `.env` with the new ngrok URL and update the Twilio Console voice webhook URL.

### Issue 2: 403 Forbidden (Signature Verification Failed)
- **Symptom**: Incoming call receives immediate busy signal; server logs `[Twilio Auth] Signature rejected`.
- **Cause**: Twilio generates signature against the exact public URL requested. If there is a mismatch between `PUBLIC_BASE_URL` and what Twilio requested (e.g., `http` vs `https`, trailing slashes, or wrong domain), signature validation fails.
- **Fix**: Verify `PUBLIC_BASE_URL` matches the exact URL configured in Twilio Console.

### Issue 3: No Audio Frames Arriving (`total_samples_received == 0`)
- **Symptom**: Call connects, but dashboard frame counter stays at 0.
- **Cause**: WebSocket connection failed or proxy blocked WebSocket upgrade.
- **Fix**: Confirm tunnel supports WebSockets (ngrok supports WebSockets by default). Ensure TwiML returned `<Stream url="wss://...">` and not `ws://`.

### Issue 4: Trial Account Restrictions
- **Symptom**: Caller hears *"Upgrade to full account to make calls to unverified numbers"*.
- **Cause**: Twilio free trial accounts only permit communication with numbers verified in your Twilio Console.
- **Fix**: Go to **Twilio Console** -> **Phone Numbers** -> **Verified Caller IDs** and add the mobile number you are calling from.

---

## 8. Verification and Tear-Down
After rehearsal completion:
1. Verify audit log cryptographic integrity:
   ```powershell
   uv run python scripts/verify_audit.py
   ```
2. Stop server (`Ctrl + C` in Terminal 1).
3. Stop tunnel (`Ctrl + C` in Terminal 2).
4. Save the screen recording file to the artifacts directory.
"""

    doc_path.write_text(content, encoding="utf-8")
    print(f"Generated {doc_path} ({len(content)} bytes)")
    return doc_path

if __name__ == "__main__":
    generate_runbook()
