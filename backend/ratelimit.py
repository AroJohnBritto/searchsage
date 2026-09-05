import threading
import time
from collections import deque

from fastapi import Depends, HTTPException, status

from backend.auth import rate_limit_key

GENERIC_RATE_LIMIT_ERROR = "Too many requests. Please slow down and try again shortly."

_lock = threading.Lock()
_buckets: dict[str, deque] = {}


class RateLimiter:
    """Simple in-memory sliding window limiter, keyed by rate_limit_key.

    In-memory is fine for a single-process deployment like this one. It
    resets on restart, which is an acceptable tradeoff for the free-tier
    scope of this project.
    """

    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def __call__(self, key: str = Depends(rate_limit_key)) -> None:
        now = time.monotonic()
        with _lock:
            bucket = _buckets.setdefault(key, deque())
            while bucket and now - bucket[0] > self.window_seconds:
                bucket.popleft()
            if len(bucket) >= self.max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=GENERIC_RATE_LIMIT_ERROR,
                )
            bucket.append(now)


query_rate_limiter = RateLimiter(max_requests=20, window_seconds=60)
