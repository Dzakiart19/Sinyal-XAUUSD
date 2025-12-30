#!/bin/bash

# XAUUSD Bot Installation Script

echo "=========================================="
echo "XAUUSD Scalping Bot Installation"
echo "=========================================="

# Check Python version
echo -n "Checking Python version..."
python_version=$(python3 --version 2>/dev/null || echo "not found")
if [[ $python_version == "not found" ]]; then
    echo "❌"
    echo "Error: Python 3 not found!"
    echo "Please install Python 3.8 or higher first."
    exit 1
fi

echo "✅ $python_version"

# Check pip
echo -n "Checking pip..."
if ! command -v pip3 &> /dev/null; then
    echo "❌"
    echo "Error: pip3 not found!"
    echo "Please install pip first: apt install python3-pip (Ubuntu/Debian)"
    exit 1
fi
echo "✅"

# Create virtual environment
echo -n "Creating virtual environment..."
python3 -m venv venv
if [ $? -eq 0 ]; then
    echo "✅"
else
    echo "❌"
    echo "Error: Failed to create virtual environment"
    exit 1
fi

# Activate virtual environment
echo -n "Activating virtual environment..."
source venv/bin/activate
echo "✅"

# Upgrade pip
echo -n "Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅"
else
    echo "❌"
fi

# Install dependencies
echo -n "Installing dependencies..."
pip install -r requirements.txt > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅"
else
    echo "❌"
    echo "Error: Failed to install dependencies"
    exit 1
fi

# Create directories
echo -n "Creating directories..."
mkdir -p data logs config
echo "✅"

# Check .env file
if [ ! -f .env ]; then
    echo "⚠️  File .env tidak ditemukan!"
    echo "Silakan edit file .env dan isi TELEGRAM_BOT_TOKEN Anda"
    cp .env.example .env 2>/dev/null || true
fi

echo ""
echo "=========================================="
echo "Installation Complete! ✅"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit file .env dan isi TELEGRAM_BOT_TOKEN"
echo "2. Jalankan bot: python main.py"
echo ""
echo "Untuk mendapatkan bot token:"
echo "1. Buka Telegram"
echo "2. Cari @BotFather"
echo "3. Buat bot baru: /newbot"
echo "4. Salin token dan isi di file .env"
echo ""
echo "Happy Trading! 🚀"