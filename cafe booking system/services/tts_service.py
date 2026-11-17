"""
Text-to-speech using Piper TTS.
Calls the piper executable directly (simplest possible integration,
no extra python binding library needed).
"""

import logging
import subprocess
import uuid
import os
import shutil
import sys

from core.config import settings

logger = logging.getLogger("tts_service")


def synthesize_speech(text: str) -> str:
    """
    Convert text to a .wav file using Piper.
    Returns the relative path to the generated audio file.
    """
    if not text:
        text = "I don't have a response for that."

    filename = f"{uuid.uuid4().hex}.wav"
    output_path = os.path.join(settings.AUDIO_DIR, filename)

    try:
        executable = shutil.which(settings.PIPER_EXECUTABLE)
        if executable is None:
            candidate = os.path.join(os.path.dirname(sys.executable), "piper.exe")
            executable = candidate if os.path.isfile(candidate) else settings.PIPER_EXECUTABLE

        process = subprocess.run(
            [
                executable,
                "--model", settings.PIPER_MODEL_PATH,
                "--output_file", output_path,
            ],
            input=text.encode("utf-8"),
            capture_output=True,
            check=True,
        )
        if process.returncode != 0:
            logger.error(f"Piper failed: {process.stderr.decode(errors='ignore')}")
            return ""
        return output_path
    except FileNotFoundError:
        logger.error("Piper executable not found. Is it installed and on PATH?")
        return ""
    except subprocess.CalledProcessError as e:
        logger.error(f"Piper TTS failed: {e}")
        return ""
    except OSError as e:
        logger.error(f"Piper TTS could not start: {e}")
        return ""


def is_loaded() -> bool:
    """Simple presence check for the piper model file."""
    return os.path.exists(settings.PIPER_MODEL_PATH)
