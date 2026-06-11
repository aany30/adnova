from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from auth import decode_token
from config import ADMIN_EMAILS, DAILY_QUERY_LIMIT, LOCAL_ADMIN_ENABLED, MODEL_PROFILES, MONTHLY_QUERY_LIMIT
from services.usage_service import usage_store

router = APIRouter(prefix="/admin", tags=["Admin"])


class AdminConfigUpdate(BaseModel):
    model_profile: str | None = None
    daily_limit: int | None = None
    monthly_limit: int | None = None


async def require_admin(request: Request) -> dict:
    if LOCAL_ADMIN_ENABLED and not ADMIN_EMAILS:
        return {"user_id": "local-admin", "email": "local@adnova.dev"}

    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin token required.")

    token_data = decode_token(auth_header.split(" ", 1)[1])
    email = (token_data.email or "").lower()
    if email and email in ADMIN_EMAILS:
        return {"user_id": token_data.user_id, "email": email}
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")


@router.get("/stats")
async def admin_stats(_: dict = Depends(require_admin)):
    return {
        "status": "success",
        "stats": usage_store.stats(),
        "config": {
            "model_profile": usage_store.model_profile,
            "available_profiles": list(MODEL_PROFILES.keys()),
            "daily_limit": usage_store.daily_limit,
            "monthly_limit": usage_store.monthly_limit,
            "default_daily_limit": DAILY_QUERY_LIMIT,
            "default_monthly_limit": MONTHLY_QUERY_LIMIT,
        },
    }


@router.patch("/config")
async def update_admin_config(body: AdminConfigUpdate, _: dict = Depends(require_admin)):
    if body.model_profile is not None:
        profile = body.model_profile.lower()
        if profile not in MODEL_PROFILES:
            raise HTTPException(status_code=400, detail=f"Unknown model profile: {body.model_profile}")
        usage_store.set_model_profile(profile)
    if body.daily_limit is not None:
        usage_store.daily_limit = max(1, body.daily_limit)
    if body.monthly_limit is not None:
        usage_store.monthly_limit = max(1, body.monthly_limit)
    return {"status": "success", "config": usage_store.stats()}
