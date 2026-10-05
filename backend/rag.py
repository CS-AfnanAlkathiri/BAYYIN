from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Dict, Iterable, List, Optional

RAG_API_BASE = os.environ.get("BAYYIN_RAG_API_BASE", "").strip().rstrip("/")
RAG_API_KEY = os.environ.get("BAYYIN_RAG_API_KEY", "").strip()
RAG_MODEL = os.environ.get("BAYYIN_RAG_MODEL", "").strip()
RAG_TIMEOUT = float(os.environ.get("BAYYIN_RAG_TIMEOUT", "12"))
RAG_MAX_TOKENS = int(os.environ.get("BAYYIN_RAG_MAX_TOKENS", "220"))

_ALLOWED_STATUSES = {"source_match", "source_linked", "context_needed", "citation_mismatch"}


def _configured() -> bool:
    return bool(RAG_API_BASE and RAG_MODEL and RAG_API_KEY)


def status() -> Dict[str, Any]:
    return {
        "implemented": True,
        "enabled": _configured(),
        "mode": "automatic",
        "provider": "OpenAI-compatible chat-completions endpoint" if RAG_API_BASE else None,
        "model": RAG_MODEL or None,
        "retrieval_sources": ["approved local knowledge layer", "Quranpedia", "QuranEnc", "Dorar.net"],
        "generation_policy": "The generator receives only evidence already retrieved and admitted by BAYYIN's verification gates.",
        "boundary": "RAG generates a short grounded explanation only; it does not generate Qur'an, hadith text, hadith grading, or religious rulings.",
        "fallback": "If RAG is unavailable or fails validation, BAYYIN returns the verified evidence report without generated explanation.",
    }


def _clean(value: Any, limit: int = 1800) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit]


def _evidence_rows(matches: Iterable[Dict[str, Any]], lang: str) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for item in list(matches)[:2]:
        reference = _clean(item.get("reference") or item.get("id"), 180)
        title = _clean(item.get("title_ar") if lang == "ar" else item.get("title_en"), 220)
        primary = _clean(item.get("text_ar"), 1200)
        rendering = _clean(item.get("text_en"), 1200)
        context = _clean(item.get("context_ar") if lang == "ar" else item.get("context_en"), 900)
        grading = _clean(item.get("grading_ar") if lang == "ar" else item.get("grading_en"), 240)
        url = _clean(item.get("source_url"), 400)
        rows.append({
            "reference": reference,
            "title": title,
            "primary_text": primary,
            "approved_rendering": rendering,
            "context_note": context,
            "hadith_grading_if_documented": grading,
            "source_url": url,
        })
    return rows


def _messages(claim: str, lang: str, result_status: str, evidence: List[Dict[str, str]]) -> List[Dict[str, str]]:
    language_instruction = "Write in Arabic." if lang == "ar" else "Write in English."
    system = (
        "You are the bounded explanation layer inside BAYYIN, an evidence-verification tool for Islamic digital content. "
        "Use ONLY the EVIDENCE supplied in the user message. Do not use outside knowledge or model memory. "
        "Do not invent Qur'an wording, hadith wording, grading, tafsir, legal rulings, or source details. "
        "Do not issue a fatwa or decide halal/haram. Do not claim that semantic similarity proves religious meaning. "
        "Explain only the relationship that the verified evidence report already supports. "
        "If the status is context_needed, explicitly preserve uncertainty in natural language. If the status is citation_mismatch, say the cited source was found but the attached claim is not supported by the verified comparison. "
        "Do not repeat internal status labels such as context_needed, citation_mismatch, source_match, or specialist_review. "
        "Return at most two short sentences. Do not include URLs or new citations. " + language_instruction
    )
    payload = {
        "claim": claim,
        "verified_status": result_status,
        "evidence": evidence,
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "EVIDENCE BUNDLE:\n" + json.dumps(payload, ensure_ascii=False)},
    ]


def _call_chat(messages: List[Dict[str, str]]) -> str:
    endpoint = RAG_API_BASE
    if not endpoint.endswith("/chat/completions"):
        endpoint += "/chat/completions"
    body = json.dumps({
        "model": RAG_MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_completion_tokens": RAG_MAX_TOKENS,
    }).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            "Authorization": f"Bearer {RAG_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "BAYYIN/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=RAG_TIMEOUT) as response:
        payload = json.loads(response.read().decode("utf-8"))
    choices = payload.get("choices") or []
    if not choices:
        raise ValueError("generator returned no choices")
    content = ((choices[0].get("message") or {}).get("content") or "").strip()
    if not content:
        raise ValueError("generator returned empty content")
    return content


def _validate_generated(text: str) -> Optional[str]:
    text = re.sub(r"https?://\S+", "", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    if not text or len(text) > 800:
        return None
    # RAG is explanatory, not a ruling layer. Reject common direct-ruling forms.
    blocked = [
        r"\b(?:therefore|thus)\s+(?:it\s+is\s+)?(?:halal|haram)\b",
        r"\b(?:fatwa|i rule that)\b",
        r"(?:إذن|وعليه)\s+(?:ف?هو|ف?هي)?\s*(?:حلال|حرام)",
        r"\b(?:حلال|حرام)\s+قطع[ًاا]\b",
    ]
    if any(re.search(p, text, flags=re.I) for p in blocked):
        return None
    return text


def generate_grounded_explanation(
    claim: str,
    lang: str,
    result_status: str,
    matches: List[Dict[str, Any]],
) -> Dict[str, Any]:
    refs = [str(m.get("reference") or m.get("id") or "").strip() for m in matches[:2] if (m.get("reference") or m.get("id"))]
    base = {
        "used": False,
        "grounded": True,
        "provider": "OpenAI-compatible",
        "model": RAG_MODEL or None,
        "evidence_refs": refs,
        "text": None,
        "failure_reason": None,
    }
    if result_status not in _ALLOWED_STATUSES or not matches:
        base["failure_reason"] = "status_or_evidence_not_eligible"
        return base
    if not _configured():
        base["failure_reason"] = "rag_not_configured"
        return base
    evidence = _evidence_rows(matches, lang)
    try:
        generated = _validate_generated(_call_chat(_messages(claim, lang, result_status, evidence)))
        if not generated:
            base["failure_reason"] = "generated_text_failed_safety_validation"
            return base
        base.update({"used": True, "text": generated, "failure_reason": None})
        return base
    except urllib.error.HTTPError as exc:
        # Keep diagnostics useful without exposing response bodies or credentials.
        base["failure_reason"] = f"generator_unavailable:HTTP_{exc.code}"
        return base
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError, OSError) as exc:
        base["failure_reason"] = f"generator_unavailable:{type(exc).__name__}"
        return base
