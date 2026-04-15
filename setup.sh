#!/usr/bin/env bash
# ============================================================
# setup.sh — Quick-start script for the RAG Chatbot
# ============================================================
set -e

echo ""
echo "==> Setting up RAG Chatbot backend..."

cd "$(dirname "$0")/backend"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
  echo "    Creating Python virtual environment..."
  python3 -m venv .venv
fi

# Activate
source .venv/bin/activate

echo "    Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo ""
echo "✅  Setup complete!"
echo ""
echo "---------------------------------------------"
echo "NEXT STEPS:"
echo "  1. Open backend/.env and set your OPENAI_API_KEY"
echo "  2. Run the backend:"
echo "       cd backend && source .venv/bin/activate && python main.py"
echo "  3. Open frontend/index.html in your browser"
echo "     (use Live Server in VS Code for best results)"
echo "---------------------------------------------"
echo ""
