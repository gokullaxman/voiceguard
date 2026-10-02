"""
VoiceGuard SPOOF Detector (AASIST)
Pretrained AASIST model using ASVspoof 2019 LA weights.
Architecture and weights source: clovaai/aasist (commit a04c9863f63d44471dde8a6abcb3b082b07cd1d1)
"""

import math
from typing import Tuple, Union
import numpy as np
import torch
import torch.nn.functional as F
from torch import Tensor
from models.aasist_net import Model as AASISTArchitecture


class AASISTSpoofDetector:
    """
    Minimal AASIST loader and scorer for Phase P1.
    Input requirement: 16 kHz audio, exactly 64,600 samples (~4.0375s).
    Output mapping:
      In ASVspoof 2019 LA AASIST, index 0 is spoof, index 1 is bonafide.
      spoof_prob = softmax(logits)[0]
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

    def preprocess_audio(self, audio: Union[np.ndarray, Tensor]) -> Tensor:
        if isinstance(audio, np.ndarray):
            audio = torch.from_numpy(audio).float()
        if audio.ndim > 1:
            audio = audio.squeeze()
        # Ensure length is 64600 samples (truncate or repeat/pad)
        length = audio.shape[0]
        if length < self.nb_samp:
            repeats = int(math.ceil(self.nb_samp / length))
            audio = audio.repeat(repeats)[:self.nb_samp]
        elif length > self.nb_samp:
            audio = audio[:self.nb_samp]
        return audio.unsqueeze(0).to(self.device)

    def score(self, audio: Union[np.ndarray, Tensor]) -> Tuple[float, np.ndarray]:
        tensor = self.preprocess_audio(audio)
        with torch.no_grad():
            _, logits = self.model(tensor)
            probs = F.softmax(logits, dim=-1)
            raw_logits = logits.cpu().numpy()[0]
            # Index 0 is spoof, index 1 is bonafide
            spoof_prob = float(probs[0, 0].item())
        return spoof_prob, raw_logits
