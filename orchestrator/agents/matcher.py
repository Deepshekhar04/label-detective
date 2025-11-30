"""
Matcher Agent -> Compares ingredients with user profile for personalized analysis.
"""

from typing import Dict, List, Any
from orchestrator import tools
from utils.logging_utils import get_logger

logger = get_logger("agents.matcher")


class MatcherAgent:
    """Matches ingredients against user profile for conflicts."""

    def match(
        self,
        ingredient_data: Dict[str, Dict],
        user_profile: Dict[str, Any],
        trace_id: str,
    ) -> Dict[str, Any]:
        """Match ingredients with user profile for personalized health verdicts."""
        logger.info(
            f"[{trace_id}] Matching {len(ingredient_data)} ingredients with user profile"
        )

        conflicts = []
        max_severity = "low"
        overall_verdict = "safe"
        requires_review = False

        for ingredient, facts in ingredient_data.items():
            tags = facts.get("tags", [])

            match_result = tools.match_with_profile(tags, user_profile)

            conflict_info = {
                "ingredient": ingredient,
                "tags": tags,
                "conflict_level": match_result["conflict_level"],
                "severity": match_result["severity"],
                "reason": match_result["reason"],
                "evidence": facts.get("evidence", []),
            }

            if match_result["conflict_level"] == "avoid":
                overall_verdict = "avoid"
                if match_result["severity"] == "high":
                    max_severity = "high"
                    requires_review = True  # High severity triggers HITL
                elif match_result["severity"] == "moderate" and max_severity != "high":
                    max_severity = "moderate"

            elif (
                match_result["conflict_level"] == "caution"
                and overall_verdict == "safe"
            ):
                overall_verdict = "caution"

            if match_result["conflict_level"] != "none":
                conflicts.append(conflict_info)

        return {
            "overall_verdict": overall_verdict,
            "max_severity": max_severity,
            "conflicts": conflicts,
            "safe_count": len(ingredient_data) - len(conflicts),
            "conflict_count": len(conflicts),
            "requires_review": requires_review,
        }
