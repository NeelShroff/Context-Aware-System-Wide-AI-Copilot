@echo off
title System-Wide AI Copilot (Windows)
echo ======================================================
echo Launching System-Wide AI Copilot (Windows)
echo Hotkey: Ctrl + Alt + E
echo ======================================================
echo.

cd /d "%~dp0"

:: 1. Priority: Bundled Portable AutoHotkey64 v2
if exist "%~dp0bin\AutoHotkey64.exe" (
    echo Launching via bundled portable AutoHotkey v2...
    start "" "%~dp0bin\AutoHotkey64.exe" "%~dp0copilot.ahk"
    goto :success
)

if exist "%~dp0bin\AutoHotkey32.exe" (
    echo Launching via bundled portable AutoHotkey 32-bit...
    start "" "%~dp0bin\AutoHotkey32.exe" "%~dp0copilot.ahk"
    goto :success
)

:: 2. Check System PATH
where AutoHotkey64.exe >nul 2>&1
if %errorlevel% equ 0 (
    echo Launching via system AutoHotkey64.exe...
    start "" AutoHotkey64.exe "%~dp0copilot.ahk"
    goto :success
)

where AutoHotkey.exe >nul 2>&1
if %errorlevel% equ 0 (
    echo Launching via system AutoHotkey.exe...
    start "" AutoHotkey.exe "%~dp0copilot.ahk"
    goto :success
)

:: 3. Check Standard Program Files installation directories
if exist "C:\Program Files\AutoHotkey\v2\AutoHotkey64.exe" (
    echo Launching via installed AutoHotkey v2...
    start "" "C:\Program Files\AutoHotkey\v2\AutoHotkey64.exe" "%~dp0copilot.ahk"
    goto :success
)

if exist "%LOCALAPPDATA%\Programs\AutoHotkey\v2\AutoHotkey64.exe" (
    echo Launching via local AutoHotkey v2...
    start "" "%LOCALAPPDATA%\Programs\AutoHotkey\v2\AutoHotkey64.exe" "%~dp0copilot.ahk"
    goto :success
)

:: 4. Fallback File Association
echo Launching copilot.ahk via Windows file association...
start "" "%~dp0copilot.ahk"

:success
echo.
echo ======================================================
echo [SUCCESS] Copilot is active and running in background!
echo.
echo HOW TO USE:
echo 1. Select text ANYWHERE in Windows
echo 2. Press Ctrl + Alt + E
echo ======================================================
echo.
echo Press any key to close this launcher window (Copilot will stay running).
pause >nul
