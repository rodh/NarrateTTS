import asyncio
import os
import struct
import subprocess
from pathlib import Path

from app.config import GENERATION_DIR

DEFAULT_VOICE = "en_US-lessac-medium"


class PiperEngine:
    def __init__(self, voice: str = DEFAULT_VOICE):
        self.voice = voice
        self._binary = None

    @property
    def binary(self) -> str:
        if self._binary is None:
            candidates = [
                "piper",
                os.path.join(os.path.dirname(__file__), "..", ".venv", "bin", "piper"),
            ]
            for path in candidates:
                resolved = os.path.expanduser(path)
                if os.path.isfile(resolved) and os.access(resolved, os.X_OK):
                    self._binary = resolved
                    return self._binary
            if _which("piper"):
                self._binary = "piper"
                return "piper"
            self._binary = "piper"
        return self._binary

    async def generate(self, text: str, voice: str | None = None) -> Path:
        """Generate audio from text using Piper TTS."""
        effective_voice = voice or self.voice

        def _synthesize():
            output_path = GENERATION_DIR / f"tts_{id(self)}_{hash(text[:100])}.wav"

            # Try Piper CLI first (handles WAV output natively)
            try:
                result = subprocess.run(
                    [self.binary, "-m", effective_voice, "-f", str(output_path)],
                    input=text,
                    encoding="utf-8",
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                if result.returncode == 0 and output_path.exists():
                    return output_path
                raise RuntimeError(f"Piper CLI failed: {result.stderr.strip()}")
            except FileNotFoundError:
                pass

            # Fallback: use piper_tts Python API directly
            from piper import PiperVoice
            import wave

            voice_obj = PiperVoice.load(effective_voice)
            samples = voice_obj.synthesize(text)
            sample_rate = voice_obj.config.sample_rate

            import numpy as np
            audio_data = np.clip(samples, -1.0, 1.0)
            audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()

            with wave.open(str(output_path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_bytes)

            return output_path

        return await asyncio.get_event_loop().run_in_executor(None, _synthesize)


def _which(cmd: str) -> bool:
    import shutil
    return shutil.which(cmd) is not None


# Module-level instance
engine = PiperEngine()
