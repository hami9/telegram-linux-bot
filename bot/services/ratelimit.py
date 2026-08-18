from __future__ import annotations

import time
from collections import defaultdict, deque


class CooldownLimiter:
    def __init__(self, calls: int = 4, period: int = 60) -> None:
        self.calls = calls
        self.period = period
        self._hits: dict[int, deque[float]] = defaultdict(deque)

    def check(self, key: int) -> int:
        now = time.monotonic()
        hits = self._hits[key]
        while hits and now - hits[0] > self.period:
            hits.popleft()
        if len(hits) >= self.calls:
            return max(1, int(self.period - (now - hits[0])))
        hits.append(now)
        return 0


class FloodTracker:
    def __init__(self, window: int = 12) -> None:
        self.window = window
        self._state: dict[tuple[int, int], tuple[int, float]] = {}

    def hit(self, chat_id: int, user_id: int, limit: int) -> bool:
        if limit <= 0:
            return False
        now = time.monotonic()
        key = (chat_id, user_id)
        count, first_seen = self._state.get(key, (0, now))
        if now - first_seen > self.window:
            count, first_seen = 0, now
        count += 1
        if count >= limit:
            self._state.pop(key, None)
            return True
        self._state[key] = (count, first_seen)
        return False

    def reset(self, chat_id: int, user_id: int) -> None:
        self._state.pop((chat_id, user_id), None)
