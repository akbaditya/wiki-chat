import asyncio
import logging
import sqlite3
import time
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.db.database import db_session
from app.retrieval.vectorstore import store
from app.services.cache import page_cache

logger = logging.getLogger("uvicorn.error")


async def touch_indexed(titles: list[str]) -> None:
    """Marks pages as used just now, so the cleanup keeps the ones people actually read."""
    now = time.time()
    try:
        async with db_session() as db:
            await db.executemany(
                "INSERT INTO indexed_pages(title, last_used) VALUES (?,?) "
                "ON CONFLICT(title) DO UPDATE SET last_used=excluded.last_used",
                [(t, now) for t in titles],
            )
    except Exception:
        logger.warning("could not record page usage", exc_info=True)


async def prune_page_cache() -> dict:
    return await asyncio.to_thread(page_cache.cleanup, settings.cache_max_mb * 1024 * 1024)


async def prune_vector_index() -> dict:
    now = time.time()
    in_index = await store.list_titles()
    async with db_session() as db:
        cur = await db.execute("SELECT title FROM indexed_pages")
        known = {r["title"] for r in await cur.fetchall()}

        for t in in_index - known:
            await db.execute("INSERT INTO indexed_pages(title, last_used) VALUES (?,?)", (t, now))
        for t in known - in_index:
            await db.execute("DELETE FROM indexed_pages WHERE title=?", (t,))

        cur = await db.execute(
            "SELECT title FROM indexed_pages WHERE last_used < ?",
            (now - settings.index_unused_days * 86400,),
        )
        drop = {r["title"] for r in await cur.fetchall()}
        cur = await db.execute( 
            "SELECT title FROM indexed_pages ORDER BY last_used DESC LIMIT -1 OFFSET ?",
            (settings.max_indexed_pages,),
        )
        drop |= {r["title"] for r in await cur.fetchall()}

        for t in drop:
            await store.delete_page(t)
            await db.execute("DELETE FROM indexed_pages WHERE title=?", (t,))
    return {"pages_removed": len(drop), "pages_kept": len(in_index | known) - len(drop)}


async def prune_tables() -> dict:
    utc = datetime.now(timezone.utc)
    logs_cut = (utc - timedelta(days=settings.log_retention_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    day_cut = (utc - timedelta(days=7)).strftime("%Y-%m-%d")
    now = time.time()
    out = {}
    async with db_session() as db:
        for name, sql, params in (
            ("usage_logs", "DELETE FROM usage_logs WHERE created_at < ?", (logs_cut,)),
            ("cache_events", "DELETE FROM cache_events WHERE created_at < ?", (logs_cut,)),
            ("guest_usage", "DELETE FROM guest_usage WHERE day < ?", (day_cut,)),
            ("login_attempts",
             "DELETE FROM login_attempts WHERE locked_until < ? AND updated_at < ?",
             (now, now - 7 * 86400)),
        ):
            cur = await db.execute(sql, params)
            out[name] = cur.rowcount
    return out


def _prune_checkpoints_sync(keep: int = 5) -> int:
    """Keeps the newest `keep` checkpoints of each chat. Checkpoint ids sort by time, and sub-step
    checkpoints share the same clock, so one cut-off id per chat covers them all."""
    if not settings.checkpoint_path.exists():
        return 0
    con = sqlite3.connect(settings.checkpoint_path, timeout=10)
    try:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {"checkpoints", "writes"} <= tables:
            return 0
        cuts = con.execute(
            "SELECT thread_id, checkpoint_id FROM ("
            "  SELECT thread_id, checkpoint_id, ROW_NUMBER() OVER ("
            "    PARTITION BY thread_id ORDER BY checkpoint_id DESC) AS rn"
            "  FROM checkpoints WHERE checkpoint_ns = '') WHERE rn = ?",
            (keep,),
        ).fetchall()
        removed = 0
        for thread_id, cut in cuts:
            con.execute("DELETE FROM writes WHERE thread_id=? AND checkpoint_id < ?", (thread_id, cut))
            cur = con.execute(
                "DELETE FROM checkpoints WHERE thread_id=? AND checkpoint_id < ?", (thread_id, cut)
            )
            removed += cur.rowcount
        con.commit()
        return removed
    finally:
        con.close()


async def prune_checkpoints() -> dict:
    return {"checkpoints_removed": await asyncio.to_thread(_prune_checkpoints_sync)}


async def run_once() -> dict:
    """Each job is independent: one failing never stops the others."""
    out: dict = {}
    for name, job in (
        ("page_cache", prune_page_cache),
        ("vector_index", prune_vector_index),
        ("tables", prune_tables),
        ("checkpoints", prune_checkpoints),
    ):
        try:
            out[name] = await job()
        except Exception:
            logger.exception("maintenance job %s failed", name)
            out[name] = "failed"
    logger.info("maintenance finished: %s", out)
    return out


async def maintenance_loop() -> None:
    await asyncio.sleep(60)  
    while True:
        await run_once()
        await asyncio.sleep(settings.maintenance_interval_hours * 3600)