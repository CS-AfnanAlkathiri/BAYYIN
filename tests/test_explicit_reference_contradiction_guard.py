from backend.main import analyze_one


def test_explicit_reference_with_contradictory_attached_claim_is_not_verified_match():
    result = analyze_one(
        "Allah said: there is no need to verify news from people you trust (Quran 49:6)",
        "en",
        "auto",
        allow_live=False,
    )
    assert result["status"] in {"context_needed", "citation_mismatch"}
    assert result["status"] != "source_match"
    assert result["review_required"] is True
    assert result["matches"][0]["reference"] == "Qur'an 49:6"


def test_reference_only_can_still_be_verified_as_reference():
    result = analyze_one("Quran 49:6", "en", "auto", allow_live=False)
    assert result["status"] == "source_match"
    assert result["matches"][0]["reference"] == "Qur'an 49:6"
