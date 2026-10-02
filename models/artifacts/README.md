# VoiceGuard Model Artifacts & Provenance Registry

## 1. AASIST Checkpoint (SPOOF Detector)
- **Architecture**: AASIST (Audio Anti-Spoofing using Integrated Spectro-Temporal Graph Attention Networks)
- **Repository**: [`clovaai/aasist`](https://github.com/clovaai/aasist)
- **Verified Commit Hash**: `a04c9863f63d44471dde8a6abcb3b082b07cd1d1`
- **Source File**: `models/weights/AASIST.pth` in official repository
- **Local Path**: `models/artifacts/AASIST.pth`
- **File Size**: 1,281,532 bytes (~1.22 MB)
- **SHA256**: `51d2d9cf0738172f61e2a384ec50a54a55363240f67c971ed55a92435bc1a1c0`
- **Training Dataset**: ASVspoof 2019 Logical Access (LA)
- **Input Preprocessing Requirements**:
  - Sample Rate: 16,000 Hz, single channel (mono) float32
  - Exact Tensor Length: **64,600 samples** (~4.0375 seconds)
  - Audio shorter than 64,600 samples must be repeat-padded; longer audio must be windowed/truncated
- **Output Mapping Convention**:
  - The model outputs a raw 2-dimensional logit vector: `[logit_0, logit_1]`.
  - In the original ASVspoof 2019 / AASIST implementation (`main.py`), label 0 corresponds to **spoof** and label 1 corresponds to **bonafide**.
  - Therefore, `spoof_prob = softmax(logits)[0]` and `bonafide_prob = softmax(logits)[1]`.

---

## 2. SpeechBrain ECAPA-TDNN (SPEAKER Detector)
- **Model**: ECAPA-TDNN (Emphasized Channel Attention, Propagation and Aggregation)
- **Hugging Face Hub Source**: [`speechbrain/spkrec-ecapa-voxceleb`](https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb)
- **Hugging Face Revision (Commit SHA)**: `0f99f2d0ebe89ac095bcc5903c4dd8f72b367286`
- **Local Cache Path**: `models/artifacts/ecapa_voxceleb/`
- **Model File**: `embedding_model.ckpt`
- **File Size**: 83,316,686 bytes (~79.45 MB)
- **SHA256**: `0575cb64845e6b9a10db9bcb74d5ac32b326b8dc90352671d345e2ee3d0126a2`
- **Training Dataset**: VoxCeleb 1 + VoxCeleb 2
- **Input Preprocessing Requirements**:
  - Sample Rate: 16,000 Hz, mono
  - Variable duration allowed; standard evaluation uses 2.0s to 4.0s windows
- **Output Representation**:
  - 192-dimensional continuous speaker embedding vector
  - Raw speaker similarity is computed as standard cosine similarity:
    $$\text{cosine\_similarity}(e_1, e_2) = \frac{e_1 \cdot e_2}{\|e_1\| \|e_2\|} \in [-1.0, 1.0]$$
- **Windows Platform Strategy**:
  - Configured with `LocalStrategy.COPY` to prevent OS symlink permission errors (`WinError 1314`) on Windows.

---

## 3. Test Audio Clip Provenance & Manifest
All clips stored in `data/metadata/` for deterministic verification:

| Filename | Role | Source / Generator | Properties | SHA256 |
|---|---|---|---|---|
| `bonafide_speaker1_utt1.wav` | Bonafide Speaker 1 (Utterance 1) | SpeechBrain official test suite (`spk1_snt1.wav`) | 16 kHz mono WAV, real human speech | `2f7315ccf543b6368528b098cd895098c154f222cd55ff7b5f66b50feb383c56` |
| `bonafide_speaker1_utt2.wav` | Bonafide Speaker 1 (Utterance 2) | SpeechBrain official test suite (`spk1_snt2.wav`) | 16 kHz mono WAV, real human speech (same speaker, distinct sentence) | `e1f125a318f4026991bf78f5c41481be0fbcf9b3b2fd72284f9824cb851c3034` |
| `bonafide_speaker2_utt1.wav` | Bonafide Speaker 2 (Utterance 1) | SpeechBrain official test suite (`spk2_snt1.wav`) | 16 kHz mono WAV, real human speech (distinct speaker) | `5f3f534ba99f159358c6ee2e4fb5e42b3b9399f37f4e290651405c76095f26f0` |
| `spoof_tts.wav` | Spoof Neural TTS (Christopher) | Microsoft Edge Neural TTS API (`edge-tts`) | 16 kHz mono WAV | `3cd603217fc0ab9b6d9b3fff40fb54aaa1cd57d10eaf2cfe6baed8b80fe3719e` |
| `spoof_tts_aria.wav` | Spoof Neural TTS (Aria) | Microsoft Edge Neural TTS API (`edge-tts`) | 16 kHz mono WAV | `834526284f934998b555a89383d74c84b70ee1b06a74435b1513423ceb809ae3` |
| `spoof_tts_guy.wav` | Spoof Neural TTS (Guy) | Microsoft Edge Neural TTS API (`edge-tts`) | 16 kHz mono WAV | `4e55b02cb32bcaed0e6aae35a1bbe77fc76c6fdc96c413eb8916e251be8affa0` |
| `spoof_tts_sonia.wav` | Spoof Neural TTS (Sonia) | Microsoft Edge Neural TTS API (`edge-tts`) | 16 kHz mono WAV | `4a54ec8b096ddeef59d82f9b78577eb4191d78649f1bd309437ce9d427549d1e` |

- **Neural TTS Generation Parameters**:
  - `spoof_tts.wav`: Voice `en-US-ChristopherNeural`, Prompt: `"This is VoiceGuard verification system screening incoming telephone audio."`
  - `spoof_tts_aria.wav`: Voice `en-US-AriaNeural`, Prompt: `"Your security is our highest priority, please hold while we confirm your credentials."`
  - `spoof_tts_guy.wav`: Voice `en-US-GuyNeural`, Prompt: `"Good afternoon, I am calling regarding an unexpected withdrawal from your checking account."`
  - `spoof_tts_sonia.wav`: Voice `en-GB-SoniaNeural`, Prompt: `"Could you please confirm the one-time passcode sent to your registered mobile telephone number?"`
  - Zero synthetic noise; pure neural speech synthesis.

---

## 4. Software Attribution & Licenses
- **`models/aasist_net.py`**: Adapted from NAVER Corp. official repository (`clovaai/aasist`, commit `a04c9863f63d44471dde8a6abcb3b082b07cd1d1`), licensed under MIT License. Copyright (c) 2021-present NAVER Corp.
- **SpeechBrain**: Pretrained models provided by SpeechBrain under Apache-2.0.

## 5. Prior Prototype Checkpoints Notice (`..\30sep\ml\models\checkpoints`)
- `..\30sep\ml\models\checkpoints\aasist.pt`: 468 KB (114,343 parameters)
- `..\30sep\ml\models\checkpoints\ecapa.pt`: 448 KB (110,083 parameters)
- `..\30sep\ml\models\checkpoints\replay.pt`: 396 KB (97,508 parameters)

**Provenance Determination**: These files were generated as lightweight synthetic stubs for offline unit tests in a previous prototype. They lack true acoustic feature extractors, pretraining weights, and documented origins. **They are explicitly rejected and not used anywhere in VoiceGuard.**
