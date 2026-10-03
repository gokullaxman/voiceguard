# VoiceGuard — Implementation Plan & Operational Status

**Plan status as of 2026-10-03**
*Exhibition Demonstration Mode: SIMULATION, not a live call*

### Execution Status Summary

| Phase | Planned Gate | Status | Key Evidence File |
| :--- | :--- | :--- | :--- |
| **Phase 1: Environment & Pretrained Models** | CPU dependencies, FFmpeg, AASIST & ECAPA inference | **DONE WITH LIMITS** | `scratch/audit_spoof_orientation.py`, `models/spoof.py` |
| **Phase 2: Telephony Pipeline & Dataset** | G.711 $\mu$-law roundtrip, 40 evaluation clips | **DONE** | `data/metadata/manifest.json`, `tests/test_telephony.py` |
| **Phase 3: Detectors, Enrollment & Risk Engine** | 3 detectors, AES-256-GCM, $\ge 90\%$ fused target | **DONE WITH LIMITS** | `scratch/fused_eval.json`, `config/settings.yaml` |
| **Phase 4: Streaming Server & Call Control** | FastAPI gateway, sustained evidence rule, action dispatcher | **DONE WITH LIMITS** | `server/streaming.py`, `tests/test_live_mock_dry_run.py` |
| **Phase 5: Live SOC Dashboard** | Real-time meter, timeline, audit chain, demo controls | **DONE** | `dashboard/index.html`, `tests/test_dashboard_demo_gate.py` |
| **Phase 6: Security, Privacy & Audit Integrity** | AES-256-GCM voiceprint, zero raw audio logs, SHA-256 chain | **DONE WITH LIMITS** | `scripts/step8_privacy_audit.py`, `data/audit/audit_log.jsonl` |
| **Phase 7: Evaluation & Demonstration** | Primary evaluation, live Twilio bring-up, 3 demo scenes | **DONE WITH LIMITS** | `scratch/fused_eval.json`, `scratch/streaming_eval.json`, `server/demo.py` |

---

### Empirical Accuracy Benchmark (Generated from Artifacts)

- **Whole-Clip Fused Accuracy (Config 2, 5-Fold CV)**: **97.5%** (39/40) | Wilson 95% CI: [87.12%, 99.56%]
  *(Evaluated on entire audio duration; post-hoc configuration selection without held-out estimate).*
- **Sustained-Window Streaming Decision Rate**: **70.0%** (28/40) | Wilson 95% CI: [54.57%, 81.93%]
  *(Evaluated on rolling 2.0s buffers advanced every 1.0s under 3-consecutive-window sustained evidence rule).*
- **Statement on Metrics**: Whole-clip scoring and sustained-window streaming are different measurements. Neither should be called "the" accuracy.

---
# VoiceGuard — Implementation Plan & Operational Status

**Plan status as of 2026-10-03**
*Exhibition Demonstration Mode: SIMULATION, not a live call*

### Execution Status Summary

| Phase | Planned Gate | Status | Key Evidence File |
| :--- | :--- | :--- | :--- |
| **Phase 1: Environment & Pretrained Models** | CPU dependencies, FFmpeg, AASIST & ECAPA inference | **DONE WITH LIMITS** | `scratch/audit_spoof_orientation.py`, `models/spoof.py` |
| **Phase 2: Telephony Pipeline & Dataset** | G.711 $\mu$-law roundtrip, 40 evaluation clips | **DONE** | `data/metadata/manifest.json`, `tests/test_telephony.py` |
| **Phase 3: Detectors, Enrollment & Risk Engine** | 3 detectors, AES-256-GCM, $\ge 90\%$ fused target | **DONE WITH LIMITS** | `scratch/fused_eval.json`, `config/settings.yaml` |
| **Phase 4: Streaming Server & Call Control** | FastAPI gateway, sustained evidence rule, action dispatcher | **DONE WITH LIMITS** | `server/streaming.py`, `tests/test_live_mock_dry_run.py` |
| **Phase 5: Live SOC Dashboard** | Real-time meter, timeline, audit chain, demo controls | **DONE** | `dashboard/index.html`, `tests/test_dashboard_demo_gate.py` |
| **Phase 6: Security, Privacy & Audit Integrity** | AES-256-GCM voiceprint, zero raw audio logs, SHA-256 chain | **DONE WITH LIMITS** | `scripts/step8_privacy_audit.py`, `data/audit/audit_log.jsonl` |
| **Phase 7: Evaluation & Demonstration** | Primary evaluation, live Twilio bring-up, 3 demo scenes | **DONE WITH LIMITS** | `scratch/fused_eval.json`, `scratch/streaming_eval.json`, `server/demo.py` |

---

### Empirical Accuracy Benchmark (Generated from Artifacts)

- **Whole-Clip Fused Accuracy (Config 2, 5-Fold CV)**: **97.5%** (39/40) | Wilson 95% CI: [87.12%, 99.56%]
  *(Evaluated on entire audio duration; post-hoc configuration selection without held-out estimate).*
- **Sustained-Window Streaming Decision Rate**: **70.0%** (28/40) | Wilson 95% CI: [54.57%, 81.93%]
  *(Evaluated on rolling 2.0s buffers advanced every 1.0s under 3-consecutive-window sustained evidence rule).*
- **Statement on Metrics**: Whole-clip scoring and sustained-window streaming are different measurements. Neither should be called "the" accuracy.

---
# VoiceGuard — Implementation Plan & Operational Status

**Plan status as of 2026-10-03**
*Exhibition Demonstration Mode: SIMULATION, not a live call*

### Execution Status Summary

| Phase | Planned Gate | Status | Key Evidence File |
| :--- | :--- | :--- | :--- |
| **Phase 1: Environment & Pretrained Models** | CPU dependencies, FFmpeg, AASIST & ECAPA inference | **DONE WITH LIMITS** | `scratch/audit_spoof_orientation.py`, `models/spoof.py` |
| **Phase 2: Telephony Pipeline & Dataset** | G.711 $\mu$-law roundtrip, 40 evaluation clips | **DONE** | `data/metadata/manifest.json`, `tests/test_telephony.py` |
| **Phase 3: Detectors, Enrollment & Risk Engine** | 3 detectors, AES-256-GCM, $\ge 90\%$ fused target | **DONE WITH LIMITS** | `scratch/fused_eval.json`, `config/settings.yaml` |
| **Phase 4: Streaming Server & Call Control** | FastAPI gateway, sustained evidence rule, action dispatcher | **DONE WITH LIMITS** | `server/streaming.py`, `tests/test_live_mock_dry_run.py` |
| **Phase 5: Live SOC Dashboard** | Real-time meter, timeline, audit chain, demo controls | **DONE** | `dashboard/index.html`, `tests/test_dashboard_demo_gate.py` |
| **Phase 6: Security, Privacy & Audit Integrity** | AES-256-GCM voiceprint, zero raw audio logs, SHA-256 chain | **DONE WITH LIMITS** | `scripts/step8_privacy_audit.py`, `data/audit/audit_log.jsonl` |
| **Phase 7: Evaluation & Demonstration** | Primary evaluation, live Twilio bring-up, 3 demo scenes | **DONE WITH LIMITS** | `scratch/fused_eval.json`, `scratch/streaming_eval.json`, `server/demo.py` |

---

### Empirical Accuracy Benchmark (Generated from Artifacts)

- **Whole-Clip Fused Accuracy (Config 2, 5-Fold CV)**: **97.5%** (39/40) | Wilson 95% CI: [87.12%, 99.56%]
  *(Evaluated on entire audio duration; post-hoc configuration selection without held-out estimate).*
- **Sustained-Window Streaming Decision Rate**: **70.0%** (28/40) | Wilson 95% CI: [54.57%, 81.93%]
  *(Evaluated on rolling 2.0s buffers advanced every 1.0s under 3-consecutive-window sustained evidence rule).*
- **Statement on Metrics**: Whole-clip scoring and sustained-window streaming are different measurements. Neither should be called "the" accuracy.

---
# VoiceGuard — Implementation Plan & Operational Status

**Plan status as of 2026-10-03**
*Exhibition Demonstration Mode: SIMULATION, not a live call*

### Execution Status Summary

| Phase | Planned Gate | Status | Key Evidence File |
| :--- | :--- | :--- | :--- |
| **Phase 1: Environment & Pretrained Models** | CPU dependencies, FFmpeg, AASIST & ECAPA inference | **DONE WITH LIMITS** | `scratch/audit_spoof_orientation.py`, `models/spoof.py` |
| **Phase 2: Telephony Pipeline & Dataset** | G.711 $\mu$-law roundtrip, 40 evaluation clips | **DONE** | `data/metadata/manifest.json`, `tests/test_telephony.py` |
| **Phase 3: Detectors, Enrollment & Risk Engine** | 3 detectors, AES-256-GCM, $\ge 90\%$ fused target | **DONE WITH LIMITS** | `scratch/fused_eval.json`, `config/settings.yaml` |
| **Phase 4: Streaming Server & Call Control** | FastAPI gateway, sustained evidence rule, action dispatcher | **DONE WITH LIMITS** | `server/streaming.py`, `tests/test_live_mock_dry_run.py` |
| **Phase 5: Live SOC Dashboard** | Real-time meter, timeline, audit chain, demo controls | **DONE** | `dashboard/index.html`, `tests/test_dashboard_demo_gate.py` |
| **Phase 6: Security, Privacy & Audit Integrity** | AES-256-GCM voiceprint, zero raw audio logs, SHA-256 chain | **DONE WITH LIMITS** | `scripts/step8_privacy_audit.py`, `data/audit/audit_log.jsonl` |
| **Phase 7: Evaluation & Demonstration** | Primary evaluation, live Twilio bring-up, 3 demo scenes | **DONE WITH LIMITS** | `scratch/fused_eval.json`, `scratch/streaming_eval.json`, `server/demo.py` |

---

### Empirical Accuracy Benchmark (Generated from Artifacts)

- **Whole-Clip Fused Accuracy (Config 2, 5-Fold CV)**: **97.5%** (39/40) | Wilson 95% CI: [87.12%, 99.56%]
  *(Evaluated on entire audio duration; post-hoc configuration selection without held-out estimate).*
