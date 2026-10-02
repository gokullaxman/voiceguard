"""
VoiceGuard Phase P1 Acceptance Gate Tests

Checks:
1. FFmpeg detected and runnable (prints ffmpeg version).
2. AASIST produces finite scores in [0, 1] on bonafide and spoof clips.
   Prints raw logits and probabilities for both. Does NOT assert spoof > bonafide.
3. ECAPA produces 192-dimensional embeddings for two speakers, and asserts
   that same-speaker cosine similarity > different-speaker cosine similarity.
"""

import os
import shutil
import subprocess
import numpy as np
import pytest
import soundfile as sf
from models.spoof import AASISTSpoofDetector
from models.speaker import ECAPASpeakerDetector


def test_ffmpeg_detected():
    """Acceptance Gate Item 1: FFmpeg executable is detected and runnable."""
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        # Check standard winget install path if PATH environment has not refreshed in current shell
        winget_path = os.path.expandvars(
            r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
        )
        if os.path.exists(winget_path):
            ffmpeg_path = winget_path

    assert ffmpeg_path is not None, "FFmpeg was not found in PATH or standard winget location"
    assert os.path.exists(ffmpeg_path), f"FFmpeg path does not exist: {ffmpeg_path}"

    res = subprocess.run([ffmpeg_path, "-version"], capture_output=True, text=True, check=True)
    first_line = res.stdout.strip().splitlines()[0]
    print(f"\n[GATE 1 - FFmpeg] Detected: {ffmpeg_path}")
    print(f"[GATE 1 - FFmpeg] Output: {first_line}")
    assert "ffmpeg version" in first_line.lower()


def test_aasist_real_inference():
    """
    Acceptance Gate Item 2: AASIST loads and produces finite scores in [0, 1].
    Prints raw logits and mapped spoof_prob. Does NOT assert spoof > bonafide.
    """
    bonafide_wav = "data/metadata/bonafide_speaker1_utt1.wav"
    spoof_wav = "data/metadata/spoof_tts.wav"

    assert os.path.exists(bonafide_wav), f"Missing test clip: {bonafide_wav}"
    assert os.path.exists(spoof_wav), f"Missing test clip: {spoof_wav}"

    detector = AASISTSpoofDetector(checkpoint_path="models/artifacts/AASIST.pth")

    audio_bonafide, sr1 = sf.read(bonafide_wav)
    audio_spoof, sr2 = sf.read(spoof_wav)

    spoof_prob_bonafide, logits_bonafide = detector.score(audio_bonafide)
    spoof_prob_spoof, logits_spoof = detector.score(audio_spoof)

    print("\n[GATE 2 - AASIST Inference]")
    print(f"Bonafide Clip ({bonafide_wav}):")
    print(f"  Raw Logits (spoof, bonafide): {logits_bonafide}")
    print(f"  Mapped spoof_prob (index 0): {spoof_prob_bonafide:.6f}")
    print(f"  Mapped bonafide_prob (index 1): {1.0 - spoof_prob_bonafide:.6f}")

    print(f"Spoof TTS Clip ({spoof_wav}):")
    print(f"  Raw Logits (spoof, bonafide): {logits_spoof}")
    print(f"  Mapped spoof_prob (index 0): {spoof_prob_spoof:.6f}")
    print(f"  Mapped bonafide_prob (index 1): {1.0 - spoof_prob_spoof:.6f}")

    # Assertions strictly per rule 5: finite and in [0, 1]
    assert np.isfinite(spoof_prob_bonafide), "Bonafide score is not finite"
    assert np.isfinite(spoof_prob_spoof), "Spoof score is not finite"
    assert 0.0 <= spoof_prob_bonafide <= 1.0, f"Bonafide score out of [0, 1]: {spoof_prob_bonafide}"
    assert 0.0 <= spoof_prob_spoof <= 1.0, f"Spoof score out of [0, 1]: {spoof_prob_spoof}"


def test_ecapa_speaker_discrimination():
    """
    Acceptance Gate Item 3: ECAPA produces 192-dim embeddings for two speakers,
    and same-speaker cosine similarity > different-speaker cosine similarity.
    """
    spk1_utt1 = "data/metadata/bonafide_speaker1_utt1.wav"
    spk1_utt2 = "data/metadata/bonafide_speaker1_utt2.wav"
    spk2_utt1 = "data/metadata/bonafide_speaker2_utt1.wav"

    for path in (spk1_utt1, spk1_utt2, spk2_utt1):
        assert os.path.exists(path), f"Missing speaker test clip: {path}"

    detector = ECAPASpeakerDetector(savedir="models/artifacts/ecapa_voxceleb")

    audio_s1_u1, _ = sf.read(spk1_utt1)
    audio_s1_u2, _ = sf.read(spk1_utt2)
    audio_s2_u1, _ = sf.read(spk2_utt1)

    emb_s1_u1 = detector.extract_embedding(audio_s1_u1)
    emb_s1_u2 = detector.extract_embedding(audio_s1_u2)
    emb_s2_u1 = detector.extract_embedding(audio_s2_u1)

    print("\n[GATE 3 - ECAPA Speaker Discrimination]")
    print(f"Embedding shape S1-U1: {emb_s1_u1.shape}")
    print(f"Embedding shape S1-U2: {emb_s1_u2.shape}")
    print(f"Embedding shape S2-U1: {emb_s2_u1.shape}")

    # Assert 192 dimensions
    assert emb_s1_u1.shape == (192,), f"Expected shape (192,), got {emb_s1_u1.shape}"
    assert emb_s1_u2.shape == (192,), f"Expected shape (192,), got {emb_s1_u2.shape}"
    assert emb_s2_u1.shape == (192,), f"Expected shape (192,), got {emb_s2_u1.shape}"

    sim_same = detector.cosine_similarity(emb_s1_u1, emb_s1_u2)
    sim_diff = detector.cosine_similarity(emb_s1_u1, emb_s2_u1)

    print(f"Same-speaker cosine similarity (S1-U1 vs S1-U2): {sim_same:.6f}")
    print(f"Different-speaker cosine similarity (S1-U1 vs S2-U1): {sim_diff:.6f}")

    # Assert same-speaker similarity exceeds different-speaker similarity
    assert sim_same > sim_diff, (
        f"Expected same-speaker similarity ({sim_same:.4f}) to exceed "
        f"different-speaker similarity ({sim_diff:.4f})"
    )
