"""
In-memory cache, keyed by a hash of the normalized message text.
Stands in for Redis so the project runs with zero external services.
Swap this out for a real Redis-backed cache later if you need it
shared across multiple processes/instances — the get/set interface
below is deliberately the only thing pipeline.py depends on.
"""

import hashlib
import time
from typing import Optional, Dict, Tuple

from config import CACHE_TTL_SECONDS


class InMemoryCache:
    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds
        self._store: Dict[str, Tuple[dict, float]] = {}

    @staticmethod
    def _normalize_key(text: str) -> str:
        normalized = text.strip().lower()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def get(self, text: str) -> Optional[dict]:
        key = self._normalize_key(text)
        entry = self._store.get(key)
        if not entry:
            return None
        value, expiry = entry
        if time.time() > expiry:
            del self._store[key]
            return None
        return value

    def set(self, text: str, value: dict) -> None:
        key = self._normalize_key(text)
        self._store[key] = (value, time.time() + self.ttl_seconds)


cache = InMemoryCache(ttl_seconds=CACHE_TTL_SECONDS)
