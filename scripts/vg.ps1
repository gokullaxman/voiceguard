# VoiceGuard PowerShell Operations CLI
param (
    [Parameter(Position=0, Mandatory=$true)]
    [ValidateSet("setup", "test", "eval", "serve", "tunnel", "demo", "preflight", "golive")]
    [string]$Command,
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$RemainingArgs
)

$ErrorActionPreference = "Stop"

switch ($Command) {
    "setup" {
        Write-Host "=== Setting up VoiceGuard Environment ===" -ForegroundColor Cyan
        uv sync
        if (-not (Test-Path ".env")) {
            Write-Host "Generating fresh enrollment key in .env..." -ForegroundColor Yellow
            uv run python scripts/enroll.py --gen-key
        }
        Write-Host "Setup complete." -ForegroundColor Green
    }
    "test" {
        Write-Host "=== Running VoiceGuard Test Suite ===" -ForegroundColor Cyan
        uv run pytest -v
    }
    "eval" {
        Write-Host "=== Running VoiceGuard Fused Evaluation ===" -ForegroundColor Cyan
        uv run python scratch/run_step4_fused_eval.py
    }
    "serve" {
        Write-Host "=== Starting VoiceGuard Telephony Gateway (Uvicorn) ===" -ForegroundColor Cyan
        uv run uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload
    }
    "tunnel" {
        Write-Host "=== Establishing Public Telephony Tunnel ===" -ForegroundColor Cyan
        Write-Host "Exposing port 8000 for Twilio Voice Webhooks..." -ForegroundColor Yellow
        Write-Host "Run: ngrok http 8000  OR  cloudflared tunnel --url http://localhost:8000" -ForegroundColor Gray
    }
    "golive" {
        Write-Host "=== VoiceGuard GoLive Tunnel Setup ===" -ForegroundColor Cyan
        uv run python scripts/golive.py $RemainingArgs
    }
    "demo" {
        Write-Host "=== Starting VoiceGuard Exhibition Demo Server [SIMULATION, not a live call] ===" -ForegroundColor Cyan
        Write-Host "Opening http://localhost:8000 in your browser..." -ForegroundColor Yellow
        $env:VOICEGUARD_SPOOF_DISPLAY = "calibrated"
        Start-Process "http://localhost:8000"
        uv run uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload
    }
    "preflight" {
        Write-Host "=== Running VoiceGuard Preflight Health Checks ===" -ForegroundColor Cyan
        uv run python scripts/preflight.py
    }
}
