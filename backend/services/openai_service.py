import os
import io
import json
import re
from typing import Any, Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv
from config import MODEL_PROFILES
from data.facebook_india_targeting import (
    get_all_behaviors_flat,
    get_all_interests_flat,
    get_targeting_context_string,
)
from services.usage_service import usage_store

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
client = AsyncOpenAI(api_key=api_key) if api_key else None

TARGETING_CONTEXT = get_targeting_context_string()
REAL_INTEREST_SET = {item.lower(): item for item in get_all_interests_flat()}
REAL_BEHAVIOR_SET = {item.lower(): item for item in get_all_behaviors_flat()}


def _active_model_profile():
    return MODEL_PROFILES.get(usage_store.model_profile, MODEL_PROFILES["balanced"])


def _attach_runtime_metadata(result: dict, model: str, fallback_used: bool = False) -> dict:
    result["model_profile"] = usage_store.model_profile
    result["model_used"] = model
    result["fallback_used"] = fallback_used
    return result


def _as_dict(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list:
    if isinstance(value, list):
        return [item for item in value if item not in (None, "")]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _as_str(value: Any, fallback: str = "—") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def _clamp_int(value: Any, low: int, high: int, fallback: int = 0) -> int:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        number = fallback
    return max(low, min(high, number))


def _score_reason(value: Any, fallback_reason: str = "No reasoning returned.") -> dict:
    value = _as_dict(value)
    return {
        "score": _clamp_int(value.get("score"), 0, 10, 0),
        "reasoning": _as_str(value.get("reasoning"), fallback_reason),
    }


def _confidence_from_text(text: str) -> int:
    lowered = text.lower()
    if any(marker in lowered for marker in ("frame at", "transcript", "visible", "shown", "says", "logo", "cta")):
        return 82
    if text and text != "—":
        return 68
    return 45


def _catalog_match(name: str, catalog: dict[str, str]) -> tuple[str, bool]:
    key = name.strip().lower()
    if key in catalog:
        return catalog[key], True
    return name.strip(), False


def _recommendation_item(
    name: Any,
    evidence: str,
    catalog: Optional[dict[str, str]] = None,
    confidence: Optional[int] = None,
) -> dict:
    raw_name = _as_str(name, "—")
    matched_name, catalog_match = _catalog_match(raw_name, catalog or {})
    return {
        "name": matched_name,
        "confidence": _clamp_int(confidence, 0, 100, _confidence_from_text(evidence) if catalog_match else 58),
        "evidence": _as_str(evidence, "Strategic recommendation inferred from the available creative evidence."),
        "catalog_match": catalog_match,
    }


def _normalize_recommendation_list(
    values: Any,
    evidence: str,
    catalog: Optional[dict[str, str]] = None,
    limit: int = 12,
) -> list[dict]:
    normalized = []
    for item in _as_list(values)[:limit]:
        if isinstance(item, dict):
            normalized.append(
                _recommendation_item(
                    item.get("name") or item.get("recommendation") or item.get("value"),
                    item.get("evidence") or evidence,
                    catalog,
                    item.get("confidence"),
                )
            )
        else:
            normalized.append(_recommendation_item(item, evidence, catalog))
    return normalized


def _normalize_test_angles(values: Any, fallback_interests: list[str], fallback_behaviors: list[str]) -> list[dict]:
    tests = []
    for index, item in enumerate(_as_list(values)[:3]):
        item = _as_dict(item)
        tests.append({
            "name": _as_str(item.get("name"), f"Audience Test {index + 1}"),
            "audience": _as_str(item.get("audience") or item.get("setup"), "Use the recommended buyer persona and priority cities."),
            "interests": _as_list(item.get("interests"))[:5] or fallback_interests[:5],
            "behaviors": _as_list(item.get("behaviors"))[:3] or fallback_behaviors[:3],
            "exclusions": _as_list(item.get("exclusions"))[:4],
            "why_test": _as_str(item.get("why_test") or item.get("hypothesis"), "Validates whether this audience responds to the creative's core promise."),
            "evidence": _as_str(item.get("evidence"), "Built from the targeting rationale and observed creative cues."),
            "confidence": _clamp_int(item.get("confidence"), 0, 100, 70),
        })
    return tests


def _extract_json(text: str) -> dict:
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return {}

async def transcribe_video(video_bytes: bytes, filename: str = "video.mp4") -> str:
    """
    Transcribe audio from a video file using OpenAI Whisper.
    Extracts a small audio track first for efficiency.
    """
    from services.media_utils import extract_audio
    
    video_size_mb = len(video_bytes) / (1024 * 1024)
    
    # Use audio extraction ONLY for large videos (> 20MB) to stay safe & fast
    if video_size_mb > 20.0:
        print(f"Large video detected ({video_size_mb:.1f}MB). Extracting audio for Whisper efficiency.")
        audio_bytes = extract_audio(video_bytes)
        if audio_bytes:
            audio_to_send = audio_bytes
            ext = "mp3"
        else:
            print("Audio extraction failed, falling back to full video.")
            audio_to_send = video_bytes
            ext = "mp4"
    else:
        # Small video: send the whole thing as originally intended
        audio_to_send = video_bytes
        ext = "mp4"

    try:
        profile = _active_model_profile()
        file_tuple = (filename.replace(".mp4", f".{ext}"), io.BytesIO(audio_to_send), f"video/{ext}" if ext == "mp4" else "audio/mp3")
        response = await client.audio.transcriptions.create(
            model=profile.transcription_model,
            file=file_tuple,
            language="hi",          # Hint Hindi first (handles Hinglish well)
            response_format="text",
            timeout=profile.timeout_seconds
        )
        return str(response).strip()
    except Exception as e:
        print(f"Whisper transcription error: {e}")
        return ""



def _build_vision_messages(
    frame_b64_list: list[str],
    user_prompt: str,
    system_prompt: str = "",
    frame_labels: Optional[list[str]] = None
) -> list:
    """Build multi-image message for GPT-4o storyboard analysis with optional system persona."""
    messages = []
    
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    content = []
    if len(frame_b64_list) == 1:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{frame_b64_list[0]}", "detail": "high"}
        })
    else:
        # Multiple frames — label each as part of a storyboard
        fallback_labels = ["Opening frame (0-5%)", "Early frame (25%)", "Mid frame (50%)", "Late frame (75%)"]
        for i, b64 in enumerate(frame_b64_list):
            if frame_labels and i < len(frame_labels):
                label = frame_labels[i]
            else:
                label = fallback_labels[i] if i < len(fallback_labels) else f"Frame {i+1}"
            content.append({"type": "text", "text": f"[{label}]"})
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "high"}
            })

    content.append({"type": "text", "text": user_prompt})
    messages.append({"role": "user", "content": content})
    return messages


