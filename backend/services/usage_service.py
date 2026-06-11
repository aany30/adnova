from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Any


class UsageLimitExceeded(Exception):
    def __init__(self, message: str, payload: dict[str, Any]):
        super().__init__(message)
        self.payload = payload


class InMemoryUsageStore:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []
        self.failures: deque[dict[str, Any]] = deque(maxlen=50)
        self.model_profile = "balanced"
        self.daily_limit = 25
        self.monthly_limit = 250

    def configure_limits(self, daily_limit: int, monthly_limit: int) -> None:
        self.daily_limit = daily_limit
        self.monthly_limit = monthly_limit

    def set_model_profile(self, profile: str) -> None:
        self.model_profile = profile

    def _counts(self, actor_id: str, now: datetime) -> tuple[int, int]:
        day_start = now - timedelta(days=1)
        month_start = now - timedelta(days=30)
        daily = 0
        monthly = 0
        for event in self.events:
            if event.get("actor_id") != actor_id or event.get("status") != "success":
                continue
            created_at = event.get("created_at")
            if not isinstance(created_at, datetime):
                continue
            if created_at >= month_start:
                monthly += 1
            if created_at >= day_start:
                daily += 1
        return daily, monthly

    def quota_status(self, actor_id: str) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        daily, monthly = self._counts(actor_id, now)
        return {
            "actor_id": actor_id,
            "daily_limit": self.daily_limit,
            "monthly_limit": self.monthly_limit,
            "daily_used": daily,
            "monthly_used": monthly,
            "daily_remaining": max(self.daily_limit - daily, 0),
            "monthly_remaining": max(self.monthly_limit - monthly, 0),
            "daily_reset_at": (now + timedelta(days=1)).isoformat(),
            "monthly_reset_at": (now + timedelta(days=30)).isoformat(),
        }

    def check_limit(self, actor_id: str) -> dict[str, Any]:
        payload = self.quota_status(actor_id)
        if payload["daily_used"] >= self.daily_limit:
            raise UsageLimitExceeded("Daily analysis limit reached.", payload)
        if payload["monthly_used"] >= self.monthly_limit:
            raise UsageLimitExceeded("Monthly analysis limit reached.", payload)
        return payload

    def record_success(self, actor_id: str, metadata: dict[str, Any]) -> None:
        self.events.append({
            "actor_id": actor_id,
            "status": "success",
            "created_at": datetime.now(timezone.utc),
            "metadata": metadata,
        })

    def record_failure(self, actor_id: str, reason: str, metadata: dict[str, Any] | None = None) -> None:
        event = {
            "actor_id": actor_id,
            "status": "failure",
            "reason": reason,
            "created_at": datetime.now(timezone.utc),
            "metadata": metadata or {},
        }
        self.events.append(event)
        self.failures.appendleft(event)

    def stats(self) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        by_actor: dict[str, dict[str, int]] = defaultdict(lambda: {"success": 0, "failure": 0})
        fallback_count = 0
        for event in self.events:
            actor = event.get("actor_id", "unknown")
            status = event.get("status", "failure")
            by_actor[actor][status] = by_actor[actor].get(status, 0) + 1
            if event.get("metadata", {}).get("fallback_used"):
                fallback_count += 1

        total = len(self.events)
        success = sum(1 for event in self.events if event.get("status") == "success")
        failures = total - success
        recent = []
        for event in self.events[-20:][::-1]:
            created_at = event.get("created_at")
            recent.append({
                "actor_id": event.get("actor_id"),
                "status": event.get("status"),
                "reason": event.get("reason"),
                "created_at": created_at.isoformat() if isinstance(created_at, datetime) else str(created_at),
                "metadata": event.get("metadata", {}),
            })

        return {
            "total_requests": total,
            "successful_requests": success,
            "failed_requests": failures,
            "fallback_count": fallback_count,
            "fallback_rate": round((fallback_count / success) * 100, 1) if success else 0,
            "model_profile": self.model_profile,
            "daily_limit": self.daily_limit,
            "monthly_limit": self.monthly_limit,
            "recent_events": recent,
            "recent_failures": [
                {
                    "actor_id": item.get("actor_id"),
                    "reason": item.get("reason"),
                    "created_at": item.get("created_at").isoformat() if isinstance(item.get("created_at"), datetime) else str(item.get("created_at")),
                    "metadata": item.get("metadata", {}),
                }
                for item in list(self.failures)[:10]
            ],
            "by_actor": dict(by_actor),
            "generated_at": now.isoformat(),
        }


usage_store = InMemoryUsageStore()
