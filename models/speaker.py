"""
VoiceGuard SPEAKER Detector (ECAPA-TDNN)
Pretrained SpeechBrain ECAPA-TDNN model (speechbrain/spkrec-ecapa-voxceleb).
Extracts 192-dimensional speaker embeddings and computes raw cosine similarity.
"""

import os
from typing import Union, Tuple, Optional
import numpy as np
import torch
from speechbrain.inference.speaker import EncoderClassifier
from speechbrain.utils.fetching import LocalStrategy


class ECAPASpeakerDetector:
    """
    ECAPA-TDNN speaker embedding extractor and cosine comparator.
    
    Requirements (Phase 3 Step 4):
      - 16 kHz mono float32.
      - Reject NaN/Inf by raising ValueError.
      - Reject audio under 2.0 seconds (< 32,000 samples) with None / 'too_short'.
      - Embed full imported clip without VAD trimming or windowing.
      - Embedding computed in memory only; cosine similarity.
    """
    def __init__(self, savedir: str = "models/artifacts/ecapa_voxceleb", device: str = "cpu"):
        os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
        self.device = device
        self.min_samples = 32000  # 2.0 seconds at 16,000 Hz
        self.classifier = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir=savedir,
            run_opts={"device": self.device},
            local_strategy=LocalStrategy.COPY
        )

    def extract_embedding(self, audio: Union[np.ndarray, torch.Tensor]) -> Optional[np.ndarray]:
        """
        Extracts 192-dimensional embedding from 16 kHz mono audio.
        Returns None if audio is under 2.0 seconds (32,000 samples).
        Raises ValueError if audio contains NaN or Inf.
        """
        if isinstance(audio, np.ndarray):
            if np.isnan(audio).any() or np.isinf(audio).any():
                raise ValueError("Audio contains NaN or Inf values")
            if audio.ndim > 1:
                audio = audio.squeeze()
            if audio.ndim > 1:
                audio = audio.mean(axis=-1)
            audio = torch.from_numpy(audio).float()
        elif isinstance(audio, torch.Tensor):
            if torch.isnan(audio).any() or torch.isinf(audio).any():
                raise ValueError("Audio contains NaN or Inf values")
            if audio.ndim > 1:
                audio = audio.squeeze()
            if audio.ndim > 1:
                audio = audio.mean(dim=-1)
            audio = audio.float()
        else:
            raise TypeError(f"Unsupported audio type: {type(audio)}")

        if audio.shape[0] < self.min_samples:
            return None

        if audio.ndim == 1:
            audio = audio.unsqueeze(0)
        audio = audio.to(self.device)

        with torch.no_grad():
            emb = self.classifier.encode_batch(audio)
            emb = emb.squeeze().cpu().numpy()
        return emb

    @staticmethod
    def cosine_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
        """
        Computes raw cosine similarity between two 192-dim embeddings.
        """
        if emb1 is None or emb2 is None:
            raise ValueError("Cannot compute cosine similarity with None embedding")
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(emb1, emb2) / (norm1 * norm2))

    def score(self, audio: Union[np.ndarray, torch.Tensor], enrollment_emb: np.ndarray) -> Tuple[Optional[float], str]:
        """
        Scores input audio against enrollment embedding.
        Returns (similarity, status).
        """
        emb = self.extract_embedding(audio)
        if emb is None:
            return None, "too_short"
        sim = self.cosine_similarity(emb, enrollment_emb)
        return sim, "ok"
