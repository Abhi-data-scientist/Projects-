"""
Thin wrapper around Gemini (google-genai SDK).
Kept simple: one function to generate text, used by every other
service that needs an LLM call.
"""

import logging
from google import genai

from core.config import settings

logger = logging.getLogger("gemini_service")

_client: genai.Client | None = None


def user_facing_error(error: Exception) -> str:
    """Return a safe, actionable message for known Gemini failures."""
    message = str(error).upper()
    if "PERMISSION_DENIED" in message or " 403" in message:
        return (
            "Gemini access is blocked for the configured Google project. "
            "Please use an API key from a project that has Gemini API access, then restart the server."
        )
    if "API_KEY" in message or "UNAUTHENTICATED" in message or " 401" in message:
        return "The configured Gemini API key is invalid or missing. Please update GEMINI_API_KEY and restart the server."
    if "NOT_FOUND" in message or " 404" in message:
        return "The configured Gemini model is unavailable. Please check GEMINI_MODEL and restart the server."
    if "RESOURCE_EXHAUSTED" in message or " 429" in message:
        return "Gemini is temporarily rate-limited. Please wait a moment and try again."
    return "Gemini could not process the request right now. Please try again."


def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def generate_text(prompt: str, temperature: float = 0.2) -> str:
    """Send a prompt to Gemini and return the plain text response."""
    try:
        client = get_client()
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config={"temperature": temperature},
        )
        return (response.text or "").strip()
    except Exception as e:
        logger.error(f"Gemini call failed: {e}")
        raise


def is_available() -> bool:
    """Cheap check used by /health — just confirms an API key is set."""
    return bool(settings.GEMINI_API_KEY)
