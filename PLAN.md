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

14. Final Acceptance Criteria

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
