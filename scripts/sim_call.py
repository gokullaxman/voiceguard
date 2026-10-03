"""
VoiceGuard Simulated Telephony Call Tool (Phase 4).
Streams audio files in Twilio-compliant base64 G.711 mu-law 8 kHz frames (20 ms chunks).
Scores rolling windows, logs to audit chain, and triggers step-up / termination.
NOTICE: SIMULATION, not a live Twilio call.
"""

import os
import sys
import time
import json
import base64
import argparse
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from server.telephony import encode_pcm_to_ulaw
from server.streaming import StreamingSession
from server.audit import AuditLogger
from server.responses import TwilioActionDispatcher


def run_simulation(
    audio_path: str,
    call_sid: str = "CA_sim_demo",
    context: dict = None,
    use_spoof: bool = False
) -> dict:
    print(f"\n{'=' * 85}")
    print(f"SIMULATION, not a live Twilio call | File: {audio_path}")
    print(f"Call SID: {call_sid} | Context: {context}")
    print(f"{'=' * 85}")

    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    audio, sr = sf.read(audio_path, dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    # Convert to 8 kHz for Twilio transmission
    if sr != 8000:
        audio_8k = resample_poly(audio, up=1, down=sr // 8000)
    else:
        audio_8k = audio

    # PCM int16
    pcm_8k = np.clip(audio_8k * 32767.0, -32768, 32767).astype(np.int16)

    # Frame chunking: 20 ms at 8 kHz = 160 samples per frame
    frame_samples = 160
    total_frames = len(pcm_8k) // frame_samples

    session = StreamingSession(
        call_sid=call_sid,
        use_spoof=use_spoof
    )
    dispatcher = TwilioActionDispatcher()

    window_results = []
    latencies = []
    actions_triggered = []

    print(f"Streaming {total_frames} frames ({len(audio)/sr:.2f}s total audio)...")

    # Ingest frames and evaluate on 1.0s hop (every 50 frames = 8000 samples = 0.5s audio)
    for f_idx in range(total_frames):
        chunk = pcm_8k[f_idx * frame_samples : (f_idx + 1) * frame_samples]
        ulaw_bytes = encode_pcm_to_ulaw(chunk)
        b64_payload = base64.b64encode(ulaw_bytes).decode("ascii")
        
        session.ingest_twilio_payload(b64_payload)

        # Hop trigger: every 0.5s (25 frames) after 2.0s (100 frames)
        if f_idx >= 100 and f_idx % 25 == 0:
            score_event = session.score_current_window(context=context)
            if score_event:
                window_results.append(score_event)
                latencies.append(score_event["latency_ms"])
                print(f"Window {score_event['window']:<2d} | Risk: {score_event['risk']:<6.4f} | Band: {score_event['band']:<8} | Decision: {score_event['decision']:<40} | Latency: {score_event['latency_ms']:.1f}ms")

                # Handle triggers
                if score_event["decision"].startswith("Block") and "block" not in actions_triggered:
                    act = dispatcher.terminate_call(call_sid)
                    actions_triggered.append("block")
                    print(f"  >>> ACTION TRIGGERED: {act['action']} ({act['reason']})")
                    break
                elif score_event["decision"].startswith("Step-Up") and "step_up" not in actions_triggered:
                    act = dispatcher.trigger_step_up(call_sid)
                    actions_triggered.append("step_up")
                    print(f"  >>> ACTION TRIGGERED: {act['action']}")

    # Summary
    p50_lat = float(np.percentile(latencies, 50)) if latencies else 0.0
    p95_lat = float(np.percentile(latencies, 95)) if latencies else 0.0

    print("-" * 85)
    print(f"Simulation completed for {call_sid}:")
    print(f"  Windows scored:       {len(window_results)}")
    print(f"  Actions triggered:    {actions_triggered if actions_triggered else 'None (Allowed)'}")
    print(f"  Latency p50:          {p50_lat:.1f} ms")
    print(f"  Latency p95:          {p95_lat:.1f} ms")

    # Verify audit chain
    is_valid, err, count = AuditLogger.verify_chain()
    print(f"  Audit chain verified: {'PASS' if is_valid else 'FAIL'} ({count} records in chain)")

    return {
        "call_sid": call_sid,
        "windows": len(window_results),
        "actions": actions_triggered,
        "p50_latency_ms": p50_lat,
        "p95_latency_ms": p95_lat,
        "audit_verified": is_valid
    }


def main():
    parser = argparse.ArgumentParser(description="VoiceGuard Telephony Stream Simulator")
    parser.add_argument("--file", type=str, help="Path to audio file")
    parser.add_argument("--call-sid", type=str, default="CA_sim_demo", help="Call SID")
    parser.add_argument("--run-3-demos", action="store_true", help="Run the 3 standardized demo scenarios")
    args = parser.parse_args()

    if args.run_3_demos or not args.file:
        print("\n" + "=" * 85)
        print("RUNNING 3 STANDARDIZED DEMO SCENARIOS")
        print("NOTICE: SIMULATION, not a live Twilio call")
        print("=" * 85)

        # Demo 1: Genuine Live
        res1 = run_simulation(
            audio_path="data/genuine/live_01.wav",
            call_sid="CA_demo1_genuine_live",
            context={"action": "balance_check", "caller_not_allowlisted": False}
        )

        # Demo 2: Borderline (cloned_merged_01_sim: direct clone near medium band)
        res2 = run_simulation(
            audio_path="data/phone_simulated/cloned_merged_01_sim.wav",
            call_sid="CA_demo2_borderline",
            context={"action": "wire_transfer", "caller_not_allowlisted": True}
        )

        # Demo 3: Cloned Replay
        res3 = run_simulation(
            audio_path="data/phone_simulated/clone_replay_01_sim.wav",
            call_sid="CA_demo3_cloned_replay",
            context={"action": "wire_transfer", "caller_not_allowlisted": True}
        )

        print("\n" + "=" * 85)
        print("DEMO SUITE EXECUTION SUMMARY")
        print("=" * 85)
        print(f"Scenario 1 (Genuine Live):  Windows={res1['windows']}, Actions={res1['actions']}, p50={res1['p50_latency_ms']}ms, p95={res1['p95_latency_ms']}ms, Audit={res1['audit_verified']}")
        print(f"Scenario 2 (Borderline):    Windows={res2['windows']}, Actions={res2['actions']}, p50={res2['p50_latency_ms']}ms, p95={res2['p95_latency_ms']}ms, Audit={res2['audit_verified']}")
        print(f"Scenario 3 (Cloned Replay): Windows={res3['windows']}, Actions={res3['actions']}, p50={res3['p50_latency_ms']}ms, p95={res3['p95_latency_ms']}ms, Audit={res3['audit_verified']}")
        print("=" * 85)
    else:
        run_simulation(args.file, call_sid=args.call_sid)


if __name__ == "__main__":
    main()
