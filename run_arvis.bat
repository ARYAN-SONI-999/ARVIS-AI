@echo off
title ARVIS AI Assistant
echo ============================================================
echo   ARVIS AI ASSISTANT — STARTING APP SERVER
echo ============================================================
echo.
cd /d "%~dp0"

:: Check if virtual environment exists
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found. Please set up venv first.
    pause
    exit /b
)

:: Run the server
echo Launching Flask + SocketIO Server on port 5000...
venv\Scripts\python.exe main.py
echo.
echo Server stopped.
pause
