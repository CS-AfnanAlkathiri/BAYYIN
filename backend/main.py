from __future__ import annotations

import json
import os
import re
import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from rapidfuzz import fuzz
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from .ai_retrieval import SemanticRetriever, AI_ENABLED
from .live_sources import dorar_search, extract_quran_reference, quranpedia_ayah, ENABLED as LIVE_SOURCES_ENABLED
from .rag import generate_grounded_explanation, status as rag_status

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
FRONTEND_DIR = BASE_DIR / "frontend"
DB_PATH = BASE_DIR / "bayyin.db"

app = FastAPI(
    title="BAYYIN API",
    version="7.0.0",
    description=(
        "Evidence-first source tracing and context checking for Islamic digital content. "
        "BAYYIN does not issue religious rulings."
    ),
)

_cors_env = os.environ.get("BAYYIN_CORS_ORIGINS", "").strip()
_cors_origins = [o.strip() for o in _cors_env.split(",") if o.strip()] or [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

AR_DIACRITICS = re.compile(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]")
PUNCT = re.compile(r"[^\w\s\u0600-\u06FF]+", re.UNICODE)
EN_PUNCT = re.compile(r"[^\w\s]+", re.UNICODE)
ARABIC_CHAR = re.compile(r"[\u0600-\u06FF]")
TOKEN_RE = re.compile(r"[\w\u0600-\u06FF]+", re.UNICODE)


def normalize_ar(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = AR_DIACRITICS.sub("", text)
    text = text.replace("ٱ", "ا").replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = text.replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
    text = PUNCT.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def normalize_en(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = EN_PUNCT.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def normalize_for(lang: str, text: str) -> str:
    return normalize_ar(text) if lang == "ar" else normalize_en(text)


def detect_lang(text: str) -> str:
    return "ar" if ARABIC_CHAR.search(text or "") else "en"


def resolve_lang(payload_lang: str, text: str) -> str:
    return detect_lang(text) if payload_lang == "auto" else payload_lang


def load_json(name: str):
    with open(DATA_DIR / name, "r", encoding="utf-8") as f:
        return json.load(f)


SOURCES: List[Dict[str, Any]] = load_json("sources.json")
CURATED_CLAIMS: List[Dict[str, Any]] = load_json("curated_claims.json")
EVALUATION_CASES: List[Dict[str, Any]] = load_json("evaluation_cases.json")
SOURCE_REGISTRY: List[Dict[str, Any]] = load_json("source_registry.json")

for item in SOURCES:
    item["_norm_ar"] = normalize_ar(item.get("text_ar", ""))
    item["_norm_en"] = normalize_en(item.get("text_en", ""))
    item["_keywords_norm_ar"] = [normalize_ar(x) for x in item.get("keywords", [])]
    item["_keywords_norm_en"] = [normalize_en(x) for x in item.get("keywords_en", [])]
    item.setdefault("review_status", "pending_specialist_review")
    item.setdefault("retrieval_policy", "curated_seed_source")

for item in CURATED_CLAIMS:
    item["_norm_ar"] = normalize_ar(item.get("claim_ar", ""))
    item["_norm_en"] = normalize_en(item.get("claim_en", ""))


AI_RETRIEVER = SemanticRetriever(SOURCES, CURATED_CLAIMS)

MESSAGES = {
    "specialist_review": {
        "ar": {
            "label": "يتطلب مراجعة مختص شرعي",
            "reason": "السؤال يتطلب حكمًا شرعيًا متخصصًا أو يعتمد على تفاصيل حالة بعينها. يمكن لـBAYYIN عرض مصادر عامة ذات صلة، لكنه لا يصدر فتوى أو حكمًا مستقلًا.",
        },
        "en": {
            "label": "Requires qualified specialist review",
            "reason": "The question requires qualified religious judgment or depends on individual circumstances. BAYYIN may surface relevant general sources, but it does not issue an independent ruling.",
        },
    },
    "source_match": {
        "ar": {
            "label": "تطابق قوي مع مصدر",
            "reason": "وجد BAYYIN تطابقًا نصيًا قويًا مع مصدر موثق. هذه نتيجة تحقق من المصدر، وليست حكمًا على صحة الواقعة أو الاستنتاج.",
        },
        "en": {
            "label": "Strong source match",
            "reason": "BAYYIN found a strong textual match with a documented source. This verifies the source match; it is not a ruling on the claim or situation.",
        },
    },
    "source_linked": {
        "ar": {
            "label": "مدعوم بنص مرجعي",
            "reason": "تم ربط الادعاء بحالة تقييم مرجعية ومصدر محدد. اعرض النص والسياق قبل استخلاص أي نتيجة.",
        },
        "en": {
            "label": "Supported by a referenced text",
            "reason": "The claim matched a curated evaluation case with a specific source. Inspect the text and context before drawing a conclusion.",
        },
    },
    "context_needed": {
        "ar": {
            "label": "يوجد مصدر قريب — السياق مطلوب",
            "reason": "يوجد مصدر قريب، لكن التشابه وحده لا يثبت أن الادعاء يعكس المعنى المقصود بالكامل. اقرأ السياق الكامل.",
        },
        "en": {
            "label": "Close source found — context needed",
            "reason": "A close source exists, but similarity alone does not establish that the claim reflects the intended meaning. Read the full context.",
        },
    },
    "citation_mismatch": {
        "ar": {
            "label": "المرجع صحيح — لكن الادعاء لا يطابقه",
            "reason": "تم العثور على المرجع المذكور، لكن النص أو الادعاء المرفق لا تدعمه صياغة المصدر بدرجة كافية. يعرض بيّن المرجع الصحيح ولا ينسب إليه الادعاء.",
        },
        "en": {
            "label": "Reference found — claim not supported by it",
            "reason": "The cited reference was found, but the accompanying wording or claim is not sufficiently supported by the source text. BAYYIN shows the authentic reference without attributing the claim to it.",
        },
    },
    "possible_lead": {
        "ar": {
            "label": "مصدر محتمل",
            "reason": "هناك إشارة نصية محتملة إلى مصدر، لكن الأدلة غير كافية لاعتبارها نتيجة موثوقة تلقائيًا.",
        },
        "en": {
            "label": "Possible source lead",
            "reason": "There is a possible textual lead, but the evidence is not strong enough for an automatic source conclusion.",
        },
    },
    "insufficient_evidence": {
        "ar": {
            "label": "أدلة غير كافية",
            "reason": "لم يجد النظام تطابقًا كافيًا في قاعدة البيانات الحالية. هذا لا يعني أن الادعاء صحيح أو خطأ.",
        },
        "en": {
            "label": "Insufficient evidence",
            "reason": "No sufficiently strong match was found in the current database. This does not mean the claim is true or false.",
        },
    },
}

DISCLAIMER = {
    "ar": "هذه نتيجة مساعدة لتتبع المصدر والسياق وليست فتوى أو حكمًا شرعيًا.",
    "en": "This is a source- and context-tracing aid, not a fatwa or religious ruling.",
}
SYSTEM_NOTE = {
    "ar": "BAYYIN لا يصدر فتاوى ولا يقرر الحلال والحرام. وظيفته تتبع النصوص وإظهار المصادر والسياق وحالات عدم اليقين.",
    "en": "BAYYIN does not issue fatwas or decide what is halal or haram. It traces text, surfaces sources and context, and makes uncertainty visible.",
}

# Safety gate: intent matters more than a keyword alone. This prevents a source-
# tracing request that merely quotes the word "haram" from being treated as a fatwa.
SENSITIVE_TERMS_AR = [
    "فتوى", "فتوي", "حلال", "حرام", "واجب", "فرض", "يجوز", "مكروه", "مستحب",
    "طلاق", "ربا", "زنا", "ميراث", "كفاره", "كفارة", "نجاسه", "نجاسة", "حكم",
]
SENSITIVE_TERMS_EN = [
    "fatwa", "halal", "haram", "permissible", "allowed", "forbidden", "obligatory",
    "ruling", "sinful", "divorce", "inheritance", "riba",
]
SENSITIVE_PATTERNS_AR = [
    r"ما\s+(?:هو\s+)?حكم",
    r"هل\s+.+\s+(?:حلال|حرام|يجوز)",
    r"هل\s+(?:يجوز|يجب)",
    r"هل\s+(?:هذا|ذلك)\s+(?:حلال|حرام|جايز)",
    r"ما\s+حكم\s+.+",
    r"افتني|افتي(?:ني|ني)",
]
SENSITIVE_PATTERNS_EN = [
    r"what(?:'s| is)\s+(?:the\s+)?(?:islamic\s+)?ruling",
    r"is\s+(?:this|it)\s+(?:halal|haram|permissible|allowed|forbidden|sinful)",
    r"am\s+i\s+allowed\s+to",
    r"can\s+i\s+(?:marry|divorce)",
    r"do\s+i\s+have\s+to",
    r"is\s+it\s+obligatory",
]
SENSITIVE_PATTERNS_AR_COMPILED = [re.compile(p) for p in SENSITIVE_PATTERNS_AR]
SENSITIVE_PATTERNS_EN_COMPILED = [re.compile(p) for p in SENSITIVE_PATTERNS_EN]


def ruling_intent(norm: str, lang: str) -> Tuple[bool, str]:
    if lang == "ar":
        if any(p.search(norm) for p in SENSITIVE_PATTERNS_AR_COMPILED):
            return True, "ruling_request_pattern"
        if any(normalize_ar(t) in norm for t in SENSITIVE_TERMS_AR):
            if norm.startswith(("هل ", "ما ", "افت", "افتي")):
                return True, "sensitive_term_with_question_intent"
        return False, ""
    if any(p.search(norm) for p in SENSITIVE_PATTERNS_EN_COMPILED):
        return True, "ruling_request_pattern"
    if any(normalize_en(t) in norm for t in SENSITIVE_TERMS_EN):
        if re.match(r"^(is|are|am|can|could|should|what|how|do|does)\b", norm):
            return True, "sensitive_term_with_question_intent"
    return False, ""


def tokenize(norm: str) -> List[str]:
    return [t for t in TOKEN_RE.findall(norm) if len(t) > 1]


def overlap_ratio(query_tokens: List[str], target_tokens: List[str]) -> float:
    if not query_tokens:
        return 0.0
    q = set(query_tokens)
    t = set(target_tokens)
    return 100.0 * len(q & t) / max(1, len(q))


def explicit_quran_reference(claim: str) -> Optional[Tuple[int, int]]:
    """Parse an explicit Qur'an reference independent of interface language."""
    return extract_quran_reference(claim)


def quran_reference_ids(claim: str) -> List[str]:
    """Return curated source ids for an explicit Qur'an reference."""
    ref = explicit_quran_reference(claim)
    if not ref:
        return []
    surah, ayah = ref
    wanted = f"{surah}:{ayah}"
    return [s["id"] for s in SOURCES if s.get("source_type") == "quran" and wanted in str(s.get("reference", ""))]


def _strip_explicit_reference(claim: str, lang: str) -> str:
    """Remove citation syntax and simple attribution scaffolding before fidelity checks."""
    text = claim or ""
    text = re.sub(r"\(?\s*(?:qur['’]?an|quran|القرآن|القران)?\s*\d{1,3}\s*[:/]\s*\d{1,3}\s*\)?", " ", text, flags=re.I)
    text = re.sub(r"\b(?:qur['’]?an|quran)\s+\d{1,3}\s+\d{1,3}\b", " ", text, flags=re.I)
    text = re.sub(r"^(?:allah|god)\s+(?:said|says)\s*[:：-]?\s*", "", text, flags=re.I)
    text = re.sub(r"^(?:قال\s+الله(?:\s+تعالى)?|يقول\s+الله(?:\s+تعالى)?)\s*[:：-]?\s*", "", text)
    return re.sub(r"\s+", " ", text).strip(" \t\n\r:：-—()[]")


def _semantic_score_for_source(query: str, lang: str, source_id: str) -> float:
    if not query.strip() or not AI_ENABLED:
        return 0.0
    rows = AI_RETRIEVER.search(query, lang, top_k=max(len(SOURCES), 4))
    row = next((r for r in rows if r.get("id") == source_id), None)
    return float(row.get("semantic_score", 0.0)) if row else 0.0


def _explicit_contradiction_cue(text: str, lang: str) -> bool:
    """Conservative contradiction cues for explicit-citation verification.

    This is not a theological classifier. It only catches obvious polarity flips
    that should never be presented as support from the cited text.
    """
    n = normalize_for(lang, text)
    if lang == "en":
        patterns = [
            r"\blying\b.*\b(?:permitted|allowed|required)\b",
            r"\b(?:permitted|allowed|required)\b.*\blying\b",
            r"\b(?:harmless|trivial)\b",
            r"\b(?:required|command(?:s|ed)?)\b.*\b(?:hide|conceal)\b.*\btruth\b",
            r"\b(?:hide|hiding|conceal|concealing)\b.*\btruth\b.*\b(?:required|commanded)\b",
            r"\bcommand(?:s|ed)?\b.*\bspy\b",
            r"\b(?:abandon|leave)\b.*\bjustice\b",
            r"\bnever\b.*\bask\b",
            r"\bfollow\b.*\b(?:every|all)\b.*\b(?:rumor|report)\b",
            r"\bdeceive\b",
        ]
    else:
        patterns = [
            r"(?:يجوز|مباح|مسموح).*الكذب|الكذب.*(?:يجوز|مباح|مسموح)",
            r"(?:يامر|امر).*التجسس|التجسس.*(?:مامور|واجب)",
            r"(?:اتركوا|ترك).*العدل",
            r"(?:يامر|امر).*كتمان.*الحق|كتمان.*الحق.*(?:واجب|مامور)",
            r"لا.*تسأل|لا.*تسال|ممنوع.*السؤال",
            r"(?:غير خطير|هين|بسيط).*بهتان|بهتان.*(?:هين|بسيط)",
        ]
    return any(re.search(p, n) for p in patterns)


def verify_explicit_quran_reference(claim: str, lang: str) -> Optional[Dict[str, Any]]:
    """Verify a cited Qur'an reference before open-ended retrieval.

    A valid reference never gets converted into an automatic source match. If the
    user attaches a materially different claim, BAYYIN reports a citation mismatch.
    """
    ref = explicit_quran_reference(claim)
    if not ref:
        return None
    ids = quran_reference_ids(claim)
    src = next((s for s in SOURCES if s.get("id") in ids), None)
    if not src:
        return {"reference": ref, "source": None, "comparison_text": _strip_explicit_reference(claim, lang)}
    comparison = _strip_explicit_reference(claim, lang)
    if not comparison or len(tokenize(normalize_for(lang, comparison))) <= 1:
        lexical = 100.0
        semantic = 100.0
        relation = "reference_only"
    else:
        lexical, _trace = _lexical_source_score(comparison, lang, src)
        semantic = _semantic_score_for_source(comparison, lang, src.get("id", ""))
        # Support requires a meaningful wording signal OR a strong, isolated
        # semantic relation. The cited reference itself never boosts this score.
        if _explicit_contradiction_cue(comparison, lang):
            relation = "mismatch"
        elif lexical >= 80 or (semantic >= 88 and lexical >= 55):
            relation = "supported"
        elif semantic >= 80 or lexical >= 60:
            relation = "needs_context"
        else:
            relation = "mismatch"
    return {
        "reference": ref, "source": src, "comparison_text": comparison,
        "lexical_score": round(lexical, 1), "semantic_score": round(semantic, 1),
        "relation": relation,
    }

def _lexical_source_score(claim: str, lang: str, src: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
    """Deterministic wording-level verification score.

    This is deliberately separate from the AI semantic signal.  BAYYIN uses
    semantic retrieval to find candidates by meaning, then lexical checks to
    tell the user whether the wording itself is close to the source.
    """
    norm = normalize_for(lang, claim)
    norm_key = f"_norm_{lang}"
    kw_key = f"_keywords_norm_{lang}"
    target = src.get(norm_key, "")
    if not target:
        return 0.0, {"retrieval": "no_text"}
    q_tokens = tokenize(norm)
    t_tokens = tokenize(target)
    exact_phrase = bool(norm and (norm == target or norm in target or target in norm))
    token_set = fuzz.token_set_ratio(norm, target)
    partial = fuzz.partial_ratio(norm, target)
    wratio = fuzz.WRatio(norm, target)
    token_overlap = overlap_ratio(q_tokens, t_tokens)
    kw_hits = 0
    matched_keywords: List[str] = []
    for kw in src.get(kw_key, []):
        if not kw:
            continue
        kw_tokens = tokenize(kw)
        # Multi-word keywords must share their actual concept tokens; fuzzy
        # substring matching (e.g. "every" vs "everything he hears") created
        # unsafe false leads in adversarial testing.
        if len(kw_tokens) > 1:
            shared = len(set(kw_tokens) & set(q_tokens))
            keyword_match = kw in norm or (shared / max(1, len(set(kw_tokens))) >= 0.75)
        else:
            keyword_match = kw in q_tokens
            if not keyword_match and q_tokens and len(kw) >= 4:
                comparable_tokens = [token for token in q_tokens if len(token) >= 4]
                keyword_match = bool(comparable_tokens) and max(fuzz.WRatio(kw, token) for token in comparable_tokens) >= 92
        if keyword_match:
            kw_hits += 1
            matched_keywords.append(kw)
    per_keyword_bonus = 20 if lang == "ar" else 8
    keyword_bonus = min(20 if lang == "ar" else 8, kw_hits * per_keyword_bonus)
    if exact_phrase:
        score = 100.0
    else:
        score = (
            token_set * 0.35
            + partial * 0.20
            + wratio * 0.20
            + token_overlap * 0.25
            + keyword_bonus
        )
        score = min(99.0, score)
    trace = {
        "exact_phrase": exact_phrase,
        "token_overlap": round(token_overlap),
        "keyword_hits": kw_hits,
        "matched_keywords": matched_keywords[:6],
        "retrieval": "exact_phrase" if exact_phrase else "lexical_fuzzy_keyword",
    }
    return score, trace


def best_source_matches(claim: str, lang: str, top_k: int = 4, use_ai: bool = True) -> List[Dict[str, Any]]:
    """Hybrid retrieval with an explicit relevance gate.

    Semantic similarity may nominate candidates, but it cannot surface evidence
    unless there is an exact/strong lexical signal or a high, well-separated
    semantic signal. This is intentionally conservative to protect abstention.
    """
    semantic_rows = AI_RETRIEVER.search(claim, lang, top_k=max(top_k * 3, len(SOURCES))) if use_ai and AI_ENABLED else []
    semantic_by_id = {row["id"]: row for row in semantic_rows}
    ordered_sem = sorted([float(r.get("semantic_score", 0.0)) for r in semantic_rows], reverse=True)
    best_sem = ordered_sem[0] if ordered_sem else 0.0
    second_sem = ordered_sem[1] if len(ordered_sem) > 1 else 0.0
    global_margin = best_sem - second_sem
    scored: List[Tuple[float, Dict[str, Any], Dict[str, Any]]] = []

    for src in SOURCES:
        lexical_score, trace = _lexical_source_score(claim, lang, src)
        semantic = semantic_by_id.get(src.get("id"), {})
        semantic_score = float(semantic.get("semantic_score", 0.0))
        exact = bool(trace.get("exact_phrase"))
        token_overlap = float(trace.get("token_overlap", 0) or 0)
        kw_hits = int(trace.get("keyword_hits", 0) or 0)
        is_semantic_top = semantic_score == best_sem and best_sem > 0

        strong_lexical = lexical_score >= 68
        semantic_rescue = (
            use_ai and AI_ENABLED and is_semantic_top and semantic_score >= 82
            and global_margin >= 8
            and (kw_hits >= 1 or lexical_score >= 50)
        )
        defensible = exact or strong_lexical or semantic_rescue

        if exact:
            final_score = 100.0
            retrieval = "exact_phrase"
        elif strong_lexical:
            final_score = max(lexical_score, lexical_score * 0.75 + semantic_score * 0.25)
            retrieval = "hybrid_ai_semantic_lexical" if use_ai and AI_ENABLED else "lexical_fuzzy_keyword"
        elif semantic_rescue:
            # Do not present semantic cosine as truth/confidence. This internal
            # ranking signal is capped and reported separately in metadata.
            final_score = min(89.0, semantic_score * 0.88)
            retrieval = "semantic_candidate_verified_by_gate"
        else:
            continue

        trace.update({
            "retrieval": retrieval,
            "lexical_score": round(lexical_score, 1),
            "semantic_score": round(semantic_score, 1) if use_ai and AI_ENABLED else None,
            "semantic_margin": round(global_margin, 1) if is_semantic_top else None,
            "semantic_method": semantic.get("ai_method") if semantic else None,
            "ai_assisted": bool(use_ai and AI_ENABLED and semantic),
            "relevance_gate_passed": True,
            "gate_reason": "exact" if exact else ("strong_lexical" if strong_lexical else "strong_isolated_semantic"),
        })
        scored.append((min(100.0, final_score), src, trace))

    scored.sort(key=lambda x: x[0], reverse=True)
    results: List[Dict[str, Any]] = []
    for score, src, trace in scored[:top_k]:
        out = {k: v for k, v in src.items() if not k.startswith("_")}
        out["match_score"] = round(score)
        out["lexical_score"] = trace.get("lexical_score")
        out["semantic_score"] = trace.get("semantic_score")
        out["retrieval_method"] = trace.get("retrieval")
        out["match_trace"] = trace
        results.append(out)
    return results

def match_curated_claim(claim: str, lang: str) -> Optional[Dict[str, Any]]:
    norm = normalize_for(lang, claim)
    norm_key = f"_norm_{lang}"
    best = None
    best_score = 0
    for item in CURATED_CLAIMS:
        target = item.get(norm_key, "")
        if not target:
            continue
        score = fuzz.token_set_ratio(norm, target)
        if score > best_score:
            best_score = score
            best = item
    if best and best_score >= 78:
        result = {k: v for k, v in best.items() if not k.startswith("_")}
        result["match_score"] = round(best_score)
        return result
    return None


def serialize_source(src: Dict[str, Any], score: Optional[int] = None, trace: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    out = {k: v for k, v in src.items() if not k.startswith("_")}
    if score is not None:
        out["match_score"] = score
    if trace is not None:
        out["match_trace"] = trace
    return out


def curated_matches_first(curated: Dict[str, Any], matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ids = curated.get("source_ids", [])
    by_id = {m.get("id"): m for m in matches}
    ordered: List[Dict[str, Any]] = []
    for sid in ids:
        if sid in by_id:
            ordered.append(by_id[sid])
        else:
            src = next((s for s in SOURCES if s.get("id") == sid), None)
            if src:
                ordered.append(serialize_source(src, 100, {"retrieval": "curated_evaluation_link"}))
    ordered.extend(m for m in matches if m.get("id") not in ids)
    return ordered[:4]


def bilingual_display(status: str, curated: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, str]]:
    """Return UI-safe bilingual labels/reasons so language switching never reuses stale text."""
    if curated:
        return {
            "ar": {
                "label": curated.get("label_ar") or MESSAGES[status]["ar"]["label"],
                "reason": curated.get("explanation_ar") or MESSAGES[status]["ar"]["reason"],
            },
            "en": {
                "label": curated.get("label_en") or MESSAGES[status]["en"]["label"],
                "reason": curated.get("explanation_en") or MESSAGES[status]["en"]["reason"],
            },
        }
    return {
        "ar": dict(MESSAGES[status]["ar"]),
        "en": dict(MESSAGES[status]["en"]),
    }


def classify_claim(
    claim: str,
    lang: str,
    matches: List[Dict[str, Any]],
    curated: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    norm = normalize_for(lang, claim)
    sensitive, safety_reason = ruling_intent(norm, lang)
    messages = {k: v[lang] for k, v in MESSAGES.items()}

    if sensitive:
        return {
            "status": "specialist_review",
            "confidence": "low",
            "review_required": True,
            "safety_reason": safety_reason,
            "display": bilingual_display("specialist_review"),
            **messages["specialist_review"],
        }

    if curated:
        score = curated.get("match_score", 0)
        curated_status = curated.get("status", "source_linked")
        return {
            "status": curated_status,
            "confidence": "high" if score >= 90 else "medium",
            "review_required": curated_status == "context_needed",
            "safety_reason": None,
            "display": bilingual_display(curated_status, curated),
            "label": curated.get(f"label_{lang}") or messages["source_linked"]["label"],
            "reason": curated.get(f"explanation_{lang}") or messages["source_linked"]["reason"],
        }

    top = matches[0] if matches else None
    score = top.get("match_score", 0) if top else 0
    if top and score >= 92:
        status = "source_match"
        confidence = "high"
        review = False
    elif top and score >= 74:
        status = "context_needed"
        confidence = "medium"
        review = True
    elif top and score >= 68:
        status = "possible_lead"
        confidence = "low"
        review = True
    else:
        status = "insufficient_evidence"
        confidence = "low"
        review = True

    return {
        "status": status,
        "confidence": confidence,
        "review_required": review,
        "safety_reason": None,
        "display": bilingual_display(status),
        **messages[status],
    }



def build_ai_explanation(
    claim: str,
    lang: str,
    classification: Dict[str, Any],
    matches: List[Dict[str, Any]],
    explicit: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return a judge-verifiable explanation of AI's bounded role.

    The semantic model may retrieve/rank candidate evidence, but a deterministic
    verification/relevance gate decides whether any source can be surfaced.
    This structure is deliberately exposed to the UI so the AI contribution is
    visible rather than hidden behind a generic "AI-powered" label.
    """
    status = AI_RETRIEVER.status()
    active_backend = status.get("active_backend", "disabled")
    method = status.get("method", "disabled")
    result_status = classification.get("status")

    # Explicit citations are source-first by design. AI cannot redirect a cited
    # verse to another source; it is only a secondary semantic comparison signal.
    if explicit and explicit.get("source"):
        return {
            "used": bool(AI_ENABLED and explicit.get("comparison_text")),
            "role": "secondary_semantic_check",
            "contribution": "reference_first",
            "value_added_over_lexical_baseline": False,
            "backend": active_backend,
            "method": method,
            "semantic_signal": explicit.get("semantic_score"),
            "lexical_signal": explicit.get("lexical_score"),
            "gate": "explicit_reference_verified",
            "decision": result_status,
            "boundary": "The cited source is resolved directly; AI cannot replace the explicit reference or generate religious evidence.",
        }

    if result_status == "specialist_review":
        return {
            "used": bool(AI_ENABLED),
            "role": "retrieval_bounded_by_safety",
            "contribution": "safety_override",
            "value_added_over_lexical_baseline": False,
            "backend": active_backend,
            "method": method,
            "semantic_signal": None,
            "lexical_signal": None,
            "gate": "blocked_by_safety_policy",
            "decision": result_status,
            "boundary": "Related evidence may be retrieved, but the safety layer prevents an automated religious ruling.",
        }

    top = matches[0] if matches else None
    top_trace = (top or {}).get("match_trace", {}) or {}
    baseline_ids: List[str] = []
    if AI_ENABLED:
        try:
            baseline_ids = [m.get("id") for m in best_source_matches(claim, lang, top_k=3, use_ai=False) if m.get("id")]
        except Exception:
            baseline_ids = []

    if top and top_trace.get("ai_assisted"):
        top_id = top.get("id")
        value_added = bool(top_id and top_id not in baseline_ids)
        return {
            "used": True,
            "role": "semantic_retrieval_and_ranking",
            "contribution": "semantic_recovery" if value_added else "semantic_ranking",
            "value_added_over_lexical_baseline": value_added,
            "backend": active_backend,
            "method": method,
            "semantic_signal": top.get("semantic_score"),
            "lexical_signal": top.get("lexical_score"),
            "gate": "passed_relevance_and_verification_gate",
            "decision": result_status,
            "boundary": "Semantic similarity nominates candidates; deterministic wording, provenance and safety checks decide what can be shown.",
        }

    if not matches and AI_ENABLED:
        raw = AI_RETRIEVER.search(claim, lang, top_k=1)
        return {
            "used": True,
            "role": "semantic_retrieval_and_ranking",
            "contribution": "candidate_rejected" if raw else "no_candidate",
            "value_added_over_lexical_baseline": False,
            "backend": active_backend,
            "method": method,
            "semantic_signal": raw[0].get("semantic_score") if raw else None,
            "lexical_signal": None,
            "gate": "blocked_by_relevance_gate",
            "decision": result_status,
            "boundary": "A semantic candidate is never shown as evidence unless it passes BAYYIN's independent relevance/verification gate.",
        }

    return {
        "used": False,
        "role": "deterministic_verification",
        "contribution": "lexical_or_curated_resolution",
        "value_added_over_lexical_baseline": False,
        "backend": active_backend,
        "method": method,
        "semantic_signal": None,
        "lexical_signal": (top or {}).get("lexical_score"),
        "gate": "deterministic_verification",
        "decision": result_status,
        "boundary": "AI is not forced into every result; exact references and deterministic source checks take precedence when sufficient.",
    }


def live_source_matches(claim: str, lang: str, local_matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Use the approved live source APIs only as a fallback/verification layer.

    Live results never replace a stronger curated result and never create a ruling.
    """
    if not LIVE_SOURCES_ENABLED:
        return []
    results: List[Dict[str, Any]] = []
    ref = extract_quran_reference(claim)
    if ref:
        q = quranpedia_ayah(*ref)
        if q:
            results.append(q)
    # Hadith live lookup is useful when no strong local source was found. Avoid
    # sending obvious Qur'an references to the hadith API.
    if not results and lang == "ar" and (not local_matches or local_matches[0].get("match_score", 0) < 78):
        results.extend(dorar_search(claim, limit=3))
    return results


def analyze_one(claim: str, lang: str, mode: str, allow_live: bool = True) -> Dict[str, Any]:
    explicit = verify_explicit_quran_reference(claim, lang)

    # Explicit citation verification has precedence over open-ended retrieval.
    # This directly handles the core BAYYIN case: a real reference attached to
    # wording that the cited source does not support.
    if explicit and explicit.get("source"):
        src = explicit["source"]
        match = serialize_source(src)
        match["match_score"] = 100 if explicit.get("relation") == "reference_only" else round(float(explicit.get("lexical_score", 0)))
        match["lexical_score"] = explicit.get("lexical_score")
        match["semantic_score"] = explicit.get("semantic_score")
        match["retrieval_method"] = "explicit_reference_verification"
        match["match_trace"] = {
            "retrieval": "explicit_reference_verification",
            "exact_reference": True,
            "lexical_score": explicit.get("lexical_score"),
            "semantic_score": explicit.get("semantic_score"),
            "ai_assisted": bool(AI_ENABLED),
            "claim_relation": explicit.get("relation"),
        }
        if explicit.get("relation") == "mismatch":
            classification = {
                "status": "citation_mismatch", "confidence": "high", "review_required": True,
                "safety_reason": "explicit_reference_content_mismatch",
                "display": bilingual_display("citation_mismatch"),
                "label": MESSAGES["citation_mismatch"][lang]["label"],
                "reason": MESSAGES["citation_mismatch"][lang]["reason"],
            }
        elif explicit.get("relation") == "needs_context":
            display = {
                "ar": {"label": "المرجع موجود — الادعاء يحتاج تحققًا إضافيًا", "reason": "تم العثور على المرجع المذكور، لكن التشابه الحالي لا يكفي لنسبة صياغة الادعاء إليه بثقة. اعرض النص الأصلي والسياق قبل الاستنتاج."},
                "en": {"label": "Reference found — claim needs further verification", "reason": "The cited reference was found, but the current similarity is not enough to attribute the claim wording to it confidently. Inspect the original text and context before concluding."},
            }
            classification = {
                "status": "context_needed", "confidence": "medium", "review_required": True,
                "safety_reason": "explicit_reference_claim_not_verified", "display": display,
                "label": display[lang]["label"], "reason": display[lang]["reason"],
            }
        elif explicit.get("relation") == "reference_only":
            display = {
                "ar": {"label": "تم التحقق من المرجع", "reason": "تم العثور على مرجع الآية المذكور والتحقق منه. يعرض بيّن النص المرجعي ولا يحول وجود المرجع وحده إلى حكم على أي استنتاج إضافي."},
                "en": {"label": "Reference verified", "reason": "The cited Qur'an reference was found and verified. BAYYIN shows the source text and does not treat the existence of the reference alone as support for any additional conclusion."},
            }
            classification = {
                "status": "source_match", "confidence": "high", "review_required": False,
                "safety_reason": None, "display": display,
                "label": display[lang]["label"], "reason": display[lang]["reason"],
            }
        else:
            # Conservative policy for explicit references with attached prose:
            # finding the cited verse is not enough to verify the user's interpretation.
            # Until a dedicated contradiction/entailment model is independently validated,
            # attached claims are capped at context_needed even when wording is close.
            display = {
                "ar": {"label": "تم العثور على المرجع — الادعاء يحتاج فحص السياق", "reason": "تم التحقق من المرجع المذكور، لكن وجود كلمات متشابهة لا يكفي لإثبات أن الادعاء يعكس معنى النص أو سياقه. اعرض النص الأصلي والسياق قبل الاستنتاج."},
                "en": {"label": "Reference found — claim needs context review", "reason": "The cited reference was verified, but shared wording is not enough to prove that the attached claim reflects the source meaning or context. Inspect the source text and context before concluding."},
            }
            classification = {
                "status": "context_needed", "confidence": "medium", "review_required": True,
                "safety_reason": "explicit_reference_attached_claim_requires_context_review",
                "display": display, "label": display[lang]["label"], "reason": display[lang]["reason"],
            }
        rag = generate_grounded_explanation(claim, lang, classification["status"], [match])
        return {
            "claim": claim, **classification, "matches": [match], "curated_reference": None,
            "trace": [
                {"step": "split", "state": "complete", "detail_key": "split"},
                {"step": "trace", "state": "review" if classification["status"] == "citation_mismatch" else "complete", "detail_key": "trace_reference"},
                {"step": "context", "state": "review" if classification["status"] == "citation_mismatch" else "complete", "detail_key": "context"},
                {"step": "explain", "state": "complete", "detail_key": "explain"},
            ],
            "disclaimer": DISCLAIMER[lang],
            "reference_check": explicit,
            "ai_explanation": build_ai_explanation(claim, lang, classification, [match], explicit=explicit),
            "rag_explanation": rag,
        }

    matches = best_source_matches(claim, lang)
    curated = match_curated_claim(claim, lang)
    if curated:
        matches = curated_matches_first(curated, matches)

    should_live_check = allow_live and LIVE_SOURCES_ENABLED and (not matches or matches[0].get("match_score", 0) < 95)
    live_matches = live_source_matches(claim, lang, matches) if should_live_check else []
    live_explicit_relation = None
    if explicit and not explicit.get("source") and live_matches:
        # For references outside the local seed corpus, compare the attached
        # wording against the exact live verse rather than treating the valid
        # reference itself as proof of the claim.
        live = dict(live_matches[0])
        live["_norm_ar"] = normalize_ar(live.get("text_ar", ""))
        live["_norm_en"] = normalize_en(live.get("text_en", ""))
        live["_keywords_norm_ar"] = []
        live["_keywords_norm_en"] = []
        comparison = explicit.get("comparison_text", "")
        if not comparison:
            live_explicit_relation = "reference_only"
        else:
            lexical, _ = _lexical_source_score(comparison, lang, live)
            live["lexical_score"] = round(lexical, 1)
            attribution = bool(re.search(r"(?:allah|god)\s+(?:said|says)|qur['’]?an\s*\d|(?:قال|يقول)\s+الله|القر[اآ]ن", claim, flags=re.I))
            if _explicit_contradiction_cue(comparison, lang) or (attribution and lexical < 55):
                live_explicit_relation = "mismatch"
            elif lexical >= 80:
                live_explicit_relation = "supported"
            else:
                live_explicit_relation = "needs_context"
        matches = [live]
    elif live_matches:
        matches = live_matches + [m for m in matches if m.get("id") not in {x.get("id") for x in live_matches}]

    classification = classify_claim(claim, lang, matches, curated)
    if live_explicit_relation == "mismatch":
        classification = {
            "status": "citation_mismatch", "confidence": "high", "review_required": True,
            "safety_reason": "explicit_live_reference_content_mismatch",
            "display": bilingual_display("citation_mismatch"),
            "label": MESSAGES["citation_mismatch"][lang]["label"],
            "reason": MESSAGES["citation_mismatch"][lang]["reason"],
        }
    elif live_explicit_relation == "needs_context":
        live_display = {
            "ar": {"label": "المرجع موجود — الادعاء يحتاج تحققًا إضافيًا", "reason": "تم استرجاع المرجع المذكور مباشرة، لكن المطابقة الحالية لا تكفي لنسبة صياغة الادعاء إليه بثقة."},
            "en": {"label": "Reference found — claim needs further verification", "reason": "The cited reference was retrieved directly, but the current match is not strong enough to attribute the claim wording to it confidently."},
        }
        classification.update({"status": "context_needed", "confidence": "medium", "review_required": True, "display": live_display, "label": live_display[lang]["label"], "reason": live_display[lang]["reason"]})
    if live_matches and not curated and classification["status"] == "insufficient_evidence":
        top_live = live_matches[0]
        if top_live.get("source_type") == "quran" and top_live.get("match_score", 0) >= 98:
            live_display = {
                "ar": {"label": "تم العثور على المرجع", "reason": "تم استرجاع مرجع الآية المطلوب من مصدر قرآني مباشر. وجود المرجع لا يثبت تلقائيًا صحة أي صياغة أو استنتاج مرفق."},
                "en": {"label": "Reference found", "reason": "The requested Qur'an reference was retrieved from an approved live source. The reference alone does not automatically support accompanying wording or conclusions."},
            }
            classification.update({"status": "context_needed", "confidence": "medium", "review_required": True, "display": live_display, "label": live_display[lang]["label"], "reason": live_display[lang]["reason"]})
        elif top_live.get("source_type") == "hadith":
            live_display = {
                "ar": {"label": MESSAGES["context_needed"]["ar"]["label"], "reason": "ظهرت نتيجة حديثية مباشرة من الدرر السنية. افتح المصدر لفحص النص والتخريج والحكم قبل الاعتماد عليها."},
                "en": {"label": MESSAGES["context_needed"]["en"]["label"], "reason": "A live Dorar.net hadith result was found. Open the source to inspect the exact text, takhrij, and grading before relying on it."},
            }
            classification.update({"status": "context_needed", "confidence": "medium", "review_required": True, "display": live_display, "label": live_display[lang]["label"], "reason": live_display[lang]["reason"]})
    if classification["status"] == "specialist_review":
        matches = [m for m in matches if m.get("match_score", 0) >= 68]
    elif classification["status"] == "insufficient_evidence":
        matches = []
    elif classification["status"] == "possible_lead":
        matches = [m for m in matches if m.get("match_score", 0) >= 68]

    trace_steps = [
        {"step": "split", "state": "complete", "detail_key": "split"},
        {"step": "trace", "state": "complete" if matches else "no_match", "detail_key": ("trace_live" if live_matches else ("trace_ai" if AI_ENABLED else "trace_curated"))},
        {"step": "context", "state": "review" if classification["status"] in {"context_needed", "possible_lead", "specialist_review"} else "complete", "detail_key": "context"},
        {"step": "explain", "state": "complete", "detail_key": "explain"},
    ]
    if classification["status"] == "specialist_review":
        trace_steps[1]["detail_key"] = "trace_specialist"

    rag = generate_grounded_explanation(claim, lang, classification["status"], matches)
    return {
        "claim": claim, **classification, "matches": matches, "curated_reference": curated,
        "trace": trace_steps, "disclaimer": DISCLAIMER[lang],
        "ai_explanation": build_ai_explanation(claim, lang, classification, matches, explicit=explicit),
        "rag_explanation": rag,
    }


class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=3, max_length=8000)
    mode: str = Field(default="auto", pattern="^(auto|quote|context|source)$")
    lang: str = Field(default="auto", pattern="^(auto|ar|en)$")


class FeedbackRequest(BaseModel):
    input_text: str = Field(min_length=1, max_length=8000)
    result_status: Optional[str] = Field(default=None, max_length=80)
    helpful: bool
    note: Optional[str] = Field(default=None, max_length=1000)


def split_claims(text: str) -> List[str]:
    chunks = re.split(r"[\n\r]+|(?<=[.!؟?؛;])\s+", text.strip())
    cleaned = [re.sub(r"\s+", " ", c).strip(" -•\t") for c in chunks]
    cleaned = [c for c in cleaned if len(c) >= 3]
    return cleaned[:8] or [text.strip()]


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            input_text TEXT NOT NULL,
            result_status TEXT,
            helpful INTEGER,
            note TEXT
        )
        """
    )
    conn.commit()
    conn.close()


init_db()


@app.get("/api/health")
def health():
    checks = {"sources_loaded": len(SOURCES) > 0, "curated_claims_loaded": len(CURATED_CLAIMS) > 0, "evaluation_cases_loaded": len(EVALUATION_CASES) > 0, "source_registry_loaded": len(SOURCE_REGISTRY) > 0, "db_reachable": False}
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("SELECT 1")
        conn.close()
        checks["db_reachable"] = True
    except sqlite3.Error:
        pass
    return {"ok": all(checks.values()), "service": "BAYYIN", "version": "7.0.0", "checks": checks}


@app.get("/api/stats")
def stats():
    return {
        "sources": len(SOURCES),
        "quran_sources": sum(1 for s in SOURCES if s["source_type"] == "quran"),
        "hadith_sources": sum(1 for s in SOURCES if s["source_type"] == "hadith"),
        "curated_claims": len(CURATED_CLAIMS),
        "evaluation_cases": len(EVALUATION_CASES),
        "robustness_evaluation_cases": 60,
        "architecture": ["claim decomposition", "AI semantic retrieval/ranking", "deterministic lexical + provenance verification", "relevance gate", "safety/referral gate", "context classification", "bounded source-grounded RAG explanation (optional)", "traceable evidence report"],
        "live_sources_enabled": LIVE_SOURCES_ENABLED,
        "live_sources": ["Quranpedia API", "QuranEnc translation API", "Dorar.net Hadith API"],
        "source_registry_entries": len(SOURCE_REGISTRY),
        "ai_retrieval": AI_RETRIEVER.status(),
        "review_status": "pending_specialist_review",
        "note_ar": "قاعدة بيانات أولية حقيقية المصدر لمشروع هاكاثون؛ يجب أن تخضع النصوص والملاحظات والمقاييس لمراجعة مختصين قبل الإطلاق العام.",
        "note_en": "A real-source seed database for the hackathon MVP; source records, context notes, and evaluation policy require specialist review before public launch.",
    }


@app.get("/api/knowledge-status")
def knowledge_status():
    """Describe BAYYIN's bounded knowledge layer without overstating corpus size.

    The hackathon build keeps a small curated local seed for deterministic tests
    and augments it with approved live-source connectors. Future expansion should
    ingest additional approved material into the same provenance-aware schema.
    """
    integrated = [r for r in SOURCE_REGISTRY if r.get("integrated")]
    expansion = [r for r in SOURCE_REGISTRY if not r.get("integrated")]
    return {
        "architecture": "hybrid approved knowledge layer",
        "local_curated_records": len(SOURCES),
        "approved_source_families": len(SOURCE_REGISTRY),
        "integrated_source_families": len(integrated),
        "live_connectors": [
            {"id": r.get("id"), "domain": r.get("domain"), "role": r.get("role")}
            for r in integrated
        ],
        "approved_expansion_sources": [
            {"id": r.get("id"), "domain": r.get("domain"), "role": r.get("role")}
            for r in expansion
        ],
        "retrieval_policy": "local curated evidence first; approved live-source retrieval when supported; no open-web evidence",
        "rag_status": rag_status(),
        "why": "BAYYIN retrieves candidate evidence, verifies it independently, and can optionally generate a short explanation using only the admitted evidence bundle. If generation is unavailable, the verified report still works.",
    }


@app.get("/api/rag-status")
def get_rag_status():
    """Report whether bounded source-grounded generation is configured at runtime."""
    return rag_status()


@app.get("/api/ai-status")
def ai_status():
    """Explain exactly where AI is used, for judges and technical reviewers."""
    return {
        **AI_RETRIEVER.status(),
        "boundary": "Semantic AI retrieves/ranks evidence. The optional RAG generator may explain admitted evidence, but it never generates source text, grading, or religious rulings.",
        "verification_layer": "RapidFuzz lexical comparison + provenance/source metadata",
        "safety_layer": "deterministic abstention/referral rules for personal rulings and insufficient evidence",
    }


@app.get("/api/ai-evaluate")
def ai_evaluate():
    """Compare AI-hybrid retrieval with the lexical baseline on the 60-case set.

    Only paraphrase and out-of-corpus cases are used for the AI comparison;
    explicit citation mismatch is reported separately by /api/evaluate-robustness.
    This is developer-authored engineering evidence, not independent validation.
    """
    path = DATA_DIR / "evaluation_regression.json"
    cases = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    positive = [c for c in cases if c.get("category") == "paraphrase"]
    negative = [c for c in cases if c.get("category") == "out_of_corpus"]
    rows = []
    ai_hits = base_hits = 0
    ai_false = base_false = 0
    for case in positive:
        expected = set(case.get("expected_source_ids", []))
        ai_found = [m.get("id") for m in best_source_matches(case["input"], case["lang"], top_k=3, use_ai=True)]
        base_found = [m.get("id") for m in best_source_matches(case["input"], case["lang"], top_k=3, use_ai=False)]
        ai_ok = bool(expected & set(ai_found)); base_ok = bool(expected & set(base_found))
        ai_hits += int(ai_ok); base_hits += int(base_ok)
        rows.append({"id": case["id"], "category": "paraphrase", "baseline_ok": base_ok, "ai_hybrid_ok": ai_ok, "baseline_top": base_found[:1], "ai_top": ai_found[:1]})
    for case in negative:
        ai_found = best_source_matches(case["input"], case["lang"], top_k=3, use_ai=True)
        base_found = best_source_matches(case["input"], case["lang"], top_k=3, use_ai=False)
        ai_false += int(bool(ai_found)); base_false += int(bool(base_found))
        rows.append({"id": case["id"], "category": "out_of_corpus", "baseline_false_lead": bool(base_found), "ai_hybrid_false_lead": bool(ai_found)})
    return {
        "cases": len(positive) + len(negative),
        "paraphrase_cases": len(positive),
        "out_of_corpus_cases": len(negative),
        "baseline_paraphrase_top3_hit_rate": round(100 * base_hits / max(1, len(positive)), 1),
        "ai_hybrid_paraphrase_top3_hit_rate": round(100 * ai_hits / max(1, len(positive)), 1),
        "baseline_false_lead_rate": round(100 * base_false / max(1, len(negative)), 1),
        "ai_hybrid_false_lead_rate": round(100 * ai_false / max(1, len(negative)), 1),
        "scope": "48 developer-authored retrieval/abstention cases from a 60-case regression set; engineering evidence only, not religious accuracy, independent validation, or scholarly certification.",
        "rows": rows,
    }


@app.get("/api/evaluate-robustness")
def evaluate_robustness():
    """Run the 60-case local robustness benchmark.

    The set is developer-authored and is not scholarly validation. Live APIs are
    disabled for this benchmark so results are reproducible and measure the
    bounded local retrieval/verification pipeline only.
    """
    path = DATA_DIR / "evaluation_regression.json"
    cases = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    rows = []
    positive_total = positive_hits = 0
    negative_total = negative_abstain = false_leads = 0
    mismatch_total = mismatch_hits = 0
    for case in cases:
        result = analyze_one(case["input"], case["lang"], "auto", allow_live=False)
        found_ids = [m.get("id") for m in result.get("matches", [])]
        category = case.get("category")
        expected = set(case.get("expected_source_ids", []))
        ok = False
        if category == "paraphrase":
            positive_total += 1
            ok = bool(expected & set(found_ids))
            positive_hits += int(ok)
        elif category == "out_of_corpus":
            negative_total += 1
            ok = result.get("status") == "insufficient_evidence" and not found_ids
            negative_abstain += int(ok)
            false_leads += int(bool(found_ids) or result.get("status") in {"possible_lead", "context_needed", "source_match", "source_linked"})
        elif category == "citation_mismatch":
            mismatch_total += 1
            ok = result.get("status") == "citation_mismatch"
            mismatch_hits += int(ok)
        rows.append({
            "id": case.get("id"), "category": category, "ok": ok,
            "observed_status": result.get("status"), "found_source_ids": found_ids[:3],
        })
    total = len(cases)
    total_ok = sum(int(r["ok"]) for r in rows)
    return {
        "cases": total,
        "overall_behavioral_pass_rate": round(100 * total_ok / max(1, total), 1),
        "paraphrase_top_match_rate": round(100 * positive_hits / max(1, positive_total), 1),
        "out_of_corpus_safe_abstention_rate": round(100 * negative_abstain / max(1, negative_total), 1),
        "out_of_corpus_false_lead_rate": round(100 * false_leads / max(1, negative_total), 1),
        "explicit_citation_mismatch_detection_rate": round(100 * mismatch_hits / max(1, mismatch_total), 1),
        "scope": "60 developer-authored local regression cases; engineering evidence only, not religious accuracy, independent validation, or scholarly certification.",
        "rows": rows,
    }



@app.get("/api/judge-evidence")
def judge_evidence():
    """Compact, reproducible evidence for challenge reviewers.

    This endpoint intentionally separates implemented evidence from future work.
    It is not a marketing scorecard and does not claim scholarly certification.
    """
    ai_eval = ai_evaluate()
    robust = evaluate_robustness()
    return {
        "implemented_now": {
            "problem": "Verify claims in digital Islamic content with traceable sources, context and explicit uncertainty.",
            "target_users": ["Islamic content researchers", "content creators", "general users checking shared claims"],
            "ai_role": "Meaning-level retrieval/ranking over a bounded approved knowledge layer; when configured, the automatic bounded RAG generator explains only evidence that passes independent verification.",
            "verification_role": "Deterministic lexical, explicit-reference, provenance and relevance-gate checks decide whether an AI candidate may be shown.",
            "safety_role": "Abstain on insufficient evidence; refer personal/specialist rulings instead of issuing a fatwa.",
        },
        "measurable_evidence": {
            "ai_vs_lexical": {
                "cases": ai_eval.get("cases"),
                "lexical_top3": ai_eval.get("baseline_paraphrase_top3_hit_rate"),
                "ai_hybrid_top3": ai_eval.get("ai_hybrid_paraphrase_top3_hit_rate"),
                "ai_false_lead_rate": ai_eval.get("ai_hybrid_false_lead_rate"),
            },
            "robustness": {
                "cases": robust.get("cases"),
                "overall_behavioral_pass_rate": robust.get("overall_behavioral_pass_rate"),
                "safe_abstention_rate": robust.get("out_of_corpus_safe_abstention_rate"),
                "citation_mismatch_detection_rate": robust.get("explicit_citation_mismatch_detection_rate"),
            },
            "scope_note": "Developer-authored engineering evidence, not religious accuracy or independent scholarly validation.",
        },
        "failure_handling": [
            "weak candidates are blocked by a relevance gate",
            "explicit citations are resolved before open retrieval",
            "live-source failure falls back to the local approved seed corpus",
            "personal/specialist rulings are referred rather than answered independently",
        ],
        "future_work_not_claimed_as_implemented": [
            "larger scholar-reviewed corpus",
            "independent user study",
            "open-ended/free-form religious answer generation (intentionally out of scope)",
            "public-deployment scholarly certification",
        ],
    }


@app.get("/api/source-policy")
def source_policy():
    return {
        "integrated": [row for row in SOURCE_REGISTRY if row.get("integrated")],
        "documented_expansion": [row for row in SOURCE_REGISTRY if not row.get("integrated")],
        "note": "Source roles are domain-specific; inclusion in the scientific package does not make every source interchangeable for every content type.",
    }


@app.get("/api/sources")
def list_sources():
    return [serialize_source(s) for s in SOURCES]


@app.get("/api/sources/{source_id}")
def get_source(source_id: str):
    src = next((s for s in SOURCES if s.get("id") == source_id), None)
    if not src:
        raise HTTPException(status_code=404, detail="Source not found")
    return serialize_source(src)


@app.post("/api/analyze")
def analyze(payload: AnalyzeRequest):
    lang = resolve_lang(payload.lang, payload.text)
    claims = split_claims(payload.text)
    analyses = [analyze_one(c, lang, payload.mode) for c in claims]

    evidence_states = {"source_match", "source_linked", "context_needed"}
    mapped = sum(1 for a in analyses if a["status"] in evidence_states)
    evidence_coverage = round(100 * mapped / max(1, len(analyses)))
    specialist = sum(1 for a in analyses if a["status"] == "specialist_review")
    review_rate = round(100 * sum(1 for a in analyses if a.get("review_required")) / max(1, len(analyses)))

    return {
        "input": payload.text,
        "mode": payload.mode,
        "lang": lang,
        "claims_count": len(analyses),
        "evidence_coverage": evidence_coverage,
        "review_rate": review_rate,
        "specialist_cases": specialist,
        "claims": analyses,
        "pipeline": [
            {"name": "SPLIT", "description": "Extract atomic claims"},
            {"name": "AI RETRIEVE", "description": "Retrieve and rank approved source candidates by meaning"},
            {"name": "VERIFY", "description": "Deterministic lexical and provenance verification"},
            {"name": "CONTEXT", "description": "Check alignment and uncertainty"},
            {"name": "EXPLAIN", "description": "Optionally generate a grounded explanation, then show source, context, and limits"},
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "system_note": SYSTEM_NOTE[lang],
        "ai": AI_RETRIEVER.status(),
    }


@app.get("/api/evaluate")
def evaluate():
    """Run the bundled labeled evaluation set against the live pipeline.

    Metrics are retrieval/abstention measurements, not a claim of religious truth.
    """
    total = len(EVALUATION_CASES)
    retrieval_hits = 0
    safe_abstentions = 0
    expected_status_hits = 0
    rows = []

    for case in EVALUATION_CASES:
        result = analyze_one(case["input"], case["lang"], "auto")
        claim = result
        expected_ids = set(case.get("expected_source_ids", []))
        found_ids = {m.get("id") for m in claim["matches"]}
        retrieval_ok = bool(expected_ids & found_ids) if expected_ids else True
        abstention_ok = claim["status"] == "specialist_review" if case.get("expect_specialist_review") else True
        status_ok = claim["status"] == case.get("expected_status") if case.get("expected_status") else True
        retrieval_hits += int(retrieval_ok)
        safe_abstentions += int(abstention_ok)
        expected_status_hits += int(status_ok)
        rows.append({"id": case["id"], "retrieval_ok": retrieval_ok, "abstention_ok": abstention_ok, "status_ok": status_ok, "observed_status": claim["status"]})

    return {
        "evaluation_cases": total,
        "retrieval_hit_rate": round(100 * retrieval_hits / max(1, total), 1),
        "safe_abstention_rate": round(100 * safe_abstentions / max(1, total), 1),
        "expected_status_rate": round(100 * expected_status_hits / max(1, total), 1),
        "scope": "Bundled MVP cases; measures pipeline behavior, not religious truth.",
        "rows": rows,
    }


@app.post("/api/feedback")
def feedback(payload: FeedbackRequest):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO feedback(created_at,input_text,result_status,helpful,note) VALUES (?,?,?,?,?)",
        (datetime.now(timezone.utc).isoformat(), payload.input_text, payload.result_status, int(payload.helpful), payload.note),
    )
    conn.commit()
    conn.close()
    return {"ok": True}


@app.get("/api/demo/{demo_id}")
def demo(demo_id: str, lang: str = "ar"):
    demos = {
        "ar": {
            "verify": "يا أيها الذين آمنوا إن جاءكم فاسق بنبإ فتبينوا",
            "context": "تكرار كل خبر نسمعه قد يوقعنا في الكذب",
            "hadith": "إنما الأعمال بالنيات",
            "unknown": "هذا نص متداول ولا أعرف هل له مصدر صحيح أم لا",
        },
        "en": {
            "verify": "O you who have believed, if there comes to you a disobedient one with information, investigate",
            "context": "Repeating everything you hear is enough to make a person unreliable",
            "hadith": "Actions are judged by intentions",
            "unknown": "This is a widely shared text and I don't know if it has an authentic source",
        },
    }
    lang = lang if lang in demos else "ar"
    if demo_id not in demos[lang]:
        raise HTTPException(status_code=404, detail="Demo not found")
    return {"text": demos[lang][demo_id], "lang": lang}


app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")


@app.get("/")
def home():
    return FileResponse(FRONTEND_DIR / "index.html")
