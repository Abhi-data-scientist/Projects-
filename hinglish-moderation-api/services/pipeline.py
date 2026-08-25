"""
Orchestrator — the single function the API route calls.

Order: cache -> NER (gazetteer) -> POS-tagging (fuzzy + clean check) -> Gemini.
Each layer only runs if the previous one didn't resolve the message
(with high or medium confidence, either flagged or confidently clean).
Gemini is the last resort, kept for the genuinely ambiguous slice of traffic.
"""

from services.cache_service import cache
from services.ner_service import detect_with_ner
from services.pos_service import detect_with_pos
from services.gemini_service import detect_with_gemini


def moderate_text(text: str) -> dict:
    cached = cache.get(text)
    if cached:
        result = dict(cached)
        result["source"] = "cache"
        return result

    ner_result = detect_with_ner(text)
    if ner_result["resolved"]:
        result = {k: v for k, v in ner_result.items() if k != "resolved"}
        result["source"] = "ner"
        cache.set(text, result)
        return result

    pos_result = detect_with_pos(text)
    if pos_result["resolved"]:
        result = {k: v for k, v in pos_result.items() if k != "resolved"}
        result["source"] = "pos_tagging"
        cache.set(text, result)
        return result

    gemini_result = detect_with_gemini(text)
    gemini_result["source"] = "gemini_llm"
    cache.set(text, gemini_result)
    return gemini_result
