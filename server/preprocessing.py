"""
VoiceGuard Preprocessing & Rolling Audio Buffer
VAD speech detection (webrtcvad with energy/ZCR fallback), amplitude bounds guard,
and rolling audio buffer enforcing the strict minimum-speech rule for AASIST.
"""

from typing import Optional, Tuple
import numpy as np


class VoiceActivityDetector:
    """
    Unified VAD interface supporting webrtcvad and energy+ZCR fallback.
    """
    def __init__(
        self,
        backend: str = "webrtcvad",
        mode: int = 2,
        frame_ms: int = 30,
        energy_threshold: float = 0.015,
        zcr_threshold: float = 0.05
    ):
        self.backend = backend
        self.mode = mode
        self.frame_ms = frame_ms
        self.energy_threshold = energy_threshold
        self.zcr_threshold = zcr_threshold
        self._vad = None

        if self.backend == "webrtcvad":
            try:
                import webrtcvad
                self._vad = webrtcvad.Vad(self.mode)
            except Exception:
                self.backend = "energy_zcr"

    def is_speech_frame(self, frame_float32: np.ndarray, sample_rate: int = 16000) -> bool:
        if self._vad is not None and self.backend == "webrtcvad":
            pcm_int16 = np.clip(frame_float32 * 32767.0, -32768, 32767).astype(np.int16)
            try:
                return self._vad.is_speech(pcm_int16.tobytes(), sample_rate)
            except Exception:
                pass

        # Fallback: Energy + ZCR
        energy = float(np.mean(frame_float32 ** 2))
        zero_crossings = float(np.mean(np.abs(np.diff(np.sign(frame_float32)))) / 2.0)
        return (energy > self.energy_threshold) and (zero_crossings < self.zcr_threshold)

    def compute_speech_fraction(self, audio_float32: np.ndarray, sample_rate: int = 16000) -> float:
        frame_size = int(sample_rate * (self.frame_ms / 1000.0))
        num_frames = len(audio_float32) // frame_size
        if num_frames == 0:
            return 0.0

        # Fresh webrtcvad.Vad instance for every clip and every window computation (order-independent)
        vad_inst = None
        if self.backend == "webrtcvad":
            try:
                import webrtcvad
                vad_inst = webrtcvad.Vad(self.mode)
            except Exception:
                pass

        speech_count = 0
        for i in range(num_frames):
            frame = audio_float32[i * frame_size:(i + 1) * frame_size]
            if vad_inst is not None:
                pcm_int16 = np.clip(frame * 32767.0, -32768, 32767).astype(np.int16)
                try:
                    if vad_inst.is_speech(pcm_int16.tobytes(), sample_rate):
                        speech_count += 1
                    continue
                except Exception:
                    pass

            if self.is_speech_frame(frame, sample_rate):
                speech_count += 1

        return float(speech_count / num_frames)


class RollingAudioBuffer:
    """
    In-memory rolling audio buffer for streaming live telephone calls.
    Enforces the production decision:
    - Never pads short audio.
    - Slices the last 64,600 samples for the spoof detector.
    - Gates inference on minimum VAD speech fraction in the window.
    """
    def __init__(
        self,
        max_buffer_seconds: float = 10.0,
        sample_rate: int = 16000,
        vad: Optional[VoiceActivityDetector] = None,
        min_speech_fraction: float = 0.3
    ):
        self.sample_rate = sample_rate
        self.max_samples = int(max_buffer_seconds * sample_rate)
        self.vad = vad or VoiceActivityDetector()
        self.min_speech_fraction = min_speech_fraction
        self._buffer = np.zeros(0, dtype=np.float32)

    def append(self, samples: np.ndarray):
        """Appends new 16 kHz float32 samples to the rolling buffer."""
        if samples.ndim > 1:
            samples = samples.mean(axis=1)
        samples = np.clip(samples.astype(np.float32), -1.0, 1.0)
        self._buffer = np.concatenate([self._buffer, samples])
        if len(self._buffer) > self.max_samples:
            self._buffer = self._buffer[-self.max_samples:]

    def clear(self):
        self._buffer = np.zeros(0, dtype=np.float32)

    @property
    def current_length(self) -> int:
        return len(self._buffer)

    def get_spoof_window(
        self,
        target_samples: int = 64600,
        min_speech_fraction: Optional[float] = None
    ) -> Tuple[Optional[np.ndarray], str]:
        """
        Extracts the last 64,600 samples from the rolling buffer for AASIST.
        Returns:
          (window_samples, "ok") if buffer has >= target_samples and passes VAD speech fraction.
          (None, "insufficient audio: ...") otherwise.
        """
        threshold = self.min_speech_fraction if min_speech_fraction is None else min_speech_fraction

        if len(self._buffer) < target_samples:
            return None, f"insufficient audio: buffer length ({len(self._buffer)}) < {target_samples}"

        # Take the exact last 64,600 samples
        window = self._buffer[-target_samples:]

        # Run VAD to compute speech fraction
        speech_frac = self.vad.compute_speech_fraction(window, self.sample_rate)
        if speech_frac < threshold:
            return None, f"insufficient audio: speech fraction ({speech_frac:.3f}) < minimum ({threshold})"

        return window, "ok"


def guard_amplitude(audio: np.ndarray) -> np.ndarray:
    """
    Strict amplitude guard: ensures audio is float32 and clamped to [-1.0, 1.0].
    Applies NO peak or RMS normalization.
    """
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    return np.clip(audio.astype(np.float32), -1.0, 1.0)
