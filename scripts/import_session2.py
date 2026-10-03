import os
import json
import numpy as np
import soundfile as sf
import subprocess
from server.telephony import simulate_telephony_channel
from server.preprocessing import VoiceActivityDetector

MANIFEST_PATH = "data/metadata/manifest.json"
FULL_WAV_PATH = "data/genuine/session2_full.wav"
CANDIDATE_PATH = "C:/Users/Dell Latitude 7410/.gemini/antigravity-ide/brain/a18e2a80-1a10-459f-9aac-6edb5b242e63/scratch/enrollment_candidate.wav"

audio, sr = sf.read(FULL_WAV_PATH, dtype="float32")
assert sr == 16000, f"Expected 16kHz, got {sr}"
total_dur = len(audio) / sr

# 1. 20s Candidate span from first half
# Selected: [43.0, 63.0]
st_sec = 43.0
end_sec = 63.0
st_sample = int(st_sec * sr)
end_sample = int(end_sec * sr)

candidate_audio = audio[st_sample:end_sample]
assert len(candidate_audio) == 20 * sr

pk_cand = float(np.max(np.abs(candidate_audio)))
clp_cand = int(np.sum(np.abs(candidate_audio) >= 0.9999))
vad_cand = VoiceActivityDetector(backend="webrtcvad", mode=2, frame_ms=30)
frac_cand = vad_cand.compute_speech_fraction(candidate_audio, sr)
speech_dur_cand = round(len(candidate_audio) / sr * frac_cand, 3)

os.makedirs(os.path.dirname(CANDIDATE_PATH), exist_ok=True)
sf.write(CANDIDATE_PATH, candidate_audio, sr, subtype="PCM_16")

# Also phone simulation for enrollment candidate
sim_cand = simulate_telephony_channel(candidate_audio)
os.makedirs("data/phone_simulated", exist_ok=True)
sf.write("data/phone_simulated/enrollment_candidate_sim.wav", sim_cand, sr, subtype="PCM_16")

print("=== ENROLLMENT CANDIDATE SPAN ===")
print(f"File:            scratch/enrollment_candidate.wav")
print(f"Start time:      {st_sec:.3f} s")
print(f"End time:        {end_sec:.3f} s")
print(f"Duration:        20.000 s")
print(f"Speech fraction: {frac_cand:.4f} ({frac_cand*100:.2f}%)")
print(f"Speech duration: {speech_dur_cand:.3f} s")
print(f"Peak amplitude:  {pk_cand:.4f}")
print(f"Clipped samples: {clp_cand}")
print(f"Label:           enrollment")
print(f"Group:           enrollment")
print(f"Status:          pending_listening_review")

# 2. Cut rest of file into 5s segments, excluding candidate span plus 1s guard on each side: [42.0, 64.0]
guard_start = max(0.0, st_sec - 1.0)  # 42.0
guard_end = min(total_dur, end_sec + 1.0)  # 64.0

segments = []
# Region 1: [0.0, 42.0]
cur = 0.0
while cur + 5.0 <= guard_start:
    segments.append((cur, cur + 5.0))
    cur += 5.0

# Region 2: [64.0, total_dur]
cur = guard_end
while cur + 5.0 <= total_dur:
    segments.append((cur, cur + 5.0))
    cur += 5.0

print(f"\nGenerated {len(segments)} non-overlapping 5s segments outside [{guard_start:.1f}s, {guard_end:.1f}s].")

# Load manifest
with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
    manifest = json.load(f)

# Filter out any existing session2 or enrollment entries
manifest = [x for x in manifest if not x.get("original_id", "").startswith("session2_") and x.get("original_id") != "enrollment_candidate"]

