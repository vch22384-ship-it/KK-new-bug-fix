@echo off
title Avatar Microphone WebSocket Service
cd /d "%~dp0"

:: Detect Python launcher on Windows
where py >nul 2>nul
if %errorlevel%==0 (
    set PY_CMD=py
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        set PY_CMD=python
    ) else (
        echo [ERROR] Python is not installed yet!
        echo Run this command in PowerShell first:
        echo winget install -e --id Python.Python.3.12
        pause
        exit /b 1
    )
)

echo Checking Python dependencies...
%PY_CMD% -m pip install -q -r requirements.txt

:loop
echo Starting Microphone WebSocket Service...
%PY_CMD% server.py
echo Service stopped or crashed. Restarting in 3 seconds...
timeout /t 3
goto loop
