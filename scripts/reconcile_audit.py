"""
VoiceGuard Audit Reconciler
Recomputes audit metrics for all 40 scenario clips directly on imported files under data/.
Ensures cloning_method='unknown' on all clone_NN and clone_replay_NN entries.
Updates data/metadata/manifest.json.
"""

import json
import os
import numpy as np
import soundfile as sf
from server.preprocessing import VoiceActivityDetector


MANIFEST_PATH = "data/metadata/manifest.json"


def audit_clip(fpath, target_samples=64600, min_speech_fraction=0.3):
    audio, sr = sf.read(fpath, dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    duration = len(audio) / sr
    peak = float(np.max(np.abs(audio)))
    clipped = int(np.sum(np.abs(audio) >= 0.9999))

    # Fresh VAD instance for clip evaluation
    vad_clip = VoiceActivityDetector(backend="webrtcvad", mode=2, frame_ms=30)
    sp_frac = vad_clip.compute_speech_fraction(audio, sr)
    speech_duration = duration * sp_frac

    if len(audio) < target_samples:
        window_eligible = False
        status = "insufficient_audio"
    else:
        last_window = audio[-target_samples:]
        # Fresh VAD instance for window evaluation
        vad_win = VoiceActivityDetector(backend="webrtcvad", mode=2, frame_ms=30)
        win_sp_frac = vad_win.compute_speech_fraction(last_window, sr)
        if win_sp_frac >= min_speech_fraction:
            window_eligible = True
            status = "ok"
        else:
            window_eligible = False
            status = "insufficient_audio"

    return {
        "duration_seconds": round(duration, 3),
        "vad_speech_duration_seconds": round(speech_duration, 3),
        "peak_amplitude": round(peak, 4),
        "clipped_samples": clipped,
        "aasist_window_eligible": window_eligible,
        "aasist_status": status,
    }


def main():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    old_live_01 = None
    old_clone_02 = None

    for item in manifest:
        cid = item.get("original_id")
        lbl = item.get("label")

        # Fix cloning_method on clone_NN and clone_replay_NN
        if "clone" in cid:
            item["cloning_method"] = "unknown"

        if cid == "live_01":
            old_live_01 = dict(item)
        elif cid == "clone_02":
            old_clone_02 = dict(item)

        orig_path = item.get("original_path")
        if orig_path and os.path.exists(orig_path) and item.get("group") == "enrolled_target":
            metrics = audit_clip(orig_path)
            item.update(metrics)

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    by_id = {x["original_id"]: x for x in manifest}
    new_live_01 = by_id["live_01"]
    new_clone_02 = by_id["clone_02"]

    print("=" * 80)
    print("RECONCILIATION OLD VS NEW COMPARISON")
    print("=" * 80)
    print(f"live_01:")
    print(f"  Old manifest: vad={old_live_01.get('vad_speech_duration_seconds')}s, peak={old_live_01.get('peak_amplitude')}, status={old_live_01.get('aasist_status')}")
    print(f"  New manifest: vad={new_live_01.get('vad_speech_duration_seconds')}s, peak={new_live_01.get('peak_amplitude')}, status={new_live_01.get('aasist_status')}")
    print(f"clone_02:")
    print(f"  Old manifest: vad={old_clone_02.get('vad_speech_duration_seconds')}s, peak={old_clone_02.get('peak_amplitude')}, status={old_clone_02.get('aasist_status')}, method={old_clone_02.get('cloning_method')}")
    print(f"  New manifest: vad={new_clone_02.get('vad_speech_duration_seconds')}s, peak={new_clone_02.get('peak_amplitude')}, status={new_clone_02.get('aasist_status')}, method={new_clone_02.get('cloning_method')}")
    print("=" * 80)


if __name__ == "__main__":
    main()
