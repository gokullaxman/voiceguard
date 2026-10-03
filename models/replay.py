"""
VoiceGuard Acoustic Replay Detector (Phase 3 Step 6).
Detects acoustic physical playback and replay attacks in telephone audio.
Features:
  - Log-mel mean and std after per-clip mean/variance normalization (gain-invariant).
  - Sub-band energy ratios.
  - Spectral rolloff (mean, std).
  - Spectral flatness (mean, std).
Classifier:
  - Scikit-learn Logistic Regression with fixed C and StandardScaler.
"""

import os
from typing import Union, Tuple, Optional, Dict, Any
import numpy as np
import torch
import librosa
import joblib


class AcousticReplayDetector:
    """
    Acoustic Replay Detector for VoiceGuard telephony pipeline.
    Rejects NaN/Inf, requires min_samples (32,000 = 2.0s at 16 kHz).
    Returns replay_prob in [0.0, 1.0].
    """
    DEFAULT_CONFIG = {
        "sr": 16000,
        "n_fft": 1024,
        "hop_length": 512,
        "n_mels": 20,
        "sub_bands": [(0, 500), (500, 2000), (2000, 4000), (4000, 8000)],
        "roll_percent": 0.85
    }

    def __init__(self, model_path: Optional[str] = "models/artifacts/replay.joblib"):
        self.min_samples = 32000  # 2.0s at 16 kHz
        self.config = dict(self.DEFAULT_CONFIG)
        self.model = None

        if model_path and os.path.exists(model_path):
            artifact = joblib.load(model_path)
            if isinstance(artifact, dict) and "pipeline" in artifact:
                self.model = artifact["pipeline"]
                self.config = artifact.get("config", self.config)
            else:
                self.model = artifact

    def extract_features(self, audio: Union[np.ndarray, torch.Tensor]) -> Optional[np.ndarray]:
        """
        Extracts 48 gain-invariant acoustic features from 16 kHz audio:
          - 20 log-mel means (standardized per clip)
          - 20 log-mel stds (standardized per clip)
          - 4 sub-band energy ratios
          - 2 spectral rolloff moments (mean, std)
          - 2 spectral flatness moments (mean, std)
        """
        if isinstance(audio, torch.Tensor):
            if torch.isnan(audio).any() or torch.isinf(audio).any():
                raise ValueError("Audio contains NaN or Inf values")
            if audio.ndim > 1:
                audio = audio.squeeze()
            if audio.ndim > 1:
                audio = audio.mean(dim=-1)
            audio = audio.cpu().numpy()
        elif isinstance(audio, np.ndarray):
            if np.isnan(audio).any() or np.isinf(audio).any():
                raise ValueError("Audio contains NaN or Inf values")
            if audio.ndim > 1:
                audio = audio.squeeze()
            if audio.ndim > 1:
                audio = audio.mean(axis=-1)
        else:
            raise TypeError(f"Unsupported audio type: {type(audio)}")

        audio = audio.astype(np.float32)

        if len(audio) < self.min_samples:
            return None

        sr = self.config["sr"]
        n_fft = self.config["n_fft"]
        hop = self.config["hop_length"]
        n_mels = self.config["n_mels"]

        # 1. Log-mel spectrogram with per-clip mean/variance standardization (gain-invariant)
        mel_spec = librosa.feature.melspectrogram(
            y=audio, sr=sr, n_fft=n_fft, hop_length=hop, n_mels=n_mels
        )
        log_mel = np.log(np.maximum(mel_spec, 1e-6))
        # Standardize log-mel across time and frequency
        norm_log_mel = (log_mel - np.mean(log_mel)) / (np.std(log_mel) + 1e-9)
        mel_mean = np.mean(norm_log_mel, axis=1)  # (20,)
        mel_std = np.std(norm_log_mel, axis=1)    # (20,)

        # 2. Linear STFT & Sub-band energy ratios
        D = np.abs(librosa.stft(audio, n_fft=n_fft, hop_length=hop))
        power = D ** 2
        total_energy = np.sum(power) + 1e-9

        freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
        band_ratios = []
        for low_f, high_f in self.config["sub_bands"]:
            mask = (freqs >= low_f) & (freqs < high_f)
            band_e = np.sum(power[mask, :])
            band_ratios.append(band_e / total_energy)
        band_ratios = np.array(band_ratios, dtype=np.float32)  # (4,)

        # 3. Spectral rolloff (mean and std across frames)
        rolloff = librosa.feature.spectral_rolloff(
            y=audio, sr=sr, n_fft=n_fft, hop_length=hop, roll_percent=self.config["roll_percent"]
        )
        ro_mean = float(np.mean(rolloff))
        ro_std = float(np.std(rolloff))

        # 4. Spectral flatness (mean and std across frames)
        flatness = librosa.feature.spectral_flatness(y=audio, n_fft=n_fft, hop_length=hop)
        fl_mean = float(np.mean(flatness))
        fl_std = float(np.std(flatness))

        feat_vector = np.concatenate([
            mel_mean,
            mel_std,
            band_ratios,
            np.array([ro_mean, ro_std, fl_mean, fl_std], dtype=np.float32)
        ])
        return feat_vector

    def score(self, audio: Union[np.ndarray, torch.Tensor]) -> Tuple[Optional[float], str]:
        """
        Scores input audio.
        Returns (replay_prob, status).
        replay_prob is probability in [0.0, 1.0] that audio is replayed.
        """
        feats = self.extract_features(audio)
        if feats is None:
            return None, "too_short"

        if self.model is None:
            raise RuntimeError("Replay detector model artifact not loaded.")

        X = feats.reshape(1, -1)
        # Probability for class 1 (replay)
        probs = self.model.predict_proba(X)[0]
        replay_prob = float(probs[1])
        return replay_prob, "ok"
