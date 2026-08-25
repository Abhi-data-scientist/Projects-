"""
Layer 1 — NER (gazetteer-based).

We don't need a heavy statistical NER model here: spaCy's EntityRuler
lets us tag every known profanity/slang word as a custom "PROFANITY"
entity via exact (case-insensitive) dictionary matching. This is a
legitimate, standard NER technique (rule/gazetteer-based entity
recognition) and it's near-instant, so it's the first and cheapest
layer in the pipeline.

If nothing here resolves the message, control passes to the POS-tagging
fallback (pos_service.py), which catches spelling variants that this
exact-match layer misses.
"""

import json
from pathlib import Path

import spacy

WORDLIST_PATH = Path(__file__).parent.parent / "data" / "profanity_wordlist.json"


def _load_wordlist() -> dict:
    with open(WORDLIST_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


_wordlist = _load_wordlist()
ALL_PROFANITY = sorted(set(w.lower() for w in _wordlist["hinglish"] + _wordlist["english"]))
SPAM_PATTERNS = [p.lower() for p in _wordlist["spam_patterns"]]

# Blank English pipeline — we only need the tokenizer + EntityRuler here,
# so this stays fast and has no model-download dependency of its own.
_nlp = spacy.blank("en")
_ruler = _nlp.add_pipe("entity_ruler")
_ruler.add_patterns([{"label": "PROFANITY", "pattern": [{"LOWER": word}]} for word in ALL_PROFANITY])


def detect_with_ner(text: str) -> dict:
    doc = _nlp(text)
    profane_spans = [ent.text for ent in doc.ents if ent.label_ == "PROFANITY"]
    lowered = text.lower()
    matched_spam_pattern = next((p for p in SPAM_PATTERNS if p in lowered), None)

    if not profane_spans and not matched_spam_pattern:
        return {"resolved": False}

    cleaned = text
    for span in profane_spans:
        cleaned = cleaned.replace(span, "*" * len(span))

    if profane_spans and matched_spam_pattern:
        category = "spam"
        explanation = (
            f"Matched known term(s) {', '.join(profane_spans)} and a spam pattern "
            f"('{matched_spam_pattern}') via NER."
        )
    elif profane_spans:
        category = "profanity"
        explanation = f"Matched known term(s) via NER: {', '.join(profane_spans)}"
    else:
        category = "spam"
        explanation = f"Matched spam pattern via NER: '{matched_spam_pattern}'"

    return {
        "resolved": True,
        "is_flagged": True,
        "category": category,
        "cleaned_text": cleaned,
        "explanation": explanation,
        "confidence": "high",
    }
