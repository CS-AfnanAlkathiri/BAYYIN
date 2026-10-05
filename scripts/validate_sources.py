import json
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
sources=json.loads((ROOT/"data/sources.json").read_text(encoding="utf-8"))
assert len(sources)==12
for s in sources:
    host=urlparse(s["source_url"]).netloc
    assert s.get("provenance"), s["id"]
    assert s.get("verification_date")=="2026-10-01", s["id"]
    if s["source_type"]=="quran":
        assert host=="quranpedia.net", s["id"]
        assert s.get("translation_name")=="Sahih International", s["id"]
        assert s.get("translation_source"), s["id"]
        assert s.get("text_en_is_source_text") is False, s["id"]
    elif s["source_type"]=="hadith":
        assert host=="dorar.net", s["id"]
        assert s.get("grading_ar"), s["id"]
        assert s.get("grading_en"), s["id"]
        assert s.get("grading_source_url"), s["id"]
        assert s.get("grading_basis"), s["id"]
        assert s.get("grading_authority"), s["id"]
print(f"PASS: {len(sources)} source records satisfy the scientific data-alignment checks.")
