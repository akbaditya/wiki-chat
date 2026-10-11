import uuid

import aiosqlite

from app.config import settings
from app.db.database import immediate_tx, now_iso

COLS = "id, title, system_message, mode, created_at, updated_at"
_UPDATABLE = {"title", "system_message", "mode"}


class ConversationLimitReached(Exception): ...


async def list_for_user(db: aiosqlite.Connection, user_id: str) -> list[dict]:
    cur = await db.execute(
        f"SELECT {COLS} FROM conversations WHERE user_id=? ORDER BY updated_at DESC",
        (user_id,),
    )
    return [dict(r) for r in await cur.fetchall()]


async def get_owned(db: aiosqlite.Connection, conv_id: str, user_id: str) -> dict | None:
    cur = await db.execute(
        f"SELECT {COLS} FROM conversations WHERE id=? AND user_id=?", (conv_id, user_id)
    )
    row = await cur.fetchone()
    return dict(row) if row else None


async def create(
    db: aiosqlite.Connection, user_id: str, title: str, system_message: str, mode: str
) -> dict:
    cid = str(uuid.uuid4())
    async with immediate_tx(db):
        cur = await db.execute(
            "SELECT COUNT(*) FROM conversations WHERE user_id=?", (user_id,)
        )
        if (await cur.fetchone())[0] >= settings.max_convos_per_user:
            raise ConversationLimitReached
        await db.execute(
            "INSERT INTO conversations(id, user_id, title, system_message, mode) "
            "VALUES (?,?,?,?,?)",
            (cid, user_id, title, system_message, mode),
        )
    return await get_owned(db, cid, user_id)


async def update_owned(
    db: aiosqlite.Connection, conv_id: str, user_id: str, **fields
) -> dict | None:
    fields = {k: v for k, v in fields.items() if k in _UPDATABLE and v is not None}
    if fields:  # keys come from the whitelist above, so the f-string is safe
        sets = ", ".join(f"{k}=?" for k in fields)
        await db.execute(
            f"UPDATE conversations SET {sets}, updated_at=? WHERE id=? AND user_id=?",
            (*fields.values(), now_iso(), conv_id, user_id),
        )
    return await get_owned(db, conv_id, user_id)


async def delete_owned(db: aiosqlite.Connection, conv_id: str, user_id: str) -> bool:
    cur = await db.execute(
        "DELETE FROM conversations WHERE id=? AND user_id=?", (conv_id, user_id)
    )
    return cur.rowcount > 0