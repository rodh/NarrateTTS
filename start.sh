#!/usr/bin/env bash
set -e

echo "Setting up NarrateTTS..."

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Check for ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "Warning: ffmpeg not found. Audio will be saved as WAV instead of MP3."
    echo "Install with: brew install ffmpeg"
fi

# Default: run server
echo ""
echo "Starting server on http://lumi.lab:8090"
echo "         ./start.sh                  (start server)"
echo "         ./start.sh tts              (also start TTS service on :8100)"
echo ""

# Run the server
exec uvicorn app.main:app --host 127.0.0.1 --port 8090
