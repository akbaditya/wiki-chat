from uuid import UUID

import aiosqlite
from fastapi import Depends, HTTPException, Request

from app.config import settings
from app.db.database import get_db
from app.db.repositories import conversations, users
from app.security.tokens import COOKIE_NAME, decode_access_token


def client_ip(request: Request) -> str:
    if settings.trust_proxy:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def get_current_user(
    request: Request, db: aiosqlite.Connection = Depends(get_db)
) -> dict:
    token = request.cookies.get(COOKIE_NAME)
    user_id = decode_access_token(token) if token else None
    user = await users.get_by_id(db, user_id) if user_id else None
    if not user:
        raise HTTPException(401, "Not authenticated")
    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "admin" or user["email"].lower() != settings.admin_email.lower():
        raise HTTPException(403, "Forbidden")
    return user


async def get_owned_conversation(
    conv_id: UUID,
    user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
) -> dict:
    """IDOR guard: user_id comes from the verified token. If the conversation
    isn't theirs, return 404 (same as not existing)."""
    conv = await conversations.get_owned(db, str(conv_id), user["id"])
    if conv is None:
        raise HTTPException(404, "Conversation not found")
    return conv