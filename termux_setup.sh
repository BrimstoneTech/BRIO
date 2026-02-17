#!/data/data/com.termux/files/usr/bin/bash

echo "========================================="
echo "   Brio AI - Android (Termux) Setup"
echo "========================================="
echo ""

# 1. Update & Install Core Tools
echo "[1/4] Updating Termux packages..."
pkg update -y && pkg upgrade -y
pkg install python git termux-api clang make libjpeg-turbo espeak -y

# 2. Check for Repo
if [ -d "Brio" ]; then
    echo "[2/4] Updating Brio Source Code..."
    cd Brio
    git pull
else
    echo "[2/4] Cloning Brio Source Code..."
    # Note: User will need to provide their auth or use a public repo structure if applicable
    # We assume they are in the folder where they want it.
    # If this script is INSIDE the repo already (which it will be after pull), we skip cloning
    echo "Current directory: $(pwd)"
fi

# 3. Virtual Environment
echo "[3/4] Creating Python Environment..."
if [ ! -d ".venv" ]; then
    python -m venv .venv
fi

# 4. Install Dependencies (Android Specific)
echo "[4/4] Installing Libraries..."
source .venv/bin/activate

# We don't use the full requirements.txt because PyQt5/cffi fails on Android easily
pip install requests beautifulsoup4 pillow 

echo ""
echo "========================================="
echo "   SETUP COMPLETE!"
echo "========================================="
echo "To launch Brio on your phone:"
echo "  python brio_termux.py"
echo ""
echo "Make sure you have installed the 'Termux:API' app from the Play Store!"


