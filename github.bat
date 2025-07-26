@echo off
REM GitHub Automation Batch Script for Operation Badger
REM Makes GitHub operations simple with one command

setlocal

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python and add it to PATH.
    pause
    exit /b 1
)

REM Check if required packages are installed
python -c "import dotenv" >nul 2>&1
if errorlevel 1 (
    echo Installing required packages...
    pip install python-dotenv
)

REM Run the git helper script
python git_helper.py %*

pause