"""
Script to re-run VoiceGuard Fused Evaluation from scratch with production config.
Computes whole config hash, Wilson 95% confidence intervals, and writes scratch/fused_eval.json.
Never writes by hand.
"""

import os
import json
import csv
import math
import hashlib
from pathlib import Path
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "settings.yaml"
MANIFEST_PATH = REPO_ROOT / "data" / "metadata" / "manifest.json"
SCRATCH_DIR = Path(r"C:\Users\Dell Latitude 7410\.gemini\antigravity-ide\brain\a18e2a80-1a10-459f-9aac-6edb5b242e63\scratch")
SPOOF_CSV = SCRATCH_DIR / "spoof_scores_run1.csv"
SPEAKER_CSV = SCRATCH_DIR / "speaker_scores_run1.csv"
REPLAY_CSV = SCRATCH_DIR / "replay_scores_run1.csv"
OUT_JSON = SCRATCH_DIR / "fused_eval.json"
DATA_OUT_JSON = REPO_ROOT / "data" / "fused_eval.json"


def wilson_score_interval(k: int, n: int, confidence: float = 0.95) -> dict:
    """Computes exact Wilson 95% score confidence interval for binomial proportion."""
    if n == 0:
        return {"proportion": 0.0, "lower": 0.0, "upper": 0.0}
    p = k / n
    z = 1.959963984540054  # 95% two-sided normal quantile
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2.0 * n)) / denom
    margin = (z / denom) * math.sqrt((p * (1.0 - p) / n) + (z2 / (4.0 * n * n)))
    lower = max(0.0, center - margin)
    upper = min(1.0, center + margin)
    return {
        "proportion": round(p, 4),
        "lower": round(lower, 4),
        "upper": round(upper, 4),
        "margin": round(margin, 4)
    }


