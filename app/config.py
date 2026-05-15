from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
AUDIO_DIR = BASE_DIR / "audio"
DATA_DIR = BASE_DIR / "data"
MODEL_CACHE_DIR = DATA_DIR / "models"

# TTS settings
GENERATION_DIR = AUDIO_DIR

# TTS Service (set to empty string to disable)
TTS_SERVICE_URL = os.environ.get("TTS_SERVICE_URL", "")

# Server settings
HOST = "127.0.0.1"
PORT = 8090

# Ensure directories exist
AUDIO_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
MODEL_CACHE_DIR.mkdir(exist_ok=True)
