@echo off
cd /d "%~dp0"
python ERON_FINAL.py
if errorlevel 1 pause
