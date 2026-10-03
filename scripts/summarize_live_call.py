"""
VoiceGuard Live Call Summary Script (Phase 4 / Step 5).
Summarizes per-window metrics and band counts for a given Call SID from data/audit/live_windows.jsonl.
Identifies whether replay_prob or speaker_sim drove the fused risk score.
Never prints or logs phone numbers, secrets, or raw audio.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np

DIAGNOSTICS_PATH = Path("data/audit/live_windows.jsonl")


def summarize_call(call_sid: str, log_path: Path = DIAGNOSTICS_PATH) -> Optional[Dict[str, Any]]:
    if not log_path.exists():
        print(f"Error: Diagnostics log file not found at {log_path}")
        return None

    windows: List[Dict[str, Any]] = []
    lifecycles: List[Dict[str, Any]] = []
    all_sids = set()

    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue

            sid = rec.get("call_sid")
            if sid:
                all_sids.add(sid)

            if sid == call_sid:
                if rec.get("event") == "window_score":
                    windows.append(rec)
                elif rec.get("event") in ("stream_started", "stream_stopped", "disconnect"):
                    lifecycles.append(rec)

    if not windows and not lifecycles:
        print(f"No records found for Call SID: {call_sid}")
        if all_sids:
            print(f"Available Call SIDs in {log_path}:")
            for s in sorted(all_sids):
                print(f"  - {s}")
        return None

    # Band counts
    band_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    speaker_sims = []
    replay_probs = []
    risks = []
    speech_fractions = []
    rms_values = []
    actions = []

    for w in windows:
        band = w.get("band", "UNKNOWN")
        band_counts[band] = band_counts.get(band, 0) + 1
        if w.get("speaker_sim") is not None:
            speaker_sims.append(float(w["speaker_sim"]))
        if w.get("replay_prob") is not None:
            replay_probs.append(float(w["replay_prob"]))
        if w.get("risk") is not None:
            risks.append(float(w["risk"]))
        if w.get("speech_fraction") is not None:
            speech_fractions.append(float(w["speech_fraction"]))
        if w.get("buffer_rms_dbfs") is not None:
            rms_values.append(float(w["buffer_rms_dbfs"]))
        if w.get("action_trigger"):
            actions.append(w["action_trigger"])

    med_speaker = float(np.median(speaker_sims)) if speaker_sims else None
    med_replay = float(np.median(replay_probs)) if replay_probs else None
    med_risk = float(np.median(risks)) if risks else 0.0
    med_speech = float(np.median(speech_fractions)) if speech_fractions else 0.0
    med_rms = float(np.median(rms_values)) if rms_values else -100.0

    # Risk driver determination
    # Production linear speaker calibration mapping (a=0.3364065, b=0.4169240)
    # Speaker risk input = 1 - clip((sim - a)/(b - a), 0, 1)
    a, b = 0.3364065, 0.4169240
    if med_speaker is not None:
        norm_speaker = max(0.0, min(1.0, (med_speaker - a) / (b - a)))
        speaker_risk_input = 1.0 - norm_speaker
    else:
        speaker_risk_input = 0.50

    replay_risk_input = med_replay if med_replay is not None else 0.50

    if replay_risk_input > speaker_risk_input + 0.05:
        driver = "replay_prob (replay acoustic artifacts drove the risk)"
    elif speaker_risk_input > replay_risk_input + 0.05:
        driver = "speaker_sim (voiceprint mismatch / unfamiliar voice drove the risk)"
    else:
        driver = "balanced (both speaker similarity and replay probability contributed equally)"

    # Lifecycle duration
    call_duration = None
    for lc in lifecycles:
        if lc.get("duration_seconds") is not None:
            call_duration = lc["duration_seconds"]

    print("=" * 80)
    print(f"LIVE CALL DIAGNOSTICS SUMMARY: {call_sid}")
    print("=" * 80)
    print(f"Total Windows Scored:     {len(windows)}")
    if call_duration is not None:
        print(f"Call Duration:            {call_duration:.2f} seconds")
    print(f"Band Distribution:")
    print(f"  LOW (Allow):            {band_counts.get('LOW', 0)}")
    print(f"  MEDIUM (Step-Up):       {band_counts.get('MEDIUM', 0)}")
    print(f"  HIGH (Block):           {band_counts.get('HIGH', 0)}")
    print(f"Per-Window Medians:")
    print(f"  Speaker Similarity:     {med_speaker:.4f}" if med_speaker is not None else "  Speaker Similarity:     N/A")
    print(f"  Replay Probability:     {med_replay:.4f}" if med_replay is not None else "  Replay Probability:     N/A")
    print(f"  Fused Risk:             {med_risk:.4f}")
    print(f"  Speech Fraction:        {med_speech:.4f}")
    print(f"  Buffer RMS dBFS:        {med_rms:.2f} dBFS")
    print(f"Risk Driver:              {driver}")
    print(f"Actions Fired:            {actions if actions else 'None (Clean Allow)'}")
    print("=" * 80)

    return {
        "call_sid": call_sid,
        "windows_count": len(windows),
        "band_counts": band_counts,
        "median_speaker_sim": med_speaker,
        "median_replay_prob": med_replay,
        "median_risk": med_risk,
        "median_speech_fraction": med_speech,
        "median_buffer_rms_dbfs": med_rms,
        "driver": driver,
        "actions": actions,
        "call_duration": call_duration
    }


def main():
    parser = argparse.ArgumentParser(description="Summarize live call telemetry from live_windows.jsonl")
    parser.add_argument("call_sid", nargs="?", help="Call SID to summarize")
    parser.add_argument("--log-path", default=str(DIAGNOSTICS_PATH), help="Path to live_windows.jsonl")
    args = parser.parse_args()

    if not args.call_sid:
        # If no SID provided, list available
        path = Path(args.log_path)
        if not path.exists():
            print(f"No diagnostics log file found at {path}")
            sys.exit(1)
        sids = set()
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        sids.add(json.loads(line).get("call_sid"))
                    except Exception:
                        pass
        sids.discard(None)
        if not sids:
            print(f"No calls found in {path}")
        else:
            print("Usage: python scripts/summarize_live_call.py <CALL_SID>")
            print(f"Available Call SIDs in {path}:")
            for s in sorted(sids):
                print(f"  - {s}")
        sys.exit(0)

    summary = summarize_call(args.call_sid, Path(args.log_path))
    if summary is None:
        sys.exit(1)


if __name__ == "__main__":
    main()
