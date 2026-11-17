"""
Security layer — checked BEFORE any LLM call or DB operation.
Simple keyword-based blocking for sensitive requests.
"""

BLOCKED_KEYWORDS = [
    "password",
    "passwords",
    "credential",
    "credentials",
    "api key",
    "api_key",
    "apikey",
    "token",
    "secret",
    ".env",
    "env file",
    "environment variable",
    "internal configuration",
    "internal config",
    "system prompt",
    "database credentials",
    "db password",
    "connection string",
    "private key",
]

BLOCKED_RESPONSE = "I cannot provide sensitive or confidential information."


def is_sensitive_request(text: str) -> bool:
    """Return True if the query text mentions any blocked keyword."""
    if not text:
        return False
    lowered = text.lower()
    return any(keyword in lowered for keyword in BLOCKED_KEYWORDS)


def guard(text: str) -> str | None:
    """
    Run the security check.
    Returns the blocked response string if the query should be blocked,
    otherwise returns None (meaning: safe to proceed).
    """
    if is_sensitive_request(text):
        return BLOCKED_RESPONSE
    return None
