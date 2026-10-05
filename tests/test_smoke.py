from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def analyze(text, lang='auto'):
    return client.post('/api/analyze', json={'text': text, 'mode': 'auto', 'lang': lang})


def test_health():
    body = client.get('/api/health').json()
    assert body['ok'] is True
    assert all(body['checks'].values())


def test_known_quran_quote_has_traceable_source():
    body = analyze('إن جاءكم فاسق بنبإ فتبينوا').json()
    assert body['claims'][0]['status'] == 'source_match'
    assert body['claims'][0]['matches'][0]['id'] == 'quran-49-6'
    assert body['claims'][0]['matches'][0]['source_url'].startswith('https://')


def test_known_hadith_curated_case_links_correct_source_first():
    body = analyze('إنما الأعمال بالنيات').json()
    claim = body['claims'][0]
    assert claim['status'] == 'source_linked'
    assert claim['matches'][0]['id'] == 'hadith-bukhari-1'
    assert claim['curated_reference']['source_ids'] == ['hadith-bukhari-1']


def test_arabic_sensitive_ruling_routes_to_specialist():
    assert analyze('هل هذا الفعل حرام؟').json()['claims'][0]['status'] == 'specialist_review'


def test_arabic_ruling_phrase_without_loaded_word_routes_to_specialist():
    assert analyze('ما حكم الاستماع إلى الموسيقى؟').json()['claims'][0]['status'] == 'specialist_review'


def test_english_sensitive_ruling_routes_to_specialist():
    assert analyze('What is the ruling on listening to music?').json()['claims'][0]['status'] == 'specialist_review'


def test_keyword_inside_non_question_does_not_automatically_trigger_safety_gate():
    body = analyze('The post contains the word haram but asks only where the quotation comes from.').json()
    assert body['claims'][0]['status'] != 'specialist_review'


def test_english_known_hadith_matches():
    body = analyze('Actions are judged by intentions').json()
    assert body['lang'] == 'en'
    assert body['claims'][0]['matches'][0]['id'] == 'hadith-bukhari-1'


def test_unknown_claim_abstains():
    body = analyze('This sentence is not represented by any source in the current seed corpus.').json()
    assert body['claims'][0]['status'] == 'insufficient_evidence'
    assert body['claims'][0]['matches'] == []


def test_mixed_input_is_split_into_atomic_claims():
    body = analyze('إنما الأعمال بالنيات. إن جاءكم فاسق بنبإ فتبينوا.').json()
    assert body['claims_count'] == 2
    assert len(body['claims']) == 2


def test_specialist_result_does_not_surface_weak_distracting_matches():
    body = analyze('ما حكم الاستماع إلى الموسيقى؟').json()
    claim = body['claims'][0]
    assert claim['status'] == 'specialist_review'
    assert all(m['match_score'] >= 60 for m in claim['matches'])


def test_evidence_coverage_is_claim_level():
    body = analyze('إنما الأعمال بالنيات. This sentence is not represented by any source in the current seed corpus.').json()
    assert body['claims_count'] == 2
    assert body['evidence_coverage'] == 50


def test_stats_expose_mvp_evidence_and_evaluation_size():
    body = client.get('/api/stats').json()
    assert body['sources'] == 12
    assert body['curated_claims'] == 5
    assert body['evaluation_cases'] == 10


def test_sources_endpoint_exposes_provenance_and_review_status():
    body = client.get('/api/sources').json()
    assert len(body) == 12
    assert body[0]['provenance']
    assert body[0]['review_status'] == 'pending_specialist_review'


def test_evaluation_endpoint_returns_measured_metrics():
    body = client.get('/api/evaluate').json()
    assert body['evaluation_cases'] == 10
    assert 0 <= body['retrieval_hit_rate'] <= 100
    assert 0 <= body['safe_abstention_rate'] <= 100
    assert len(body['rows']) == 10


def test_feedback_accepts_valid_input():
    r = client.post('/api/feedback', json={'input_text': 'test claim', 'result_status': 'insufficient_evidence', 'helpful': True})
    assert r.status_code == 200
    assert r.json()['ok'] is True


def test_demo_endpoint():
    r = client.get('/api/demo/hadith?lang=en')
    assert r.status_code == 200
    assert 'intentions' in r.json()['text']


def test_source_policy_endpoint_exposes_integrated_and_expansion_sources():
    body = client.get('/api/source-policy').json()
    integrated = {row['id'] for row in body['integrated']}
    expansion = {row['id'] for row in body['documented_expansion']}
    assert {'quranpedia', 'quranenc', 'dorar'} <= integrated
    assert {'hadeethenc', 'terminologyenc'} <= expansion
