# VoiceGuard

**Real-Time Voice-Cloning and Impersonation Attack Detection for Telephony**  
*CresIgnite Project Expo 2K26 | Team Chipers | Developer: Gokul*

VoiceGuard inspects live telephone audio streams in real time to detect voice-cloning attacks, acoustic replay attacks, and synthetic speech before sensitive financial actions are executed.

> **Note**: Evaluation audio, the enrollment voiceprint, model weights and .env are not included in this repository. Tests and demos that need them will fail or skip on a fresh clone. Results reported here come from a small single-speaker custom dataset and are not a validated accuracy figure.

---

## 1. Quick Start & Operations CLI (`scripts/vg.ps1`)

The PowerShell script [scripts/vg.ps1](file:///c:/Users/Dell%20Latitude%207410/Downloads/expo/scripts/vg.ps1) automates all core operations:

```powershell
# 1. Environment Setup & Key Provisioning
.\scripts\vg.ps1 setup

# 2. Run Comprehensive Unit & Integration Test Suite
.\scripts\vg.ps1 test

# 3. Run Multi-Detector Fused Cross-Validation Evaluation
.\scripts\vg.ps1 eval

# 4. Start Telephony Streaming Server & Dashboard Gateway (FastAPI)
.\scripts\vg.ps1 serve

# 5. Instructions for Public Webhook Tunneling (ngrok / cloudflared)
.\scripts\vg.ps1 tunnel

# 6. Launch Exhibition Demo Server (Simulation Mode)
.\scripts\vg.ps1 demo
```

> [!IMPORTANT]
> **Telephony Connectivity & Simulation Mode**:
> Live carrier Twilio PSTN interconnect is **optional and untested**. Live PSTN carrier trunks introduce uncontrolled packet loss and jitter. The primary exhibition presentation of VoiceGuard is the **software simulation demo**, launched via `.\scripts\vg.ps1 demo`, which opens the interactive web dashboard at `http://localhost:8000`. The simulation streams allowlisted evaluation audio as 20 ms G.711 mu-law frames over the real WebSocket and pipeline without external carrier dependencies.

---

## 2. Exhibition Demo & Documentation Links

- **Exhibition Demonstration Guide**: [docs/DEMO_GUIDE.md](file:///c:/Users/Dell%20Latitude%207410/Downloads/expo/docs/DEMO_GUIDE.md) (Three-scene script, presenter talking points, boundaries on claims, and technical Q&A).
- **Comprehensive Evaluation Report**: [docs/EVALUATION.md](file:///c:/Users/Dell%20Latitude%207410/Downloads/expo/docs/EVALUATION.md) (Cross-validation matrices, Wilson confidence intervals, domain shift findings, and limitations).
- **Live Carrier Bring-Up Runbook**: [docs/LIVE_BRINGUP.md](file:///c:/Users/Dell%20Latitude%207410/Downloads/expo/docs/LIVE_BRINGUP.md) (Optional PSTN onboarding with Twilio).

---

## 3. Cryptographic Security & Audit Chain

- **Voiceprint Enrollment**:
  - Encrypted via AES-256-GCM with a 12-byte random nonce.
  - Plaintext embeddings are stored in memory only and never written to disk or logs.
  - AAD includes the speaker ID and timestamp.
  - File stored under [data/enrollment/enrolled_voiceprint.bin](file:///c:/Users/Dell%20Latitude%207410/Downloads/expo/data/enrollment/enrolled_voiceprint.bin) (`.gitignore`).
- **Cryptographic Audit Chain**:
  - Every call scoring event is appended to [data/audit/audit_log.jsonl](file:///c:/Users/Dell%20Latitude%207410/Downloads/expo/data/audit/audit_log.jsonl).
  - Each record contains a deterministic SHA-256 hash chaining back to the previous record.
  - Verification CLI: `uv run python scripts/verify_audit.py`
  - **Security Notice**: *A cryptographic hash chain alone proves internal sequential consistency and detects tampering, reordering, deletion, or insertion; it cannot prevent a privileged attacker with operating system write permissions from rewriting the whole chain from scratch.*

---

## 4. Architecture & Fused Risk Engine

VoiceGuard uses a modular multi-detector architecture configured in [config/settings.yaml](file:///c:/Users/Dell%20Latitude%207410/Downloads/expo/config/settings.yaml):
- **Speaker Verification (ECAPA-TDNN)**: 192-dimensional embeddings compared via cosine similarity.
- **Acoustic Replay Detector**: Gain-normalized acoustic spectral features and logistic regression.
- **Synthetic Spoof Detector (AASIST)**: Evaluated for domain shift; disabled (`weight: 0.0`) in production.
- **Decision Bands**:
  - **LOW (< 0.30)**: Allow call to proceed.
  - **MEDIUM (0.30 - 0.60)**: Step-Up Challenge (MOCK OTP flow).
  - **HIGH (> 0.60)**: Immediate call termination upon sustained evidence (3 consecutive windows).

---

## 5. Audio File Upload Analysis Mode

The dashboard provides a dedicated **"Analyse an audio file"** card for ad-hoc exhibition testing:

- **How to Use**:
  1. Open the dashboard at `http://localhost:8000`.
  2. Drag and drop or browse for an audio file (`.wav`, `.mp3`, `.m4a`, `.ogg`, `.opus`, `.flac`, `.aac`, `.webm`). Limits: 2.0s &ndash; 120s, max 25 MB.
  3. Select intent sensitivity (`balance_check`, `password_reset`, `wire_transfer`), analysis mode (`stream` [default] or `whole`), and whether to apply telephony simulation (`phone_sim`).
  4. Click **Analyse Audio**. Local audio plays directly from a browser-only object URL (`URL.createObjectURL(file)`).
  5. Download the complete result as a clean JSON report (contains scores, explanation, and metrics only; no audio).
- **Files to Try**:
  - Genuine speech of the enrolled speaker (`data/genuine/live_01.wav` &ndash; `live_03.wav`).
  - Cloned speech (`data/cloned/clone_01.wav` &ndash; `clone_02.wav`).
  - Acoustic replay recordings (`data/replay/live_replay_01.wav`, `clone_replay_02.wav`).
  - Lossy compressed audio (e.g. 128 kbps MP3) to inspect codec quantization effects.
- **How to Read Results**:
  - **Risk Meter & Band**: Fused risk score with LOW / MEDIUM / HIGH classification.
  - **Whole-Stream Outcome**: `Allow`, `Step-up (mock OTP)`, or `Block`.
  - **Detectors**: Speaker Verification (ECAPA), Acoustic Replay Detector, and Synthetic Spoof strictly labeled as `OFF (domain shift, see limitations)`.
  - **Timeline Strip & Explanation**: Per-window risk progression, weighted contributions, acoustic SNR, peak amplitude, and speech fraction.
  - **Active Warnings**: Highlighted in amber (e.g. short clips, clipping, silence, single-speaker notice).
- **What NOT to Claim**:
  - Every upload result carries the label: **"UPLOAD ANALYSIS, not a validated accuracy figure"**.
  - Calibrated for one enrolled speaker (`gokul`).
  - Synthetic-speech detector (AASIST) is OFF due to unmeasured domain shift.
  - A "Block" or "Step-up" means the system is suspicious, not that the clip is proven fake. An "Allow" does not prove the clip is genuine.
- **Privacy & Data Handling Statement**:
  - Uploaded audio is processed in memory and an isolated temporary directory (`tempfile.TemporaryDirectory()`).
  - All temporary files are guaranteed deleted in a `finally` block immediately after processing, even on errors.
  - Uploaded audio is never stored on disk, never logged, never committed to git, never added to the manifest, and never used for training or calibration. Audit records store scores and parameters only with an anonymous ID (`UPLOAD_<hex>`).

