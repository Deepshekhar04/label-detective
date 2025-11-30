"""
Explain Agent - Formats verdict and generates user-friendly explanations.
"""

from typing import Dict, List, Any
from orchestrator import tools
from utils.logging_utils import get_logger

logger = get_logger("agents.explain")


class ExplainAgent:
    """Formats verdicts and explanations for users."""

    def explain(
        self,
        match_result: Dict[str, Any],
        ingredient_data: Dict[str, Dict],
        user_profile: Dict[str, Any],
        trace_id: str,
    ) -> Dict[str, Any]:
        """
        Generate user-facing explanation with adaptive detail level.

        Args:
            match_result: Result from Matcher Agent
            ingredient_data: Ingredient facts from Lookup Agent
            user_profile: User profile with explain_level preference
            trace_id: Trace identifier

        Returns:
            Formatted explanation with verdict, details, and alternatives
        """
        logger.info(
            f"[{trace_id}] Generating explanation (level: {user_profile.get('explain_level', 'detailed')})"
        )

        explain_level = user_profile.get("explain_level", "detailed")
        verdict = match_result["overall_verdict"]
        conflicts = match_result["conflicts"]

        # Generate explanation based on level
        if explain_level == "brief":
            explanation = self._generate_brief(verdict, conflicts)
        elif explain_level == "citations_only":
            explanation = self._generate_citations_only(conflicts)
        else:  # detailed
            explanation = self._generate_detailed(verdict, conflicts, match_result)

        # Generate alternatives for conflicting ingredients
        alternatives = []
        if conflicts:
            conflict_tags = []
            for conflict in conflicts:
                conflict_tags.extend(conflict["tags"])

            alternatives = tools.suggest_alternatives(conflict_tags, "food")

        # Build ingredient table
        ingredient_table = self._build_ingredient_table(
            ingredient_data, match_result["conflicts"]
        )

        return {
            "verdict": verdict,
            "severity": match_result.get("max_severity", "low"),
            "summary": explanation["summary"],
            "details": explanation["details"],
            "ingredient_table": ingredient_table,
            "alternatives": alternatives,
            "evidence_urls": explanation.get("evidence_urls", []),
            "conflict_count": len(conflicts),
            "safe_count": match_result.get("safe_count", 0),
        }

    def _generate_brief(self, verdict: str, conflicts: List[Dict]) -> Dict[str, Any]:
        """Generate brief explanation."""
        if verdict == "safe":
            summary = "✓ Safe - No conflicts detected"
        elif verdict == "caution":
            summary = f"⚠ Caution - {len(conflicts)} ingredient(s) flagged"
        else:  # avoid
            summary = f"✗ Avoid - {len(conflicts)} conflicting ingredient(s)"

        return {"summary": summary, "details": ""}

    def _generate_citations_only(self, conflicts: List[Dict]) -> Dict[str, Any]:
        """Generate citations-only explanation."""
        evidence_urls = []
        for conflict in conflicts:
            evidence_urls.extend(conflict.get("evidence", []))

        return {
            "summary": f"Found {len(conflicts)} conflict(s). See evidence links below.",
            "details": "",
            "evidence_urls": evidence_urls,
        }

    def _generate_detailed(
        self, verdict: str, conflicts: List[Dict], match_result: Dict
    ) -> Dict[str, Any]:
        """Generate detailed explanation."""
        if verdict == "safe":
            summary = "✓ This product appears safe based on your profile."
            details = f"All {match_result.get('safe_count', 0)} ingredients checked. No conflicts detected."

        elif verdict == "caution":
            summary = f"⚠ Caution recommended - {len(conflicts)} ingredient(s) may be of concern."
            details_list = []
            for conflict in conflicts:
                details_list.append(
                    f"• **{conflict['ingredient']}**: {conflict['reason']}"
                )
            details = "\n".join(details_list)

        else:  # avoid
            summary = f"✗ Not recommended - {len(conflicts)} conflicting ingredient(s) detected."
            details_list = []
            for conflict in conflicts:
                severity_badge = "🔴" if conflict["severity"] == "high" else "🟡"
                details_list.append(
                    f"{severity_badge} **{conflict['ingredient']}** (Severity: {conflict['severity']})\n"
                    f"   Reason: {conflict['reason']}"
                )
            details = "\n\n".join(details_list)

        return {"summary": summary, "details": details}

    def _build_ingredient_table(
        self, ingredient_data: Dict[str, Dict], conflicts: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Build per-ingredient table for display."""
        conflict_map = {c["ingredient"]: c for c in conflicts}

        table = []
        for ingredient, facts in ingredient_data.items():
            conflict = conflict_map.get(ingredient)

            row = {
                "canonical_name": ingredient,
                "tags": ", ".join(facts.get("tags", [])),
                "conflict": conflict["conflict_level"] if conflict else "none",
                "severity": conflict["severity"] if conflict else "",
                "reason": conflict["reason"] if conflict else "OK",
                "evidence": facts.get("evidence", []),
            }
            table.append(row)

        # Sort by conflict level
        priority = {"avoid": 0, "caution": 1, "none": 2}
        table.sort(key=lambda x: priority.get(x["conflict"], 3))

        return table
