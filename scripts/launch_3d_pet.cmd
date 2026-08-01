@echo off
title 3D VRM Desktop Pet Companion
cd /d "%~dp0.."
echo Launching 3D VRM AI Companion Overlay...
start "" "%~dp0..\vevn\Scripts\python.exe" -m src.pet.vrm_pet_gui
echo Done.
