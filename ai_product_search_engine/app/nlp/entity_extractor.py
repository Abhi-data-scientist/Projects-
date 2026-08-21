import re
import spacy
from spacy.matcher import PhraseMatcher

nlp = spacy.load("en_core_web_sm")

# Vocabulary used for custom NER via PhraseMatcher.
# spaCy's pretrained NER doesn't recognize domain terms like "black" as COLOR
# or "formal" as STYLE, so we drive extraction with our own product vocabulary.
COLORS = [
    "black", "white", "brown", "red", "blue", "green",
    "grey", "gray", "yellow", "pink", "beige", "navy",
]
STYLES = [
    "formal", "casual", "sports", "running", "party",
    "ethnic", "waterproof", "lightweight", "slim fit",
]
PRODUCT_TYPES = [
    "shoes", "shirt", "jacket", "jeans", "watch", "bag",
    "t-shirt", "kurta", "sneakers", "sandals",
]
USE_CASES = [
    "office", "running", "party", "casual", "outdoor",
    "wedding", "gym", "travel",
]

matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
matcher.add("COLOR", [nlp.make_doc(c) for c in COLORS])
matcher.add("STYLE", [nlp.make_doc(s) for s in STYLES])
matcher.add("PRODUCT", [nlp.make_doc(p) for p in PRODUCT_TYPES])
matcher.add("USE_CASE", [nlp.make_doc(u) for u in USE_CASES])

# "under 3000" / "under ₹3000" / "below $3000" style phrases
PRICE_PATTERN = re.compile(r"(?:under|below|less than|within)\s*[₹$]?\s*(\d+)", re.IGNORECASE)
# fallback: bare "₹3000"
PRICE_PATTERN_ALT = re.compile(r"[₹$]\s*(\d+)")


def extract_price(text: str):
    match = PRICE_PATTERN.search(text)
    if match:
        return int(match.group(1))
    match = PRICE_PATTERN_ALT.search(text)
    if match:
        return int(match.group(1))
    return None


def extract_entities(raw_query: str) -> dict:
    """
    Runs NER (PhraseMatcher over product vocabulary) + POS tagging (adjective
    extraction) over the raw query and returns structured entities, e.g.:

    {
      "product": "shoes",
      "color": "black",
      "style": ["formal"],
      "use_case": "office",
      "max_price": 3000,
      "attributes": ["comfortable", "black", "formal"]
    }
    """
    doc = nlp(raw_query.lower())
    matches = matcher(doc)

    entities = {"color": None, "style": [], "product": None, "use_case": None}

    for match_id, start, end in matches:
        label = nlp.vocab.strings[match_id]
        span_text = doc[start:end].text

        if label == "COLOR" and not entities["color"]:
            entities["color"] = span_text
        elif label == "STYLE":
            if span_text not in entities["style"]:
                entities["style"].append(span_text)
        elif label == "PRODUCT" and not entities["product"]:
            entities["product"] = span_text
        elif label == "USE_CASE" and not entities["use_case"]:
            entities["use_case"] = span_text

    entities["max_price"] = extract_price(raw_query)

    # POS tagging: adjectives describe product attributes (e.g. "comfortable")
    entities["attributes"] = [token.text for token in doc if token.pos_ == "ADJ"]

    return entities
