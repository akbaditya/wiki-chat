import json
import uuid

import aiosqlite

from app.db.database import now_iso


async def add(db: aiosqlite.Connection, conv_id: str, role: str, content: str,
              meta: dict | None = None) -> None:
    await db.execute(
        "INSERT INTO messages(id, conversation_id, role, content, meta) VALUES (?,?,?,?,?)",
        (str(uuid.uuid4()), conv_id, role, content, json.dumps(meta) if meta else None),
    )
    await db.execute(
        "UPDATE conversations SET updated_at=? WHERE id=?", (now_iso(), conv_id)
    )


def _row(r) -> dict:
    d = dict(r)
    d["meta"] = json.loads(d["meta"]) if d.get("meta") else None
    return d


async def recent(db: aiosqlite.Connection, conv_id: str, limit: int) -> list[dict]:
    cur = await db.execute(
        "SELECT role, content FROM messages WHERE conversation_id=? "
        "ORDER BY rowid DESC LIMIT ?", (conv_id, limit),
    )
    return [dict(r) for r in reversed(await cur.fetchall())]


async def list_all(db: aiosqlite.Connection, conv_id: str, limit: int = 500) -> list[dict]:
    cur = await db.execute(
        "SELECT id, role, content, meta, created_at FROM messages "
        "WHERE conversation_id=? ORDER BY rowid ASC LIMIT ?", (conv_id, limit),
    )
    return [_row(r) for r in await cur.fetchall()]