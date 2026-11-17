"""Application logging, timing helpers, and shared pipeline exceptions."""
from __future__ import annotations

import asyncio
import logging
import time
from contextlib import contextmanager
from functools import wraps
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Callable, Final, Iterator, TypeVar, cast

from core.config import LOGS_DIR

LOG_FILE: Final[Path] = LOGS_DIR / "voice_assistant.log"
LOGGER_NAME: Final[str] = "voice_assistant"
F = TypeVar("F", bound=Callable[..., Any])


class VoiceAssistantError(Exception):
    """Base class for expected application and voice-pipeline failures."""
    def __init__(self, message: str, *, code: str = "voice_assistant_error") -> None:
        super().__init__(message)
        self.code = code


class ConfigurationError(VoiceAssistantError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="configuration_error")


class TranscriptionError(VoiceAssistantError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="transcription_error")


class ResponseGenerationError(VoiceAssistantError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="response_generation_error")


class SpeechSynthesisError(VoiceAssistantError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="speech_synthesis_error")


def get_logger(name: str = LOGGER_NAME) -> logging.Logger:
    """Return a configured logger that writes to the logs folder."""
    logger_instance = logging.getLogger(name)
    if getattr(logger_instance, "_voice_assistant_configured", False):
        return logger_instance

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    handler.setLevel(logging.INFO)
    logger_instance.setLevel(logging.INFO)
    logger_instance.addHandler(handler)
    logger_instance.propagate = False
    logger_instance._voice_assistant_configured = True  # type: ignore[attr-defined]
    return logger_instance


logger = get_logger()


def track_latency(func: F) -> F:
    """Log explicit start and finish events plus runtime for a function."""
    function_name = func.__qualname__
    if asyncio.iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            started = time.perf_counter()
            status = "success"
            try:
                return await func(*args, **kwargs)
            except asyncio.CancelledError:
                status = "cancelled"
                raise
            except Exception:
                status = "error"
                raise
            finally:
                duration_ms = (time.perf_counter() - started) * 1000
                logger.info(
                    "function_finished name=%s status=%s duration_ms=%.2f",
                    function_name, status, duration_ms,
                )
        return cast(F, async_wrapper)

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        status = "success"
        try:
            return func(*args, **kwargs)
        except Exception:
            status = "error"
            raise
        finally:
            duration_ms = (time.perf_counter() - started) * 1000
            logger.info(
                "function_finished name=%s status=%s duration_ms=%.2f",
                function_name, status, duration_ms,
            )
    return cast(F, wrapper)


@contextmanager
def measure_step(step_name: str) -> Iterator[None]:
    """Log start and finish events plus runtime for a named pipeline step."""
    started = time.perf_counter()
    status = "success"
    try:
        yield
    except BaseException as exc:
        status = "cancelled" if isinstance(exc, asyncio.CancelledError) else "error"
        raise
    finally:
        duration_ms = (time.perf_counter() - started) * 1000
        logger.info(
            "step_finished name=%s status=%s duration_ms=%.2f",
            step_name, status, duration_ms,
        )
