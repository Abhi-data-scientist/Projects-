"""
Layer 2 — POS-tagging fallback.

Runs only when the NER layer found no exact dictionary match. It does
two things with spaCy's POS tagger:

1. Looks at NOUN/ADJ/INTJ/PROPN/VERB tokens (the POS categories that
   usually carry slang/profanity) and fuzzy-matches them against the
   wordlist using difflib, to catch spelling variants NER's exact
   match missed (e.g. "bakwaas" vs "bakwas").

2. If nothing is flagged, decides whether the message can be marked
   confidently CLEAN or is genuinely ambiguous. A message is treated
   as confidently clean when every alphabetic token is a recognized
   dictionary English word. If there are unrecognized alphabetic
   tokens (typically Hindi/Hinglish words in Roman script that
   aren't in our wordlist), we can't be sure — that's exactly the
   code-mixed/sarcastic case that needs the Gemini fallback.

   Note: spaCy's own `token.is_oov` flag is NOT used for this, because
   the small `en_core_web_sm` model ships without word vectors, which
   makes `is_oov` unreliable (it comes back True for almost everything,
   including common English words). Instead we check tokens against
   `pyspellchecker`'s bundled offline English frequency dictionary.
"""

from difflib import get_close_matches

import spacy
from spellchecker import SpellChecker

from config import POS_FUZZY_CUTOFF
from services.ner_service import ALL_PROFANITY

# Needs the tagger, so this is the full small model rather than a blank
# pipeline — disable the pieces we don't use to keep it fast.
_nlp = spacy.load("en_core_web_sm", disable=["ner", "parser", "lemmatizer"])
_spell = SpellChecker()

_SLANG_CARRYING_POS = {"NOUN", "ADJ", "INTJ", "PROPN", "VERB"}


def detect_with_pos(text: str, cutoff: float = POS_FUZZY_CUTOFF) -> dict:
    doc = _nlp(text)
    cleaned_tokens = [t.text_with_ws for t in doc]
    flagged_tokens = []
    has_unrecognized_token = False

    for i, token in enumerate(doc):
        if not token.is_alpha:
            continue

        if token.pos_ in _SLANG_CARRYING_POS:
            match = get_close_matches(token.text.lower(), ALL_PROFANITY, n=1, cutoff=cutoff)
            if match:
                flagged_tokens.append(token.text)
                cleaned_tokens[i] = "*" * len(token.text) + token.whitespace_
                continue

        if len(token.text) > 2 and token.text.lower() not in _spell:
            has_unrecognized_token = True

    if flagged_tokens:
        return {
            "resolved": True,
            "is_flagged": True,
            "category": "profanity",
            "cleaned_text": "".join(cleaned_tokens),
            "explanation": f"Fuzzy POS-based match on: {', '.join(flagged_tokens)}",
            "confidence": "medium",
        }

    if not has_unrecognized_token:
        return {
            "resolved": True,
            "is_flagged": False,
            "category": "clean",
            "cleaned_text": text,
            "explanation": "No profanity found and all tokens are recognized standard English words.",
            "confidence": "high",
        }

    # Alphabetic tokens exist that aren't standard English and don't match
    # the wordlist even fuzzily — genuinely ambiguous, hand off to Gemini.
    return {"resolved": False}
