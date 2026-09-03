"""
Voice-to-text using Faster-Whisper.
Model is loaded once at startup and reused for every request.
"""

import logging
from faster_whisper import WhisperModel

from core.config import settings

logger = logging.getLogger("whisper_service")

_model: WhisperModel | None = None


def load_model() -> WhisperModel:
    global _model
    if _model is None:
        logger.info("Loading Faster-Whisper model...")
        _model = WhisperModel(
            settings.WHISPER_MODEL_SIZE,
            device=settings.WHISPER_DEVICE,
            compute_type=settings.WHISPER_COMPUTE_TYPE,
        )
        logger.info("Faster-Whisper model loaded.")
    return _model


def transcribe_audio(file_path: str) -> str:
    """Transcribe an audio file to plain text."""
    model = load_model()
    segments, _info = model.transcribe(file_path, beam_size=5)
    text = " ".join(segment.text.strip() for segment in segments)
    return text.strip()


def is_loaded() -> bool:
    return _model is not None
