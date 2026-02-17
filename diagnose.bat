@echo off
echo ==========================================
echo   Brio Diagnostic Tool
echo ==========================================
echo.

:: Check Python Environment
echo [1/5] Checking Python Virtual Environment...
if exist ".venv\Scripts\pythonw.exe" (
    echo    [OK] pythonw.exe found
) else (
    echo    [ERROR] pythonw.exe NOT FOUND
    echo    Please run setup.bat to install Brio
    pause
    exit /b 1
)

:: Check Main Script
echo [2/5] Checking Main Script...
if exist "brio_main.py" (
    echo    [OK] brio_main.py found
) else (
    echo    [ERROR] brio_main.py NOT FOUND
    pause
    exit /b 1
)

:: Check Dependencies
echo [3/5] Checking PyQt5 Installation...
.venv\Scripts\python.exe -c "import PyQt5; print('   [OK] PyQt5 installed')" 2>nul
if %errorlevel% neq 0 (
    echo    [ERROR] PyQt5 not installed
    echo    Run: .venv\Scripts\pip install PyQt5
)

echo [4/5] Checking Imports...
.venv\Scripts\python.exe -c "from brio_main import BrioSystem; print('   [OK] All imports successful')" 2>nul
if %errorlevel% neq 0 (
    echo    [ERROR] Import errors detected. Running detailed diagnostics...
    .venv\Scripts\python.exe -c "from brio_main import BrioSystem"
    pause
    exit /b 1
)

:: Check Icon
echo [5/5] Checking Desktop Icon...
if exist "assets\brio_icon.ico" (
    echo    [OK] Icon file found
) else (
    echo    [WARNING] Icon not found, generating...
    .venv\Scripts\python.exe create_icon.py
)

echo.
echo ==========================================
echo   All Checks Passed!
echo ==========================================
echo.
echo Starting Brio in TEST mode (console visible)...
echo Press Ctrl+C to stop.
echo.
.venv\Scripts\python.exe brio_main.py
pause


