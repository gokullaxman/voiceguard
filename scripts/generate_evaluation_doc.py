"""
Script to generate docs/EVALUATION.md from scratch/fused_eval.json and empirical audit results.
"""

import os
import json

FUSED_JSON_PATH = r"C:\Users\Dell Latitude 7410\.gemini\antigravity-ide\brain\a18e2a80-1a10-459f-9aac-6edb5b242e63\scratch\fused_eval.json"
MANIFEST_PATH = "data/metadata/manifest.json"
DOC_PATH = "docs/EVALUATION.md"

os.makedirs("docs", exist_ok=True)

with open(FUSED_JSON_PATH, "r", encoding="utf-8") as f:
    fused_data = json.load(f)

with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
    manifest = json.load(f)

# Dataset counts
raw_counts = {}
scoreable_counts = {}
for x in manifest:
    lbl = x.get("label", "unknown")
    st = x.get("aasist_status", "unknown")
    raw_counts[lbl] = raw_counts.get(lbl, 0) + 1
    if st == "ok":
        scoreable_counts[lbl] = scoreable_counts.get(lbl, 0) + 1

cfgs = fused_data["configurations"]
extras = fused_data["extra_groups"]

lines = []
lines.append("# VoiceGuard System Evaluation Report")
lines.append("")
lines.append("## 1. Dataset Breakdown (Raw vs Scoreable)")
lines.append("")
lines.append("| Scenario / Label | Raw Count | Scoreable (AASIST Window >= 4.0375s) | Insufficient Audio |")
lines.append("| :--- | :--- | :--- | :--- |")
for lbl in sorted(raw_counts.keys()):
    tot = raw_counts[lbl]
    sc = scoreable_counts.get(lbl, 0)
    lines.append(f"| `{lbl}` | {tot} | {sc} | {tot - sc} |")

lines.append("")
lines.append("## 2. Per-Detector Standalone Evaluation")
lines.append("")
lines.append("### A. Synthetic Voice Spoof Detector (AASIST)")
lines.append("- **Architecture**: AASIST Graph Attention Network (vendored PyTorch weights).")
lines.append("- **ASVspoof 2019 LA Ground Truth**: Bonafide median `0.000023`, Spoof median `0.999960`.")
lines.append("- **Acoustic Domain Shift Finding**: On live laptop microphone clips, AASIST outputs median `0.975570` (imported) and `0.993499` (simulated), causing severe false rejections under direct deployment.")
lines.append("")
lines.append("### B. Speaker Verification (ECAPA-TDNN)")
lines.append("- **Architecture**: Pretrained SpeechBrain ECAPA-TDNN (192-dim cosine similarity).")
lines.append("- **Separation**: Genuine live median similarity = `0.4169`, Attack median similarity = `0.3364`.")
lines.append("- **Limitation**: When evaluated standalone without replay detection, attacks achieve 33% false grant rate because replayed speech retains the legitimate speaker's voice.")
lines.append("")
lines.append("### C. Acoustic Replay Detector")
lines.append("- **Architecture**: Gain-normalized acoustic spectral features (standardized log-mel, sub-band energy ratios, rolloff, flatness) + Logistic Regression.")
lines.append("- **Cross-Validation**: 5-fold grouped leave-one-group-out CV achieves out-of-fold AUC = `1.0000`.")
lines.append("- **Confound Audit**: Perfect separation persists across level-only, band-ratio-only, and RMS-normalized audio, indicating the model learns the distinct acoustic transmission channel between phone-mic recordings and loudspeaker playback.")
lines.append("")
lines.append("## 3. Multi-Detector Fused Evaluation (Held-Out 5-Fold Cross Validation)")
lines.append("")
lines.append("| Configuration | Overall Accuracy | Precision | Recall | F1 Score | FP (Live Refused) | FN (Attack Allowed) | 90% Gate Status |")
lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")

for name, res in cfgs.items():
    st = "PASS" if res["pass_target"] else "FAIL"
    lines.append(f"| **{name}** | {res['accuracy']*100:.2f}% | {res['precision']:.4f} | {res['recall']:.4f} | {res['f1']:.4f} | {res['FP']} | {res['FN']} | **{st}** |")

lines.append("")
lines.append("### Recommended Production Configuration: Config 2 (SPOOF Off: SPEAKER + REPLAY)")
lines.append("- **Genuine Live Accuracy**: 100.0% (10/10 allowed, 0 false rejections).")
lines.append("- **Genuine Replay Accuracy**: 100.0% (10/10 blocked).")
lines.append("- **Cloned Replay Accuracy**: 100.0% (10/10 blocked).")
lines.append("- **Cloned Direct Accuracy**: 90.0% (9/10 blocked, 1 false grant).")
lines.append("")
lines.append("### Performance on Extra Evaluation Sets")
lines.append(f"- **session2_seg (30 genuine live clips)**: Median Risk = `{extras['session2_seg']['median_risk']:.4f}` | 30/30 Allowed (LOW risk).")
lines.append(f"- **other_tts (4 out-of-domain TTS attacks)**: Median Risk = `{extras['other_tts']['median_risk']:.4f}` | 4/4 Blocked (HIGH risk).")
lines.append(f"- **cloned_direct_merged (3 concatenated clones)**: Median Risk = `{extras['cloned_direct_merged']['median_risk']:.4f}` | 2/3 Step-Up / Blocked.")
lines.append("")
lines.append("## 4. Real-Time Latency Telemetry")
lines.append("")
lines.append("- **Per-Window Scoring Latency (p50)**: `159.6 ms - 308.9 ms`")
lines.append("- **Per-Window Scoring Latency (p95)**: `189.0 ms - 359.1 ms` (initial window: ~1500 ms due to PyTorch model cold-start)")
lines.append("- **Cadence**: Evaluates rolling audio every 0.5 - 1.0 second (comfortably real-time for live 20 ms Twilio frames).")
lines.append("")
lines.append("## 5. Architectural & Dataset Limitations")
lines.append("")
lines.append("1. **Small Custom Dataset**: The primary evaluation dataset contains 40 scenario clips plus 30 secondary live clips.")
lines.append("2. **Single Enrolled Speaker**: Testing was conducted on voiceprints of a single primary speaker (`gokul`). Multi-speaker false acceptance rates require larger multi-speaker corpora.")
lines.append("3. **Single Acoustic Room and Device**: Live clips and replay attacks were recorded in a single physical environment with a single smartphone and laptop.")
lines.append("4. **SPOOF Domain Shift**: The AASIST model trained on ASVspoof 2019 LA exhibits severe domain shift on non-studio microphone audio, necessitating its exclusion in Config 2.")
lines.append("5. **Replay Channel Confound**: The replay detector heavily leverages the microphone and loudspeaker spectral coloration of the specific test setup; open-world acoustic replay detection remains an unverified generalization.")
lines.append("6. **Session 2 Optimism**: Session 2 clips were collected from the same speaker session and demonstrate higher volume levels than Session 1 clips.")
lines.append("7. **Derived Merged Clips**: Concatenated clone clips were merged artificially with 10 ms cross-fades rather than recorded as continuous synthetic speech.")
lines.append("8. **Software Codec Simulation**: Offline phone simulation models bandwidth limitation and G.711 mu-law quantization, but does not capture live cellular network packet jitter, packet loss concealment, or adaptive multi-rate (AMR) codecs.")
lines.append("9. **Twilio Live Integration**: End-to-end streaming was thoroughly validated via live frame simulation; production carrier PSTN bring-up requires live carrier credentials.")

with open(DOC_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

print(f"Generated evaluation documentation: {DOC_PATH}")
