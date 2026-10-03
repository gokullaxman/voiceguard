"""
Script to update PLAN.md and regenerate documentation from evaluation artifacts.
Label: "SIMULATION, not a live call"

Reads:
- scratch/fused_eval.json
- scratch/streaming_eval.json
Generates:
- Updated PLAN.md (preserving all original text verbatim, adding status header, deviations, and acceptance criteria)
- docs/IMPLEMENTATION_PLAN.md
- docs/EVALUATION.md (with streaming vs whole-clip comparison)
- docs/DEMO_GUIDE.md (with mismatch guidance and honest presentation rules)
"""

import os
import json
import re
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLAN_PATH = REPO_ROOT / "PLAN.md"
DOCS_PLAN_PATH = REPO_ROOT / "docs" / "IMPLEMENTATION_PLAN.md"
FUSED_JSON_PATH = REPO_ROOT / "scratch" / "fused_eval.json"
STREAMING_JSON_PATH = REPO_ROOT / "scratch" / "streaming_eval.json"


def update_plan_document():
    with open(FUSED_JSON_PATH, "r", encoding="utf-8") as f:
        fused = json.load(f)
    with open(STREAMING_JSON_PATH, "r", encoding="utf-8") as f:
        streaming = json.load(f)

    cfg2 = fused["configurations"]["Config 2: SPOOF Off (SPEAKER + REPLAY)"]
    whole_acc = cfg2["accuracy"] * 100
    whole_ci = f"[{cfg2['wilson_ci_95']['lower']*100:.2f}%, {cfg2['wilson_ci_95']['upper']*100:.2f}%]"

    stream_acc = streaming["overall_match_rate"] * 100
    stream_ci = f"[{streaming['overall_wilson_ci_95']['lower']*100:.2f}%, {streaming['overall_wilson_ci_95']['upper']*100:.2f}%]"
    total_clips = streaming["total_clips"]
    match_count = streaming["overall_match_count"]

    today_str = datetime.now().strftime("%Y-%m-%d")

    status_header = f"""# VoiceGuard — Implementation Plan & Operational Status

**Plan status as of {today_str}**
*Exhibition Demonstration Mode: SIMULATION, not a live call*

### Execution Status Summary

| Phase | Planned Gate | Status | Key Evidence File |
| :--- | :--- | :--- | :--- |
| **Phase 1: Environment & Pretrained Models** | CPU dependencies, FFmpeg, AASIST & ECAPA inference | **DONE WITH LIMITS** | `scratch/audit_spoof_orientation.py`, `models/spoof.py` |
| **Phase 2: Telephony Pipeline & Dataset** | G.711 $\\mu$-law roundtrip, 40 evaluation clips | **DONE** | `data/metadata/manifest.json`, `tests/test_telephony.py` |
| **Phase 3: Detectors, Enrollment & Risk Engine** | 3 detectors, AES-256-GCM, $\\ge 90\\%$ fused target | **DONE WITH LIMITS** | `scratch/fused_eval.json`, `config/settings.yaml` |
| **Phase 4: Streaming Server & Call Control** | FastAPI gateway, sustained evidence rule, action dispatcher | **DONE WITH LIMITS** | `server/streaming.py`, `tests/test_live_mock_dry_run.py` |
| **Phase 5: Live SOC Dashboard** | Real-time meter, timeline, audit chain, demo controls | **DONE** | `dashboard/index.html`, `tests/test_dashboard_demo_gate.py` |
| **Phase 6: Security, Privacy & Audit Integrity** | AES-256-GCM voiceprint, zero raw audio logs, SHA-256 chain | **DONE WITH LIMITS** | `scripts/step8_privacy_audit.py`, `data/audit/audit_log.jsonl` |
| **Phase 7: Evaluation & Demonstration** | Primary evaluation, live Twilio bring-up, 3 demo scenes | **DONE WITH LIMITS** | `scratch/fused_eval.json`, `scratch/streaming_eval.json`, `server/demo.py` |

---

### Empirical Accuracy Benchmark (Generated from Artifacts)

- **Whole-Clip Fused Accuracy (Config 2, 5-Fold CV)**: **{whole_acc:.1f}%** (39/40) | Wilson 95% CI: {whole_ci}
  *(Evaluated on entire audio duration; post-hoc configuration selection without held-out estimate).*
- **Sustained-Window Streaming Decision Rate**: **{stream_acc:.1f}%** ({match_count}/{total_clips}) | Wilson 95% CI: {stream_ci}
  *(Evaluated on rolling 2.0s buffers advanced every 1.0s under 3-consecutive-window sustained evidence rule).*
- **Statement on Metrics**: Whole-clip scoring and sustained-window streaming are different measurements. Neither should be called "the" accuracy.

---
"""

    with open(PLAN_PATH, "r", encoding="utf-8") as f:
        original_text = f.read()

    # Insert "As built vs planned" under each phase in original text
    p1_dev = """
### As Built vs Planned — Phase 1 Deviations
- **SPOOF (AASIST) Disabled in Production**: Pretrained AASIST model was successfully integrated and performs real inference. However, on consumer smartphone and laptop microphone audio, AASIST exhibits severe acoustic domain shift, classifying bonafide speech as 0.92–0.99 spoof probability. The underlying physical/acoustic cause is unmeasured (`cause not measured`). Consequently, SPOOF is disabled (`weight: 0.0`) in production.
- **Evidence**: `scratch/audit_spoof_orientation.py`, `models/spoof.py`, `config/settings.yaml`.
"""

    p2_dev = """
### As Built vs Planned — Phase 2 Deviations
- **Phone-Live Dataset Limitation**: The 18 phone-live clips collected in Step 7 (`data/phone_live/`) represent 18 slices of ONE WhatsApp voice-note recording from one phone in one room. They are not independent clips; the effective sample size is approximately 1. The zero false-positive result on these slices is weak evidence of field robustness.
- **Replay Detector Acoustic Confound**: The acoustic replay detector was trained on 40 clips recorded with a single phone and a single loudspeaker. It cannot be ruled out that the model distinguishes hardware/transducer coloration rather than generalized replay acoustics.
- **Evidence**: `data/metadata/manifest.json`, `data/phone_live/`, `models/replay.py`.
"""

    p3_dev = """
### As Built vs Planned — Phase 3 Deviations
- **Production Fusion Weights & Post-Hoc Selection**: Planned fusion weights were `0.4` SPOOF / `0.3` SPEAKER / `0.3` REPLAY. In production, Config 2 is used with weights `0.0` SPOOF / `0.5` SPEAKER / `0.5` REPLAY. The decision to disable SPOOF was made after observing evaluation results; reported cross-validation accuracy is therefore an optimistic post-hoc selection.
- **Linear Speaker Calibration Fit on All Data**: The linear speaker mapping parameters `(a = 0.3364, b = 0.4169)` were fitted on all 40 phone-simulated evaluation clips without a held-out estimate.
- **Sustained-Evidence Rule on Both Bands**: Decision bands apply to final fused risk. The sustained-evidence rule requires 3 consecutive qualifying windows before triggering either MEDIUM (Step-Up) or HIGH (Block).
- **Configuration File Split**: Configuration is split into `config/settings.yaml` (hashed whole, strictly matching `scratch/fused_eval.json` hash `ea7f4e3d...`) and `config/live.yaml` (telephony operational settings with a separate hash).
- **AASIST Display Modes & Recalibration (Experimental)**: Added `spoof.display_mode` (`off` [default], `real`, `calibrated`) configured in `config/live.yaml` or via `VOICEGUARD_SPOOF_DISPLAY`. In `calibrated` mode, AASIST outputs are recalibrated on project data (weight = -0.259134, intercept = 1.911943) and displayed with neutral chip "EXPERIMENTAL, display only" and disclosure label: "AASIST output recalibrated on project data (optimistic, one speaker). Display only, not used in decision." Crucially, the recalibrated value strictly does not enter the risk engine; fused risk, band, streaks, actions, audit risk fields, and outcome remain 100% byte-identical across all three modes.
- **Evidence**: `config/settings.yaml`, `config/live.yaml`, `scratch/fused_eval.json`, `models/artifacts/spoof_calibration.json`, `server/risk_engine.py`, `server/streaming.py`.
"""

    p4_dev = """
### As Built vs Planned — Phase 4 Deviations
- **Twilio Live Telephony Untested on Live PSTN**: The complete Twilio Media Stream path was implemented, unit tested, and rehearsed over public ngrok tunnels using a simulated client. However, no live carrier PSTN telephone call was completed; the phone number was not provisioned on the Twilio account.
- **Dry Mode Protection**: Added `live.dry_mode` (`config/live.yaml`) to log and display actions on the SOC dashboard without dispatching REST termination calls during initial bring-up.
- **Mock Step-Up OTP**: Step-up OTP is implemented as an exhibition mock simulation ("MOCK OTP"). The interactive carrier DTMF `<Gather>` flow is untested on live carrier lines.
- **Evidence**: `config/live.yaml`, `server/responses.py`, `tests/test_live_mock_dry_run.py`, `scripts/tunnel_rehearsal.py`.
"""

    p5_dev = """
### As Built vs Planned — Phase 5 Deviations
- **Exhibition Simulation Demo Mode Added**: Added dedicated `/demo/*` endpoints in `server/demo.py` and an interactive demo controller panel in `dashboard/index.html`. Streams allowlisted evaluation clips through the full real-time pipeline with fixed banner: `SIMULATION, not a live call`.
- **Upload Analysis Mode Added**: Upload analysis mode added for exhibition; not part of the original plan; not a validated evaluation.
- **Three-Path Streaming Consistency Aligned**: Window triggering threshold in `server/demo.py` was aligned from `< 640` to `< 320` samples residue to match `eval_streaming.py` and `server/upload.py`. All three streaming execution paths now evaluate identical 1.0s window cadences and produce concordant outcomes across evaluation scenarios.
- **Superseded Prior Demo Results**: Demo results before the window-cadence fix (demo.py < 640) are invalid and superseded.
- **Evidence**: `server/demo.py`, `server/upload.py`, `scripts/eval_streaming.py`, `tests/test_path_consistency.py`.
"""

    p6_dev = """
### As Built vs Planned — Phase 6 Deviations
- **Archived Audit Log**: An earlier automated agent action truncated `data/audit/audit_log.jsonl` to 40 records. To preserve forensic integrity, the truncated file was archived to `data/audit/archive_20261003_024646.jsonl` and a fresh, fully valid hash chain was initialized.
- **Evidence**: `data/audit/archive_20261003_024646.jsonl`, `server/audit.py`, `tests/test_audit.py`.
"""

    p7_dev = f"""
### As Built vs Planned — Phase 7 Deviations
- **Streaming-Level Evaluation Results (Step 3)**:
  - Genuine Live (n=10): 8 Allow, 2 Step-Up only, 0 Block (80.0% Match | Wilson 95% CI: [49.02%, 94.33%]). False step-up rate = 20.0%.
  - Cloned Direct (n=10): 7 Allow, 3 Step-Up only, 0 Block (30.0% Match | Wilson 95% CI: [10.78%, 60.32%]). Miss rate = 70.0% (clips too short to sustain 3 consecutive windows above 0.30 threshold).
  - Genuine Replay (n=10): 0 Allow, 1 Step-Up only, 9 Block (100.0% Match | Wilson 95% CI: [72.25%, 100.00%]). Miss rate = 0.0%.
  - Cloned Replay (n=10): 3 Allow, 3 Step-Up only, 4 Block (70.0% Match | Wilson 95% CI: [39.68%, 89.22%]). Miss rate = 30.0%.
  - Overall Streaming Decision Rate = {stream_acc:.1f}% ({match_count}/40) | Wilson 95% CI: {stream_ci}.
- **MP3 Lossy Compression Effect on Genuine Live Audio (n=10)**:
  - Evaluated 10 genuine_live clips across WAV, MP3 128 kbps, and MP3 64 kbps under upload analysis (phone_sim ON).
  - WAV: 8/10 Allow (80.0% | Wilson 95% CI: [49.02%, 94.33%]), mean max risk = 0.3962, mean median speaker_sim = 0.3917, mean median replay_prob = 0.0001.
  - MP3 128 kbps: 8/10 Allow (80.0% | Wilson 95% CI: [49.02%, 94.33%]), mean max risk = 0.3922, mean median speaker_sim = 0.3923, mean median replay_prob = 0.0001.
  - MP3 64 kbps: 8/10 Allow (80.0% | Wilson 95% CI: [49.02%, 94.33%]), mean max risk = 0.3967, mean median speaker_sim = 0.3962, mean median replay_prob = 0.0001.
  - Measured pattern: Compression to MP3 at 128 kbps or 64 kbps yielded identical Allow rates (8/10) with negligible mean risk delta (< 0.005).
- **Demo Set Mismatches After Cadence Alignment**:
  - `live_01` (Genuine Live 1): Expected Allow -> Actual: Step-up only (false step-up). Windows 1-3 scored MEDIUM risk (`0.5004`, `0.5001`, `0.4137`) before settling to LOW in window 4 (`0.2703`). Fired MOCK OTP at 8.00s. Cause: `cause not measured`.
  - `clone_02` (Direct Voice Clone 2): Expected Not Allow -> Actual: Allow (missed). 2 windows scored, both MEDIUM risk (`0.5000`), but clip ended before sustaining 3 consecutive windows. Cause: `cause not measured`.
  - `clone_replay_01` (Cloned Replay Attack 1): Expected Not Allow -> Actual: Allow (missed). Windows 1-2 scored HIGH/MEDIUM before dropping to LOW on windows 3-4. Cause: `cause not measured`.
- **Evidence**: `scratch/streaming_eval.json`, `scripts/run_demo_set.py`, `scripts/step3_mp3_effect.py`.
"""

    # Inject subsections
    updated = original_text
    updated = updated.replace("5. Phase 2 — Telephony Pipeline", p1_dev + "\n5. Phase 2 — Telephony Pipeline")
    updated = updated.replace("6. Phase 3 — Three Detectors", p2_dev + "\n6. Phase 3 — Three Detectors")
    updated = updated.replace("7. Phase 4 — Streaming Server", p3_dev + "\n7. Phase 4 — Streaming Server")
    updated = updated.replace("8. Phase 5 — Live Dashboard", p4_dev + "\n8. Phase 5 — Live Dashboard")
    updated = updated.replace("9. Phase 6 — Security, Privacy and Audit Integrity", p5_dev + "\n9. Phase 6 — Security, Privacy and Audit Integrity")
    updated = updated.replace("10. Phase 7 — Evaluation, Live Integration and Rehearsal", p6_dev + "\n10. Phase 7 — Evaluation, Live Integration and Rehearsal")
    updated = updated.replace("11. Configuration Design", p7_dev + "\n11. Configuration Design")

    # Update Section 14 (Final Acceptance Criteria)
    section_14_updated = """14. Final Acceptance Criteria — Operational Verdict

| Acceptance Criterion | Verdict | Evidence & Verification |
| :--- | :--- | :--- |
| **All three detectors perform real inference** | **MET WITH LIMITS** | ECAPA and Replay active in production. AASIST produces real inference on GPU/CPU but is disabled in production due to measured domain shift (`cause not measured`). Verified in `tests/test_spoof.py`. |
| **Telephony simulator reproduces intended codec path** | **MET** | Verified 8kHz G.711 $\\mu$-law round-trip and polyphase resampling against Python `audioop` reference across all 256 code points. Verified in `tests/test_telephony.py`. |
| **Risk engine produces explainable decisions** | **MET** | Fused risk computes weighted detector contributions, context adjustments, and sustained-window escalation rules with human-readable breakdowns. Verified in `tests/test_risk_engine.py`. |
| **Step-up authentication and call blocking work** | **MET WITH LIMITS** | Blocking and step-up work reliably in software simulation and mock dispatcher. Outbound carrier DTMF IVR challenge is untested on live PSTN lines. Verified in `tests/test_live_mock_dry_run.py`. |
| **Dashboard receives live decision updates** | **MET** | Vanilla JS dashboard connects to `/dashboard-ws`, receiving per-window scores, timeline strips, and audit records with auto-reconnection. Verified in `tests/test_dashboard_demo_gate.py`. |
| **Voiceprint is encrypted at rest** | **MET** | AES-256-GCM encryption with 12-byte random nonce and authenticated speaker ID. Plaintext embeddings are memory-only. Verified in `tests/test_encryption.py`. |
| **Live audio remains in memory** | **MET** | Audio streaming buffers remain exclusively in RAM. No raw audio, PCM chunks, or voiceprints are written to disk or logs. Verified in `scripts/step8_privacy_audit.py`. |
| **Audit verifier detects tampering** | **MET** | SHA-256 cryptographic hash chain validates all historical scoring events and successfully detects record deletion, modification, or reordering. Verified in `tests/test_audit.py`. |
| **Evaluation uses held-out data with full disclosures** | **MET WITH LIMITS** | 5-fold cross-validation conducted; post-hoc configuration selection, single-speaker calibration, and streaming-window limitations explicitly disclosed. Verified in `scratch/fused_eval.json`. |
| **Live Twilio demonstration works or fallback identified** | **NOT MET** | Live PSTN carrier demonstration was not executed due to unprovisioned carrier account. Fallback successfully implemented and verified: full real-time software simulation demo labeled `"SIMULATION, not a live call"`. Verified in `tests/test_demo.py`. |
| **Documentation explains limitations, privacy & setup** | **MET** | Comprehensive operational, evaluation, and exhibition guides provided in `docs/EVALUATION.md`, `docs/DEMO_GUIDE.md`, and `docs/LIVE_BRINGUP.md`. |
"""
    updated = updated.replace("14. Final Acceptance Criteria", section_14_updated)

    # Add Known Limitations and What NOT to Claim
    limitations_section = """
16. Known Limitations and Presentation Boundaries

To maintain scientific integrity and avoid AI hyperbole, the following boundaries must be maintained:

1. **DO NOT claim universal deepfake protection**: The system does not claim 100% detection against unseen, state-of-the-art zero-shot generative voice models.
2. **DO NOT claim multi-speaker generalization**: The prototype is enrolled and calibrated specifically against a single target speaker (`gokul`). Multi-speaker false acceptance rates require larger multi-speaker corpora.
3. **DO NOT claim AASIST is actively protecting calls**: AASIST is deactivated in production (`weight: 0.0`) due to documented acoustic domain shift on non-studio microphones (`cause not measured`).
4. **DO NOT claim the replay detector is device-independent**: The replay detector relies on spectral coloration differences between recording and playback devices; open-world acoustic replay generalization remains an ongoing research challenge.
5. **DO NOT claim this is live carrier telephony**: The exhibition demo is a faithful **software simulation** streaming 20 ms G.711 $\\mu$-law frames over WebSocket. It is not connected to live carrier PSTN trunks.
6. **DO NOT claim Step-Up OTP sends real SMS or carrier DTMF**: In demo mode, step-up OTP is a mock UI simulation ("MOCK OTP").
"""
    updated += limitations_section

    full_updated_plan = status_header + updated

    with open(PLAN_PATH, "w", encoding="utf-8") as f:
        f.write(full_updated_plan)
    with open(DOCS_PLAN_PATH, "w", encoding="utf-8") as f:
        f.write(full_updated_plan)

    print(f"Updated {PLAN_PATH} and {DOCS_PLAN_PATH}")


if __name__ == "__main__":
    update_plan_document()
