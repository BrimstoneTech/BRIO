@echo off
echo Starting Brio with enhanced logging...

cd /d "%~dp0"

REM Redirect all output to a log file
".venv\Scripts\python.exe" brio_main.py > console_output.txt 2>&1

echo Brio has exited. Check console_output.txt for details.
pause