# Add enrollment candidate
manifest.append({
    "clip_id": "enrollment_candidate",
    "filename": "enrollment_candidate.wav",
    "original_path": CANDIDATE_PATH,
    "simulated_path": "data/phone_simulated/enrollment_candidate_sim.wav",
    "label": "enrollment",
    "group": "enrollment",
    "status": "pending_listening_review",
    "speaker_id": "gokul",
    "original_id": "enrollment_candidate",
    "source_original_id": None,
    "cloning_method": "none",
    "duration_seconds": 20.0,
    "sample_rate": 16000,
    "device": "unknown",
    "room": "unknown",
    "distance": "unknown",
    "source_container": "mp4",
    "source_codec": "aac",
    "consent": "owner recording",
    "conditions": f"extracted from session2 [{st_sec}s - {end_sec}s]",
    "vad_speech_duration_seconds": speech_dur_cand,
    "peak_amplitude": round(pk_cand, 4),
    "clipped_samples": clp_cand,
    "aasist_window_eligible": True,
    "aasist_status": "ok"
})

# Save each 5s segment and add to manifest
for idx, (t0, t1) in enumerate(segments, start=1):
    seg_id = f"session2_seg_{idx:02d}"
    seg_fname = f"{seg_id}.wav"
    seg_path = os.path.join("data/genuine", seg_fname).replace("\\", "/")
    sim_path = os.path.join("data/phone_simulated", f"{seg_id}_sim.wav").replace("\\", "/")
    
    seg_audio = audio[int(t0 * sr):int(t1 * sr)]
    sf.write(seg_path, seg_audio, sr, subtype="PCM_16")
    
    seg_sim = simulate_telephony_channel(seg_audio)
    sf.write(sim_path, seg_sim, sr, subtype="PCM_16")
    
    pk = float(np.max(np.abs(seg_audio)))
    clp = int(np.sum(np.abs(seg_audio) >= 0.9999))
    
    # Fresh VAD for segment
    vad_seg = VoiceActivityDetector(backend="webrtcvad", mode=2, frame_ms=30)
    sp_frac = vad_seg.compute_speech_fraction(seg_audio, sr)
    vad_sp_sec = round(5.0 * sp_frac, 3)
    
    # Window check on last 64,600 samples (5s = 80,000 samples >= 64,600)
    last_win = seg_audio[-64600:]
    vad_win = VoiceActivityDetector(backend="webrtcvad", mode=2, frame_ms=30)
    win_sp_frac = vad_win.compute_speech_fraction(last_win, sr)
    status = "ok" if win_sp_frac >= 0.3 else "insufficient_audio"
    
    manifest.append({
        "clip_id": seg_id,
        "filename": seg_fname,
        "original_path": seg_path,
        "simulated_path": sim_path,
        "label": "genuine_live_extra",
        "group": "session2_extra",
        "speaker_id": "gokul",
        "original_id": seg_id,
        "source_original_id": None,
        "cloning_method": "none",
        "duration_seconds": 5.0,
        "sample_rate": 16000,
        "device": "unknown",
        "room": "unknown",
        "distance": "unknown",
        "source_container": "mp4",
        "source_codec": "aac",
        "consent": "owner recording",
        "conditions": f"session2 extracted [{t0:.1f}s - {t1:.1f}s]",
        "vad_speech_duration_seconds": vad_sp_sec,
        "peak_amplitude": round(pk, 4),
        "clipped_samples": clp,
        "aasist_window_eligible": (status == "ok"),
        "aasist_status": status
    })

# Save manifest
with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)

print("\n=== PER-LABEL MANIFEST INVENTORY ===")
label_counts = {}
for item in manifest:
    lbl = item.get("label", "unknown")
    label_counts[lbl] = label_counts.get(lbl, 0) + 1

for lbl, count in sorted(label_counts.items()):
    print(f"  * {lbl:<22}: {count}")

# Count by label (overall and enrolled target scenarios)
scenario_counts = {}
for item in manifest:
    if item.get("group") == "enrolled_target":
        lbl = item.get("label")
        scenario_counts[lbl] = scenario_counts.get(lbl, 0) + 1

print("\n=== ENROLLED TARGET SCENARIO COUNTS (SPEAKER: GOKUL) ===")
for lbl in ["genuine_live", "cloned_direct", "genuine_replay", "cloned_replay"]:
    print(f"  * {lbl:<22}: {scenario_counts.get(lbl, 0)} (target: 10)")
    assert scenario_counts.get(lbl) == 10, f"Expected 10 {lbl}, got {scenario_counts.get(lbl)}"

print("\nASSERTION PASSED: All 4 evaluation scenario counts for enrolled target are still exactly 10.")