def _normalize_creative_analysis(result: dict, is_video: bool = False) -> dict:
    """Validate and repair the model response so the UI always receives a stable contract."""
    if not isinstance(result, dict) or not result:
        return _parse_error_response()

    if result.get("api_error") or result.get("parse_error"):
        return result

    targeting = _as_dict(result.get("targeting"))
    agent_analysis = _as_dict(result.get("agent_analysis"))
    evidence = _as_dict(agent_analysis.get("evidence_synthesizer"))
    meta_agent = _as_dict(agent_analysis.get("meta_targeting_agent"))
    hook_agent = _as_dict(agent_analysis.get("hook_agent"))
    virality_agent = _as_dict(agent_analysis.get("virality_agent"))
    copy_agent = _as_dict(agent_analysis.get("caption_copy_agent"))
    diagnosis_agent = _as_dict(agent_analysis.get("creative_diagnosis_agent"))

    detected_product = _as_str(result.get("detected_product"), "Unspecified ad creative")
    creative_meaning = _as_str(
        result.get("creative_meaning_analysis"),
        "The creative communicates a product or service promise, but the model did not return a detailed meaning analysis.",
    )
    targeting_rationale = _as_str(
        targeting.get("targeting_rationale") or meta_agent.get("reasoning") or targeting.get("interest_reasoning"),
        "Targeting is inferred from visible product cues, transcript context, and standard India D2C buyer behavior.",
    )
    timeline = _as_list(evidence.get("observed_timeline"))
    product_cues = _as_list(evidence.get("product_cues"))
    cta_cues = _as_list(evidence.get("cta_cues"))
    missing_evidence = _as_list(evidence.get("missing_evidence"))
    unsupported_assumptions = _as_list(result.get("unsupported_assumptions") or evidence.get("unsupported_assumptions"))

    if not timeline:
        timeline = [{
            "timestamp": "Image" if not is_video else "Storyboard",
            "observation": creative_meaning,
            "marketing_signal": targeting_rationale,
        }]

    if not product_cues:
        product_cues = [detected_product]
    if not cta_cues:
        cta_cues = ["CTA or offer clarity should be verified from the creative before scaling."]
    if not missing_evidence:
        missing_evidence = ["Price, offer strength, landing page continuity, and proof signals may need manual verification."]
    if not unsupported_assumptions:
        unsupported_assumptions = [
            "Exact audience size, CPC, CPM, and conversion rate cannot be known from the creative alone.",
            "Catalog availability can vary inside the live Meta Ads Manager account.",
        ]

    top_interests = _as_list(targeting.get("top_interests") or meta_agent.get("interests_to_choose"))[:12]
    behaviors = _as_list(targeting.get("behaviors") or meta_agent.get("behaviors_to_choose"))[:8]
    cities = _as_list(targeting.get("recommended_cities") or meta_agent.get("locations_to_choose"))[:10]
    exclusions = _as_list(targeting.get("excluded_audiences") or meta_agent.get("exclusions"))[:8]
    placements = _as_list(meta_agent.get("placements")) or [_as_str(result.get("placement_recommendation"), "Instagram Reels")]

    recommendation_evidence = f"{targeting_rationale} Evidence cues: {', '.join(product_cues[:3])}."
    targeting_recommendations = _as_dict(targeting.get("targeting_recommendations"))
    targeting_recommendations = {
        "demographics": _recommendation_item(
            _as_dict(targeting_recommendations.get("demographics")).get("name")
            or _as_dict(targeting_recommendations.get("demographics")).get("recommendation")
            or targeting.get("recommended_age_range")
            or "Broad test audience",
            _as_dict(targeting_recommendations.get("demographics")).get("evidence") or targeting_rationale,
            None,
            _as_dict(targeting_recommendations.get("demographics")).get("confidence"),
        ),
        "gender": _recommendation_item(
            _as_dict(targeting_recommendations.get("gender")).get("name")
            or _as_dict(targeting_recommendations.get("gender")).get("recommendation")
            or targeting.get("gender")
            or "All",
            _as_dict(targeting_recommendations.get("gender")).get("evidence") or targeting_rationale,
            None,
            _as_dict(targeting_recommendations.get("gender")).get("confidence"),
        ),
        "interests": _normalize_recommendation_list(
            targeting_recommendations.get("interests") or top_interests,
            recommendation_evidence,
            REAL_INTEREST_SET,
            12,
        ),
        "behaviors": _normalize_recommendation_list(
            targeting_recommendations.get("behaviors") or behaviors,
            recommendation_evidence,
            REAL_BEHAVIOR_SET,
            8,
        ),
        "locations": _normalize_recommendation_list(
            targeting_recommendations.get("locations") or cities,
            _as_str(targeting.get("city_reasoning"), recommendation_evidence),
            None,
            10,
        ),
        "placements": _normalize_recommendation_list(
            targeting_recommendations.get("placements") or placements,
            _as_str(result.get("placement_recommendation"), recommendation_evidence),
            None,
            5,
        ),
        "exclusions": _normalize_recommendation_list(
            targeting_recommendations.get("exclusions") or exclusions,
            "These exclusions reduce wasted spend from users unlikely to convert based on the creative promise.",
            None,
            8,
        ),
    }

    strategy_depth = _as_dict(result.get("strategy_depth"))
    strategy_depth = {
        "funnel_stage": _as_str(strategy_depth.get("funnel_stage"), "Problem-aware / consideration"),
        "buyer_intent_level": _as_str(strategy_depth.get("buyer_intent_level"), "Medium"),
        "offer_clarity_score": _clamp_int(strategy_depth.get("offer_clarity_score"), 0, 100, 55),
        "cta_strength_score": _clamp_int(strategy_depth.get("cta_strength_score"), 0, 100, 55),
        "landing_page_risk": _as_str(
            strategy_depth.get("landing_page_risk"),
            "Landing page promise must match the creative's hook, offer, and proof claims.",
        ),
        "audience_clusters": _as_dict(strategy_depth.get("audience_clusters")) or {
            "premium_buyers": [],
            "value_buyers": [],
            "trend_buyers": [],
            "problem_aware_buyers": [],
        },
        "next_tests": _normalize_test_angles(
            strategy_depth.get("next_tests") or targeting.get("testing_angles") or meta_agent.get("testing_angles"),
            top_interests,
            behaviors,
        ),
    }

    targeting.update({
        "recommended_age_range": _as_str(targeting.get("recommended_age_range"), "18-44 broad test"),
        "gender": _as_str(targeting.get("gender"), "All"),
        "psychographic_profile": _as_str(targeting.get("psychographic_profile"), targeting_rationale),
        "audience_persona": _as_str(targeting.get("audience_persona") or meta_agent.get("primary_persona"), targeting_rationale),
        "top_interests": top_interests,
        "interest_reasoning": _as_str(targeting.get("interest_reasoning"), targeting_rationale),
        "targeting_rationale": targeting_rationale,
        "behaviors": behaviors,
        "behavior_reasoning": _as_str(targeting.get("behavior_reasoning"), targeting_rationale),
        "city_tiers": _as_list(targeting.get("city_tiers")) or ["Tier-1", "Tier-2"],
        "recommended_cities": cities,
        "city_reasoning": _as_str(targeting.get("city_reasoning"), "Test a mix of metro and high-intent Tier-2 markets."),
        "excluded_audiences": exclusions,
        "language_recommendation": _as_str(targeting.get("language_recommendation"), "Hinglish with regional variants after first test."),
        "testing_angles": _normalize_test_angles(targeting.get("testing_angles"), top_interests, behaviors),
        "targeting_recommendations": targeting_recommendations,
    })

    agent_analysis["evidence_synthesizer"] = {
        "observed_timeline": timeline,
        "product_cues": product_cues,
        "cta_cues": cta_cues,
        "missing_evidence": missing_evidence,
        "unsupported_assumptions": unsupported_assumptions,
    }
    meta_testing_angles = []
    for index, item in enumerate(_as_list(meta_agent.get("testing_angles")) or strategy_depth["next_tests"]):
        item = _as_dict(item)
        meta_testing_angles.append({
            "name": _as_str(item.get("name"), f"Audience Test {index + 1}"),
            "setup": _as_str(item.get("setup") or item.get("audience"), "Use the recommended persona, locations, interests, and behaviors."),
            "hypothesis": _as_str(item.get("hypothesis") or item.get("why_test"), "Validates whether this audience responds to the core creative promise."),
        })

    agent_analysis["meta_targeting_agent"] = {
        "primary_persona": _as_str(meta_agent.get("primary_persona"), targeting["audience_persona"]),
        "demographics": _as_str(meta_agent.get("demographics"), targeting["psychographic_profile"]),
        "interests_to_choose": _as_list(meta_agent.get("interests_to_choose")) or top_interests,
        "behaviors_to_choose": _as_list(meta_agent.get("behaviors_to_choose")) or behaviors,
        "locations_to_choose": _as_list(meta_agent.get("locations_to_choose")) or cities,
        "exclusions": _as_list(meta_agent.get("exclusions")) or exclusions,
        "placements": placements,
        "testing_angles": meta_testing_angles,
        "reasoning": targeting_rationale,
    }
    agent_analysis["hook_agent"] = {
        "score": _clamp_int(hook_agent.get("score"), 0, 100, _clamp_int(result.get("hook_score"), 0, 100, 0)),
        "hook_type": _as_str(hook_agent.get("hook_type"), _as_str(result.get("hook_type"), "—")),
        "opening_diagnosis": _as_str(hook_agent.get("opening_diagnosis"), _as_str(result.get("hook_score_reasoning"), "—")),
        "fix": _as_str(hook_agent.get("fix"), _as_str(result.get("hook_timing"), "—")),
    }
    agent_analysis["virality_agent"] = {
        "score": _clamp_int(virality_agent.get("score"), 0, 100, 50),
        "scroll_stop_factor": _as_str(virality_agent.get("scroll_stop_factor"), "Needs a stronger first-frame pattern interrupt to improve scroll-stop."),
        "shareability": _as_str(virality_agent.get("shareability"), "Shareability depends on relatability, proof, or novelty shown in the first few seconds."),
        "trend_fit": _as_str(virality_agent.get("trend_fit"), "Trend fit should be validated against current Reels/UGC patterns."),
    }
    agent_analysis["caption_copy_agent"] = {
        "primary_caption": _as_str(copy_agent.get("primary_caption"), "Test a direct promise-led caption tied to the main buyer pain point."),
        "headline": _as_str(copy_agent.get("headline"), detected_product[:60]),
        "cta": _as_str(copy_agent.get("cta"), "Shop Now"),
        "copy_angles": _as_list(copy_agent.get("copy_angles")) or ["Pain-aware", "Proof-led", "Offer-led"],
    }
    agent_analysis["creative_diagnosis_agent"] = {
        "priority_fixes": _as_list(diagnosis_agent.get("priority_fixes")) or _as_list(result.get("improvement_suggestions")),
        "keep": _as_list(diagnosis_agent.get("keep")) or _as_list(result.get("strengths")),
        "risk": _as_str(diagnosis_agent.get("risk"), _as_str(result.get("overall_ad_readiness_reasoning"), "—")),
    }

    creative_format_score = _as_dict(result.get("creative_format_score"))
    result.update({
        "detected_product": detected_product,
        "creative_meaning_analysis": creative_meaning,
        "detected_brand_stage": _as_str(result.get("detected_brand_stage"), "Early-stage D2C (no brand recognition)"),
        "creative_type": _as_str(result.get("creative_type"), "Video Ad" if is_video else "Image Ad"),
        "hook_score": _clamp_int(result.get("hook_score"), 0, 100, 0),
        "hook_score_reasoning": _as_str(result.get("hook_score_reasoning"), agent_analysis["hook_agent"]["opening_diagnosis"]),
        "hook_timing": _as_str(result.get("hook_timing"), "Opening 0-3s"),
        "hook_type": _as_str(result.get("hook_type"), agent_analysis["hook_agent"]["hook_type"]),
        "strengths": _as_list(result.get("strengths")),
        "weaknesses": _as_list(result.get("weaknesses")),
        "improvement_suggestions": _as_list(result.get("improvement_suggestions")),
        "creative_format_score": {
            "visual_clarity": _score_reason(creative_format_score.get("visual_clarity")),
            "brand_visibility": _score_reason(creative_format_score.get("brand_visibility")),
            "emotion_factor": _score_reason(creative_format_score.get("emotion_factor")),
            "india_relevance": _score_reason(creative_format_score.get("india_relevance")),
        },
        "targeting": targeting,
        "placement_recommendation": _as_str(result.get("placement_recommendation"), "Instagram Reels and Stories for vertical-first testing."),
        "agent_analysis": agent_analysis,
        "strategy_depth": strategy_depth,
        "unsupported_assumptions": unsupported_assumptions,
        "overall_ad_readiness": _as_str(result.get("overall_ad_readiness"), "Needs minor fixes"),
        "overall_ad_readiness_reasoning": _as_str(result.get("overall_ad_readiness_reasoning"), "Run a small-budget test after addressing the highest-impact fixes."),
        "generated_hooks": _as_list(result.get("generated_hooks")),
        "generated_ad_copy": _as_list(result.get("generated_ad_copy")),
        "analysis_quality": {
            "schema_validated": True,
            "catalog_grounded": True,
            "recommendation_count": sum(len(targeting_recommendations[key]) for key in ("interests", "behaviors", "locations", "placements", "exclusions")),
            "unsupported_assumption_count": len(unsupported_assumptions),
        },
    })
    return result


