from pathlib import Path

from backend.main import analyze_one, demo, judge_evidence


def test_semantic_demo_makes_ai_value_visible():
    for lang in ("ar", "en"):
        text = demo("context", lang)["text"]
        result = analyze_one(text, lang, "auto", allow_live=False)
        assert result["status"] == "context_needed"
        assert result["matches"][0]["id"] == "hadith-muslim-5"
        ai = result["ai_explanation"]
        assert ai["used"] is True
        assert ai["contribution"] == "semantic_recovery"
        assert ai["value_added_over_lexical_baseline"] is True


def test_abstention_explains_that_ai_candidate_was_blocked():
    result = analyze_one("Fasting in Ramadan is obligatory", "en", "auto", allow_live=False)
    assert result["status"] == "insufficient_evidence"
    assert result["matches"] == []
    assert result["ai_explanation"]["gate"] == "blocked_by_relevance_gate"


def test_frontend_exposes_ai_role_and_contribution_panel():
    html = Path("frontend/index.html").read_text(encoding="utf-8")
    js = Path("frontend/assets/app.js").read_text(encoding="utf-8")
    assert "ai-role-card" in html
    assert "process-box" in html
    assert "semantic_recovery" in js
    assert "How did BAYYIN reach this result?" in js


def test_judge_evidence_is_reproducible_and_bounded():
    evidence = judge_evidence()
    assert evidence["implemented_now"]["ai_role"].startswith("Meaning-level retrieval")
    assert evidence["measurable_evidence"]["ai_vs_lexical"]["cases"] >= 40
    assert any('free-form religious answer generation' in x for x in evidence['future_work_not_claimed_as_implemented'])
