import time
from collections import deque
from typing import Deque, Dict


class SlidingWindowLimiter:
    """In-process limiter. Correct for a single instance, which is the supported deployment."""

    def __init__(self) -> None:
        self._hits: Dict[str, Deque[float]] = {}

    def _prune(self, key: str, window: float, now: float) -> Deque[float]:
        q = self._hits.setdefault(key, deque())
        while q and now - q[0] > window:
            q.popleft()
        if not q:
            # keep the dict from growing without bound
            self._hits.pop(key, None)
            q = self._hits.setdefault(key, deque())
        if len(self._hits) > 50_000:
            for stale in [k for k, v in self._hits.items() if not v][:10_000]:
                self._hits.pop(stale, None)
        return q

    def count(self, key: str, window: float) -> int:
        return len(self._prune(key, window, time.monotonic()))

    def allow(self, key: str, limit: int, window: float) -> bool:
        """Record a hit and return False once the limit is exceeded."""
        now = time.monotonic()
        q = self._prune(key, window, now)
        if len(q) >= limit:
            return False
        q.append(now)
        return True

    def record(self, key: str, window: float) -> None:
        now = time.monotonic()
        self._prune(key, window, now).append(now)

    def reset(self, key: str) -> None:
        self._hits.pop(key, None)

    def clear(self) -> None:
        self._hits.clear()


limiter = SlidingWindowLimiter()
