import asyncio
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
AUDIO_DIR = BASE_DIR / "audio"
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"

# Kokoro TTS settings
DEFAULT_VOICE = os.environ.get("TTS_VOICE", "af_heart")
KOKORO_MODEL = os.environ.get("KOKORO_MODEL", "mlx-community/Kokoro-82M-bf16")

# Standalone mlx-audio (Kokoro) TTS service
TTS_SERVICE_URL = os.environ.get("TTS_SERVICE_URL", "http://macstudio1.lab:8203")

# Kokoro voices available via the TTS service
KOKORO_VOICES = [
    {"id": "af_heart", "name": "Heart (F)"},
    {"id": "af_bella", "name": "Bella (F)"},
    {"id": "af_nicole", "name": "Nicole (F)"},
    {"id": "af_sarah", "name": "Sarah (F)"},
    {"id": "af_sky", "name": "Sky (F)"},
    {"id": "am_adam", "name": "Adam (M)"},
    {"id": "am_michael", "name": "Michael (M)"},
    {"id": "bf_emma", "name": "Emma (F, UK)"},
    {"id": "bf_isabella", "name": "Isabella (F, UK)"},
    {"id": "bm_george", "name": "George (M, UK)"},
    {"id": "bm_lewis", "name": "Lewis (M, UK)"},
]

# LLM Service for summaries (empty = disabled, uses text extraction fallback)
LLM_SERVICE_URL = os.environ.get("LLM_SERVICE_URL", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "gemma-2-9b-it-4bit")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_SEMAPHORE = asyncio.Semaphore(1)

# Feed settings
FEED_TTL_DAYS = int(os.environ.get("FEED_TTL_DAYS", "7"))

# Server settings
HOST = "127.0.0.1"
PORT = 8090

# Ensure directories exist
AUDIO_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)