def _light_repair_creative_analysis(result: dict, is_video: bool = False) -> dict:
    """Keep rich model output intact; only add missing containers required by the UI."""
    if not isinstance(result, dict) or not result:
        return _parse_error_response()
    if result.get("api_error") or result.get("parse_error"):
        return result

    result.setdefault("detected_product", "Unspecified ad creative")
    result.setdefault("creative_meaning_analysis", "No creative meaning analysis returned.")
    result.setdefault("detected_brand_stage", "Early-stage D2C (no brand recognition)")
    result.setdefault("creative_type", "Video Ad" if is_video else "Image Ad")
    result["hook_score"] = _clamp_int(result.get("hook_score"), 0, 100, 0)
    result.setdefault("hook_score_reasoning", "No hook reasoning returned.")
    result.setdefault("hook_timing", "Opening 0-3s")
    result.setdefault("hook_type", "—")
    result["strengths"] = _as_list(result.get("strengths"))
    result["weaknesses"] = _as_list(result.get("weaknesses"))
    result["improvement_suggestions"] = _as_list(result.get("improvement_suggestions"))

    creative_format_score = _as_dict(result.get("creative_format_score"))
    result["creative_format_score"] = {
        "visual_clarity": _score_reason(creative_format_score.get("visual_clarity")),
        "brand_visibility": _score_reason(creative_format_score.get("brand_visibility")),
        "emotion_factor": _score_reason(creative_format_score.get("emotion_factor")),
        "india_relevance": _score_reason(creative_format_score.get("india_relevance")),
    }

    targeting = _as_dict(result.get("targeting"))
    targeting.setdefault("recommended_age_range", "—")
    targeting.setdefault("gender", "All")
    targeting.setdefault("psychographic_profile", "No psychographic profile returned.")
    targeting.setdefault("audience_persona", targeting.get("psychographic_profile", "—"))
    targeting["top_interests"] = _as_list(targeting.get("top_interests"))
    targeting.setdefault("interest_reasoning", "No interest reasoning returned.")
    targeting.setdefault("targeting_rationale", targeting.get("interest_reasoning", "—"))
    targeting["behaviors"] = _as_list(targeting.get("behaviors"))
    targeting.setdefault("behavior_reasoning", "No behavior reasoning returned.")
    targeting["city_tiers"] = _as_list(targeting.get("city_tiers"))
    targeting["recommended_cities"] = _as_list(targeting.get("recommended_cities"))
    targeting.setdefault("city_reasoning", "No city reasoning returned.")
    targeting["excluded_audiences"] = _as_list(targeting.get("excluded_audiences"))
    targeting.setdefault("language_recommendation", "Hinglish")
    targeting["testing_angles"] = _as_list(targeting.get("testing_angles"))
    result["targeting"] = targeting

    result.setdefault("placement_recommendation", "Instagram Reels and Stories for vertical-first testing.")
    result.setdefault("overall_ad_readiness", "Needs minor fixes")
    result.setdefault("overall_ad_readiness_reasoning", "No readiness reasoning returned.")
    result["generated_hooks"] = _as_list(result.get("generated_hooks"))
    result["generated_ad_copy"] = _as_list(result.get("generated_ad_copy"))

    agent_analysis = _as_dict(result.get("agent_analysis"))
    evidence = _as_dict(agent_analysis.get("evidence_synthesizer"))
    evidence.setdefault("observed_timeline", [])
    evidence["product_cues"] = _as_list(evidence.get("product_cues"))
    evidence["cta_cues"] = _as_list(evidence.get("cta_cues"))
    evidence["missing_evidence"] = _as_list(evidence.get("missing_evidence"))
    agent_analysis["evidence_synthesizer"] = evidence

    meta_agent = _as_dict(agent_analysis.get("meta_targeting_agent"))
    meta_agent.setdefault("primary_persona", targeting.get("audience_persona", "—"))
    meta_agent.setdefault("demographics", targeting.get("psychographic_profile", "—"))
    meta_agent["interests_to_choose"] = _as_list(meta_agent.get("interests_to_choose")) or targeting["top_interests"]
    meta_agent["behaviors_to_choose"] = _as_list(meta_agent.get("behaviors_to_choose")) or targeting["behaviors"]
    meta_agent["locations_to_choose"] = _as_list(meta_agent.get("locations_to_choose")) or targeting["recommended_cities"]
    meta_agent["exclusions"] = _as_list(meta_agent.get("exclusions")) or targeting["excluded_audiences"]
    meta_agent["placements"] = _as_list(meta_agent.get("placements")) or [result["placement_recommendation"]]
    meta_agent["testing_angles"] = _as_list(meta_agent.get("testing_angles")) or targeting["testing_angles"]
    meta_agent.setdefault("reasoning", targeting.get("targeting_rationale", "—"))
    agent_analysis["meta_targeting_agent"] = meta_agent

    hook_agent = _as_dict(agent_analysis.get("hook_agent"))
    hook_agent.setdefault("score", result["hook_score"])
    hook_agent.setdefault("hook_type", result["hook_type"])
    hook_agent.setdefault("opening_diagnosis", result["hook_score_reasoning"])
    hook_agent.setdefault("fix", result["hook_timing"])
    agent_analysis["hook_agent"] = hook_agent

    virality_agent = _as_dict(agent_analysis.get("virality_agent"))
    virality_agent.setdefault("score", 0)
    virality_agent.setdefault("scroll_stop_factor", "Virality scoring not returned.")
    virality_agent.setdefault("shareability", "Shareability not returned.")
    virality_agent.setdefault("trend_fit", "Trend fit not returned.")
    agent_analysis["virality_agent"] = virality_agent

    copy_agent = _as_dict(agent_analysis.get("caption_copy_agent"))
    copy_agent.setdefault("primary_caption", "")
    copy_agent.setdefault("headline", "")
    copy_agent.setdefault("cta", "")
    copy_agent["copy_angles"] = _as_list(copy_agent.get("copy_angles"))
    agent_analysis["caption_copy_agent"] = copy_agent

    diagnosis_agent = _as_dict(agent_analysis.get("creative_diagnosis_agent"))
    diagnosis_agent["priority_fixes"] = _as_list(diagnosis_agent.get("priority_fixes")) or result["improvement_suggestions"]
    diagnosis_agent["keep"] = _as_list(diagnosis_agent.get("keep")) or result["strengths"]
    diagnosis_agent.setdefault("risk", result["overall_ad_readiness_reasoning"])
    agent_analysis["creative_diagnosis_agent"] = diagnosis_agent

    result["agent_analysis"] = agent_analysis
    return result


