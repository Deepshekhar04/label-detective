"""
Tool function implementations for Label Detective agents.
Provides OCR, ingredient lookup, profile matching, and alternative suggestions.
"""

import os
import csv
import json
import base64
import re
from io import BytesIO
from typing import Dict, List, Any, Optional
from PIL import Image
import requests
from utils.logging_utils import get_logger
from utils import firestore_client as db

logger = get_logger("tools")

# Load local ingredient data
INGREDIENT_MAP = {}
INGREDIENT_FACTS = {}


def _load_ingredient_data():
    """Load local CSV and JSON data files."""
    global INGREDIENT_MAP, INGREDIENT_FACTS

    # Load ingredient map CSV
    map_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "ingredient_map.csv"
    )
    try:
        with open(map_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                INGREDIENT_MAP[row["raw_name"].lower()] = {
                    "canonical_name": row["canonical_name"],
                    "synonyms": row["synonyms"].split("|") if row["synonyms"] else [],
                    "category": row["category"],
                }
        logger.info(f"Loaded {len(INGREDIENT_MAP)} ingredients from CSV")
    except Exception as e:
        logger.error(f"Failed to load ingredient map: {e}")

    # Load ingredient facts JSON
    facts_path = os.path.join(
        os.path.dirname(__file__), "..", "data", "ingredient_facts.json"
    )
    try:
        with open(facts_path, "r", encoding="utf-8") as f:
            INGREDIENT_FACTS = json.load(f)
        logger.info(f"Loaded {len(INGREDIENT_FACTS)} ingredient facts from JSON")
    except Exception as e:
        logger.error(f"Failed to load ingredient facts: {e}")


# Load data on module import
_load_ingredient_data()


def ocr_image(image_bytes: bytes) -> Dict[str, Any]:
    """Extract text from image using Google Vision API."""
    try:
        from google.cloud import vision

        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=image_bytes)

        response = client.text_detection(image=image)
        texts = response.text_annotations

        if texts:
            detected_text = texts[0].description
            confidence = 0.9

            logger.info(f"Google Vision OCR extracted {len(detected_text)} characters")
            return {"text": detected_text.strip(), "confidence": confidence}
        else:
            logger.warning("Google Vision OCR found no text")
            return {"text": "", "confidence": 0.0}

    except Exception as e:
        logger.error(f"Google Vision OCR failed: {e}")
        return {"text": "", "confidence": 0.0}


def canonicalize_ingredient(raw_name: str) -> Dict[str, Any]:
    """Map raw ingredient name to canonical form (e.g., E120 -> Cochineal)."""
    # Clean the raw name
    clean_name = raw_name.strip().lower()
    clean_name = re.sub(r"[^a-z0-9\s-]", "", clean_name)

    # Check local map first
    if clean_name in INGREDIENT_MAP:
        data = INGREDIENT_MAP[clean_name]
        return {
            "canonical_name": data["canonical_name"],
            "synonyms": data["synonyms"],
            "source": "local",
        }

    # Check if it's a partial match (e.g., "e120" matches "E120")
    for key, data in INGREDIENT_MAP.items():
        if clean_name in key or key in clean_name:
            return {
                "canonical_name": data["canonical_name"],
                "synonyms": data["synonyms"],
                "source": "local",
            }

    # Fallback: return capitalized version as canonical
    canonical = raw_name.strip().title()
    logger.warning(f"No canonical mapping found for '{raw_name}', using '{canonical}'")

    return {"canonical_name": canonical, "synonyms": [], "source": "unknown"}


def lookup_ingredient(canonical_name: str) -> Dict[str, Any]:
    """Retrieve ingredient facts and evidence from local database or web search."""
    # Check local facts first
    if canonical_name in INGREDIENT_FACTS:
        return INGREDIENT_FACTS[canonical_name]

    # Try case-insensitive match
    for key, value in INGREDIENT_FACTS.items():
        if key.lower() == canonical_name.lower():
            return value

    # Use web search for unknown ingredients
    return _lookup_via_web_search(canonical_name)


