# VoiceGuard PowerShell Command Interface
# Usage: .\scripts\vg.ps1 <command>

param (
    [Parameter(Position=0, Mandatory=$true)]
    [ValidateSet("setup", "test", "eval", "serve", "tunnel", "demo")]
    [string]$Command
)

$ErrorActionPreference = "Stop"

# Ensure FFmpeg is available in environment
$wingetFfmpeg = "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin"
if ((Test-Path $wingetFfmpeg) -and ($env:Path -notlike "*$wingetFfmpeg*")) {
    $env:Path = "$wingetFfmpeg;$env:Path"
}

switch ($Command) {
    "setup" {
        Write-Host "Setting up VoiceGuard environment with uv..." -ForegroundColor Cyan
        uv sync
        uv run python scripts/download_models.py
        Write-Host "Setup complete." -ForegroundColor Green
    }
    "test" {
        Write-Host "Running VoiceGuard test suite..." -ForegroundColor Cyan
        uv run pytest tests/test_p1_gate.py -v -s
    }
    default {
        Write-Host "Command '$Command' is not yet implemented for the current phase." -ForegroundColor Yellow
    }
}
