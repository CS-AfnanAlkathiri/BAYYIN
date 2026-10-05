from backend import rag


def _match():
    return {
        "id": "quran-49-6",
        "reference": "Qur'an 49:6",
        "title_en": "Surah Al-Hujurat — Verse 6",
        "title_ar": "سورة الحجرات — الآية 6",
        "text_ar": "يَا أَيُّهَا الَّذِينَ آمَنُوا إِن جَاءَكُمْ فَاسِقٌ بِنَبَإٍ فَتَبَيَّنُوا",
        "text_en": "O you who have believed, if there comes to you a disobedient one with information, investigate...",
        "context_en": "This verse addresses verifying news before acting on it in a way that could harm people.",
        "source_url": "https://quranpedia.net/en/translations/49",
    }


def test_rag_falls_back_safely_when_provider_is_not_configured(monkeypatch):
    monkeypatch.setattr(rag, "RAG_API_BASE", "")
    monkeypatch.setattr(rag, "RAG_API_KEY", "")
    monkeypatch.setattr(rag, "RAG_MODEL", "")

    result = rag.generate_grounded_explanation(
        "Verify every news before acting",
        "en",
        "context_needed",
        [_match()],
    )

    assert result["used"] is False
    assert result["grounded"] is True
    assert result["failure_reason"] in {
        "rag_not_configured",
        "status_or_evidence_not_eligible",
    }

def test_rag_uses_only_admitted_evidence(monkeypatch):
    monkeypatch.setattr(rag, "RAG_API_BASE", "https://example.invalid/v1")
    monkeypatch.setattr(rag, "RAG_API_KEY", "test-key")
    monkeypatch.setattr(rag, "RAG_MODEL", "test-model")
    seen = {}

    def fake_call(messages):
        seen["messages"] = messages
        return "The wording is related to the verified source, but it is a paraphrase rather than an exact quotation."

    monkeypatch.setattr(rag, "_call_chat", fake_call)
    result = rag.generate_grounded_explanation("Verify every news before acting", "en", "context_needed", [_match()])
    assert result["used"] is True
    assert result["evidence_refs"] == ["Qur'an 49:6"]
    payload = seen["messages"][1]["content"]
    assert "Qur'an 49:6" in payload
    assert "source_url" in payload
    assert "Use ONLY the EVIDENCE" in seen["messages"][0]["content"]


def test_rag_rejects_ruling_style_generation(monkeypatch):
    monkeypatch.setattr(rag, "RAG_API_BASE", "https://example.invalid/v1")
    monkeypatch.setattr(rag, "RAG_API_KEY", "test-key")
    monkeypatch.setattr(rag, "RAG_MODEL", "test-model")
    monkeypatch.setattr(rag, "_call_chat", lambda messages: "Therefore it is halal.")
    result = rag.generate_grounded_explanation("A claim", "en", "context_needed", [_match()])
    assert result["used"] is False
    assert result["failure_reason"] == "generated_text_failed_safety_validation"


def test_rag_skips_specialist_review(monkeypatch):
    monkeypatch.setattr(rag, "RAG_API_BASE", "https://example.invalid/v1")
    monkeypatch.setattr(rag, "RAG_API_KEY", "test-key")
    monkeypatch.setattr(rag, "RAG_MODEL", "test-model")
    result = rag.generate_grounded_explanation("What is the ruling for me?", "en", "specialist_review", [_match()])
    assert result["used"] is False
    assert result["failure_reason"] == "status_or_evidence_not_eligible"
