# BAYYIN

**BAYYIN is an AI-assisted verification platform for claims in digital Islamic content, with an automatic bounded RAG explanation layer when a compatible generator is configured.** It helps users trace a claim to an approved source, compare the wording, surface relevant context, and understand the limits of the result without issuing an independent fatwa.

The core idea is simple: **AI helps find the right evidence by meaning; verification rules decide whether that evidence is safe to show. The source remains the authority.**

## Live MVP

Try the live BAYYIN prototype here:

[Open BAYYIN MVP](YOUR_MVP_LINK)

## Created by

**Afnan Alkathiri**  
Computer Science Student | Aspiring AI/ML Engineer  
Creator and Developer of BAYYIN

- LinkedIn: [Afnan Alkathiri](https://www.linkedin.com/in/afnan-alkathiri-4451b741a)
- Email: afnanalkthiri21@gmail.com

## Why BAYYIN exists

Islamic content online may contain:

- authentic quotations,
- paraphrases that no longer match the original wording,
- correct references attached to unsupported claims,
- valid texts used without enough context, and
- statements for which no reliable evidence is available.

BAYYIN is designed to make those differences visible in a traceable report instead of treating every similar-looking result as proof.

## How BAYYIN works

```text
User claim or post
        ↓
1. Split into checkable claims
        ↓
2. AI semantic retrieval by meaning
        ↓
3. Approved-source candidate retrieval
        ↓
4. Text / citation / provenance verification
        ↓
5. Relevance and safety gate
        ↓
6. Bounded RAG explanation from admitted evidence only (automatic when a generator is configured)
        ↓
7. Source + context + limits
        ↓
   or abstain / refer
```

### 1. AI retrieval

The default AI backend is an offline semantic-retrieval model built with:

- word and character TF-IDF,
- TruncatedSVD / Latent Semantic Analysis (LSA), and
- cosine similarity.

Its job is to recover relevant approved sources when the user paraphrases the source rather than quoting it exactly.

An optional local multilingual embedding backend using `BAAI/bge-m3` is also supported. BAYYIN does **not** silently download a large model at runtime.

### 2. Independent verification

AI similarity is never treated as proof. Candidate sources are checked with:

- explicit citation resolution,
- lexical similarity,
- token and keyword evidence,
- source provenance,
- relevance thresholds, and
- safety / specialist-review rules.

For example, if a user writes a false statement and attaches `Quran 49:6`, BAYYIN checks that exact verse first. If the verse does not support the attached statement, BAYYIN returns a citation mismatch instead of treating the reference as evidence.

**Important limitation:** lexical and semantic similarity are not contradiction detectors. When an explicit Qur'an reference is accompanied by an attached claim, BAYYIN will not promote that claim to a confident verified match solely because it reuses the verse's wording. Unless an obvious mismatch is detected, the result is conservatively capped at `context_needed` for source/context review. A dedicated entailment/contradiction model is future work.

### 3. Bounded source-grounded RAG

V7 includes an automatic, provider-configured generation layer that can call an **OpenAI-compatible chat-completions API** after retrieval and verification. The generator receives only the evidence bundle that BAYYIN has already admitted through its source, relevance, and safety checks.

The generated text is deliberately narrow: a maximum two-sentence explanation of the verified relationship between the claim and the retrieved evidence. Source citations are attached from BAYYIN's structured source metadata rather than invented by the model. If the generator is unavailable, unconfigured, times out, or fails the safety validator, the normal verification report is returned without generated text.

This is bounded RAG: **retrieve approved evidence → verify it → generate a short grounded explanation**. It is not an open-ended religious chatbot.

## What BAYYIN does not do

BAYYIN does not generate Qur'an text, hadith text, hadith grading, tafsir, or independent religious rulings. When evidence is insufficient, it abstains. When a question requires a qualified religious judgment, it routes the case to specialist review.

## Knowledge and source policy

BAYYIN uses a **hybrid approved knowledge layer**:

- a small local curated seed corpus keeps tests and the demo reproducible,
- approved live connectors extend verification where supported,
- every surfaced result keeps source provenance and a source URL, and
- open-web pages are not treated as evidence.

Currently integrated source roles include:

- **Quranpedia** — Qur'an text/reference verification,
- **QuranEnc** — approved multilingual Qur'an translations,
- **Dorar** — hadith source tracing and grading inspection.

Quranpedia's documented API is used for exact Qur'an reference retrieval and related structured content; Dorar's documented JSON API is used as a hadith-search source. The generator never treats arbitrary open-web pages as evidence.

Additional approved source families are documented for controlled future expansion. See [`docs/SOURCES_AND_LICENSES.md`](docs/SOURCES_AND_LICENSES.md).

## Result states

BAYYIN distinguishes between:

- `source_match` — strong wording/reference verification,
- `context_needed` — relevant source found, but similarity alone is not enough to establish the intended meaning,
- `citation_mismatch` — the cited reference exists, but does not support the attached claim,
- `insufficient_evidence` — no sufficiently reliable evidence was found,
- `specialist_review` — the case requires qualified religious judgment.

The UI exposes one collapsible **How BAYYIN reached this result** panel so reviewers can see the AI contribution, verification steps, and safety decision without cluttering the result.

## Current engineering evaluation

The repository includes a developer-authored regression set used to test retrieval and safety behavior.

With the default offline LSA backend in this build:

- lexical-only paraphrase top-3 retrieval: **55.6%**,
- AI-hybrid paraphrase top-3 retrieval: **83.3%**,
- out-of-corpus false-lead rate: **0.0%**,
- safe abstention on the tested out-of-corpus cases: **100%**,
- explicit citation-mismatch detection on the tested cases: **100%**,
- overall behavioral pass rate across the 60-case regression set: **90.0%**.

These are **engineering regression results**, not religious accuracy, independent scholarly validation, or production-scale certification. Full methodology and limitations are in [`docs/EVALUATION.md`](docs/EVALUATION.md).

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system pipeline, AI role, verification gates, and live-source behavior.
- [`docs/EVALUATION.md`](docs/EVALUATION.md) — regression methodology, baseline comparison, metrics, and limitations.
- [`docs/SAFETY_AND_SCOPE.md`](docs/SAFETY_AND_SCOPE.md) — abstention, specialist referral, explicit-reference safety, and known limitations.
- [`docs/SOURCES_AND_LICENSES.md`](docs/SOURCES_AND_LICENSES.md) — approved source roles, provenance, tools, and licenses.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — controlled next steps without claiming them as implemented.

## Project structure

```text
bayyin/
├── .github/workflows/      # CI tests
├── backend/                # FastAPI API, AI retrieval, live-source adapters, bounded RAG
├── data/                   # curated sources, source registry, evaluation cases
├── docs/                   # public technical and source documentation
├── frontend/               # web interface
├── scripts/                # source validation / controlled ingestion helpers
├── tests/                  # automated regression tests
├── .env.example            # documented optional configuration
├── .gitignore
├── LICENSE
├── README.md
├── requirements-dev.txt
└── requirements-embeddings.txt
```

Local environments, runtime databases, secrets, organizer files, presentations, and private working notes are intentionally excluded from the public repository.

## Run locally on Windows PowerShell

From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
python -m uvicorn backend.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

If PowerShell blocks activation for the current terminal session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

If PowerShell renders Arabic or typographic punctuation as `Ù...` / `â...`, the project files are still UTF-8. For terminal inspection, run:

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
```

The browser UI is the preferred place to verify Arabic rendering.

## Run locally on macOS / Linux

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Run tests

```bash
pip install -r backend/requirements.txt -r requirements-dev.txt
pytest -q
python scripts/validate_sources.py
```

`pytest.ini` keeps the repository root on the Python path, so no manual `PYTHONPATH` setting is required.

## Optional BGE-M3 semantic backend

```powershell
pip install -r requirements-embeddings.txt
$env:BAYYIN_AI_BACKEND="bge-m3"
$env:BAYYIN_EMBEDDING_MODEL="BAAI/bge-m3"
python -m uvicorn backend.main:app --reload
```

For a live demo, pre-download the model or use a local model path. If the embedding backend cannot load, BAYYIN falls back to the offline LSA backend.

## RAG provider configuration

RAG is part of BAYYIN's default pipeline. There is no `BAYYIN_RAG=on` switch. When the provider settings below are configured, BAYYIN automatically generates a short grounded explanation from evidence that has already passed retrieval and verification. If the provider is unavailable, BAYYIN falls back safely to the verified evidence report instead of failing.

Create a local `.env` from `.env.example`, then add the provider settings. BAYYIN uses an OpenAI-compatible `/chat/completions` endpoint.

Generic configuration:

```env
BAYYIN_RAG_API_BASE=https://YOUR-PROVIDER/v1
BAYYIN_RAG_API_KEY=YOUR_SECRET_KEY
BAYYIN_RAG_MODEL=YOUR_MODEL_NAME
BAYYIN_RAG_TIMEOUT=30
BAYYIN_RAG_MAX_TOKENS=220
```

Example for Groq:

```env
BAYYIN_RAG_API_BASE=https://api.groq.com/openai/v1
BAYYIN_RAG_API_KEY=YOUR_GROQ_API_KEY
BAYYIN_RAG_MODEL=openai/gpt-oss-120b
BAYYIN_RAG_TIMEOUT=30
BAYYIN_RAG_MAX_TOKENS=220
```

Do **not** commit a real key. `.env` is ignored by Git and is intentionally absent from the public ZIP; `.env.example` contains placeholders only.

Check runtime status with:

```text
GET /api/rag-status
```

Expected behavior:

- `enabled: true` when the provider URL, key, and model are configured.
- `mode: automatic` because no runtime toggle is required.
- If the generator is unavailable, source retrieval and verification continue normally and no generated explanation is shown.

## Deploy on Render

Use the repository root as the service root.

**Build command**

```bash
pip install -r backend/requirements.txt
```

**Start command**

```bash
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

After deployment, verify the web UI and these endpoints:

- `GET /api/health`
- `GET /api/ai-status`
- `GET /api/rag-status`
- `GET /api/knowledge-status`
- `GET /api/ai-evaluate`
- `GET /api/evaluate-robustness`

GitHub Actions runs the automated tests and source validation on pushes and pull requests.

## Public documentation

The repository keeps documentation needed to understand, verify, run, and review the project:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system design and AI / verification pipeline.
- [`docs/EVALUATION.md`](docs/EVALUATION.md) — evaluation methodology, results, and limitations.
- [`docs/SAFETY_AND_SCOPE.md`](docs/SAFETY_AND_SCOPE.md) — safety boundaries, abstention, specialist review, and known limitations.
- [`docs/SOURCES_AND_LICENSES.md`](docs/SOURCES_AND_LICENSES.md) — religious/knowledge sources, provenance, tools, and licenses.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — future work clearly separated from implemented features.

## License

BAYYIN's original project code is released under the license in [`LICENSE`](LICENSE). External source texts, translations, APIs, datasets, trademarks, and optional model weights remain subject to their own terms.
