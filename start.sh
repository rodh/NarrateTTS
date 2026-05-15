#!/usr/bin/env bash
set -e

# Check for venv
if [ ! -d .venv ]; then
    echo "Virtual environment not found. Run ./install.sh first."
    exit 1
fi
source .venv/bin/activate

cleanup() {
    echo ""
    echo "Shutting down..."
    [ -n "$TTS_PID" ] && kill "$TTS_PID" 2>/dev/null
    [ -n "$APP_PID" ] && kill "$APP_PID" 2>/dev/null
    wait 2>/dev/null
    echo "Done."
}
trap cleanup EXIT INT TERM

# Start mlx-audio TTS server in background
echo "Starting Kokoro TTS server on http://localhost:8100..."
python -m mlx_audio.server --host 0.0.0.0 --port 8100 &
TTS_PID=$!
sleep 3

# Start main app
export TTS_SERVICE_URL=http://localhost:8100
echo "Starting NarrateTTS on http://localhost:8090..."
uvicorn app.main:app --host 0.0.0.0 --port 8090 &
APP_PID=$!

echo ""
echo "NarrateTTS is running:"
echo "  App:  http://localhost:8090"
echo "  TTS:  http://localhost:8100"
echo ""
echo "Press Ctrl+C to stop."

wait
