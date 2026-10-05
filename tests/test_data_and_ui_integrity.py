import json
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    return json.loads((ROOT / 'data' / name).read_text(encoding='utf-8'))


def test_source_ids_are_unique_and_all_declared_links_exist():
    sources = _load('sources.json')
    curated = _load('curated_claims.json')
    evaluation = _load('evaluation_cases.json')
    ids = [s['id'] for s in sources]
    assert len(ids) == len(set(ids))
    known = set(ids)
    for item in curated:
        assert set(item.get('source_ids', [])) <= known
    for case in evaluation:
        assert set(case.get('expected_source_ids', [])) <= known


def test_quran_records_have_required_scientific_package_metadata():
    for source in _load('sources.json'):
        if source['source_type'] != 'quran':
            continue
        assert urlparse(source['source_url']).netloc == 'quranpedia.net'
        assert source['text_ar'].strip()
        assert source['text_en'].strip()
        assert source['translation_name'] == 'Sahih International'
        assert 'Quranpedia' in source['translation_source']
        assert source['text_en_is_source_text'] is False
        assert source['provenance'] and source['verification_date']


def test_hadith_records_have_source_and_documented_grading():
    for source in _load('sources.json'):
        if source['source_type'] != 'hadith':
            continue
        assert urlparse(source['source_url']).netloc == 'dorar.net'
        assert source['text_ar'].strip()
        assert source['grading_ar'].strip()
        assert source['grading_en'].strip()
        assert urlparse(source['grading_source_url']).netloc == 'dorar.net'
        assert source['grading_basis'].strip()
        assert source['text_en_is_source_text'] is False


def test_home_has_only_three_core_quick_actions():
    html = (ROOT / 'frontend' / 'index.html').read_text(encoding='utf-8')
    assert html.count('data-demo=') == 3
    assert 'data-demo="verify"' in html
    assert 'data-demo="context"' in html
    assert 'data-demo="hadith"' in html
    assert 'sensitive_phrase' not in html


def test_duplicate_pipeline_strip_removed_and_accordion_has_hard_hidden_rule():
    html = (ROOT / 'frontend' / 'index.html').read_text(encoding='utf-8')
    css = (ROOT / 'frontend' / 'assets' / 'styles.css').read_text(encoding='utf-8')
    assert 'id="pipeline"' not in html
    assert '.trace-steps[hidden]{display:none!important}' in css


def test_frontend_no_longer_claims_ai_provides_evidence():
    js = (ROOT / 'frontend' / 'assets' / 'app.js').read_text(encoding='utf-8')
    html = (ROOT / 'frontend' / 'index.html').read_text(encoding='utf-8')
    bad_phrases = ['ذكاء اصطناعي يقدّم الدليل', 'AI provides evidence']
    assert all(p not in js and p not in html for p in bad_phrases)


def test_source_registry_reflects_latest_scientific_package_roles():
    registry = _load('source_registry.json')
    by_id = {row['id']: row for row in registry}
    assert by_id['quranpedia']['integrated'] is True
    assert by_id['quranenc']['integrated'] is True
    assert by_id['dorar']['integrated'] is True
    assert by_id['hadeethenc']['integrated'] is False
    assert by_id['terminologyenc']['integrated'] is False


def test_semantic_benchmark_source_links_are_valid():
    known = {s['id'] for s in _load('sources.json')}
    for case in _load('evaluation_regression.json'):
        assert set(case.get('expected_source_ids', [])) <= known


def test_frontend_explains_ai_as_semantic_retrieval_not_evidence_generation():
    js = (ROOT / 'frontend' / 'assets' / 'app.js').read_text(encoding='utf-8')
    assert 'Semantic retrieval + verification + bounded RAG' in js
    assert 'AI provides evidence' not in js
    assert '% need review' not in js
