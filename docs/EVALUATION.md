# VoiceGuard System Evaluation Report
**Label: SIMULATION, not a live call**

## 1. Dataset Breakdown & Composition

The VoiceGuard telephony evaluation dataset comprises:
- **Core 40-Clip Scenario Set**: 10 genuine live recordings, 10 direct clones, 10 genuine replay attacks, and 10 cloned replay attacks (enrolled speaker `gokul`).
- **30 Session-2 Segments**: Additional genuine speech clips (`session2_seg_01` .. `session2_seg_30`).
- **18 Phone-Live WhatsApp Voice Notes**: Field recordings collected on smartphone hardware (`phone_live_01` .. `phone_live_18`, labeled `evaluation_only`).
- **4 Out-of-Domain TTS Attacks**: Synthesized text-to-speech attacks (`spoof_tts_01` .. `spoof_tts_04`).
- **3 Merged Clone Attacks**: Concatenated clone clips (`cloned_merged_01` .. `cloned_merged_03`).

---

## 2. Multi-Detector Whole-Clip Fused Evaluation (5-Fold Cross-Validation)

### Configuration Comparison

| Configuration | Overall Accuracy | Wilson 95% CI | Precision | Recall | F1 Score | FP (Live Refused) | FN (Attack Allowed) | Target (>=90%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Config 1: All Three (SPOOF + SPEAKER + REPLAY)** | 97.50% | [87.12%, 99.56%] | 1.0000 | 0.9667 | 0.9831 | 0 | 1 | **PASS** |
| **Config 2: SPOOF Off (SPEAKER + REPLAY)** | 97.50% | [87.12%, 99.56%] | 1.0000 | 0.9667 | 0.9831 | 0 | 1 | **PASS** |
| **Config 3: SPEAKER Only** | 70.00% | [54.57%, 81.93%] | 0.9091 | 0.6667 | 0.7692 | 2 | 10 | **FAIL** |

### Per-Scenario Accuracy (Config 2)
- **Genuine Live**: 100.0% | Wilson 95% CI: [72.25%, 100.00%]
- **Cloned Direct**: 90.0% | Wilson 95% CI: [59.58%, 98.21%]
- **Genuine Replay**: 100.0% | Wilson 95% CI: [72.25%, 100.00%]
- **Cloned Replay**: 100.0% | Wilson 95% CI: [72.25%, 100.00%]

---

## 3. Sustained-Window Streaming Evaluation (Step 3)

The 40 primary evaluation clips were streamed through the real `StreamingSession` pipeline with rolling 2.0s buffers advanced every 1.0s under the 3-window sustained evidence rule.

### Streaming Results per Scenario Group (N=10 each)

| Scenario Group | N | Allow | Step-Up Only | Block | Match Rate | Wilson 95% CI | Discrepancy Flag |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **genuine_live** | 10 | 8 | 2 | 0 | 80.0% (8/10) | [49.02%, 94.33%] | 2 false step-up |
| **cloned_direct** | 10 | 7 | 3 | 0 | 30.0% (3/10) | [10.78%, 60.32%] | 7 missed |
| **genuine_replay** | 10 | 0 | 1 | 9 | 100.0% (10/10) | [72.25%, 100.00%] | 0 missed |
| **cloned_replay** | 10 | 3 | 3 | 4 | 70.0% (7/10) | [39.68%, 89.22%] | 3 missed |
| **OVERALL STREAMING** | **40** | -- | -- | -- | **70.0%** (28/40) | **[54.57%, 81.93%]** | **12 discrepancies** |

---

## 4. Comparison: Whole-Clip Scoring vs. Sustained-Window Streaming

| Metric / Scenario Group | Whole-Clip Scoring (`fused_eval.json`) | Sustained-Window Streaming (`streaming_eval.json`) |
| :--- | :--- | :--- |
| **Overall Decision Rate** | **97.5%** (39/40) [87.12%, 99.56%] | **70.0%** (28/40) [54.57%, 81.93%] |
| **genuine_live** | 100.0% [72.25%, 100.00%] | 80.0% [49.02%, 94.33%] |
| **cloned_direct** | 90.0% [59.58%, 98.21%] | 30.0% [10.78%, 60.32%] |
| **genuine_replay** | 100.0% [72.25%, 100.00%] | 100.0% [72.25%, 100.00%] |
| **cloned_replay** | 100.0% [72.25%, 100.00%] | 70.0% [39.68%, 89.22%] |

> [!IMPORTANT]
> **Methodological Statement on Metrics**:
> Whole-clip scoring and sustained-window streaming are fundamentally **different measurements**:
> 1. Whole-clip scoring evaluates a single risk score computed from the entire audio duration.
> 2. Sustained-window streaming evaluates a rolling 2.0s buffer advanced every 1.0s, requiring consecutive window threshold exceedances (sustained evidence rule) to fire action triggers.
> Neither measurement should be designated "the" accuracy of the system.
> Note: The linear speaker calibration map (a, b) was fit on these same 40 clips; results are optimistic and lack a held-out speaker estimate.

---

## 5. Important Methodological Disclosures

### A. Post-Hoc Configuration Caveat
> [!WARNING]
> The decision to disable SPOOF (Config 2) was made **after observing evaluation results** on the dataset. Consequently, reported cross-validation accuracy is **optimistic** and represents an empirical post-hoc selection rather than a purely pre-specified blinded trial.

### B. Production Speaker Calibration Note
> [!NOTE]
> The production linear speaker calibration mapping `(a = 0.3364065, b = 0.4169240)` was fitted once on all 40 phone-simulated evaluation clips using the same median rule as cross-validation folds (`a` = median attack similarity, `b` = median genuine live similarity). It is strictly labeled:
> **"fit on all evaluation data, no held-out estimate"**.

### C. SPOOF Disabled Due to Acoustic Domain Shift
> [!IMPORTANT]
> The AASIST synthetic voice spoof detector is kept fully implemented in code but set to `enabled: false` with weight `0.00` in `config/settings.yaml`.
> **Documented Rationale**: Measured domain shift. On non-studio recordings, AASIST outputs 0.92 to 0.99 spoof probability on bonafide speech. The physical or acoustic cause is unmeasured (`cause not measured`).

### D. Replay Channel Confound & Phone-Live Limitation
- **Phone-Live Dataset**: 18 slices of ONE WhatsApp audio recording from a single smartphone. Slices are not independent (effective sample size ≈ 1).
- **Replay Detector**: Trained on 40 clips from a single smartphone and single loudspeaker. Channel coloration confounds have not been ruled out.

---

## 6. Architectural & System Limitations

1. **Small Custom Dataset**: Primary evaluation conducted across 40 clips, 30 session-2 segments, and 18 phone-live slices.
2. **Single Enrolled Speaker**: Calibrated solely against enrolled speaker `gokul`.
3. **Software Codec Simulation**: Offline G.711 mu-law simulation approximates PSTN quantization but does not capture carrier packet loss concealment, jitter, or AMR transcoding.
4. **Twilio Telephony Optional and Untested on Live PSTN**: The complete Twilio Media Stream path was validated in simulation and tunnel rehearsals; no real carrier call was completed.
5. **Step-Up Verification**: Step-up OTP is a mock simulation ("MOCK OTP").
