import sqlite3
import uuid

import aiosqlite

from app.config import settings
from app.db.database import immediate_tx, now_iso

PUBLIC_COLS = "id, email, role, created_at, last_active_at"


class RegistrationFull(Exception): ...
class EmailTaken(Exception): ...


async def get_by_id(db: aiosqlite.Connection, user_id: str) -> dict | None:
    cur = await db.execute(f"SELECT {PUBLIC_COLS} FROM users WHERE id=?", (user_id,))
    row = await cur.fetchone()
    return dict(row) if row else None


async def get_auth_row(db: aiosqlite.Connection, email: str) -> dict | None:
    cur = await db.execute(
        "SELECT id, email, role, password_hash FROM users WHERE email=?", (email,)
    )
    row = await cur.fetchone()
    return dict(row) if row else None


async def create_user(db: aiosqlite.Connection, email: str, password_hash: str) -> dict:
    uid = str(uuid.uuid4())
    async with immediate_tx(db):
        cur = await db.execute("SELECT COUNT(*) FROM users WHERE role='user'")
        if (await cur.fetchone())[0] >= settings.max_users:
            raise RegistrationFull
        try:
            await db.execute(
                "INSERT INTO users(id, email, password_hash, role, last_active_at) "
                "VALUES (?,?,?, 'user', ?)",
                (uid, email, password_hash, now_iso()),
            )
        except sqlite3.IntegrityError:
            raise EmailTaken
    return await get_by_id(db, uid)


async def ensure_admin(db: aiosqlite.Connection) -> None:
    """Admin comes from .env, never from public signup. Not counted in MAX_USERS."""
    email = settings.admin_email.lower()
    async with immediate_tx(db):
        cur = await db.execute("SELECT id FROM users WHERE email=?", (email,))
        row = await cur.fetchone()
        if row:
            await db.execute(
                "UPDATE users SET role='admin', password_hash=? WHERE id=?",
                (settings.admin_password_hash, row["id"]),
            )
        else:
            await db.execute(
                "INSERT INTO users(id, email, password_hash, role) VALUES (?,?,?, 'admin')",
                (str(uuid.uuid4()), email, settings.admin_password_hash),
            )


async def touch_last_active(db: aiosqlite.Connection, user_id: str) -> None:
    await db.execute(
        "UPDATE users SET last_active_at=? WHERE id=?", (now_iso(), user_id)
    )