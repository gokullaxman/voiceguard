# VoiceGuard Exhibition Demonstration Guide
**Label: SIMULATION, not a live call**

This guide provides the official exhibition script, scene walkthroughs, boundaries on claims, and technical Q&A for presenting VoiceGuard at CresIgnite Project Expo 2K26.

---

## 1. Unified Expectation & Match Rules

To ensure transparent and standardized evaluation during exhibition demonstrations:
- **genuine_live Clips**: Expected outcome = **Allow**.
- **Attack Clips (cloned_direct, genuine_replay, cloned_replay)**: Expected outcome = **Not Allow (Step-up or Block)**.
- **Outcome Definition (Whole Stream)**:
  - **Allow**: No action fired across the entire stream.
  - **Step-up only**: MOCK OTP step-up challenge fired, no block.
  - **Block**: Call termination block fired.
- **Match Criteria**:
  - `Match = (genuine and outcome is Allow) or (attack and outcome is Step-up only or Block)`
  - Mismatches are flagged prominently on the dashboard in amber:
    - Genuine clip with step-up/block -> **false step-up** / **false block**
    - Attack clip ending in Allow -> **missed**

---

## 2. Step 2 Demo Set Results & Honest Mismatch Guidance

> [!WARNING]
> **Superseded Prior Results**: Demo results before the window-cadence fix (demo.py < 640) are invalid and superseded.

### Demo Set Rehearsal Results (Evaluated Across 3 Runs at 2x Speed, Cadence-Aligned)

| Scenario ID | Title | Expected Outcome | Outcome (Whole Stream) | Final Band | Time 1st Action | Match? | Discrepancy Note |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `live_01` | Genuine Live Call 1 | Allow | Step-up only | LOW | 8.00s | **NO** | False step-up (Windows 1-3 scored MEDIUM; cause not measured) |
| `live_02` | Genuine Live Call 2 | Allow | Allow | LOW | None | **YES** | Clean Allow throughout (0 challenges fired; 5 windows) |
| `live_03` | Genuine Live Call 3 | Allow | Allow | LOW | None | **YES** | Clean Allow throughout (0 challenges fired; 5 windows) |
| `clone_01` | Direct Voice Clone 1 | Not Allow (Step-up or Block) | Step-up only | MEDIUM | 8.00s | **YES** | Step-Up challenge fired (3 windows) |
| `clone_02` | Direct Voice Clone 2 | Not Allow (Step-up or Block) | Allow | MEDIUM | None | **NO** | Missed (only 2 windows; clip ended before 3-window streak) |
| `live_replay_01` | Genuine Replay Attack 1 | Not Allow (Step-up or Block) | Block | MEDIUM | 8.00s | **YES** | Loudspeaker replay triggered Block (6 windows) |
| `live_replay_02` | Genuine Replay Attack 2 | Not Allow (Step-up or Block) | Block | HIGH | 8.00s | **YES** | Loudspeaker replay triggered Block (5 windows) |
| `clone_replay_01`| Cloned Replay Attack 1 | Not Allow (Step-up or Block) | Allow | LOW | None | **NO** | Missed (early risk dropped to LOW before 3-window streak) |
| `clone_replay_02`| Cloned Replay Attack 2 | Not Allow (Step-up or Block) | Block | HIGH | 8.00s | **YES** | Block action fired (4 windows) |

### How Presenters Must Describe Mismatches Truthfully
> [!IMPORTANT]
> **Never hide or explain away mismatches during the exhibition**:
> - When presenting **`live_01`**, point out the amber **`MISMATCH: false step-up`** pill on the dashboard.
> - Explain plainly: *"Notice that while the caller's voice settled firmly into the LOW risk band (Allow) by the end of the call, the first 3 windows sustained MEDIUM risk, triggering an early Step-Up (MOCK OTP) challenge at 8.00 seconds (`cause not measured`). This is an authentic artifact of rolling-buffer initialization under telephony simulation. It highlights why banking gateways employ progressive out-of-band step-up challenges rather than premature call termination."*
> - For **`clone_02`** and **`clone_replay_01`**, explain that short clips can terminate before the 3-consecutive-window sustained evidence threshold is reached, demonstrating the inherent operational trade-off between false alarm suppression and prompt attack interception.

---

## 3. Exhibition Three-Scene Script

