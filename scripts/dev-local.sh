#!/bin/bash

echo "🚀 Starting local Flask development server..."
echo "📋 Make sure you have Python requirements installed:"
echo "   pip install -r app/requirements.txt"
echo ""

# Get the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT/app"
export FLASK_DEBUG=true
export FLASK_ENV=development
export DEV_PORT=5079
echo "🌐 Starting development server on http://localhost:${DEV_PORT}"
echo "📝 HTML/CSS changes will auto-reload!"

# Use the virtual environment Python if it exists
if [ -f "$PROJECT_ROOT/.venv/bin/python" ]; then
    echo "🐍 Using virtual environment Python"
    "$PROJECT_ROOT/.venv/bin/python" app.py
else
    echo "🐍 Using system Python"
    python app.py
fi