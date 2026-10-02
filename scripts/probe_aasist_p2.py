"""
VoiceGuard Post-P2 AASIST Diagnostic Probe
Interim exploratory probe evaluating phone-simulated bonafide and TTS clips.
Report-only: outputs raw logits, spoof_prob, and exploratory AUC / EER.
Applies ZERO calibration, zero tuning, and zero filtering.
"""

import json
import os
import numpy as np
import soundfile as sf
import torch
from sklearn.metrics import roc_auc_score, roc_curve
from scipy.optimize import brentq
from scipy.interpolate import interp1d
from models.spoof import AASISTSpoofDetector
from server.telephony import simulate_telephony_channel


def compute_eer(y_true, y_score):
    """Computes Equal Error Rate (EER) where y_true=1 is positive (spoof)."""
    fpr, tpr, thresholds = roc_curve(y_true, y_score, pos_label=1)
    fnr = 1 - tpr
    try:
        eer = brentq(lambda x: 1.0 - x - interp1d(fpr, tpr)(x), 0.0, 1.0)
    except Exception:
        diff = np.abs(fpr - fnr)
        idx = np.argmin(diff)
        eer = (fpr[idx] + fnr[idx]) / 2.0
    return float(eer)


def main():
    print("=" * 105)
    print("VOICEGUARD P2 INTERIM AASIST PROBE: PHONE-SIMULATED AUDIO [EXPLORATORY, TINY SAMPLE]")
    print("=" * 105)

    detector = AASISTSpoofDetector(checkpoint_path="models/artifacts/AASIST.pth")

    # 1. Define real SpeechBrain bonafide clips
    sb_clips = [
        ("bonafide_speaker1_utt1", "data/metadata/bonafide_speaker1_utt1.wav", "speaker1", "genuine_live"),
        ("bonafide_speaker1_utt2", "data/metadata/bonafide_speaker1_utt2.wav", "speaker1", "genuine_live"),
        ("bonafide_speaker2_utt1", "data/metadata/bonafide_speaker2_utt1.wav", "speaker2", "genuine_live"),
    ]

    # 2. Define edge-tts clips
    tts_clips = [
        ("spoof_tts_christopher", "data/metadata/spoof_tts.wav", "tts_christopher", "cloned_direct"),
        ("spoof_tts_aria", "data/metadata/spoof_tts_aria.wav", "tts_aria", "cloned_direct"),
        ("spoof_tts_guy", "data/metadata/spoof_tts_guy.wav", "tts_guy", "cloned_direct"),
        ("spoof_tts_sonia", "data/metadata/spoof_tts_sonia.wav", "tts_sonia", "cloned_direct"),
    ]

    probe_entries = []

    # Process individual bonafide clips
    spk1_audios = []
    for name, path, spk, lbl in sb_clips:
        audio, sr = sf.read(path, dtype="float32")
        if "speaker1" in spk:
            spk1_audios.append(audio)
        probe_entries.append({
            "name": name,
            "speaker_id": spk,
            "label": lbl,
            "audio": audio,
            "is_spoof": 0,
            "note": "single utterance (tile padded to 64.6k)"
        })

    # Concatenate speaker1 utt1 + utt2 (~6s, > 64,600 samples)
    if len(spk1_audios) == 2:
        concat_spk1 = np.concatenate(spk1_audios)
        probe_entries.append({
            "name": "bonafide_spk1_concat_utt1_utt2",
            "speaker_id": "speaker1",
            "label": "genuine_live",
            "audio": concat_spk1,
            "is_spoof": 0,
            "note": "concatenated (~6.0s, FULL window, NO padding)"
        })

    # Process TTS clips
    for name, path, spk, lbl in tts_clips:
        if os.path.exists(path):
            audio, sr = sf.read(path, dtype="float32")
            probe_entries.append({
                "name": name,
                "speaker_id": spk,
                "label": lbl,
                "audio": audio,
                "is_spoof": 1,
                "note": "TTS synthesis (full window, no padding)"
            })

    # Run phone simulation and evaluate AASIST
    results = []
    y_true = []
    y_scores = []

    for entry in probe_entries:
        raw_audio = entry["audio"]
        # Apply offline phone-channel simulation (WAV -> mono -> 8k -> mu-law -> 16k -> float32)
        sim_audio = simulate_telephony_channel(raw_audio)
        spoof_prob, raw_logits = detector.score(sim_audio)

        y_true.append(entry["is_spoof"])
        y_scores.append(spoof_prob)

        results.append({
            "name": entry["name"],
            "label": entry["label"],
            "speaker_id": entry["speaker_id"],
            "samples": len(raw_audio),
            "duration": len(raw_audio) / 16000.0,
            "raw_logits": raw_logits,
            "spoof_prob": spoof_prob,
            "note": entry["note"],
        })

    print(f"\n{'Clip Name':<34} | {'Label':<14} | {'Speaker':<17} | {'Dur (s)':<7} | {'Raw Logits':<18} | {'Spoof Prob':<10} | {'Window / Padding Note'}")
    print("-" * 140)
    for r in results:
        logits_str = f"[{r['raw_logits'][0]:.2f}, {r['raw_logits'][1]:.2f}]"
        print(f"{r['name']:<34} | {r['label']:<14} | {r['speaker_id']:<17} | {r['duration']:<7.2f} | {logits_str:<18} | {r['spoof_prob']:<10.4f} | {r['note']}")
    print("=" * 140)

    # Summary of bonafide behavior
    bonafide_scores = [r["spoof_prob"] for r in results if r["label"] == "genuine_live"]
    spoof_scores = [r["spoof_prob"] for r in results if r["label"] == "cloned_direct"]

    print("\n" + "-" * 80)
    print("FINDINGS ON PHONE-SIMULATED BONAFIDE SPEECH [EXPLORATORY, TINY SAMPLE]:")
    print("-" * 80)
    above_half = [s > 0.5 for s in bonafide_scores]
    if all(above_half):
        print("PLAIN STATEMENT: YES, ALL phone-simulated bonafide clips scored ABOVE 0.5 spoof probability.")
    elif any(above_half):
        print(f"PLAIN STATEMENT: PARTIAL, {sum(above_half)} of {len(bonafide_scores)} phone-simulated bonafide clips scored ABOVE 0.5.")
    else:
        print("PLAIN STATEMENT: NO, phone-simulated bonafide clips scored below 0.5.")

    for r in results:
        if r["label"] == "genuine_live":
            verdict = "SCORES ABOVE 0.5 (False Positive)" if r["spoof_prob"] > 0.5 else "SCORES BELOW 0.5 (Bonafide)"
            print(f"  * {r['name']:<32}: spoof_prob = {r['spoof_prob']:.4f} -> {verdict}")

    # Exploratory ROC AUC and EER
    num_spoofs = sum(y_true)
    num_bonafide = len(y_true) - num_spoofs
    print(f"\nEvaluated sample counts: {num_bonafide} bonafide, {num_spoofs} spoof (Total: {len(y_true)})")

    if num_spoofs > 0 and num_bonafide > 0:
        try:
            auc = roc_auc_score(y_true, y_scores)
            eer = compute_eer(y_true, y_scores)
            print(f"\nExploratory Metrics [EXPLORATORY, TINY SAMPLE - NOT TUNED / NOT CALIBRATED]:")
            print(f"  ROC AUC: {auc:.4f}  (exploratory, tiny sample)")
            print(f"  EER:     {eer * 100:.2f}% (exploratory, tiny sample)")
        except Exception as e:
            print(f"Could not compute ROC/EER: {e}")

    print("\n" + "=" * 105)
    print("END OF INTERIM AASIST PROBE")
    print("=" * 105)


if __name__ == "__main__":
    main()
