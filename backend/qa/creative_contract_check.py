from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_ANALYSIS_FIELDS = [
    "detected_product",
    "creative_meaning_analysis",
    "hook_score",
    "hook_score_reasoning",
    "targeting",
    "agent_analysis",
    "generated_hooks",
    "generated_ad_copy",
]

REQUIRED_TARGETING_FIELDS = [
    "recommended_age_range",
    "gender",
    "top_interests",
    "behaviors",
    "recommended_cities",
    "excluded_audiences",
    "language_recommendation",
]


def _failures_for_response(payload: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if payload.get("status") != "success":
        failures.append("top-level status should be success")

    frames = payload.get("frames_analyzed")
    if payload.get("is_video") and not (12 <= int(frames or 0) <= 16):
        failures.append(f"video frames_analyzed should be 12-16, got {frames}")
    if not payload.get("is_video") and frames != 1:
        failures.append(f"image frames_analyzed should be 1, got {frames}")

    analysis = payload.get("ai_analysis")
    if not isinstance(analysis, dict):
        return failures + ["ai_analysis should be an object"]

    for field in REQUIRED_ANALYSIS_FIELDS:
        if field not in analysis:
            failures.append(f"missing ai_analysis.{field}")

    targeting = analysis.get("targeting")
    if not isinstance(targeting, dict):
        failures.append("ai_analysis.targeting should be an object")
    else:
        for field in REQUIRED_TARGETING_FIELDS:
            if field not in targeting:
                failures.append(f"missing ai_analysis.targeting.{field}")
        if not targeting.get("top_interests"):
            failures.append("targeting.top_interests should not be empty")
        if not targeting.get("behaviors"):
            failures.append("targeting.behaviors should not be empty")

    agents = analysis.get("agent_analysis")
    if not isinstance(agents, dict):
        failures.append("ai_analysis.agent_analysis should be an object")
    else:
        for agent in ["evidence_synthesizer", "meta_targeting_agent", "hook_agent", "virality_agent", "caption_copy_agent", "creative_diagnosis_agent"]:
            if agent not in agents:
                failures.append(f"missing agent_analysis.{agent}")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Campaign Optimizer JSON response contract.")
    parser.add_argument("response_json", type=Path, help="Path to a saved /api/campaign-optimizer response JSON")
    args = parser.parse_args()

    payload = json.loads(args.response_json.read_text())
    failures = _failures_for_response(payload)
    if failures:
        print("Creative contract check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Creative contract check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
