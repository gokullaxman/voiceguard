"""
Unit tests for VoiceGuard Acoustic Replay Detector (models/replay.py).
Tests:
  - Rejects NaN input with ValueError.
  - Rejects Inf input with ValueError.
  - Rejects too-short input (< 2.0s / 32,000 samples) with (None, "too_short").
  - Produces valid replay_prob in [0.0, 1.0] for valid audio.
  - Correct input types (numpy array, torch Tensor).
"""

import os
import pytest
import numpy as np
import torch

from models.replay import AcousticReplayDetector


@pytest.fixture
def replay_detector():
    return AcousticReplayDetector(model_path="models/artifacts/replay.joblib")


def test_replay_detector_rejects_nan(replay_detector):
    """Verifies that audio containing NaN raises ValueError."""
    audio = np.random.randn(32000).astype(np.float32)
    audio[100] = np.nan
    with pytest.raises(ValueError, match="NaN or Inf"):
        replay_detector.score(audio)

    tensor_audio = torch.from_numpy(audio)
    with pytest.raises(ValueError, match="NaN or Inf"):
        replay_detector.score(tensor_audio)


def test_replay_detector_rejects_inf(replay_detector):
    """Verifies that audio containing Inf raises ValueError."""
    audio = np.random.randn(32000).astype(np.float32)
    audio[500] = np.inf
    with pytest.raises(ValueError, match="NaN or Inf"):
        replay_detector.score(audio)


def test_replay_detector_too_short(replay_detector):
    """Verifies that audio under 32,000 samples returns (None, 'too_short')."""
    short_audio = np.random.randn(31999).astype(np.float32)
    prob, status = replay_detector.score(short_audio)
    assert prob is None
    assert status == "too_short"


def test_replay_detector_valid_score(replay_detector):
    """Verifies that valid audio produces replay_prob in [0.0, 1.0] and status 'ok'."""
    np.random.seed(42)
    valid_audio = np.random.randn(32000).astype(np.float32) * 0.1
    prob, status = replay_detector.score(valid_audio)
    assert status == "ok"
    assert prob is not None
    assert 0.0 <= prob <= 1.0


def test_replay_detector_tensor_input(replay_detector):
    """Verifies that torch.Tensor input is supported."""
    torch.manual_seed(42)
    valid_tensor = torch.randn(32000, dtype=torch.float32) * 0.1
    prob, status = replay_detector.score(valid_tensor)
    assert status == "ok"
    assert prob is not None
    assert 0.0 <= prob <= 1.0
