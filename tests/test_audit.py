"""
Unit Tests for VoiceGuard Cryptographic Audit Chain (server/audit.py).
Validates:
  - Valid chain verifies cleanly
  - In-place modification/edit is detected
  - Record deletion is detected
  - Record reordering is detected
  - Record insertion is detected
"""

import os
import json
import pytest
from server.audit import AuditLogger, compute_record_hash, GENESIS_HASH


@pytest.fixture
def temp_audit_log(tmp_path):
    log_path = str(tmp_path / "test_audit.jsonl")
    logger = AuditLogger(log_path=log_path)
    
    # Generate 5 chained records
    for i in range(1, 6):
        logger.log_event(
            call_sid=f"CA_test_{i:03d}",
            detector_scores={"spoof": 0.1 * i, "speaker": 0.8, "replay": 0.05 * i},
            context={"action": "balance_check"},
            risk=0.15 * i,
            band="LOW" if i < 3 else "MEDIUM",
            decision="Allow" if i < 3 else "Step-Up / Challenge",
            explanation={"base": 0.15 * i}
        )
    return log_path


def test_valid_chain_verifies(temp_audit_log):
    """Verifies that an unmodified chain passes validation."""
    is_valid, err, count = AuditLogger.verify_chain(temp_audit_log)
    assert is_valid is True
    assert err is None
    assert count == 5


def test_edit_detected(temp_audit_log):
    """Verifies that editing a field in any record is detected."""
    with open(temp_audit_log, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Modify line 3 content (tamper with decision)
    rec = json.loads(lines[2])
    rec["decision"] = "Allow"  # Was Step-Up
    lines[2] = json.dumps(rec) + "\n"

    with open(temp_audit_log, "w", encoding="utf-8") as f:
        f.writelines(lines)

    is_valid, err, count = AuditLogger.verify_chain(temp_audit_log)
    assert is_valid is False
    assert "Record hash mismatch" in err
    assert count == 2  # First 2 were valid


def test_deletion_detected(temp_audit_log):
    """Verifies that deleting a record breaks the previous_hash link."""
    with open(temp_audit_log, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Delete record 3 (index 2)
    del lines[2]

    with open(temp_audit_log, "w", encoding="utf-8") as f:
        f.writelines(lines)

    is_valid, err, count = AuditLogger.verify_chain(temp_audit_log)
    assert is_valid is False
    assert "Broken chain" in err
    assert count == 2


def test_reorder_detected(temp_audit_log):
    """Verifies that swapping the order of two records breaks hash chaining."""
    with open(temp_audit_log, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Swap records 2 and 3
    lines[1], lines[2] = lines[2], lines[1]

    with open(temp_audit_log, "w", encoding="utf-8") as f:
        f.writelines(lines)

    is_valid, err, count = AuditLogger.verify_chain(temp_audit_log)
    assert is_valid is False
    assert "Broken chain" in err
    assert count == 1


def test_insertion_detected(temp_audit_log):
    """Verifies that inserting a foreign record breaks the chain."""
    with open(temp_audit_log, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Create an inserted record
    fake_record = {
        "timestamp": "2026-10-02T12:00:00Z",
        "call_sid": "CA_injected",
        "detector_scores": {},
        "context": {},
        "risk": 0.0,
        "band": "LOW",
        "decision": "Allow",
        "explanation": {},
        "previous_hash": GENESIS_HASH
    }
    fake_record["record_hash"] = compute_record_hash(fake_record)
    lines.insert(2, json.dumps(fake_record) + "\n")

    with open(temp_audit_log, "w", encoding="utf-8") as f:
        f.writelines(lines)

    is_valid, err, count = AuditLogger.verify_chain(temp_audit_log)
    assert is_valid is False
    assert "Broken chain" in err
    assert count == 2
