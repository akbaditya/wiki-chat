import asyncio
import logging
import time

from app.config import settings
from app.llm.providers import get_providers
from app.llm.text import chunk_text

logger = logging.getLogger(__name__)


class AllProvidersFailed(Exception):
    def __init__(self, message: str = "", rate_limited: bool = False):
        super().__init__(message)
        self.rate_limited = rate_limited  

class PartialStreamError(Exception): ...


def _is_rate_limit(e: Exception) -> bool:
    s = str(e).lower()
    return any(k in s for k in ("429", "rate limit", "rate_limit", "quota", "resource_exhausted"))


def _is_transient(e: Exception) -> bool:
    name = type(e).__name__.lower()
    return isinstance(e, (TimeoutError, ConnectionError)) or "timeout" in name or "connect" in name


class CircuitBreaker:
    """After `threshold` consecutive failures a provider is skipped for `cooldown` seconds."""

    def __init__(self, threshold: int = 3, cooldown: float = 60.0):
        self.threshold, self.cooldown = threshold, cooldown
        self._fails: dict[str, int] = {}
        self._open_until: dict[str, float] = {}

    def is_open(self, name: str) -> bool:
        return self._open_until.get(name, 0) > time.monotonic()

    def failure(self, name: str) -> None:
        self._fails[name] = self._fails.get(name, 0) + 1
        if self._fails[name] >= self.threshold:
            self._open_until[name] = time.monotonic() + self.cooldown
            self._fails[name] = 0

    def success(self, name: str) -> None:
        self._fails[name] = 0


breaker = CircuitBreaker()


async def stream_llm(messages, kind: str = "main"):
    """Async generator yielding ("token", provider, text) and finally ("done", provider, usage).
    Per provider: one quick retry on timeouts/connection errors, then fall back to the next."""
    providers = get_providers(kind)
    if not providers:
        raise AllProvidersFailed("no LLM provider configured (check API keys in .env)")
    errors: list[str] = []
    rate_flags: list[bool] = []

    for p in providers:
        if breaker.is_open(p.name):
            errors.append(f"{p.name}: circuit open")
            continue
        for attempt in (0, 1):
            got_text, usage = False, None
            try:
                it = p.model.astream(messages).__aiter__()
                async with asyncio.timeout(settings.llm_first_token_timeout):
                    chunk = await anext(it, None)
                while chunk is not None:
                    usage = getattr(chunk, "usage_metadata", None) or usage
                    text = chunk_text(chunk)
                    if text:
                        got_text = True
                        yield ("token", p.name, text)
                    async with asyncio.timeout(settings.llm_chunk_timeout):
                        chunk = await anext(it, None)
                if not got_text:
                    raise RuntimeError("empty response")
                breaker.success(p.name)
                yield ("done", p.name, usage)
                return
            except Exception as e:
                logger.warning("LLM provider %s failed (attempt %d): %r", p.name, attempt + 1, e)
                if got_text: 
                    breaker.failure(p.name)
                    raise PartialStreamError(p.name) from e
                rate = _is_rate_limit(e)
                if attempt == 0 and not rate and _is_transient(e):
                    await asyncio.sleep(0.5)
                    continue 
                breaker.failure(p.name)
                errors.append(f"{p.name}: {type(e).__name__}")
                rate_flags.append(rate)
                break

    raise AllProvidersFailed("; ".join(errors),
                             rate_limited=bool(rate_flags) and all(rate_flags))