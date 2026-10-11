from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from app.config import settings

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


async def _connect() -> aiosqlite.Connection:
    db = await aiosqlite.connect(settings.db_path, isolation_level=None)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys=ON")
    await db.execute("PRAGMA busy_timeout=5000")
    return db


async def get_db():
    """FastAPI dependency: one connection per request."""
    db = await _connect()
    try:
        yield db
    finally:
        await db.close()


@asynccontextmanager
async def db_session():
    """For use outside request handlers (startup, background tasks)."""
    db = await _connect()
    try:
        yield db
    finally:
        await db.close()


@asynccontextmanager
async def immediate_tx(db: aiosqlite.Connection):
    """BEGIN IMMEDIATE takes the write lock up front, so count-then-insert checks
    (user cap, conversation cap) can't race."""
    await db.execute("BEGIN IMMEDIATE")
    try:
        yield
        await db.execute("COMMIT")
    except BaseException:
        await db.execute("ROLLBACK")
        raise


async def init_db() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    async with db_session() as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))