### Scene 1: Legitimate Caller (Genuine Voice Verification)
- **Scenario**: `live_03` (or `live_01`) — *Genuine Live Call*
- **Intent**: Balance Inquiry (`+0.00` risk offset)
- **Expected Outcome**: **Allow** (Green / LOW risk band, `< 0.30`)
- **Key Narration**:
  > *"The gateway inspects the acoustic stream every 500 milliseconds. With live_03, the enrolled speaker's embedding matches reference parameters with minimal replay signatures. Fused risk remains below 0.30, allowing the caller to complete their routine inquiry without friction."*

### Scene 2: Synthetic Voice Clone Impersonation
- **Scenario**: `clone_01` — *Direct Voice Clone Attack*
- **Intent**: Credential Reset (`+0.15` risk offset)
- **Expected Outcome**: **Step-Up (MOCK OTP)** (Amber / MEDIUM risk band)
- **Key Narration**:
  > *"Here, an attacker plays a synthesized neural clone. While plausible to a human ear, high-dimensional ECAPA embeddings show subtle timbre shifts. Elevated intent pushes the fused risk into MEDIUM, firing a mock OTP step-up challenge."*

### Scene 3: Acoustic Loudspeaker Replay Attack
- **Scenario**: `clone_replay_02` — *Cloned Loudspeaker Replay Attack*
- **Intent**: Wire Transfer (`+0.20` risk offset)
- **Expected Outcome**: **Block** (Red / HIGH risk band)
- **Key Narration**:
  > *"Loudspeaker playback introduces distinct room coloration and physical transducer distortion. The acoustic replay detector catches this immediately, exceeding 0.90 risk. After 3 consecutive windows, the sustained evidence rule enforces an automated call block."*

---

## 4. Audio File Upload Analysis Walkthrough & Disclosures

The exhibition dashboard features an **"Analyse an audio file"** card enabling attendees and evaluators to test arbitrary audio files through the real-time scoring engine:

### How to Use the Upload Tool
1. **Choose an Audio File**: Drag and drop or browse for an audio file (`.wav`, `.mp3`, `.m4a`, `.ogg`, `.opus`, `.flac`, `.aac`, `.webm`). Validation constraints: 2.0s to 120s, maximum file size 25 MB.
2. **Select Parameters**:
   - **Action Sensitivity**: `balance_check` (+0.00), `password_reset` (+0.15), or `wire_transfer` (+0.20).
   - **Analysis Mode**: `stream` (streams 20 ms frames at full speed through a fresh `StreamingSession`) or `whole` (single fused clip score).
   - **Phone Simulation Checkbox**: Toggle 8 kHz G.711 mu-law bandpass filtering (default ON).
3. **Analyse**: Click **Analyse Audio**. Audio playback occurs exclusively in the browser using a local object URL (`URL.createObjectURL(file)`); audio is never echoed back by the server.
4. **Export**: Click **Download result as JSON** to retrieve the complete breakdown (metrics, scores, explanation, and warnings; strictly no audio bytes).

### Recommended Files to Try
- **Genuine Enrolled Voice**: `data/genuine/live_01.wav` &ndash; `live_03.wav`.
- **Cloned Speech**: `data/cloned/clone_01.wav` &ndash; `clone_02.wav`.
- **Acoustic Loudspeaker Replay**: `data/replay/live_replay_01.wav`, `clone_replay_02.wav`.
- **Lossy Compression Test**: Upload a WAV file, then upload a 128 kbps MP3 re-encoding of the same clip to observe codec quantization shifts on feature spaces.

### How to Read the Results
- **Risk Meter & Decision**: Risk score (0.00 to 1.00), band (LOW / MEDIUM / HIGH), and whole-stream outcome (`Allow`, `Step-up (mock OTP)`, or `Block`).
- **Detectors**: Speaker Verification (ECAPA similarity), Acoustic Replay Detector (probability), and Synthetic Spoof (strictly displayed as `OFF (domain shift, see limitations)`).
- **Per-Window Timeline**: Progression of 20 ms streaming frames and rolling buffer windows.
- **Active Warnings**: Displayed in amber (e.g. short clips, clipping, silence, single-speaker calibration).

### What NOT to Claim for Uploaded Audio
- Every upload carries the explicit label: **"UPLOAD ANALYSIS, not a validated accuracy figure"**.
- Calibrated for one enrolled speaker (`gokul`).
- Synthetic-speech detector (AASIST) is disabled.
- A "Block" or "Step-up" means the system is suspicious, not that the clip is proven fake.
- An "Allow" does not prove the clip is genuine.

