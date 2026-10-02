"""
VoiceGuard SPEAKER Detector (ECAPA-TDNN)
Pretrained SpeechBrain ECAPA-TDNN model (speechbrain/spkrec-ecapa-voxceleb).
Extracts 192-dimensional speaker embeddings and computes raw cosine similarity.
"""

import os
from typing import Union
import numpy as np
import torch
import torch.nn.functional as F
from speechbrain.inference.speaker import EncoderClassifier
from speechbrain.utils.fetching import LocalStrategy


class ECAPASpeakerDetector:
    """
    Minimal ECAPA-TDNN speaker embedding extractor and cosine comparator for Phase P1.
    """
    def __init__(self, savedir: str = "models/artifacts/ecapa_voxceleb", device: str = "cpu"):
        os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
        self.device = device
        self.classifier = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir=savedir,
            run_opts={"device": self.device},
            local_strategy=LocalStrategy.COPY
        )

    def extract_embedding(self, audio: Union[np.ndarray, torch.Tensor]) -> np.ndarray:
        """
        Extracts 192-dimensional embedding from 16 kHz mono audio.
        """
        if isinstance(audio, np.ndarray):
            audio = torch.from_numpy(audio).float()
        if audio.ndim == 1:
            audio = audio.unsqueeze(0)
        audio = audio.to(self.device)

        with torch.no_grad():
            emb = self.classifier.encode_batch(audio)
            # Squeeze batch dimensions to (192,)
            emb = emb.squeeze().cpu().numpy()
        return emb

    @staticmethod
    def cosine_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
        """
        Computes raw cosine similarity between two 192-dim embeddings.
        """
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(emb1, emb2) / (norm1 * norm2))
