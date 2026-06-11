from fastapi import APIRouter, File, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse

from auth import decode_token
from config import DAILY_QUERY_LIMIT, DEFAULT_MODEL_PROFILE, MONTHLY_QUERY_LIMIT
from services.openai_service import analyze_creative_for_targeting, transcribe_video
from services.usage_service import UsageLimitExceeded, usage_store
from services.media_utils import (
    extract_adaptive_video_frames,
    extract_video_storyboard,
    process_uploaded_file,
    encode_image_to_base64
)
from data.facebook_india_targeting import (
    REAL_META_INTERESTS,
    REAL_META_BEHAVIORS,
    CITY_TIERS,
    AGE_CLUSTERS,
    AD_PLACEMENTS
)

router = APIRouter(prefix="/api", tags=["Campaign Optimizer"])
usage_store.configure_limits(DAILY_QUERY_LIMIT, MONTHLY_QUERY_LIMIT)
usage_store.set_model_profile(DEFAULT_MODEL_PROFILE)


def _actor_id_from_request(request: Request) -> str:
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        try:
            token_data = decode_token(auth_header.split(" ", 1)[1])
            if token_data.user_id:
                return f"user:{token_data.user_id}"
        except Exception:
            pass
    forwarded = request.headers.get("x-forwarded-for")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "local")
    return f"session:{ip}"


@router.post("/campaign-optimizer")
async def campaign_optimizer(
    request: Request,
    creative: UploadFile = File(...)
):
    if not creative or not creative.filename:
        raise HTTPException(status_code=400, detail="Creative file is required.")

    actor_id = _actor_id_from_request(request)
    try:
        quota = usage_store.check_limit(actor_id)
    except UsageLimitExceeded as exc:
        return JSONResponse(
            status_code=429,
            content={
                "detail": str(exc),
                "code": "QUERY_LIMIT_EXCEEDED",
                "quota": exc.payload,
            },
        )

    file_bytes = await creative.read()
    content_type = creative.content_type or "image/jpeg"
    is_video = "video" in content_type

    try:
        # ── Step 1: Extract frames ───────────────────────────────
        frame_labels = None
        if is_video:
            adaptive_frames = extract_adaptive_video_frames(file_bytes, min_frames=12, max_frames=16)
            if adaptive_frames:
                frame_bytes_list = [f["bytes"] for f in adaptive_frames]
                frame_labels = [f"Frame at {f['timestamp']:.2f}s" for f in adaptive_frames]
            else:
                print("Adaptive frame extraction failed; falling back to 4-frame storyboard.")
                frame_bytes_list = extract_video_storyboard(file_bytes, num_frames=4)
            if not frame_bytes_list:
                usage_store.record_failure(actor_id, "frame_extraction_failed", {"file_name": creative.filename, "is_video": is_video})
                raise HTTPException(
                    status_code=400,
                    detail="Could not extract frames from video. Try MP4 or MOV format."
                )
        else:
            single = process_uploaded_file(file_bytes, content_type)
            if not single:
                usage_store.record_failure(actor_id, "image_processing_failed", {"file_name": creative.filename, "is_video": is_video})
                raise HTTPException(status_code=400, detail="Could not process image.")
            frame_bytes_list = [single]

        frame_b64_list = [encode_image_to_base64(f) for f in frame_bytes_list]

        # ── Step 2: Transcribe if video ──────────────────────────
        transcript = ""
        if is_video:
            transcript = await transcribe_video(file_bytes, filename=creative.filename or "video.mp4")

        # ── Step 3: AI analysis ──────────────────────────────────
        ai_result = await analyze_creative_for_targeting(
            frame_b64_list=frame_b64_list,
            transcript=transcript,
            is_video=is_video,
            frame_labels=frame_labels
        )
        fallback_used = bool(ai_result.get("fallback_used") or ai_result.get("api_error"))
        usage_store.record_success(actor_id, {
            "file_name": creative.filename,
            "is_video": is_video,
            "frames_analyzed": len(frame_b64_list),
            "fallback_used": fallback_used,
            "model_profile": usage_store.model_profile,
        })

        return JSONResponse({
            "ai_analysis": ai_result,
            "transcript": transcript,
            "is_video": is_video,
            "frames_analyzed": len(frame_b64_list),
            "quota": usage_store.quota_status(actor_id),
            "status": "success"
        })
    except HTTPException:
        raise
    except Exception as exc:
        usage_store.record_failure(actor_id, "analysis_failed", {"file_name": creative.filename, "error": str(exc)})
        raise


@router.get("/targeting-data")
async def get_targeting_data():
    return JSONResponse({
        "interest_categories": REAL_META_INTERESTS,
        "behaviors": REAL_META_BEHAVIORS,
        "city_tiers": CITY_TIERS,
        "age_clusters": AGE_CLUSTERS,
        "ad_placements": AD_PLACEMENTS,
        "status": "success"
    })
