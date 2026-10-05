from fastapi.testclient import TestClient

from backend import live_sources
from backend.main import app

client = TestClient(app)


def test_demo_direct_quote_is_exactly_traceable_ar():
    demo = client.get('/api/demo/verify?lang=ar').json()['text']
    result = client.post('/api/analyze', json={'text': demo, 'mode': 'auto', 'lang': 'ar'}).json()
    assert result['claims'][0]['status'] == 'source_match'
    assert result['claims'][0]['matches'][0]['id'] == 'quran-49-6'


def test_demo_direct_quote_is_traceable_en():
    demo = client.get('/api/demo/verify?lang=en').json()['text']
    result = client.post('/api/analyze', json={'text': demo, 'mode': 'auto', 'lang': 'en'}).json()
    assert result['claims'][0]['matches'][0]['id'] == 'quran-49-6'
    assert result['claims'][0]['matches'][0]['match_score'] >= 92


def test_context_demo_really_returns_context_needed():
    for lang in ('ar', 'en'):
        demo = client.get(f'/api/demo/context?lang={lang}').json()['text']
        result = client.post('/api/analyze', json={'text': demo, 'mode': 'auto', 'lang': lang}).json()
        assert result['claims'][0]['status'] == 'context_needed'
        assert result['claims'][0]['matches'][0]['id'] == 'hadith-muslim-5'


def test_sensitive_quick_demo_was_removed_but_safety_gate_remains():
    assert client.get('/api/demo/sensitive_phrase?lang=ar').status_code == 404
    result = client.post('/api/analyze', json={'text': 'ما حكم الاستماع إلى الموسيقى؟', 'mode': 'auto', 'lang': 'ar'}).json()
    assert result['claims'][0]['status'] == 'specialist_review'


def test_analysis_exposes_bilingual_dynamic_copy():
    result = client.post('/api/analyze', json={'text': 'إنما الأعمال بالنيات', 'mode': 'auto', 'lang': 'ar'}).json()
    display = result['claims'][0]['display']
    assert display['ar']['label']
    assert display['en']['label']
    assert display['ar']['reason'] != display['en']['reason']


def test_trace_is_semantic_and_language_independent():
    result = client.post('/api/analyze', json={'text': 'إنما الأعمال بالنيات', 'mode': 'auto', 'lang': 'ar'}).json()
    keys = [step['detail_key'] for step in result['claims'][0]['trace']]
    assert keys == ['split', 'trace_ai', 'context', 'explain']


def test_dorar_dict_shape_does_not_crash(monkeypatch):
    monkeypatch.setattr(live_sources, 'ENABLED', True)
    monkeypatch.setattr(live_sources, '_get_json', lambda _url: {'data': {'ahadith': {'0': {'th': 'إنما الأعمال بالنيات'}, '1': {'th': 'فليقل خيرا أو ليصمت'}}}})
    rows = live_sources.dorar_search('إنما الأعمال بالنيات', limit=1)
    assert len(rows) == 1
    assert rows[0]['source_type'] == 'hadith'
    assert rows[0]['text_ar'] == 'إنما الأعمال بالنيات'


def test_quranpedia_wrapped_shapes_are_tolerated(monkeypatch):
    monkeypatch.setattr(live_sources, 'ENABLED', True)
    responses = iter([
        {'data': {'text': 'يَا أَيُّهَا الَّذِينَ آمَنُوا'}},
        {'translation': 'O you who have believed', 'sura': 49, 'aya': 6},
    ])
    monkeypatch.setattr(live_sources, '_get_json', lambda _url: next(responses))
    row = live_sources.quranpedia_ayah(49, 6)
    assert row is not None
    assert row['text_ar'].startswith('يَا')
    assert row['text_en'] == 'O you who have believed'
    assert row['translation_source'].startswith('QuranEnc.com')
    assert row['match_trace']['exact_reference'] is True


def test_english_named_quran_reference_is_recognized():
    assert live_sources.extract_quran_reference('Al-Hujurat 6') == (49, 6)


def test_quran_translation_falls_back_to_quranpedia_when_quranenc_fails(monkeypatch):
    monkeypatch.setattr(live_sources, 'ENABLED', True)
    def fake(url):
        if '/mushafs/' in url:
            return {'text': 'نص الآية'}
        if 'quranenc.com' in url:
            raise ValueError('temporary')
        return [{'book': {'id': 1947, 'name': 'Saheeh International'}, 'translation-content': 'Fallback translation'}]
    monkeypatch.setattr(live_sources, '_get_json', fake)
    row = live_sources.quranpedia_ayah(49, 6)
    assert row['text_en'] == 'Fallback translation'
    assert row['translation_source'].startswith('Quranpedia.net')


def test_dorar_html_fragment_is_sanitized(monkeypatch):
    monkeypatch.setattr(live_sources, 'ENABLED', True)
    html = '<head><link rel="canonical" href="https://dorar.net/x"></head><div><span class="hadith">1 - كفى بالمرء كذبا أن يحدث بكل ما سمع</span><span>الراوي : أبو هريرة</span><span>المحدث : مسلم</span><span>خلاصة حكم المحدث : صحيح</span></div>'
    monkeypatch.setattr(live_sources, '_get_json', lambda _url: {'data': {'ahadith': [{'th': html}]}})
    rows = live_sources.dorar_search('كفى بالمرء كذبا', limit=1)
    assert len(rows) == 1
    assert '<' not in rows[0]['text_ar'] and '>' not in rows[0]['text_ar']
    assert rows[0]['text_ar'].startswith('كفى بالمرء')
    assert rows[0]['hadith_grading_ar'] == 'صحيح'


def test_ai_status_is_real_and_bounded():
    body = client.get('/api/ai-status').json()
    assert body['enabled'] is True
    assert 'TruncatedSVD' in body['method']
    assert body['generates_religious_content'] is False
    assert body['languages']['ar']['ready'] is True
    assert body['languages']['en']['ready'] is True


def test_ai_hybrid_benchmark_beats_or_matches_lexical_baseline():
    body = client.get('/api/ai-evaluate').json()
    assert body['cases'] >= 10
    assert body['ai_hybrid_paraphrase_top3_hit_rate'] >= body['baseline_paraphrase_top3_hit_rate']
    assert body['ai_hybrid_false_lead_rate'] <= body['baseline_false_lead_rate']
    assert 'not religious accuracy' in body['scope']
