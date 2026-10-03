"""
VoiceGuard SPEAKER Detector (ECAPA-TDNN) Tests
Validates:
1. Shape: embedding is 192-dimensional.
2. Range: cosine similarity is within [-1.0, 1.0].
3. Rejection of NaN and Inf audio with ValueError.
4. Too-short audio (< 2.0s / 32,000 samples) returns None and status 'too_short'.
5. Same-clip cosine similarity is ~1.0.
"""

import numpy as np
import pytest
import torch
from models.speaker import ECAPASpeakerDetector


@pytest.fixture(scope="module")
def detector():
    return ECAPASpeakerDetector(savedir="models/artifacts/ecapa_voxceleb", device="cpu")


def test_speaker_detector_shape_and_range(detector):
    """Verifies 192-dimensional embedding shape and [-1.0, 1.0] cosine similarity range."""
    np.random.seed(42)
    # 3.0 seconds of audio at 16 kHz
    audio1 = np.random.randn(48000).astype(np.float32) * 0.1
    audio2 = np.random.randn(48000).astype(np.float32) * 0.1

    emb1 = detector.extract_embedding(audio1)
    emb2 = detector.extract_embedding(audio2)

    assert emb1 is not None
    assert emb2 is not None
    assert emb1.shape == (192,), f"Expected shape (192,), got {emb1.shape}"
    assert emb2.shape == (192,), f"Expected shape (192,), got {emb2.shape}"

    sim = detector.cosine_similarity(emb1, emb2)
    assert -1.0 <= sim <= 1.0, f"Cosine similarity out of [-1, 1]: {sim}"


def test_speaker_detector_same_clip_similarity(detector):
    """Verifies that an audio clip compared with itself produces cosine similarity ~ 1.0."""
    np.random.seed(99)
    audio = np.random.randn(48000).astype(np.float32) * 0.1
    emb = detector.extract_embedding(audio)
    assert emb is not None

    sim, status = detector.score(audio, emb)
    assert status == "ok"
    assert sim is not None
    assert np.isclose(sim, 1.0, atol=1e-4), f"Expected similarity ~ 1.0, got {sim}"


def test_speaker_detector_too_short(detector):
    """Verifies that audio shorter than 2.0s (< 32,000 samples) is rejected."""
    np.random.seed(123)
    dummy_enrollment = np.random.randn(192).astype(np.float32)

    short_lengths = [0, 1000, 16000, 31999]
    for length in short_lengths:
        audio = np.random.randn(length).astype(np.float32) * 0.1
        emb = detector.extract_embedding(audio)
        assert emb is None, f"Expected None embedding for length {length}, got {emb}"

        score, status = detector.score(audio, dummy_enrollment)
        assert score is None, f"Expected None score for length {length}, got {score}"
        assert status == "too_short", f"Expected 'too_short' for length {length}, got {status}"


def test_speaker_detector_rejects_nan_inf(detector):
    """Verifies that audio containing NaN or Inf raises ValueError."""
    audio_valid = np.zeros(48000, dtype=np.float32)

    # Test numpy NaN
    audio_nan = audio_valid.copy()
    audio_nan[100] = np.nan
    with pytest.raises(ValueError, match="Audio contains NaN or Inf values"):
        detector.extract_embedding(audio_nan)

    # Test numpy Inf
    audio_inf = audio_valid.copy()
    audio_inf[100] = np.inf
    with pytest.raises(ValueError, match="Audio contains NaN or Inf values"):
        detector.extract_embedding(audio_inf)

    # Test torch Tensor NaN
    t_nan = torch.zeros(48000)
    t_nan[100] = float("nan")
    with pytest.raises(ValueError, match="Audio contains NaN or Inf values"):
        detector.extract_embedding(t_nan)