### Empirical MP3 Lossy Compression Study (10 Genuine Live Recordings)
To evaluate the impact of lossy compression on upload streaming analysis:
- 10 original genuine_live clips (`live_01` &ndash; `live_10`) were screened across WAV, MP3 128 kbps, and MP3 64 kbps formats under upload analysis (phone_sim ON, stream mode).
- **Summary by Format (n=10)**:
  - **WAV**: 8/10 Allow (80.0% | Wilson 95% CI: [49.02%, 94.33%]), mean max risk = 0.3962, mean median speaker_sim = 0.3917, mean median replay_prob = 0.0001.
  - **MP3 128 kbps**: 8/10 Allow (80.0% | Wilson 95% CI: [49.02%, 94.33%]), mean max risk = 0.3922, mean median speaker_sim = 0.3923, mean median replay_prob = 0.0001.
  - **MP3 64 kbps**: 8/10 Allow (80.0% | Wilson 95% CI: [49.02%, 94.33%]), mean max risk = 0.3967, mean median speaker_sim = 0.3962, mean median replay_prob = 0.0001.
- **Measured Pattern (no causes)**: MP3 compression at 128 kbps or 64 kbps yielded identical discrete Allow decision rates (8/10) to uncompressed WAV with negligible mean risk delta (< 0.005).

---

## 5. Strict Presentation Boundaries: What NOT to Claim

1. **DO NOT claim universal deepfake protection**: The system does not claim 100% detection against unseen, state-of-the-art zero-shot generative models.
2. **DO NOT claim multi-speaker generalization**: The prototype is enrolled and calibrated specifically against a single target speaker (`gokul`).
3. **DO NOT claim AASIST is actively protecting calls**: AASIST is turned **OFF** (`weight: 0.0`) due to measured acoustic domain shift on non-studio microphones (`cause not measured`).
4. **DO NOT claim the replay detector is device-independent**: The replay detector relies on spectral coloration differences between recording and playback devices; open-world acoustic replay generalization remains unproven.
5. **DO NOT claim this is live carrier telephony**: The exhibition demo is a faithful **software simulation** streaming 20 ms G.711 mu-law frames over WebSocket. It is not connected to live carrier PSTN trunks.
6. **DO NOT claim Step-Up OTP sends real SMS or carrier DTMF**: In demo mode, step-up OTP is a mock UI simulation ("MOCK OTP").
7. **DO NOT claim upload scores are validated evaluation figures**: Uploaded audio is evaluated ad-hoc; every result is labeled **"UPLOAD ANALYSIS, not a validated accuracy figure"**.

---

## 6. Technical Q&A Cheat Sheet

### Q1: Why is the Synthetic Spoof Detector (AASIST) turned OFF?
> **Answer**: AASIST was trained on the ASVspoof 2019 dataset (studio-quality audio). On consumer smartphone and laptop microphones, it suffered severe acoustic domain shift, classifying bonafide live speech as 0.92–0.99 spoof probability. The cause is unmeasured (`cause not measured`). It was disabled in `config/settings.yaml` to prevent false rejections.

### Q2: How was system accuracy measured?
> **Answer**: Accuracy was measured in two distinct ways: (1) Whole-clip 5-fold cross-validation on 40 clips (97.5% for Config 2, though post-hoc selected), and (2) Real-time sustained-window streaming evaluation (70.0% decision rate on 40 clips under 3-consecutive-window rules). Neither should be called "the" accuracy.

### Q3: Why only one enrolled speaker?
> **Answer**: VoiceGuard was designed as an identity-centric voice gateway protecting specific enrolled accounts. As an undergraduate proof-of-concept, enrollment was performed on the primary developer's voice. Multi-speaker scaling involves enrolling multiple embeddings in the encrypted key-value store.

### Q4: Is this real telephony?
> **Answer**: The audio payload, format, and network protocol are identical to production telephony: 8kHz G.711 mu-law audio packaged into 20 ms chunks streamed over WebSockets, exactly as delivered by Twilio Voice Media Streams. In demo mode, frames are streamed from allowlisted evaluation recordings rather than over public cellular networks.

### Q5: Is the step-up verification real?
> **Answer**: In the exhibition simulation, the step-up OTP challenge is a mock interface simulation labeled "MOCK OTP". In the production telephony design, the gateway dispatches a TwiML `<Gather>` challenge to collect DTMF PINs.
