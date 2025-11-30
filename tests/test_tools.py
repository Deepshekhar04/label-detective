def test_canonicalize_e_number():
    """Test E-number canonicalization."""
    result = tools.canonicalize_ingredient("E1520")
    assert result["canonical_name"] == "Propylene glycol"
    assert result["source"] == "local"


def test_canonicalize_common_allergen():
    """Test common allergen canonicalization."""
    result = tools.canonicalize_ingredient("Peanut Oil")
    assert result["canonical_name"] == "Peanut oil"
    assert result["source"] == "local"


def test_lookup_ingredient_local():
    """Test ingredient lookup from local database."""
    result = tools.lookup_ingredient("Peanut oil")
    assert "allergen" in result["tags"]
    assert result["confidence"] > 0.9
    assert len(result["evidence"]) > 0


def test_match_with_profile_severe_allergy():
    """Test profile matching with severe allergy."""
    user_profile = {
        "allergies": [
            {"name": "Peanut", "severity": "high", "canonical_name": "peanut"}
        ],
        "diet_tags": [],
        "sustainability_goals": [],
        "ingredient_blocklist": [],
    }

    ingredient_tags = ["allergen", "oil", "peanut"]

    result = tools.match_with_profile(ingredient_tags, user_profile)

    assert result["conflict_level"] == "avoid"
    assert result["severity"] == "high"
    assert "peanut" in result["reason"].lower()


def test_match_with_profile_vegan():
    """Test vegan diet matching."""
    user_profile = {
        "allergies": [],
        "diet_tags": ["vegan"],
        "sustainability_goals": [],
        "ingredient_blocklist": [],
    }

    ingredient_tags = ["animal-derived", "protein"]

    result = tools.match_with_profile(ingredient_tags, user_profile)

    assert result["conflict_level"] == "avoid"
    assert "vegan" in result["reason"].lower()


def test_match_with_profile_palm_oil_sustainability():
    """Test palm oil sustainability matching."""
    user_profile = {
        "allergies": [],
        "diet_tags": [],
        "sustainability_goals": ["avoid_palm_oil"],
        "ingredient_blocklist": [],
    }

    ingredient_tags = ["oil", "sustainability-concern", "palm"]

    result = tools.match_with_profile(ingredient_tags, user_profile)

    assert result["conflict_level"] in ["caution", "avoid"]
    assert (
        "palm oil" in result["reason"].lower()
        or "sustainability" in result["reason"].lower()
    )


def test_match_with_profile_no_conflicts():
    """Test profile matching with safe ingredients."""
    user_profile = {
        "allergies": [],
        "diet_tags": [],
        "sustainability_goals": [],
        "ingredient_blocklist": [],
    }

    ingredient_tags = ["sweetener", "natural"]

    result = tools.match_with_profile(ingredient_tags, user_profile)

    assert result["conflict_level"] == "none"


def test_suggest_alternatives():
    """Test alternative suggestions."""
    conflict_tags = ["palm", "sustainability-concern"]

    alternatives = tools.suggest_alternatives(conflict_tags, "oil")

    assert len(alternatives) > 0
    assert any(
        "coconut" in alt["product_name"].lower() or "palm-free" in alt["reason"].lower()
        for alt in alternatives
    )


def test_canonicalize_unknown_ingredient():
    """Test canonicalization of unknown ingredient."""
    result = tools.canonicalize_ingredient("XYZ123Unknown")

    # Should return capitalized version as fallback
    assert result["canonical_name"] == "Xyz123Unknown"
    assert result["source"] == "unknown"


def test_lookup_missing_ingredient():
    """Test lookup of missing ingredient."""
    result = tools.lookup_ingredient("NonExistentIngredient12345")

    # Should return minimal data
    assert "unknown" in result["tags"] or "lookup-failed" in result["tags"]
    assert result["confidence"] < 0.5


def test_blocklist_matching():
    """Test ingredient blocklist matching."""
    user_profile = {
        "allergies": [],
        "diet_tags": [],
        "sustainability_goals": [],
        "ingredient_blocklist": ["MSG", "artificial sweeteners"],
    }

    ingredient_tags = ["flavor-enhancer", "msg"]

    result = tools.match_with_profile(ingredient_tags, user_profile)

    assert result["conflict_level"] == "avoid"
    assert "blocked" in result["reason"].lower() or "msg" in result["reason"].lower()


def test_multiple_allergies():
    """Test multiple allergies in profile."""
    user_profile = {
        "allergies": [
            {"name": "Milk", "severity": "moderate", "canonical_name": "milk"},
            {"name": "Eggs", "severity": "high", "canonical_name": "eggs"},
        ],
        "diet_tags": [],
        "sustainability_goals": [],
        "ingredient_blocklist": [],
    }

    # Test with egg tags
    egg_tags = ["allergen", "animal-derived", "egg", "protein"]
    result = tools.match_with_profile(egg_tags, user_profile)

    assert result["conflict_level"] == "avoid"
    assert result["severity"] == "high"


def test_ocr_fallback():
    """Test OCR with fallback (when pytesseract not available)."""
    # Create a dummy image bytes
    dummy_image = b"fake_image_data"

    result = tools.ocr_image(dummy_image)

    # Should return some result (either real OCR or fallback)
    assert "text" in result
    assert "confidence" in result
    assert isinstance(result["confidence"], float)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
