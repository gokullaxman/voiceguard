"""
VoiceGuard Interactive Sample Recorder
Records 16 kHz mono PCM_16 audio via sounddevice and writes metadata immediately after each take.
Usage: uv run python scripts/record_samples.py
"""

import json
import os
import time
import sounddevice as sd
import soundfile as sf
import numpy as np


SAMPLE_RATE = 16000
MANIFEST_PATH = "data/metadata/manifest.json"

PROMPTED_SENTENCES = [
    "My name is Gokul and this is my official VoiceGuard security voiceprint test.",
    "I authorize the transfer of five hundred dollars to my savings account.",
    "Please verify my telephone identity for access to the CresIgnite demonstration system.",
    "The quick brown fox jumps over the lazy dog near the telephone receiver.",
    "Artificial intelligence audio detection evaluates frequency trajectories and acoustic reflections.",
    "Confirming security passcode four eight one nine zero for two-factor authentication.",
    "VoiceGuard monitors live telephone streams to prevent unauthorized clone attacks.",
    "Speech recognition models extract acoustic features to evaluate speaker similarity.",
    "Replay attacks introduce speaker transducer distortion and room reverberation cues.",
    "This voice sample represents bonafide live human vocal production in real time."
]


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
    print("=" * 70)
    print("VOICEGUARD INTERACTIVE SAMPLE RECORDER (16 kHz Mono PCM_16)")
    print("=" * 70)

    print("\nSelect recording scenario:")
    print("  1. genuine_live   (Direct speech into microphone by enrolled speaker)")
    print("  2. genuine_replay (Play genuine audio on speaker, record via phone mic)")
    print("  3. cloned_replay  (Play cloned synthetic audio on speaker, record via phone mic)")
    print("  4. Exit")

    choice = input("\nEnter choice [1-4]: ").strip()
    if choice == "1":
        scenario = "genuine_live"
        folder = "data/genuine"
    elif choice == "2":
        scenario = "genuine_replay"
        folder = "data/replay"
    elif choice == "3":
        scenario = "cloned_replay"
        folder = "data/replay"
    else:
        print("Exiting recorder.")
        return

    os.makedirs(folder, exist_ok=True)

    speaker_id = input("Enter speaker_id [default: gokul]: ").strip() or "gokul"
    conditions = input("Enter recording conditions [e.g. laptop mic, quiet room, 20cm]: ").strip() or "laptop mic, quiet room, 20cm"
    source_original_id = None
    if "replay" in scenario:
        source_original_id = input("Enter source_original_id (the original clip played): ").strip()

    duration = float(input("Enter recording duration in seconds [default: 5.0]: ").strip() or "5.0")

    print("\nAvailable Prompt Sentences:")
    for idx, sentence in enumerate(PROMPTED_SENTENCES, 1):
        print(f"  {idx}. \"{sentence}\"")

    sentence_idx = input(f"Choose sentence prompt [1-{len(PROMPTED_SENTENCES)}] or press enter for custom: ").strip()
    if sentence_idx.isdigit() and 1 <= int(sentence_idx) <= len(PROMPTED_SENTENCES):
        prompt_text = PROMPTED_SENTENCES[int(sentence_idx) - 1]
    else:
        prompt_text = input("Enter custom transcript: ").strip()

    timestamp = int(time.time())
    clip_id = f"{scenario}_{speaker_id}_{timestamp}"
    filename = f"{clip_id}.wav"
    filepath = os.path.join(folder, filename)

    print("\n" + "-" * 70)
    print(f"Target file: {filepath}")
    print(f"Prompt: \"{prompt_text}\"")
    print(f"Duration: {duration} seconds")
    print("-" * 70)
    input("Press ENTER when ready to start recording...")

    print(">>> RECORDING IN PROGRESS... Speak now! <<<")
    audio = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype="float32")
    sd.wait()
    print(">>> RECORDING COMPLETE <<<")

    # Save 16 kHz mono PCM_16
    sf.write(filepath, audio, SAMPLE_RATE, subtype="PCM_16")

    # Update manifest immediately
    manifest = load_manifest()
    entry = {
        "clip_id": clip_id,
        "filename": filename,
        "original_path": filepath,
        "label": scenario,
        "speaker_id": speaker_id,
        "original_id": clip_id if "replay" not in scenario else (source_original_id or clip_id),
        "source_original_id": source_original_id,
        "cloning_method": "none" if "genuine" in scenario else "voice_clone",
        "duration_seconds": round(duration, 3),
        "sample_rate": SAMPLE_RATE,
        "prompt": prompt_text,
        "conditions": conditions,
        "recorded_at": timestamp
    }
    manifest.append(entry)
    save_manifest(manifest)

    print(f"\nSaved clip: {filepath}")
    print(f"Updated metadata manifest: {MANIFEST_PATH} (Total entries: {len(manifest)})")


if __name__ == "__main__":
    main()
