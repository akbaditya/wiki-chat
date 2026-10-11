import time

import aiosqlite

from app.config import settings
from app.db.database import immediate_tx
from app.security.passwords import hmac_hash


def _keys(email: str, ip: str) -> list[tuple[str, int]]:
    return [
        (f"email:{hmac_hash(email.lower())}", settings.login_max_failures),
        (f"ip:{hmac_hash(ip)}", settings.login_max_failures_ip),
    ]


async def seconds_locked(db: aiosqlite.Connection, email: str, ip: str) -> int:
    keys = [k for k, _ in _keys(email, ip)]
    cur = await db.execute(
        "SELECT MAX(locked_until) AS lu FROM login_attempts WHERE key IN (?, ?)", keys
    )
    row = await cur.fetchone()
    return max(0, int((row["lu"] or 0) - time.time()))


async def register_failure(db: aiosqlite.Connection, email: str, ip: str) -> None:
    now = time.time()
    hours = settings.lockout_hours_list
    for key, limit in _keys(email, ip):
        async with immediate_tx(db):
            cur = await db.execute(
                "SELECT fail_count, lock_level, locked_until FROM login_attempts WHERE key=?",
                (key,),
            )
            row = await cur.fetchone()
            fails, level, until = (
                (row["fail_count"], row["lock_level"], row["locked_until"])
                if row
                else (0, 0, 0.0)
            )
            fails += 1
            if fails >= limit:  # lock: 3h, then 12h, then 24h for repeat offenders
                until = now + hours[min(level, len(hours) - 1)] * 3600
                level += 1
                fails = 0
            await db.execute(
                """INSERT INTO login_attempts(key, fail_count, lock_level, locked_until, updated_at)
                   VALUES (?,?,?,?,?)
                   ON CONFLICT(key) DO UPDATE SET
                     fail_count=excluded.fail_count, lock_level=excluded.lock_level,
                     locked_until=excluded.locked_until, updated_at=excluded.updated_at""",
                (key, fails, level, until, now),
            )


async def register_success(db: aiosqlite.Connection, email: str) -> None:
    """Clears only the email counter. The IP counter stays, so one valid
    account can't be used to wipe an attacker's IP failures."""
    await db.execute(
        "DELETE FROM login_attempts WHERE key=?", (f"email:{hmac_hash(email.lower())}",)
    )