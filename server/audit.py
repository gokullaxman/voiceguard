"""
VoiceGuard Cryptographic Audit Chain (Phase 6).
Provides tamper-evident append-only JSONL logging of all call scoring events.
Each record includes a cryptographic SHA-256 hash chaining back to the previous record.
NOTE: A hash chain alone proves internal consistency; it cannot prevent a privileged
attacker with filesystem write permissions from rewriting the whole chain from scratch.
"""

import os
import json
import hashlib
import datetime
from typing import Dict, Any, Optional, Tuple, List

import threading

GENESIS_HASH = "0" * 64
DEFAULT_AUDIT_LOG_PATH = "data/audit/audit_log.jsonl"
_audit_lock = threading.Lock()


def compute_record_hash(record_dict: Dict[str, Any]) -> str:
    """
    Computes deterministic SHA-256 hash over canonical JSON representation of record fields,
    excluding 'record_hash' itself.
    """
    body = {k: v for k, v in record_dict.items() if k != "record_hash"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class AuditLogger:
    def __init__(self, log_path: str = DEFAULT_AUDIT_LOG_PATH):
        self.log_path = log_path
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def get_last_hash(self) -> str:
        """Reads the latest record_hash in the chain, or returns GENESIS_HASH."""
        if not os.path.exists(self.log_path) or os.path.getsize(self.log_path) == 0:
            return GENESIS_HASH

        last_line = None
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    last_line = line.strip()

        if not last_line:
            return GENESIS_HASH

        try:
            record = json.loads(last_line)
            return record.get("record_hash", GENESIS_HASH)
        except Exception:
            return GENESIS_HASH

    def log_event(
        self,
        call_sid: str,
        detector_scores: Dict[str, Any],
        context: Optional[Dict[str, Any]],
        risk: float,
        band: str,
        decision: str,
        explanation: Dict[str, Any],
        timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates and appends a cryptographically chained audit record.
        """
        if timestamp is None:
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

        with _audit_lock:
            prev_hash = self.get_last_hash()

            record = {
                "timestamp": timestamp,
                "call_sid": call_sid,
                "detector_scores": detector_scores,
                "context": context if context is not None else {},
                "risk": round(risk, 4),
                "band": band,
                "decision": decision,
                "explanation": explanation,
                "previous_hash": prev_hash
            }

            h = compute_record_hash(record)
            record["record_hash"] = h

            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")

        return record

    @staticmethod
    def verify_chain(log_path: str = DEFAULT_AUDIT_LOG_PATH) -> Tuple[bool, Optional[str], int]:
        """
        Verifies the cryptographic integrity of an audit chain JSONL file.
        Detects edits, deletions, insertions, and reorderings.
        Returns (is_valid, error_message, count_verified).
        """
        if not os.path.exists(log_path):
            return True, None, 0

        expected_prev_hash = GENESIS_HASH
        count = 0

        with open(log_path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    record = json.loads(line)
                except Exception as e:
                    return False, f"Line {idx}: JSON parse error: {e}", count

                stored_hash = record.get("record_hash")
                prev_hash = record.get("previous_hash")

                if prev_hash != expected_prev_hash:
                    return False, (
                        f"Line {idx} (call_sid={record.get('call_sid')}): Broken chain. "
                        f"Expected previous_hash {expected_prev_hash[:16]}..., but found {prev_hash[:16]}..."
                    ), count

                expected_record_hash = compute_record_hash(record)
                if stored_hash != expected_record_hash:
                    return False, (
                        f"Line {idx} (call_sid={record.get('call_sid')}): Record hash mismatch (tampered content). "
                        f"Stored {stored_hash[:16]}..., recomputed {expected_record_hash[:16]}..."
                    ), count

                expected_prev_hash = stored_hash
                count += 1

        return True, None, count
