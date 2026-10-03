Write-Host "=== Starting VoiceGuard Gateway and Exhibition Dashboard ===" -ForegroundColor Cyan
$env:VOICEGUARD_SPOOF_DISPLAY = "calibrated"
Start-Process "http://localhost:8000"
uv run uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload
