#!/usr/bin/env bash
set -e

# Check for venv
if [ ! -d .venv ]; then
    echo "Virtual environment not found. Run ./install.sh first."
    exit 1
fi
source .venv/bin/activate

# Load configuration from .env (see .env.example)
if [ -f .env ]; then
    set -a
    source .env
    set +a
else
    echo "Warning: .env not found. Copy .env.example to .env and configure it."
fi

cleanup() {
    echo ""
    echo "Shutting down..."
    [ -n "$APP_PID" ] && kill "$APP_PID" 2>/dev/null
    wait 2>/dev/null
    echo "Done."
}
trap cleanup EXIT INT TERM

# Start main app (configuration comes from .env)
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
