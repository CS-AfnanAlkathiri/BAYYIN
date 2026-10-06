# Sources and Licenses

This document records the religious and knowledge sources used by BAYYIN, how each source is used and verified, how provenance is preserved, and the software/tool licensing relevant to the public repository.

## Source policy

BAYYIN does not treat the open web as religious evidence. Source roles are controlled through `data/source_registry.json`, and surfaced evidence keeps provenance, reference metadata, and a source URL.

The local corpus is intentionally small and reproducible for the competition demo and automated testing. Approved live-source connectors extend verification where supported. Future expansion must preserve the same source-role, provenance, verification, attribution, and licensing rules.

## Integrated source roles

### Quranpedia
**Role:** Qur'an text and reference verification.

BAYYIN uses Quranpedia-linked records for structured Qur'anic references and keeps surah/ayah metadata, source identity, source URL, and provenance with each record.

### QuranEnc
**Role:** approved multilingual Qur'an translation retrieval.

Translations are displayed as translations and remain distinct from the primary Arabic Qur'anic text.

### Dorar
**Role:** hadith source tracing, takhrij/grading inspection, and supported hadith retrieval.

Hadith grading is displayed only when it is actually available from the documented source record or response. BAYYIN does not invent grading. Live API HTML is sanitized before text is shown in the UI.

### Local curated knowledge layer
**Role:** reproducible demo and test evidence.

The competition repository includes a small deterministic seed set with provenance and source URLs. Hadith records include documented grading metadata where used.

## Verification architecture

BAYYIN deliberately separates retrieval from verification:

1. **Semantic Retrieval - LSA / scikit-learn:** retrieves and ranks candidate evidence by meaning over the approved knowledge layer.
2. **Lexical Verification - RapidFuzz:** performs deterministic wording and text-similarity checks on candidate evidence. RapidFuzz is not the primary semantic retrieval engine.
3. **Verification Gates:** citation, provenance, relevance, wording, and context checks decide whether evidence may be shown.
4. **Bounded RAG Explanation:** generates a short explanation only from evidence that has already passed the verification gates.

In short:

**Claim -> Semantic Retrieval -> Lexical / Provenance Verification -> Verification Gates -> Accepted Evidence -> Bounded RAG Explanation**

If evidence is insufficient, BAYYIN abstains rather than generating unsupported religious evidence. If a cited source exists but does not support the attributed meaning, BAYYIN can surface a citation mismatch. BAYYIN does not issue independent fatwas or replace qualified scholarly review.

## Controlled ingestion

`scripts/ingest_approved_sources.py` validates supplied JSON/JSONL records before they are merged into the local corpus. It checks approved domains and required provenance fields, including hadith grading requirements where applicable.

Do not bulk-copy or redistribute external corpora without checking the source owner's terms, licensing, attribution, and provenance requirements.

## Approved expansion sources

`data/source_registry.json` documents additional approved source families for controlled future expansion. A source being listed for expansion does not mean it is already integrated into the runtime.

Examples include HadeethEnc, TerminologyEnc, King Fahd Glorious Qur'an Printing Complex resources, Shamela, and Tafsir.net. Future integrations must be reviewed for source suitability, attribution, access terms, and redistribution rights before content is added to the project corpus.

## Tools, services, and licenses

| Tool / service | Role in BAYYIN | License / terms |
|---|---|---|
| FastAPI | Backend API framework | MIT |
| Uvicorn | ASGI application server | BSD-3-Clause |
| Pydantic | Request/response validation | MIT |
| scikit-learn | **LSA semantic retrieval** using TF-IDF + TruncatedSVD | BSD-3-Clause |
| RapidFuzz | **Lexical verification and text-similarity checks** after/beside retrieval | MIT |
| python-dotenv | Environment-variable loading | BSD-3-Clause |
| sentence-transformers | Optional embedding retrieval backend | Apache-2.0 package license; model-specific terms apply separately |
| Quranpedia | Qur'an text/reference source | External source/API terms apply; content is not relicensed by BAYYIN |
| QuranEnc | Multilingual Qur'an translations | External content/API terms and attribution requirements apply |
| Dorar.net | Hadith tracing/search source | External service/content terms apply; content is not relicensed by BAYYIN |
| OpenAI-compatible RAG provider | Bounded explanation from admitted evidence | Provider/model terms apply; it is not a religious evidence source |

The exact runtime packages are listed in `backend/requirements.txt`. Optional embedding dependencies are separated in `requirements-embeddings.txt`.

## Live retrieval used by bounded RAG

The RAG explanation layer does not retrieve religious evidence from the open web. Its evidence bundle can contain records from the local approved seed corpus and approved live connectors already implemented by BAYYIN.

Quranpedia is used for structured Qur'an reference/text retrieval; Dorar.net is used for supported hadith search/tracing; QuranEnc is used for approved translations where configured. The generator receives only the resulting structured evidence after BAYYIN's verification gates.

## RAG generator service

The generator service is not a religious evidence source. It is used only to phrase a short explanation from the evidence bundle already admitted by BAYYIN. The repository supports OpenAI-compatible chat-completions endpoints; provider credentials belong in deployment secrets or a local `.env` file and are never committed.

## Repository license and third-party rights

The root `LICENSE` applies only to BAYYIN's original project code unless a file explicitly states otherwise.

External source texts, Qur'an translations, hadith databases, datasets, APIs/services, trademarks, and optional model weights remain subject to their respective owners' licenses, terms of use, attribution requirements, and redistribution restrictions. Their inclusion as a source reference or live connector does not mean that BAYYIN owns or relicenses that material.



## RAG generator service

The generator service is not a religious evidence source. It is used only to phrase a short explanation from the evidence bundle already admitted by BAYYIN. The repository supports OpenAI-compatible chat-completions endpoints; provider credentials belong in deployment secrets or a local `.env` file and are never committed.
