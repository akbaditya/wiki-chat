import uuid

import aiosqlite

from app.config import settings
from app.db.database import immediate_tx


async def list_facts(db: aiosqlite.Connection, user_id: str, limit: int) -> list[str]:
    cur = await db.execute(
        "SELECT fact FROM memories WHERE user_id=? ORDER BY rowid DESC LIMIT ?",
        (user_id, limit),
    )
    return [r["fact"] for r in reversed(await cur.fetchall())]


async def list_for_user(db: aiosqlite.Connection, user_id: str) -> list[dict]:
    cur = await db.execute(
        "SELECT id, fact, created_at FROM memories WHERE user_id=? ORDER BY rowid DESC",
        (user_id,),
    )
    return [dict(r) for r in await cur.fetchall()]


async def add_facts(db: aiosqlite.Connection, user_id: str, facts: list[str]) -> int:
    added = 0
    async with immediate_tx(db):
        cur = await db.execute(
            "SELECT lower(fact) AS f FROM memories WHERE user_id=?", (user_id,)
        )
        existing = {r["f"] for r in await cur.fetchall()}
        for fact in facts:
            key = fact.lower()
            if key in existing:
                continue
            await db.execute(
                "INSERT INTO memories(id, user_id, fact) VALUES (?,?,?)",
                (str(uuid.uuid4()), user_id, fact),
            )
            existing.add(key)
            added += 1
        await db.execute(  # keep only the newest N
            "DELETE FROM memories WHERE user_id=? AND id NOT IN "
            "(SELECT id FROM memories WHERE user_id=? ORDER BY rowid DESC LIMIT ?)",
            (user_id, user_id, settings.max_memories_per_user),
        )
    return added


async def delete_owned(db: aiosqlite.Connection, user_id: str, mem_id: str) -> bool:
    cur = await db.execute(
        "DELETE FROM memories WHERE id=? AND user_id=?", (mem_id, user_id)
    )
    return cur.rowcount > 0


async def delete_all(db: aiosqlite.Connection, user_id: str) -> None:
    await db.execute("DELETE FROM memories WHERE user_id=?", (user_id,))