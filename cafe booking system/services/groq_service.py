"""Small Groq chat-completions wrapper used by all LLM features."""

import logging

from groq import Groq

from core.config import settings

logger = logging.getLogger("groq_service")

_client: Groq | None = None


def get_client() -> Groq:
    global _client
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured.")
    if _client is None:
        _client = Groq(api_key=settings.GROQ_API_KEY)
    return _client


def generate_text(prompt: str, temperature: float = 0.2) -> str:
    """Send a prompt to Groq and return the plain-text assistant response."""
    try:
        completion = get_client().chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return (completion.choices[0].message.content or "").strip()
    except Exception as error:
        logger.error("Groq call failed: %s", error)
        raise


def is_available() -> bool:
    """Cheap readiness check that does not consume quota."""
    return bool(settings.GROQ_API_KEY)


def user_facing_error(error: Exception) -> str:
    message = str(error).upper()
    if "GROQ_API_KEY" in message or "UNAUTHORIZED" in message or " 401" in message:
        return "The configured Groq API key is invalid or missing. Please update GROQ_API_KEY and restart the server."
    if " 429" in message or "RATE_LIMIT" in message or "RATE LIMIT" in message:
        return "Groq is temporarily rate-limited. Please wait a moment and try again."
    if "NOT_FOUND" in message or " 404" in message:
        return "The configured Groq model is unavailable. Please check GROQ_MODEL and restart the server."
    return "Groq could not process the request right now. Please try again."