async def analyze_creative_for_targeting(
    frame_b64_list: list[str],
    transcript: str = "",
    is_video: bool = False,
    frame_labels: Optional[list[str]] = None
) -> dict:
    """
    Deep creative analysis using GPT-4o Vision.
    Accepts storyboard frames (1 for image, up to 4 for video) + Whisper transcript.
    Returns granular scoring WITH reasoning, dynamic Meta targeting, and compact mini-agent sections.
    """
    media_context = f"video ad storyboard ({len(frame_b64_list)} timestamped frames shown)" if is_video and len(frame_b64_list) > 1 else "image ad creative"
    transcript_section = f"\nVIDEO TRANSCRIPT (from Whisper):\n\"{transcript}\"\n" if transcript else "\n(No audio transcript available — image upload or silent video)\n"

    system_prompt = """You are a senior Meta Ads strategist, creative director, and agent orchestrator for Indian D2C brands.
Your primary job is to turn creative evidence into Meta-ready targeting decisions: demographics, interests, behaviors, placements, exclusions, and testable ad-set angles.
You must be brutally specific and evidence-backed. Do not invent unsupported audience claims. All output MUST be valid JSON."""

    user_prompt = f"""You are analyzing a {media_context} for a brand running Facebook/Instagram ads in India. {transcript_section}

REAL META TARGETING CATALOG CONTEXT:
Use the following catalog as grounding for interests and behaviors when relevant, but do not compress your reasoning into confidence-score objects. Give rich explanations in normal text fields.
{TARGETING_CONTEXT}
    
YOUR TASK:
Run a single-call mini-agent orchestration. Think in these roles, then return one unified JSON:
1. Evidence Synthesizer: identify concrete frame/transcript evidence, timeline moments, product cues, offer cues, emotions, CTA cues, and missing signals.
2. Meta Ads Targeting Agent (MAIN AGENT): convert that evidence into practical Meta ad-set decisions. This is the most important section. Give exact demographics, interests, behaviors, exclusions, locations, placements, languages, and 2-3 test audiences.
3. Hook Agent: score the opening, hook type, timing, and what to fix in the first 3 seconds.
4. Virality Agent: score scroll-stopping/shareability, trend fit, social proof, and friction.
5. Caption/Copy Agent: produce caption/copy variants tied to the target audience.
6. Creative Diagnosis Agent: produce strengths, weaknesses, and prioritized fixes.

First, deeply understand WHAT is happening in this ad and WHO it is speaking to. Do not just look at surface-level objects. Analyze the story, the emotional hook, the implicit pain points being solved, and the cultural context.
For video ads, you are seeing timestamped frames selected from a full local scan of the video. Reference exact timestamps such as "Frame at 1.20s" when explaining the hook, strengths, weaknesses, CTA, product visibility, and improvement ideas. Make it obvious that your reasoning comes from the observed timeline, not from generic ad advice.

Then, act as a dynamic Meta Ads interest search engine. Generate hyper-specific, highly relevant targeting parameters based directly on the ad content. DO NOT use generic buckets.
- For Demographics: Define exact life stages, jobs, and roles (e.g., 'college goers', 'parents of toddlers', 'software engineers in IT hubs').
- For Interests: List highly specific brands, competitors, and exact Meta interests (e.g., 'Fabindia', 'Myntra', 'Organic food', 'Puma').
- For Locations: Identify specific Indian cities, districts, or regions where this exact product will "boom" (e.g., 'Koramangala in Bangalore', 'Tier-2 districts like Nashik or Surat for ethnic wear').
	- For test audiences: create 2-3 Meta ad-set variants, each with audience name, age/gender/location/interests/behaviors/exclusions, and why to test it.
	- Use exact interest/behavior names from the grounding catalog whenever possible, but prioritize a detailed and useful strategy over compact validation metadata.
	- Evidence-backed reasoning: every major recommendation should cite a visible frame timestamp, transcript phrase, product cue, offer cue, or CTA cue.
	- Creative timeline: for video, analyze EVERY selected frame label provided above. For image, create one detailed "Image" row. Each timeline row must explain what is visible, what it signals for marketing, and the conversion issue or opportunity.
	- Audience clusters: produce premium buyers, value buyers, trend buyers, problem-aware buyers, and gift buyers. Each cluster should include the buyer type, targeting cue, copy angle, and evidence.
	- Copy generation: create 5 primary texts, 5 hooks, 3 headlines, 3 CTA variants, 3 first-frame overlay text ideas, and 2 short UGC scripts. Avoid repeating the same angle.

	Return ONLY a valid JSON object with this EXACT structure:

{{
  "detected_product": "<Be specific: e.g. 'Ayurvedic anti-hairfall oil for postpartum mothers' not 'hair oil'>",
  "creative_meaning_analysis": "<2-3 sentences analyzing the underlying message and meaning of the ad. What is the emotional or utilitarian pitch?>",
  "detected_brand_stage": "<one of: Early-stage D2C (no brand recognition), Growing D2C (some presence), Established brand>",
  "creative_type": "<one of: Video Ad, Image Ad, UGC Video, Brand Film, Product Demo, Testimonial, Lifestyle, Unboxing, Meme/Trend>",

  "hook_score": <integer 1-100>,
  "hook_score_reasoning": "<Cite the EXACT visual/audio element in the first 2-3 seconds that creates or kills the hook. e.g. 'Opens with a static product shot against white background — no motion, no curiosity gap, viewer has no reason to stop scrolling'>",
  "hook_timing": "<e.g. 'Hook peaks at ~1.5s when the model reacts with surprise — this is the stop-scroll moment'>",
  "hook_type": "<one of: Motion Hook, Curiosity/Pattern Interrupt, Emotion/Reaction Hook, Price/Offer Hook, UGC/Social Proof Hook, Product Transformation Hook, Text-first Hook>",

  "strengths": [
    "<Cite SPECIFIC visual/audio element + WHY it hits the target demographic's psychology. If the ad uses relatability or meme/trend factors effectively, explicitly mention it here.>",
    "<Strength 2>",
    "<Strength 3>"
  ],

  "weaknesses": [
    "<Weakness 1: cite exactly what's missing and why it hurts conversions.>",
    "<Weakness 2>",
    "<Weakness 3>"
  ],

  "improvement_suggestions": [
    "<Actionable suggestion tied to a specific weakness.>",
    "<Suggestion 2>",
    "<Suggestion 3>"
  ],

  "creative_format_score": {{
    "visual_clarity": {{
      "score": <1-10>,
      "reasoning": "<What specifically makes it clear or unclear>"
    }},
    "brand_visibility": {{
      "score": <1-10>,
      "reasoning": "<Is brand name/logo visible? Where?>"
    }},
    "emotion_factor": {{
      "score": <1-10>,
      "reasoning": "<What emotion does this creative evoke and how effectively?>"
    }},
    "india_relevance": {{
      "score": <1-10>,
      "reasoning": "<Cultural nuances, language, casting, aesthetics that fit India>"
    }}
  }},

  "targeting": {{
    "recommended_age_range": "<e.g. '18-24 (College)', '28-35 (Young Parents)'>",
    "gender": "<All / Women / Men — with brief justification>",
    "psychographic_profile": "<1-2 sentences. Exactly who wakes up needing this solution based on the ad's messaging? Include their job, lifestyle, or daily routine.>",
    "audience_persona": "<A specific buyer persona title + short description, e.g. 'Urban first-job skincare optimizer: 22-28 women in Bangalore/Mumbai who buy Nykaa products monthly'>",
    "top_interests": [
      "<Generate 8 to 12 highly specific Meta interests. Cast a wide but relevant net.>",
      "<Include exact competitor brands (e.g. FirstCry, Hamleys)>",
      "<Include lateral affinities (e.g. School supplies, Organic kids clothing)>",
      "<Include broad but relevant buyer buckets (e.g. Parents of toddlers, Primary school teachers)>",
      "<Interest 5>",
      "<Interest 6>",
      "<Interest 7>",
      "<Interest 8>"
    ],
    "interest_reasoning": "<Why are these exact interests, brands, or jobs the best fit for this creative?>",
    "targeting_rationale": "<Strategic explanation tying demographics, interests, behaviors, and placements to observed creative evidence. Mention frame/timestamp evidence when available.>",
    "behaviors": [
      "<e.g. 'Online Shopping', 'Engaged Shoppers', 'Early technology adopters', 'Frequent International Travelers'>",
      "<Behavior 2>"
    ],
    "behavior_reasoning": "<Why these behaviors match the buyer's intent>",
    "city_tiers": ["<Tier-1 / Tier-2 / Tier-3>"],
    "recommended_cities": [
      "<Provide 6 to 10 highly specific Indian districts or cities where this product will boom. Must include a mix of Tier-1 hubs and high-potential Tier-2/3 towns based on the exact product.>",
      "<City 2>",
      "<City 3>",
      "<City 4>",
      "<City 5>",
      "<City 6>"
    ],
    "city_reasoning": "<Provide a deep, 3-4 sentence strategic elaboration on WHY these precise Indian districts/cities are the primary market. Explain the geographic strategy based on wealth, infrastructure, or cultural affinity to the product.>",
    "excluded_audiences": ["<Who to exclude to save money>"],
    "language_recommendation": "<Hindi / English / Hinglish / Regional — with reasoning>",
	    "testing_angles": [
	      {{
	        "name": "<Ad set name, e.g. 'Urban Premium Buyers'>",
	        "audience": "<Age, gender, city tier, and persona>",
	        "age_range": "<exact Meta age range>",
	        "gender": "<All / Women / Men with reason>",
	        "locations": ["<city/district>", "<city/district>", "<city/district>"],
	        "interests": ["<specific interest>", "<specific interest>", "<specific interest>"],
	        "behaviors": ["<specific behavior>", "<specific behavior>"],
	        "exclusions": ["<audience to exclude>"],
	        "placements": ["<placement>", "<placement>"],
	        "copy_angle": "<message angle for this ad set>",
	        "why_test": "<What hypothesis this ad set tests>",
	        "evidence": "<Frame timestamp/transcript/product cue that supports this audience>"
	      }},
	      {{
	        "name": "<Ad set name>",
	        "audience": "<Age, gender, city tier, and persona>",
	        "age_range": "<exact Meta age range>",
	        "gender": "<All / Women / Men with reason>",
	        "locations": ["<city/district>", "<city/district>", "<city/district>"],
	        "interests": ["<specific interest>", "<specific interest>", "<specific interest>"],
	        "behaviors": ["<specific behavior>", "<specific behavior>"],
	        "exclusions": ["<audience to exclude>"],
	        "placements": ["<placement>", "<placement>"],
	        "copy_angle": "<message angle for this ad set>",
	        "why_test": "<What hypothesis this ad set tests>",
	        "evidence": "<Frame timestamp/transcript/product cue that supports this audience>"
	      }}
	    ]
	  }},

  "placement_recommendation": "<Best Meta placement for this aspect ratio/style, with reasoning>",

	  "agent_analysis": {{
	    "evidence_synthesizer": {{
	      "observed_timeline": [
	        {{"timestamp": "<Frame at 0.40s or Image>", "observation": "<What is visibly/audibly present>", "marketing_signal": "<Why it matters for ad performance or targeting>", "conversion_issue_or_opportunity": "<Specific issue/opportunity in this moment>"}},
	        {{"timestamp": "<Frame at 2.20s>", "observation": "<Observation>", "marketing_signal": "<Signal>", "conversion_issue_or_opportunity": "<Issue/opportunity>"}}
	      ],
	      "product_cues": ["<specific visible/audio cue>", "<cue 2>"],
	      "cta_cues": ["<specific CTA/offer cue or missing CTA>", "<cue 2>"],
      "missing_evidence": ["<important signal not visible, e.g. price, offer, proof, logo, CTA>"]
    }},
    "meta_targeting_agent": {{
      "primary_persona": "<Specific Meta buyer persona>",
      "demographics": "<Age/gender/life-stage/job-role decision>",
      "interests_to_choose": ["<specific Meta interest>", "<specific brand/competitor>", "<interest 3>", "<interest 4>", "<interest 5>", "<interest 6>"],
      "behaviors_to_choose": ["<Meta behavior>", "<behavior 2>", "<behavior 3>"],
      "locations_to_choose": ["<city/district>", "<city/district>", "<city/district>"],
      "exclusions": ["<exclude this audience>", "<exclude this audience>"],
	      "placements": ["<placement>", "<placement>"],
	      "testing_angles": [
	        {{"name": "<ad set name>", "setup": "<Meta targeting setup with age, gender, locations, interests, behaviors, exclusions, placements>", "hypothesis": "<why this could win>", "evidence": "<frame/transcript cue>", "copy_angle": "<message angle>"}},
	        {{"name": "<ad set name>", "setup": "<Meta targeting setup with age, gender, locations, interests, behaviors, exclusions, placements>", "hypothesis": "<why this could win>", "evidence": "<frame/transcript cue>", "copy_angle": "<message angle>"}}
	      ],
	      "reasoning": "<Evidence-backed targeting rationale>"
	    }},
    "hook_agent": {{
      "score": <integer 1-100>,
      "hook_type": "<specific hook type>",
      "opening_diagnosis": "<What happens in first 3 seconds and why it stops/loses attention>",
      "fix": "<Precise opening change>"
    }},
    "virality_agent": {{
      "score": <integer 1-100>,
      "scroll_stop_factor": "<What creates or fails to create a scroll stop>",
      "shareability": "<Why someone would or would not share/comment/save>",
      "trend_fit": "<How it fits or misses current Reels/UGC/meta ad patterns>"
    }},
    "caption_copy_agent": {{
      "primary_caption": "<Best primary text for Meta>",
      "headline": "<Short headline>",
      "cta": "<CTA button/text recommendation>",
	      "copy_angles": ["<angle 1>", "<angle 2>", "<angle 3>"]
	    }},
    "creative_diagnosis_agent": {{
      "priority_fixes": ["<highest leverage fix>", "<fix 2>", "<fix 3>"],
      "keep": ["<what not to change>", "<keep 2>"],
      "risk": "<Biggest spend-waste risk if launched as-is>"
    }}
	  }},

	  "strategy_depth": {{
	    "audience_clusters": {{
	      "premium_buyers": [
	        {{"buyer_type": "<specific premium buyer>", "targeting_cue": "<interest/behavior/location cue>", "copy_angle": "<angle>", "evidence": "<frame/transcript/product cue>"}}
	      ],
	      "value_buyers": [
	        {{"buyer_type": "<specific value buyer>", "targeting_cue": "<cue>", "copy_angle": "<angle>", "evidence": "<evidence>"}}
	      ],
	      "trend_buyers": [
	        {{"buyer_type": "<specific trend buyer>", "targeting_cue": "<cue>", "copy_angle": "<angle>", "evidence": "<evidence>"}}
	      ],
	      "problem_aware_buyers": [
	        {{"buyer_type": "<specific problem-aware buyer>", "targeting_cue": "<cue>", "copy_angle": "<angle>", "evidence": "<evidence>"}}
	      ],
	      "gift_buyers": [
	        {{"buyer_type": "<specific gift buyer if relevant, otherwise explain low relevance>", "targeting_cue": "<cue>", "copy_angle": "<angle>", "evidence": "<evidence>"}}
	      ]
	    }}
	  }},

	  "overall_ad_readiness": "<one of: Ready to run / Needs minor fixes / Needs major rework>",
	  "overall_ad_readiness_reasoning": "<1-2 sentences on whether this creative is strong enough to spend budget on right now>",

	  "generated_hooks": [
	    {{
	      "hook_script": "<A detailed 3-second video hook script (Visuals + Dialogue)>",
	      "psychological_angle": "<Why this specific angle will convert the target audience>"
	    }},
	    {{"hook_script": "...", "psychological_angle": "..."}},
	    {{"hook_script": "...", "psychological_angle": "..."}},
	    {{"hook_script": "...", "psychological_angle": "..."}},
	    {{"hook_script": "...", "psychological_angle": "..."}}
	  ],

	  "generated_ad_copy": [
    {{
      "copy_text": "<Full 3-4 line Facebook/Instagram primary text. Use emojis appropriately.>",
      "copy_angle": "<e.g. 'Storytelling', 'Direct Offer', 'Pain-Agitate-Resolve'>"
	    }},
	    {{"copy_text": "...", "copy_angle": "..."}},
	    {{"copy_text": "...", "copy_angle": "..."}},
	    {{"copy_text": "...", "copy_angle": "..."}},
	    {{"copy_text": "...", "copy_angle": "..."}}
	  ],

	  "generated_headlines": ["<headline 1>", "<headline 2>", "<headline 3>"],
	  "cta_variants": ["<CTA 1>", "<CTA 2>", "<CTA 3>"],
	  "overlay_text_ideas": ["<first-frame overlay text 1>", "<overlay 2>", "<overlay 3>"],
	  "ugc_scripts": [
	    {{"script_title": "<UGC script name>", "opening_visual": "<first shot>", "voiceover": "<short script>", "cta": "<ending CTA>", "target_audience": "<who this script is for>"}},
	    {{"script_title": "<UGC script name>", "opening_visual": "<first shot>", "voiceover": "<short script>", "cta": "<ending CTA>", "target_audience": "<who this script is for>"}}
	  ]
	}}

Be brutally honest. Specific. Reference what you actually see/hear. Do not output anything outside the JSON boundaries. Return ONLY valid JSON."""

    if not client:
        result = _default_targeting_response()
        return _attach_runtime_metadata(result, "none", fallback_used=True)

    messages = _build_vision_messages(frame_b64_list, user_prompt, system_prompt, frame_labels=frame_labels)
    profile = _active_model_profile()
    attempts = [
        (profile.vision_model, False),
        (profile.fallback_vision_model, True),
    ]
    last_error = None

    for model, fallback_used in attempts:
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
                max_tokens=7600,
                temperature=0.2,
                timeout=profile.timeout_seconds,
            )
            raw = response.choices[0].message.content or ""
            result = _extract_json(raw)
            if not result:
                last_error = f"JSON parse failed from {model}: {raw[:500]}"
                print(last_error)
                continue
            repaired = _light_repair_creative_analysis(result, is_video=is_video)
            return _attach_runtime_metadata(repaired, model, fallback_used=fallback_used)
        except Exception as e:
            last_error = str(e)
            print(f"OpenAI creative targeting error with {model}: {e}")

    print(f"All creative targeting attempts failed: {last_error}")
    result = _default_targeting_response()
    result["failure_reason"] = "OpenAI request failed or returned malformed JSON after fallback."
    return _attach_runtime_metadata(result, profile.fallback_vision_model, fallback_used=True)


