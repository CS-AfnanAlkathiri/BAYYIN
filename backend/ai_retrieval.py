"""Bounded AI/NLP retrieval for BAYYIN.

BAYYIN never uses the model as a religious authority. The AI layer only ranks
approved source records by semantic relevance. Source text, provenance,
lexical verification, citation checks, and safety/abstention remain separate.

Backends
--------
- ``lsa`` (default): fully offline word/character TF-IDF + TruncatedSVD.
- ``bge-m3`` / ``sentence-transformers``: optional multilingual embeddings.
  Install ``requirements-embeddings.txt`` and make the model available locally.
  If unavailable, BAYYIN falls back to LSA rather than failing startup.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import Normalizer
from sklearn.pipeline import FeatureUnion, make_pipeline

AI_ENABLED = os.getenv("BAYYIN_AI_RETRIEVAL", "on").strip().lower() not in {"0", "off", "false", "no"}
AI_BACKEND_REQUESTED = os.getenv("BAYYIN_AI_BACKEND", "lsa").strip().lower()
EMBEDDING_MODEL = os.getenv("BAYYIN_EMBEDDING_MODEL", "BAAI/bge-m3").strip()


@dataclass
class _LSAIndex:
    lang: str
    ids: List[str]
    vectorizer: Any
    lsa: Any
    matrix: Any
    components: int


@dataclass
class _EmbeddingIndex:
    lang: str
    ids: List[str]
    matrix: Any


class SemanticRetriever:
    """Semantic retrieval over approved source records only."""

    def __init__(self, sources: List[Dict[str, Any]], curated_claims: List[Dict[str, Any]]):
        self.sources = sources
        self.curated_claims = curated_claims
        self.indices: Dict[str, Optional[Any]] = {"ar": None, "en": None}
        self.embedding_model: Any = None
        self.active_backend = "disabled" if not AI_ENABLED else "lsa"
        self.backend_note = ""
        self._train()

    @staticmethod
    def _clean_parts(parts: Iterable[Any]) -> str:
        return " ".join(str(x).strip() for x in parts if isinstance(x, (str, int, float)) and str(x).strip())

    def _doc_for(self, src: Dict[str, Any], lang: str) -> str:
        if lang == "ar":
            parts: List[Any] = [src.get("title_ar"), src.get("text_ar"), src.get("context_ar")]
            parts.extend(src.get("keywords", []) or [])
            claim_key, expl_key = "claim_ar", "explanation_ar"
        else:
            parts = [src.get("title_en"), src.get("text_en"), src.get("context_en")]
            parts.extend(src.get("keywords_en", []) or [])
            claim_key, expl_key = "claim_en", "explanation_en"
        sid = src.get("id")
        for claim in self.curated_claims:
            if sid in (claim.get("source_ids") or []):
                parts.extend([claim.get(claim_key), claim.get(expl_key)])
        return self._clean_parts(parts)

    def _docs(self, lang: str):
        ids, docs = [], []
        for src in self.sources:
            doc = self._doc_for(src, lang)
            if doc.strip():
                ids.append(str(src.get("id")))
                docs.append(doc)
        return ids, docs

    def _train_lsa_lang(self, lang: str) -> Optional[_LSAIndex]:
        ids, docs = self._docs(lang)
        if len(docs) < 2:
            return None
        vectorizer = FeatureUnion([
            ("word", TfidfVectorizer(lowercase=True, analyzer="word", ngram_range=(1, 2), min_df=1, sublinear_tf=True, norm="l2")),
            ("char", TfidfVectorizer(lowercase=True, analyzer="char_wb", ngram_range=(3, 5), min_df=1, sublinear_tf=True, norm="l2", max_features=5000)),
        ])
        tfidf = vectorizer.fit_transform(docs)
        components = max(1, min(8, tfidf.shape[0] - 1, tfidf.shape[1] - 1))
        lsa = make_pipeline(TruncatedSVD(n_components=components, random_state=42), Normalizer(copy=False))
        matrix = lsa.fit_transform(tfidf)
        return _LSAIndex(lang, ids, vectorizer, lsa, matrix, components)

    def _try_train_embeddings(self) -> bool:
        if AI_BACKEND_REQUESTED not in {"bge-m3", "sentence-transformers", "embeddings"}:
            return False
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            # Avoid surprise network dependence for judging. Set BAYYIN_EMBEDDING_MODEL
            # to a local model path, or pre-download the named model into the cache.
            try:
                model = SentenceTransformer(EMBEDDING_MODEL, local_files_only=True)
            except TypeError:
                model = SentenceTransformer(EMBEDDING_MODEL)
            self.embedding_model = model
            for lang in ("ar", "en"):
                ids, docs = self._docs(lang)
                if not docs:
                    continue
                matrix = model.encode(docs, normalize_embeddings=True, show_progress_bar=False)
                self.indices[lang] = _EmbeddingIndex(lang, ids, np.asarray(matrix))
            self.active_backend = "multilingual_embeddings"
            self.backend_note = f"Loaded local sentence-transformers model: {EMBEDDING_MODEL}"
            return True
        except Exception as exc:
            self.backend_note = f"Requested embedding backend unavailable; fell back to offline LSA ({type(exc).__name__})."
            self.embedding_model = None
            self.indices = {"ar": None, "en": None}
            return False

    def _train(self) -> None:
        if not AI_ENABLED:
            return
        if self._try_train_embeddings():
            return
        self.active_backend = "lsa"
        for lang in ("ar", "en"):
            try:
                self.indices[lang] = self._train_lsa_lang(lang)
            except Exception:
                self.indices[lang] = None

    def search(self, query: str, lang: str, top_k: int = 4) -> List[Dict[str, Any]]:
        index = self.indices.get(lang)
        if not AI_ENABLED or not index or not (query or "").strip():
            return []
        try:
            if isinstance(index, _EmbeddingIndex):
                q = self.embedding_model.encode([query], normalize_embeddings=True, show_progress_bar=False)
                sims = np.asarray(q)[0] @ index.matrix.T
                method = "multilingual_sentence_embeddings"
                model_name = EMBEDDING_MODEL
            else:
                q_tfidf = index.vectorizer.transform([query])
                q_lsa = index.lsa.transform(q_tfidf)
                sims = cosine_similarity(q_lsa, index.matrix)[0]
                method = "latent_semantic_analysis"
                model_name = f"word/character TF-IDF + TruncatedSVD ({index.components} latent dimensions)"
        except Exception:
            return []
        order = np.argsort(-sims)
        results = []
        for idx in order[: max(0, top_k)]:
            raw = float(sims[idx])
            score = max(0.0, min(100.0, raw * 100.0))
            results.append({
                "id": index.ids[int(idx)],
                "semantic_score": round(score, 1),
                "semantic_similarity": round(raw, 4),
                "ai_method": method,
                "ai_model": model_name,
            })
        return results

    def status(self) -> Dict[str, Any]:
        langs = {}
        for lang, index in self.indices.items():
            if isinstance(index, _EmbeddingIndex):
                langs[lang] = {"ready": True, "documents": len(index.ids), "latent_dimensions": None}
            elif isinstance(index, _LSAIndex):
                langs[lang] = {"ready": True, "documents": len(index.ids), "latent_dimensions": index.components}
            else:
                langs[lang] = {"ready": False, "documents": 0, "latent_dimensions": 0}
        return {
            "enabled": AI_ENABLED,
            "requested_backend": AI_BACKEND_REQUESTED,
            "active_backend": self.active_backend,
            "method": "Multilingual sentence embeddings" if self.active_backend == "multilingual_embeddings" else "Latent Semantic Analysis (word/character TF-IDF + TruncatedSVD)",
            "model": EMBEDDING_MODEL if self.active_backend == "multilingual_embeddings" else "offline LSA",
            "purpose": "meaning-level retrieval/ranking of approved source records",
            "generates_religious_content": False,
            "backend_note": self.backend_note,
            "languages": langs,
        }
