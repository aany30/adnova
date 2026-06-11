import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _list_env(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [item.strip().lower() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class ModelProfile:
    vision_model: str
    fallback_vision_model: str
    text_model: str
    transcription_model: str
    timeout_seconds: float


MODEL_PROFILES: dict[str, ModelProfile] = {
    "quality": ModelProfile(
        vision_model=os.getenv("OPENAI_QUALITY_VISION_MODEL", "gpt-4o"),
        fallback_vision_model=os.getenv("OPENAI_QUALITY_FALLBACK_MODEL", "gpt-4o-mini"),
        text_model=os.getenv("OPENAI_QUALITY_TEXT_MODEL", "gpt-4o"),
        transcription_model=os.getenv("OPENAI_TRANSCRIPTION_MODEL", "whisper-1"),
        timeout_seconds=float(os.getenv("OPENAI_QUALITY_TIMEOUT", "90")),
    ),
    "balanced": ModelProfile(
        vision_model=os.getenv("OPENAI_BALANCED_VISION_MODEL", "gpt-4o"),
        fallback_vision_model=os.getenv("OPENAI_BALANCED_FALLBACK_MODEL", "gpt-4o-mini"),
        text_model=os.getenv("OPENAI_BALANCED_TEXT_MODEL", "gpt-4o-mini"),
        transcription_model=os.getenv("OPENAI_TRANSCRIPTION_MODEL", "whisper-1"),
        timeout_seconds=float(os.getenv("OPENAI_BALANCED_TIMEOUT", "75")),
    ),
    "economy": ModelProfile(
        vision_model=os.getenv("OPENAI_ECONOMY_VISION_MODEL", "gpt-4o-mini"),
        fallback_vision_model=os.getenv("OPENAI_ECONOMY_FALLBACK_MODEL", "gpt-4o-mini"),
        text_model=os.getenv("OPENAI_ECONOMY_TEXT_MODEL", "gpt-4o-mini"),
        transcription_model=os.getenv("OPENAI_TRANSCRIPTION_MODEL", "whisper-1"),
        timeout_seconds=float(os.getenv("OPENAI_ECONOMY_TIMEOUT", "60")),
    ),
}


DEFAULT_MODEL_PROFILE = os.getenv("ADNOVA_MODEL_PROFILE", "balanced").lower()
if DEFAULT_MODEL_PROFILE not in MODEL_PROFILES:
    DEFAULT_MODEL_PROFILE = "balanced"

DAILY_QUERY_LIMIT = _int_env("ADNOVA_DAILY_QUERY_LIMIT", 25)
MONTHLY_QUERY_LIMIT = _int_env("ADNOVA_MONTHLY_QUERY_LIMIT", 250)
ADMIN_EMAILS = _list_env("ADNOVA_ADMIN_EMAILS")
LOCAL_ADMIN_ENABLED = os.getenv("NEXT_PUBLIC_DISABLE_AUTH", "").lower() == "true" or os.getenv("ADNOVA_LOCAL_ADMIN", "true").lower() == "true"
