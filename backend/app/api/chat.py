import json
import logging
import re
import uuid
from time import perf_counter

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Request
from sse_starlette.sse import EventSourceResponse

from app.config import settings
from app.db.database import db_session, get_db
from app.db.repositories import conversations as conv_repo
from app.db.repositories import messages as msg_repo
from app.db.repositories import usage as usage_repo
from app.db.repositories import users as users_repo
from app.deps import client_ip, get_current_user, get_owned_conversation
from app.schemas.chat import ChatIn
from app.security.limits import enforce_chat_limits
from app.security.passwords import hmac_hash
from app.services.chat_runner import run_chat
from app.services.guest_sessions import guest_sessions
from app.services.usage import log_usage

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])

_GUEST_ID = re.compile(r"[0-9a-f]{32}")


def _sse(name: str, data: dict) -> dict:
    return {"event": name, "data": json.dumps(data, ensure_ascii=False)}


async def _event_stream(query, persona, history, finish, done_extra=None,
                        *, user_id=None, conv_id=None, mode="normal"):
    request_id = uuid.uuid4().hex[:12]
    t0 = perf_counter()
    answer, error, images, meta = None, None, [], {}
    async for ev in run_chat(query=query, persona=persona, history=history,
                             user_id=user_id, conv_id=conv_id,
                             request_id=request_id, mode=mode):
        name, data = ev["event"], ev["data"]
        if name == "images":
            images = data["images"]
        elif name == "metadata":
            answer, meta = data["answer"], data
        elif name == "details":
            meta["details"] = data  
        elif name == "error":
            error = data
        yield _sse(name, data)
    try:
        await finish(answer, error, images, meta)
    except Exception:
        logger.exception("failed to persist chat turn")
    await log_usage(  
        node="request", latency_ms=int((perf_counter() - t0) * 1000),
        status=f"error:{error['code']}" if error else "ok",
        user_id=user_id, request_id=request_id, mode=mode,
    )
    yield _sse("done", {"request_id": request_id, **(done_extra or {})})


@router.post("/conversations/{conv_id}/stream")
async def stream_user_chat(
    body: ChatIn,
    request: Request,
    conv: dict = Depends(get_owned_conversation),   # IDOR guard
    user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    await enforce_chat_limits(request, user["id"])
    await users_repo.touch_last_active(db, user["id"])

    async def finish(answer, error, images, meta):
        if error and error["code"] == "busy":  
            return
        async with db_session() as s:
            await msg_repo.add(s, conv["id"], "human", body.message)
            if answer:
                await msg_repo.add(s, conv["id"], "ai", answer, {
                    "sources": meta.get("sources"), "images": images,
                    "provider": meta.get("provider"), "usage": meta.get("usage"),
                    "mode": meta.get("mode"), "details": meta.get("details"),
                })
            elif error:
                await msg_repo.add(s, conv["id"], "ai", error["message"],
                                   {"failed": error["code"], "details": meta.get("details")})
            if conv["title"] == "New chat":
                await conv_repo.update_owned(
                    s, conv["id"], user["id"], title=body.message[:40]
                )

    gen = _event_stream(body.message, conv["system_message"], None, finish,
                        user_id=user["id"], conv_id=conv["id"], mode=conv["mode"])
    return EventSourceResponse(gen)


@router.get("/conversations/{conv_id}/messages")
async def get_messages(
    conv: dict = Depends(get_owned_conversation),
    db: aiosqlite.Connection = Depends(get_db),
):
    return await msg_repo.list_all(db, conv["id"])


@router.post("/chat/guest/stream")
async def stream_guest_chat(
    body: ChatIn, request: Request, db: aiosqlite.Connection = Depends(get_db)
):
    await enforce_chat_limits(request, None)  
    remaining = await usage_repo.consume_guest_message(
        db, hmac_hash(client_ip(request)), settings.guest_message_limit
    )
    if remaining is None:
        raise HTTPException(
            429, f"Guest limit reached ({settings.guest_message_limit} messages). "
                 "Sign up to keep chatting."
        )

    gid = request.cookies.get("guest_id", "")
    if not _GUEST_ID.fullmatch(gid):
        gid = uuid.uuid4().hex
    history = guest_sessions.get(gid)

    async def finish(answer, error, images, meta):
        if answer:
            guest_sessions.add_turn(gid, body.message, answer)

    gen = _event_stream(body.message, body.system_message or "", history, finish,
                        {"guest_remaining": remaining})
    resp = EventSourceResponse(gen)
    resp.set_cookie("guest_id", gid, httponly=True, samesite="lax",
                    secure=settings.cookie_secure,
                    max_age=settings.guest_session_ttl_seconds)
    return resp