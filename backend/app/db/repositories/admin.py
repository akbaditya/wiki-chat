import aiosqlite

USERS_SQL = """
SELECT u.id, u.email, u.created_at, u.last_active_at,
  (SELECT COUNT(*) FROM conversations c WHERE c.user_id = u.id) AS chats,
  (SELECT COUNT(*) FROM messages m JOIN conversations c ON c.id = m.conversation_id
     WHERE c.user_id = u.id) AS messages,
  (SELECT COUNT(*) FROM memories x WHERE x.user_id = u.id) AS memories,
  (SELECT COUNT(*) FROM usage_logs l WHERE l.user_id = u.id AND l.node = 'request') AS requests,
  COALESCE((SELECT SUM(l.tokens_in + l.tokens_out) FROM usage_logs l
            WHERE l.user_id = u.id), 0) AS tokens_total,
  COALESCE((SELECT SUM(l.tokens_in + l.tokens_out) FROM usage_logs l
            WHERE l.user_id = u.id AND l.created_at >= ?), 0) AS tokens_today
FROM users u WHERE u.role = 'user' ORDER BY u.created_at
"""


async def list_users(db: aiosqlite.Connection, today_start: str) -> list[dict]:
    cur = await db.execute(USERS_SQL, (today_start,))
    return [dict(r) for r in await cur.fetchall()]


async def get_user_any_role(db: aiosqlite.Connection, user_id: str) -> dict | None:
    cur = await db.execute("SELECT id, email, role FROM users WHERE id=?", (user_id,))
    row = await cur.fetchone()
    return dict(row) if row else None


async def conversation_ids(db: aiosqlite.Connection, user_id: str) -> list[str]:
    cur = await db.execute("SELECT id FROM conversations WHERE user_id=?", (user_id,))
    return [r["id"] for r in await cur.fetchall()]


async def conversations_summary(db: aiosqlite.Connection, user_id: str) -> list[dict]:
    """Counts only. Titles are deliberately excluded (they come from the user's first message)."""
    cur = await db.execute(
        "SELECT c.id, c.mode, c.created_at, c.updated_at, "
        "(SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS messages "
        "FROM conversations c WHERE c.user_id=? ORDER BY c.updated_at DESC",
        (user_id,),
    )
    return [dict(r) for r in await cur.fetchall()]


async def delete_user(db: aiosqlite.Connection, user_id: str) -> None:
    # ON DELETE CASCADE removes conversations, messages and memories;
    # usage_logs.user_id becomes NULL (history kept, anonymised).
    await db.execute("DELETE FROM users WHERE id=?", (user_id,))


async def conversation_owner(db: aiosqlite.Connection, conv_id: str) -> str | None:
    cur = await db.execute("SELECT user_id FROM conversations WHERE id=?", (conv_id,))
    row = await cur.fetchone()
    return row["user_id"] if row else None


async def delete_conversation(db: aiosqlite.Connection, conv_id: str) -> None:
    await db.execute("DELETE FROM conversations WHERE id=?", (conv_id,))


async def clear_lockouts(db: aiosqlite.Connection) -> int:
    cur = await db.execute("DELETE FROM login_attempts")
    return cur.rowcount