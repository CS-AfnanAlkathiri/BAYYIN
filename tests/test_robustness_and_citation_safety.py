import os
os.environ.setdefault('BAYYIN_LIVE_SOURCES','off')

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def analyze(text, lang='en'):
    r=client.post('/api/analyze',json={'text':text,'lang':lang,'mode':'auto'})
    assert r.status_code==200
    return r.json()['claims'][0]

def test_out_of_corpus_abstains_without_sources():
    for text,lang in [
        ('Fasting in Ramadan is obligatory','en'),
        ('The Prophet said God loves the one who insults his neighbor','en'),
        ('كل مسلم يجب أن يملك حصانا','ar'),
    ]:
        c=analyze(text,lang)
        assert c['status']=='insufficient_evidence'
        assert c['matches']==[]

def test_clean_quran_paraphrase_retrieves_correct_source():
    c=analyze('Verify every news before acting','en')
    assert c['status'] in {'context_needed','source_match','source_linked'}
    assert c['matches'][0]['id']=='quran-49-6'

def test_explicit_real_reference_false_claim_is_mismatch():
    c=analyze('Allah said: lying is permitted whenever it benefits you (Quran 49:6)','en')
    assert c['status']=='citation_mismatch'
    assert len(c['matches'])==1
    assert c['matches'][0]['id']=='quran-49-6'

def test_reference_only_verifies_exact_reference():
    c=analyze('Quran 49:6','en')
    assert c['status']=='source_match'
    assert c['matches'][0]['id']=='quran-49-6'

def test_robustness_endpoint_reports_false_lead_metric():
    data=client.get('/api/evaluate-robustness').json()
    assert data['cases'] >= 50
    assert data['out_of_corpus_false_lead_rate'] == 0.0
    assert data['explicit_citation_mismatch_detection_rate'] == 100.0
