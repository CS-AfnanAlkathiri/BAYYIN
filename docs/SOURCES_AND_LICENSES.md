# Sources and Licenses

This document records the religious/knowledge sources used by BAYYIN, how each source is used, how provenance is preserved, and the software/tool licensing relevant to the public repository.

## Source policy

BAYYIN does not treat the open web as evidence. Source roles are controlled through `data/source_registry.json`, and surfaced evidence keeps provenance and a source URL.

The local corpus is intentionally small and reproducible. Approved live-source connectors extend verification where supported. Future expansion should preserve the same source-role and provenance rules.

## Integrated source roles

### Quranpedia

**Role:** Qur'an text/reference verification and approved Qur'anic source records used by the project.

BAYYIN uses Quranpedia-linked records for Qur'anic references and keeps surah/ayah metadata, source URL, and provenance with each record.

### QuranEnc

**Role:** approved multilingual Qur'an translation retrieval for supported explicit-reference workflows.

Translations are displayed as translations, not as the Arabic primary source text.

### Dorar

**Role:** hadith source tracing, takhrij/grading inspection, and supported hadith retrieval workflows.

Hadith grading is displayed only when it is actually available from the documented source record/response. BAYYIN does not invent grading. Live API HTML is sanitized before any text is shown in the UI.

## Bundled source records

The competition repository includes a small deterministic seed set for reproducible demos and automated testing. Each bundled record includes provenance and a source URL. Hadith records include documented grading metadata where used.

English hadith text in the seed data is display rendering and is not a substitute for the primary Arabic evidence.

## Approved expansion sources

`data/source_registry.json` also documents additional approved source families for controlled future expansion. A source being listed for expansion does not mean it is already integrated into the runtime.

## Controlled ingestion

`scripts/ingest_approved_sources.py` is provided to validate supplied JSON/JSONL records before they are merged into the local corpus. It checks approved domains and required provenance fields, including hadith grading requirements where applicable.

Do not bulk-copy external corpora without checking source terms, licensing, attribution, and provenance requirements.

## Software dependencies and licenses

- **FastAPI** — MIT
- **Uvicorn** — BSD-3-Clause
- **RapidFuzz** — MIT
- **Pydantic** — MIT
- **scikit-learn** — BSD-3-Clause
- **python-dotenv** — BSD-3-Clause
- **sentence-transformers** — optional package; Apache-2.0, with model-specific terms applying separately

The root `LICENSE` applies only to BAYYIN's original project code. External source texts, translations, datasets, APIs/services, trademarks, and optional model weights remain subject to their respective terms.

## Live retrieval used by bounded RAG

The RAG explanation layer does not retrieve from the open web. Its evidence bundle can contain records from the local approved seed corpus and approved live connectors already implemented by BAYYIN. Quranpedia is used for structured Qur'an reference/text retrieval; Dorar.net is used for hadith search/tracing; QuranEnc is used for approved translations where configured. The generator receives only the resulting structured evidence after BAYYIN's verification gates.


## RAG generator service

The generator service is not a religious evidence source. It is used only to phrase a short explanation from the evidence bundle already admitted by BAYYIN. The repository supports OpenAI-compatible chat-completions endpoints; provider credentials belong in deployment secrets or a local `.env` file and are never committed.
