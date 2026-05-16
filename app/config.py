from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
AUDIO_DIR = BASE_DIR / "audio"
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"

# Kokoro TTS settings
DEFAULT_VOICE = os.environ.get("TTS_VOICE", "af_heart")
KOKORO_MODEL = os.environ.get("KOKORO_MODEL", "mlx-community/Kokoro-82M-bf16")

# TTS Service (set to empty string to use local engine)
TTS_SERVICE_URL = os.environ.get("TTS_SERVICE_URL", "")

# LLM Service for summaries (empty = disabled, uses text extraction fallback)
LLM_SERVICE_URL = os.environ.get("LLM_SERVICE_URL", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "mlx-community/Qwen3.5-9B-8bit")

# Server settings
HOST = "127.0.0.1"
PORT = 8090

# Ensure directories exist
AUDIO_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)
