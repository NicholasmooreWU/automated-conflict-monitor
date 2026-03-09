#!/bin/bash

# OSINT Conflict Monitor - Quick Setup Script for Unix/Linux/Mac

echo "🕵️  OSINT Conflict Monitor - Setup"
echo "=================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
required_version="3.10"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then 
    echo "❌ Error: Python 3.10+ is required. You have Python $python_version"
    exit 1
fi
echo "✅ Python $python_version detected"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv .venv
echo "✅ Virtual environment created"
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip --quiet
echo "✅ Pip upgraded"
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt --quiet
echo "✅ Dependencies installed"
echo ""

# Download spaCy model
echo "Downloading spaCy language model..."
python3 -m spacy download en_core_web_sm --quiet
echo "✅ spaCy model downloaded"
echo ""

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your NewsAPI key"
    echo ""
fi

# Create necessary directories
echo "Creating data directories..."
mkdir -p intel_data
echo "✅ Directories created"
echo ""

echo "=================================="
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your NewsAPI key (get one at https://newsapi.org/)"
echo "2. Run the dashboard: streamlit run dashboard.py"
echo "3. Or run tests: pytest"
echo ""
echo "For more information, see README.md"