- **Sustained-Window Streaming Decision Rate**: **70.0%** (28/40) | Wilson 95% CI: [54.57%, 81.93%]
  *(Evaluated on rolling 2.0s buffers advanced every 1.0s under 3-consecutive-window sustained evidence rule).*
- **Statement on Metrics**: Whole-clip scoring and sustained-window streaming are different measurements. Neither should be called "the" accuracy.

---
# VoiceGuard — Implementation Plan & Operational Status

**Plan status as of 2026-10-03**
*Exhibition Demonstration Mode: SIMULATION, not a live call*

### Execution Status Summary

| Phase | Planned Gate | Status | Key Evidence File |
| :--- | :--- | :--- | :--- |
| **Phase 1: Environment & Pretrained Models** | CPU dependencies, FFmpeg, AASIST & ECAPA inference | **DONE WITH LIMITS** | `scratch/audit_spoof_orientation.py`, `models/spoof.py` |
| **Phase 2: Telephony Pipeline & Dataset** | G.711 $\mu$-law roundtrip, 40 evaluation clips | **DONE** | `data/metadata/manifest.json`, `tests/test_telephony.py` |
| **Phase 3: Detectors, Enrollment & Risk Engine** | 3 detectors, AES-256-GCM, $\ge 90\%$ fused target | **DONE WITH LIMITS** | `scratch/fused_eval.json`, `config/settings.yaml` |
| **Phase 4: Streaming Server & Call Control** | FastAPI gateway, sustained evidence rule, action dispatcher | **DONE WITH LIMITS** | `server/streaming.py`, `tests/test_live_mock_dry_run.py` |
| **Phase 5: Live SOC Dashboard** | Real-time meter, timeline, audit chain, demo controls | **DONE** | `dashboard/index.html`, `tests/test_dashboard_demo_gate.py` |
| **Phase 6: Security, Privacy & Audit Integrity** | AES-256-GCM voiceprint, zero raw audio logs, SHA-256 chain | **DONE WITH LIMITS** | `scripts/step8_privacy_audit.py`, `data/audit/audit_log.jsonl` |
| **Phase 7: Evaluation & Demonstration** | Primary evaluation, live Twilio bring-up, 3 demo scenes | **DONE WITH LIMITS** | `scratch/fused_eval.json`, `scratch/streaming_eval.json`, `server/demo.py` |

---

### Empirical Accuracy Benchmark (Generated from Artifacts)

- **Whole-Clip Fused Accuracy (Config 2, 5-Fold CV)**: **97.5%** (39/40) | Wilson 95% CI: [87.12%, 99.56%]
  *(Evaluated on entire audio duration; post-hoc configuration selection without held-out estimate).*
- **Sustained-Window Streaming Decision Rate**: **70.0%** (28/40) | Wilson 95% CI: [54.57%, 81.93%]
  *(Evaluated on rolling 2.0s buffers advanced every 1.0s under 3-consecutive-window sustained evidence rule).*
- **Statement on Metrics**: Whole-clip scoring and sustained-window streaming are different measurements. Neither should be called "the" accuracy.

---
VOICEGUARD

Real-Time Voice-Cloning and Impersonation Attack Detection System

Team Chipers  |  Developer: Gokul
CresIgnite Project Expo 2K26

COMPLETE IMPLEMENTATION PLAN

1. Project Objective

Build a working security layer that screens live telephone audio, identifies synthetic speech, replay attacks and speaker mismatches, calculates an explainable risk score, and decides whether to allow the call, request additional authentication or block it. There is no fixed deadline; implementation proceeds phase by phase with evidence-based acceptance gates.

2. Overall System Architecture

Incoming phone call → Twilio Media Streams → base64 decode and G.711 μ-law PCM → 8 kHz to 16 kHz conversion → VAD and preprocessing → rolling audio buffer → three parallel detectors → context-aware risk engine → Allow / Step-up / Block → dashboard and audit trail.

| Component | Responsibility |
| --- | --- |
| Telephony pipeline | Decode Twilio frames, convert audio, simulate the phone codec path, buffer windows. |
| SPOOF detector | Pretrained AASIST using compatible ASVspoof 2019 LA weights. |
| REPLAY detector | Project-trained classifier using acoustic features from live and speaker-replayed clips. |
| SPEAKER detector | SpeechBrain ECAPA-TDNN embeddings and cosine similarity to an enrolled voiceprint. |
| Risk engine | Weighted detector fusion, context adjustments, sustained-evidence rule and explanation. |
| Twilio response layer | Continue calls, initiate step-up authentication, terminate high-risk calls. |
| Dashboard and audit | Live risk display, detector reasons, alerts, analytics and hash-chained decision records. |

3. Proposed Repository Structure

```text
voiceguard/
├── README.md
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .env.example
├── config/
│   └── settings.yaml
├── models/
│   ├── spoof.py
│   ├── speaker.py
│   ├── replay.py
│   └── artifacts/                 # downloaded/trained weights; not committed
├── server/
│   ├── app.py
│   ├── telephony.py
│   ├── preprocessing.py
│   ├── streaming.py
│   ├── risk_engine.py
│   ├── responses.py
│   ├── enrollment.py
│   ├── storage.py
│   └── audit.py
├── dashboard/
│   └── index.html
├── data/
│   ├── genuine/
│   ├── cloned/
│   ├── replay/
│   ├── phone_simulated/
│   └── metadata/
├── scripts/
│   ├── vg.ps1
│   ├── download_models.py
│   ├── record_samples.py
│   ├── prepare_data.py
│   ├── train_replay.py
│   ├── enroll.py
│   ├── eval.py
│   ├── sim_call.py
│   └── verify_audit.py
└── tests/
    ├── test_telephony.py
    ├── test_preprocessing.py
    ├── test_spoof.py
    ├── test_speaker.py
    ├── test_replay.py
    ├── test_risk_engine.py
    ├── test_encryption.py
    ├── test_audit.py
    └── test_streaming.py
`

4. Phase 1 — Environment and Pretrained Models

Objective: establish a reproducible Windows environment and confirm that both pretrained models perform actual inference.

Install Python 3.10+, uv, Git and FFmpeg.

Initialize the repository and create the virtual environment with uv.

Install CPU-compatible dependencies and record package versions.

Obtain the AASIST implementation and compatible ASVspoof 2019 LA checkpoint.

Load SpeechBrain ECAPA-TDNN and test embeddings from two speakers.

Run initial AASIST inference on bonafide and spoof audio; record raw outputs and preprocessing assumptions.

Dependencies: torch, torchaudio, librosa, soundfile, scipy, numpy, scikit-learn, speechbrain, fastapi, uvicorn[standard], websockets, cryptography, python-dotenv, twilio, pytest, and WebRTC VAD or a compatible alternative.

Acceptance gate

Environment installation succeeds and FFmpeg is detected.

AASIST loads and produces real scores for genuine and spoof clips.

ECAPA produces real embeddings; same-speaker similarity exceeds different-speaker similarity in the initial sanity test, subject to sample limitations.

Actual commands, outputs, versions and failures are recorded.

Fallback: if checkpoint access, architecture compatibility or Windows dependencies fail, isolate the issue and use a smaller permitted subset where possible. Do not substitute a fake detector.


### As Built vs Planned — Phase 1 Deviations
- **SPOOF (AASIST) Disabled in Production**: Pretrained AASIST model was successfully integrated and performs real inference. However, on consumer smartphone and laptop microphone audio, AASIST exhibits severe acoustic domain shift, classifying bonafide speech as 0.92–0.99 spoof probability. The underlying physical/acoustic cause is unmeasured (`cause not measured`). Consequently, SPOOF is disabled (`weight: 0.0`) in production.
- **Evidence**: `scratch/audit_spoof_orientation.py`, `models/spoof.py`, `config/settings.yaml`.


### As Built vs Planned — Phase 1 Deviations
- **SPOOF (AASIST) Disabled in Production**: Pretrained AASIST model was successfully integrated and performs real inference. However, on consumer smartphone and laptop microphone audio, AASIST exhibits severe acoustic domain shift, classifying bonafide speech as 0.92–0.99 spoof probability. The underlying physical/acoustic cause is unmeasured (`cause not measured`). Consequently, SPOOF is disabled (`weight: 0.0`) in production.
- **Evidence**: `scratch/audit_spoof_orientation.py`, `models/spoof.py`, `config/settings.yaml`.


### As Built vs Planned — Phase 1 Deviations
- **SPOOF (AASIST) Disabled in Production**: Pretrained AASIST model was successfully integrated and performs real inference. However, on consumer smartphone and laptop microphone audio, AASIST exhibits severe acoustic domain shift, classifying bonafide speech as 0.92–0.99 spoof probability. The underlying physical/acoustic cause is unmeasured (`cause not measured`). Consequently, SPOOF is disabled (`weight: 0.0`) in production.
- **Evidence**: `scratch/audit_spoof_orientation.py`, `models/spoof.py`, `config/settings.yaml`.


### As Built vs Planned — Phase 1 Deviations
- **SPOOF (AASIST) Disabled in Production**: Pretrained AASIST model was successfully integrated and performs real inference. However, on consumer smartphone and laptop microphone audio, AASIST exhibits severe acoustic domain shift, classifying bonafide speech as 0.92–0.99 spoof probability. The underlying physical/acoustic cause is unmeasured (`cause not measured`). Consequently, SPOOF is disabled (`weight: 0.0`) in production.
- **Evidence**: `scratch/audit_spoof_orientation.py`, `models/spoof.py`, `config/settings.yaml`.


### As Built vs Planned — Phase 1 Deviations
- **SPOOF (AASIST) Disabled in Production**: Pretrained AASIST model was successfully integrated and performs real inference. However, on consumer smartphone and laptop microphone audio, AASIST exhibits severe acoustic domain shift, classifying bonafide speech as 0.92–0.99 spoof probability. The underlying physical/acoustic cause is unmeasured (`cause not measured`). Consequently, SPOOF is disabled (`weight: 0.0`) in production.
- **Evidence**: `scratch/audit_spoof_orientation.py`, `models/spoof.py`, `config/settings.yaml`.

