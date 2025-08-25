#!/bin/bash
# NFL GPP Sim Lab - One-click launcher for macOS/Linux
# This script sets up the environment and launches the Streamlit UI

set -e  # Exit on any error

echo "🏈 NFL GPP Sim Lab - Starting..."
echo "================================"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is required but not found"
    echo "Please install Python 3.10+ and try again"
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment found"
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
python -m pip install --upgrade pip

# Install requirements
echo "📦 Installing requirements..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✅ Requirements installed"
else
    echo "❌ Error: requirements.txt not found"
    exit 1
fi

# Create data directory if it doesn't exist
mkdir -p data/sim_week

# Check if streamlit is available
if ! command -v streamlit &> /dev/null; then
    echo "❌ Error: Streamlit not found after installation"
    echo "Please check the installation and try again"
    exit 1
fi

echo "✅ Setup complete!"
echo ""
echo "🚀 Starting Streamlit app..."
echo "📖 Open your browser to: http://localhost:8501"
echo ""
echo "💡 Press Ctrl+C to stop the application"
echo "================================"

# Launch Streamlit
streamlit run streamlit_app.py