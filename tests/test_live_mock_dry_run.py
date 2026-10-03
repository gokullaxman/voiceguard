"""
Integration Test: VoiceGuard Live-Path Dry Run with Mocks (Phase 4 / Step 4).
Tests:
  - Twilio Webhook (POST /voice) signature validation and TwiML wss:// stream generation
  - WebSocket media stream handshake and token consumption
  - Real-time scoring and risk band classification
  - Step-up challenge trigger
  - Sustained evidence rule: Block fires only after N consecutive HIGH windows
  - Post-termination media frame ignoring
  - Mid-stream disconnect cleanup
  - Cryptographic audit chain integrity
"""

import pytest
from scripts.dry_run_simulation import run_live_pipeline_dry_run


def test_live_path_pipeline_mock_dry_run():
    """Executes the full simulated live pipeline and asserts all gates pass."""
    success = run_live_pipeline_dry_run()
    assert success is True
