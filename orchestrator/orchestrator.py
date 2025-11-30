"""
Main Orchestrator for Label Detective.
Coordinates all agents and manages session flow for ingredient analysis.
"""

import time
from datetime import datetime
from typing import Dict, Any, Optional
from orchestrator.agents.extractor import ExtractorAgent
from orchestrator.agents.normalizer import NormalizerAgent
from orchestrator.agents.lookup import LookupAgent
from orchestrator.agents.matcher import MatcherAgent
from orchestrator.agents.explain import ExplainAgent
from orchestrator import tools
from utils.logging_utils import get_logger, create_trace_id
from utils import firestore_client as db

logger = get_logger("orchestrator")


class LabelDetectiveOrchestrator:
    """
    Main orchestrator coordinating sub-agents for ingredient analysis.
    """

    def __init__(self):
        self.extractor = ExtractorAgent()
        self.normalizer = NormalizerAgent()
        self.lookup = LookupAgent()
        self.matcher = MatcherAgent()
        self.explainer = ExplainAgent()

    def run_scan(
        self,
        user_id: str,
        input_payload: Dict[str, Any],
        session_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute a complete scan workflow with full session tracking.

        Args:
            user_id: User identifier
            input_payload: Input data containing:
                - input_type: "text"|"image"|"product_search"
                - raw_input: actual input data
                - user_profile: user preferences and constraints
            session_config: Optional configuration

        Returns:
            Complete scan result with verdict, trace, and review status
        """
        # Initialize session
        trace_id = create_trace_id()
        session_id = create_trace_id()

        session = {
            "session_id": session_id,
            "trace_id": trace_id,
            "user_id": user_id,
            "input_type": input_payload.get("input_type"),
            "created_at": datetime.utcnow().isoformat(),
            "events": [],
        }

        logger.info(
            f"[{trace_id}] Starting scan session {session_id} for user {user_id}"
        )

        try:
            # Step 1: Extract ingredients
            extraction_start = time.time()
            extraction_result = self.extractor.extract(
                input_payload["input_type"], input_payload["raw_input"], trace_id
            )
            extraction_duration = (time.time() - extraction_start) * 1000

            session["events"].append(
                {
                    "agent": "extractor",
                    "duration_ms": extraction_duration,
                    "result_summary": f"Extracted {len(extraction_result.get('ingredients', []))} ingredients",
                    "confidence": extraction_result.get("confidence", 0.0),
                }
            )

            ingredients = extraction_result.get("ingredients", [])
            if not ingredients:
                logger.warning(f"[{trace_id}] No ingredients extracted")
                return self._create_empty_result(
                    session_id, trace_id, "No ingredients found in input"
                )

            # Step 2: Normalize ingredients
            normalization_start = time.time()
            normalization_result = self.normalizer.normalize(ingredients, trace_id)
            normalization_duration = (time.time() - normalization_start) * 1000

            session["events"].append(
                {
                    "agent": "normalizer",
                    "duration_ms": normalization_duration,
                    "result_summary": f"Normalized {len(normalization_result['canonical_ingredients'])} ingredients",
                    "success_rate": normalization_result["success_rate"],
                }
            )

            canonical_ingredients = normalization_result["canonical_ingredients"]

            # Step 3: Lookup ingredient facts (parallel)
            lookup_start = time.time()
            lookup_result = self.lookup.lookup_all(canonical_ingredients, trace_id)
            lookup_duration = (time.time() - lookup_start) * 1000

            session["events"].append(
                {
                    "agent": "lookup",
                    "duration_ms": lookup_duration,
                    "result_summary": f"Looked up {lookup_result['lookup_count']} ingredients",
                    "avg_confidence": lookup_result["avg_confidence"],
                }
            )

            ingredient_data = lookup_result["ingredient_data"]

            # Step 4: Match with user profile
            user_profile = input_payload.get("user_profile", {})

            matching_start = time.time()
            match_result = self.matcher.match(ingredient_data, user_profile, trace_id)
            matching_duration = (time.time() - matching_start) * 1000

            session["events"].append(
                {
                    "agent": "matcher",
                    "duration_ms": matching_duration,
                    "result_summary": f"Verdict: {match_result['overall_verdict']}, Conflicts: {len(match_result['conflicts'])}",
                    "requires_review": match_result["requires_review"],
                }
            )

            # Step 5: Check if HITL review is needed
            review_id = None
            if match_result["requires_review"]:
                logger.warning(
                    f"[{trace_id}] High severity detected, creating pending review"
                )
                review_id = tools.create_pending_review(
                    user_id,
                    session_id,
                    f"High severity allergen detected: {match_result['max_severity']}",
                )

                session["events"].append(
                    {
                        "agent": "hitl",
                        "review_id": review_id,
                        "result_summary": "Pending human review",
                    }
                )

            # Step 6: Generate explanation
            explain_start = time.time()
            explanation = self.explainer.explain(
                match_result, ingredient_data, user_profile, trace_id
            )
            explain_duration = (time.time() - explain_start) * 1000

            session["events"].append(
                {
                    "agent": "explainer",
                    "duration_ms": explain_duration,
                    "result_summary": f"Generated {user_profile.get('explain_level', 'detailed')} explanation",
                }
            )

            # Finalize session
            session["final_verdict"] = explanation
            session["raw_input"] = str(input_payload.get("raw_input", ""))[
                :500
            ]  # Truncate

            # Save session to database
            db.save_session(session)

            # If not requiring review, save to history automatically
            if not match_result["requires_review"]:
                history_entry = {
                    "session_id": session_id,
                    "summary": f"{len(ingredients)} ingredients analyzed",
                    "verdict": explanation["verdict"],
                    "timestamp": session["created_at"],
                }
                db.save_scan_history(user_id, history_entry)

            # Return complete result
            total_duration = sum(e.get("duration_ms", 0) for e in session["events"])

            logger.info(f"[{trace_id}] Scan completed in {total_duration:.2f}ms")

            return {
                "session_id": session_id,
                "trace_id": trace_id,
                "final_verdict": explanation,
                "trace": session["events"],
                "requires_review": match_result["requires_review"],
                "review_id": review_id,
                "extraction_result": extraction_result,
                "total_duration_ms": total_duration,
            }

        except Exception as e:
            logger.error(f"[{trace_id}] Scan failed: {e}", exc_info=True)
            session["events"].append(
                {
                    "agent": "orchestrator",
                    "error": str(e),
                    "result_summary": "Scan failed",
                }
            )
            db.save_session(session)

            return {
                "session_id": session_id,
                "trace_id": trace_id,
                "error": str(e),
                "trace": session["events"],
            }

    def _create_empty_result(
        self, session_id: str, trace_id: str, reason: str
    ) -> Dict[str, Any]:
        """Create an empty result when no ingredients found."""
        return {
            "session_id": session_id,
            "trace_id": trace_id,
            "final_verdict": {
                "verdict": "safe",
                "summary": reason,
                "details": "",
                "ingredient_table": [],
                "alternatives": [],
                "conflict_count": 0,
                "safe_count": 0,
            },
            "trace": [],
            "requires_review": False,
        }