async def analyze_creative_performance(image_b64: str, metrics_context: dict) -> dict:
    """
    Analyzes an ad creative via GPT-4o Vision in context of real campaign metrics.
    Returns deep reasoning on why the ad worked, and specific improvements.
    """
    metrics_str = json.dumps(metrics_context, indent=2)

    system_prompt = """You are a senior Meta Ads strategist specializing in Indian D2C e-commerce.
You review real campaign performance data alongside ad creatives.
Your analysis must be professional, data-driven, and returned ONLY as a valid JSON object."""

    user_prompt = f"""Analyze WHY this creative drove the specific results shown below.
    
CAMPAIGN PERFORMANCE:
{metrics_str}

TASK: Be specific about:
- Which exact visual elements likely drove conversions (or hurt them)
- How the ROAS of {metrics_context.get('roas', 'N/A')}x compares to what this creative deserves
- What to test next based on what you actually see

Return a JSON object:
{{
  "creative_quality_score": <integer 1-100>,
  "creative_quality_reasoning": "<What specifically earns or loses this score>",
  "hook_analysis": "<Specific observation about the opening 3 seconds — what works or doesn't>",
  "why_it_worked": [
    "<Specific element + mechanism: e.g. 'The unboxing reveal at 2s creates a pattern interrupt — viewers who stop here are high-intent'>",
    "<Reason 2>",
    "<Reason 3>"
  ],
  "why_it_underperformed": [
    "<Specific friction point if ROAS < break-even, else skip with null>"
  ],
  "improvement_suggestions": [
    "<Specific test idea: e.g. 'Test a version that opens with the end result (product in use/worn) instead of the packaging — reduces cognitive load'>",
    "<Suggestion 2>",
    "<Suggestion 3>"
  ],
  "india_market_fit": "<How well does this creative feel designed FOR India? Cite specific cultural signals you see>",
  "verdict": "<Strong Performer / Good Creative / Needs Improvement>"
}}

Return ONLY valid JSON."""

    try:
        profile = _active_model_profile()
        response = await client.chat.completions.create(
            model=profile.vision_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}", "detail": "high"}},
                        {"type": "text", "text": user_prompt}
                    ]
                }
            ],
            max_tokens=1400,
            temperature=0.3,
            timeout=profile.timeout_seconds,
        )
        raw = response.choices[0].message.content or ""
        result = _extract_json(raw)
        return result or _default_performance_response()
    except Exception as e:
        print(f"OpenAI performance analysis error: {e}")
        return _default_performance_response()


