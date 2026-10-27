@echo off
title CrediSense AI - Loan & Credit Policy RAG Copilot
echo =================================================================
echo   CrediSense AI - Loan Policy & Credit Risk RAG Assistant
echo =================================================================
echo.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found at .venv\Scripts\python.exe
    pause
    exit /b 1
)
echo Opening Web Dashboard at http://127.0.0.1:8000 ...
start http://127.0.0.1:8000
echo Starting FastAPI application server...
".venv\Scripts\python.exe" main.py --host 127.0.0.1 --port 8000
pause

