import requests
import os
from dotenv import load_dotenv

# .env file load karo
load_dotenv()

# API key read karo
API_KEY = os.getenv("RAINFOREST_API_KEY")


def fetch_products(keyword: str):

    params = {
        "api_key": API_KEY,
        "type": "search",
        "amazon_domain": "amazon.com",
        "search_term": keyword
    }

    response = requests.get(
        "https://api.rainforestapi.com/request",
        params=params
    )

    response.raise_for_status()

    return response.json()