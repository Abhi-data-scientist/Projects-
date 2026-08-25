"""Local invoice-field extraction using Regex and optional spaCy NER.

This module never needs an API key.  If the spaCy English model is installed it
is used to recognise people/organisations; otherwise the label-based regex
rules still provide a deterministic fallback.
"""
from __future__ import annotations

import re
from typing import Any

try:
    import spacy
except ImportError:  # spaCy is optional at runtime
    spacy = None


_NLP = None
_NLP_ATTEMPTED = False


def _get_ner_model():
    """Load the small English NER model once, when it is available."""
    global _NLP, _NLP_ATTEMPTED
    if _NLP_ATTEMPTED:
        return _NLP
    _NLP_ATTEMPTED = True
    if spacy is None:
        return None
    try:
        _NLP = spacy.load("en_core_web_sm", disable=["tagger", "parser", "lemmatizer"])
    except OSError:
        _NLP = None
    return _NLP


def _clean(value: str | None) -> str | None:
    if not value:
        return None
    value = re.sub(r"\s+", " ", value).strip(" :-,|\t")
    return value or None


def _label_value(text: str, labels: tuple[str, ...]) -> str | None:
    label_pattern = "|".join(re.escape(label) for label in labels)
    match = re.search(rf"(?im)^\s*(?:{label_pattern})\s*[:#-]\s*(.+?)\s*$", text)
    return _clean(match.group(1)) if match else None


def _number(raw: str) -> float:
    return float(raw.replace(",", "").replace("₹", "").replace("$", "").strip())


def _extract_items(text: str) -> list[dict[str, Any]]:
    """Recognise common `description | qty | unit price` invoice rows."""
    items: list[dict[str, Any]] = []
    ignored = re.compile(r"(?i)\b(subtotal|total|tax|gst|vat|discount|amount due|balance)\b")
    patterns = (
        re.compile(
            r"^\s*(?P<description>[A-Za-z][A-Za-z0-9 .&()/_-]{1,80}?)\s*"
            r"(?:\||,|\t)\s*(?P<quantity>\d+(?:\.\d+)?)\s*"
            r"(?:\||,|\t)\s*(?:Rs\.?|INR|USD|\$|₹)?\s*(?P<price>[\d,]+(?:\.\d{1,2})?)\s*$",
            re.IGNORECASE,
        ),
        re.compile(
            r"^\s*(?P<description>[A-Za-z][A-Za-z0-9 .&()/_-]{1,80}?)\s+"
            r"(?P<quantity>\d+(?:\.\d+)?)\s*(?:x|×|@)\s*"
            r"(?:Rs\.?|INR|USD|\$|₹)?\s*(?P<price>[\d,]+(?:\.\d{1,2})?)\s*$",
            re.IGNORECASE,
        ),
    )
    for line in text.splitlines():
        if ignored.search(line):
            continue
        for pattern in patterns:
            match = pattern.match(line)
            if not match:
                continue
            try:
                item = {
                    "description": _clean(match.group("description")),
                    "quantity": _number(match.group("quantity")),
                    "unit_price": _number(match.group("price")),
                }
            except ValueError:
                continue
            if item["description"] and item["quantity"] > 0:
                items.append(item)
            break
    return items


def _ner_customer_name(text: str) -> str | None:
    model = _get_ner_model()
    if not model:
        return None
    # Invoice headers are usually the strongest location for the recipient name.
    for entity in model(text[:2500]).ents:
        if entity.label_ in {"PERSON", "ORG"} and len(entity.text.strip()) > 2:
            return _clean(entity.text)
    return None


def extract_invoice_data_with_nlp(text: str) -> dict[str, Any]:
    """Return the application invoice schema using local Regex + NER."""
    email_match = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text)
    phone_match = re.search(r"(?<!\w)(?:\+?\d{1,3}[ -]?)?(?:\(?\d{2,5}\)?[ -]?)?\d{6,10}(?!\w)", text)
    tax_match = re.search(r"(?i)\b(?:gst|vat|tax)(?:\s*rate)?\s*[:@-]?\s*(\d+(?:\.\d+)?)\s*%", text)
    due_match = re.search(r"(?im)^\s*(?:due\s*date|payment\s*due)\s*[:#-]\s*(.+?)\s*$", text)

    customer_name = _label_value(text, ("bill to", "billed to", "customer", "client", "buyer", "recipient"))
    return {
        "customer_name": customer_name or _ner_customer_name(text),
        "customer_email": email_match.group(0) if email_match else None,
        "customer_phone": _clean(phone_match.group(0)) if phone_match else None,
        "customer_address": _label_value(text, ("address", "billing address", "bill to address")),
        "items": _extract_items(text),
        "tax_rate_percent": _number(tax_match.group(1)) if tax_match else None,
        "due_date": _clean(due_match.group(1)) if due_match else None,
        "order_reference": _label_value(text, ("order reference", "order no", "order number", "po number", "po no", "reference")),
    }


def has_minimum_invoice_data(data: dict[str, Any]) -> bool:
    """Whether local extraction found the fields needed for a usable invoice."""
    return bool(data.get("customer_name") and data.get("items"))
