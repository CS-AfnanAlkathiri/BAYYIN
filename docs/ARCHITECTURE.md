# Architecture

## Purpose

BAYYIN verifies claims in digital Islamic content by combining semantic retrieval with deterministic source verification. The AI narrows the evidence space; the verification layer decides what can be presented as evidence.

## End-to-end pipeline

1. **SPLIT** — separate input into checkable claims.
2. **AI RETRIEVE** — rank approved source records by semantic relevance.
3. **VERIFY** — check wording, explicit citations, provenance, and relevance thresholds.
4. **CONTEXT** — distinguish exact match, semantic relevance, contextual uncertainty, and specialist-review cases.
5. **RAG EXPLAIN** — when a compatible generator is configured, automatically generate a short explanation using only evidence that passed BAYYIN's verification gates.
6. **REPORT** — show source text, provenance, context notes, retrieval method, generated explanation when available, and limits.

```text
claim
  ↓
AI semantic retrieval
  ↓
approved candidates
  ↓
lexical + citation + provenance verification
  ↓
relevance / safety gate
  ├─ pass → source + context + limits
  ├─ weak → insufficient evidence
  └─ specialist judgment → specialist review
```

## Components

- **Frontend:** static HTML, CSS, and JavaScript.
- **API:** FastAPI.
- **Default semantic retriever:** scikit-learn LSA using word/character TF-IDF + TruncatedSVD + cosine similarity.
- **Optional semantic retriever:** local sentence-transformers-compatible multilingual embedding model such as BGE-M3.
- **Lexical verification:** RapidFuzz plus token/keyword overlap.
- **Approved live-source adapters:** Quranpedia, QuranEnc, and Dorar for supported retrieval/verification tasks.
- **Safety:** deterministic abstention and specialist-review routing.

## Why AI is used

Users often paraphrase religious texts instead of quoting them exactly. Keyword and fuzzy search can miss a relevant source when wording changes. BAYYIN therefore uses semantic retrieval to recover candidates by meaning.

Semantic similarity is deliberately **not** treated as proof. The retrieved candidate must still pass independent verification before it is shown.

## Explicit-reference verification

A reference such as `Quran 49:6` is resolved before open-ended retrieval. BAYYIN compares the user's attached claim with that exact source instead of assuming that the existence of the citation proves the claim.

Possible outcomes include:

- strong source match,
- context needed,
- citation mismatch,
- insufficient evidence.

## Hybrid approved knowledge layer

BAYYIN uses a bounded hybrid knowledge layer rather than open-web evidence:

- a local curated seed corpus keeps tests and demos reproducible,
- approved live-source connectors extend verification where supported,
- surfaced items keep provenance and source URLs,
- unsupported websites are not treated as evidence,
- controlled ingestion can expand the local corpus without changing the verification contract.

This build implements **AI-assisted retrieval and verification**, plus an **automatic bounded source-grounded RAG explanation layer when a compatible generator is configured**. It intentionally does not implement free-form religious answer generation.

## Failure handling

- weak semantic candidates are blocked by a relevance gate,
- explicit references are resolved directly before semantic retrieval,
- live-source failures fall back to the local approved seed where possible,
- missing evidence produces abstention rather than fabricated attribution,
- personal/specialist ruling requests are referred rather than answered independently.

## Bounded source-grounded RAG (V7)

V7 adds a provider-configured generation layer after retrieval and verification:

```text
claim
  -> semantic / explicit-reference retrieval
  -> approved-source + provenance checks
  -> relevance / safety gate
  -> admitted evidence bundle
  -> bounded RAG generator
  -> short grounded explanation + machine-attached evidence references
```

The generator is never the source of Qur'an, hadith text, grading, or a religious ruling. It receives only evidence that has already passed BAYYIN's verification gates. The prompt explicitly forbids outside knowledge and free religious judgment. Generated output is capped, stripped of URLs, and rejected if it takes a direct ruling form. Generation failure is non-fatal: the verified source report is still returned.

Runtime status is available at `GET /api/rag-status`. RAG is automatic: when an API base URL, secret key, and model are configured, BAYYIN uses the bounded RAG explanation layer by default. If the provider is missing or unavailable, the verified evidence report remains fully functional.
