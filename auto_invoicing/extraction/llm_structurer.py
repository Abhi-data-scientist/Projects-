"""
Raw extracted text -> Gemini -> structured invoice draft JSON.
IMPORTANT: Gemini sirf EXTRACTION ke liye use hota hai. Calculation kabhi LLM se nahi -
woh validation/calculator.py me Python code se hota hai (deterministic + auditable).
"""
import json
import re

from google import genai

from config import GEMINI_API_KEY, GEMINI_MODEL

_client = genai.Client(api_key=GEMINI_API_KEY)

EXTRACTION_PROMPT = """You are a data extraction engine for an invoicing system.
Read the document text below and extract invoice-relevant information.

Return ONLY a valid JSON object, no markdown, no explanation, no code fences.
Use this exact schema:

{{
  "customer_name": string or null,
  "customer_email": string or null,
  "customer_phone": string or null,
  "customer_address": string or null,
  "items": [
    {{"description": string, "quantity": number, "unit_price": number}}
  ],
  "tax_rate_percent": number or null,
  "due_date": string or null,
  "order_reference": string or null
}}

Rules:
- If a field is not present in the text, use null (or empty list for items).
- quantity and unit_price must be numbers, not strings.
- Do not invent data that isn't in the text.

Document text:
---
{document_text}
---
"""


def _strip_code_fences(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```(json)?", "", raw).strip()
    raw = re.sub(r"```$", "", raw).strip()
    return raw


def extract_invoice_data(document_text: str) -> dict:
    prompt = EXTRACTION_PROMPT.format(document_text=document_text[:12000])

    response = _client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )

    raw_text = (response.text or "").strip()
    cleaned = _strip_code_fences(raw_text)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # fallback: text me se pehla {...} block nikalne ki koshish
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise ValueError(f"LLM se valid JSON nahi mila: {raw_text[:300]}")
        data = json.loads(match.group(0))

    # defaults ensure karo taaki downstream code KeyError na de
    data.setdefault("customer_name", None)
    data.setdefault("customer_email", None)
    data.setdefault("customer_phone", None)
    data.setdefault("customer_address", None)
    data.setdefault("items", [])
    data.setdefault("tax_rate_percent", None)
    data.setdefault("due_date", None)
    data.setdefault("order_reference", None)

    return data
