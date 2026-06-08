from fastapi import FastAPI
from pydantic_model import ProductRequest
from fetching import fetch_products
from scoring import calculate_score
app = FastAPI()


@app.post("/search")
def search_products(req: ProductRequest):

    data = fetch_products(req.keyword)

    products = []

    for item in data.get("search_results", []):

        price = item.get("price", {}).get("value", 0)

        if not(req.min_price <= price <= req.max_price):
            continue

        product = {
            "title": item.get("title"),
            "price": price,
            "rating": item.get("rating"),
            "reviews": item.get("ratings_total"),
            "asin": item.get("asin"),
            "link": item.get("link")
        }

        product["score"] = calculate_score(item)

        products.append(product)

    products.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    products = products[:req.num_results]

    return {
        "keyword": req.keyword,
        "total_products": len(products),
        "products": products
    }