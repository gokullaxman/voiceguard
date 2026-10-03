"""
VoiceGuard Risk Fusion Engine & Sustained Evidence Evaluator (Phase 3 Step 7).
Fuses SPOOF, SPEAKER, and REPLAY detectors with contextual adjustments.
Enforces weight renormalization for missing detectors and temporal smoothing.
"""

import os
import math
import yaml
from typing import Dict, Any, Optional, Tuple, List
import numpy as np


class RiskEngine:
    DEFAULT_CONFIG = {
        "weights": {"spoof": 0.40, "speaker": 0.30, "replay": 0.30},
        "bands": {"low_max": 0.30, "medium_max": 0.60},
        "speaker_mapping": {"a": 0.15, "b": 0.75},
        "context_adjustments": {
            "action_sensitivity": {
                "balance_check": 0.00,
                "wire_transfer": 0.20,
                "password_reset": 0.15,
                "unvalidated_design_label": "unvalidated design values"
            },
            "caller_not_allowlisted": 0.15,
            "call_time_anomaly": 0.10
        },
        "sustained_evidence": {
            "consecutive_windows_required": 3,
            "window_threshold": 0.60
        }
    }

    def __init__(self, config_path: Optional[str] = "config/settings.yaml"):
        self.config_path = config_path
        self.config = dict(self.DEFAULT_CONFIG)
        if config_path and os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if loaded and "risk_engine" in loaded:
                    self.config = loaded["risk_engine"]

    def get_config_hash(self) -> str:
        """Returns SHA-256 hash of the whole settings.yaml file bytes as loaded by the server."""
        import hashlib
        if self.config_path and os.path.exists(self.config_path):
            with open(self.config_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        raw = yaml.dump(self.config, sort_keys=True).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def get_live_config_hash(live_config_path: str = "config/live.yaml") -> str:
        """Returns SHA-256 hash of the whole live.yaml file bytes."""
        import hashlib
        if os.path.exists(live_config_path):
            with open(live_config_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        return ""

    def compute_risk(
        self,
        spoof_prob: Optional[float] = None,
        speaker_sim: Optional[float] = None,
        replay_prob: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
        speaker_map: Optional[Tuple[float, float]] = None
    ) -> Dict[str, Any]:
        """
        Computes fused risk score.
        Inputs:
          - spoof_prob: in [0, 1] (or None)
          - speaker_sim: cosine similarity, typical [-1, 1] (or None)
          - replay_prob: in [0, 1] (or None)
          - context: optional dict (e.g. {'action': 'wire_transfer', 'allowlisted': False, 'call_time_anomaly': True})
        """
        # 1. Validation
        for name, val in [("spoof_prob", spoof_prob), ("replay_prob", replay_prob)]:
            if val is not None:
                if math.isnan(val) or math.isinf(val):
                    raise ValueError(f"{name} must not be NaN or Inf.")
                if not (0.0 <= val <= 1.0):
                    raise ValueError(f"{name} out of range [0, 1]: {val}")

        if speaker_sim is not None:
            if math.isnan(speaker_sim) or math.isinf(speaker_sim):
                raise ValueError("speaker_sim must not be NaN or Inf.")
            if not (-1.0 <= speaker_sim <= 1.0):
                raise ValueError(f"speaker_sim out of range [-1, 1]: {speaker_sim}")

        # 2. Speaker mapping to risk input (1 - speaker_map)
        speaker_risk = None
        if speaker_sim is not None:
            if speaker_map is not None:
                a, b = speaker_map
            else:
                a = float(self.config["speaker_mapping"]["a"])
                b = float(self.config["speaker_mapping"]["b"])

            if b <= a:
                raise ValueError(f"Invalid speaker_mapping: b ({b}) must be strictly greater than a ({a}).")

            mapped_sim = max(0.0, min(1.0, (speaker_sim - a) / (b - a)))
            speaker_risk = 1.0 - mapped_sim

        # 3. Detectors and Renormalization
        active_detectors = {}
        missing_detectors = []

        raw_weights = self.config["weights"]

        if spoof_prob is not None:
            active_detectors["spoof"] = (spoof_prob, raw_weights["spoof"])
        else:
            missing_detectors.append("spoof")

        if speaker_risk is not None:
            active_detectors["speaker"] = (speaker_risk, raw_weights["speaker"])
        else:
            missing_detectors.append("speaker")

        if replay_prob is not None:
            active_detectors["replay"] = (replay_prob, raw_weights["replay"])
        else:
            missing_detectors.append("replay")

        if not active_detectors:
            raise ValueError("All detectors returned None. Cannot compute risk.")

        # Renormalize active weights
        total_active_weight = sum(w for _, w in active_detectors.values())
        normalized_weights = {k: w / total_active_weight for k, (_, w) in active_detectors.items()}

        contributions = {}
        base_risk = 0.0
        for k, (score, _) in active_detectors.items():
            contrib = normalized_weights[k] * score
            contributions[k] = round(contrib, 6)
            base_risk += contrib

        base_risk = float(np.clip(base_risk, 0.0, 1.0))

        # 4. Context Adjustments (Unvalidated Design Values)
        adjustments = {}
        total_adj = 0.0

        if context:
            adj_cfg = self.config.get("context_adjustments", {})

            # Action sensitivity
            act = context.get("action")
            if act:
                act_cfg = adj_cfg.get("action_sensitivity", {})
                act_val = act_cfg.get(act, 0.0)
                if act_val > 0.0:
                    adjustments["action_sensitivity"] = {
                        "action": act,
                        "value": act_val,
                        "label": "unvalidated design values"
                    }
                    total_adj += act_val

            # Allow-list
            if context.get("caller_not_allowlisted", False):
                val = adj_cfg.get("caller_not_allowlisted", 0.15)
                adjustments["caller_not_allowlisted"] = {
                    "value": val,
                    "label": "unvalidated design values"
                }
                total_adj += val

            # Call time anomaly
            if context.get("call_time_anomaly", False):
                val = adj_cfg.get("call_time_anomaly", 0.10)
                adjustments["call_time_anomaly"] = {
                    "value": val,
                    "label": "unvalidated design values"
                }
                total_adj += val

        # 5. Final Risk and Bands
        final_risk = float(np.clip(base_risk + total_adj, 0.0, 1.0))

        low_max = float(self.config["bands"]["low_max"])
        med_max = float(self.config["bands"]["medium_max"])

        if final_risk < low_max:
            band = "LOW"
            decision = "Allow"
        elif final_risk <= med_max:
            band = "MEDIUM"
            decision = "Step-Up / Challenge"
        else:
            band = "HIGH"
            decision = "Block / Terminate"

        return {
            "base_risk": round(base_risk, 4),
            "contributions": contributions,
            "normalized_weights": {k: round(w, 4) for k, w in normalized_weights.items()},
            "missing_detectors": missing_detectors,
            "adjustments": adjustments,
            "total_adjustments": round(total_adj, 4),
            "final_risk": round(final_risk, 4),
            "band": band,
            "decision": decision,
            "explanation": {
                "base": round(base_risk, 4),
                "adjustments_total": round(total_adj, 4),
                "final": round(final_risk, 4),
                "band": band,
                "missing": missing_detectors if missing_detectors else "None"
            }
        }


class SustainedEvidence:
    """
    Suppresses transient spikes:
    - No action (step_up or block) fires before N consecutive qualifying windows.
    - MEDIUM sustained N windows -> step_up
    - HIGH sustained N windows -> block
    - Band drop mid-stream (HIGH -> MEDIUM, or MEDIUM/HIGH -> LOW) resets qualifying streaks.
    - Actions are idempotent (duplicate triggers suppressed).
    """
    def __init__(
        self,
        consecutive_required: int = 3,
        threshold: float = 0.60,
        medium_threshold: float = 0.30,
        high_threshold: float = 0.60
    ):
        self.consecutive_required = consecutive_required
        self.threshold = threshold
        self.medium_threshold = medium_threshold
        self.high_threshold = high_threshold
        self.consecutive_count = 0
        self.high_count = 0
        self.medium_count = 0
        self.step_up_triggered = False
        self.block_triggered = False
        self.escalated = False

    def add_window(self, risk_score: float) -> bool:
        """
        Adds window risk score.
        Returns True if sustained high escalation condition is met, False otherwise.
        Maintains backwards compatibility with tests expecting bool.
        """
        res = self.evaluate_window(risk_score)
        return res["is_sustained_high"]

    def evaluate_window(self, risk_score: float) -> Dict[str, Any]:
        """
        Evaluates risk score and sustained window counts.
        Enforces:
        - No action fires before N consecutive qualifying windows.
        - HIGH sustained N windows -> block action.
        - MEDIUM sustained N windows -> step_up action.
        - Band drop resets streaks.
        - Idempotent triggers.
        """
        if risk_score >= self.high_threshold:
            self.high_count += 1
            self.medium_count += 1
            self.consecutive_count = self.high_count
            band = "HIGH"
        elif risk_score >= self.medium_threshold:
            self.high_count = 0  # Reset high streak on drop to medium
            self.consecutive_count = 0
            self.medium_count += 1
            band = "MEDIUM"
        else:
            self.high_count = 0
            self.medium_count = 0
            self.consecutive_count = 0
            band = "LOW"

        is_sustained_high = (self.high_count >= self.consecutive_required)
        is_sustained_medium = (self.medium_count >= self.consecutive_required)
        self.escalated = is_sustained_high

        action_trigger = None

        if band == "HIGH":
            if is_sustained_high:
                decision = "Block (Sustained Impersonation Attack)"
                if not self.block_triggered:
                    action_trigger = "block"
                    self.block_triggered = True
            else:
                decision = "Monitoring (Awaiting Sustained High Evidence)"
        elif band == "MEDIUM":
            if is_sustained_medium:
                decision = "Step-Up / Challenge (Sustained Medium Risk)"
                if not self.step_up_triggered:
                    action_trigger = "step_up"
                    self.step_up_triggered = True
            else:
                decision = "Monitoring (Awaiting Sustained Medium Evidence)"
        else:
            decision = "Allow"

        return {
            "band": band,
            "decision": decision,
            "action_trigger": action_trigger,
            "is_sustained_high": is_sustained_high,
            "is_sustained_medium": is_sustained_medium,
            "high_count": self.high_count,
            "medium_count": self.medium_count
        }

    def reset(self):
        self.consecutive_count = 0
        self.high_count = 0
        self.medium_count = 0
        self.step_up_triggered = False
        self.block_triggered = False
        self.escalated = False
