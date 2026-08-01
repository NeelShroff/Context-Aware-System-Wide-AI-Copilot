@echo off
title Copilot Web Dashboard Launcher
echo ======================================================
echo Launching Interactive Knowledge Graph Web Dashboard...
echo ======================================================
echo.

cd /d "%~dp0.."
".\vevn\Scripts\python.exe" "scripts\web_dashboard.py"
pause
