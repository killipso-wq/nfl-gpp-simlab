@echo off
REM NFL GPP Sim Lab - One-click launcher for Windows
REM This script sets up the environment and launches the Streamlit UI

echo 🏈 NFL GPP Sim Lab - Starting...
echo ================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Python is required but not found
    echo Please install Python 3.10+ and try again
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python found
python --version

REM Create virtual environment if it doesn't exist
if not exist ".venv" (
    echo 📦 Creating virtual environment...
    python -m venv .venv
    echo ✅ Virtual environment created
) else (
    echo ✅ Virtual environment found
)

REM Activate virtual environment
echo 🔄 Activating virtual environment...
call .venv\Scripts\activate.bat

REM Upgrade pip
echo 📦 Upgrading pip...
python -m pip install --upgrade pip

REM Install requirements
echo 📦 Installing requirements...
if exist "requirements.txt" (
    pip install -r requirements.txt
    echo ✅ Requirements installed
) else (
    echo ❌ Error: requirements.txt not found
    pause
    exit /b 1
)

REM Create data directory if it doesn't exist
if not exist "data\sim_week" mkdir data\sim_week

REM Check if streamlit is available
streamlit --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Streamlit not found after installation
    echo Please check the installation and try again
    pause
    exit /b 1
)

echo ✅ Setup complete!
echo.
echo 🚀 Starting Streamlit app...
echo 📖 Open your browser to: http://localhost:8501
echo.
echo 💡 Press Ctrl+C to stop the application
echo ================================

REM Launch Streamlit
streamlit run streamlit_app.py

pause