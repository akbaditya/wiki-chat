from fastapi import APIRouter, Depends

from app.config import settings
from app.deps import get_current_user
from app.services.usage import budget

router = APIRouter(tags=["usage"])


@router.get("/usage/me")
async def my_usage(user: dict = Depends(get_current_user)):
    used = budget.user_used(user["id"])
    cap = settings.user_daily_token_budget
    return {"tokens_used_today": used, "daily_budget": cap,
            "tokens_remaining": max(0, cap - used)}