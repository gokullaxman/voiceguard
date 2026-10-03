"""
VoiceGuard Enrollment & Encryption Service (Phase 3 Step 5).
Encrypts speaker voiceprints using AES-256-GCM with a 12-byte random nonce
and Associated Authenticated Data (AAD) consisting of speaker_id and timestamp.
Plaintext embeddings are kept in-memory only and never persisted.
"""

import os
import sys
import json
import base64
import struct
import datetime
import subprocess
from typing import Tuple, Dict, Any, Optional
import numpy as np
import soundfile as sf
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
from dotenv import load_dotenv

from models.speaker import ECAPASpeakerDetector

MAGIC = b"VGE1"
NONCE_LENGTH = 12


def load_enrollment_key(env_path: Optional[str] = ".env") -> bytes:
    """
    Loads and validates the 32-byte AES-256 key from VOICEGUARD_ENROLLMENT_KEY.
    Never prints or logs the key.
    """
    if env_path is not None:
        if os.path.exists(env_path):
            load_dotenv(dotenv_path=env_path)
    else:
        load_dotenv()

    key_b64 = os.getenv("VOICEGUARD_ENROLLMENT_KEY")
    if not key_b64:
        raise ValueError("Missing VOICEGUARD_ENROLLMENT_KEY in environment or .env file.")

    try:
        key_bytes = base64.b64decode(key_b64.strip())
    except Exception as e:
        raise ValueError("Failed to base64-decode VOICEGUARD_ENROLLMENT_KEY.") from e

    if len(key_bytes) != 32:
        raise ValueError(f"VOICEGUARD_ENROLLMENT_KEY must be exactly 32 bytes (got {len(key_bytes)} bytes).")

    return key_bytes


def generate_and_save_key(env_path: str = ".env") -> bool:
    """
    Generates a fresh 32-byte base64 key and writes it to .env
    ONLY AFTER confirming .env is git-ignored.
    Never prints or logs the key value.
    """
    # Check if .env is git-ignored
    res = subprocess.run(["git", "check-ignore", "-v", env_path], capture_output=True, text=True)
    if res.returncode != 0 or not res.stdout.strip():
        raise PermissionError(f"Safety check failed: {env_path} is NOT ignored by git. Refusing to write key.")

    key_bytes = os.urandom(32)
    key_b64 = base64.b64encode(key_bytes).decode("ascii")

    lines = []
    key_found = False
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("VOICEGUARD_ENROLLMENT_KEY="):
                    lines.append(f"VOICEGUARD_ENROLLMENT_KEY={key_b64}\n")
                    key_found = True
                else:
                    lines.append(line)

    if not key_found:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        lines.append(f"VOICEGUARD_ENROLLMENT_KEY={key_b64}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    return True


def encrypt_voiceprint(
    embedding: np.ndarray,
    speaker_id: str,
    key_bytes: bytes,
    timestamp: Optional[str] = None
) -> bytes:
    """
    Encrypts a float32 speaker embedding vector using AES-256-GCM.
    AAD = f"{speaker_id}:{timestamp}".encode("utf-8")
    Binary format:
      [4 bytes MAGIC]
      [4 bytes uint32 header_length]
      [header JSON bytes]
      [12 bytes nonce]
      [ciphertext + 16 bytes tag]
    """
    if timestamp is None:
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

    header_dict = {
        "speaker_id": speaker_id,
        "timestamp": timestamp,
        "dim": int(embedding.shape[0]),
        "dtype": "float32"
    }
    header_bytes = json.dumps(header_dict).encode("utf-8")
    header_len = len(header_bytes)

    aad = f"{speaker_id}:{timestamp}".encode("utf-8")
    nonce = os.urandom(NONCE_LENGTH)

    plaintext = embedding.astype(np.float32).tobytes()

    aesgcm = AESGCM(key_bytes)
    ciphertext_and_tag = aesgcm.encrypt(nonce, plaintext, aad)

    packed_data = (
        MAGIC +
        struct.pack(">I", header_len) +
        header_bytes +
        nonce +
        ciphertext_and_tag
    )
    return packed_data


def decrypt_voiceprint(
    packed_data: bytes,
    key_bytes: bytes
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Decrypts an enrolled voiceprint binary buffer.
    Verifies AAD, nonce, ciphertext, and tag.
    Returns (embedding_float32, header_dict).
    Raises InvalidTag if any authentication or integrity check fails.
    """
    if len(packed_data) < len(MAGIC) + 4 + NONCE_LENGTH + 16:
        raise ValueError("Invalid payload: buffer too short.")

    if not packed_data.startswith(MAGIC):
        raise ValueError("Invalid payload: magic signature mismatch.")

    offset = len(MAGIC)
    header_len = struct.unpack(">I", packed_data[offset:offset + 4])[0]
    offset += 4

    header_bytes = packed_data[offset:offset + header_len]
    offset += header_len

    try:
        header_dict = json.loads(header_bytes.decode("utf-8"))
    except Exception as e:
        raise ValueError("Failed to parse header JSON.") from e

    speaker_id = header_dict.get("speaker_id", "")
    timestamp = header_dict.get("timestamp", "")
    aad = f"{speaker_id}:{timestamp}".encode("utf-8")

    nonce = packed_data[offset:offset + NONCE_LENGTH]
    offset += NONCE_LENGTH

    ciphertext_and_tag = packed_data[offset:]

    aesgcm = AESGCM(key_bytes)
    # This will raise cryptography.exceptions.InvalidTag if key, nonce, ciphertext, tag, or AAD do not match
    plaintext = aesgcm.decrypt(nonce, ciphertext_and_tag, aad)

    embedding = np.frombuffer(plaintext, dtype=np.float32)
    return embedding, header_dict


def enroll_speaker(
    audio_path: str,
    speaker_id: str,
    consent: bool,
    key_bytes: Optional[bytes] = None,
    output_bin_path: str = "data/enrollment/enrolled_voiceprint.bin"
) -> Dict[str, Any]:
    """
    High-level enrollment pipeline:
      1. Enforces explicit consent == True.
      2. Validates/loads encryption key.
      3. Extracts ECAPA-TDNN embedding in memory.
      4. Encrypts embedding via AES-256-GCM.
      5. Writes ciphertext to output_bin_path.
      6. Returns metadata without exposing embedding or key.
    """
    if consent is not True:
        raise ValueError("Explicit consent=True is required for speaker enrollment. Refusing without consent.")

    if key_bytes is None:
        key_bytes = load_enrollment_key()

    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Enrollment audio file not found: {audio_path}")

    audio, sr = sf.read(audio_path, dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    detector = ECAPASpeakerDetector(device="cpu")
    embedding = detector.extract_embedding(audio)
    if embedding is None:
        raise ValueError(f"Audio file {audio_path} is too short (< 2.0s) for speaker enrollment.")

    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    encrypted_blob = encrypt_voiceprint(embedding, speaker_id, key_bytes, timestamp=timestamp)

    os.makedirs(os.path.dirname(output_bin_path), exist_ok=True)
    with open(output_bin_path, "wb") as f:
        f.write(encrypted_blob)

    return {
        "status": "success",
        "speaker_id": speaker_id,
        "timestamp": timestamp,
        "audio_path": audio_path,
        "output_bin_path": output_bin_path,
        "ciphertext_bytes": len(encrypted_blob)
    }