def _lookup_via_web_search(ingredient_name: str) -> Dict[str, Any]:
    """
    Lookup ingredient via Google Custom Search API with Wikipedia fallback.

    Args:
        ingredient_name: Ingredient to search for

    Returns:
        Ingredient facts dictionary
    """
    api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")

    if not api_key or not engine_id:
        logger.warning("Google Custom Search not configured, using Wikipedia fallback")
        wikipedia_url = (
            f"https://en.wikipedia.org/wiki/{ingredient_name.replace(' ', '_')}"
        )
        return {
            "tags": ["unknown", "web-lookup"],
            "summary": f"Web information about {ingredient_name}. Verify from authoritative sources.",
            "evidence": [
                {"url": wikipedia_url, "title": f"{ingredient_name} - Wikipedia"},
                {"url": "https://www.fda.gov/food", "title": "FDA Food Information"},
            ],
            "confidence": 0.6,
        }

    try:
        # Use Google Custom Search API
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": api_key,
            "cx": engine_id,
            "q": f"{ingredient_name} food ingredient safety",
            "num": 3,
        }

        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()

        evidence = [
            {"url": item["link"], "title": item["title"]}
            for item in data.get("items", [])[:3]
        ]

        logger.info(
            f"Google Search found {len(evidence)} results for {ingredient_name}"
        )

        return {
            "tags": ["web-lookup"],
            "summary": f"Web information about {ingredient_name} from trusted sources.",
            "evidence": evidence,
            "confidence": 0.7,
        }

    except Exception as e:
        logger.error(f"Google Custom Search failed: {e}")
        # Fallback to Wikipedia
        wikipedia_url = (
            f"https://en.wikipedia.org/wiki/{ingredient_name.replace(' ', '_')}"
        )
        return {
            "tags": ["lookup-failed"],
            "summary": f"Search failed, showing fallback information about {ingredient_name}.",
            "evidence": [
                {"url": wikipedia_url, "title": f"{ingredient_name} - Wikipedia"}
            ],
            "confidence": 0.4,
        }


def match_with_profile(
    ingredient_tags: List[str], user_profile: Dict[str, Any]
) -> Dict[str, Any]:
    """Compare ingredient tags with user profile to detect conflicts."""
    conflicts = []
    max_severity = "low"
    conflict_level = "none"

    # Check allergies
    allergies = user_profile.get("allergies", [])
    for allergy in allergies:
        allergy_name = allergy.get("canonical_name", allergy.get("name", "")).lower()

        # Check if any tag matches the allergy
        for tag in ingredient_tags:
            if allergy_name in tag.lower() or tag.lower() in allergy_name:
                severity = allergy.get("severity", "moderate")
                conflicts.append(
                    f"Contains allergen: {allergy_name} (severity: {severity})"
                )
                conflict_level = "avoid"
                if severity == "high":
                    max_severity = "high"
                elif severity == "moderate" and max_severity != "high":
                    max_severity = "moderate"

    # Check diet tags
    diet_tags = user_profile.get("diet_tags", [])
    for diet_tag in diet_tags:
        if diet_tag == "vegan" and "animal-derived" in ingredient_tags:
            conflicts.append(
                "Not suitable for vegan diet (contains animal-derived ingredient)"
            )
            conflict_level = "avoid" if conflict_level != "avoid" else conflict_level
            if max_severity == "low":
                max_severity = "moderate"

        if diet_tag == "vegetarian" and "animal-derived" in ingredient_tags:
            # Check if it's meat/fish specifically
            if (
                "fish" in ingredient_tags
                or "shellfish" in ingredient_tags
                or "meat" in ingredient_tags
            ):
                conflicts.append("Not suitable for vegetarian diet")
                conflict_level = (
                    "avoid" if conflict_level != "avoid" else conflict_level
                )
                if max_severity == "low":
                    max_severity = "moderate"

        if diet_tag == "gluten-free" and "gluten" in ingredient_tags:
            conflicts.append("Contains gluten")
            conflict_level = "avoid"
            if max_severity != "high":
                max_severity = "moderate"

    # Check sustainability goals
    sustainability_goals = user_profile.get("sustainability_goals", [])
    for goal in sustainability_goals:
        if goal == "avoid_palm_oil" and "palm" in " ".join(ingredient_tags).lower():
            conflicts.append("Contains palm oil (sustainability concern)")
            conflict_level = "caution" if conflict_level == "none" else conflict_level

        if goal == "avoid_palm_oil" and "sustainability-concern" in ingredient_tags:
            conflicts.append("Sustainability concern flagged")
            conflict_level = "caution" if conflict_level == "none" else conflict_level

    # Check blocklist
    blocklist = user_profile.get("ingredient_blocklist", [])
    for blocked in blocklist:
        for tag in ingredient_tags:
            if blocked.lower() in tag.lower():
                conflicts.append(f"Blocked ingredient: {blocked}")
                conflict_level = "avoid"
                if max_severity != "high":
                    max_severity = "moderate"

    # Synthetic dyes check
    if any(dye in ingredient_tags for dye in ["dye", "synthetic"]):
        if "avoid_synthetic_dyes" in user_profile.get("preferences", []):
            conflicts.append("Contains synthetic dye")
            conflict_level = "caution" if conflict_level == "none" else conflict_level

    reason = "; ".join(conflicts) if conflicts else "No conflicts detected"

    return {
        "conflict_level": conflict_level,
        "severity": max_severity,
        "reason": reason,
    }


