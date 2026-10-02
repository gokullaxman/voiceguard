"""
VoiceGuard Model and Test Data Acquisition Script
Acquires:
1. AASIST pretrained checkpoint from clovaai/aasist (commit a04c9863f63d44471dde8a6abcb3b082b07cd1d1)
2. SpeechBrain ECAPA-TDNN pretrained model from speechbrain/spkrec-ecapa-voxceleb
3. Real test audio clips from SpeechBrain official test repository
4. Real neural TTS spoof clip generated via edge-tts (model: en-US-ChristopherNeural)
"""

import asyncio
import hashlib
import os
import urllib.request
import soundfile as sf
import numpy as np
import librosa
import edge_tts
from speechbrain.inference.speaker import EncoderClassifier
from speechbrain.utils.fetching import LocalStrategy


def compute_sha256(filepath: str) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def ensure_dir(d: str):
    os.makedirs(d, exist_ok=True)


def download_file(url: str, dest_path: str):
    if not os.path.exists(dest_path):
        print(f"Downloading {url} -> {dest_path}")
        urllib.request.urlretrieve(url, dest_path)
    print(f"File ready: {dest_path} (SHA256: {compute_sha256(dest_path)})")


async def generate_neural_tts(prompt: str, voice: str, out_wav: str):
    ensure_dir(os.path.dirname(out_wav))
    temp_mp3 = out_wav + ".tmp.mp3"
    print(f"Generating Neural TTS via edge-tts (voice={voice})...")
    comm = edge_tts.Communicate(prompt, voice)
    await comm.save(temp_mp3)

    # Convert to 16 kHz mono WAV
    audio, sr = librosa.load(temp_mp3, sr=16000, mono=True)
    sf.write(out_wav, audio, 16000, subtype="PCM_16")
    if os.path.exists(temp_mp3):
        os.remove(temp_mp3)
    print(f"Generated neural TTS WAV: {out_wav} (SHA256: {compute_sha256(out_wav)})")


def main():
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    artifacts_dir = "models/artifacts"
    metadata_dir = "data/metadata"
    ensure_dir(artifacts_dir)
    ensure_dir(metadata_dir)

    # 1. AASIST weights
    aasist_path = os.path.join(artifacts_dir, "AASIST.pth")
    if not os.path.exists(aasist_path):
        aasist_url = "https://raw.githubusercontent.com/clovaai/aasist/a04c9863f63d44471dde8a6abcb3b082b07cd1d1/models/weights/AASIST.pth"
        download_file(aasist_url, aasist_path)
    else:
        print(f"AASIST checkpoint present: {aasist_path} (SHA256: {compute_sha256(aasist_path)})")

    # 2. SpeechBrain ECAPA-TDNN model
    ecapa_dir = os.path.join(artifacts_dir, "ecapa_voxceleb")
    ensure_dir(ecapa_dir)
    print("Loading/verifying SpeechBrain ECAPA model (LocalStrategy.COPY)...")
    _ = EncoderClassifier.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
        savedir=ecapa_dir,
        run_opts={"device": "cpu"},
        local_strategy=LocalStrategy.COPY
    )
    ecapa_model_path = os.path.join(ecapa_dir, "embedding_model.ckpt")
    if os.path.exists(ecapa_model_path):
        print(f"ECAPA model ready: {ecapa_model_path} (SHA256: {compute_sha256(ecapa_model_path)})")

    # 3. Real audio test clips (SpeechBrain repository benchmark files)
    test_clips = {
        "bonafide_speaker1_utt1.wav": "https://raw.githubusercontent.com/speechbrain/speechbrain/develop/tests/samples/ASR/spk1_snt1.wav",
        "bonafide_speaker1_utt2.wav": "https://raw.githubusercontent.com/speechbrain/speechbrain/develop/tests/samples/ASR/spk1_snt2.wav",
        "bonafide_speaker2_utt1.wav": "https://raw.githubusercontent.com/speechbrain/speechbrain/develop/tests/samples/ASR/spk2_snt1.wav",
    }
    for fname, url in test_clips.items():
        out_path = os.path.join(metadata_dir, fname)
        download_file(url, out_path)

    # 4. Real neural TTS spoof clip
    tts_wav = os.path.join(metadata_dir, "spoof_tts.wav")
    prompt = "This is VoiceGuard verification system screening incoming telephone audio."
    voice = "en-US-ChristopherNeural"
    if not os.path.exists(tts_wav):
        asyncio.run(generate_neural_tts(prompt, voice, tts_wav))
    else:
        print(f"Spoof TTS clip present: {tts_wav} (SHA256: {compute_sha256(tts_wav)})")

    print("\nAll models and test assets ready!")


if __name__ == "__main__":
    main()
