from fastapi import HTTPException, Request

from app.deps import client_ip
from app.security.rate_limit import chat_ip_bucket, chat_user_bucket
from app.services.usage import budget, log_usage, seconds_until_midnight_utc


async def enforce_chat_limits(request: Request, user_id: str | None) -> None:
    """Token buckets (burst control) + daily token budgets (cost control).
    Runs BEFORE streaming starts, so failures are normal 429/503 responses."""
    ip = client_ip(request)

    if not chat_ip_bucket.allow(ip):
        await log_usage(node="rate_limit", status="rate_limited:ip", user_id=user_id)
        raise HTTPException(
            429, "You're sending messages too fast. Please wait a few seconds.",
            headers={"Retry-After": str(chat_ip_bucket.retry_after(ip))},
        )
    if user_id and not chat_user_bucket.allow(user_id):
        await log_usage(node="rate_limit", status="rate_limited:user", user_id=user_id)
        raise HTTPException(
            429, "You're sending messages too fast. Please wait a few seconds.",
            headers={"Retry-After": str(chat_user_bucket.retry_after(user_id))},
        )

    which = budget.exceeded(user_id)
    if which:
        await log_usage(node="rate_limit", status=f"budget:{which}", user_id=user_id)
        wait = str(seconds_until_midnight_utc())
        if which == "user":
            raise HTTPException(
                429, "You've used today's token allowance. It resets at midnight UTC.",
                headers={"Retry-After": wait},
            )
        raise HTTPException(
            503, "The demo has reached its daily capacity. Please try again tomorrow.",
            headers={"Retry-After": wait},
        )