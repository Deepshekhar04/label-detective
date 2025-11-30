"""
Lookup Agent -> Knowledge retrieval specialist with parallel execution.
"""

import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any
from orchestrator import tools
from utils.logging_utils import get_logger

logger = get_logger("agents.lookup")


class LookupAgent:
    """Looks up ingredient facts from local DB or web sources."""

    def __init__(self):
        self.max_parallel = int(os.getenv("MAX_PARALLEL_LOOKUPS", "6"))

    def lookup_all(
        self, canonical_ingredients: List[str], trace_id: str
    ) -> Dict[str, Any]:
        """Parallel ingredient lookup for faster processing."""
        logger.info(
            f"[{trace_id}] Looking up {len(canonical_ingredients)} ingredients (max parallel: {self.max_parallel})"
        )

        ingredient_data = {}

        with ThreadPoolExecutor(max_workers=self.max_parallel) as executor:
            futures = {
                executor.submit(self._lookup_single, ingredient, trace_id): ingredient
                for ingredient in canonical_ingredients
            }

            for future in futures:
                ingredient = futures[future]
                try:
                    result = future.result()
                    ingredient_data[ingredient] = result
                except Exception as e:
                    logger.error(f"[{trace_id}] Lookup failed for {ingredient}: {e}")
                    ingredient_data[ingredient] = {
                        "tags": ["lookup-error"],
                        "summary": f"Failed to retrieve information: {str(e)}",
                        "evidence": [],
                        "confidence": 0.0,
                    }

        return {
            "ingredient_data": ingredient_data,
            "lookup_count": len(ingredient_data),
            "avg_confidence": (
                sum(d.get("confidence", 0) for d in ingredient_data.values())
                / len(ingredient_data)
                if ingredient_data
                else 0.0
            ),
        }

    def _lookup_single(self, ingredient: str, trace_id: str) -> Dict[str, Any]:
        """Lookup a single ingredient."""
        return tools.lookup_ingredient(ingredient)
