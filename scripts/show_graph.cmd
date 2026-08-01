@echo off
title Copilot Knowledge Graph Viewer
cd /d "%~dp0.."
".\vevn\Scripts\python.exe" "scripts\show_graph.py"
echo.
pause

