import asyncio
import os
import subprocess
from pathlib import Path

DEFAULT_VOICE = os.environ.get("TTS_VOICE", "en_US-lessac-medium")
OUTPUT_DIR = Path(os.environ.get("TTS_OUTPUT_DIR", "/app/audio"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR = Path("/app/models")


def _resolve_voice_path(voice: str):
    """Resolve a voice identifier to its HuggingFace path components.

    Piper voices follow the pattern: <locale>_<region>-<speaker>-<quality>
    e.g. en_US-lessac-medium, en_GB-seaver-medium, es_ES-pavoque-low

    Returns (language_code, speaker, quality) or None if unrecognized.
    """
    if voice.endswith(".onnx"):
        voice = Path(voice).stem

    parts = voice.rsplit("-", 2)
    if len(parts) < 3:
        return None

    locale = parts[0]
    quality = parts[-1].lower()
    speaker = parts[-2]

    if quality not in ("low", "medium", "high"):
        return None

    lang_code = locale.split("_")[0].lower()
    return (lang_code, speaker, quality)


def _ensure_voice_files(voice: str):
    """Ensure Piper voice files exist in MODELS_DIR so Piper can find them.

    PiperVoice.load expects:
      - model:  <name>.onnx
      - config: <name>.json   (NOT .onnx.json)

    Piper downloads from HF name them <name>.onnx.json, so we rename.
    """
    voice_name = voice if not voice.endswith(".onnx") else Path(voice).stem
    onnx_path = MODELS_DIR / f"{voice_name}.onnx"
    piper_config_path = MODELS_DIR / f"{voice_name}.json"  # Piper expects .json
    hf_config_path = MODELS_DIR / f"{voice_name}.onnx.json"

    if onnx_path.exists() and piper_config_path.exists():
        return voice_name

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    import urllib.request

    resolved = _resolve_voice_path(voice_name)
    if resolved is None:
        raise FileNotFoundError(f"Cannot determine download path for voice: {voice}")

    lang_code, speaker, quality = resolved
    base = f"https://huggingface.co/rhasspy/piper-voices/resolve/main/{lang_code}/{lang_code}_{speaker}/{quality}/"

    try:
        urllib.request.urlretrieve(base + f"{voice_name}.onnx", str(onnx_path))
        urllib.request.urlretrieve(base + f"{voice_name}.onnx.json", str(hf_config_path))
    except urllib.error.HTTPError as e:
        onnx_path.unlink(missing_ok=True)
        hf_config_path.unlink(missing_ok=True)
        raise FileNotFoundError(
            f"Voice not found on HuggingFace: {voice} (tried {base}{voice_name}.onnx). "
            f"Status: {e.code} {e.reason}. Available voices can be checked at https://huggingface.co/rhasspy/piper-voices"
        )

    # Piper expects <name>.json, not <name>.onnx.json
    if hf_config_path.exists() and not piper_config_path.exists():
        hf_config_path.rename(piper_config_path)

    return voice_name


class PiperEngine:
    def __init__(self, voice: str = DEFAULT_VOICE):
        self.voice = voice
        self._binary = None

    @property
    def binary(self) -> str:
        if self._binary is None:
            candidates = [
                "piper",
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
        """Generate audio from text using Piper TTS. Returns path to WAV file."""
        effective_voice = voice or self.voice

        def _synthesize():
            import hashlib
            filename = f"tts_{hashlib.md5(text[:100].encode()).hexdigest()[:12]}.wav"
            output_path = OUTPUT_DIR / filename

            voice_name = _ensure_voice_files(effective_voice)

            try:
                result = subprocess.run(
                    [self.binary, "-m", voice_name, "-f", str(output_path)],
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

            from piper import PiperVoice
            import wave

            voice_obj = PiperVoice.load(voice_name)
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
