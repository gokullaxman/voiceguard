# VoiceGuard System Evaluation Report

## 1. Dataset Breakdown (Raw vs Scoreable)

| Scenario / Label | Raw Count | Scoreable (AASIST Window >= 4.0375s) | Insufficient Audio |
| :--- | :--- | :--- | :--- |
| `cloned_direct` | 14 | 7 | 7 |
| `cloned_direct_merged` | 3 | 3 | 0 |
| `cloned_replay` | 10 | 8 | 2 |
| `enrollment` | 1 | 1 | 0 |
| `genuine_live` | 28 | 10 | 18 |
| `genuine_live_extra` | 30 | 30 | 0 |
| `genuine_replay` | 10 | 10 | 0 |
| `unassigned` | 1 | 1 | 0 |

## 2. Per-Detector Standalone Evaluation

### A. Synthetic Voice Spoof Detector (AASIST)
- **Architecture**: AASIST Graph Attention Network (vendored PyTorch weights).
- **ASVspoof 2019 LA Ground Truth**: Bonafide median `0.000023`, Spoof median `0.999960`.
- **Acoustic Domain Shift Finding**: On live laptop microphone clips, AASIST outputs median `0.975570` (imported) and `0.993499` (simulated), causing severe false rejections under direct deployment.

### B. AASIST Recalibration & Display Modes
- **Modes**: `off` (default, suppressed), `real` (raw output, uncalibrated), `calibrated` (recalibrated logistic regression).
- **Calibration Parameters**: `weight = -0.259134`, `intercept = 1.911943` fit on 31 usable clips (9 excluded for duration < 4.0375s).
- **Disclosure Label**: `"AASIST output recalibrated on project data (optimistic, one speaker). Display only, not used in decision."`
- **Critical Boundary**: *Fit on the evaluation data, one speaker, optimistic; direction of the effect is opposite to the original AASIST convention on our recordings (cause not measured).*
- **Risk Engine Isolation**: Recalibrated spoof strictly does not enter the risk engine; decision, band, streaks, and outcome remain 100% byte-identical across all three modes.

### C. Speaker Verification (ECAPA-TDNN)
- **Architecture**: Pretrained SpeechBrain ECAPA-TDNN (192-dim cosine similarity).
- **Separation**: Genuine live median similarity = `0.4169`, Attack median similarity = `0.3364`.
- **Limitation**: When evaluated standalone without replay detection, attacks achieve 33% false grant rate because replayed speech retains the legitimate speaker's voice.

### D. Acoustic Replay Detector
- **Architecture**: Gain-normalized acoustic spectral features (standardized log-mel, sub-band energy ratios, rolloff, flatness) + Logistic Regression.
- **Cross-Validation**: 5-fold grouped leave-one-group-out CV achieves out-of-fold AUC = `1.0000`.
- **Confound Audit**: Perfect separation persists across level-only, band-ratio-only, and RMS-normalized audio, indicating the model learns the distinct acoustic transmission channel between phone-mic recordings and loudspeaker playback.

## 3. Multi-Detector Fused Evaluation (Held-Out 5-Fold Cross Validation)

| Configuration | Overall Accuracy | Precision | Recall | F1 Score | FP (Live Refused) | FN (Attack Allowed) | 90% Gate Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Config 1: All Three (SPOOF + SPEAKER + REPLAY)** | 97.50% | 1.0000 | 0.9667 | 0.9831 | 0 | 1 | **PASS** |
| **Config 2: SPOOF Off (SPEAKER + REPLAY)** | 97.50% | 1.0000 | 0.9667 | 0.9831 | 0 | 1 | **PASS** |
| **Config 3: SPEAKER Only** | 70.00% | 0.9091 | 0.6667 | 0.7692 | 2 | 10 | **FAIL** |

### Recommended Production Configuration: Config 2 (SPOOF Off: SPEAKER + REPLAY)
- **Genuine Live Accuracy**: 100.0% (10/10 allowed, 0 false rejections).
- **Genuine Replay Accuracy**: 100.0% (10/10 blocked).
- **Cloned Replay Accuracy**: 100.0% (10/10 blocked).
- **Cloned Direct Accuracy**: 90.0% (9/10 blocked, 1 false grant).

### Performance on Extra Evaluation Sets
- **session2_seg (30 genuine live clips)**: Median Risk = `0.0011` | 30/30 Allowed (LOW risk).
- **other_tts (4 out-of-domain TTS attacks)**: Median Risk = `0.9531` | 4/4 Blocked (HIGH risk).
- **cloned_direct_merged (3 concatenated clones)**: Median Risk = `0.5011` | 2/3 Step-Up / Blocked.

## 4. Real-Time Latency Telemetry

- **Per-Window Scoring Latency (p50)**: `159.6 ms - 308.9 ms`
- **Per-Window Scoring Latency (p95)**: `189.0 ms - 359.1 ms` (initial window: ~1500 ms due to PyTorch model cold-start)
- **Cadence**: Evaluates rolling audio every 0.5 - 1.0 second (comfortably real-time for live 20 ms Twilio frames).

## 5. Architectural & Dataset Limitations

1. **Small Custom Dataset**: The primary evaluation dataset contains 40 scenario clips plus 30 secondary live clips.
2. **Single Enrolled Speaker**: Testing was conducted on voiceprints of a single primary speaker (`gokul`). Multi-speaker false acceptance rates require larger multi-speaker corpora.
3. **Single Acoustic Room and Device**: Live clips and replay attacks were recorded in a single physical environment with a single smartphone and laptop.
4. **SPOOF Domain Shift**: The AASIST model trained on ASVspoof 2019 LA exhibits severe domain shift on non-studio microphone audio, necessitating its exclusion in Config 2.
5. **Replay Channel Confound**: The replay detector heavily leverages the microphone and loudspeaker spectral coloration of the specific test setup; open-world acoustic replay detection remains an unverified generalization.
6. **Session 2 Optimism**: Session 2 clips were collected from the same speaker session and demonstrate higher volume levels than Session 1 clips.
7. **Derived Merged Clips**: Concatenated clone clips were merged artificially with 10 ms cross-fades rather than recorded as continuous synthetic speech.
8. **Software Codec Simulation**: Offline phone simulation models bandwidth limitation and G.711 mu-law quantization, but does not capture live cellular network packet jitter, packet loss concealment, or adaptive multi-rate (AMR) codecs.
9. **Twilio Live Integration**: End-to-end streaming was thoroughly validated via live frame simulation; production carrier PSTN bring-up requires live carrier credentials.
