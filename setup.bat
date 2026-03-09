@echo off
REM OSINT Conflict Monitor - Quick Setup Script for Windows

echo.
echo ============================================
echo ^🕵️  OSINT Conflict Monitor - Setup
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Python is not installed or not in PATH
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

echo ✅ Python detected
echo.

REM Create virtual environment
echo Creating virtual environment...
python -m venv .venv
if errorlevel 1 (
    echo ❌ Error creating virtual environment
    pause
    exit /b 1
)
echo ✅ Virtual environment created
echo.

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat
echo ✅ Virtual environment activated
echo.

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip --quiet
echo ✅ Pip upgraded
echo.

REM Install dependencies
echo Installing dependencies (this may take a few minutes)...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ❌ Error installing dependencies
    pause
    exit /b 1
)
echo ✅ Dependencies installed
echo.

REM Download spaCy model
echo Downloading spaCy language model...
python -m spacy download en_core_web_sm --quiet
if errorlevel 1 (
    echo ❌ Error downloading spaCy model
    pause
    exit /b 1
)
echo ✅ spaCy model downloaded
echo.

REM Create .env file if it doesn't exist
if not exist .env (
    echo Creating .env file from template...
    copy .env.example .env >nul
    echo ⚠️  Please edit .env and add your NewsAPI key
    echo.
)

REM Create necessary directories
echo Creating data directories...
if not exist intel_data mkdir intel_data
echo ✅ Directories created
echo.

echo ============================================
echo 🎉 Setup complete!
echo ============================================
echo.
echo Next steps:
echo 1. Edit .env and add your NewsAPI key
echo    (Get one free at https://newsapi.org/)
echo 2. Run the dashboard: streamlit run dashboard.py
echo 3. Or run tests: pytest
echo.
echo For more information, see README.md
echo.
pause
