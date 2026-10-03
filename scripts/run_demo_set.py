"""
VoiceGuard Demo Evaluation Harness (scripts/run_demo_set.py).
Label: "SIMULATION, not a live call"

Runs the full set of 9 allowlisted demo scenarios at 2x speed through the real StreamingSession pipeline.
- Warms up the model pipeline before timed execution.
- Evaluates whole-stream any-action outcome: Allow / Step-up only / Block.
- Reports audio seconds from stream start to first fired action (None if no action).
- Evaluates Match using Step 1 unified rules:
    genuine_live: expected = Allow
    attacks: expected = Not Allow (Step-up or Block)
    Match = (genuine and outcome is Allow) or (attack and outcome is Step-up only or Block)
- Evaluates rehearsal stability across 3 runs.
- Prints plain mismatch list with per-window risk and band sequence. No speculation of causes.
"""

import sys
import time
import asyncio
from typing import Dict, Any, List, Optional

from server.demo import DemoRunner, DEMO_SCENARIOS, SIMULATION_LABEL


async def run_single_scenario(runner: DemoRunner, scenario_id: str, speed: float = 2.0) -> Dict[str, Any]:
    sc = DEMO_SCENARIOS[scenario_id]

    res = await runner.run_scenario_stream(
        scenario_id=scenario_id,
        action_sensitivity="balance_check",
        speed=speed
    )

    window_sequence = [
        {"win": w["window"], "risk": round(w["risk"], 4), "band": w["band"], "action": w.get("action_taken")}
        for w in res.get("windows", [])
    ]

    return {
        "scenario_id": scenario_id,
        "title": sc["title"],
        "group": sc["group"],
        "expected": res["expected_outcome"],
        "windows_scored": res["total_windows"],
        "final_band": res["final_band"],
        "outcome": res["outcome"],
        "actions_fired": res["actions_fired"],
        "time_to_first_action": res["time_to_first_action"],
        "match": res["match"],
        "discrepancy": res["discrepancy"],
        "window_sequence": window_sequence
    }


async def main():
    print("=" * 95)
    print(f"VOICEGUARD DEMO SET EXECUTION [{SIMULATION_LABEL}]")
    print("Unified Expectation Rules: Genuine -> Allow | Attacks -> Not Allow (Step-up or Block)")
    print("=" * 95)

    runner = DemoRunner()
    scenario_ids = list(DEMO_SCENARIOS.keys())

    # 1. Warm-up run (ensures cold-start torch/model weights are paged in before timed passes)
    print("\n[Warmup] Warming up model pipeline with live_01 at 50x speed...")
    await runner.run_scenario_stream("live_01", speed=50.0)
    print("[Warmup] Complete.\n")

    all_runs_results: List[List[Dict[str, Any]]] = []

    for run_idx in range(1, 4):
        print(f"--- EXECUTION RUN {run_idx} / 3 (2x Speed) ---")
        run_results = []
        for sc_id in scenario_ids:
            res = await run_single_scenario(runner, sc_id, speed=2.0)
            run_results.append(res)
            time_act_str = f"{res['time_to_first_action']}s" if res['time_to_first_action'] is not None else "None"
            print(f"  [{sc_id}] windows={res['windows_scored']}, final_band={res['final_band']}, outcome={res['outcome']}, first_action_time={time_act_str}, match={'YES' if res['match'] else 'NO'}")
        all_runs_results.append(run_results)

    # 1. Print detailed summary table for Run 1
    print("\n" + "=" * 115)
    print(f"DETAILED RESULTS (RUN 1) [{SIMULATION_LABEL}]:")
    print(f"{'Scenario':<16} | {'Expected':<30} | {'Windows':<7} | {'Final Band':<10} | {'Outcome':<14} | {'Time 1st Act':<12} | {'Match?':<6}")
    print("-" * 115)
    for r in all_runs_results[0]:
        time_act_str = f"{r['time_to_first_action']:.2f}s" if r['time_to_first_action'] is not None else "None"
        match_str = "YES" if r["match"] else "NO"
        print(f"{r['scenario_id']:<16} | {r['expected']:<30} | {r['windows_scored']:<7} | {r['final_band']:<10} | {r['outcome']:<14} | {time_act_str:<12} | {match_str:<6}")
    print("=" * 115)

    # 2. Rehearsal Stability Comparison across all 3 runs
    print("\nREHEARSAL STABILITY COMPARISON (RUNS 1, 2, 3):")
    print(f"{'Scenario':<16} | {'Run 1 (Band / Outcome)':<26} | {'Run 2 (Band / Outcome)':<26} | {'Run 3 (Band / Outcome)':<26} | {'Stable?'}")
    print("-" * 115)
    all_stable = True
    for i, sc_id in enumerate(scenario_ids):
        r1 = all_runs_results[0][i]
        r2 = all_runs_results[1][i]
        r3 = all_runs_results[2][i]

        s1 = f"{r1['final_band']} / {r1['outcome']}"
        s2 = f"{r2['final_band']} / {r2['outcome']}"
        s3 = f"{r3['final_band']} / {r3['outcome']}"

        is_stable = (s1 == s2 == s3) and (r1["windows_scored"] == r2["windows_scored"] == r3["windows_scored"])
        if not is_stable:
            all_stable = False
        print(f"{sc_id:<16} | {s1:<26} | {s2:<26} | {s3:<26} | {'YES' if is_stable else 'NO'}")

    print("-" * 115)
    if all_stable:
        print("STABILITY VERDICT: ALL 3 RUNS GAVE IDENTICAL OUTCOMES AND BAND PROGRESSIONS (100% REHEARSAL STABILITY).")
    else:
        print("STABILITY VERDICT: DISCREPANCIES DETECTED ACROSS RUNS.")

    # 3. Honest Mismatch List (No speculation of causes)
    print("\n" + "=" * 95)
    print("PLAIN MISMATCH LIST (SCENARIOS WHERE MATCH IS NO):")
    print("=" * 95)
    mismatches = [r for r in all_runs_results[0] if not r["match"]]
    if not mismatches:
        print("No mismatches found across the demo set.")
    else:
        for m in mismatches:
            print(f"- Scenario : {m['scenario_id']} ({m['title']})")
            print(f"  Expected : {m['expected']}")
            print(f"  Outcome  : {m['outcome']} ({m['discrepancy']})")
            print(f"  Final Band: {m['final_band']}")
            time_act_str = f"{m['time_to_first_action']:.2f}s" if m['time_to_first_action'] is not None else "None"
            print(f"  Time to First Action: {time_act_str}")
            print(f"  Per-Window Risk and Band Sequence:")
            for w in m["window_sequence"]:
                act_str = f" [Action: {w['action']}]" if w["action"] else ""
                print(f"    * Window {w['win']}: Risk={w['risk']:.4f}, Band={w['band']}{act_str}")
            print(f"  Cause: cause not measured")
            print()


if __name__ == "__main__":
    asyncio.run(main())
