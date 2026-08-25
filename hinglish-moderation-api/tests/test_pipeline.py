"""
Run with: python -m pytest tests/ -v
(Gemini calls are mocked — no API key or network needed to run these.)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.ner_service import detect_with_ner
from services.pos_service import detect_with_pos
from services.rate_limiter import RateLimiter


def test_ner_catches_known_word():
    result = detect_with_ner("bhai ye bakwas hai")
    assert result["resolved"] is True
    assert result["is_flagged"] is True
    assert "*" * len("bakwas") in result["cleaned_text"]


def test_ner_catches_spam_link():
    result = detect_with_ner("click here http://free-prize.win now!!")
    assert result["resolved"] is True
    assert result["category"] == "spam"


def test_ner_ignores_clean_text():
    result = detect_with_ner("This session was really helpful, thank you!")
    assert result["resolved"] is False


def test_pos_catches_spelling_variant():
    result = detect_with_pos("yaar tu bakwaas bol raha hai")
    assert result["resolved"] is True
    assert result["is_flagged"] is True


def test_pos_marks_plain_english_as_confidently_clean():
    result = detect_with_pos("The teacher explained the concept very clearly today")
    assert result["resolved"] is True
    assert result["is_flagged"] is False
    assert result["category"] == "clean"


def test_pos_leaves_ambiguous_hinglish_unresolved():
    result = detect_with_pos("yaar tu bhi na kabhi kabhi bilkul pagal hai but chill respect")
    assert result["resolved"] is False


def test_rate_limiter_allows_only_five_requests_per_user_per_day():
    limiter = RateLimiter(max_requests=5)

    assert [limiter.is_allowed("same-user") for _ in range(6)] == [True, True, True, True, True, False]
    assert limiter.is_allowed("different-user") is True


def test_pipeline_caches_gemini_result(monkeypatch):
    import services.gemini_service as gemini_service
    import services.pipeline as pipeline

    def fake_gemini(text):
        return {
            "is_flagged": False,
            "category": "other",
            "cleaned_text": text,
            "explanation": "Playful teasing between friends, not abusive.",
            "confidence": "high",
        }

    monkeypatch.setattr(gemini_service, "detect_with_gemini", fake_gemini)
    monkeypatch.setattr(pipeline, "detect_with_gemini", fake_gemini)

    text = "yaar tu bhi na kabhi kabhi bilkul pagal hai but chill respect"
    first = pipeline.moderate_text(text)
    second = pipeline.moderate_text(text)

    assert first["source"] == "gemini_llm"
    assert second["source"] == "cache"
