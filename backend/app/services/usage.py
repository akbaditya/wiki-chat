import functools
import logging
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from time import perf_counter

from app.config import settings
from app.db.database import db_session

logger = logging.getLogger(__name__)

# Per-request context (user, request id, mode). Set once in run_chat and inherited
# by graph nodes and background tasks, so we don't pass it through every function.
_ctx: ContextVar[dict] = ContextVar("usage_ctx", default={})


def set_context(**kw) -> None:
    _ctx.set({**kw, "trace": []})   # trace collects this request's usage rows for the details panel


def get_trace() -> list[dict]:
    return list(_ctx.get().get("trace") or [])


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)  # rough fallback when a provider returns no usage


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def seconds_until_midnight_utc() -> int:
    now = datetime.now(timezone.utc)
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return int((tomorrow - now).total_seconds())


class TokenBudget:
    """In-memory daily counters (reset at UTC midnight), seeded from the DB at startup."""

    def __init__(self) -> None:
        self._day = ""
        self._global = 0
        self._users: dict[str, int] = {}

    def _roll(self) -> None:
        today = _today()
        if today != self._day:
            self._day, self._global, self._users = today, 0, {}

    async def load_today(self) -> None:
        self._roll()
        async with db_session() as db:
            cur = await db.execute(
                "SELECT user_id, SUM(tokens_in + tokens_out) AS t FROM usage_logs "
                "WHERE created_at >= ? GROUP BY user_id",
                (self._day + "T00:00:00Z",),
            )
            for r in await cur.fetchall():
                total = int(r["t"] or 0)
                self._global += total
                if r["user_id"]:
                    self._users[r["user_id"]] = total

    def add(self, user_id: str | None, tokens: int) -> None:
        self._roll()
        self._global += tokens
        if user_id:
            self._users[user_id] = self._users.get(user_id, 0) + tokens

    def exceeded(self, user_id: str | None) -> str | None:
        self._roll()
        if self._global >= settings.global_daily_token_budget:
            return "global"
        if user_id and self._users.get(user_id, 0) >= settings.user_daily_token_budget:
            return "user"
        return None

    def user_used(self, user_id: str) -> int:
        self._roll()
        return self._users.get(user_id, 0)


budget = TokenBudget()


async def log_usage(*, node: str, tokens_in: int = 0, tokens_out: int = 0,
                    latency_ms: int | None = None, model: str | None = None,
                    status: str = "ok", user_id: str | None = None,
                    request_id: str | None = None, mode: str | None = None) -> None:
    ctx = _ctx.get()
    uid = user_id or ctx.get("user_id") or None  # None for guests (FK-safe)
    budget.add(uid, tokens_in + tokens_out)
    trace = ctx.get("trace")
    if trace is not None:
        trace.append({"node": node, "tokens_in": tokens_in, "tokens_out": tokens_out,
                      "latency_ms": latency_ms or 0, "model": model, "status": status})
    try:
        async with db_session() as db:
            await db.execute(
                "INSERT INTO usage_logs(user_id, request_id, node, tokens_in, tokens_out, "
                "latency_ms, model, mode, status) VALUES (?,?,?,?,?,?,?,?,?)",
                (uid, request_id or ctx.get("request_id"), node, tokens_in, tokens_out,
                 latency_ms, model, mode or ctx.get("mode"), status),
            )
    except Exception:
        logger.warning("usage log failed", exc_info=True)  # never break a chat over logging


def track(node: str):
    """Decorator for graph nodes: logs latency and outcome to usage_logs."""
    def deco(fn):
        @functools.wraps(fn)
        async def wrapper(state, *a, **kw):
            t, status = perf_counter(), "ok"
            try:
                out = await fn(state, *a, **kw)
                if isinstance(out, dict) and out.get("fail_code"):
                    status = f"error:{out['fail_code']}"
                return out
            except BaseException as e:
                status = "cancelled" if "Cancelled" in type(e).__name__ else "error:exception"
                raise
            finally:
                await log_usage(node=node, latency_ms=int((perf_counter() - t) * 1000),
                                status=status)
        return wrapper
    return deco

async def log_cache(pages_total: int, page_hits: int, index_hits: int) -> None:
    """One row per retrieval, used for the admin cache hit rate."""
    if pages_total <= 0:
        return
    try:
        async with db_session() as db:
            await db.execute(
                "INSERT INTO cache_events(pages_total, page_hits, index_hits) VALUES (?,?,?)",
                (pages_total, page_hits, index_hits),
            )
    except Exception:
        logger.warning("cache log failed", exc_info=True)