5. Phase 2 — Telephony Pipeline and Dataset Preparation

5.1 Twilio audio conversion

Twilio Media Streams sends audio payloads in WebSocket JSON events. For the standard telephony stream, audio is mono, 8 kHz G.711 μ-law. The server extracts the base64 payload, decodes μ-law to PCM, resamples to 16 kHz and converts to float32 mono.

Extract the audio payload from the Twilio media event.

Base64-decode the payload.

Decode G.711 μ-law to PCM samples at 8 kHz.

Resample to 16 kHz.

Convert to float32 mono and apply validated amplitude handling.

Append samples to an in-memory rolling buffer.

The offline simulator will apply: WAV → mono → 8 kHz → μ-law encode/decode → 16 kHz → float32. This reproduces the codec path but not all real-world acoustic effects.

5.2 Dataset preparation

| Dataset | Initial target | Collection method / label |
| --- | --- | --- |
| Genuine live | 6–10+ clips | Consented recordings of Gokul's voice; label genuine_live; keep enrollment audio separate. |
| Cloned direct | 6+ clips | Authorized synthetic speech clips; label cloned_direct and record generation method. |
| Genuine replay | 6+ clips | Play genuine clips through a speaker and record through the phone; label genuine_replay. |
| Cloned replay | 6+ clips | Play cloned clips through a speaker and record through the phone; label cloned_replay. |

Store original recordings separately from phone-simulated versions.

Record metadata such as source, label, duration, sample rate and recording conditions.

Create simulated-phone versions for every original sample.

Do not treat codec simulation as equivalent to speaker playback: replay recordings capture acoustic channel, speaker, microphone and room effects.

Acceptance gate

μ-law round-trip and resampling tests pass.

Dataset counts are printed and minimum counts are met.

Every original sample has a corresponding phone-simulated version.

Metadata and labels match the actual recordings.

Privacy: live calls are processed in memory and are not saved as raw audio. Only deliberately collected offline training and evaluation recordings are stored.


### As Built vs Planned — Phase 2 Deviations
- **Phone-Live Dataset Limitation**: The 18 phone-live clips collected in Step 7 (`data/phone_live/`) represent 18 slices of ONE WhatsApp voice-note recording from one phone in one room. They are not independent clips; the effective sample size is approximately 1. The zero false-positive result on these slices is weak evidence of field robustness.
- **Replay Detector Acoustic Confound**: The acoustic replay detector was trained on 40 clips recorded with a single phone and a single loudspeaker. It cannot be ruled out that the model distinguishes hardware/transducer coloration rather than generalized replay acoustics.
- **Evidence**: `data/metadata/manifest.json`, `data/phone_live/`, `models/replay.py`.


### As Built vs Planned — Phase 2 Deviations
- **Phone-Live Dataset Limitation**: The 18 phone-live clips collected in Step 7 (`data/phone_live/`) represent 18 slices of ONE WhatsApp voice-note recording from one phone in one room. They are not independent clips; the effective sample size is approximately 1. The zero false-positive result on these slices is weak evidence of field robustness.
- **Replay Detector Acoustic Confound**: The acoustic replay detector was trained on 40 clips recorded with a single phone and a single loudspeaker. It cannot be ruled out that the model distinguishes hardware/transducer coloration rather than generalized replay acoustics.
- **Evidence**: `data/metadata/manifest.json`, `data/phone_live/`, `models/replay.py`.


### As Built vs Planned — Phase 2 Deviations
- **Phone-Live Dataset Limitation**: The 18 phone-live clips collected in Step 7 (`data/phone_live/`) represent 18 slices of ONE WhatsApp voice-note recording from one phone in one room. They are not independent clips; the effective sample size is approximately 1. The zero false-positive result on these slices is weak evidence of field robustness.
- **Replay Detector Acoustic Confound**: The acoustic replay detector was trained on 40 clips recorded with a single phone and a single loudspeaker. It cannot be ruled out that the model distinguishes hardware/transducer coloration rather than generalized replay acoustics.
- **Evidence**: `data/metadata/manifest.json`, `data/phone_live/`, `models/replay.py`.


### As Built vs Planned — Phase 2 Deviations
- **Phone-Live Dataset Limitation**: The 18 phone-live clips collected in Step 7 (`data/phone_live/`) represent 18 slices of ONE WhatsApp voice-note recording from one phone in one room. They are not independent clips; the effective sample size is approximately 1. The zero false-positive result on these slices is weak evidence of field robustness.
- **Replay Detector Acoustic Confound**: The acoustic replay detector was trained on 40 clips recorded with a single phone and a single loudspeaker. It cannot be ruled out that the model distinguishes hardware/transducer coloration rather than generalized replay acoustics.
- **Evidence**: `data/metadata/manifest.json`, `data/phone_live/`, `models/replay.py`.


### As Built vs Planned — Phase 2 Deviations
- **Phone-Live Dataset Limitation**: The 18 phone-live clips collected in Step 7 (`data/phone_live/`) represent 18 slices of ONE WhatsApp voice-note recording from one phone in one room. They are not independent clips; the effective sample size is approximately 1. The zero false-positive result on these slices is weak evidence of field robustness.
- **Replay Detector Acoustic Confound**: The acoustic replay detector was trained on 40 clips recorded with a single phone and a single loudspeaker. It cannot be ruled out that the model distinguishes hardware/transducer coloration rather than generalized replay acoustics.
- **Evidence**: `data/metadata/manifest.json`, `data/phone_live/`, `models/replay.py`.

6. Phase 3 — Three Detectors, Enrollment and Risk Engine

6.1 SPOOF — AASIST

Use pretrained AASIST with a compatible ASVspoof 2019 LA checkpoint. Apply checkpoint-compatible preprocessing, score four-second windows, validate output orientation and track inference latency. Output: spoof_prob in [0, 1], where a high value represents stronger spoof evidence only after this mapping is verified.

6.2 REPLAY — Project-trained classifier

Start with logistic regression using log-mel or LFCC features and acoustic statistics. Features may include frequency-band energy ratios, spectral rolloff, spectral flatness, noise-floor estimates and reverberation/channel cues.

Read genuine live and speaker-replayed recordings.

Apply the phone-simulation pipeline.

Extract acoustic features.

Split by original recording before selecting or creating windows.

Train on the training split and evaluate only on held-out recordings.

Save the classifier and its preprocessing configuration.

Output: replay_prob in [0, 1]. This initial model is specific to the collected speakers, devices and recording environment; it is not a general-purpose replay detector.

6.3 SPEAKER — ECAPA-TDNN

Request explicit consent before enrollment.

Create an ECAPA embedding from a suitable clean enrollment recording.

Encrypt the embedding with AES-256-GCM and store it locally.

For incoming speech, compute an embedding using the same model and compatible preprocessing.

Compare with the enrolled embedding using cosine similarity.

Output: speaker_sim. Cosine similarity is not automatically a probability; evaluate genuine and impostor score distributions and select a threshold based on available data.

6.4 Risk engine

Initial fusion formula:

Base risk = 0.4 × spoof_prob + 0.3 × (1 − speaker_sim) + 0.3 × replay_prob

The speaker similarity must be mapped to a validated range suitable for the formula. Context adjustments include action sensitivity (e.g., balance check vs wire transfer), caller number not on the allow-list and configured call-time anomalies. Keep detector evidence separate from context adjustments.

| Base risk | Initial band |
| --- | --- |
| Below 0.30 | LOW |
| 0.30 through 0.60 | MEDIUM |
| Above 0.60 | HIGH |

Use a configurable sustained-evidence rule to prevent one noisy window from triggering a disruptive action. Explanations should show exact weighted contributions and each context adjustment.

Acceptance gate

All three detectors produce real outputs, with shape/range/error tests.

Encryption round-trip tests pass; invalid keys and modified ciphertext are rejected.

Risk contributions, context adjustments and decision bands behave as configured.

Evaluation covers genuine live, genuine replayed, cloned direct and cloned replayed scenarios.

Target: at least 90% fused classification accuracy on the held-out phone-simulated set, with genuine live = Allow and cloned/replayed attacks = not Allow. This is a target, not a guarantee.

If the target fails, report actual results, identify weak detectors, collect more data or tune features/thresholds. Never fabricate accuracy.


### As Built vs Planned — Phase 3 Deviations
- **Production Fusion Weights & Post-Hoc Selection**: Planned fusion weights were `0.4` SPOOF / `0.3` SPEAKER / `0.3` REPLAY. In production, Config 2 is used with weights `0.0` SPOOF / `0.5` SPEAKER / `0.5` REPLAY. The decision to disable SPOOF was made after observing evaluation results; reported cross-validation accuracy is therefore an optimistic post-hoc selection.
- **Linear Speaker Calibration Fit on All Data**: The linear speaker mapping parameters `(a = 0.3364, b = 0.4169)` were fitted on all 40 phone-simulated evaluation clips without a held-out estimate.
- **Sustained-Evidence Rule on Both Bands**: Decision bands apply to final fused risk. The sustained-evidence rule requires 3 consecutive qualifying windows before triggering either MEDIUM (Step-Up) or HIGH (Block).
- **Configuration File Split**: Configuration is split into `config/settings.yaml` (hashed whole, strictly matching `scratch/fused_eval.json` hash `ea7f4e3d...`) and `config/live.yaml` (telephony operational settings with a separate hash).
- **Evidence**: `config/settings.yaml`, `config/live.yaml`, `scratch/fused_eval.json`, `server/risk_engine.py`.


