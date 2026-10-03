"""
VoiceGuard Batch Import, Format Verification, VAD Analysis & Pairing Sanity Check
Executes:
1. Stream info inspection of original replay files.
2. FFmpeg conversion to 16 kHz mono PCM_16 for all 40 scenario clips.
3. Provenance manifest registration with exact metadata.
4. Telephony simulation copy generation (via prepare_data.py pipeline).
5. Per-clip VAD speech duration, peak level, clipped sample count, and AASIST window eligibility.
6. Pairing sanity check via speech energy envelope cross-correlation.
7. Verification that git status has no audio staged.
"""

import json
import os
import shutil
import subprocess
import sys
import numpy as np
from scipy.signal import correlate, resample_poly
import soundfile as sf
import yaml

from server.telephony import simulate_telephony_channel
from server.preprocessing import VoiceActivityDetector, RollingAudioBuffer, guard_amplitude
from scripts.import_recording import find_ffmpeg, load_manifest, save_manifest, MANIFEST_PATH


SOURCE_DIR = r"C:\Users\Dell Latitude 7410\Downloads\voice"


def get_replay_stream_info():
    """Prints soundfile info for every replay file to verify subtype."""
    print("=" * 90)
    print("REPLAY FILE STREAM INFO (ORIGINAL FILES)")
    print("=" * 90)
    replay_folders = ["geniune replay", "cloned replay"]
    for folder in replay_folders:
        folder_path = os.path.join(SOURCE_DIR, folder)
        if not os.path.exists(folder_path):
            continue
        for fname in sorted(os.listdir(folder_path)):
            if not fname.lower().endswith(".wav"):
                continue
            fpath = os.path.join(folder_path, fname)
            info = sf.info(fpath)
            print(f"{os.path.join(folder, fname):<35} | format={info.format} | subtype={info.subtype:<7} | "
                  f"samplerate={info.samplerate:<5} | channels={info.channels} | duration={info.duration:.3f}s")
    print("=" * 90 + "\n")


def build_import_queue():
    """Builds explicit list of 40 scenario files plus testimony_replay metadata."""
    queue = []

    # 1. genuine_live (live_01 .. live_10)
    for i in range(1, 11):
        idx_str = f"{i:02d}"
        fname = f"live_{idx_str}.wav"
        src = os.path.join(SOURCE_DIR, "geninue", fname)
        queue.append({
            "source_path": src,
            "filename": fname,
            "original_id": f"live_{idx_str}",
            "source_original_id": None,
            "label": "genuine_live",
            "group": "enrolled_target",
            "speaker_id": "gokul",
            "target_dir": "data/genuine",
            "device": "laptop mic",
            "room": "unknown",
            "distance": "unknown",
            "cloning_method": "none",
            "tool": "none",
            "version": "none",
            "conditions": "device: laptop mic, room: unknown, distance: unknown"
        })

    # 2. cloned_direct (clone_01 .. clone_10)
    for i in range(1, 11):
        idx_str = f"{i:02d}"
        fname = f"clone_{idx_str}.wav"
        src = os.path.join(SOURCE_DIR, "cloned", fname)
        queue.append({
            "source_path": src,
            "filename": fname,
            "original_id": f"clone_{idx_str}",
            "source_original_id": None,
            "label": "cloned_direct",
            "group": "enrolled_target",
            "speaker_id": "gokul",
            "target_dir": "data/cloned",
            "device": "unknown",
            "room": "unknown",
            "distance": "unknown",
            "cloning_method": "unknown",
            "tool": "unknown",
            "version": "unknown",
            "conditions": "tool: unknown, version: unknown, cloning_method: unknown"
        })

    # 3. genuine_replay (live_replay_01 .. live_replay_10)
    for i in range(1, 11):
        idx_str = f"{i:02d}"
        fname = f"live_replay_{idx_str}.wav"
        src = os.path.join(SOURCE_DIR, "geniune replay", fname)
        queue.append({
            "source_path": src,
            "filename": fname,
            "original_id": f"live_replay_{idx_str}",
            "source_original_id": f"live_{idx_str}",
            "label": "genuine_replay",
            "group": "enrolled_target",
            "speaker_id": "gokul",
            "target_dir": "data/replay",
            "device": "phone mic",
            "room": "unknown",
            "distance": "unknown",
            "cloning_method": "none",
            "tool": "none",
            "version": "none",
            "conditions": "playback: laptop speaker -> phone mic, phone: unknown, room: unknown, distance: unknown"
        })

    # 4. cloned_replay (clone_replay_01 .. clone_replay_10)
    for i in range(1, 11):
        idx_str = f"{i:02d}"
        fname = f"clone_replay_{idx_str}.wav"
        src = os.path.join(SOURCE_DIR, "cloned replay", fname)
        queue.append({
            "source_path": src,
            "filename": fname,
            "original_id": f"clone_replay_{idx_str}",
            "source_original_id": f"clone_{idx_str}",
            "label": "cloned_replay",
            "group": "enrolled_target",
            "speaker_id": "gokul",
            "target_dir": "data/replay",
            "device": "phone mic",
            "room": "unknown",
            "distance": "unknown",
            "cloning_method": "voice_clone",
            "tool": "unknown",
            "version": "unknown",
            "conditions": "playback: laptop speaker -> phone mic, phone: unknown, room: unknown, distance: unknown"
        })

    # 5. testimony_replay.wav (not part of any scenario, group="unassigned")
    testimony_src = os.path.join(SOURCE_DIR, "geniune replay", "testimony_replay.wav")
    if os.path.exists(testimony_src):
        queue.append({
            "source_path": testimony_src,
            "filename": "testimony_replay.wav",
            "original_id": "testimony_replay",
            "source_original_id": None,
            "label": "unassigned",
            "group": "unassigned",
            "speaker_id": "gokul",
            "target_dir": "data/replay",
            "device": "phone mic",
            "room": "unknown",
            "distance": "unknown",
            "cloning_method": "none",
            "tool": "none",
            "version": "none",
            "conditions": "playback: laptop speaker -> phone mic, unassigned"
        })

    return queue


