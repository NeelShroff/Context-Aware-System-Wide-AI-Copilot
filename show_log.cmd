@echo off
title Copilot Real-Time Log Viewer
echo ======================================================
echo System-Wide AI Copilot - Real-Time Log Viewer
echo ======================================================
echo.

if not exist "%~dp0copilot.log" (
    echo [INFO] Log file has not been created yet.
    echo Try selecting text and pressing Ctrl + Alt + E!
    echo.
    pause
    exit /b 0
)

powershell -NoProfile -Command "Get-Content -Path '%~dp0copilot.log' -Wait -Tail 30"
