@echo off
if "%~1"=="" (
    call "%~dp0run.bat"
) else (
    powershell -ExecutionPolicy Bypass -File "%~dp0scripts\vg.ps1" %*
)
