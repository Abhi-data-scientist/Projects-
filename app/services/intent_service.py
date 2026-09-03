"""
Detects whether a query needs database access (sql) or is a
general knowledge question (general).
"""

# Local routing avoids an unnecessary LLM call for every request. This both
# reduces response time and preserves the free-tier quota for actual answers.
SQL_KEYWORDS = [
    "revenue", "sales", "top selling", "top product", "top customer",
    "top cities", "average order", "profitable category", "orders this week",
    "new customers", "how many orders", "how much revenue", "best selling",
    "total order", "total customer", "monthly sales", "sales trend", "customers",
    "products", "order value", "category", "city", "signup", "purchase",
]


def detect_intent(query: str) -> str:
    """Returns 'sql' or 'general'."""
    lowered = query.lower()

    if any(kw in lowered for kw in SQL_KEYWORDS):
        return "sql"

    return "general"
