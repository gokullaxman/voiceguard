"""
Unit and Integration Tests for VoiceGuard Voiceprint Encryption (Phase 3 Step 5).
Validates:
  - Exact float32 round trip
  - Wrong key rejected
  - 1-bit ciphertext flip rejected
  - Nonce tamper rejected
  - AAD tamper rejected
  - Missing key refuses
  - Missing consent refuses
"""

import os
import struct
import pytest
import numpy as np
from cryptography.exceptions import InvalidTag

from server.enrollment import (
    encrypt_voiceprint,
    decrypt_voiceprint,
    enroll_speaker,
    load_enrollment_key,
    MAGIC,
    NONCE_LENGTH
)


@pytest.fixture
def mock_embedding():
    np.random.seed(42)
    return np.random.randn(192).astype(np.float32)


@pytest.fixture
def test_key():
    return os.urandom(32)


def test_exact_float32_round_trip(mock_embedding, test_key):
    """Verifies bit-exact float32 reconstruction across encryption/decryption."""
    speaker_id = "test_speaker"
    timestamp = "2026-10-02T12:00:00Z"

    packed = encrypt_voiceprint(mock_embedding, speaker_id, test_key, timestamp=timestamp)
    decrypted_emb, header = decrypt_voiceprint(packed, test_key)

    assert header["speaker_id"] == speaker_id
    assert header["timestamp"] == timestamp
    assert header["dim"] == 192
    assert header["dtype"] == "float32"

    # Exact byte and value equality
    np.testing.assert_array_equal(mock_embedding, decrypted_emb)
    assert mock_embedding.tobytes() == decrypted_emb.tobytes()


def test_wrong_key_rejected(mock_embedding, test_key):
    """Verifies that an incorrect decryption key is rejected with InvalidTag."""
    wrong_key = os.urandom(32)
    packed = encrypt_voiceprint(mock_embedding, "speaker_a", test_key)

    with pytest.raises(InvalidTag):
        decrypt_voiceprint(packed, wrong_key)


def test_one_bit_ciphertext_flip_rejected(mock_embedding, test_key):
    """Verifies that flipping even a single bit in the ciphertext or tag fails authentication."""
    packed = bytearray(encrypt_voiceprint(mock_embedding, "speaker_a", test_key))

    # Target byte in the ciphertext payload (last byte)
    packed[-1] ^= 0x01

    with pytest.raises(InvalidTag):
        decrypt_voiceprint(bytes(packed), test_key)


def test_nonce_tamper_rejected(mock_embedding, test_key):
    """Verifies that altering the nonce causes authentication failure."""
    packed = bytearray(encrypt_voiceprint(mock_embedding, "speaker_a", test_key))

    # Locate nonce position: MAGIC (4) + len (4) + header_len
    header_len = struct.unpack(">I", packed[4:8])[0]
    nonce_idx = 8 + header_len

    # Tamper with the first byte of the nonce
    packed[nonce_idx] ^= 0x01

    with pytest.raises(InvalidTag):
        decrypt_voiceprint(bytes(packed), test_key)


def test_aad_tamper_rejected(mock_embedding, test_key):
    """Verifies that tampering with header AAD metadata (e.g. changing speaker_id) fails authentication."""
    speaker_id = "alice"
    timestamp = "2026-10-02T12:00:00Z"
    packed = encrypt_voiceprint(mock_embedding, speaker_id, test_key, timestamp=timestamp)

    # Reconstruct packet with a modified speaker_id in the header JSON
    offset = len(MAGIC)
    header_len = struct.unpack(">I", packed[offset:offset + 4])[0]
    offset += 4
    header_bytes = packed[offset:offset + header_len]
    offset += header_len
    nonce_and_ct = packed[offset:]

    # Tamper header JSON: change alice to bob
    tampered_header = header_bytes.replace(b"alice", b"bob  ")
    tampered_packet = (
        MAGIC +
        struct.pack(">I", len(tampered_header)) +
        tampered_header +
        nonce_and_ct
    )

    with pytest.raises(InvalidTag):
        decrypt_voiceprint(tampered_packet, test_key)


def test_missing_consent_refuses():
    """Verifies that enrollment refuses to execute without explicit consent=True."""
    with pytest.raises(ValueError, match="Explicit consent=True is required"):
        enroll_speaker(
            audio_path="data/enrollment/enrollment_candidate.wav",
            speaker_id="gokul",
            consent=False
        )


def test_missing_key_refuses(monkeypatch):
    """Verifies that enrollment refuses to run if VOICEGUARD_ENROLLMENT_KEY is missing."""
    monkeypatch.delenv("VOICEGUARD_ENROLLMENT_KEY", raising=False)

    with pytest.raises(ValueError, match="Missing VOICEGUARD_ENROLLMENT_KEY"):
        load_enrollment_key(env_path="nonexistent.env")
