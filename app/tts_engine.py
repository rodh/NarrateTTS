import asyncio
import hashlib
from pathlib import Path

from app.config import AUDIO_DIR, DEFAULT_VOICE, KOKORO_MODEL

# Kokoro voices available via mlx-audio
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


class KokoroEngine:
    def __init__(self, voice: str = DEFAULT_VOICE):
        self.voice = voice

    async def generate(self, text: str, voice: str | None = None) -> Path:
        """Generate audio from text using Kokoro TTS via mlx-audio. Returns path to WAV file."""
        effective_voice = voice or self.voice

        def _synthesize():
            from mlx_audio.tts.generate import generate_audio

            file_hash = hashlib.md5(text[:200].encode()).hexdigest()[:12]
            file_prefix = f"tts_{file_hash}"
            output_path = str(AUDIO_DIR)

            generate_audio(
                text=text,
                model=KOKORO_MODEL,
                voice=effective_voice,
                speed=1.0,
                lang_code="a" if not effective_voice.startswith("b") else "b",
                output_path=output_path,
                file_prefix=file_prefix,
                audio_format="wav",
                join_audio=True,
                verbose=False,
            )

            # generate_audio writes to output_path/file_prefix.wav (or _joined.wav for multi-segment)
            joined = AUDIO_DIR / f"{file_prefix}_joined.wav"
            single = AUDIO_DIR / f"{file_prefix}.wav"
            if joined.exists():
                return joined
            elif single.exists():
                return single
            else:
                # Find any file matching the prefix
                matches = sorted(AUDIO_DIR.glob(f"{file_prefix}*.wav"))
                if matches:
                    return matches[-1]
                raise RuntimeError(f"Kokoro generated no output for prefix {file_prefix}")

        return await asyncio.get_event_loop().run_in_executor(None, _synthesize)


engine = KokoroEngine()
