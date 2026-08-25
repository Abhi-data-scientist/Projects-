# Hinglish Moderation API

Simple, Docker-free Python/FastAPI service that moderates Hinglish/English
chat messages and masks bad words with `****`.

## Pipeline

Cheapest/fastest layer first, each one only runs if the layer before it
couldn't confidently resolve the message:

```
Cache (in-memory, TTL) --HIT--> return cached result
   |
   MISS
   v
[1] NER (gazetteer-based, spaCy EntityRuler)
   -- exact match against the wordlist -> resolved, high confidence
   |
   unresolved
   v
[2] POS-tagging fallback (spaCy tagger + fuzzy match)
   -- catches spelling variants (e.g. "bakwaas" vs "bakwas")
   -- if nothing found AND every word is a recognized English word
      -> confidently "clean" (never needs Gemini)
   -- if unrecognized Hinglish words remain with no match -> unresolved
   |
   unresolved (genuinely ambiguous / code-mixed / sarcastic)
   v
[3] Gemini LLM (final fallback, authoritative verdict)
```

Every layer's result gets cached, so an identical message never triggers
a second Gemini call.

## What's different from a typical setup

- **No Docker, no Redis.** The cache and the per-user daily rate limiter
  (five free requests per calendar day) are
  both simple in-memory Python (`services/cache_service.py`,
  `services/rate_limiter.py`). Good enough for a single-process
  deployment; swap for Redis later if you run multiple instances.
- **NER layer** = spaCy's `EntityRuler` doing gazetteer (dictionary)
  matching against `data/profanity_wordlist.json` — fast, no model
  download needed for this layer.
- **POS-tagging layer** = spaCy's tagger (`en_core_web_sm`) picks out
  NOUN/ADJ/INTJ/PROPN/VERB tokens and fuzzy-matches them against the
  same wordlist (`difflib`) to catch spelling variants. It also decides
  "confidently clean" using `pyspellchecker`'s offline English
  dictionary — *not* spaCy's `is_oov`, which is unreliable on the small
  model (no word vectors, so it flags almost everything as OOV).
- **Gemini** uses the current `google-genai` SDK.

## Setup (no Docker)

```bash
cd hinglish-moderation-api
python3 -m venv venv
source venv/bin/activate        # venv\Scripts\activate on Windows

pip install -r requirements.txt
python -m spacy download en_core_web_sm

cp .env.example .env            # then fill in GEMINI_API_KEY

uvicorn main:app --reload
```

API is now live at `http://localhost:8000`. Interactive docs at
`http://localhost:8000/docs`.

## Try it

```bash
curl -X POST http://localhost:8000/api/v1/moderate \
  -H "Content-Type: application/json" \
  -d '{"text": "bhai ye bakwas hai", "user_id": "user_1"}'
```

## Run tests

```bash
python -m pytest tests/ -v
```

Tests mock the Gemini call, so no API key or network access is needed
to run them.

## Extending the wordlist

`data/profanity_wordlist.json` ships with a small starter list. Add
more Hinglish/English terms and spam patterns there — no code change
needed, both the NER and POS layers read from it at startup.
