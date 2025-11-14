@echo off
REM Swizosoft Admin Portal - Launch Script

echo.
echo ========================================
echo   SWIZOSOFT ADMIN PORTAL
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.7 or higher
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv\" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo [INFO] Installing dependencies...
    pip install -r requirements.txt
) else (
    echo [INFO] Activating virtual environment...
    call venv\Scripts\activate.bat
)

echo.
echo [INFO] Starting Flask application...
echo [INFO] Opening http://localhost:5000 in your browser...
echo.
echo Press Ctrl+C to stop the application
echo.

REM Start the application
python app.py

pause
