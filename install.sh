#!/usr/bin/env bash
set -e

echo "=== NarrateTTS Installer ==="
echo ""

# Check for Python 3.11-3.13 (3.14 not yet supported by all dependencies)
PYTHON=""
for PY in python3.13 python3.12 python3.11 python3; do
    if command -v "$PY" &> /dev/null; then
        VER=$("$PY" -c "import sys; v=sys.version_info; print(f'{v.major}.{v.minor}')")
        MAJOR=$("$PY" -c "import sys; print(sys.version_info.major)")
        MINOR=$("$PY" -c "import sys; print(sys.version_info.minor)")
        if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 11 ] && [ "$MINOR" -le 13 ]; then
            PYTHON="$PY"
            echo "Found Python $VER at $(which $PY)"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "Error: Python 3.11-3.13 required (3.14 not yet supported by all deps)."
    echo "  brew install python@3.13"
    exit 1
fi

# Check for espeak-ng (required by phonemizer for text processing)
if ! command -v espeak-ng &> /dev/null; then
    echo "Installing espeak-ng..."
    if command -v brew &> /dev/null; then
        brew install espeak-ng
    else
        echo "Error: espeak-ng not found. Install with: brew install espeak-ng"
        exit 1
    fi
fi

# Check for ffmpeg (optional, for WAV→MP3 conversion in local mode)
if ! command -v ffmpeg &> /dev/null; then
    echo "Note: ffmpeg not found (optional). Without it, local engine saves WAV instead of MP3."
    echo "  Install with: brew install ffmpeg"
fi

# Create virtual environment
if [ ! -d .venv ]; then
    echo ""
    echo "Creating virtual environment with $PYTHON..."
    $PYTHON -m venv .venv
else
    echo "Virtual environment already exists."
fi
source .venv/bin/activate

# Install dependencies
echo ""
echo "Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Download spacy English model (used by misaki for tokenization)
echo ""
echo "Downloading spacy English model..."
python -m spacy download en_core_web_sm -q 2>&1 || true

# Pre-download the Kokoro model so first run is fast
echo ""
echo "Pre-downloading Kokoro TTS model (~500MB)..."
python3 -c "
from mlx_audio.utils import load_model
print('Loading Kokoro-82M model...')
model = load_model('mlx-community/Kokoro-82M-bf16')
print('Model downloaded and cached.')
"

echo ""
echo "=== Installation complete ==="
echo ""
echo "To start NarrateTTS:"
echo "  ./start.sh"