### As Built vs Planned — Phase 3 Deviations
- **Production Fusion Weights & Post-Hoc Selection**: Planned fusion weights were `0.4` SPOOF / `0.3` SPEAKER / `0.3` REPLAY. In production, Config 2 is used with weights `0.0` SPOOF / `0.5` SPEAKER / `0.5` REPLAY. The decision to disable SPOOF was made after observing evaluation results; reported cross-validation accuracy is therefore an optimistic post-hoc selection.
- **Linear Speaker Calibration Fit on All Data**: The linear speaker mapping parameters `(a = 0.3364, b = 0.4169)` were fitted on all 40 phone-simulated evaluation clips without a held-out estimate.
- **Sustained-Evidence Rule on Both Bands**: Decision bands apply to final fused risk. The sustained-evidence rule requires 3 consecutive qualifying windows before triggering either MEDIUM (Step-Up) or HIGH (Block).
- **Configuration File Split**: Configuration is split into `config/settings.yaml` (hashed whole, strictly matching `scratch/fused_eval.json` hash `ea7f4e3d...`) and `config/live.yaml` (telephony operational settings with a separate hash).
- **Evidence**: `config/settings.yaml`, `config/live.yaml`, `scratch/fused_eval.json`, `server/risk_engine.py`.


### As Built vs Planned — Phase 3 Deviations
- **Production Fusion Weights & Post-Hoc Selection**: Planned fusion weights were `0.4` SPOOF / `0.3` SPEAKER / `0.3` REPLAY. In production, Config 2 is used with weights `0.0` SPOOF / `0.5` SPEAKER / `0.5` REPLAY. The decision to disable SPOOF was made after observing evaluation results; reported cross-validation accuracy is therefore an optimistic post-hoc selection.
- **Linear Speaker Calibration Fit on All Data**: The linear speaker mapping parameters `(a = 0.3364, b = 0.4169)` were fitted on all 40 phone-simulated evaluation clips without a held-out estimate.
- **Sustained-Evidence Rule on Both Bands**: Decision bands apply to final fused risk. The sustained-evidence rule requires 3 consecutive qualifying windows before triggering either MEDIUM (Step-Up) or HIGH (Block).
- **Configuration File Split**: Configuration is split into `config/settings.yaml` (hashed whole, strictly matching `scratch/fused_eval.json` hash `ea7f4e3d...`) and `config/live.yaml` (telephony operational settings with a separate hash).
- **Evidence**: `config/settings.yaml`, `config/live.yaml`, `scratch/fused_eval.json`, `server/risk_engine.py`.


### As Built vs Planned — Phase 3 Deviations
- **Production Fusion Weights & Post-Hoc Selection**: Planned fusion weights were `0.4` SPOOF / `0.3` SPEAKER / `0.3` REPLAY. In production, Config 2 is used with weights `0.0` SPOOF / `0.5` SPEAKER / `0.5` REPLAY. The decision to disable SPOOF was made after observing evaluation results; reported cross-validation accuracy is therefore an optimistic post-hoc selection.
- **Linear Speaker Calibration Fit on All Data**: The linear speaker mapping parameters `(a = 0.3364, b = 0.4169)` were fitted on all 40 phone-simulated evaluation clips without a held-out estimate.
- **Sustained-Evidence Rule on Both Bands**: Decision bands apply to final fused risk. The sustained-evidence rule requires 3 consecutive qualifying windows before triggering either MEDIUM (Step-Up) or HIGH (Block).
- **Configuration File Split**: Configuration is split into `config/settings.yaml` (hashed whole, strictly matching `scratch/fused_eval.json` hash `ea7f4e3d...`) and `config/live.yaml` (telephony operational settings with a separate hash).
- **Evidence**: `config/settings.yaml`, `config/live.yaml`, `scratch/fused_eval.json`, `server/risk_engine.py`.


### As Built vs Planned — Phase 3 Deviations
- **Production Fusion Weights & Post-Hoc Selection**: Planned fusion weights were `0.4` SPOOF / `0.3` SPEAKER / `0.3` REPLAY. In production, Config 2 is used with weights `0.0` SPOOF / `0.5` SPEAKER / `0.5` REPLAY. The decision to disable SPOOF was made after observing evaluation results; reported cross-validation accuracy is therefore an optimistic post-hoc selection.
- **Linear Speaker Calibration Fit on All Data**: The linear speaker mapping parameters `(a = 0.3364, b = 0.4169)` were fitted on all 40 phone-simulated evaluation clips without a held-out estimate.
- **Sustained-Evidence Rule on Both Bands**: Decision bands apply to final fused risk. The sustained-evidence rule requires 3 consecutive qualifying windows before triggering either MEDIUM (Step-Up) or HIGH (Block).
- **Configuration File Split**: Configuration is split into `config/settings.yaml` (hashed whole, strictly matching `scratch/fused_eval.json` hash `ea7f4e3d...`) and `config/live.yaml` (telephony operational settings with a separate hash).
- **AASIST Display Modes & Recalibration (Experimental)**: Added `spoof.display_mode` (`off` [default], `real`, `calibrated`) configured in `config/live.yaml` or via `VOICEGUARD_SPOOF_DISPLAY`. In `calibrated` mode, AASIST outputs are recalibrated on project data (weight = -0.259134, intercept = 1.911943) and displayed with neutral chip "EXPERIMENTAL, display only" and disclosure label: "AASIST output recalibrated on project data (optimistic, one speaker). Display only, not used in decision." Crucially, the recalibrated value strictly does not enter the risk engine; fused risk, band, streaks, actions, audit risk fields, and outcome remain 100% byte-identical across all three modes.
- **Evidence**: `config/settings.yaml`, `config/live.yaml`, `scratch/fused_eval.json`, `models/artifacts/spoof_calibration.json`, `server/risk_engine.py`, `server/streaming.py`.

7. Phase 4 — Streaming Server, Twilio Webhooks and Call Control

| Endpoint | Responsibility |
| --- | --- |
| POST /voice | Return TwiML that connects the call to the configured public WSS stream. |
| WS /twilio-ws | Receive media frames, decode and score rolling windows. |
| WS /dashboard-ws | Broadcast detector scores, decisions and alerts. |
| GET /health | Health check. |
| GET /audit | Authorized audit-record retrieval. |
| GET /audit/verify | Verify audit-chain integrity. |
| GET / | Serve the dashboard. |

Validate WebSocket lifecycle and call identifier.

Decode incoming audio payloads and append samples to the rolling buffer.

Run preprocessing and detector inference at the configured hop interval.

Fuse detector outputs with call context and apply the sustained-evidence rule.

Broadcast results to the dashboard and write the decision record.

Trigger Twilio call-control actions when the decision policy requires them.

Response actions

| Decision | Behavior |
| --- | --- |
| LOW — Allow | Keep the call connected and continue monitoring. |
| MEDIUM — Step-up | Transition to a DTMF OTP or challenge flow, validate the result, and reconnect media streaming if authentication succeeds. |
| HIGH — Block | Update the active call to terminate it and log the reason. |

Important Twilio behavior: updating an active call with new TwiML replaces its current instructions. Step-up must explicitly transition to the challenge, collect and validate the result, then re-establish the media stream if authentication succeeds. Test duplicate triggers, race conditions, failures and post-termination behavior.

Acceptance gate

sim_call.py replays audio as Twilio-format frames.

Actual per-window JSON scores and explanations are produced.

Step-up and block triggers are demonstrated.

Audit records are written and the chain verifies.

Per-window latency is reported and stream disconnects are handled.


### As Built vs Planned — Phase 4 Deviations
- **Twilio Live Telephony Untested on Live PSTN**: The complete Twilio Media Stream path was implemented, unit tested, and rehearsed over public ngrok tunnels using a simulated client. However, no live carrier PSTN telephone call was completed; the phone number was not provisioned on the Twilio account.
- **Dry Mode Protection**: Added `live.dry_mode` (`config/live.yaml`) to log and display actions on the SOC dashboard without dispatching REST termination calls during initial bring-up.
- **Mock Step-Up OTP**: Step-up OTP is implemented as an exhibition mock simulation ("MOCK OTP"). The interactive carrier DTMF `<Gather>` flow is untested on live carrier lines.
- **Evidence**: `config/live.yaml`, `server/responses.py`, `tests/test_live_mock_dry_run.py`, `scripts/tunnel_rehearsal.py`.


### As Built vs Planned — Phase 4 Deviations
- **Twilio Live Telephony Untested on Live PSTN**: The complete Twilio Media Stream path was implemented, unit tested, and rehearsed over public ngrok tunnels using a simulated client. However, no live carrier PSTN telephone call was completed; the phone number was not provisioned on the Twilio account.
- **Dry Mode Protection**: Added `live.dry_mode` (`config/live.yaml`) to log and display actions on the SOC dashboard without dispatching REST termination calls during initial bring-up.
- **Mock Step-Up OTP**: Step-up OTP is implemented as an exhibition mock simulation ("MOCK OTP"). The interactive carrier DTMF `<Gather>` flow is untested on live carrier lines.
- **Evidence**: `config/live.yaml`, `server/responses.py`, `tests/test_live_mock_dry_run.py`, `scripts/tunnel_rehearsal.py`.


### As Built vs Planned — Phase 4 Deviations
- **Twilio Live Telephony Untested on Live PSTN**: The complete Twilio Media Stream path was implemented, unit tested, and rehearsed over public ngrok tunnels using a simulated client. However, no live carrier PSTN telephone call was completed; the phone number was not provisioned on the Twilio account.
- **Dry Mode Protection**: Added `live.dry_mode` (`config/live.yaml`) to log and display actions on the SOC dashboard without dispatching REST termination calls during initial bring-up.
- **Mock Step-Up OTP**: Step-up OTP is implemented as an exhibition mock simulation ("MOCK OTP"). The interactive carrier DTMF `<Gather>` flow is untested on live carrier lines.
- **Evidence**: `config/live.yaml`, `server/responses.py`, `tests/test_live_mock_dry_run.py`, `scripts/tunnel_rehearsal.py`.


### As Built vs Planned — Phase 4 Deviations
- **Twilio Live Telephony Untested on Live PSTN**: The complete Twilio Media Stream path was implemented, unit tested, and rehearsed over public ngrok tunnels using a simulated client. However, no live carrier PSTN telephone call was completed; the phone number was not provisioned on the Twilio account.
- **Dry Mode Protection**: Added `live.dry_mode` (`config/live.yaml`) to log and display actions on the SOC dashboard without dispatching REST termination calls during initial bring-up.
- **Mock Step-Up OTP**: Step-up OTP is implemented as an exhibition mock simulation ("MOCK OTP"). The interactive carrier DTMF `<Gather>` flow is untested on live carrier lines.
- **Evidence**: `config/live.yaml`, `server/responses.py`, `tests/test_live_mock_dry_run.py`, `scripts/tunnel_rehearsal.py`.


