#!/usr/bin/env bash
set -e

# Check for venv
if [ ! -d .venv ]; then
    echo "Virtual environment not found. Run ./install.sh first."
    exit 1
fi
source .venv/bin/activate

# Load local overrides (API keys, etc.) if present
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

cleanup() {
    echo ""
    echo "Shutting down..."
    [ -n "$APP_PID" ] && kill "$APP_PID" 2>/dev/null
    wait 2>/dev/null
    echo "Done."
}
trap cleanup EXIT INT TERM

# Start main app (TTS is handled by the standalone mlx-audio service)
export TTS_SERVICE_URL=http://macstudio1.lab:8203
export LLM_SERVICE_URL=https://lumi-omlx.howlab.us
export LLM_MODEL=gemma-2-9b-it-4bit
echo "Starting NarrateTTS on http://localhost:8090..."
uvicorn app.main:app --host 0.0.0.0 --port 8090 &
APP_PID=$!

echo ""
echo "NarrateTTS is running:"
echo "  App:  http://localhost:8090"
echo "  TTS:  $TTS_SERVICE_URL"
echo ""
echo "Press Ctrl+C to stop."

wait
