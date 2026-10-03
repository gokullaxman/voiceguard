"""
VoiceGuard SPOOF Detector (AASIST) Tests
Validates:
1. Shape and windowing: exactly last 64,600 samples evaluated.
2. Range: spoof_prob is within [0.0, 1.0].
3. Too-short audio (< 64,600 samples) returns score None and status 'insufficient_audio'.
4. Rejection of NaN and Inf audio with ValueError.
"""

import numpy as np
import pytest
import torch
from models.spoof import AASISTSpoofDetector


@pytest.fixture(scope="module")
def detector():
    return AASISTSpoofDetector(checkpoint_path="models/artifacts/AASIST.pth")


def test_spoof_detector_range(detector):
    """Verifies that valid audio produces a finite score in [0.0, 1.0] with status 'ok'."""
    np.random.seed(42)
    audio = np.random.randn(64600).astype(np.float32) * 0.1
    score, status = detector.score(audio)
    assert status == "ok"
    assert score is not None
    assert 0.0 <= score <= 1.0


def test_spoof_detector_shape_and_windowing(detector):
    """
    Verifies that scoring uses exactly the last 64,600 samples:
    Prepending arbitrary audio before the same 64,600 samples produces the identical score.
    """
    np.random.seed(123)
    target_window = np.random.randn(64600).astype(np.float32) * 0.05
    score_target, status_target = detector.score(target_window)
    assert status_target == "ok"

    # Prepend 20,000 different samples
    prefix = np.sin(np.linspace(0, 500, 20000)).astype(np.float32) * 0.2
    extended_audio = np.concatenate([prefix, target_window])
    assert len(extended_audio) == 84600

    score_extended, status_extended = detector.score(extended_audio)
    assert status_extended == "ok"
    assert np.isclose(score_target, score_extended, atol=1e-5), (
        f"Scores differ: {score_target} vs {score_extended}"
    )


def test_spoof_detector_too_short(detector):
    """Verifies that audio shorter than 64,600 samples returns None and 'insufficient_audio'."""
    short_lengths = [0, 1000, 32000, 64599]
    for length in short_lengths:
        audio = np.zeros(length, dtype=np.float32)
        score, status = detector.score(audio)
        assert score is None, f"Expected None for length {length}, got {score}"
        assert status == "insufficient_audio", f"Expected insufficient_audio for length {length}, got {status}"

        # Test with return_logits=True
        score_l, logits, status_l = detector.score(audio, return_logits=True)
        assert score_l is None
        assert logits is None
        assert status_l == "insufficient_audio"


def test_spoof_detector_rejects_nan_inf(detector):
    """Verifies that audio containing NaN or Inf raises ValueError."""
    audio_valid = np.zeros(64600, dtype=np.float32)

    # Test numpy NaN
    audio_nan = audio_valid.copy()
    audio_nan[500] = np.nan
    with pytest.raises(ValueError, match="Audio contains NaN or Inf values"):
        detector.score(audio_nan)

    # Test numpy +Inf
    audio_pinf = audio_valid.copy()
    audio_pinf[500] = np.inf
    with pytest.raises(ValueError, match="Audio contains NaN or Inf values"):
        detector.score(audio_pinf)

    # Test numpy -Inf
    audio_ninf = audio_valid.copy()
    audio_ninf[500] = -np.inf
    with pytest.raises(ValueError, match="Audio contains NaN or Inf values"):
        detector.score(audio_ninf)

    # Test torch Tensor NaN
    t_nan = torch.zeros(64600)
    t_nan[500] = float('nan')
    with pytest.raises(ValueError, match="Audio contains NaN or Inf values"):
        detector.score(t_nan)