### As Built vs Planned — Phase 4 Deviations
- **Twilio Live Telephony Untested on Live PSTN**: The complete Twilio Media Stream path was implemented, unit tested, and rehearsed over public ngrok tunnels using a simulated client. However, no live carrier PSTN telephone call was completed; the phone number was not provisioned on the Twilio account.
- **Dry Mode Protection**: Added `live.dry_mode` (`config/live.yaml`) to log and display actions on the SOC dashboard without dispatching REST termination calls during initial bring-up.
- **Mock Step-Up OTP**: Step-up OTP is implemented as an exhibition mock simulation ("MOCK OTP"). The interactive carrier DTMF `<Gather>` flow is untested on live carrier lines.
- **Evidence**: `config/live.yaml`, `server/responses.py`, `tests/test_live_mock_dry_run.py`, `scripts/tunnel_rehearsal.py`.

8. Phase 5 — Live Dashboard

Build dashboard/index.html with vanilla JavaScript and serve it through FastAPI.

Large risk meter with green/amber/red status.

Allow / Step-up / Block decision label.

Three detector indicators: spoof probability, speaker match and replay probability.

Human-readable explanation with weighted contributions and context adjustments.

Scrolling alert log.

Audit-trail table with timestamp, call SID, scores, context, risk, decision and explanation.

Analytics: counts of Allow/Step-up/Block, average risk and calls screened.

Action-sensitivity selection for the current call, validated by the server.

Acceptance gate

Dashboard updates every second when driven by sim_call.py.

All detector indicators and decision explanations update.

Three demo scenarios can be displayed.

Audit records and analytics are consistent.

Browser refresh and WebSocket reconnection are tested.


### As Built vs Planned — Phase 5 Deviations
- **Exhibition Simulation Demo Mode Added**: Added dedicated `/demo/*` endpoints in `server/demo.py` and an interactive demo controller panel in `dashboard/index.html`. Streams allowlisted evaluation clips through the full real-time pipeline with fixed banner: `SIMULATION, not a live call`.
- **Evidence**: `server/demo.py`, `dashboard/index.html`, `tests/test_dashboard_demo_gate.py`.


### As Built vs Planned — Phase 5 Deviations
- **Exhibition Simulation Demo Mode Added**: Added dedicated `/demo/*` endpoints in `server/demo.py` and an interactive demo controller panel in `dashboard/index.html`. Streams allowlisted evaluation clips through the full real-time pipeline with fixed banner: `SIMULATION, not a live call`.
- **Upload Analysis Mode Added**: Upload analysis mode added for exhibition; not part of the original plan; not a validated evaluation.
- **Evidence**: `server/demo.py`, `server/upload.py`, `dashboard/index.html`, `tests/test_dashboard_upload_gate.py`.


### As Built vs Planned — Phase 5 Deviations
- **Exhibition Simulation Demo Mode Added**: Added dedicated `/demo/*` endpoints in `server/demo.py` and an interactive demo controller panel in `dashboard/index.html`. Streams allowlisted evaluation clips through the full real-time pipeline with fixed banner: `SIMULATION, not a live call`.
- **Upload Analysis Mode Added**: Upload analysis mode added for exhibition; not part of the original plan; not a validated evaluation.
- **Three-Path Streaming Consistency Aligned**: Window triggering threshold in `server/demo.py` was aligned from `< 640` to `< 320` samples residue to match `eval_streaming.py` and `server/upload.py`. All three streaming execution paths now evaluate identical 1.0s window cadences and produce concordant outcomes across evaluation scenarios.
- **Evidence**: `server/demo.py`, `server/upload.py`, `scripts/eval_streaming.py`, `tests/test_path_consistency.py`.


### As Built vs Planned — Phase 5 Deviations
- **Exhibition Simulation Demo Mode Added**: Added dedicated `/demo/*` endpoints in `server/demo.py` and an interactive demo controller panel in `dashboard/index.html`. Streams allowlisted evaluation clips through the full real-time pipeline with fixed banner: `SIMULATION, not a live call`.
- **Upload Analysis Mode Added**: Upload analysis mode added for exhibition; not part of the original plan; not a validated evaluation.
- **Three-Path Streaming Consistency Aligned**: Window triggering threshold in `server/demo.py` was aligned from `< 640` to `< 320` samples residue to match `eval_streaming.py` and `server/upload.py`. All three streaming execution paths now evaluate identical 1.0s window cadences and produce concordant outcomes across evaluation scenarios.
- **Superseded Prior Demo Results**: Demo results before the window-cadence fix (demo.py < 640) are invalid and superseded.
- **Evidence**: `server/demo.py`, `server/upload.py`, `scripts/eval_streaming.py`, `tests/test_path_consistency.py`.


### As Built vs Planned — Phase 5 Deviations
- **Exhibition Simulation Demo Mode Added**: Added dedicated `/demo/*` endpoints in `server/demo.py` and an interactive demo controller panel in `dashboard/index.html`. Streams allowlisted evaluation clips through the full real-time pipeline with fixed banner: `SIMULATION, not a live call`.
- **Upload Analysis Mode Added**: Upload analysis mode added for exhibition; not part of the original plan; not a validated evaluation.
- **Three-Path Streaming Consistency Aligned**: Window triggering threshold in `server/demo.py` was aligned from `< 640` to `< 320` samples residue to match `eval_streaming.py` and `server/upload.py`. All three streaming execution paths now evaluate identical 1.0s window cadences and produce concordant outcomes across evaluation scenarios.
- **Superseded Prior Demo Results**: Demo results before the window-cadence fix (demo.py < 640) are invalid and superseded.
- **Evidence**: `server/demo.py`, `server/upload.py`, `scripts/eval_streaming.py`, `tests/test_path_consistency.py`.

9. Phase 6 — Security, Privacy and Audit Integrity

Voiceprint protection

Require explicit consent before enrollment.

Encrypt the voiceprint embedding using AES-256-GCM.

Load the encryption key from .env; never commit it.

Keep decrypted material in memory only when needed.

Live audio privacy

Keep live call audio and rolling buffers in memory.

Do not write raw live audio or payloads to disk or logs.

Log only necessary detector scores, decisions, timestamps, context and explanations.

Keep offline training data separate from live-call processing.

Hash-chained audit

Each record will include timestamp, call SID, detector scores, context, risk, band, decision, explanation, previous_hash and record_hash. Hash a canonical record representation together with the previous hash. A verifier should detect edits, missing records within the chain and reordered records. A hash chain alone cannot prevent a privileged attacker from rewriting the entire chain; access control and storage protection remain necessary.

Acceptance gate

Voiceprint encryption/decryption succeeds.

Invalid keys and altered ciphertext are rejected.

Audit chain verifies and deliberate test tampering is detected.

No credentials, raw live audio or voiceprints appear in logs or Git.


### As Built vs Planned — Phase 6 Deviations
- **Archived Audit Log**: An earlier automated agent action truncated `data/audit/audit_log.jsonl` to 40 records. To preserve forensic integrity, the truncated file was archived to `data/audit/archive_20261003_024646.jsonl` and a fresh, fully valid hash chain was initialized.
- **Evidence**: `data/audit/archive_20261003_024646.jsonl`, `server/audit.py`, `tests/test_audit.py`.


### As Built vs Planned — Phase 6 Deviations
- **Archived Audit Log**: An earlier automated agent action truncated `data/audit/audit_log.jsonl` to 40 records. To preserve forensic integrity, the truncated file was archived to `data/audit/archive_20261003_024646.jsonl` and a fresh, fully valid hash chain was initialized.
- **Evidence**: `data/audit/archive_20261003_024646.jsonl`, `server/audit.py`, `tests/test_audit.py`.


### As Built vs Planned — Phase 6 Deviations
- **Archived Audit Log**: An earlier automated agent action truncated `data/audit/audit_log.jsonl` to 40 records. To preserve forensic integrity, the truncated file was archived to `data/audit/archive_20261003_024646.jsonl` and a fresh, fully valid hash chain was initialized.
- **Evidence**: `data/audit/archive_20261003_024646.jsonl`, `server/audit.py`, `tests/test_audit.py`.


### As Built vs Planned — Phase 6 Deviations
- **Archived Audit Log**: An earlier automated agent action truncated `data/audit/audit_log.jsonl` to 40 records. To preserve forensic integrity, the truncated file was archived to `data/audit/archive_20261003_024646.jsonl` and a fresh, fully valid hash chain was initialized.
- **Evidence**: `data/audit/archive_20261003_024646.jsonl`, `server/audit.py`, `tests/test_audit.py`.


### As Built vs Planned — Phase 6 Deviations
- **Archived Audit Log**: An earlier automated agent action truncated `data/audit/audit_log.jsonl` to 40 records. To preserve forensic integrity, the truncated file was archived to `data/audit/archive_20261003_024646.jsonl` and a fresh, fully valid hash chain was initialized.
- **Evidence**: `data/audit/archive_20261003_024646.jsonl`, `server/audit.py`, `tests/test_audit.py`.

10. Phase 7 — Evaluation, Live Integration and Rehearsal

Evaluation methodology

Use phone-simulated WAVs for the primary evaluation.

Keep clips from the same original recording in the same data split.

Report per-detector results and fused decision accuracy.

Report confusion matrix, precision, recall, F1, false-positive and false-negative counts where meaningful.

Run fusion-weight and threshold sweeps.

Report sample counts, average and percentile latency, and per-scenario results.

Disclose that results come from a small custom dataset and may not generalize to unseen speakers, devices, rooms or cloning methods.

Live Twilio bring-up

Configure the Twilio account and phone number.

Verify required phone numbers if using a trial account.

Start the local server and public HTTPS/WSS tunnel.

Configure the voice webhook URL.

Confirm that Twilio can reach the endpoint.

