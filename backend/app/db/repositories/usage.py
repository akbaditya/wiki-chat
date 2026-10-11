from datetime import datetime, timezone

import aiosqlite

from app.db.database import immediate_tx


async def consume_guest_message(db: aiosqlite.Connection, ip_hash: str, limit: int) -> int | None:
    """Counts one guest message for today. Returns messages remaining, or None if over the limit."""
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    async with immediate_tx(db):
        cur = await db.execute(
            "SELECT count FROM guest_usage WHERE ip_hash=? AND day=?", (ip_hash, day)
        )
        row = await cur.fetchone()
        count = row["count"] if row else 0
        if count >= limit:
            return None
        await db.execute(
            "INSERT INTO guest_usage(ip_hash, day, count) VALUES (?,?,1) "
            "ON CONFLICT(ip_hash, day) DO UPDATE SET count = count + 1",
            (ip_hash, day),
        )
    return limit - count - 1