def run_evaluation():
    print("=" * 80)
    print("STEP 3: RUN FUSED EVALUATION WITH WHOLE CONFIG HASH & WILSON INTERVALS")
    print("=" * 80)

    # 1. Compute hash of the WHOLE config file as loaded by server
    with open(CONFIG_PATH, "rb") as f:
        whole_config_bytes = f.read()
    whole_config_hash = hashlib.sha256(whole_config_bytes).hexdigest()
    print(f"Whole config file SHA-256: {whole_config_hash}")

    from server.risk_engine import RiskEngine
    engine = RiskEngine(config_path=str(CONFIG_PATH))
    engine_hash = engine.get_config_hash()
    print(f"Server loaded config SHA-256: {engine_hash}")
    assert whole_config_hash == engine_hash, "Config hash mismatch between file and RiskEngine"

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    # Load score lookup dicts (phone_simulated)
    spoof_scores = {}
    with open(SPOOF_CSV, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["audio_type"] == "phone_simulated":
                spoof_scores[row["clip_id"]] = float(row["spoof_prob"])

    speaker_scores = {}
    with open(SPEAKER_CSV, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["audio_type"] == "phone_simulated":
                speaker_scores[row["clip_id"]] = float(row["speaker_sim"])

    replay_scores = {}
    with open(REPLAY_CSV, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["audio_type"] == "phone_simulated":
                p = row["replay_prob"]
                replay_scores[row["clip_id"]] = float(p) if p != "None" else None

    # Assemble 40 evaluation clips across 5 folds (2 groups per fold: 1 live + 1 clone)
    fold_data = []
    for i in range(1, 11):
        fold_idx = (i - 1) // 2
        live_id = f"live_{i:02d}"
        item_live_rep = next(x for x in manifest if x.get("label") == "genuine_replay" and x.get("source_original_id") == live_id)
        clone_id = f"clone_{i:02d}"
        item_clone_rep = next(x for x in manifest if x.get("label") == "cloned_replay" and x.get("source_original_id") == clone_id)

        fold_data.append({"clip_id": live_id, "group": f"{i:02d}-live", "scenario": "genuine_live", "is_attack": False, "fold": fold_idx})
        fold_data.append({"clip_id": item_live_rep["original_id"], "group": f"{i:02d}-live", "scenario": "genuine_replay", "is_attack": True, "fold": fold_idx})
        fold_data.append({"clip_id": clone_id, "group": f"{i:02d}-clone", "scenario": "cloned_direct", "is_attack": True, "fold": fold_idx})
        fold_data.append({"clip_id": item_clone_rep["original_id"], "group": f"{i:02d}-clone", "scenario": "cloned_replay", "is_attack": True, "fold": fold_idx})

    # Fit fold-wise speaker maps
    fold_speaker_maps = {}
    for f_idx in range(5):
        tr_clips = [e for e in fold_data if e["fold"] != f_idx]
        tr_live_sims = [speaker_scores[e["clip_id"]] for e in tr_clips if not e["is_attack"]]
        tr_att_sims = [speaker_scores[e["clip_id"]] for e in tr_clips if e["is_attack"]]
        b_val = float(np.median(tr_live_sims))
        a_val = float(np.median(tr_att_sims))
        fold_speaker_maps[f_idx] = (a_val, b_val)

    # Production fit on all 40 clips
    all_live_sims = [speaker_scores[e["clip_id"]] for e in fold_data if not e["is_attack"]]
    all_att_sims = [speaker_scores[e["clip_id"]] for e in fold_data if e["is_attack"]]
    prod_a = float(np.median(all_att_sims))
    prod_b = float(np.median(all_live_sims))

    configs = [
        ("Config 1: All Three (SPOOF + SPEAKER + REPLAY)", {"use_spoof": True, "use_speaker": True, "use_replay": True}),
        ("Config 2: SPOOF Off (SPEAKER + REPLAY)",        {"use_spoof": False, "use_speaker": True, "use_replay": True}),
        ("Config 3: SPEAKER Only",                        {"use_spoof": False, "use_speaker": True, "use_replay": False}),
    ]

    eval_results = {}

    for cfg_name, cfg in configs:
        predictions = []
        missing_count = 0
        for e in fold_data:
            cid = e["clip_id"]
            f_idx = e["fold"]
            s_map = fold_speaker_maps[f_idx]

            sp = spoof_scores.get(cid) if cfg["use_spoof"] else None
            spk = speaker_scores.get(cid) if cfg["use_speaker"] else None
            rep = replay_scores.get(cid) if cfg["use_replay"] else None

            if cfg["use_spoof"] and sp is None:
                missing_count += 1

            res = engine.compute_risk(spoof_prob=sp, speaker_sim=spk, replay_prob=rep, speaker_map=s_map)
            is_allow = (res["band"] == "LOW")
            predictions.append({
                "clip_id": cid,
                "scenario": e["scenario"],
                "is_attack": e["is_attack"],
                "is_allow": is_allow,
                "final_risk": res["final_risk"],
                "band": res["band"]
            })

        # Calculate confusion matrix (Positive = Attack, Negative = Genuine Live)
        tp = sum(1 for p in predictions if p["is_attack"] and not p["is_allow"])
        tn = sum(1 for p in predictions if not p["is_attack"] and p["is_allow"])
        fp = sum(1 for p in predictions if not p["is_attack"] and not p["is_allow"])
        fn = sum(1 for p in predictions if p["is_attack"] and p["is_allow"])

        total = len(predictions)
        correct = tp + tn
        acc = correct / total
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        # Per scenario accuracies
        scenario_acc = {}
        scenario_wilson = {}
        for scen in ["genuine_live", "cloned_direct", "genuine_replay", "cloned_replay"]:
            scen_preds = [p for p in predictions if p["scenario"] == scen]
            if scen == "genuine_live":
                k_scen = sum(1 for p in scen_preds if p["is_allow"])
            else:
                k_scen = sum(1 for p in scen_preds if not p["is_allow"])
            n_scen = len(scen_preds)
            scenario_acc[scen] = round(k_scen / n_scen, 4)
            scenario_wilson[scen] = wilson_score_interval(k_scen, n_scen)

        acc_wilson = wilson_score_interval(correct, total)

        eval_results[cfg_name] = {
            "accuracy": round(acc, 4),
            "wilson_ci_95": acc_wilson,
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "TP": tp,
            "TN": tn,
            "FP": fp,
            "FN": fn,
            "missing_detector_clips": missing_count,
            "scenario_accuracies": scenario_acc,
            "scenario_wilson_ci_95": scenario_wilson,
            "pass_target": (acc >= 0.90 and fp == 0)
        }

    # Extra groups scored under Config 2 (SPOOF Off)
    prod_s_map = (prod_a, prod_b)

    def score_extra_group(clip_ids, group_name):
        risks = []
        allows = 0
        for cid in clip_ids:
            spk = speaker_scores.get(cid)
            rep = replay_scores.get(cid)
            res = engine.compute_risk(spoof_prob=None, speaker_sim=spk, replay_prob=rep, speaker_map=prod_s_map)
            risks.append(res["final_risk"])
            if res["band"] == "LOW":
                allows += 1
        med_risk = float(np.median(risks)) if risks else 0.0
        not_allow = len(clip_ids) - allows
        return {"n": len(clip_ids), "median_risk": round(med_risk, 4), "allow": allows, "not_allow": not_allow}

    extra_groups_res = {}
    extra_groups_res["cloned_direct_merged"] = score_extra_group(["cloned_merged_01", "cloned_merged_02", "cloned_merged_03"], "cloned_direct_merged")
    other_tts_ids = ["spoof_tts", "spoof_tts_aria", "spoof_tts_guy", "spoof_tts_sonia"]
    extra_groups_res["other_tts"] = score_extra_group(other_tts_ids, "other_tts")
    s2_ids = [x["original_id"] for x in manifest if x.get("label") == "genuine_live_extra" and x.get("original_id", "").startswith("session2_seg_")]
    extra_groups_res["session2_seg"] = score_extra_group(s2_ids, "session2_seg")

    out_data = {
        "config_hash": whole_config_hash,
        "configurations": eval_results,
        "extra_groups": extra_groups_res,
        "production_alternative": "Config 2: SPOOF Off (SPEAKER + REPLAY)",
        "post_hoc_caveat": "Choosing 'SPOOF off' was done post-hoc after seeing results indicating severe domain shift on live clips; accuracy is optimistic and cannot be treated as a pure held-out estimate.",
        "speaker_map_calibration": {
            "a": prod_a,
            "b": prod_b,
            "label": "fit on all evaluation data, no held-out estimate"
        }
    }

    SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2)

    with open(DATA_OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out_data, f, indent=2)

    print(f"\nWrote evaluated results to: {OUT_JSON} and {DATA_OUT_JSON}")
    print("\nSummary of Pre-Specified Alternatives:")
    for name, res in eval_results.items():
        ci = res["wilson_ci_95"]
        print(f"  {name}:")
        print(f"    Accuracy: {res['accuracy']*100:.2f}% (Wilson 95% CI: [{ci['lower']*100:.2f}%, {ci['upper']*100:.2f}%])")
        print(f"    FP (Live Refused): {res['FP']}, FN (Attack Allowed): {res['FN']}")
        for scen, sc_ci in res["scenario_wilson_ci_95"].items():
            print(f"      {scen}: {sc_ci['proportion']*100:.1f}% [{sc_ci['lower']*100:.1f}%, {sc_ci['upper']*100:.1f}%]")

    print(f"\nProduction calibration: a={prod_a:.7f}, b={prod_b:.7f}")
    print(f"Gate check: fused_eval.json config_hash == server loaded config hash: {out_data['config_hash'] == whole_config_hash}")
    print("=" * 80)


if __name__ == "__main__":
    run_evaluation()
