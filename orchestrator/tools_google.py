"""
Google Cloud service integrations for Label Detective.
This file contains the Google Vision API and Custom Search implementations.
"""

import os
from typing import Dict, Any
from utils.logging_utils import get_logger

logger = get_logger("tools_google")


def ocr_with_google_vision(image_bytes: bytes) -> Dict[str, Any]:
    """Extract text using Google Vision API."""
    try:
        from google.cloud import vision

        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=image_bytes)

        response = client.text_detection(image=image)
        texts = response.text_annotations

        if texts:
            detected_text = texts[0].description
            confidence = 0.9  # Google Vision doesn't provide per-word confidence

            logger.info(f"Google Vision OCR extracted {len(detected_text)} characters")
            return {"text": detected_text.strip(), "confidence": confidence}
        else:
            logger.warning("Google Vision OCR found no text")
            return {"text": "", "confidence": 0.0}

    except Exception as e:
        logger.error(f"Google Vision OCR failed: {e}")
        return {"text": "", "confidence": 0.0}


def search_with_google_custom_search(query: str) -> Dict[str, Any]:
    """Search using Google Custom Search API."""
    api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")

    if not api_key or not engine_id:
        logger.warning("Google Custom Search not configured")
        return {"items": []}

    try:
        import requests

        url = "https://www.googleapis.com/customsearch/v1"
        params = {"key": api_key, "cx": engine_id, "q": query, "num": 3}

        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()

        data = response.json()
        return data

    except Exception as e:
        logger.error(f"Google Custom Search failed: {e}")
        return {"items": []}
