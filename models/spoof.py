"""
VoiceGuard SPOOF Detector (AASIST)
Pretrained AASIST model using ASVspoof 2019 LA weights.
Architecture and weights source: clovaai/aasist (commit a04c9863f63d44471dde8a6abcb3b082b07cd1d1)
"""

from typing import Tuple, Union, Optional
import numpy as np
import torch
import torch.nn.functional as F
from torch import Tensor
from models.aasist_net import Model as AASISTArchitecture


class AASISTSpoofDetector:
    """
    AASIST anti-spoofing detector.
    
    ASVspoof 2019 LA AASIST output convention:
      Raw 2-logit output: [logit_0, logit_1]
      Index 0: spoof
      Index 1: bonafide
      spoof_prob = softmax(logits)[0]
    
    Scoring rule (Phase 3):
      - Audio must be 16 kHz mono float32.
      - Scores strictly the last 64,600 samples (~4.0375 s).
      - No window search, no padding or tiling.
      - If input length < 64,600 samples, returns (None, "insufficient_audio").
      - Rejects NaN and Inf values by raising ValueError.
    """
    def __init__(self, checkpoint_path: str = "models/artifacts/AASIST.pth", device: str = "cpu"):
        self.device = torch.device(device)
        self.nb_samp = 64600
        
        d_args = {
            "architecture": "AASIST",
            "nb_samp": self.nb_samp,
            "first_conv": 128,
            "filts": [70, [1, 32], [32, 32], [32, 64], [64, 64]],
            "gat_dims": [64, 32],
            "pool_ratios": [0.5, 0.7, 0.5, 0.5],
            "temperatures": [2.0, 2.0, 100.0, 100.0]
        }
        self.model = AASISTArchitecture(d_args).to(self.device)
        state_dict = torch.load(checkpoint_path, map_location=self.device, weights_only=False)
        self.model.load_state_dict(state_dict)
        self.model.eval()

    def score(
        self,
        audio: Union[np.ndarray, Tensor],
        return_logits: bool = False
    ) -> Union[Tuple[Optional[float], str], Tuple[Optional[float], Optional[np.ndarray], str]]:
        """
        Score input audio.
        Extracts exactly the last 64,600 samples without padding or tiling.
        Returns:
            If return_logits is False: (spoof_prob, status)
            If return_logits is True:  (spoof_prob, raw_logits, status)
        """
        if isinstance(audio, np.ndarray):
            if np.isnan(audio).any() or np.isinf(audio).any():
                raise ValueError("Audio contains NaN or Inf values")
            if audio.ndim > 1:
                audio = audio.squeeze()
            if audio.ndim > 1:
                audio = audio.mean(axis=-1)
            audio = torch.from_numpy(audio).float()
        elif isinstance(audio, Tensor):
            if torch.isnan(audio).any() or torch.isinf(audio).any():
                raise ValueError("Audio contains NaN or Inf values")
            if audio.ndim > 1:
                audio = audio.squeeze()
            if audio.ndim > 1:
                audio = audio.mean(dim=-1)
            audio = audio.float()
        else:
            raise TypeError(f"Unsupported audio type: {type(audio)}")

        length = audio.shape[0]
        if length < self.nb_samp:
            if return_logits:
                return None, None, "insufficient_audio"
            return None, "insufficient_audio"

        # Strictly the last 64,600 samples
        window = audio[-self.nb_samp:].unsqueeze(0).to(self.device)

        with torch.no_grad():
            _, logits = self.model(window)
            probs = F.softmax(logits, dim=-1)
            raw_logits = logits.cpu().numpy()[0]
            # Index 0 is spoof, index 1 is bonafide
            spoof_prob = float(probs[0, 0].item())

        if return_logits:
            return spoof_prob, raw_logits, "ok"
        return spoof_prob, "ok"
