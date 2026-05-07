#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
#  Brio Web — Setup Script (Linux / macOS)
# ═══════════════════════════════════════════════════════════
set -e

echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║     BRIO — Sentient AI Companion         ║"
echo "  ║     Web Edition Setup                    ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "  ✗ Python 3 not found. Please install Python 3.9+"
    exit 1
fi
echo "  ✓ Python: $(python3 --version)"

# 2. Install pip deps
echo "  → Installing dependencies…"
pip3 install -q flask flask-socketio requests
echo "  ✓ Dependencies installed (flask, flask-socketio, requests)"

# 3. Check Ollama
echo ""
if command -v ollama &> /dev/null; then
    echo "  ✓ Ollama found: $(ollama --version 2>/dev/null || echo 'installed')"
    
    # Check if running
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "  ✓ Ollama is running"
        
        # Check for llama3.2
        if ollama list 2>/dev/null | grep -q "llama3.2"; then
            echo "  ✓ Model llama3.2 available"
        else
            echo "  ⚠ Model llama3.2 not found."
            read -p "    Pull llama3.2 now? (y/n): " yn
            if [ "$yn" = "y" ] || [ "$yn" = "Y" ]; then
                ollama pull llama3.2
            fi
        fi
    else
        echo "  ⚠ Ollama is installed but not running."
        echo "    Start it with:  ollama serve"
    fi
else
    echo "  ⚠ Ollama not found."
    echo "    Install from: https://ollama.ai"
    echo "    Then run:     ollama serve && ollama pull llama3.2"
fi

echo ""
echo "  ════════════════════════════════════════════"
echo "  Setup complete! Launch Brio:"
echo ""
echo "    python3 brio_web.py"
echo ""
echo "  Then open http://localhost:5000"
echo "  ════════════════════════════════════════════"
echo ""
