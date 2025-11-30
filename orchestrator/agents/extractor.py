"""
Extractor Agent - Extracts and cleans ingredient text from images or raw input.
"""

from typing import Dict, List, Any
import re
from orchestrator import tools
from utils.logging_utils import get_logger

logger = get_logger("agents.extractor")


class ExtractorAgent:
    """Extracts and cleans ingredient lists from various input types."""

    def extract(self, input_type: str, raw_input: Any, trace_id: str) -> Dict[str, Any]:
        """
        Extract ingredients from input.

        Args:
            input_type: Type of input ("text", "image", "product_search")
            raw_input: Raw input data
            trace_id: Trace identifier

        Returns:
            Dictionary with extracted ingredients and metadata
        """
        if input_type == "image":
            return self._extract_from_image(raw_input, trace_id)
        elif input_type == "text":
            return self._extract_from_text(raw_input, trace_id)
        elif input_type == "product_search":
            return self._extract_from_product_search(raw_input, trace_id)
        else:
            logger.error(f"Unknown input type: {input_type}")
            return {
                "ingredients": [],
                "raw_text": "",
                "confidence": 0.0,
                "error": "Unknown input type",
            }

    def _extract_from_image(self, image_bytes: bytes, trace_id: str) -> Dict[str, Any]:
        """Extract from image using OCR."""
        logger.info(f"[{trace_id}] Extracting from image")

        # Call OCR tool
        ocr_result = tools.ocr_image(image_bytes)

        # Clean the extracted text
        cleaned_text = self._clean_text(ocr_result["text"])
        ingredients = self._parse_ingredients(cleaned_text)

        return {
            "ingredients": ingredients,
            "raw_text": ocr_result["text"],
            "cleaned_text": cleaned_text,
            "confidence": ocr_result["confidence"],
            "method": "ocr",
        }

    def _extract_from_text(self, raw_text: str, trace_id: str) -> Dict[str, Any]:
        """Extract from pasted text."""
        logger.info(f"[{trace_id}] Extracting from text")

        cleaned_text = self._clean_text(raw_text)
        ingredients = self._parse_ingredients(cleaned_text)

        return {
            "ingredients": ingredients,
            "raw_text": raw_text,
            "cleaned_text": cleaned_text,
            "confidence": 1.0,
            "method": "text",
        }

    def _extract_from_product_search(
        self, product_query: str, trace_id: str
    ) -> Dict[str, Any]:
        """Extract from product search (future feature)."""
        logger.warning(f"[{trace_id}] Product search not yet implemented")

        return {
            "ingredients": [],
            "raw_text": product_query,
            "confidence": 0.0,
            "error": "Product search not yet implemented",
        }

    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text by removing non-ingredient information.

        Args:
            text: Raw text

        Returns:
            Cleaned text containing only ingredients
        """
        # Remove common non-ingredient prefixes
        patterns_to_remove = [
            r"ingredients?\s*:",  # "Ingredients:"
            r"contains?\s*:",  # "Contains:"
            r"net\s+weight.+",  # "Net weight..."
            r"product\s+of.+",  # "Product of..."
            r"best\s+before.+",  # "Best before..."
            r"store\s+in.+",  # "Store in..."
            r"allergen\s+info.+",  # "Allergen info..."
        ]

        cleaned = text
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)

        # Remove extra whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return cleaned

    def _parse_ingredients(self, text: str) -> List[str]:
        """
        Parse ingredient list into individual ingredients.

        Args:
            text: Cleaned ingredient text

        Returns:
            List of individual ingredients
        """
        # Split by common delimiters
        ingredients = re.split(r"[,;]\s*", text)

        # Clean each ingredient
        cleaned_ingredients = []
        for ing in ingredients:
            ing = ing.strip()

            # Remove percentages and quantities in parentheses
            ing = re.sub(r"\([^)]*%[^)]*\)", "", ing)
            ing = re.sub(r"\([^)]*\)", "", ing)

            # Remove trailing periods
            ing = ing.rstrip(".")

            if ing and len(ing) > 1:  # Skip empty or single-char strings
                cleaned_ingredients.append(ing)

        return cleaned_ingredients