async def analyze_text_only_performance(metrics_context: dict) -> dict:
    metrics_str = json.dumps(metrics_context, indent=2)
    prompt = f"""You are a Meta Ads strategist for Indian D2C brands.
Analyze these campaign metrics and give specific, useful advice (not generic):

METRICS:
{metrics_str}

Return JSON:
{{
  "performance_verdict": "<Strong Performer / Good / Break-even / Underperformer>",
  "performance_summary": "<2 sentences specific to these numbers>",
  "key_insights": ["<insight with specific numbers>", "<insight 2>", "<insight 3>"],
  "improvement_actions": ["<action tied to specific metric>", "<action 2>", "<action 3>"],
  "next_steps": "<What to do in the next 7 days based on these exact numbers>",
  "benchmark_comparison": "<How ROAS of {metrics_context.get('roas','?')}x compares to Indian D2C benchmarks by category>"
}}
Return ONLY valid JSON."""
    try:
        profile = _active_model_profile()
        response = await client.chat.completions.create(
            model=profile.text_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=700,
            temperature=0.3,
            timeout=profile.timeout_seconds,
        )
        raw = response.choices[0].message.content or ""
        return _extract_json(raw) or _default_text_analysis()
    except Exception as e:
        print(f"Text analysis error: {e}")
        return _default_text_analysis()