def suggest_alternatives(
    conflict_tags: List[str], category: str
) -> List[Dict[str, Any]]:
    """Suggest alternative products based on detected conflicts."""
    alternatives = []

    # Simple rule-based alternatives
    if "palm" in " ".join(conflict_tags).lower():
        alternatives.append(
            {
                "product_name": "Coconut oil-based alternative",
                "reason": "Palm oil-free, sustainable",
                "link": "",
            }
        )

    if "allergen" in " ".join(conflict_tags).lower():
        alternatives.append(
            {
                "product_name": "Allergen-free alternative",
                "reason": "Free from common allergens",
                "link": "",
            }
        )

    if "animal-derived" in conflict_tags:
        alternatives.append(
            {
                "product_name": "Vegan alternative",
                "reason": "100% plant-based",
                "link": "",
            }
        )

    if "synthetic" in " ".join(conflict_tags).lower() or "dye" in conflict_tags:
        alternatives.append(
            {
                "product_name": "Naturally colored alternative",
                "reason": "Uses only natural coloring",
                "link": "",
            }
        )

    return alternatives[:3]  # Return top 3


def save_user_event(user_id: str, event_dict: Dict[str, Any]) -> None:
    """
    Save event to session trace (deprecated - handled by orchestrator).
    """
    logger.info(f"Event logged for user {user_id}: {event_dict.get('type', 'unknown')}")


def create_pending_review(user_id: str, session_id: str, reason: str) -> str:
    """
    Create a pending review for human-in-the-loop confirmation.

    Args:
        user_id: User identifier
        session_id: Session requiring review
        reason: Reason for review

    Returns:
        review_id
    """
    return db.create_pending_review(user_id, session_id, reason)


def fetch_memory(
    user_id: str, filters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Fetch long-term memory facts for the user.

    Args:
        user_id: User identifier
        filters: Optional filters

    Returns:
        Dictionary with memory facts
    """
    facts = db.fetch_memories(user_id, filters)
    return {"facts": facts, "count": len(facts)}


def write_memory(user_id: str, memory_item: Dict[str, Any]) -> None:
    """
    Write long-term memory fact for persistent storage.

    Args:
        user_id: User identifier
        memory_item: Memory fact to store
    """
    db.save_memory(user_id, memory_item)
    logger.info(f"Wrote memory for user {user_id}: {memory_item.get('type')}")
