"""
VoiceGuard Demo Mode Runner (server/demo.py).
Label: "SIMULATION, not a live call"

Provides interactive and headless demo streaming over the real StreamingSession pipeline
without requiring Twilio telephony credentials or public tunnels.
"""

import os
import time
import json
import base64
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from server.telephony import encode_pcm_to_ulaw
from server.streaming import StreamingSession
from server.audit import AuditLogger
from server.diagnostics import LiveDiagnosticsLogger

SIMULATION_LABEL = "SIMULATION, not a live call"

# Allowlisted demo scenarios sourced from manifest.json
DEMO_SCENARIOS: Dict[str, Dict[str, Any]] = {
    "live_01": {
        "id": "live_01",
        "title": "Genuine Live Call 1",
        "group": "genuine_live",
        "expected_outcome": "Allow",
        "source": "from the evaluation set",
        "file_path": "data/phone_simulated/live_01_sim.wav",
        "description": "Natural voice of enrolled speaker (gokul) under standard phone simulation."
    },
    "live_02": {
        "id": "live_02",
        "title": "Genuine Live Call 2",
        "group": "genuine_live",
        "expected_outcome": "Allow",
        "source": "from the evaluation set",
        "file_path": "data/phone_simulated/live_02_sim.wav",
        "description": "Natural voice of enrolled speaker (gokul) with varied speech cadence."
    },
    "live_03": {
        "id": "live_03",
        "title": "Genuine Live Call 3",
        "group": "genuine_live",
        "expected_outcome": "Allow",
        "source": "from the evaluation set",
        "file_path": "data/phone_simulated/live_03_sim.wav",
        "description": "Natural conversational voice of enrolled speaker."
    },
    "clone_01": {
        "id": "clone_01",
        "title": "Direct Voice Clone 1",
        "group": "cloned_direct",
        "expected_outcome": "Not Allow (Step-up or Block)",
        "source": "from the evaluation set",
        "file_path": "data/phone_simulated/clone_01_sim.wav",
        "description": "Direct neural TTS clone targeting enrolled voiceprint."
    },
    "clone_02": {
        "id": "clone_02",
        "title": "Direct Voice Clone 2",
        "group": "cloned_direct",
        "expected_outcome": "Not Allow (Step-up or Block)",
        "source": "from the evaluation set",
        "file_path": "data/phone_simulated/clone_02_sim.wav",
        "description": "Synthesized neural clone speech segment."
    },
    "live_replay_01": {
        "id": "live_replay_01",
        "title": "Genuine Replay Attack 1",
        "group": "genuine_replay",
        "expected_outcome": "Not Allow (Step-up or Block)",
        "source": "from the evaluation set",
        "file_path": "data/phone_simulated/live_replay_01_sim.wav",
        "description": "Legitimate speaker recording replayed through a loudspeaker."
    },
    "live_replay_02": {
        "id": "live_replay_02",
        "title": "Genuine Replay Attack 2",
        "group": "genuine_replay",
        "expected_outcome": "Not Allow (Step-up or Block)",
        "source": "from the evaluation set",
        "file_path": "data/phone_simulated/live_replay_02_sim.wav",
        "description": "Acoustic loudspeaker replay of genuine speech."
    },
    "clone_replay_01": {
        "id": "clone_replay_01",
        "title": "Cloned Replay Attack 1",
        "group": "cloned_replay",
        "expected_outcome": "Not Allow (Step-up or Block)",
        "source": "from the evaluation set",
        "file_path": "data/phone_simulated/clone_replay_01_sim.wav",
        "description": "Synthesized clone voice replayed through an acoustic loudspeaker channel."
    },
    "clone_replay_02": {
        "id": "clone_replay_02",
        "title": "Cloned Replay Attack 2",
        "group": "cloned_replay",
        "expected_outcome": "Not Allow (Step-up or Block)",
        "source": "from the evaluation set",
        "file_path": "data/phone_simulated/clone_replay_02_sim.wav",
        "description": "Replayed neural clone voice attack."
    },
}


def compute_stream_outcome(actions_fired: List[str]) -> str:
    """
    Computes stream outcome from all actions fired during the whole stream:
    - Allow: no action fired
    - Step-up only: step_up fired, no block
    - Block: block fired
    """
    has_block = any("block" in a.lower() for a in actions_fired)
    if has_block:
        return "Block"
    has_step_up = any("otp" in a.lower() or "step_up" in a.lower() or "step-up" in a.lower() for a in actions_fired)
    if has_step_up:
        return "Step-up only"
    return "Allow"


