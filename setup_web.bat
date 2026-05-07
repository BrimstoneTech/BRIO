@echo off
REM ═══════════════════════════════════════════════════════════
REM  Brio Web — Setup Script (Windows)
REM ═══════════════════════════════════════════════════════════

echo.
echo   ╔══════════════════════════════════════════╗
echo   ║     BRIO — Sentient AI Companion         ║
echo   ║     Web Edition Setup                    ║
echo   ╚══════════════════════════════════════════╝
echo.

REM 1. Check Python
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo   ✗ Python not found. Please install Python 3.9+ from python.org
    pause
    exit /b 1
)
echo   ✓ Python found

REM 2. Install deps
echo   → Installing dependencies...
pip install flask flask-socketio requests -q
echo   ✓ Dependencies installed

REM 3. Check Ollama
echo.
ollama --version >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo   ✓ Ollama found
    echo   → Make sure Ollama is running: ollama serve
    echo   → Pull a model if needed:     ollama pull llama3.2
) else (
    echo   ⚠ Ollama not found.
    echo     Install from: https://ollama.ai
    echo     Then run:     ollama serve
    echo                   ollama pull llama3.2
)

echo.
echo   ════════════════════════════════════════════
echo   Setup complete! Launch Brio:
echo.
echo     python brio_web.py
echo.
echo   Then open http://localhost:5000
echo   ════════════════════════════════════════════
echo.
pause
