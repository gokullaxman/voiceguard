"""
Display Mel-Spectrogram Generator (Phase 5 Dashboard).
Label: "Mel-spectrogram (display only, not the model input)"
Computes downsampled int8 log-mel spectrogram matrix (max 64 mels x 300 frames).
Returns NO audio samples.
"""

from typing import Dict, Any, List
import numpy as np
import torch
import torchaudio

def compute_display_mel_spectrogram(audio_16k: np.ndarray, sr: int = 16000) -> Dict[str, Any]:
    """
    Computes a small downsampled int8 matrix (at most 64 mel bands x 300 frames) for UI visualization.
    Contains NO raw audio samples.
    """
    if len(audio_16k) == 0:
        return {
            "mel_matrix": [],
            "n_mels": 0,
            "n_frames": 0,
            "duration_sec": 0.0,
            "max_freq_hz": sr // 2,
            "label": "Mel-spectrogram (display only, not the model input)"
        }

    tensor = torch.from_numpy(audio_16k).float()
    if tensor.ndim == 1:
        tensor = tensor.unsqueeze(0)

    n_mels = 64
    n_fft = 512
    # Ensure at most 300 frames across duration
    duration = len(audio_16k) / sr
    hop_length = max(int(sr * 0.02), int(len(audio_16k) / 250))
    if hop_length <= 0:
        hop_length = 320

    mel_transform = torchaudio.transforms.MelSpectrogram(
        sample_rate=sr,
        n_fft=n_fft,
        hop_length=hop_length,
        n_mels=n_mels,
        power=2.0
    )
    mel = mel_transform(tensor).squeeze(0)  # (64, T)
    log_mel = torch.log(mel + 1e-6)

    # Downsample if T > 300
    if log_mel.shape[1] > 300:
        step = int(np.ceil(log_mel.shape[1] / 300.0))
        log_mel = log_mel[:, ::step]
        if log_mel.shape[1] > 300:
            log_mel = log_mel[:, :300]

    # Quantize to int8 [-128, 127]
    mi = log_mel.min()
    ma = log_mel.max()
    denom = ma - mi if (ma - mi) > 1e-6 else 1.0
    norm = (log_mel - mi) / denom
    int8_mat = (norm * 255.0 - 128.0).clamp(-128, 127).to(torch.int8)

    return {
        "mel_matrix": int8_mat.numpy().tolist(),
        "n_mels": int(int8_mat.shape[0]),
        "n_frames": int(int8_mat.shape[1]),
        "duration_sec": round(duration, 2),
        "max_freq_hz": sr // 2,
        "label": "Mel-spectrogram (display only, not the model input)"
    }