def evaluate_scenario_match(group: str, outcome: str) -> Dict[str, Any]:
    """
    Unified expectation matching rule:
    - genuine_live: expected = Allow
    - cloned_direct, genuine_replay, cloned_replay: expected = Not Allow (Step-up or Block)

    Match = (genuine and outcome is Allow) or (attack and outcome is Step-up only or Block).

    Discrepancy flags:
    - genuine + Step-up only -> "false step-up"
    - genuine + Block -> "false block"
    - attack + Allow -> "missed"
    """
    is_genuine = (group == "genuine_live")
    expected = "Allow" if is_genuine else "Not Allow (Step-up or Block)"

    if is_genuine:
        if outcome == "Allow":
            match = True
            discrepancy = None
        else:
            match = False
            discrepancy = "false step-up" if outcome == "Step-up only" else "false block"
    else:
        if outcome in ("Step-up only", "Block"):
            match = True
            discrepancy = None
        else:
            match = False
            discrepancy = "missed"

    return {
        "expected": expected,
        "outcome": outcome,
        "match": match,
        "discrepancy": discrepancy
    }


class DemoRunner:
    """Orchestrates streaming of allowlisted demo audio through the full risk pipeline."""

    def __init__(self, broadcast_callback: Optional[Callable] = None):
        self.broadcast_callback = broadcast_callback
        self.active_task: Optional[asyncio.Task] = None
        self.stop_requested = asyncio.Event()
        self.current_scenario_id: Optional[str] = None
        self.current_call_sid: Optional[str] = None
        self.current_session: Optional[StreamingSession] = None
        self.audit_logger = AuditLogger()
        self.diagnostics_logger = LiveDiagnosticsLogger()

    def is_running(self) -> bool:
        return self.active_task is not None and not self.active_task.done()

    def get_scenarios(self) -> List[Dict[str, Any]]:
        """Returns list of allowlisted demo scenarios."""
        result = []
        for s in DEMO_SCENARIOS.values():
            item = dict(s)
            item["simulation_label"] = SIMULATION_LABEL
            result.append(item)
        return result

    def get_scenario(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        return DEMO_SCENARIOS.get(scenario_id)

    def load_audio_frames(self, audio_path: str) -> List[str]:
        """Loads audio file, downsamples to 8kHz, converts to 20ms G.711 mu-law base64 frames."""
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

    async def run_scenario_stream(
        self,
        scenario_id: str,
        action_sensitivity: str = "balance_check",
        speed: float = 1.0,
        on_window: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Streams a scenario through the real StreamingSession pipeline."""
        scenario = DEMO_SCENARIOS.get(scenario_id)
        if not scenario:
            raise ValueError(f"Scenario {scenario_id} not in allowlist")

        self.current_scenario_id = scenario_id
        call_sid = f"CA_demo_{scenario_id}_{int(time.time())}"
        stream_sid = f"MZ_demo_{scenario_id}_{int(time.time())}"
        self.current_call_sid = call_sid

        frames = self.load_audio_frames(scenario["file_path"])
        session = StreamingSession(
            call_sid=call_sid,
            stream_sid=stream_sid,
            use_spoof=False,
            audit_logger=self.audit_logger
        )
        self.current_session = session

        context = {
            "action": action_sensitivity,
            "action_sensitivity": action_sensitivity,
            "caller_not_allowlisted": False,
            "simulation": True,
            "simulation_label": SIMULATION_LABEL
        }

        # Cadence pacing
        base_frame_delay = 0.020 / max(0.1, speed)
        windows_scored = []
        actions_fired = []
        first_action_audio_sec: Optional[float] = None

        try:
            for idx, payload in enumerate(frames):
                if self.stop_requested.is_set():
                    break

                session.ingest_twilio_payload(payload)

                # Window trigger check: every 16000 samples (1s) after initial 32000 samples (2s)
                if session.audio_buffer.total_samples_received >= 32000 and (session.audio_buffer.total_samples_received % 16000 < 320):
                    ev = session.score_current_window(context)
                    if ev:
                        # Strictly guarantee SIMULATION label and suppress spoof numbers
                        ev["simulation_label"] = SIMULATION_LABEL
                        ev["scenario_id"] = scenario_id
                        ev["scenario_group"] = scenario["group"]

                        # Format action for mock presentation
                        if ev.get("action_trigger") == "step_up":
                            ev["action_display"] = "Step-Up (MOCK OTP)"
                            ev["action_taken"] = "MOCK OTP"
                            actions_fired.append("MOCK OTP")
                            if first_action_audio_sec is None:
                                first_action_audio_sec = round(session.audio_buffer.total_samples_received / 8000.0, 2)
                        elif ev.get("action_trigger") == "block":
                            ev["action_display"] = "Block (Call Disconnected)"
                            ev["action_taken"] = "Block"
                            actions_fired.append("Block")
                            if first_action_audio_sec is None:
                                first_action_audio_sec = round(session.audio_buffer.total_samples_received / 8000.0, 2)
                        else:
                            ev["action_display"] = "Allow"
                            ev["action_taken"] = None

                        # Synthetic spoof is OFF due to measured domain shift
                        if "detector_scores" in ev:
                            ev["detector_scores"]["spoof"] = "OFF (domain shift, see limitations)"
                            ev["detector_scores"].pop("spoof_prob", None)
                        ev["spoof_status"] = "OFF (domain shift, see limitations)"
                        ev.pop("spoof_prob", None)

                        # Outcome and match evaluated across whole stream so far
                        curr_outcome = compute_stream_outcome(actions_fired)
                        curr_eval = evaluate_scenario_match(scenario["group"], curr_outcome)
                        ev["outcome"] = curr_outcome
                        ev["expected_outcome"] = curr_eval["expected"]
                        ev["match"] = curr_eval["match"]
                        ev["discrepancy"] = curr_eval["discrepancy"]

                        windows_scored.append(ev)

                        if on_window:
                            if asyncio.iscoroutinefunction(on_window):
                                await on_window(ev)
                            else:
                                on_window(ev)

                        if self.broadcast_callback:
                            try:
                                if asyncio.iscoroutinefunction(self.broadcast_callback):
                                    await self.broadcast_callback(ev)
                                else:
                                    self.broadcast_callback(ev)
                            except Exception:
                                pass

                await asyncio.sleep(base_frame_delay)

        finally:
            self.current_session = None

        final_band = windows_scored[-1]["band"] if windows_scored else "LOW"
        final_decision = windows_scored[-1]["decision"] if windows_scored else "Allow"
        final_action = actions_fired[0] if actions_fired else "None"
        final_outcome = compute_stream_outcome(actions_fired)
        final_eval = evaluate_scenario_match(scenario["group"], final_outcome)

        return {
            "simulation_label": SIMULATION_LABEL,
            "scenario_id": scenario_id,
            "call_sid": call_sid,
            "total_windows": len(windows_scored),
            "final_band": final_band,
            "final_decision": final_decision,
            "outcome": final_outcome,
            "actions_fired": actions_fired,
            "first_action": final_action,
            "time_to_first_action": first_action_audio_sec,
            "expected_outcome": final_eval["expected"],
            "match": final_eval["match"],
            "discrepancy": final_eval["discrepancy"],
            "windows": windows_scored
        }

    async def start(
        self,
        scenario_id: str,
        action_sensitivity: str = "balance_check",
        speed: float = 1.0
    ) -> Dict[str, Any]:
        """Starts a demo run as an asynchronous task; rejects with 409 if already active."""
        if self.is_running():
            raise RuntimeError("Demo is already running")

        if scenario_id not in DEMO_SCENARIOS:
            raise ValueError(f"Unknown scenario ID: {scenario_id}")

        self.stop_requested.clear()
        scenario = DEMO_SCENARIOS[scenario_id]

        call_sid = f"CA_demo_{scenario_id}_{int(time.time())}"
        self.current_call_sid = call_sid
        self.current_scenario_id = scenario_id

        async def _run_wrapper():
            try:
                await self.run_scenario_stream(
                    scenario_id=scenario_id,
                    action_sensitivity=action_sensitivity,
                    speed=speed
                )
            except asyncio.CancelledError:
                pass
            finally:
                self.active_task = None
                self.current_scenario_id = None
                self.current_call_sid = None

        self.active_task = asyncio.create_task(_run_wrapper())

        return {
            "status": "started",
            "simulation_label": SIMULATION_LABEL,
            "scenario_id": scenario_id,
            "title": scenario["title"],
            "group": scenario["group"],
            "expected_outcome": scenario["expected_outcome"],
            "call_sid": call_sid,
            "speed": speed,
            "action_sensitivity": action_sensitivity
        }

    async def stop(self) -> Dict[str, Any]:
        """Cancels running demo task if active."""
        self.stop_requested.set()
        if self.active_task and not self.active_task.done():
            self.active_task.cancel()
            try:
                await asyncio.wait_for(self.active_task, timeout=1.5)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        self.active_task = None
        self.current_scenario_id = None
        self.current_call_sid = None
        return {
            "status": "stopped",
            "simulation_label": SIMULATION_LABEL
        }
