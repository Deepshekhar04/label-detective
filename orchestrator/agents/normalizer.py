"""
Normalizer Agent -> Maps raw ingredient names to canonical names.
"""

from typing import Dict, List, Any
from orchestrator import tools
from utils.logging_utils import get_logger

logger = get_logger("agents.normalizer")


class NormalizerAgent:
    """Normalizes ingredient names to canonical forms."""

    def normalize(self, ingredients: List[str], trace_id: str) -> Dict[str, Any]:
        """Normalize ingredient list to canonical names."""
        logger.info(f"[{trace_id}] Normalizing {len(ingredients)} ingredients")

        mapping = {}
        canonical_ingredients = []
        unmapped = []

        for raw_name in ingredients:
            result = tools.canonicalize_ingredient(raw_name)
            canonical_name = result["canonical_name"]

            mapping[raw_name] = {
                "canonical_name": canonical_name,
                "synonyms": result["synonyms"],
                "source": result["source"],
            }

            canonical_ingredients.append(canonical_name)

            if result["source"] == "unknown":
                unmapped.append(raw_name)

        if unmapped:
            logger.warning(
                f"[{trace_id}] {len(unmapped)} ingredients unmapped: {unmapped}"
            )

        return {
            "mapping": mapping,
            "canonical_ingredients": canonical_ingredients,
            "unmapped": unmapped,
            "success_rate": (
                (len(ingredients) - len(unmapped)) / len(ingredients)
                if ingredients
                else 1.0
            ),
        }
