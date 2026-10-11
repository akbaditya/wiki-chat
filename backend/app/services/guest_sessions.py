import time

from app.config import settings


class GuestSessions:
    def __init__(self, max_sessions: int = 2000, max_messages: int = 10):
        self._d: dict[str, tuple[float, list[dict]]] = {}
        self.max_sessions, self.max_messages = max_sessions, max_messages

    def _purge(self) -> None:
        now = time.time()
        for k in [k for k, (exp, _) in self._d.items() if exp < now]:
            del self._d[k]
        if len(self._d) >= self.max_sessions:
            oldest = min(self._d, key=lambda k: self._d[k][0])
            del self._d[oldest]

    def get(self, gid: str) -> list[dict]:
        item = self._d.get(gid)
        if item and item[0] > time.time():
            return list(item[1])
        return []

    def add_turn(self, gid: str, query: str, answer: str) -> None:
        self._purge()
        hist = self.get(gid) + [
            {"role": "human", "content": query}, {"role": "ai", "content": answer}
        ]
        self._d[gid] = (time.time() + settings.guest_session_ttl_seconds,
                        hist[-self.max_messages:])


guest_sessions = GuestSessions()