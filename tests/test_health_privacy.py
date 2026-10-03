"""
Unit tests for /health endpoint privacy and schema (Step 3).
Asserts that /health returns only non-secret status flags, and that NO
values from .env (SIDs, tokens, phone numbers, enrollment keys) appear in the response.
"""

import os
from pathlib import Path
from dotenv import dotenv_values
from fastapi.testclient import TestClient
from server.app import app

client = TestClient(app)


def test_health_endpoint_schema_and_privacy():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()

    # Required keys according to Step 3 specification
    expected_keys = [
        "public_base_url_set",
        "dry_mode",
        "spoof_enabled",
        "config_hash",
        "live_config_hash",
        "enrollment_loaded",
        "twilio_credentials_present",
        "models_loaded",
    ]
    for key in expected_keys:
        assert key in data, f"Missing key in /health response: {key}"

    # Verify types of booleans
    assert isinstance(data["public_base_url_set"], bool)
    assert isinstance(data["dry_mode"], bool)
    assert isinstance(data["spoof_enabled"], bool)
    assert isinstance(data["enrollment_loaded"], bool)
    assert isinstance(data["twilio_credentials_present"], bool)
    assert isinstance(data["models_loaded"], bool)

    # Verify hashes are 64-char hex strings
    assert len(data["config_hash"]) == 64
    assert len(data["live_config_hash"]) == 64

    # Privacy assertion: check against all values in .env
    env_path = Path(".env")
    if env_path.exists():
        raw_response_text = response.text
        env_vals = dotenv_values(env_path)
        for k, v in env_vals.items():
            if not v or len(str(v).strip()) < 4:
                continue
            v_clean = str(v).strip()
            # None of the secret values (account sid, auth token, phone number, keys) should appear in response
            # Note: PUBLIC_BASE_URL or boolean flags are non-secret, but any credential must never appear
            if any(secret_key in k.upper() for secret_key in ["KEY", "TOKEN", "SID", "SECRET", "PHONE"]):
                assert v_clean not in raw_response_text, f"Secret from {k} leaked in /health response!"