Place a test call and verify streaming, dashboard updates and audit records.

Test step-up transition and call termination.

If Twilio account restrictions, networking or tunnel failures prevent a real call, use sim_call.py as a clearly labeled fallback rather than claiming a live telephony test succeeded.

Three demo scenarios

| Scene | Test | Expected behavior (subject to measured scores) |
| --- | --- | --- |
| 1 — Genuine caller | Enrolled voice on a normal call | LOW / Allow |
| 2 — Borderline call | Borderline sample or sensitive action context | MEDIUM / Step-up; pass then continue |
| 3 — Replayed clone | Authorized cloned voice played through speaker and captured by phone | HIGH / Block if sustained evidence supports it |

Prepare a three-run checklist using the actual phone and speaker in a noisy room.

Prepare a screen-recording backup.

Prepare Q&A covering models, measured results, dataset limitations, privacy and audit integrity.


### As Built vs Planned — Phase 7 Deviations
- **Streaming-Level Evaluation Results (Step 3)**:
  - Genuine Live (n=10): 8 Allow, 2 Step-Up only, 0 Block (80.0% Match | Wilson 95% CI: [49.02%, 94.33%]). False step-up rate = 20.0%.
  - Cloned Direct (n=10): 7 Allow, 3 Step-Up only, 0 Block (30.0% Match | Wilson 95% CI: [10.78%, 60.32%]). Miss rate = 70.0% (clips too short to sustain 3 consecutive windows above 0.30 threshold).
  - Genuine Replay (n=10): 0 Allow, 1 Step-Up only, 9 Block (100.0% Match | Wilson 95% CI: [72.25%, 100.00%]). Miss rate = 0.0%.
  - Cloned Replay (n=10): 3 Allow, 3 Step-Up only, 4 Block (70.0% Match | Wilson 95% CI: [39.68%, 89.22%]). Miss rate = 30.0%.
  - Overall Streaming Decision Rate = 70.0% (28/40) | Wilson 95% CI: [54.57%, 81.93%].
- **Demo Set Mismatches (Step 2)**:
  - `live_01` (Genuine Live 1): Expected Allow -> Actual: Step-up only (false step-up). Windows 1-6 scored MEDIUM risk before settling to LOW in windows 7-8. Fired MOCK OTP at 6.00s. Cause: `cause not measured`.
  - `live_02` (Genuine Live 2): Expected Allow -> Actual: Step-up only (false step-up). Windows 1-4 scored MEDIUM risk before settling to LOW in windows 5-10. Fired MOCK OTP at 6.00s. Cause: `cause not measured`.
- **Evidence**: `scratch/streaming_eval.json`, `scripts/run_demo_set.py`.


### As Built vs Planned — Phase 7 Deviations
- **Streaming-Level Evaluation Results (Step 3)**:
  - Genuine Live (n=10): 8 Allow, 2 Step-Up only, 0 Block (80.0% Match | Wilson 95% CI: [49.02%, 94.33%]). False step-up rate = 20.0%.
  - Cloned Direct (n=10): 7 Allow, 3 Step-Up only, 0 Block (30.0% Match | Wilson 95% CI: [10.78%, 60.32%]). Miss rate = 70.0% (clips too short to sustain 3 consecutive windows above 0.30 threshold).
  - Genuine Replay (n=10): 0 Allow, 1 Step-Up only, 9 Block (100.0% Match | Wilson 95% CI: [72.25%, 100.00%]). Miss rate = 0.0%.
  - Cloned Replay (n=10): 3 Allow, 3 Step-Up only, 4 Block (70.0% Match | Wilson 95% CI: [39.68%, 89.22%]). Miss rate = 30.0%.
  - Overall Streaming Decision Rate = 70.0% (28/40) | Wilson 95% CI: [54.57%, 81.93%].
- **Demo Set Mismatches (Step 2)**:
  - `live_01` (Genuine Live 1): Expected Allow -> Actual: Step-up only (false step-up). Windows 1-6 scored MEDIUM risk before settling to LOW in windows 7-8. Fired MOCK OTP at 6.00s. Cause: `cause not measured`.
  - `live_02` (Genuine Live 2): Expected Allow -> Actual: Step-up only (false step-up). Windows 1-4 scored MEDIUM risk before settling to LOW in windows 5-10. Fired MOCK OTP at 6.00s. Cause: `cause not measured`.
- **Evidence**: `scratch/streaming_eval.json`, `scripts/run_demo_set.py`.


### As Built vs Planned — Phase 7 Deviations
- **Streaming-Level Evaluation Results (Step 3)**:
  - Genuine Live (n=10): 8 Allow, 2 Step-Up only, 0 Block (80.0% Match | Wilson 95% CI: [49.02%, 94.33%]). False step-up rate = 20.0%.
  - Cloned Direct (n=10): 7 Allow, 3 Step-Up only, 0 Block (30.0% Match | Wilson 95% CI: [10.78%, 60.32%]). Miss rate = 70.0% (clips too short to sustain 3 consecutive windows above 0.30 threshold).
  - Genuine Replay (n=10): 0 Allow, 1 Step-Up only, 9 Block (100.0% Match | Wilson 95% CI: [72.25%, 100.00%]). Miss rate = 0.0%.
  - Cloned Replay (n=10): 3 Allow, 3 Step-Up only, 4 Block (70.0% Match | Wilson 95% CI: [39.68%, 89.22%]). Miss rate = 30.0%.
  - Overall Streaming Decision Rate = 70.0% (28/40) | Wilson 95% CI: [54.57%, 81.93%].
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


### As Built vs Planned — Phase 7 Deviations
- **Streaming-Level Evaluation Results (Step 3)**:
  - Genuine Live (n=10): 8 Allow, 2 Step-Up only, 0 Block (80.0% Match | Wilson 95% CI: [49.02%, 94.33%]). False step-up rate = 20.0%.
  - Cloned Direct (n=10): 7 Allow, 3 Step-Up only, 0 Block (30.0% Match | Wilson 95% CI: [10.78%, 60.32%]). Miss rate = 70.0% (clips too short to sustain 3 consecutive windows above 0.30 threshold).
  - Genuine Replay (n=10): 0 Allow, 1 Step-Up only, 9 Block (100.0% Match | Wilson 95% CI: [72.25%, 100.00%]). Miss rate = 0.0%.
  - Cloned Replay (n=10): 3 Allow, 3 Step-Up only, 4 Block (70.0% Match | Wilson 95% CI: [39.68%, 89.22%]). Miss rate = 30.0%.
  - Overall Streaming Decision Rate = 70.0% (28/40) | Wilson 95% CI: [54.57%, 81.93%].
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


### As Built vs Planned — Phase 7 Deviations
- **Streaming-Level Evaluation Results (Step 3)**:
  - Genuine Live (n=10): 8 Allow, 2 Step-Up only, 0 Block (80.0% Match | Wilson 95% CI: [49.02%, 94.33%]). False step-up rate = 20.0%.
  - Cloned Direct (n=10): 7 Allow, 3 Step-Up only, 0 Block (30.0% Match | Wilson 95% CI: [10.78%, 60.32%]). Miss rate = 70.0% (clips too short to sustain 3 consecutive windows above 0.30 threshold).
  - Genuine Replay (n=10): 0 Allow, 1 Step-Up only, 9 Block (100.0% Match | Wilson 95% CI: [72.25%, 100.00%]). Miss rate = 0.0%.
  - Cloned Replay (n=10): 3 Allow, 3 Step-Up only, 4 Block (70.0% Match | Wilson 95% CI: [39.68%, 89.22%]). Miss rate = 30.0%.
  - Overall Streaming Decision Rate = 70.0% (28/40) | Wilson 95% CI: [54.57%, 81.93%].
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

11. Configuration Design

| Setting | Purpose |
| --- | --- |
| Detector window length | Duration required by each detector. |
| Hop interval | How often a new window is scored. |
| VAD thresholds | Minimum speech content for scoring. |
| Fusion weights | Relative detector contributions. |
| Risk bands | LOW, MEDIUM and HIGH thresholds. |
| Context adjustments | Action sensitivity, allow-list and call-time signals. |
| Sustained-evidence count | Number of qualifying windows required before escalation. |
| Step-up settings | Challenge type, timeout, retries and result policy. |
| Latency limits | Performance monitoring and fallback behavior. |
| Audio buffering | Memory limits and stream-disconnect behavior. |

Keep all thresholds and operational settings in config/settings.yaml. Save the final evaluated configuration with the evaluation results.

12. PowerShell Command Interface

| Command | Purpose |
| --- | --- |
| .\scripts\vg.ps1 setup | Set up environment and validate dependencies. |
| .\scripts\vg.ps1 test | Run unit and integration tests. |
| .\scripts\vg.ps1 eval | Run held-out evaluation. |
| .\scripts\vg.ps1 serve | Start FastAPI and the dashboard. |
| .\scripts\vg.ps1 tunnel | Start the public tunnel. |
| .\scripts\vg.ps1 demo | Launch the local demo workflow. |

Document exact invocation syntax and expected output in README.md.

13. Phase-by-Phase Approval Workflow

Review the intended changes before implementation.

Implement only the current phase.

Run its acceptance gate.

Show the actual commands and their output.

If the gate fails, explain the failure, apply the fallback and rerun the gate.

Commit only after the phase passes.

Wait for explicit user approval before beginning the next phase.

No secrets will be committed. .env.example contains placeholders only. Docker, Redis, PostgreSQL, React, ONNX and SHAP are out of scope unless explicitly requested.

14. Final Acceptance Criteria — Operational Verdict

