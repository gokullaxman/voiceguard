"""
Streaming-Level Evaluation Harness (scripts/eval_streaming.py).
Label: "SIMULATION, not a live call"

Streams all 40 phone_simulated evaluation clips through the real StreamingSession pipeline
under production configuration (Config 2: SPEAKER + REPLAY, SPOOF off).
- Evaluates per-clip streaming outcomes: Allow / Step-up only / Block.
- Uses Step 1 unified match rules:
    genuine_live: expected = Allow
    attacks (cloned_direct, genuine_replay, cloned_replay): expected = Not Allow (Step-up or Block)
- Computes Wilson 95% confidence intervals for match rates.
- Reports false step-up rate on genuine_live and miss rate on attack groups.
- Compares streaming evaluation with whole-clip fused evaluation (scratch/fused_eval.json).
- Generates scratch/streaming_eval.json.
NOTE: The production speaker map was fit on these same 40 clips, so results are optimistic.
"""

import os
import json
import base64
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from pathlib import Path
from typing import Dict, Any, List, Optional

from server.telephony import encode_pcm_to_ulaw
from server.streaming import StreamingSession
from server.demo import compute_stream_outcome, evaluate_scenario_match, SIMULATION_LABEL


REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "data" / "metadata" / "manifest.json"
FUSED_EVAL_PATH = REPO_ROOT / "scratch" / "fused_eval.json"
STREAMING_EVAL_PATH = REPO_ROOT / "scratch" / "streaming_eval.json"


def wilson_ci_95(k: int, n: int) -> Dict[str, float]:
    if n == 0:
        return {"proportion": 0.0, "lower": 0.0, "upper": 0.0, "margin": 0.0}
    p = k / n
    z = 1.959963984540054  # 95%
    denom = 1.0 + (z**2) / n
    center = (p + (z**2) / (2.0 * n)) / denom
    margin = (z * np.sqrt((p * (1.0 - p) + (z**2) / (4.0 * n)) / n)) / denom
    lower = max(0.0, center - margin)
    upper = min(1.0, center + margin)
    return {
        "proportion": round(p, 4),
        "lower": round(lower, 4),
        "upper": round(upper, 4),
        "margin": round(margin, 4)
    }


