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

echo ""
echo "=== Installation complete ==="
echo ""
echo "To start NarrateTTS:"
echo "  ./start.sh"