| Acceptance Criterion | Verdict | Evidence & Verification |
| :--- | :--- | :--- |
| **All three detectors perform real inference** | **MET WITH LIMITS** | ECAPA and Replay active in production. AASIST produces real inference on GPU/CPU but is disabled in production due to measured domain shift (`cause not measured`). Verified in `tests/test_spoof.py`. |
| **Telephony simulator reproduces intended codec path** | **MET** | Verified 8kHz G.711 $\mu$-law round-trip and polyphase resampling against Python `audioop` reference across all 256 code points. Verified in `tests/test_telephony.py`. |
| **Risk engine produces explainable decisions** | **MET** | Fused risk computes weighted detector contributions, context adjustments, and sustained-window escalation rules with human-readable breakdowns. Verified in `tests/test_risk_engine.py`. |
| **Step-up authentication and call blocking work** | **MET WITH LIMITS** | Blocking and step-up work reliably in software simulation and mock dispatcher. Outbound carrier DTMF IVR challenge is untested on live PSTN lines. Verified in `tests/test_live_mock_dry_run.py`. |
| **Dashboard receives live decision updates** | **MET** | Vanilla JS dashboard connects to `/dashboard-ws`, receiving per-window scores, timeline strips, and audit records with auto-reconnection. Verified in `tests/test_dashboard_demo_gate.py`. |
| **Voiceprint is encrypted at rest** | **MET** | AES-256-GCM encryption with 12-byte random nonce and authenticated speaker ID. Plaintext embeddings are memory-only. Verified in `tests/test_encryption.py`. |
| **Live audio remains in memory** | **MET** | Audio streaming buffers remain exclusively in RAM. No raw audio, PCM chunks, or voiceprints are written to disk or logs. Verified in `scripts/step8_privacy_audit.py`. |
| **Audit verifier detects tampering** | **MET** | SHA-256 cryptographic hash chain validates all historical scoring events and successfully detects record deletion, modification, or reordering. Verified in `tests/test_audit.py`. |
| **Evaluation uses held-out data with full disclosures** | **MET WITH LIMITS** | 5-fold cross-validation conducted; post-hoc configuration selection, single-speaker calibration, and streaming-window limitations explicitly disclosed. Verified in `scratch/fused_eval.json`. |
| **Live Twilio demonstration works or fallback identified** | **NOT MET** | Live PSTN carrier demonstration was not executed due to unprovisioned carrier account. Fallback successfully implemented and verified: full real-time software simulation demo labeled `"SIMULATION, not a live call"`. Verified in `tests/test_demo.py`. |
| **Documentation explains limitations, privacy & setup** | **MET** | Comprehensive operational, evaluation, and exhibition guides provided in `docs/EVALUATION.md`, `docs/DEMO_GUIDE.md`, and `docs/LIVE_BRINGUP.md`. |
 — Operational Verdict

| Acceptance Criterion | Verdict | Evidence & Verification |
| :--- | :--- | :--- |
| **All three detectors perform real inference** | **MET WITH LIMITS** | ECAPA and Replay active in production. AASIST produces real inference on GPU/CPU but is disabled in production due to measured domain shift (`cause not measured`). Verified in `tests/test_spoof.py`. |
| **Telephony simulator reproduces intended codec path** | **MET** | Verified 8kHz G.711 $\mu$-law round-trip and polyphase resampling against Python `audioop` reference across all 256 code points. Verified in `tests/test_telephony.py`. |
| **Risk engine produces explainable decisions** | **MET** | Fused risk computes weighted detector contributions, context adjustments, and sustained-window escalation rules with human-readable breakdowns. Verified in `tests/test_risk_engine.py`. |
| **Step-up authentication and call blocking work** | **MET WITH LIMITS** | Blocking and step-up work reliably in software simulation and mock dispatcher. Outbound carrier DTMF IVR challenge is untested on live PSTN lines. Verified in `tests/test_live_mock_dry_run.py`. |
| **Dashboard receives live decision updates** | **MET** | Vanilla JS dashboard connects to `/dashboard-ws`, receiving per-window scores, timeline strips, and audit records with auto-reconnection. Verified in `tests/test_dashboard_demo_gate.py`. |
| **Voiceprint is encrypted at rest** | **MET** | AES-256-GCM encryption with 12-byte random nonce and authenticated speaker ID. Plaintext embeddings are memory-only. Verified in `tests/test_encryption.py`. |
| **Live audio remains in memory** | **MET** | Audio streaming buffers remain exclusively in RAM. No raw audio, PCM chunks, or voiceprints are written to disk or logs. Verified in `scripts/step8_privacy_audit.py`. |
| **Audit verifier detects tampering** | **MET** | SHA-256 cryptographic hash chain validates all historical scoring events and successfully detects record deletion, modification, or reordering. Verified in `tests/test_audit.py`. |
| **Evaluation uses held-out data with full disclosures** | **MET WITH LIMITS** | 5-fold cross-validation conducted; post-hoc configuration selection, single-speaker calibration, and streaming-window limitations explicitly disclosed. Verified in `scratch/fused_eval.json`. |
| **Live Twilio demonstration works or fallback identified** | **NOT MET** | Live PSTN carrier demonstration was not executed due to unprovisioned carrier account. Fallback successfully implemented and verified: full real-time software simulation demo labeled `"SIMULATION, not a live call"`. Verified in `tests/test_demo.py`. |
| **Documentation explains limitations, privacy & setup** | **MET** | Comprehensive operational, evaluation, and exhibition guides provided in `docs/EVALUATION.md`, `docs/DEMO_GUIDE.md`, and `docs/LIVE_BRINGUP.md`. |
 — Operational Verdict

| Acceptance Criterion | Verdict | Evidence & Verification |
| :--- | :--- | :--- |
| **All three detectors perform real inference** | **MET WITH LIMITS** | ECAPA and Replay active in production. AASIST produces real inference on GPU/CPU but is disabled in production due to measured domain shift (`cause not measured`). Verified in `tests/test_spoof.py`. |
| **Telephony simulator reproduces intended codec path** | **MET** | Verified 8kHz G.711 $\mu$-law round-trip and polyphase resampling against Python `audioop` reference across all 256 code points. Verified in `tests/test_telephony.py`. |
| **Risk engine produces explainable decisions** | **MET** | Fused risk computes weighted detector contributions, context adjustments, and sustained-window escalation rules with human-readable breakdowns. Verified in `tests/test_risk_engine.py`. |
| **Step-up authentication and call blocking work** | **MET WITH LIMITS** | Blocking and step-up work reliably in software simulation and mock dispatcher. Outbound carrier DTMF IVR challenge is untested on live PSTN lines. Verified in `tests/test_live_mock_dry_run.py`. |
| **Dashboard receives live decision updates** | **MET** | Vanilla JS dashboard connects to `/dashboard-ws`, receiving per-window scores, timeline strips, and audit records with auto-reconnection. Verified in `tests/test_dashboard_demo_gate.py`. |
| **Voiceprint is encrypted at rest** | **MET** | AES-256-GCM encryption with 12-byte random nonce and authenticated speaker ID. Plaintext embeddings are memory-only. Verified in `tests/test_encryption.py`. |
| **Live audio remains in memory** | **MET** | Audio streaming buffers remain exclusively in RAM. No raw audio, PCM chunks, or voiceprints are written to disk or logs. Verified in `scripts/step8_privacy_audit.py`. |
| **Audit verifier detects tampering** | **MET** | SHA-256 cryptographic hash chain validates all historical scoring events and successfully detects record deletion, modification, or reordering. Verified in `tests/test_audit.py`. |
| **Evaluation uses held-out data with full disclosures** | **MET WITH LIMITS** | 5-fold cross-validation conducted; post-hoc configuration selection, single-speaker calibration, and streaming-window limitations explicitly disclosed. Verified in `scratch/fused_eval.json`. |
| **Live Twilio demonstration works or fallback identified** | **NOT MET** | Live PSTN carrier demonstration was not executed due to unprovisioned carrier account. Fallback successfully implemented and verified: full real-time software simulation demo labeled `"SIMULATION, not a live call"`. Verified in `tests/test_demo.py`. |
| **Documentation explains limitations, privacy & setup** | **MET** | Comprehensive operational, evaluation, and exhibition guides provided in `docs/EVALUATION.md`, `docs/DEMO_GUIDE.md`, and `docs/LIVE_BRINGUP.md`. |
 — Operational Verdict

| Acceptance Criterion | Verdict | Evidence & Verification |
| :--- | :--- | :--- |
| **All three detectors perform real inference** | **MET WITH LIMITS** | ECAPA and Replay active in production. AASIST produces real inference on GPU/CPU but is disabled in production due to measured domain shift (`cause not measured`). Verified in `tests/test_spoof.py`. |
| **Telephony simulator reproduces intended codec path** | **MET** | Verified 8kHz G.711 $\mu$-law round-trip and polyphase resampling against Python `audioop` reference across all 256 code points. Verified in `tests/test_telephony.py`. |
| **Risk engine produces explainable decisions** | **MET** | Fused risk computes weighted detector contributions, context adjustments, and sustained-window escalation rules with human-readable breakdowns. Verified in `tests/test_risk_engine.py`. |
| **Step-up authentication and call blocking work** | **MET WITH LIMITS** | Blocking and step-up work reliably in software simulation and mock dispatcher. Outbound carrier DTMF IVR challenge is untested on live PSTN lines. Verified in `tests/test_live_mock_dry_run.py`. |
| **Dashboard receives live decision updates** | **MET** | Vanilla JS dashboard connects to `/dashboard-ws`, receiving per-window scores, timeline strips, and audit records with auto-reconnection. Verified in `tests/test_dashboard_demo_gate.py`. |
| **Voiceprint is encrypted at rest** | **MET** | AES-256-GCM encryption with 12-byte random nonce and authenticated speaker ID. Plaintext embeddings are memory-only. Verified in `tests/test_encryption.py`. |
| **Live audio remains in memory** | **MET** | Audio streaming buffers remain exclusively in RAM. No raw audio, PCM chunks, or voiceprints are written to disk or logs. Verified in `scripts/step8_privacy_audit.py`. |
| **Audit verifier detects tampering** | **MET** | SHA-256 cryptographic hash chain validates all historical scoring events and successfully detects record deletion, modification, or reordering. Verified in `tests/test_audit.py`. |
| **Evaluation uses held-out data with full disclosures** | **MET WITH LIMITS** | 5-fold cross-validation conducted; post-hoc configuration selection, single-speaker calibration, and streaming-window limitations explicitly disclosed. Verified in `scratch/fused_eval.json`. |
| **Live Twilio demonstration works or fallback identified** | **NOT MET** | Live PSTN carrier demonstration was not executed due to unprovisioned carrier account. Fallback successfully implemented and verified: full real-time software simulation demo labeled `"SIMULATION, not a live call"`. Verified in `tests/test_demo.py`. |
| **Documentation explains limitations, privacy & setup** | **MET** | Comprehensive operational, evaluation, and exhibition guides provided in `docs/EVALUATION.md`, `docs/DEMO_GUIDE.md`, and `docs/LIVE_BRINGUP.md`. |
 — Operational Verdict

