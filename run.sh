#!/bin/bash

# NFL GPP Simulator - One-click setup and run script (macOS/Linux)

echo "🏈 NFL GPP Simulator - Setup & Launch"
echo "======================================"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is required but not installed"
    echo "Please install Python 3.8+ and try again"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo "❌ Error: Failed to create virtual environment"
        exit 1
    fi
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📥 Installing dependencies..."
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Error: Failed to install dependencies"
    echo "Check requirements.txt and try again"
    exit 1
fi

echo "✅ Setup complete!"
echo ""
echo "🚀 Launching NFL GPP Simulator..."
echo "Opening http://localhost:8501 in your browser..."
echo ""
echo "Press Ctrl+C to stop the server"
echo "======================================"

# Launch Streamlit
streamlit run app.py

# Deactivate virtual environment on exit
deactivate