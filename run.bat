@echo off
REM NFL GPP Simulator - One-click setup and run script (Windows)

echo 🏈 NFL GPP Simulator - Setup ^& Launch
echo ======================================

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Error: Python is required but not installed
    echo Please install Python 3.8+ and try again
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist ".venv" (
    echo 📦 Creating virtual environment...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo ❌ Error: Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo 🔄 Activating virtual environment...
call .venv\Scripts\activate.bat

REM Upgrade pip
echo ⬆️  Upgrading pip...
python -m pip install --upgrade pip

REM Install requirements
echo 📥 Installing dependencies...
pip install -r requirements.txt

if %errorlevel% neq 0 (
    echo ❌ Error: Failed to install dependencies
    echo Check requirements.txt and try again
    pause
    exit /b 1
)

echo ✅ Setup complete!
echo.
echo 🚀 Launching NFL GPP Simulator...
echo Opening http://localhost:8501 in your browser...
echo.
echo Press Ctrl+C to stop the server
echo ======================================

REM Launch Streamlit
streamlit run app.py

REM Deactivate virtual environment on exit
call .venv\Scripts\deactivate.bat
pause