| Acceptance Criterion | Verdict | Evidence & Verification |
| :--- | :--- | :--- |
| **All three detectors perform real inference** | **MET WITH LIMITS** | ECAPA and Replay active in production. AASIST produces real inference on GPU/CPU but is disabled in production due to measured domain shift (`cause not measured`). Verified in `tests/test_spoof.py`. |
| **Telephony simulator reproduces intended codec path** | **MET** | Verified 8kHz G.711 $\mu$-law round-trip and polyphase resampling against Python `audioop` reference across all 256 code points. Verified in `tests/test_telephony.py`. |
| **Risk engine produces explainable decisions** | **MET** | Fused risk computes weighted detector contributions, context adjustments, and sustained-window escalation rules with human-readable breakdowns. Verified in `tests/test_risk_engine.py`. |
| **Step-up authentication and call blocking work** | **MET WITH LIMITS** | Blocking and step-up work reliably in software simulation and mock dispatcher. Outbound carrier DTMF IVR challenge is untested on live PSTN lines. Verified in `tests/test_live_mock_dry_run.py`. |
| **Dashboard receives live decision updates** | **MET** | Vanilla JS dashboard connects to `/dashboard-ws`, receiving per-window scores, timeline strips, and audit records with auto-reconnection. Verified in `tests/test_dashboard_demo_gate.py`. |
| **Voiceprint is encrypted at rest** | **MET** | AES-256-GCM encryption with 12-byte random nonce and authenticated speaker ID. Plaintext embeddings are memory-only. Verified in `tests/test_encryption.py`. |
| **Live audio remains in memory** | **MET** | Audio streaming buffers remain exclusively in RAM. No raw audio, PCM chunks, or voiceprints are written to disk or logs. Verified in `scripts/step8_privacy_audit.py`. |
| **Audit verifier detects tampering** | **MET** | SHA-256 cryptographic hash chain validates all historical scoring events and successfully detects record deletion, modification, or reordering. Verified in `tests/test_audit.py`. |
| **Evaluation uses held-out data with full disclosures** | **MET WITH LIMITS** | 5-fold cross-validation conducted; post-hoc configuration selection, single-speaker calibration, and streaming-window limitations explicitly disclosed. Verified in `scratch/fused_eval.json`. |
| **Live Twilio demonstration works or fallback identified** | **NOT MET** | Live PSTN carrier demonstration was not executed due to unprovisioned carrier account. Fallback successfully implemented and verified: full real-time software simulation demo labeled `"SIMULATION, not a live call"`. Verified in `tests/test_demo.py`. |
| **Documentation explains limitations, privacy & setup** | **MET** | Comprehensive operational, evaluation, and exhibition guides provided in `docs/EVALUATION.md`, `docs/DEMO_GUIDE.md`, and `docs/LIVE_BRINGUP.md`. |


All three detectors perform real inference.

The telephony simulator reproduces the intended codec path.

The risk engine produces explainable decisions.

Step-up authentication and call blocking work in the tested environment.

The dashboard receives live decision updates.

The voiceprint is encrypted at rest.

Live audio remains in memory.

The audit verifier detects tampering.

Evaluation uses held-out recordings and discloses dataset size and limitations.

The live Twilio demonstration works, or the fallback is clearly identified.

Documentation explains model limitations, privacy design and operational setup.

15. Immediate Next Step

Begin with Phase 1 only after explicit approval of the implementation plan. No code or files should be created before approval. The first phase will establish the environment, load the pretrained models and produce real inference output. Later phases proceed only after the previous gate passes and the user approves moving forward.

16. Known Limitations and Presentation Boundaries

To maintain scientific integrity and avoid AI hyperbole, the following boundaries must be maintained:

1. **DO NOT claim universal deepfake protection**: The system does not claim 100% detection against unseen, state-of-the-art zero-shot generative voice models.
2. **DO NOT claim multi-speaker generalization**: The prototype is enrolled and calibrated specifically against a single target speaker (`gokul`). Multi-speaker false acceptance rates require larger multi-speaker corpora.
3. **DO NOT claim AASIST is actively protecting calls**: AASIST is deactivated in production (`weight: 0.0`) due to documented acoustic domain shift on non-studio microphones (`cause not measured`).
4. **DO NOT claim the replay detector is device-independent**: The replay detector relies on spectral coloration differences between recording and playback devices; open-world acoustic replay generalization remains an ongoing research challenge.
5. **DO NOT claim this is live carrier telephony**: The exhibition demo is a faithful **software simulation** streaming 20 ms G.711 $\mu$-law frames over WebSocket. It is not connected to live carrier PSTN trunks.
6. **DO NOT claim Step-Up OTP sends real SMS or carrier DTMF**: In demo mode, step-up OTP is a mock UI simulation ("MOCK OTP").

16. Known Limitations and Presentation Boundaries

To maintain scientific integrity and avoid AI hyperbole, the following boundaries must be maintained:

1. **DO NOT claim universal deepfake protection**: The system does not claim 100% detection against unseen, state-of-the-art zero-shot generative voice models.
2. **DO NOT claim multi-speaker generalization**: The prototype is enrolled and calibrated specifically against a single target speaker (`gokul`). Multi-speaker false acceptance rates require larger multi-speaker corpora.
3. **DO NOT claim AASIST is actively protecting calls**: AASIST is deactivated in production (`weight: 0.0`) due to documented acoustic domain shift on non-studio microphones (`cause not measured`).
4. **DO NOT claim the replay detector is device-independent**: The replay detector relies on spectral coloration differences between recording and playback devices; open-world acoustic replay generalization remains an ongoing research challenge.
5. **DO NOT claim this is live carrier telephony**: The exhibition demo is a faithful **software simulation** streaming 20 ms G.711 $\mu$-law frames over WebSocket. It is not connected to live carrier PSTN trunks.
6. **DO NOT claim Step-Up OTP sends real SMS or carrier DTMF**: In demo mode, step-up OTP is a mock UI simulation ("MOCK OTP").

16. Known Limitations and Presentation Boundaries

To maintain scientific integrity and avoid AI hyperbole, the following boundaries must be maintained:

1. **DO NOT claim universal deepfake protection**: The system does not claim 100% detection against unseen, state-of-the-art zero-shot generative voice models.
2. **DO NOT claim multi-speaker generalization**: The prototype is enrolled and calibrated specifically against a single target speaker (`gokul`). Multi-speaker false acceptance rates require larger multi-speaker corpora.
3. **DO NOT claim AASIST is actively protecting calls**: AASIST is deactivated in production (`weight: 0.0`) due to documented acoustic domain shift on non-studio microphones (`cause not measured`).
4. **DO NOT claim the replay detector is device-independent**: The replay detector relies on spectral coloration differences between recording and playback devices; open-world acoustic replay generalization remains an ongoing research challenge.
5. **DO NOT claim this is live carrier telephony**: The exhibition demo is a faithful **software simulation** streaming 20 ms G.711 $\mu$-law frames over WebSocket. It is not connected to live carrier PSTN trunks.
6. **DO NOT claim Step-Up OTP sends real SMS or carrier DTMF**: In demo mode, step-up OTP is a mock UI simulation ("MOCK OTP").

16. Known Limitations and Presentation Boundaries

To maintain scientific integrity and avoid AI hyperbole, the following boundaries must be maintained:

1. **DO NOT claim universal deepfake protection**: The system does not claim 100% detection against unseen, state-of-the-art zero-shot generative voice models.
2. **DO NOT claim multi-speaker generalization**: The prototype is enrolled and calibrated specifically against a single target speaker (`gokul`). Multi-speaker false acceptance rates require larger multi-speaker corpora.
3. **DO NOT claim AASIST is actively protecting calls**: AASIST is deactivated in production (`weight: 0.0`) due to documented acoustic domain shift on non-studio microphones (`cause not measured`).
4. **DO NOT claim the replay detector is device-independent**: The replay detector relies on spectral coloration differences between recording and playback devices; open-world acoustic replay generalization remains an ongoing research challenge.
5. **DO NOT claim this is live carrier telephony**: The exhibition demo is a faithful **software simulation** streaming 20 ms G.711 $\mu$-law frames over WebSocket. It is not connected to live carrier PSTN trunks.
6. **DO NOT claim Step-Up OTP sends real SMS or carrier DTMF**: In demo mode, step-up OTP is a mock UI simulation ("MOCK OTP").

16. Known Limitations and Presentation Boundaries

To maintain scientific integrity and avoid AI hyperbole, the following boundaries must be maintained:

1. **DO NOT claim universal deepfake protection**: The system does not claim 100% detection against unseen, state-of-the-art zero-shot generative voice models.
2. **DO NOT claim multi-speaker generalization**: The prototype is enrolled and calibrated specifically against a single target speaker (`gokul`). Multi-speaker false acceptance rates require larger multi-speaker corpora.
3. **DO NOT claim AASIST is actively protecting calls**: AASIST is deactivated in production (`weight: 0.0`) due to documented acoustic domain shift on non-studio microphones (`cause not measured`).
4. **DO NOT claim the replay detector is device-independent**: The replay detector relies on spectral coloration differences between recording and playback devices; open-world acoustic replay generalization remains an ongoing research challenge.
5. **DO NOT claim this is live carrier telephony**: The exhibition demo is a faithful **software simulation** streaming 20 ms G.711 $\mu$-law frames over WebSocket. It is not connected to live carrier PSTN trunks.
6. **DO NOT claim Step-Up OTP sends real SMS or carrier DTMF**: In demo mode, step-up OTP is a mock UI simulation ("MOCK OTP").
