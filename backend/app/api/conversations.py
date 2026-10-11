import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

from app.services.thread_cleanup import purge_thread
from app.config import settings
from app.db.database import get_db
from app.db.repositories import conversations as repo
from app.deps import get_current_user, get_owned_conversation
from app.schemas.conversations import (
    ConversationCreate,
    ConversationOut,
    ConversationUpdate,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationOut])
async def list_conversations(
    user: dict = Depends(get_current_user), db: aiosqlite.Connection = Depends(get_db)
):
    return await repo.list_for_user(db, user["id"])


@router.post("", response_model=ConversationOut, status_code=201)
async def create_conversation(
    body: ConversationCreate,
    user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    try:
        return await repo.create(
            db, user["id"], body.title, body.system_message, body.mode
        )
    except repo.ConversationLimitReached:
        raise HTTPException(
            409,
            f"Chat limit reached ({settings.max_convos_per_user}). Delete one to create a new chat.",
        )


@router.get("/{conv_id}", response_model=ConversationOut)
async def get_conversation(conv: dict = Depends(get_owned_conversation)):
    return conv


@router.patch("/{conv_id}", response_model=ConversationOut)
async def update_conversation(
    body: ConversationUpdate,
    conv: dict = Depends(get_owned_conversation),
    user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    return await repo.update_owned(
        db, conv["id"], user["id"], **body.model_dump(exclude_none=True)
    )


@router.delete("/{conv_id}", status_code=204)
async def delete_conversation(
    conv: dict = Depends(get_owned_conversation),
    user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    await repo.delete_owned(db, conv["id"], user["id"])
    await purge_thread(f"{user['id']}:{conv['id']}")  