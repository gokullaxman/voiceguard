@echo off
echo === Starting VoiceGuard Gateway and Exhibition Dashboard ===
set VOICEGUARD_SPOOF_DISPLAY=calibrated
start http://localhost:8000
uv run uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload
