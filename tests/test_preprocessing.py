"""
VoiceGuard Preprocessing & Spoof Window Gating Unit Tests
Validates:
1. VAD speech detection on silence vs speech.
2. Spoof gating: last 64,600 samples of rolling buffer.
3. Short buffer returns 'insufficient audio'.
4. Silence buffer returns 'insufficient audio'.
5. Valid speech window returns 'ok' with exactly 64,600 samples.
6. Amplitude guard strictly bounds [-1, 1] without scaling or normalization.
"""

import numpy as np
import pytest
import soundfile as sf
from server.preprocessing import (
    VoiceActivityDetector,
    RollingAudioBuffer,
    guard_amplitude
)


def test_vad_silence_vs_speech():
    """Validates VAD discrimination on pure silence vs harmonic speech tone."""
    vad = VoiceActivityDetector(backend="webrtcvad", mode=2)

    # 1 second of silence
    silence = np.zeros(16000, dtype=np.float32)
    frac_silence = vad.compute_speech_fraction(silence, 16000)
    assert frac_silence == 0.0, f"Expected 0.0 speech in silence, got {frac_silence}"

    # 1 second of voiced speech-like harmonic signal (400 Hz tone + harmonics)
    t = np.linspace(0, 1.0, 16000, endpoint=False, dtype=np.float32)
    speech_signal = (
        0.4 * np.sin(2 * np.pi * 300 * t) +
        0.2 * np.sin(2 * np.pi * 600 * t) +
        0.1 * np.sin(2 * np.pi * 900 * t)
    )
    frac_speech = vad.compute_speech_fraction(speech_signal, 16000)
    assert frac_speech > 0.8, f"Expected high speech fraction, got {frac_speech}"


def test_rolling_buffer_short_buffer_returns_insufficient_audio():
    """Validates that a buffer shorter than 64,600 samples is rejected without scoring."""
    buffer = RollingAudioBuffer(max_buffer_seconds=10.0, min_speech_fraction=0.3)

    # Append only 32,000 samples (2 seconds @ 16 kHz)
    short_audio = np.random.uniform(-0.2, 0.2, 32000).astype(np.float32)
    buffer.append(short_audio)

    window, status = buffer.get_spoof_window(target_samples=64600)
    assert window is None
    assert "insufficient audio" in status
    assert "buffer length (32000) < 64600" in status


def test_rolling_buffer_silence_returns_insufficient_audio():
    """Validates that a 64,600-sample buffer containing silence is rejected as insufficient speech."""
    buffer = RollingAudioBuffer(max_buffer_seconds=10.0, min_speech_fraction=0.3)

    # Append 80,000 samples of silence
    silence = np.zeros(80000, dtype=np.float32)
    buffer.append(silence)

    window, status = buffer.get_spoof_window(target_samples=64600)
    assert window is None
    assert "insufficient audio" in status
    assert "speech fraction (0.000) < minimum (0.3)" in status


def test_rolling_buffer_valid_speech_returns_ok_window():
    """Validates that a buffer with >= 64,600 samples of active speech returns exactly 64,600 samples and status 'ok'."""
    buffer = RollingAudioBuffer(max_buffer_seconds=10.0, min_speech_fraction=0.3)

    # Read a real human speech sample
    real_speech, sr = sf.read("data/metadata/bonafide_speaker1_utt1.wav", dtype="float32")
    # Tile speech to exceed 64,600 samples for the buffer test
    speech_stream = np.tile(real_speech, 3) # ~137,000 samples
    buffer.append(speech_stream)

    window, status = buffer.get_spoof_window(target_samples=64600)
    assert status == "ok"
    assert window is not None
    assert len(window) == 64600
    assert window.dtype == np.float32
    # Ensure window is the LAST 64,600 samples of the buffer
    np.testing.assert_array_equal(window, buffer._buffer[-64600:])


def test_guard_amplitude_bounds_without_normalization():
    """Validates that guard_amplitude clips outliers to [-1, 1] without modifying valid amplitudes."""
    test_wave = np.array([-1.5, -0.75, -0.2, 0.0, 0.2, 0.75, 1.5], dtype=np.float32)
    guarded = guard_amplitude(test_wave)

    assert guarded.dtype == np.float32
    # Outliers clipped
    assert guarded[0] == -1.0
    assert guarded[-1] == 1.0
    # In-range values unchanged (no normalization or scaling applied)
    assert np.isclose(guarded[1], -0.75)
    assert np.isclose(guarded[2], -0.2)
    assert np.isclose(guarded[3], 0.0)
    assert np.isclose(guarded[4], 0.2)
    assert np.isclose(guarded[5], 0.75)