def _parse_error_response() -> dict:
    """Returned when GPT-4o responded but did not produce parseable JSON.
    Typically happens for non-ad images (portraits, memes, pixel art, etc.).
    Does NOT mention API keys — the key is fine, the image just isn't an ad."""
    return {
        "parse_error": True,
        "detected_product": "Not identifiable as an ad creative",
        "creative_meaning_analysis": "This image does not appear to be an advertisement. Upload a real ad creative (image or video) to get targeting and scoring analysis.",
        "detected_brand_stage": "—",
        "creative_type": "—",
        "hook_score": 0,
        "hook_score_reasoning": "No ad hook detected — this does not appear to be an ad creative.",
        "hook_timing": "—",
        "hook_type": "—",
        "strengths": [],
        "weaknesses": ["Image is not an ad creative — analysis cannot be performed."],
        "improvement_suggestions": ["Upload a Facebook/Instagram ad image or video to receive targeting and creative scoring."],
        "creative_format_score": {
            "visual_clarity": {"score": 0, "reasoning": "Not an ad creative"},
            "brand_visibility": {"score": 0, "reasoning": "Not an ad creative"},
            "emotion_factor": {"score": 0, "reasoning": "Not an ad creative"},
            "india_relevance": {"score": 0, "reasoning": "Not an ad creative"}
        },
        "targeting": {
            "recommended_age_range": "—",
            "gender": "—",
            "psychographic_profile": "Upload an ad creative to generate targeting recommendations.",
            "audience_persona": "—",
            "top_interests": [],
            "interest_reasoning": "—",
            "targeting_rationale": "—",
            "behaviors": [],
            "behavior_reasoning": "—",
            "city_tiers": [],
            "recommended_cities": [],
            "city_reasoning": "—",
            "excluded_audiences": [],
            "language_recommendation": "—",
            "testing_angles": []
        },
        "placement_recommendation": "—",
        "agent_analysis": {
            "evidence_synthesizer": {
                "observed_timeline": [],
                "product_cues": [],
                "cta_cues": [],
                "missing_evidence": ["Upload a clear ad creative to generate evidence-backed analysis."]
            },
            "meta_targeting_agent": {
                "primary_persona": "—",
                "demographics": "—",
                "interests_to_choose": [],
                "behaviors_to_choose": [],
                "locations_to_choose": [],
                "exclusions": [],
                "placements": [],
                "testing_angles": [],
                "reasoning": "—"
            },
            "hook_agent": {
                "score": 0,
                "hook_type": "—",
                "opening_diagnosis": "—",
                "fix": "—"
            },
            "virality_agent": {
                "score": 0,
                "scroll_stop_factor": "—",
                "shareability": "—",
                "trend_fit": "—"
            },
            "caption_copy_agent": {
                "primary_caption": "—",
                "headline": "—",
                "cta": "—",
                "copy_angles": []
            },
            "creative_diagnosis_agent": {
                "priority_fixes": [],
                "keep": [],
                "risk": "—"
            }
        },
        "overall_ad_readiness": "Needs major rework",
        "overall_ad_readiness_reasoning": "This does not appear to be an ad creative.",
        "generated_hooks": [],
        "generated_ad_copy": []
    }


