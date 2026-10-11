import math
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import aiosqlite

from app.config import settings
from app.llm.providers import get_providers
from app.llm.streaming import breaker
from app.services.cache import page_cache

# request outcomes: real faults vs. "nothing found on Wikipedia" (not a fault)
SYSTEM_ERRORS = {"internal", "timeout", "llm_unavailable", "llm_rate_limited",
                 "wikipedia_unavailable"}
NO_RESULT = {"no_pages", "low_relevance", "empty_query"}


def classify(status: str) -> str:
    if status == "ok":
        return "ok"
    code = status.split(":", 1)[1] if status.startswith("error:") else status
    if code in SYSTEM_ERRORS:
        return "errors"
    if code in NO_RESULT:
        return "no_result"
    return "other"  # e.g. "busy"


def percentile(sorted_vals: list[int], p: float) -> int | None:
    if not sorted_vals:
        return None
    k = max(0, min(len(sorted_vals) - 1, math.ceil(p / 100 * len(sorted_vals)) - 1))
    return sorted_vals[k]


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def today_start() -> str:
    return f"{_today()}T00:00:00Z"


def _since(days: int) -> str:
    start = datetime.now(timezone.utc).date() - timedelta(days=days - 1)
    return f"{start.isoformat()}T00:00:00Z"


def _day_list(days: int) -> list[str]:
    today = datetime.now(timezone.utc).date()
    return [(today - timedelta(days=i)).isoformat() for i in range(days - 1, -1, -1)]


def _rate(part: int, total: int) -> float:
    return round(part / total, 4) if total else 0.0


async def _one(db: aiosqlite.Connection, sql: str, params: tuple = ()):
    cur = await db.execute(sql, params)
    return await cur.fetchone()


async def _all(db: aiosqlite.Connection, sql: str, params: tuple = ()):
    cur = await db.execute(sql, params)
    return await cur.fetchall()


async def build_overview(db: aiosqlite.Connection) -> dict:
    ts = today_start()
    users = (await _one(db, "SELECT COUNT(*) AS n FROM users WHERE role='user'"))["n"]
    convs = (await _one(db, "SELECT COUNT(*) AS n FROM conversations"))["n"]
    msgs = (await _one(db, "SELECT COUNT(*) AS n FROM messages"))["n"]
    mems = (await _one(db, "SELECT COUNT(*) AS n FROM memories"))["n"]
    tokens = (await _one(
        db, "SELECT COALESCE(SUM(tokens_in + tokens_out), 0) AS n FROM usage_logs "
            "WHERE created_at >= ?", (ts,)))["n"]
    reqs = await _all(
        db, "SELECT status FROM usage_logs WHERE node='request' AND created_at >= ?", (ts,))
    kinds = [classify(r["status"]) for r in reqs]
    guests = (await _one(
        db, "SELECT COALESCE(SUM(count), 0) AS n FROM guest_usage WHERE day = ?", (_today(),)))["n"]
    locked = (await _one(
        db, "SELECT COUNT(*) AS n FROM login_attempts WHERE locked_until > ?", (time.time(),)))["n"]
    return {
        "users": {"count": users, "max": settings.max_users},
        "max_convos_per_user": settings.max_convos_per_user,
        "conversations": convs, "messages": msgs, "memory_facts": mems,
        "today": {
            "tokens": tokens, "requests": len(reqs),
            "errors": kinds.count("errors"), "no_result": kinds.count("no_result"),
            "guest_messages": guests,
        },
        "budgets": {
            "global_daily": settings.global_daily_token_budget,
            "global_used_today": tokens,
            "per_user_daily": settings.user_daily_token_budget,
        },
        "providers": [{"name": p.name, "circuit_open": breaker.is_open(p.name)}
                      for p in get_providers("main")],
        "active_lockouts": locked,
        "page_cache_since_restart": page_cache.stats(),
    }