def load_audio_frames(audio_path: str) -> List[str]:
    """Loads audio, resamples to 8kHz, converts to 20ms G.711 mu-law base64 frames."""
    audio, sr = sf.read(audio_path, dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    if sr != 8000:
        audio_8k = resample_poly(audio, up=1, down=sr // 8000)
    else:
        audio_8k = audio

    pcm_8k = np.clip(audio_8k * 32767.0, -32768, 32767).astype(np.int16)
    frame_samples = 160  # 20ms at 8kHz

    frames = []
    for i in range(0, len(pcm_8k) - frame_samples + 1, frame_samples):
        chunk = pcm_8k[i:i + frame_samples]
        ulaw_bytes = encode_pcm_to_ulaw(chunk)
        frames.append(base64.b64encode(ulaw_bytes).decode("ascii"))
    return frames


def stream_clip(clip_meta: Dict[str, Any]) -> Dict[str, Any]:
    clip_id = clip_meta["clip_id"]
    group = clip_meta["label"]
    audio_path = REPO_ROOT / clip_meta["simulated_path"]

    frames = load_audio_frames(str(audio_path))
    session = StreamingSession(
        call_sid=f"CA_eval_{clip_id}",
        stream_sid=f"MZ_eval_{clip_id}",
        use_spoof=False,
        audit_logger=None
    )

    context = {
        "action": "balance_check",
        "action_sensitivity": "balance_check",
        "caller_not_allowlisted": False,
        "simulation": True,
        "simulation_label": SIMULATION_LABEL
    }

    windows_scored = []
    actions_fired = []
    first_action_sec: Optional[float] = None

    for payload in frames:
        session.ingest_twilio_payload(payload)

        # Trigger window evaluation: 32000 samples initial (2.0s), then every 16000 samples (1.0s)
        if session.audio_buffer.total_samples_received >= 32000 and (session.audio_buffer.total_samples_received % 16000 < 320):
            ev = session.score_current_window(context)
            if ev:
                windows_scored.append(ev)
                act = ev.get("action_trigger")
                if act == "step_up":
                    actions_fired.append("MOCK OTP")
                    if first_action_sec is None:
                        first_action_sec = round(session.audio_buffer.total_samples_received / 8000.0, 2)
                elif act == "block":
                    actions_fired.append("Block")
                    if first_action_sec is None:
                        first_action_sec = round(session.audio_buffer.total_samples_received / 8000.0, 2)

    final_band = windows_scored[-1]["band"] if windows_scored else "LOW"
    max_risk = max([w["risk"] for w in windows_scored]) if windows_scored else 0.0
    outcome = compute_stream_outcome(actions_fired)
    eval_match = evaluate_scenario_match(group, outcome)

    return {
        "clip_id": clip_id,
        "group": group,
        "windows_scored": len(windows_scored),
        "max_risk": round(max_risk, 4),
        "final_band": final_band,
        "outcome": outcome,
        "time_to_first_action": first_action_sec,
        "expected": eval_match["expected"],
        "match": eval_match["match"],
        "discrepancy": eval_match["discrepancy"]
    }


def main():
    print("=" * 100)
    print(f"VOICEGUARD STREAMING-LEVEL EVALUATION [{SIMULATION_LABEL}]")
    print("Streaming 40 phone-simulated evaluation clips through real StreamingSession pipeline...")
    print("=" * 100)

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Filter the 40 primary evaluation clips
    eval_groups = ["genuine_live", "cloned_direct", "genuine_replay", "cloned_replay"]
    core_clips = [x for x in manifest if x.get("label") in eval_groups and x.get("clip_id", "").startswith(("live_", "clone_"))]
    # Filter to exact 40 primary scenario clips (10 per group)
    core_40 = []
    for grp in eval_groups:
        grp_clips = [c for c in core_clips if c.get("label") == grp]
        # Sort and take first 10
        grp_clips = sorted(grp_clips, key=lambda x: x["clip_id"])[:10]
        core_40.extend(grp_clips)

    assert len(core_40) == 40, f"Expected 40 evaluation clips, found {len(core_40)}"

    print(f"Loaded 40 evaluation clips across 4 scenario groups (10 per group).")

    results_by_clip = []
    for c in core_40:
        res = stream_clip(c)
        results_by_clip.append(res)
        time_str = f"{res['time_to_first_action']}s" if res['time_to_first_action'] is not None else "None"
        print(f"[{res['clip_id']:<16}] Group={res['group']:<15} Win={res['windows_scored']:<2} MaxRisk={res['max_risk']:<6} Band={res['final_band']:<6} Outcome={res['outcome']:<12} ActTime={time_str:<6} Match={'YES' if res['match'] else 'NO'}")

    # 1. Group summary table
    print("\n" + "=" * 115)
    print(f"STREAMING EVALUATION RESULTS PER SCENARIO GROUP (N=10 EACH) [{SIMULATION_LABEL}]:")
    print(f"{'Scenario Group':<16} | {'N':<3} | {'Allow':<6} | {'Step-Up':<8} | {'Block':<6} | {'Match Rate':<11} | {'Wilson 95% CI':<24} | {'Discrepancy':<14}")
    print("-" * 115)

    group_stats: Dict[str, Any] = {}
    total_matches = 0

    for grp in eval_groups:
        grp_res = [r for r in results_by_clip if r["group"] == grp]
        n = len(grp_res)
        allow_cnt = sum(1 for r in grp_res if r["outcome"] == "Allow")
        stepup_cnt = sum(1 for r in grp_res if r["outcome"] == "Step-up only")
        block_cnt = sum(1 for r in grp_res if r["outcome"] == "Block")
        match_cnt = sum(1 for r in grp_res if r["match"])
        total_matches += match_cnt

        ci = wilson_ci_95(match_cnt, n)

        if grp == "genuine_live":
            discrepancy_str = f"{n - match_cnt} false step-up"
        else:
            discrepancy_str = f"{n - match_cnt} missed"

        ci_str = f"[{ci['lower']*100:.2f}%, {ci['upper']*100:.2f}%]"
        match_pct_str = f"{ci['proportion']*100:.1f}% ({match_cnt}/{n})"

        print(f"{grp:<16} | {n:<3} | {allow_cnt:<6} | {stepup_cnt:<8} | {block_cnt:<6} | {match_pct_str:<11} | {ci_str:<24} | {discrepancy_str:<14}")

        group_stats[grp] = {
            "n": n,
            "allow_count": allow_cnt,
            "step_up_only_count": stepup_cnt,
            "block_count": block_cnt,
            "match_count": match_cnt,
            "match_rate": ci["proportion"],
            "wilson_ci_95": ci,
            "false_step_up_count": (n - match_cnt) if grp == "genuine_live" else 0,
            "miss_count": (n - match_cnt) if grp != "genuine_live" else 0
        }

    overall_ci = wilson_ci_95(total_matches, 40)
    print("-" * 115)
    print(f"{'OVERALL STREAMING':<16} | {'40':<3} | {'--':<6} | {'--':<8} | {'--':<6} | {overall_ci['proportion']*100:.1f}% ({total_matches}/40)| [{overall_ci['lower']*100:.2f}%, {overall_ci['upper']*100:.2f}%] | {(40 - total_matches)} discrepancies")
    print("=" * 115)

    # 2. Specific rates
    gen_stats = group_stats["genuine_live"]
    false_step_up_rate = gen_stats["false_step_up_count"] / gen_stats["n"]
    false_step_up_ci = wilson_ci_95(gen_stats["false_step_up_count"], gen_stats["n"])

    print("\nSPECIFIC ERROR RATES:")
    print(f"- False Step-Up Rate on Genuine Live (n=10): {false_step_up_rate*100:.1f}% ({gen_stats['false_step_up_count']}/10) | Wilson 95% CI: [{false_step_up_ci['lower']*100:.2f}%, {false_step_up_ci['upper']*100:.2f}%]")

    for grp in ["cloned_direct", "genuine_replay", "cloned_replay"]:
        st = group_stats[grp]
        miss_rate = st["miss_count"] / st["n"]
        miss_ci = wilson_ci_95(st["miss_count"], st["n"])
        print(f"- Miss Rate on {grp} (n=10): {miss_rate*100:.1f}% ({st['miss_count']}/10) | Wilson 95% CI: [{miss_ci['lower']*100:.2f}%, {miss_ci['upper']*100:.2f}%]")

    # 3. Comparison with Whole-Clip Evaluation (Config 2)
    with open(FUSED_EVAL_PATH, "r", encoding="utf-8") as f:
        fused_json = json.load(f)
    cfg2_fused = fused_json["configurations"]["Config 2: SPOOF Off (SPEAKER + REPLAY)"]

    print("\n" + "=" * 110)
    print("COMPARISON: WHOLE-CLIP SCORING VS. SUSTAINED-WINDOW STREAMING EVALUATION:")
    print("=" * 110)
    print(f"{'Metric / Scenario':<24} | {'Whole-Clip Scoring (fused_eval.json)':<38} | {'Sustained-Window Streaming':<30}")
    print("-" * 110)
    print(f"{'Overall Decision Rate':<24} | {cfg2_fused['accuracy']*100:.1f}% (39/40) [{cfg2_fused['wilson_ci_95']['lower']*100:.2f}%, {cfg2_fused['wilson_ci_95']['upper']*100:.2f}%] | {overall_ci['proportion']*100:.1f}% ({total_matches}/40) [{overall_ci['lower']*100:.2f}%, {overall_ci['upper']*100:.2f}%]")
    for grp in eval_groups:
        wh_acc = cfg2_fused['scenario_accuracies'][grp]
        wh_ci = cfg2_fused['scenario_wilson_ci_95'][grp]
        st_grp = group_stats[grp]
        print(f"{grp:<24} | {wh_acc*100:.1f}% [{wh_ci['lower']*100:.2f}%, {wh_ci['upper']*100:.2f}%]          | {st_grp['match_rate']*100:.1f}% [{st_grp['wilson_ci_95']['lower']*100:.2f}%, {st_grp['wilson_ci_95']['upper']*100:.2f}%]")
    print("-" * 110)
    print("IMPORTANT METHODOLOGICAL STATEMENT:")
    print("Whole-clip scoring and sustained-window streaming are DIFFERENT measurements:")
    print("  1. Whole-clip scoring evaluates a single risk score computed from the entire audio duration.")
    print("  2. Sustained-window streaming evaluates a rolling 2.0s buffer advanced every 1.0s, requiring")
    print("     consecutive window threshold exceedances (sustained evidence rule) to fire action triggers.")
    print("Neither measurement should be called 'the' accuracy of the system.")
    print("=" * 110)

    # 4. Save to scratch/streaming_eval.json
    output_data = {
        "simulation_label": SIMULATION_LABEL,
        "methodological_note": "The linear speaker calibration map (a, b) was fit on these same 40 clips; results are optimistic and lack a held-out speaker estimate.",
        "config_hash": fused_json.get("config_hash"),
        "total_clips": 40,
        "overall_match_count": total_matches,
        "overall_match_rate": overall_ci["proportion"],
        "overall_wilson_ci_95": overall_ci,
        "false_step_up_rate_genuine_live": false_step_up_rate,
        "false_step_up_ci_95": false_step_up_ci,
        "group_statistics": group_stats,
        "clips": results_by_clip
    }

    with open(STREAMING_EVAL_PATH, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)

    print(f"\nWrote streaming evaluation results to {STREAMING_EVAL_PATH}")


if __name__ == "__main__":
    main()
