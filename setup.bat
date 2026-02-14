@echo off
REM Setup script for Restim Funscript Processor - Windows
REM Creates a virtual environment and installs dependencies

echo ============================================
echo  Restim Funscript Processor - Windows Setup
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.8 or later from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo Found Python:
python --version
echo.

REM Check Python version (need 3.8+)
for /f "tokens=2 delims= " %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set PYTHON_MAJOR=%%a
    set PYTHON_MINOR=%%b
)

if %PYTHON_MAJOR% LSS 3 (
    echo ERROR: Python 3.8 or later is required. Found Python %PYTHON_VERSION%
    pause
    exit /b 1
)
if %PYTHON_MAJOR% EQU 3 if %PYTHON_MINOR% LSS 8 (
    echo ERROR: Python 3.8 or later is required. Found Python %PYTHON_VERSION%
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo Virtual environment created.
) else (
    echo Virtual environment already exists.
)
echo.

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip
echo.

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)
echo.

echo ============================================
echo  Setup Complete!
echo ============================================
echo.
echo To run the application:
echo   1. Activate the environment: venv\Scripts\activate.bat
echo   2. Run the app: python main.py
echo.
echo Or use the run.bat script (will be created now)...

REM Create a run script
(
echo @echo off
echo call venv\Scripts\activate.bat
echo python main.py
echo pause
) > run.bat

echo.
echo Created run.bat - double-click it to start the application!
echo.
pause
