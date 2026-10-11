from uuid import UUID

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

from app.db.database import get_db
from app.db.repositories import memories as repo
from app.deps import get_current_user, get_owned_conversation
from app.graph.main_graph import get_user_graph

router = APIRouter(tags=["memory"])


@router.get("/memory")
async def list_memory(
    user: dict = Depends(get_current_user), db: aiosqlite.Connection = Depends(get_db)
):
    return await repo.list_for_user(db, user["id"])


@router.delete("/memory/{mem_id}", status_code=204)
async def delete_memory(
    mem_id: UUID,
    user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    if not await repo.delete_owned(db, user["id"], str(mem_id)):
        raise HTTPException(404, "Memory not found")


@router.delete("/memory", status_code=204)
async def clear_memory(
    user: dict = Depends(get_current_user), db: aiosqlite.Connection = Depends(get_db)
):
    await repo.delete_all(db, user["id"])


@router.get("/conversations/{conv_id}/memory")
async def conversation_memory(
    conv: dict = Depends(get_owned_conversation),
    user: dict = Depends(get_current_user),
):
    snap = await get_user_graph().aget_state(
        {"configurable": {"thread_id": f"{user['id']}:{conv['id']}"}}
    )
    v = snap.values or {}
    return {
        "summary": v.get("summary", ""),
        "recent_messages": len(v.get("recent", [])),
        "turn_count": v.get("turn_count", 0),
    }