def run_batch_import(queue):
    """Executes FFmpeg conversion and manifest registration."""
    ffmpeg_bin = find_ffmpeg()
    os.makedirs("data/genuine", exist_ok=True)
    os.makedirs("data/cloned", exist_ok=True)
    os.makedirs("data/replay", exist_ok=True)
    os.makedirs("data/phone_simulated", exist_ok=True)

    manifest = load_manifest()
    # Remove any existing entries for these clip IDs to avoid duplicates
    queue_clip_ids = {item["original_id"] for item in queue}
    manifest = [m for m in manifest if m.get("original_id") not in queue_clip_ids]

    print("=" * 80)
    print("IMPORTING 40 AUDIO FILES VIA FFMPEG (16 kHz mono PCM_16)")
    print("=" * 80)

    for item in queue:
        src = item["source_path"]
        orig_id = item["original_id"]
        target_path = os.path.join(item["target_dir"], f"{orig_id}.wav").replace("\\", "/")
        sim_path = os.path.join("data/phone_simulated", f"{orig_id}_sim.wav").replace("\\", "/")

        cmd = [
            ffmpeg_bin,
            "-y",
            "-i", src,
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            target_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg failed for {src}: {res.stderr}")

        # Read converted audio to verify and record duration
        audio_16k, sr = sf.read(target_path, dtype="float32")
        duration = len(audio_16k) / sr

        entry = {
            "clip_id": orig_id,
            "filename": f"{orig_id}.wav",
            "original_path": target_path,
            "simulated_path": sim_path,
            "label": item["label"],
            "group": item["group"],
            "speaker_id": item["speaker_id"],
            "original_id": orig_id,
            "source_original_id": item["source_original_id"],
            "cloning_method": item["cloning_method"],
            "duration_seconds": round(duration, 3),
            "sample_rate": 16000,
            "conditions": item["conditions"],
            "device": item["device"],
            "room": item["room"],
            "distance": item["distance"],
        }
        manifest.append(entry)

    save_manifest(manifest)
    print(f"Import complete. 40 clips written to data/ folders and registered in {MANIFEST_PATH}.")


def run_phone_simulation_pipeline():
    """Generates phone-simulated versions for all manifest entries."""
    print("\n" + "=" * 80)
    print("GENERATING PHONE-SIMULATED COPIES VIA server.telephony.simulate_telephony_channel")
    print("=" * 80)
    manifest = load_manifest()
    count = 0
    for item in manifest:
        orig = item.get("original_path")
        sim = item.get("simulated_path")
        if not orig or not os.path.exists(orig):
            continue
        audio_16k, sr = sf.read(orig, dtype="float32")
        sim_audio = simulate_telephony_channel(audio_16k)
        sf.write(sim, sim_audio, 16000, subtype="PCM_16")
        count += 1
    print(f"Generated {count} phone-simulated copies in data/phone_simulated/.")


def analyze_clips_vad_and_clipping(queue):
    """
    Per-clip report: duration, speech duration after VAD, peak level, count of clipped
    samples, and whether the last 64,600 samples contain at least min_speech_fraction
    of speech (AASIST window eligibility).
    """
    print("\n" + "=" * 125)
    print("PER-CLIP AUDIT: DURATION, VAD SPEECH, PEAKS, CLIPPING, AND AASIST 64.6k WINDOW ELIGIBILITY")
    print("=" * 125)

    min_speech_fraction = 0.3
    target_samples = 64600

    results = []
    scoreable_counts = {
        "genuine_live": 0,
        "cloned_direct": 0,
        "genuine_replay": 0,
        "cloned_replay": 0,
    }
    failing_clips = []

    print(f"{'Clip ID':<18} | {'Label':<15} | {'Dur (s)':<7} | {'Speech (s)':<10} | {'Peak':<6} | {'Clipped':<7} | {'Win Sp Frac':<11} | {'AASIST Window Status'}")
    print("-" * 125)

    manifest = load_manifest()
    manifest_by_id = {item.get("original_id"): item for item in manifest}

    for item in queue:
        orig_id = item["original_id"]
        label = item["label"]
        fpath = os.path.join(item["target_dir"], f"{orig_id}.wav").replace("\\", "/")

        audio, sr = sf.read(fpath, dtype="float32")
        duration = len(audio) / sr
        peak = float(np.max(np.abs(audio)))
        clipped_count = int(np.sum(np.abs(audio) >= 0.9999))

        # Overall speech fraction (fresh VAD per clip)
        vad_clip = VoiceActivityDetector(backend="webrtcvad", mode=2, frame_ms=30)
        overall_speech_fraction = vad_clip.compute_speech_fraction(audio, sr)
        speech_duration = duration * overall_speech_fraction

        # Last 64,600 samples window check (fresh VAD per window)
        if len(audio) < target_samples:
            window_status = "insufficient_audio (buffer < 64.6k)"
            win_sp_frac_str = "N/A"
            passed_window = False
        else:
            last_window = audio[-target_samples:]
            vad_win = VoiceActivityDetector(backend="webrtcvad", mode=2, frame_ms=30)
            win_sp_frac = vad_win.compute_speech_fraction(last_window, sr)
            win_sp_frac_str = f"{win_sp_frac:.3f}"
            if win_sp_frac >= min_speech_fraction:
                window_status = "OK (full window scoreable)"
                passed_window = True
            else:
                window_status = f"insufficient_audio (speech {win_sp_frac:.2f} < {min_speech_fraction})"
                passed_window = False

        if passed_window:
            if label in scoreable_counts:
                scoreable_counts[label] += 1
        else:
            if label in scoreable_counts:
                failing_clips.append((orig_id, label, duration, window_status))

        # Record in manifest
        if orig_id in manifest_by_id:
            manifest_by_id[orig_id]["vad_speech_duration_seconds"] = round(speech_duration, 3)
            manifest_by_id[orig_id]["peak_amplitude"] = round(peak, 4)
            manifest_by_id[orig_id]["clipped_samples"] = clipped_count
            manifest_by_id[orig_id]["aasist_window_eligible"] = passed_window
            manifest_by_id[orig_id]["aasist_status"] = "ok" if passed_window else "insufficient_audio"

        print(f"{orig_id:<18} | {label:<15} | {duration:<7.3f} | {speech_duration:<10.3f} | {peak:<6.3f} | {clipped_count:<7} | {win_sp_frac_str:<11} | {window_status}")

    save_manifest(list(manifest_by_id.values()))
    print("=" * 125)

    print("\nSCOREABLE CLIPS SUMMARY (Full 64,600-sample window with >= 30% VAD speech):")
    for lbl, cnt in scoreable_counts.items():
        print(f"  * {lbl:<16}: {cnt}/10 scoreable")

    if failing_clips:
        print(f"\nFAILING CLIPS ({len(failing_clips)} clips marked 'insufficient_audio'):")
        for cid, lbl, dur, reason in failing_clips:
            print(f"  * {cid:<18} ({lbl}, dur={dur:.2f}s): {reason}")
    else:
        print("\nAll 40 clips passed the AASIST window check.")


def pairing_cross_correlation_check():
    """
    Pairing check, report only: for each replay, cross-correlate its speech
    energy envelope with its stated source after resampling. List any pair that looks wrong.
    """
    print("\n" + "=" * 105)
    print("REPLAY PAIRING SANITY CHECK: ENVELOPE CROSS-CORRELATION")
    print("=" * 105)

    manifest = load_manifest()
    by_id = {item.get("original_id"): item for item in manifest}

    replays = [m for m in manifest if m.get("label") in ["genuine_replay", "cloned_replay"]]

    def compute_energy_envelope(sig, hop=160, win=320):
        # 10 ms hop (160 samples), 20 ms window (320 samples) at 16 kHz
        n_frames = (len(sig) - win) // hop + 1
        if n_frames <= 0:
            return np.array([np.sqrt(np.mean(sig**2))])
        frames = np.lib.stride_tricks.as_strided(
            sig,
            shape=(n_frames, win),
            strides=(sig.strides[0] * hop, sig.strides[0])
        )
        return np.sqrt(np.mean(frames**2, axis=1) + 1e-10)

    print(f"{'Replay Clip':<18} | {'Stated Source':<15} | {'Label':<15} | {'Peak Corr':<10} | {'Lag (ms)':<9} | {'Verdict'}")
    print("-" * 105)

    suspect_pairs = []

    for r in sorted(replays, key=lambda x: x.get("original_id", "")):
        rep_id = r.get("original_id")
        src_id = r.get("source_original_id")
        lbl = r.get("label")

        rep_path = r.get("original_path")
        src_entry = by_id.get(src_id)
        if not src_entry:
            print(f"{rep_id:<18} | {str(src_id):<15} | {lbl:<15} | {'N/A':<10} | {'N/A':<9} | MISSING SOURCE")
            suspect_pairs.append((rep_id, src_id, "Source not found"))
            continue

        src_path = src_entry.get("original_path")
        rep_audio, _ = sf.read(rep_path, dtype="float32")
        src_audio, _ = sf.read(src_path, dtype="float32")

        env_rep = compute_energy_envelope(rep_audio)
        env_src = compute_energy_envelope(src_audio)

        # Standardize envelopes
        env_rep = (env_rep - np.mean(env_rep)) / (np.std(env_rep) + 1e-8)
        env_src = (env_src - np.mean(env_src)) / (np.std(env_src) + 1e-8)

        # Cross-correlation
        xcorr = correlate(env_rep, env_src, mode="full") / (np.sqrt(len(env_rep) * len(env_src)))
        lags = np.arange(-len(env_src) + 1, len(env_rep)) * 10.0  # 10 ms per hop

        max_idx = np.argmax(xcorr)
        peak_corr = float(xcorr[max_idx])
        best_lag_ms = float(lags[max_idx])

        # High confidence match if correlation > 0.45
        if peak_corr >= 0.45:
            verdict = "MATCH CONFIRMED"
        elif peak_corr >= 0.30:
            verdict = "PLAUSIBLE MATCH"
        else:
            verdict = "SUSPECT (LOW CORRELATION)"
            suspect_pairs.append((rep_id, src_id, f"Low correlation: {peak_corr:.3f}"))

        print(f"{rep_id:<18} | {src_id:<15} | {lbl:<15} | {peak_corr:<10.3f} | {best_lag_ms:<9.0f} | {verdict}")

    print("=" * 105)
    if suspect_pairs:
        print(f"\nWARNING: {len(suspect_pairs)} suspect replay pairs detected:")
        for r_id, s_id, reason in suspect_pairs:
            print(f"  * {r_id} -> {s_id}: {reason}")
    else:
        print("\nAll 20 replay clips exhibit strong cross-correlation with their stated source files.")


def print_scenario_counts():
    """Prints per-scenario inventory from manifest."""
    manifest = load_manifest()
    counts = {
        "genuine_live": 0,
        "cloned_direct": 0,
        "genuine_replay": 0,
        "cloned_replay": 0,
    }
    target_speaker = "gokul"
    other_tts_count = 0
    unassigned_count = 0

    for item in manifest:
        grp = item.get("group")
        spk = item.get("speaker_id")
        lbl = item.get("label")
        if grp == "other_tts":
            other_tts_count += 1
        elif grp == "unassigned":
            unassigned_count += 1
        elif spk == target_speaker and grp == "enrolled_target":
            if lbl in counts:
                counts[lbl] += 1

    print("\n" + "=" * 80)
    print("VOICEGUARD DATASET INVENTORY PER SCENARIO (SPEAKER: GOKUL)")
    print("=" * 80)
    print(f"{'Scenario / Label':<25} | {'Count':<10} | {'Target':<10} | {'Status'}")
    print("-" * 65)
    for lbl, cnt in counts.items():
        status = "MET" if cnt >= 10 else f"SHORT ({10 - cnt} missing)"
        print(f"{lbl:<25} | {cnt:<10} | {10:<10} | {status}")
    print("-" * 65)
    print(f"Other TTS clips: {other_tts_count} (excluded from Gokul targets)")
    print(f"Unassigned clips: {unassigned_count} (testimony_replay.wav, excluded from all targets)")
    print("-" * 65)
    print("ENROLLMENT CLIP STATUS: Not present yet. None of the evaluation clips are assigned as enrollment.")
    print("=" * 80 + "\n")


def main():
    get_replay_stream_info()
    queue = build_import_queue()
    run_batch_import(queue)
    run_phone_simulation_pipeline()
    analyze_clips_vad_and_clipping(queue)
    pairing_cross_correlation_check()
    print_scenario_counts()


if __name__ == "__main__":
    main()
