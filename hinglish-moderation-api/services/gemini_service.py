"""
Layer 3 — Gemini LLM fallback (final layer).

Only reached when both the NER layer and the POS-tagging layer were
inconclusive: no known bad word, but also not confidently clean
(code-mixed, sarcastic, or genuinely unclear text). Gemini's verdict
is treated as authoritative once it runs.

Uses the `google-genai` SDK (the current SDK — `google-generativeai`
is deprecated).
"""

import json

from google import genai

from config import GEMINI_API_KEY, GEMINI_MODEL

# Built lazily on first real use, not at import time. Most traffic never
# reaches this layer, so the app shouldn't fail to start just because
# GEMINI_API_KEY is missing/unset in an environment that never needs it.
_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client

SYSTEM_PROMPT = """You are a moderation classifier for Hinglish and English chat/review messages.

Given a single message, decide if it should be flagged, and return ONLY a strict JSON object
with exactly these keys, no markdown fences, no extra text:

{
  "is_flagged": true or false,
  "category": one of "clean", "profanity", "spam", "harassment", "other",
  "cleaned_text": the message with any profane/abusive word masked using asterisks
                  matching that word's length (e.g. "bakwas" -> "******"),
  "explanation": one short sentence explaining the decision
}

If the message is clean, cleaned_text should be identical to the original message.
"""


def detect_with_gemini(text: str) -> dict:
    prompt = f"{SYSTEM_PROMPT}\n\nMessage: \"{text}\""

    response = _get_client().models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )

    raw = (response.text or "").strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(raw)
        required_keys = {"is_flagged", "category", "cleaned_text", "explanation"}
        if not required_keys.issubset(parsed.keys()):
            raise ValueError("Gemini response missing required keys")
    except (json.JSONDecodeError, ValueError):
        parsed = {
            "is_flagged": False,
            "category": "other",
            "cleaned_text": text,
            "explanation": "Gemini response could not be parsed; defaulted to unflagged for safety.",
        }

    parsed["confidence"] = "high"
    return parsed
