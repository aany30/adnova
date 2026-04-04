from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Any, Optional
from datetime import datetime, timezone

from auth import get_current_user, TokenData
from database import get_db

router = APIRouter(prefix="/activity", tags=["Activity"])


class ActivityLog(BaseModel):
    module: str          # e.g. "business_metrics", "campaign_optimizer"
    action: str          # e.g. "analyze", "submit"
    input_data: dict[str, Any]  # the actual user inputs
    result_summary: Optional[str] = None  # brief AI result snippet


@router.post("/log")
async def log_activity(
    body: ActivityLog,
    token_data: TokenData = Depends(get_current_user),
):
    """
    Log every user input for persona tracking.
    Called automatically whenever a user submits data to any AdNova module.

    Supabase table: user_activity
    Columns: id, user_id, module, action, input_data (jsonb), result_summary, created_at
    """
    db = get_db()
    db.table("user_activity").insert({
        "user_id": token_data.user_id,
        "module": body.module,
        "action": body.action,
        "input_data": body.input_data,
        "result_summary": body.result_summary,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }).execute()
    return {"status": "logged"}


@router.get("/history")
async def get_activity_history(
    token_data: TokenData = Depends(get_current_user),
):
    """Return this user's full activity log for persona insights."""
    db = get_db()
    result = (
        db.table("user_activity")
        .select("*")
        .eq("user_id", token_data.user_id)
        .order("created_at", desc=True)
        .limit(100)
        .execute()
    )
    return {"activity": result.data}
