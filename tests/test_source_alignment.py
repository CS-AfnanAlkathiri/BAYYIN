import json
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]

def test_scientific_source_alignment():
    sources=json.loads((ROOT/"data/sources.json").read_text(encoding="utf-8"))
    assert len(sources)==12
    for s in sources:
        assert s["provenance"]
        if s["source_type"]=="quran":
            assert urlparse(s["source_url"]).netloc=="quranpedia.net"
            assert s["translation_name"]=="Sahih International"
            assert s["text_en_is_source_text"] is False
        else:
            assert urlparse(s["source_url"]).netloc=="dorar.net"
            assert s["grading_ar"] and s["grading_en"]
            assert s["grading_source_url"]
            assert s["grading_authority"]
