import re
import spacy

nlp = spacy.load("en_core_web_sm")


def clean_text(text: str) -> str:
    """Lowercase, strip currency symbols/punctuation, collapse whitespace."""
    text = text.lower()
    text = re.sub(r"[₹$,]", " ", text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def preprocess(text: str) -> str:
    """
    Full preprocessing pipeline: clean -> tokenize -> remove stopwords -> lemmatize.
    Returns a single space-joined string ready for TF-IDF vectorization.
    """
    cleaned = clean_text(text)
    doc = nlp(cleaned)
    tokens = [
        token.lemma_
        for token in doc
        if not token.is_stop and not token.is_space and token.text.strip()
    ]
    return " ".join(tokens)
