import time

from app.config import settings


class TokenBucket:
    def __init__(self, capacity: float, refill_per_sec: float, max_keys: int = 10_000):
        self.capacity = capacity
        self.refill = refill_per_sec
        self.max_keys = max_keys
        self._state: dict[str, tuple[float, float]] = {}

    def _tokens(self, key: str, now: float) -> float:
        tokens, last = self._state.get(key, (self.capacity, now))
        return min(self.capacity, tokens + (now - last) * self.refill)

    def allow(self, key: str, cost: float = 1.0) -> bool:
        now = time.monotonic()
        if len(self._state) > self.max_keys:
            self._state.clear()  # crude memory guard, fine at this scale
        tokens = self._tokens(key, now)
        if tokens >= cost:
            self._state[key] = (tokens - cost, now)
            return True
        self._state[key] = (tokens, now)
        return False

    def retry_after(self, key: str, cost: float = 1.0) -> int:
        tokens = self._tokens(key, time.monotonic())
        return max(1, int((cost - tokens) / self.refill) + 1)


# 10 auth requests burst per IP, refilling 1 every 6 seconds
auth_bucket = TokenBucket(capacity=10, refill_per_sec=1 / 6)
chat_user_bucket = TokenBucket(settings.chat_bucket_capacity, settings.chat_bucket_refill_per_sec)
chat_ip_bucket = TokenBucket(settings.chat_ip_bucket_capacity, settings.chat_bucket_refill_per_sec)