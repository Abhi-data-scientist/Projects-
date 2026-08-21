from fastapi import FastAPI
from pydantic import BaseModel

from app.search.engine import search_products

app = FastAPI(title="AI Product Search & Intelligence Engine")


class SearchRequest(BaseModel):
    query: str


@app.post("/search")
def search(request: SearchRequest):
    """
    Single route: takes a natural-language product query and returns
    NER-extracted entities plus a ranked list of matching products.
    """
    return search_products(request.query)