async def build_metrics(db: aiosqlite.Connection, days: int) -> dict:
    since = _since(days)

    # ---- per-day series -------------------------------------------------
    daily = {d: {"day": d, "requests": 0, "ok": 0, "errors": 0, "no_result": 0,
                 "other": 0, "tokens_in": 0, "tokens_out": 0} for d in _day_list(days)}
    for r in await _all(
        db, "SELECT substr(created_at,1,10) AS day, SUM(tokens_in) AS tin, SUM(tokens_out) AS tout "
            "FROM usage_logs WHERE created_at >= ? GROUP BY day", (since,)):
        if r["day"] in daily:
            daily[r["day"]]["tokens_in"] = r["tin"] or 0
            daily[r["day"]]["tokens_out"] = r["tout"] or 0

    statuses: dict[str, int] = defaultdict(int)
    for r in await _all(
        db, "SELECT substr(created_at,1,10) AS day, status, COUNT(*) AS n FROM usage_logs "
            "WHERE node='request' AND created_at >= ? GROUP BY day, status", (since,)):
        statuses[r["status"]] += r["n"]
        if r["day"] in daily:
            d = daily[r["day"]]
            d["requests"] += r["n"]
            d[classify(r["status"])] += r["n"]
    series = list(daily.values())
    total = sum(d["requests"] for d in series)
    n_ok = sum(d["ok"] for d in series)
    n_err = sum(d["errors"] for d in series)
    n_none = sum(d["no_result"] for d in series)
    active = (await _one(
        db, "SELECT COUNT(DISTINCT user_id) AS n FROM usage_logs WHERE node='request' "
            "AND user_id IS NOT NULL AND created_at >= ?", (since,)))["n"]

    # ---- latency p50/p95 per node (successful runs only) ---------------
    by_node: dict[str, list[int]] = defaultdict(list)
    for r in await _all(
        db, "SELECT node, latency_ms FROM usage_logs WHERE created_at >= ? "
            "AND latency_ms IS NOT NULL AND status='ok' AND node != 'rate_limit' LIMIT 100000",
        (since,)):
        by_node[r["node"]].append(r["latency_ms"])
    latency = []
    for node, vals in sorted(by_node.items()):
        vals.sort()
        latency.append({
            "node": node, "count": len(vals), "avg_ms": round(sum(vals) / len(vals)),
            "p50_ms": percentile(vals, 50), "p95_ms": percentile(vals, 95), "max_ms": vals[-1],
        })

    # ---- tokens by node --------------------------------------------------
    tokens_by_node = [dict(r) for r in await _all(
        db, "SELECT node, COUNT(*) AS calls, SUM(tokens_in) AS tokens_in, "
            "SUM(tokens_out) AS tokens_out FROM usage_logs WHERE created_at >= ? "
            "GROUP BY node HAVING SUM(tokens_in + tokens_out) > 0 "
            "ORDER BY SUM(tokens_in + tokens_out) DESC", (since,))]

    # ---- provider split / fallback rate ----------------------------------
    counts = {r["model"]: r["n"] for r in await _all(
        db, "SELECT model, COUNT(*) AS n FROM usage_logs WHERE node='generate' "
            "AND model IS NOT NULL AND created_at >= ? GROUP BY model", (since,))}
    providers = get_providers("main")
    primary = providers[0].name if providers else None
    answered = sum(counts.values())
    fallback = answered - counts.get(primary, 0) if primary else 0

    # ---- mode split -------------------------------------------------------
    tok_by_mode = {r["mode"]: r["avg_tokens"] for r in await _all(
        db, "SELECT mode, ROUND(AVG(t)) AS avg_tokens FROM ("
            "SELECT COALESCE(MAX(mode), 'normal') AS mode, SUM(tokens_in + tokens_out) AS t "
            "FROM usage_logs WHERE request_id IS NOT NULL AND created_at >= ? "
            "GROUP BY request_id) GROUP BY mode", (since,))}
    modes = [{
        "mode": r["mode"], "requests": r["n"], "avg_latency_ms": r["avg_latency"],
        "avg_tokens_per_request": tok_by_mode.get(r["mode"]),
    } for r in await _all(
        db, "SELECT COALESCE(mode, 'normal') AS mode, COUNT(*) AS n, "
            "CAST(AVG(CASE WHEN status='ok' THEN latency_ms END) AS INTEGER) AS avg_latency "
            "FROM usage_logs WHERE node='request' AND created_at >= ? GROUP BY 1", (since,))]

    # ---- audience, rate limits, cache ------------------------------------
    aud = await _one(
        db, "SELECT COALESCE(SUM(user_id IS NULL), 0) AS guest, "
            "COALESCE(SUM(user_id IS NOT NULL), 0) AS usr FROM usage_logs "
            "WHERE node='request' AND created_at >= ?", (since,))
    rate_limits = {r["status"]: r["n"] for r in await _all(
        db, "SELECT status, COUNT(*) AS n FROM usage_logs WHERE node='rate_limit' "
            "AND created_at >= ? GROUP BY status", (since,))}
    c = await _one(
        db, "SELECT COALESCE(SUM(pages_total), 0) AS pages, COALESCE(SUM(page_hits), 0) AS ph, "
            "COALESCE(SUM(index_hits), 0) AS ih FROM cache_events WHERE created_at >= ?", (since,))

    return {
        "days": days,
        "totals": {
            "requests": total, "ok": n_ok, "errors": n_err, "no_result": n_none,
            "other": total - n_ok - n_err - n_none,
            "error_rate": _rate(n_err, total), "no_result_rate": _rate(n_none, total),
            "tokens_in": sum(d["tokens_in"] for d in series),
            "tokens_out": sum(d["tokens_out"] for d in series),
            "active_users": active,
        },
        "daily": series,
        "request_statuses": dict(statuses),
        "latency": latency,
        "tokens_by_node": tokens_by_node,
        "providers": {"counts": counts, "primary": primary, "fallback_rate": _rate(fallback, answered)},
        "modes": modes,
        "audience": {"guest": aud["guest"], "user": aud["usr"]},
        "rate_limits": rate_limits,
        "cache": {
            "pages_total": c["pages"],
            "page_cache_hit_rate": _rate(c["ph"], c["pages"]),
            "index_cache_hit_rate": _rate(c["ih"], c["pages"]),
        },
    }