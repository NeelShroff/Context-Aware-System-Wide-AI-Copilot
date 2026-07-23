@echo off
cd /d "%~dp0\.."
".\vevn\Scripts\python.exe" "src\main.py" "%~1" > "%~2" 2>&1
