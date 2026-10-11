from datetime import datetime, timezone

import aiosqlite
from fastapi import APIRouter, Depends, Request

from app.config import settings
from app.db.database import get_db
from app.deps import client_ip
from app.security.passwords import hmac_hash

router = APIRouter(tags=["meta"])


@router.get("/meta")
async def meta(request: Request, db: aiosqlite.Connection = Depends(get_db)):
    cur = await db.execute("SELECT COUNT(*) AS n FROM users WHERE role='user'")
    users = (await cur.fetchone())["n"]
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cur = await db.execute(
        "SELECT count FROM guest_usage WHERE ip_hash=? AND day=?",
        (hmac_hash(client_ip(request)), day),
    )
    row = await cur.fetchone()
    used = row["count"] if row else 0
    return {
        "max_convos_per_user": settings.max_convos_per_user,
        "guest_message_limit": settings.guest_message_limit,
        "guest_remaining": max(0, settings.guest_message_limit - used),
        "registrations_open": users < settings.max_users,
        "max_message_chars": 1000,
        "max_persona_chars": 500,
    }