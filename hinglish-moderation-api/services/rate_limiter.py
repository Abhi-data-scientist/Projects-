"""
Daily rate limiter, in-memory, keyed by user_id.
No Redis needed — good enough for a single-process deployment.
If you later run multiple instances behind a load balancer, this
would need a shared store (Redis) instead, since each process
would otherwise keep its own counters.
"""

from collections import defaultdict
from datetime import date
from typing import DefaultDict, Tuple

from config import RATE_LIMIT_PER_DAY


class RateLimiter:
    def __init__(self, max_requests: int = 5):
        self.max_requests = max_requests
        self._requests: DefaultDict[Tuple[str, date], int] = defaultdict(int)

    def is_allowed(self, user_id: str) -> bool:
        key = (user_id, date.today())
        if self._requests[key] >= self.max_requests:
            return False
        self._requests[key] += 1
        return True


rate_limiter = RateLimiter(max_requests=RATE_LIMIT_PER_DAY)
