"""
Self-check script: scripts/check_upload_path.py
Uploads original evaluation clips through the real upload endpoint (via TestClient)
with phone_sim ON and mode "stream", comparing outcomes with scratch/streaming_eval.json.
Also re-encodes a clip as MP3 128kbps to compare lossy compression effects.
"""

import os
import sys
import json
import tempfile
import subprocess
from pathlib import Path
from fastapi.testclient import TestClient

from server.app import app

CLIPS_TO_CHECK = [
    {"id": "live_01", "path": "data/genuine/live_01.wav", "group": "genuine_live"},
    {"id": "live_02", "path": "data/genuine/live_02.wav", "group": "genuine_live"},
    {"id": "live_03", "path": "data/genuine/live_03.wav", "group": "genuine_live"},
    {"id": "clone_01", "path": "data/cloned/clone_01.wav", "group": "cloned_direct"},
    {"id": "clone_02", "path": "data/cloned/clone_02.wav", "group": "cloned_direct"},
    {"id": "live_replay_01", "path": "data/replay/live_replay_01.wav", "group": "genuine_replay"},
    {"id": "live_replay_02", "path": "data/replay/live_replay_02.wav", "group": "genuine_replay"},
    {"id": "clone_replay_01", "path": "data/replay/clone_replay_01.wav", "group": "cloned_replay"},
    {"id": "clone_replay_02", "path": "data/replay/clone_replay_02.wav", "group": "cloned_replay"},
]


def load_streaming_eval_lookup() -> dict:
    eval_path = Path("scratch/streaming_eval.json")
    if not eval_path.exists():
        return {}
    with open(eval_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    lookup = {}
    for c in data.get("clips", []):
        lookup[c["clip_id"]] = c
    return lookup


def main():
    print("================================================================================")
    print("STEP 3: UPLOAD PATH SELF-CHECK WITH EVALUATION CLIPS")
    print("Label: UPLOAD ANALYSIS, not a validated accuracy figure")
    print("================================================================================")

    eval_lookup = load_streaming_eval_lookup()
    client = TestClient(app)

    results = []
    differences = []

    for item in CLIPS_TO_CHECK:
        clip_id = item["id"]
        clip_path = item["path"]

        if not os.path.exists(clip_path):
            print(f"Error: {clip_path} not found")
            continue

        with open(clip_path, "rb") as f:
            file_bytes = f.read()

        resp = client.post(
            "/analyze/upload",
            files={"file": (os.path.basename(clip_path), file_bytes, "audio/wav")},
            data={"action_sensitivity": "balance_check", "mode": "stream", "phone_sim": "true"}
        )

        if resp.status_code != 200:
            print(f"Failed to analyze {clip_id}: status {resp.status_code} {resp.text}")
            continue

        data = resp.json()
        upload_outcome = data.get("outcome") or data.get("whole_stream_outcome")
        upload_band = data.get("final_band") or data.get("band")

        windows = data.get("windows", [])
        max_risk = max([w.get("risk", 0.0) for w in windows]) if windows else data.get("risk", 0.0)

        # Baseline from streaming_eval.json
        base_item = eval_lookup.get(clip_id, {})
        base_outcome = base_item.get("outcome", "N/A")
        base_band = base_item.get("final_band", "N/A")
        base_max_risk = base_item.get("max_risk", "N/A")

        differs = (upload_outcome != base_outcome)
        if differs:
            differences.append({
                "clip_id": clip_id,
                "upload_outcome": upload_outcome,
                "streaming_eval_outcome": base_outcome,
                "note": "cause not measured"
            })

        results.append({
            "id": clip_id,
            "group": item["group"],
            "upload_outcome": upload_outcome,
            "upload_band": upload_band,
            "upload_max_risk": round(max_risk, 4),
            "eval_outcome": base_outcome,
            "eval_band": base_band,
            "eval_max_risk": base_max_risk,
            "differs": differs
        })

    # Print Table
    print(f"\n{'Clip ID':<16} {'Group':<16} {'Upload Outcome':<16} {'Final Band':<12} {'Max Risk':<10} {'Eval Outcome':<16} {'Differs?'}")
    print("-" * 92)
    for r in results:
        diff_str = "YES (diff)" if r["differs"] else "NO"
        print(f"{r['id']:<16} {r['group']:<16} {r['upload_outcome']:<16} {r['upload_band']:<12} {r['upload_max_risk']:<10.4f} {str(r['eval_outcome']):<16} {diff_str}")

    print("\n--------------------------------------------------------------------------------")
    print("Outcome Discrepancy Analysis:")
    if differences:
        for d in differences:
            print(f"- Clip {d['clip_id']}: upload-path outcome '{d['upload_outcome']}' differs from streaming_eval outcome '{d['streaming_eval_outcome']}' -> {d['note']}")
    else:
        print("All 9 clips matched their streaming_eval.json outcomes exactly.")
    print("--------------------------------------------------------------------------------")

    # Part 4: Lossy Compression Test (WAV vs MP3 128 kbps)
    test_clip = CLIPS_TO_CHECK[0]  # live_01.wav
    wav_path = test_clip["path"]
    print(f"\nLossy Compression Test on {test_clip['id']} (WAV vs MP3 128kbps):")

    with tempfile.TemporaryDirectory() as tmp_dir:
        mp3_path = os.path.join(tmp_dir, f"{test_clip['id']}_128k.mp3")
        # Run ffmpeg to re-encode
        cmd = ["ffmpeg", "-y", "-i", wav_path, "-b:a", "128k", mp3_path]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        with open(wav_path, "rb") as f_wav:
            wav_bytes = f_wav.read()
        with open(mp3_path, "rb") as f_mp3:
            mp3_bytes = f_mp3.read()

        # Upload WAV
        resp_wav = client.post(
            "/analyze/upload",
            files={"file": (f"{test_clip['id']}.wav", wav_bytes, "audio/wav")},
            data={"action_sensitivity": "balance_check", "mode": "stream", "phone_sim": "true"}
        )
        wav_data = resp_wav.json()
        wav_risk = wav_data.get("risk", 0.0)

        # Upload MP3
        resp_mp3 = client.post(
            "/analyze/upload",
            files={"file": (f"{test_clip['id']}.mp3", mp3_bytes, "audio/mpeg")},
            data={"action_sensitivity": "balance_check", "mode": "stream", "phone_sim": "true"}
        )
        mp3_data = resp_mp3.json()
        mp3_risk = mp3_data.get("risk", 0.0)

        risk_diff = mp3_risk - wav_risk
        print(f"WAV final risk: {wav_risk:.4f}")
        print(f"MP3 128k final risk: {mp3_risk:.4f}")
        print(f"Risk difference (MP3 - WAV): {risk_diff:+.4f}")
        print("Note: Reported for demonstration of lossy codec quantization effect.")


if __name__ == "__main__":
    main()
