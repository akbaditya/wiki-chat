import logging
from typing import Annotated
from uuid import UUID

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Query

from app.db.database import get_db
from app.db.repositories import admin as repo
from app.deps import require_admin
from app.security.passwords import hmac_hash
from app.services import admin_metrics
from app.services.thread_cleanup import purge_thread

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/overview")
async def overview(db: aiosqlite.Connection = Depends(get_db)):
    return await admin_metrics.build_overview(db)


@router.get("/users")
async def list_users(db: aiosqlite.Connection = Depends(get_db)):
    return await repo.list_users(db, admin_metrics.today_start())


@router.get("/users/{user_id}/conversations")
async def user_conversations(user_id: UUID, db: aiosqlite.Connection = Depends(get_db)):
    if not await repo.get_user_any_role(db, str(user_id)):
        raise HTTPException(404, "User not found")
    return await repo.conversations_summary(db, str(user_id))


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: UUID,
    admin: dict = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db),
):
    uid = str(user_id)
    user = await repo.get_user_any_role(db, uid)
    if not user:
        raise HTTPException(404, "User not found")
    if user["role"] != "user":
        raise HTTPException(400, "The admin account can't be deleted")

    conv_ids = await repo.conversation_ids(db, uid)
    await repo.delete_user(db, uid)  
    for cid in conv_ids:
        await purge_thread(f"{uid}:{cid}")  
    await db.execute(  
        "DELETE FROM login_attempts WHERE key=?", (f"email:{hmac_hash(user['email'].lower())}",)
    )
    logger.warning("admin %s deleted user %s (%d chats)", admin["email"], uid, len(conv_ids))


@router.delete("/conversations/{conv_id}", status_code=204)
async def delete_conversation(
    conv_id: UUID,
    admin: dict = Depends(require_admin),
    db: aiosqlite.Connection = Depends(get_db),
):
    cid = str(conv_id)
    owner = await repo.conversation_owner(db, cid)
    if not owner:
        raise HTTPException(404, "Conversation not found")
    await repo.delete_conversation(db, cid)
    await purge_thread(f"{owner}:{cid}")
    logger.warning("admin %s deleted conversation %s", admin["email"], cid)


@router.get("/metrics")
async def metrics(
    days: Annotated[int, Query(ge=1, le=90)] = 7,
    db: aiosqlite.Connection = Depends(get_db),
):
    return await admin_metrics.build_metrics(db, days)


@router.post("/security/clear-lockouts")
async def clear_lockouts(
    admin: dict = Depends(require_admin), db: aiosqlite.Connection = Depends(get_db)
):
    n = await repo.clear_lockouts(db)
    logger.warning("admin %s cleared %d lockout records", admin["email"], n)
    return {"cleared": n}