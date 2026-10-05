# Evaluation

BAYYIN separates engineering evaluation from religious or scholarly validation.

## Regression dataset

The file is intentionally named `evaluation_regression.json`: these cases were authored during development and may have influenced thresholds. They are therefore a regression suite, not an independent holdout benchmark.


`data/evaluation_regression.json` contains 60 developer-authored engineering cases:

- 36 paraphrase-retrieval cases,
- 12 out-of-corpus / adversarial cases,
- 12 explicit-reference mismatch cases.

These cases are used to test retrieval behavior, false leads, abstention, and citation handling. They are not a scholarly benchmark.

## Current reproducible results

With the default offline LSA backend:

- overall behavioral pass rate: **90.0%**,
- paraphrase top-match rate: **83.3%**,
- out-of-corpus safe abstention: **100.0%**,
- out-of-corpus false-lead rate: **0.0%**,
- explicit-citation mismatch detection: **100.0%**.

`GET /api/evaluate-robustness` reproduces these measurements with live-source calls disabled for consistency.

## Baseline vs AI

On the 48 retrieval/abstention cases used for the comparison:

- lexical-only paraphrase top-3 hit rate: **55.6%**,
- AI-hybrid paraphrase top-3 hit rate: **83.3%**,
- lexical-only false-lead rate on the 12 out-of-corpus cases: **0.0%**,
- AI-hybrid false-lead rate: **0.0%**.

`GET /api/ai-evaluate` reproduces the comparison.

## What these metrics mean

The comparison tests the specific engineering hypothesis that semantic retrieval can recover relevant approved sources for paraphrases better than lexical-only retrieval without increasing false source leads on the included adversarial cases.

The numbers do **not** mean:

- religious accuracy,
- scholarly certification,
- comprehensive coverage of Islamic knowledge,
- production-scale validation,
- independent external evaluation.

## Next validation steps

Before production-scale public deployment:

1. expand the corpus using approved, provenance-preserving source ingestion,
2. freeze retrieval thresholds,
3. create an independent evaluation set that was not written during model development,
4. conduct qualified scholarly review of content policy and source mappings,
5. run user testing for task completion, clarity, and trust calibration.

## RAG evaluation scope

V7 adds regression tests for the RAG boundary: safe fallback when no generator is configured, evidence-only prompt construction, rejection of direct ruling-style generation, and automatic skip for specialist-review cases. These tests verify the integration contract and safety behavior; they do not establish theological correctness or independent scholarly validation. A larger human-reviewed grounded-generation benchmark remains future work.
