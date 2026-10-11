import asyncio

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.config import settings
from app.db.database import get_db
from app.db.repositories import users
from app.deps import client_ip, get_current_user
from app.schemas.auth import LoginIn, SignupIn, UserOut
from app.security import lockout
from app.security.passwords import burn_verify, hash_password, verify_password
from app.security.rate_limit import auth_bucket
from app.security.tokens import COOKIE_NAME, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_cookie(response: Response, user_id: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        create_access_token(user_id),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.jwt_expire_minutes * 60,
        path="/",
    )


@router.post("/signup", response_model=UserOut, status_code=201)
async def signup(
    body: SignupIn,
    request: Request,
    response: Response,
    db: aiosqlite.Connection = Depends(get_db),
):
    if not auth_bucket.allow(client_ip(request)):
        raise HTTPException(429, "Too many requests. Slow down.")
    email = body.email.lower()
    if email == settings.admin_email.lower():
        raise HTTPException(409, "Email already registered")
    pw_hash = await asyncio.to_thread(hash_password, body.password)  
    try:
        user = await users.create_user(db, email, pw_hash)
    except users.RegistrationFull:
        raise HTTPException(403, "Registrations are full. This demo is invite-only.")
    except users.EmailTaken:
        raise HTTPException(409, "Email already registered")
    _set_cookie(response, user["id"])
    return user


@router.post("/login", response_model=UserOut)
async def login(
    body: LoginIn,
    request: Request,
    response: Response,
    db: aiosqlite.Connection = Depends(get_db),
):
    ip = client_ip(request)
    email = body.email.lower()

    if not auth_bucket.allow(ip):
        raise HTTPException(429, "Too many requests. Slow down.")

    remaining = await lockout.seconds_locked(db, email, ip)
    if remaining:
        raise HTTPException(
            429,
            "Too many failed attempts. Try again later.",
            headers={"Retry-After": str(remaining)},
        )

    row = await users.get_auth_row(db, email)
    if row:
        ok = await asyncio.to_thread(verify_password, row["password_hash"], body.password)
    else:
        await asyncio.to_thread(burn_verify, body.password)
        ok = False

    if not ok:
        await lockout.register_failure(db, email, ip)
        raise HTTPException(401, "Invalid email or password")

    await lockout.register_success(db, email)
    await users.touch_last_active(db, row["id"])
    _set_cookie(response, row["id"])
    return {"id": row["id"], "email": row["email"], "role": row["role"]}


@router.post("/logout", status_code=204)
async def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")


@router.get("/me", response_model=UserOut)
async def me(user: dict = Depends(get_current_user)):
    return user