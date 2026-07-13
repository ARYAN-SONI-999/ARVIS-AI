@echo off
title ARVIS Test Suite
echo.
echo  ============================================================
echo    ARVIS COMMAND TEST SUITE
echo  ============================================================
echo.
cd /d "E:\MY AI\real"
venv\Scripts\python.exe test_commands.py
echo.
pause
