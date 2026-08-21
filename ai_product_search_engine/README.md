# AI Product Search & Intelligence Engine

Single-route NLP-based product search API. No frontend, no separate services —
just `POST /search`.

## Pipeline

```
Query -> Preprocessing -> NER (PhraseMatcher) -> POS Tagging
      -> TF-IDF Vectorization -> Cosine Similarity
      -> Product Filtering -> Product Ranking -> Response
```

## Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   ```

2. **Set up MySQL**
   Run the schema file directly in your MySQL server:
   ```bash
   mysql -u root -p < database/schema.sql
   ```
   This creates the `product_search_db` database, a `products` table, and
   seeds it with sample shoes/jacket/shirt/sandals products.

3. **Configure DB connection**
   Copy `.env.example` to `.env` and adjust if your MySQL user/password
   differ from the defaults (`root` / empty password), or just edit the
   defaults directly in `app/config.py`.

4. **Run the API**
   ```bash
   uvicorn app.main:app --reload
   ```
   Server runs at `http://127.0.0.1:8000`.

## Usage

```bash
curl -X POST http://127.0.0.1:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "I need comfortable black formal shoes for office under 3000"}'
```

Response:
```json
{
  "query": "I need comfortable black formal shoes for office under 3000",
  "entities": {
    "color": "black",
    "style": ["formal"],
    "product": "shoes",
    "use_case": "office",
    "max_price": 3000,
    "attributes": ["comfortable", "black", "formal"]
  },
  "results": [
    {
      "product_id": "P101",
      "product": "Black Leather Formal Shoes",
      "price": 2499.0,
      "score": 0.91,
      "tfidf_score": 0.87
    }
  ]
}
```

## Project structure

```
ai_product_search_engine/
├── app/
│   ├── main.py              # FastAPI app, /search route
│   ├── config.py            # DB config
│   ├── database.py          # Raw SQL (mysql-connector, no ORM)
│   ├── nlp/
│   │   ├── preprocessing.py     # cleaning, lemmatization
│   │   └── entity_extractor.py  # NER (PhraseMatcher) + POS tagging
│   └── search/
│       └── engine.py        # TF-IDF, cosine similarity, filtering, ranking
├── database/
│   └── schema.sql           # run this in your MySQL
├── requirements.txt
├── .env.example
└── README.md
```

## Notes

- NER uses a custom `PhraseMatcher` vocabulary (colors, styles, product
  types, use cases) since spaCy's pretrained NER doesn't recognize domain
  terms like "black" as COLOR out of the box. Extend the lists in
  `app/nlp/entity_extractor.py` as your catalog grows.
- Final ranking score = `0.6 * TF-IDF similarity + 0.15 * color match +
  0.15 * style match + 0.10 * price match`. Adjust weights in
  `app/search/engine.py` if needed.
- `TOP_N_RESULTS` (default 5) controls how many ranked products are returned.
