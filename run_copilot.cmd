@echo off
title System-Wide AI Copilot (Windows)

cd /d "%~dp0"

:: Launch Python 3D Pet Overlay using windowless pythonw.exe
if exist "%~dp0vevn\Scripts\pythonw.exe" (
    start "" "%~dp0vevn\Scripts\pythonw.exe" -m src.pet.vrm_pet_gui
) else (
    start "" "%~dp0vevn\Scripts\python.exe" -m src.pet.vrm_pet_gui
)

:: Launch AutoHotkey Engine via bundled portable AutoHotkey v2
if exist "%~dp0bin\AutoHotkey64.exe" (
    start "" "%~dp0bin\AutoHotkey64.exe" "%~dp0copilot.ahk"
    exit /b
)

if exist "%~dp0bin\AutoHotkey32.exe" (
    start "" "%~dp0bin\AutoHotkey32.exe" "%~dp0copilot.ahk"
    exit /b
)

where AutoHotkey64.exe >nul 2>&1
if %errorlevel% equ 0 (
    start "" AutoHotkey64.exe "%~dp0copilot.ahk"
    exit /b
)

where AutoHotkey.exe >nul 2>&1
if %errorlevel% equ 0 (
    start "" AutoHotkey.exe "%~dp0copilot.ahk"
    exit /b
)

start "" "%~dp0copilot.ahk"
exit /b
