import time
import uuid

import jwt

from app.config import settings

ALGO = "HS256"
COOKIE_NAME = "access_token"


def create_access_token(user_id: str) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + settings.jwt_expire_minutes * 60,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGO)


def decode_access_token(token: str) -> str | None:
    """Returns user_id or None. The token carries NO role; role is always read from DB."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[ALGO],
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError:
        return None
    return payload.get("sub")