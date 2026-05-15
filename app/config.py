from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
AUDIO_DIR = BASE_DIR / "audio"
DATA_DIR = BASE_DIR / "data"

# Kokoro TTS settings
DEFAULT_VOICE = os.environ.get("TTS_VOICE", "af_heart")
KOKORO_MODEL = os.environ.get("KOKORO_MODEL", "mlx-community/Kokoro-82M-bf16")

# TTS Service (set to empty string to use local engine)
TTS_SERVICE_URL = os.environ.get("TTS_SERVICE_URL", "")

# Server settings
HOST = "127.0.0.1"
PORT = 8090

# Ensure directories exist
AUDIO_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
