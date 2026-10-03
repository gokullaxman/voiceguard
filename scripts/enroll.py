"""
VoiceGuard CLI Enrollment Script (Phase 3 Step 5).
Encrypts a speaker voiceprint from an enrollment audio file.
Enforces explicit consent and secure key management.
"""

import os
import sys
import argparse
import subprocess
from server.enrollment import (
    load_enrollment_key,
    generate_and_save_key,
    enroll_speaker
)


def main():
    parser = argparse.ArgumentParser(description="VoiceGuard Voiceprint Enrollment CLI")
    parser.add_argument("--gen-key", action="store_true", help="Generate a fresh AES-256 enrollment key into .env after checking git-ignore")
    parser.add_argument("--consent", action="store_true", help="Explicit consent flag required to perform enrollment")
    parser.add_argument("--audio", type=str, default="data/enrollment/enrollment_candidate.wav", help="Path to enrollment audio file")
    parser.add_argument("--speaker-id", type=str, default="gokul", help="Speaker identifier")
    parser.add_argument("--out", type=str, default="data/enrollment/enrolled_voiceprint.bin", help="Path to output encrypted voiceprint binary")
    args = parser.parse_args()

    if args.gen_key:
        print("[Key Management] Checking .env git-ignore status...")
        res = subprocess.run(["git", "check-ignore", "-v", ".env"], capture_output=True, text=True)
        if res.returncode != 0 or not res.stdout.strip():
            print("ERROR: .env is NOT ignored by git. Aborting key generation for security.")
            sys.exit(1)
        print(f"Git-ignore confirmed: {res.stdout.strip()}")
        generate_and_save_key(".env")
        print("Success: Generated fresh 32-byte enrollment key and stored securely in .env.")
        print("Notice: The key is NOT printed to stdout/stderr in compliance with security rules.")

    if not args.consent:
        print("ERROR: Explicit consent is required to perform voiceprint enrollment.")
        print("Please supply the --consent flag to confirm owner/subject authorization.")
        sys.exit(1)

    print(f"\n[Enrollment] Processing enrollment file: {args.audio}")
    try:
        key_bytes = load_enrollment_key()
    except Exception as e:
        print(f"ERROR loading enrollment key: {e}")
        sys.exit(1)

    try:
        result = enroll_speaker(
            audio_path=args.audio,
            speaker_id=args.speaker_id,
            consent=args.consent,
            key_bytes=key_bytes,
            output_bin_path=args.out
        )
    except Exception as e:
        print(f"ERROR during enrollment: {e}")
        sys.exit(1)

    print(f"Enrollment successful for speaker: '{result['speaker_id']}'")
    print(f"Timestamp:       {result['timestamp']}")
    print(f"Encrypted file:  {result['output_bin_path']} ({result['ciphertext_bytes']} bytes)")
    
    # Check ignore on .bin
    res_bin = subprocess.run(["git", "check-ignore", "-v", result["output_bin_path"]], capture_output=True, text=True)
    print(f"Git-ignore check on encrypted voiceprint:\n  {res_bin.stdout.strip()}")


if __name__ == "__main__":
    main()
