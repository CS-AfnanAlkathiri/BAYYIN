# Safety and Scope

BAYYIN is a source-verification tool. It is not a fatwa system.

## Core boundaries

- Religious source text is kept separate from BAYYIN's analysis.
- BAYYIN does not invent evidence when no reliable source is found.
- Weak or irrelevant semantic associations are suppressed by a relevance gate.
- `insufficient_evidence` returns no attributed source.
- Personal or specialist ruling requests are routed to `specialist_review`.
- A real citation may return `citation_mismatch` when the attached claim is not supported by the cited text.
- Live hadith responses are sanitized before display; raw API HTML is never shown as religious text.
- The semantic model retrieves and ranks candidates; it does not generate Qur'an, hadith, grading, tafsir, or independent rulings.

## Result states

- `source_match` — strong wording/reference verification.
- `source_linked` — curated linked source/evaluation case.
- `context_needed` — a relevant source exists, but similarity alone does not establish the intended meaning.
- `citation_mismatch` — cited reference found, attached claim not supported by it.
- `insufficient_evidence` — no sufficiently reliable evidence; no source is attributed.
- `specialist_review` — qualified religious judgment is required.

## Human-in-the-loop

Human review is not presented as a separate user feature. It is a safety behavior that appears when the system detects that the request requires qualified religious judgment or when evidence is insufficient for a responsible conclusion.

## Public-deployment boundary

The competition build demonstrates the verification architecture and safety behavior. A larger corpus, final content policy, thresholds, context notes, and public-deployment procedures require qualified scholarly review before production use.

## Explicit-reference limitation

BAYYIN currently uses semantic retrieval plus deterministic lexical/provenance checks; it does not contain a validated natural-language-inference model for general contradiction detection. A claim can reuse many words from a cited verse while reversing its meaning. To avoid presenting that case as confidently verified, any explicit Qur'an reference accompanied by additional claim text is capped at `context_needed` unless the deterministic mismatch rules already identify a citation mismatch. This conservative policy is deliberate and should be replaced only after a dedicated entailment/contradiction component is independently evaluated.

## RAG safety boundary

The V7 generator is an automatic post-verification explanation layer when configured, not a religious answering engine. It is skipped for `specialist_review` and `insufficient_evidence`, sees only admitted evidence, and cannot create source text or grading. If generation is unavailable or fails validation, BAYYIN falls back to the source-linked verification report without generated prose.
