from pathlib import Path

from fastapi.testclient import TestClient
from backend.main import app, analyze_one, demo, judge_evidence, knowledge_status

client = TestClient(app)


def test_home_ai_explanation_is_collapsible_and_result_process_is_unified():
    html = Path('frontend/index.html').read_text(encoding='utf-8')
    js = Path('frontend/assets/app.js').read_text(encoding='utf-8')
    assert 'id="aiRoleToggle"' in html
    assert 'id="aiRoleBody" hidden' in html
    assert 'process-box' in html
    assert 'process-toggle' in html
    assert 'trace-box' not in html
    assert 'ai-contribution"' not in html
    assert "How did BAYYIN reach this result?" in js


def test_svg_icons_replace_placeholder_glyphs():
    html = Path('frontend/index.html').read_text(encoding='utf-8')
    assert html.count('<svg viewBox="0 0 24 24">') >= 6
    assert '>◇<' not in html
    assert '>◌<' not in html


def test_knowledge_status_exposes_hybrid_bounded_knowledge_layer():
    data = knowledge_status()
    assert data['architecture'] == 'hybrid approved knowledge layer'
    assert data['local_curated_records'] >= 12
    assert data['approved_source_families'] >= 8
    assert data['integrated_source_families'] >= 3
    assert 'no open-web evidence' in data['retrieval_policy']
    assert data['rag_status']['implemented'] is True
    assert data['rag_status']['generation_policy'].startswith('The generator receives only evidence')


def test_knowledge_status_endpoint():
    r = client.get('/api/knowledge-status')
    assert r.status_code == 200
    assert r.json()['integrated_source_families'] >= 3


def test_semantic_context_demo_still_shows_ai_value():
    for lang in ('ar', 'en'):
        text = demo('context', lang)['text']
        result = analyze_one(text, lang, 'auto', allow_live=False)
        assert result['status'] == 'context_needed'
        assert result['matches'][0]['id'] == 'hadith-muslim-5'
        assert result['ai_explanation']['value_added_over_lexical_baseline'] is True


def test_judge_evidence_explains_core_ai_role():
    evidence = judge_evidence()
    assert 'Meaning-level retrieval' in evidence['implemented_now']['ai_role']
    assert evidence['measurable_evidence']['ai_vs_lexical']['cases'] >= 40
    assert any('free-form religious answer generation' in x for x in evidence['future_work_not_claimed_as_implemented'])
