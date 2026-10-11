import asyncio

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.db.database import get_db
from app.db.repositories import admin as admin_repo
from app.db.repositories import users as users_repo
from app.deps import client_ip, get_current_user
from app.security.passwords import hmac_hash, verify_password
from app.security.rate_limit import auth_bucket
from app.security.tokens import COOKIE_NAME
from app.services.thread_cleanup import purge_thread

router = APIRouter(tags=["account"])


class DeleteAccountIn(BaseModel):
    password: str = Field(min_length=1, max_length=128)


@router.post("/account/delete", status_code=204)
async def delete_account(
    body: DeleteAccountIn,
    request: Request,
    response: Response,
    user: dict = Depends(get_current_user),
    db: aiosqlite.Connection = Depends(get_db),
):
    if not auth_bucket.allow(client_ip(request)):
        raise HTTPException(429, "Too many requests. Slow down.")
    if user["role"] != "user":
        raise HTTPException(400, "The admin account can't be deleted here")

    row = await users_repo.get_auth_row(db, user["email"])
    ok = False
    if row:
        ok = await asyncio.to_thread(verify_password, row["password_hash"], body.password)
    if not ok:  
        raise HTTPException(403, "Incorrect password")

    conv_ids = await admin_repo.conversation_ids(db, user["id"])
    await admin_repo.delete_user(db, user["id"])  
    for cid in conv_ids:
        await purge_thread(f"{user['id']}:{cid}")  
    await db.execute(
        "DELETE FROM login_attempts WHERE key=?", (f"email:{hmac_hash(user['email'].lower())}",)
    )
    response.delete_cookie(COOKIE_NAME, path="/")