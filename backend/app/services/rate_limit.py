

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class SlidingWindowRateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        bucket = self._hits[key]
        cutoff = now - self.window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        return bucket

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            bucket = self._prune(key, now)
            if len(bucket) >= self.max_attempts:
                return False
            bucket.append(now)
            return True

    def remaining(self, key: str) -> int:
        now = time.monotonic()
        with self._lock:
            bucket = self._prune(key, now)
            return max(0, self.max_attempts - len(bucket))

    def reset(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._hits.clear()


_limiter: SlidingWindowRateLimiter | None = None
_limiter_lock = threading.Lock()


def get_rate_limiter() -> SlidingWindowRateLimiter:
    global _limiter
    if _limiter is None:
        from app.core.config import settings

        with _limiter_lock:
            if _limiter is None:
                _limiter = SlidingWindowRateLimiter(
                    max_attempts=settings.LOGIN_RATE_LIMIT_ATTEMPTS,
                    window_seconds=settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS,
                )
    return _limiter


def reset_rate_limiter() -> None:
    
    get_rate_limiter().clear()
