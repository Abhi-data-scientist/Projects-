from pydantic import BaseModel, Field


class ProductRequest(BaseModel):
    keyword: str
    min_price: float
    max_price: float
    num_results: int = Field(10, ge=1, le=50)