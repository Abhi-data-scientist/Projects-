from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.nlp.preprocessing import preprocess
from app.nlp.entity_extractor import extract_entities
from app.database import fetch_all_products
from app.config import TOP_N_RESULTS


def _text_match(value: str, text: str) -> bool:
    return value is not None and value.lower() in text.lower()


def search_products(raw_query: str) -> dict:
    """
    Full pipeline: NER/POS -> TF-IDF -> cosine similarity -> filtering -> ranking.
    Returns the same shape as the /search API response.
    """
    entities = extract_entities(raw_query)
    processed_query = preprocess(raw_query)

    products = fetch_all_products()
    if not products:
        return {"query": raw_query, "entities": entities, "results": []}

    # Build TF-IDF corpus: query first, then every product's name+description
    corpus = [processed_query] + [
        preprocess(f"{p['name']} {p['description']}") for p in products
    ]

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(corpus)

    query_vector = tfidf_matrix[0:1]
    product_vectors = tfidf_matrix[1:]
    similarities = cosine_similarity(query_vector, product_vectors)[0]

    scored_results = []
    for product, tfidf_score in zip(products, similarities):
        combined_text = f"{product['name']} {product['description']}"

        color_match = 1.0 if _text_match(entities["color"], combined_text) else 0.0

        style_match = 1.0
        if entities["style"]:
            style_match = 1.0 if any(
                _text_match(s, combined_text) for s in entities["style"]
            ) else 0.0

        price_match = 1.0
        if entities["max_price"] is not None:
            price_match = 1.0 if float(product["price"]) <= entities["max_price"] else 0.0

        # Weighted final score: TF-IDF similarity is the primary signal,
        # entity matches (color/style/price) nudge relevant products up.
        final_score = (
            0.6 * tfidf_score
            + 0.15 * color_match
            + 0.15 * style_match
            + 0.10 * price_match
        )

        scored_results.append(
            {
                "product_id": product["product_id"],
                "product": product["name"],
                "price": float(product["price"]),
                "score": round(float(final_score), 4),
                "tfidf_score": round(float(tfidf_score), 4),
            }
        )

    scored_results.sort(key=lambda r: r["score"], reverse=True)

    return {
        "query": raw_query,
        "entities": entities,
        "results": scored_results[:TOP_N_RESULTS],
    }