def _default_targeting_response() -> dict:
    return {
        "api_error": True,
        "detected_product": "Unable to detect — OpenAI key may not be set",
        "detected_brand_stage": "Early-stage D2C (no brand recognition)",
        "creative_type": "Video Ad",
        "hook_score": 0,
        "hook_score_reasoning": "Analysis unavailable — check your OpenAI API key in backend/.env",
        "hook_timing": "—",
        "hook_type": "Product Demo",
        "strengths": ["Set your OPENAI_API_KEY in backend/.env to enable analysis"],
        "weaknesses": ["API key required for real analysis"],
        "improvement_suggestions": ["Add OPENAI_API_KEY=sk-... to backend/.env and restart the server"],
        "creative_format_score": {
            "visual_clarity": {"score": 0, "reasoning": "API key not configured"},
            "brand_visibility": {"score": 0, "reasoning": "API key not configured"},
            "emotion_factor": {"score": 0, "reasoning": "API key not configured"},
            "india_relevance": {"score": 0, "reasoning": "API key not configured"}
        },
        "targeting": {
            "recommended_age_range": "—",
            "gender": "—",
            "psychographic_profile": "Configure API key to enable targeting",
            "audience_persona": "—",
            "top_interests": ["API key required"],
            "interest_reasoning": "—",
            "targeting_rationale": "—",
            "behaviors": ["API key required"],
            "behavior_reasoning": "—",
            "city_tiers": ["Tier-1"],
            "recommended_cities": ["Mumbai", "Delhi", "Bangalore"],
            "city_reasoning": "—",
            "excluded_audiences": [],
            "language_recommendation": "Hinglish",
            "testing_angles": []
        },
        "placement_recommendation": "Instagram Reels (9:16 vertical video)",
        "agent_analysis": {
            "evidence_synthesizer": {
                "observed_timeline": [],
                "product_cues": [],
                "cta_cues": [],
                "missing_evidence": ["OpenAI API key required for visual evidence analysis"]
            },
            "meta_targeting_agent": {
                "primary_persona": "—",
                "demographics": "—",
                "interests_to_choose": ["API key required"],
                "behaviors_to_choose": ["API key required"],
                "locations_to_choose": ["Mumbai", "Delhi", "Bangalore"],
                "exclusions": [],
                "placements": ["Instagram Reels"],
                "testing_angles": [],
                "reasoning": "Configure API key to enable targeting."
            },
            "hook_agent": {
                "score": 0,
                "hook_type": "Product Demo",
                "opening_diagnosis": "Analysis unavailable — check OpenAI API key.",
                "fix": "Add OPENAI_API_KEY to backend/.env and restart the server."
            },
            "virality_agent": {
                "score": 0,
                "scroll_stop_factor": "—",
                "shareability": "—",
                "trend_fit": "—"
            },
            "caption_copy_agent": {
                "primary_caption": "—",
                "headline": "—",
                "cta": "—",
                "copy_angles": []
            },
            "creative_diagnosis_agent": {
                "priority_fixes": ["Add OPENAI_API_KEY=sk-... to backend/.env"],
                "keep": [],
                "risk": "Analysis cannot run without API access."
            }
        },
        "overall_ad_readiness": "Needs major rework",
        "overall_ad_readiness_reasoning": "Cannot assess without OpenAI API key.",
        "generated_hooks": [],
        "generated_ad_copy": []
    }


def _default_performance_response() -> dict:
    return {
        "creative_quality_score": 0,
        "creative_quality_reasoning": "API key not configured — add to backend/.env",
        "hook_analysis": "—",
        "why_it_worked": ["Configure OPENAI_API_KEY to enable analysis"],
        "why_it_underperformed": [],
        "improvement_suggestions": ["Add OPENAI_API_KEY=sk-... to backend/.env"],
        "india_market_fit": "—",
        "verdict": "Needs Improvement"
    }


def _default_text_analysis() -> dict:
    return {
        "performance_verdict": "Good",
        "performance_summary": "Analysis temporarily unavailable.",
        "key_insights": ["Configure OpenAI key to enable insights"],
        "improvement_actions": ["Add OPENAI_API_KEY to backend/.env"],
        "next_steps": "—",
        "benchmark_comparison": "Indian D2C average ROAS: 2-4x"
    }
