"""
VoiceGuard Phase P1 Detailed Diagnostic Script
Runs AASIST and padding diagnostics across all bonafide and TTS clips.
"""

import os
import math
import numpy as np
import soundfile as sf
import torch
import torch.nn.functional as F
from models.spoof import AASISTSpoofDetector


def main():
    detector = AASISTSpoofDetector(checkpoint_path="models/artifacts/AASIST.pth")
    target_samples = 64600

    clips = [
        # Bonafide clips
        ("bonafide_speaker1_utt1.wav", "bonafide", "data/metadata/bonafide_speaker1_utt1.wav"),
        ("bonafide_speaker1_utt2.wav", "bonafide", "data/metadata/bonafide_speaker1_utt2.wav"),
        ("bonafide_speaker2_utt1.wav", "bonafide", "data/metadata/bonafide_speaker2_utt1.wav"),
        # Spoof TTS clips
        ("spoof_tts.wav", "spoof", "data/metadata/spoof_tts.wav"),
        ("spoof_tts_aria.wav", "spoof", "data/metadata/spoof_tts_aria.wav"),
        ("spoof_tts_guy.wav", "spoof", "data/metadata/spoof_tts_guy.wav"),
        ("spoof_tts_sonia.wav", "spoof", "data/metadata/spoof_tts_sonia.wav"),
    ]

    print("=" * 80)
    print("VOICEGUARD P1 DIAGNOSTIC REPORT: AUDIO & AASIST ANALYSIS")
    print("=" * 80)

    summary_rows = []

    for name, label, path in clips:
        if not os.path.exists(path):
            print(f"Skipping missing file: {path}")
            continue

        data, sr = sf.read(path, dtype="float32")
        if data.ndim > 1:
            data = data.mean(axis=1)

        num_samples = len(data)
        duration_sec = num_samples / sr
        peak_amp = float(np.max(np.abs(data)))
        is_float32 = (data.dtype == np.float32)
        in_range = (-1.0 <= np.min(data) <= 1.0) and (-1.0 <= np.max(data) <= 1.0)

        # 1. Tile padding (Official clovaai/aasist strategy)
        if num_samples < target_samples:
            repeats = int(math.ceil(target_samples / num_samples))
            tiled = np.tile(data, repeats)[:target_samples]
        else:
            tiled = data[:target_samples]

        tensor_tile = torch.from_numpy(tiled).float().unsqueeze(0)
        with torch.no_grad():
            _, logits_tile = detector.model(tensor_tile)
            probs_tile = F.softmax(logits_tile, dim=-1)
            raw_logits_tile = logits_tile.cpu().numpy()[0]
            spoof_prob_tile = float(probs_tile[0, 0].item())

        # 2. Zero padding (Alternative comparison)
        if num_samples < target_samples:
            padded_zero = np.pad(data, (0, target_samples - num_samples), mode="constant")
        else:
            padded_zero = data[:target_samples]

        tensor_zero = torch.from_numpy(padded_zero).float().unsqueeze(0)
        with torch.no_grad():
            _, logits_zero = detector.model(tensor_zero)
            probs_zero = F.softmax(logits_zero, dim=-1)
            raw_logits_zero = logits_zero.cpu().numpy()[0]
            spoof_prob_zero = float(probs_zero[0, 0].item())

        print(f"\n--- Clip: {name} [{label.upper()}] ---")
        print(f"  Duration:          {duration_sec:.3f} s")
        print(f"  Sample Rate:       {sr} Hz")
        print(f"  Sample Count:      {num_samples} (target: {target_samples}, diff: {num_samples - target_samples:+d})")
        print(f"  Peak Amplitude:    {peak_amp:.4f}")
        print(f"  Format:            dtype={data.dtype}, in_range_[-1,1]={in_range}")
        print(f"  [Tile/Repeat Pad]  Logits: [{raw_logits_tile[0]:.4f}, {raw_logits_tile[1]:.4f}] -> spoof_prob: {spoof_prob_tile:.6f}")
        print(f"  [Zero Pad]         Logits: [{raw_logits_zero[0]:.4f}, {raw_logits_zero[1]:.4f}] -> spoof_prob: {spoof_prob_zero:.6f}")

        summary_rows.append({
            "clip": name,
            "label": label,
            "samples": num_samples,
            "spoof_prob_tile": spoof_prob_tile,
            "spoof_prob_zero": spoof_prob_zero,
            "raw_logits": raw_logits_tile
        })

    print("\n" + "=" * 80)
    print("SUMMARY SCORE TABLE (Official Tile-Pad vs Zero-Pad)")
    print("=" * 80)
    header = f"{'Clip':<30} | {'Label':<10} | {'Samples':<8} | {'Spoof Prob (Tile)':<18} | {'Spoof Prob (Zero)':<18}"
    print(header)
    print("-" * len(header))
    for r in summary_rows:
        print(f"{r['clip']:<30} | {r['label']:<10} | {r['samples']:<8} | {r['spoof_prob_tile']:<18.6f} | {r['spoof_prob_zero']:<18.6f}")

    print("=" * 80)


if __name__ == "__main__":
    main()
