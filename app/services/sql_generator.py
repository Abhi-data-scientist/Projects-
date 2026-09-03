"""
Generates SQL from a natural-language question using Groq.
The raw output still has to pass through sql_validator before execution.
"""

import re
from pathlib import Path

from services.groq_service import generate_text

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "sql_prompt.txt"
_PROMPT_TEMPLATE = PROMPT_PATH.read_text(encoding="utf-8")


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```sql", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"^```", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    return text


def generate_sql(query: str) -> str:
    """Ask Groq to produce a raw SQL string for the given question."""
    prompt = _PROMPT_TEMPLATE.format(query=query)
    raw = generate_text(prompt, temperature=0.1)
    return _strip_code_fences(raw)


_SUMMARY_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "summary_prompt.txt"
_SUMMARY_PROMPT_TEMPLATE = _SUMMARY_PROMPT_PATH.read_text(encoding="utf-8")


def summarize_results(query: str, sql: str, results: list[dict]) -> str:
    """Turn raw SQL result rows into a natural-language answer."""
    import json
    trimmed = results[:20]  # keep prompt small even if many rows came back
    prompt = _SUMMARY_PROMPT_TEMPLATE.format(
        query=query,
        sql=sql,
        results=json.dumps(trimmed, default=str),
    )
    return generate_text(prompt, temperature=0.3)
