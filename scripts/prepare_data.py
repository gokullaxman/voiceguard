"""
VoiceGuard Dataset Preparation Pipeline
1. Scans original audio files in data/genuine/, data/cloned/, data/replay/.
2. Applies offline phone-channel simulation (WAV -> mono -> 8k -> mu-law -> 16k -> float32).
3. Saves phone-simulated copies into data/phone_simulated/.
4. Generates and updates data/metadata/manifest.json with full provenance.
5. Validates minimum target count (>= 10 per scenario for enrolled speaker 'gokul').
   Segregates edge-tts clips into an 'other_tts' group.
6. If any required recordings are missing, prints exact instructions and checklist.
"""

import json
import os
import sys
import numpy as np
import soundfile as sf
import yaml
from server.telephony import simulate_telephony_channel
from server.preprocessing import VoiceActivityDetector


MANIFEST_PATH = "data/metadata/manifest.json"
SETTINGS_PATH = "config/settings.yaml"


def load_settings():
    if os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return {}


def load_manifest():
    if os.path.exists(MANIFEST_PATH):
        try:
            with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_manifest(manifest):
    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def main():
    print("=" * 80)
    print("VOICEGUARD DATASET PREPARATION & TELEPHONY SIMULATION")
    print("=" * 80)

    settings = load_settings()
    dataset_cfg = settings.get("dataset", {})
    target_speaker = dataset_cfg.get("target_speaker_id", "gokul")
    min_target = dataset_cfg.get("min_samples_per_scenario", 10)

    os.makedirs("data/genuine", exist_ok=True)
    os.makedirs("data/cloned", exist_ok=True)
    os.makedirs("data/replay", exist_ok=True)
    os.makedirs("data/phone_simulated", exist_ok=True)
    os.makedirs("data/metadata", exist_ok=True)

    # Ingest existing metadata edge-tts clips into data/cloned if not already there
    for fname in ["spoof_tts.wav", "spoof_tts_aria.wav", "spoof_tts_guy.wav", "spoof_tts_sonia.wav"]:
        src = os.path.join("data/metadata", fname)
        dst = os.path.join("data/cloned", fname)
        if os.path.exists(src) and not os.path.exists(dst):
            data, sr = sf.read(src)
            sf.write(dst, data, sr, subtype="PCM_16")

    # Discover and simulate files
    manifest = load_manifest()
    manifest_by_path = {item.get("original_path"): item for item in manifest}

    scan_dirs = [
        ("data/genuine", "genuine_live"),
        ("data/cloned", "cloned_direct"),
        ("data/replay", "replay"),
    ]

    updated_manifest = []

    for directory, default_label in scan_dirs:
        for fname in os.listdir(directory):
            if not fname.lower().endswith((".wav", ".flac")):
                continue

            orig_path = os.path.join(directory, fname).replace("\\", "/")
            base_name, _ = os.path.splitext(fname)
            sim_path = os.path.join("data/phone_simulated", f"{base_name}_sim.wav").replace("\\", "/")

            # Read original audio
            audio, sr = sf.read(orig_path, dtype="float32")
            duration = len(audio) / sr

            # Perform telephony simulation
            sim_audio = simulate_telephony_channel(audio)
            sf.write(sim_path, sim_audio, 16000, subtype="PCM_16")

            # Determine metadata attributes
            existing_meta = manifest_by_path.get(orig_path, {})
            label = existing_meta.get("label", default_label)
            if label == "replay":
                label = "cloned_replay" if "cloned" in fname else "genuine_replay"

            # Check edge-tts / other TTS
            if "edge-tts" in existing_meta.get("cloning_method", "") or "spoof_tts" in fname:
                if fname == "spoof_tts.wav":
                    speaker_id = "tts_christopher"
                elif existing_meta.get("speaker_id") and existing_meta.get("speaker_id") != "tts_tts":
                    speaker_id = existing_meta.get("speaker_id")
                else:
                    speaker_id = f"tts_{fname.split('_')[-1].split('.')[0]}"
                cloning_method = "edge-tts"
                group = "other_tts"
            else:
                speaker_id = existing_meta.get("speaker_id", target_speaker)
                cloning_method = existing_meta.get("cloning_method", "none" if "genuine" in label else "voice_clone")
                group = existing_meta.get("group", "enrolled_target" if speaker_id == target_speaker else "impostor")

            entry = {
                "clip_id": existing_meta.get("clip_id", base_name),
                "filename": fname,
                "original_path": orig_path,
                "simulated_path": sim_path,
                "label": label,
                "group": group,
                "speaker_id": speaker_id,
                "original_id": existing_meta.get("original_id", base_name),
                "source_original_id": existing_meta.get("source_original_id"),
                "cloning_method": cloning_method,
                "duration_seconds": round(duration, 3),
                "sample_rate": sr,
                "conditions": existing_meta.get("conditions", "default recording"),
                "device": existing_meta.get("device", "unknown"),
                "room": existing_meta.get("room", "unknown"),
                "distance": existing_meta.get("distance", "unknown"),
            }
            for k in ["vad_speech_duration_seconds", "peak_amplitude", "clipped_samples", "aasist_window_eligible", "aasist_status"]:
                if k in existing_meta:
                    entry[k] = existing_meta[k]

            if "vad_speech_duration_seconds" not in entry:
                vad_clip = VoiceActivityDetector(backend="webrtcvad", mode=2, frame_ms=30)
                sp_frac = vad_clip.compute_speech_fraction(audio, sr)
                entry["vad_speech_duration_seconds"] = round(duration * sp_frac, 3)
                entry["peak_amplitude"] = round(float(np.max(np.abs(audio))), 4)
                entry["clipped_samples"] = int(np.sum(np.abs(audio) >= 0.9999))
                if len(audio) < 64600:
                    entry["aasist_window_eligible"] = False
                    entry["aasist_status"] = "insufficient_audio"
                else:
                    last_win = audio[-64600:]
                    vad_win = VoiceActivityDetector(backend="webrtcvad", mode=2, frame_ms=30)
                    win_sp_frac = vad_win.compute_speech_fraction(last_win, sr)
                    passed = win_sp_frac >= 0.3
                    entry["aasist_window_eligible"] = passed
                    entry["aasist_status"] = "ok" if passed else "insufficient_audio"
            updated_manifest.append(entry)

    save_manifest(updated_manifest)
    print(f"Telephony simulation complete. Processed {len(updated_manifest)} clips into data/phone_simulated/.")

    # Count statistics for enrolled speaker vs other TTS
    counts = {
        "genuine_live": 0,
        "cloned_direct": 0,
        "genuine_replay": 0,
        "cloned_replay": 0,
    }
    other_tts_count = 0

    for item in updated_manifest:
        lbl = item["label"]
        spk = item["speaker_id"]
        grp = item["group"]

        if grp == "other_tts":
            other_tts_count += 1
        elif spk == target_speaker and lbl in counts:
            counts[lbl] += 1

    print("\n" + "=" * 80)
    print(f"DATASET INVENTORY FOR ENROLLED SPEAKER: '{target_speaker.upper()}' (Target: >= {min_target} each)")
    print("=" * 80)
    print(f"{'Scenario / Label':<25} | {'Current Count':<15} | {'Target':<10} | {'Status'}")
    print("-" * 70)
    all_passed = True
    missing_checklist = {}

    for scenario, count in counts.items():
        status = "MET" if count >= min_target else f"MISSING ({min_target - count} needed)"
        if count < min_target:
            all_passed = False
            missing_checklist[scenario] = min_target - count
        print(f"{scenario:<25} | {count:<15} | {min_target:<10} | {status}")

    print("-" * 70)
    print(f"Other TTS clips (method=edge-tts, non-enrolled): {other_tts_count} clips")
    print("=" * 80)

    if not all_passed:
        print("\n" + "!" * 80)
        print("ACTION REQUIRED: REAL RECORDINGS NEEDED FROM DEVELOPER (GOKUL)")
        print("!" * 80)
        print("Per project rules, no fake data, synthetic noise or invented numbers may be used.")
        print(f"Please use `uv run python scripts/record_samples.py` to record the following:\n")

        if "genuine_live" in missing_checklist:
            n = missing_checklist["genuine_live"]
            print(f"1. [genuine_live] Need {n} recordings:")
            print(f"   - Speaker: Gokul")
            print(f"   - Environment: Quiet room, normal speaking volume")
            print(f"   - Hardware: Laptop microphone, distance approx 20-30 cm")
            print(f"   - Duration: 4 to 6 seconds per clip")
            print(f"   - Content: Read prompted security sentences (e.g. prompts 1-10 in recorder)\n")

        if "genuine_replay" in missing_checklist:
            n = missing_checklist["genuine_replay"]
            print(f"2. [genuine_replay] Need {n} recordings:")
            print(f"   - Speaker: Gokul (replayed)")
            print(f"   - Procedure: Play genuine_live clips through an external loudspeaker / second device")
            print(f"   - Capture: Record through the phone / primary microphone placed 10-15 cm from the speaker")
            print(f"   - Tag: Enter the corresponding source_original_id when prompted in the recorder\n")

        if "cloned_direct" in missing_checklist:
            n = missing_checklist["cloned_direct"]
            print(f"3. [cloned_direct] Need {n} recordings:")
            print(f"   - Speaker: Gokul's cloned voice")
            print(f"   - Procedure: Generate synthetic speech trained/cloned on Gokul's voice (e.g. ElevenLabs/F5-TTS/Tortoise)")
            print(f"   - Save in: data/cloned/ with filename format cloned_direct_gokul_<id>.wav\n")

        if "cloned_replay" in missing_checklist:
            n = missing_checklist["cloned_replay"]
            print(f"4. [cloned_replay] Need {n} recordings:")
            print(f"   - Speaker: Gokul's cloned voice (replayed)")
            print(f"   - Procedure: Play the cloned direct clips through external speaker, record through phone mic\n")

        print("=" * 80)
        print("Dataset preparation is stopped here until real recordings are supplied.")
        print("=" * 80)
        sys.exit(101)  # Distinct exit code signaling missing physical recordings
    else:
        print("\nAll minimum dataset targets met!")


if __name__ == "__main__":
    main()
