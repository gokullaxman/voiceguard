"""
VoiceGuard Phone Recording Import Utility
Imports mobile/external recordings (m4a, wav, mp3, flac, aac),
converts them via FFmpeg to 16 kHz mono PCM_16 WAV,
applies telephony channel simulation, and registers provenance in the manifest.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import numpy as np
import soundfile as sf
import yaml
from server.telephony import simulate_telephony_channel


SETTINGS_PATH = "config/settings.yaml"
MANIFEST_PATH = "data/metadata/manifest.json"


def find_ffmpeg() -> str:
    """Finds FFmpeg executable in PATH or standard winget location."""
    path = shutil.which("ffmpeg")
    if path:
        return path
    winget_path = os.path.expandvars(
        r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
    )
    if os.path.exists(winget_path):
        return winget_path
    raise RuntimeError(
        "FFmpeg executable not found in PATH or standard winget install directory."
    )


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
    parser = argparse.ArgumentParser(
        description="Import audio recording into VoiceGuard dataset."
    )
    parser.add_argument(
        "--input", "-i", required=True, help="Path to input audio file (m4a, wav, mp3, etc.)"
    )
    parser.add_argument(
        "--label",
        "-l",
        required=True,
        choices=["genuine_live", "genuine_replay", "cloned_direct", "cloned_replay"],
        help="Dataset scenario label",
    )
    parser.add_argument(
        "--speaker_id",
        "-s",
        default="gokul",
        help="Speaker ID (default: gokul)",
    )
    parser.add_argument(
        "--original_id",
        "-id",
        default=None,
        help="Identifier for this clip (defaults to input filename stem)",
    )
    parser.add_argument(
        "--source_original_id",
        "-src",
        default=None,
        help="For replays: original_id of the source clip played",
    )
    parser.add_argument(
        "--device",
        "-d",
        default="phone_mic",
        help="Recording device / mic model (e.g. 'iPhone 13 mic', 'laptop mic')",
    )
    parser.add_argument(
        "--room",
        "-r",
        default="quiet_room",
        help="Acoustic environment description (e.g. 'bedroom', 'office')",
    )
    parser.add_argument(
        "--distance",
        default="20-30cm",
        help="Distance from mouth or speaker to mic (e.g. '20-30cm', '10-15cm')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate import and display actions without writing to disk",
    )

    args = parser.parse_args()

    input_path = os.path.abspath(args.input)
    if not os.path.exists(input_path):
        print(f"Error: Input file does not exist: {input_path}")
        sys.exit(1)

    stem = os.path.splitext(os.path.basename(input_path))[0]
    clip_id = args.original_id if args.original_id else stem

    # Validate replay provenance
    if "replay" in args.label and not args.source_original_id:
        print(f"Warning: Replay scenario '{args.label}' should ideally specify --source_original_id.")

    # Target folder selection
    if args.label == "genuine_live":
        target_dir = "data/genuine"
    elif args.label == "cloned_direct":
        target_dir = "data/cloned"
    else:
        target_dir = "data/replay"

    target_path = os.path.join(target_dir, f"{clip_id}.wav").replace("\\", "/")
    sim_path = os.path.join("data/phone_simulated", f"{clip_id}_sim.wav").replace("\\", "/")

    ffmpeg_bin = find_ffmpeg()
    ffmpeg_cmd = [
        ffmpeg_bin,
        "-y",
        "-i", input_path,
        "-ar", "16000",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        target_path,
    ]

    settings = load_settings()
    target_speaker = settings.get("dataset", {}).get("target_speaker_id", "gokul")

    group = "enrolled_target" if args.speaker_id == target_speaker else "impostor"
    cloning_method = "none" if "genuine" in args.label else "voice_clone"
    conditions = f"device: {args.device}, room: {args.room}, distance: {args.distance}"

    manifest_entry = {
        "clip_id": clip_id,
        "filename": f"{clip_id}.wav",
        "original_path": target_path,
        "simulated_path": sim_path,
        "label": args.label,
        "group": group,
        "speaker_id": args.speaker_id,
        "original_id": clip_id,
        "source_original_id": args.source_original_id,
        "cloning_method": cloning_method,
        "duration_seconds": None,
        "sample_rate": 16000,
        "conditions": conditions,
        "device": args.device,
        "room": args.room,
        "distance": args.distance,
    }

    print("=" * 80)
    print("VOICEGUARD RECORDING IMPORT")
    print("=" * 80)
    print(f"Input file:       {input_path}")
    print(f"Clip ID:          {clip_id}")
    print(f"Label:            {args.label}")
    print(f"Speaker ID:       {args.speaker_id}")
    print(f"Source ID:        {args.source_original_id}")
    print(f"Target path:      {target_path}")
    print(f"Simulated path:   {sim_path}")
    print(f"FFmpeg command:   {' '.join(ffmpeg_cmd)}")
    print("\nManifest entry preview:")
    print(json.dumps(manifest_entry, indent=2))
    print("=" * 80)

    if args.dry_run:
        print("[DRY RUN] No files were converted or written. Manifest was not modified.")
        return

    # Execute conversion
    os.makedirs(target_dir, exist_ok=True)
    os.makedirs("data/phone_simulated", exist_ok=True)

    print("\nRunning FFmpeg conversion to 16 kHz mono PCM_16...")
    subprocess.run(ffmpeg_cmd, check=True, capture_output=True)

    # Read converted audio
    audio_16k, sr = sf.read(target_path, dtype="float32")
    duration = len(audio_16k) / sr
    manifest_entry["duration_seconds"] = round(duration, 3)

    # Apply phone simulation
    print("Applying G.711 telephony channel simulation...")
    sim_audio = simulate_telephony_channel(audio_16k)
    sf.write(sim_path, sim_audio, 16000, subtype="PCM_16")

    # Update manifest
    manifest = load_manifest()
    manifest = [item for item in manifest if item.get("original_path") != target_path]
    manifest.append(manifest_entry)
    save_manifest(manifest)

    print(f"\nSuccessfully imported '{clip_id}':")
    print(f"  Duration:       {duration:.3f} s ({len(audio_16k)} samples)")
    print(f"  Original WAV:   {target_path}")
    print(f"  Simulated WAV:  {sim_path}")
    print(f"  Manifest:       {MANIFEST_PATH} updated.")


if __name__ == "__main__":
    main()
