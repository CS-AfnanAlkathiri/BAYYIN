const $ = (s, r=document) => r.querySelector(s);
const input = $('#claimInput');
const home = $('#homeView');
const loading = $('#loadingView');
const result = $('#resultView');
const claimsList = $('#claimsList');
const template = $('#claimTemplate');
const errorBanner = $('#errorBanner');
const errorText = $('#errorText');
const htmlRoot = $('#htmlRoot');
const langToggle = $('#langToggle');
const loadingStep = $('#loadingStep');
let lastPayload = null;
let loadingTimer = null;

const STRINGS = {
  ar: {
    brand_subtitle:'تتبّع المصدر. افهم السياق.', feature1_title:'تحقق مرتبط بالمصدر', feature1_sub:'مرجع ظاهر وقابل للفتح', feature2_title:'السياق قبل الاستنتاج', feature2_sub:'التشابه وحده لا يثبت المعنى', feature3_title:'حدود واضحة', feature3_sub:'نتوقف عندما لا تكفي المصادر', rail_quote:'«فتبيّنوا»', safe_pill:'استرجاع دلالي + تحقق + RAG مقيد بالمصدر', home_eyebrow:'تحقق من المحتوى الإسلامي', heading:'تحقّق من الادعاء<br><span>بوضوح وهدوء.</span>', lead:'ألصق اقتباسًا أو منشورًا أو ادعاءً، وبيّن يساعدك في تتبّع مصدره وفحص مطابقته وسياقه وبيان حدود النتيجة.', ai_role_title:'كيف يعمل بيّن؟', ai_role_sub:'ذكاء اصطناعي للاسترجاع بالمعنى، ثم تحقق مستقل، ومع تفعيل RAG يشرح النتيجة اعتمادًا على الأدلة المقبولة فقط.', ai_stage_split:'1 فهم الادعاء', ai_stage_retrieve:'2 AI: استرجاع بالمعنى', ai_stage_verify:'3 تحقق من النص والمصدر', ai_stage_decide:'4 سياق / امتناع / إحالة', ai_role_boundary:'الذكاء الاصطناعي يسترجع ويرتب المرشحين؛ وRAG — عند تفعيله — يشرح فقط الأدلة التي اجتازت التحقق. لا يُنشئ نصًا شرعيًا ولا يصدر حكمًا؛ المصدر المعتمد هو المرجع.', process_label:'كيف عمل بيّن في هذه النتيجة؟', ai_flow_understand:'فهم الادعاء', ai_flow_retrieve:'استرجاع دلالي', ai_flow_verify:'تحقق مستقل', ai_flow_gate:'بوابة الصلة', ai_flow_decision:'قرار آمن', ai_model_prefix:'النموذج', quick_section_title:'تجارب سريعة', quick_section_sub:'ثلاث طرق لرؤية كيف يعمل التحقق', quick_verify_title:'تحقق من اقتباس', quick_verify_sub:'تتبّع نصًا إلى مصدره', quick_context_title:'افحص السياق', quick_context_sub:'اعرف متى لا يكفي التشابه', quick_hadith_title:'تتبّع حديثًا', quick_hadith_sub:'اعرض المصدر والحكم الموثق', composer_placeholder:'ألصق اقتباسًا أو منشورًا أو ادعاءً…', analyze_aria:'تحليل', shortcut:'Ctrl/⌘ + Enter', fineprint:'بيّن يتحقق من المصادر والسياق — ولا يصدر فتوى أو حكمًا شرعيًا مستقلًا.', loading_title:'نتتبّع المصدر…', loading_step_1:'نفصل الادعاء ونسترجع المصادر دلاليًا بالذكاء الاصطناعي.', loading_step_2:'نتحقق من الصياغة نصيًا ونقارنها بالمصدر الأصلي.', loading_step_3:'نراجع السياق وحدود ما يمكن استنتاجه.', close_aria:'إغلاق', back_label:'تحقق من نص آخر', result_eyebrow:'نتيجة التحقق', result_title:'ماذا وجد بيّن؟', result_disclaimer_bold:'حدود الأداة', result_disclaimer_text:'بيّن يتتبّع المصادر ويعرض السياق وحدود الثقة. المسائل التي تحتاج حكمًا متخصصًا تُحال إلى مختص مؤهل.', feedback_prompt:'هل كانت النتيجة مفيدة؟', feedback_up_aria:'النتيجة مفيدة', feedback_down_aria:'النتيجة غير مفيدة', no_evidence:'لم يظهر تطابق موثوق في مجموعة المصادر الحالية. لا يعني ذلك أن النص غير موجود؛ بل يعني أن بيّن لا يملك الآن مصدرًا كافيًا لعرضه كنتيجة موثقة.', open_source:'فتح المصدر ↗', match_score_label:'إشارة المطابقة النصية', ai_semantic_label:'صلة دلالية بالذكاء الاصطناعي', signal_exact:'مطابق', signal_strong:'قوية', signal_medium:'متوسطة', signal_low:'محدودة', trace_label:'تفاصيل التحقق', source_quran:'قرآن', source_hadith:'حديث', provenance:'التتبّع', live_source:'مصدر مباشر', method:'طريقة الاسترجاع', translation_source:'مصدر الترجمة', grading:'حكم الحديث', primary_text:'النص الأصلي', approved_translation:'الترجمة المعتمدة', display_rendering:'صياغة العرض بالإنجليزية', context_label:'السياق وحدود النتيجة', exact:'تطابق مباشر', hybrid:'مطابقة هجينة', curated:'ربط مرجعي', live_quran:'مرجع قرآني مباشر', live_hadith:'بحث حديث مباشر', keywords:'كلمات متطابقة', conf_high:'مطابقة قوية', conf_medium:'تحتاج سياقًا', conf_low:'ثقة محدودة', conf_mismatch:'تعارض مع المرجع', conf_none:'لا توجد مطابقة موثوقة', conf_specialist:'مراجعة مختص', claims_meta:n=>n===1?'ادعاء واحد':`${n} ادعاءات`, review_meta:n=>n?'توجد حالة تحتاج مراجعة':'لا توجد إحالة إلزامية', input_lang_ar:'النص: عربي', input_lang_en:'النص: إنجليزي', error_generic:'تعذر إكمال التحقق. يمكنك المحاولة مرة أخرى؛ وإذا تعذر المصدر المباشر فسيستمر بيّن بالمصادر المحلية المتاحة.', error_timeout:'استغرق الاتصال بالمصدر وقتًا أطول من المتوقع. حاولي مرة أخرى.', trace:{split:'فصل الادعاء إلى وحدة قابلة للفحص.', trace_ai:'استرجاع دلالي بنموذج NLP داخل المصادر المعتمدة، ثم تحقق نصي حتمي من الصياغة.', trace_curated:'البحث في المصادر المعتمدة بالمطابقة النصية الحتمية.', trace_live:'تم فحص مصدر مباشر معتمد بعد البحث المحلي.', trace_specialist:'قد تظهر مصادر مرتبطة، لكن بوابة الأمان تمنع إصدار حكم آلي.', trace_reference:'تمت قراءة المرجع الصريح أولًا قبل أي استرجاع مفتوح.', verify_reference:'قورنت صياغة الادعاء بالنص الموجود في المرجع المذكور.', verify_gate:'لا يظهر أي مصدر إلا بعد اجتياز بوابة الصلة والمطابقة.', context:'التشابه النصي لا يُعامل كدليل كافٍ على المعنى في سياقه.', explain:'عرض المصدر والسياق وحدود الثقة بوضوح.'}, statusIcons:{source_match:'✓',source_linked:'✓',context_needed:'≈',possible_lead:'?',citation_mismatch:'!',insufficient_evidence:'—',specialist_review:'◇'}, rag_title:'شرح مولّد ومقيد بالمصادر', rag_refs:'المراجع المستخدمة', source_unknown:'مصدر'
  },
  en: {
    brand_subtitle:'Trace claims. Check context.', feature1_title:'Source-linked verification', feature1_sub:'Visible, openable references', feature2_title:'Context before conclusion', feature2_sub:'Similarity alone does not prove meaning', feature3_title:'Clear limits', feature3_sub:'Stop when the sources are not enough', rail_quote:'“Verify it.”', safe_pill:'Semantic retrieval + verification + bounded RAG', home_eyebrow:'Islamic content verification', heading:'Check a claim<br><span>with clarity.</span>', lead:'Paste a quote, post, or claim. BAYYIN helps trace its source, check the match and context, and show the limits of the result.', ai_role_title:'How does BAYYIN work?', ai_role_sub:'AI retrieves by meaning, an independent layer verifies each candidate, and optional bounded RAG explains only admitted evidence.', ai_stage_split:'1 Understand the claim', ai_stage_retrieve:'2 AI: retrieve by meaning', ai_stage_verify:'3 Verify wording + source', ai_stage_decide:'4 Context / abstain / refer', ai_role_boundary:'AI retrieves and ranks candidates; optional RAG explains only verified evidence. It does not create religious source text or issue rulings; the approved source remains the authority.', process_label:'How did BAYYIN reach this result?', ai_flow_understand:'Claim understanding', ai_flow_retrieve:'Semantic retrieval', ai_flow_verify:'Independent verification', ai_flow_gate:'Relevance gate', ai_flow_decision:'Safe decision', ai_model_prefix:'Model', quick_section_title:'Quick examples', quick_section_sub:'Three ways to see the verification workflow', quick_verify_title:'Verify a quote', quick_verify_sub:'Trace text back to its source', quick_context_title:'Check context', quick_context_sub:'See when similarity is not enough', quick_hadith_title:'Trace a hadith', quick_hadith_sub:'Show the source and documented grading', composer_placeholder:'Paste a quote, post, or claim…', analyze_aria:'Analyze', shortcut:'Ctrl/⌘ + Enter', fineprint:'BAYYIN checks sources and context — it does not issue independent fatwas or religious rulings.', loading_title:'Tracing the source…', loading_step_1:'Splitting the claim and using AI semantic retrieval over approved sources.', loading_step_2:'Verifying the wording lexically against the original source text.', loading_step_3:'Checking context and the limits of what can be concluded.', close_aria:'Close', back_label:'Check another text', result_eyebrow:'Verification result', result_title:'What did BAYYIN find?', result_disclaimer_bold:'Tool boundary', result_disclaimer_text:'BAYYIN traces sources and surfaces context and confidence limits. Questions requiring specialist judgment are referred to a qualified specialist.', feedback_prompt:'Was this result helpful?', feedback_up_aria:'Result was helpful', feedback_down_aria:'Result was not helpful', no_evidence:'No reliable match appeared in the current source set. This does not mean the text does not exist; it means BAYYIN does not currently have enough source evidence to present a verified match.', open_source:'Open source ↗', match_score_label:'Text-match signal', ai_semantic_label:'AI semantic relevance', signal_exact:'Exact', signal_strong:'Strong', signal_medium:'Moderate', signal_low:'Limited', trace_label:'Verification details', source_quran:'Qur’an', source_hadith:'Hadith', provenance:'Source record', live_source:'Live source', method:'Retrieval method', translation_source:'Translation source', grading:'Hadith grading', primary_text:'Primary source text', approved_translation:'Approved translation', display_rendering:'English display rendering', context_label:'Context and result limits', exact:'Direct match', hybrid:'Hybrid matching', curated:'Curated reference link', live_quran:'Live Qur’an reference', live_hadith:'Live hadith search', keywords:'Matched keywords', conf_high:'Strong match', conf_medium:'Context needed', conf_low:'Limited confidence', conf_mismatch:'Reference mismatch', conf_none:'No reliable match', conf_specialist:'Specialist review', claims_meta:n=>n===1?'1 claim':`${n} claims`, review_meta:n=>n?'Review is required for at least one case':'No required referral', input_lang_ar:'Input: Arabic', input_lang_en:'Input: English', error_generic:"Couldn't complete the verification. You can try again; if a live source is unavailable, BAYYIN will continue with the local approved source set.", error_timeout:'The source request took longer than expected. Please try again.', trace:{split:'The text was isolated into an atomic claim for checking.', trace_ai:'A bounded NLP model performed latent-semantic retrieval over the approved source set, followed by deterministic lexical verification.', trace_curated:'The approved source set was searched with deterministic lexical matching.', trace_live:'An approved live source was checked after local retrieval.', trace_specialist:'Related sources may be shown, but the safety gate prevents an automated ruling.', trace_reference:'The explicit citation was resolved before open-ended retrieval.', verify_reference:'The attached claim wording was compared against the cited source text.', verify_gate:'A source is surfaced only after passing the relevance and verification gate.', context:'Textual similarity is not treated as sufficient proof of contextual meaning.', explain:'The source, context, and confidence limits are shown explicitly.'}, statusIcons:{source_match:'✓',source_linked:'✓',context_needed:'≈',possible_lead:'?',citation_mismatch:'!',insufficient_evidence:'—',specialist_review:'◇'}, rag_title:'Grounded generated explanation', rag_refs:'Evidence used', source_unknown:'Source'
  }
};

let uiLang = localStorage.getItem('bayyin:lang') || 'ar';
function applyStaticStrings(){
  const d=STRINGS[uiLang];
  document.querySelectorAll('[data-i18n]').forEach(el=>{ const v=d[el.dataset.i18n]; if(v!==undefined) el.textContent=v; });
  document.querySelectorAll('[data-i18n-html]').forEach(el=>{ const v=d[el.dataset.i18nHtml]; if(v!==undefined) el.innerHTML=v; });
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el=>{ const v=d[el.dataset.i18nPlaceholder]; if(v!==undefined) el.placeholder=v; });
  document.querySelectorAll('[data-i18n-aria]').forEach(el=>{ const v=d[el.dataset.i18nAria]; if(v!==undefined) el.setAttribute('aria-label',v); });
  htmlRoot.lang=uiLang; htmlRoot.dir=uiLang==='ar'?'rtl':'ltr'; langToggle.textContent=uiLang==='ar'?'EN':'AR';
}
function setLang(lang){ uiLang=lang; localStorage.setItem('bayyin:lang',lang); applyStaticStrings(); if(lastPayload) render(lastPayload); loadStats(); }
langToggle.addEventListener('click',()=>setLang(uiLang==='ar'?'en':'ar'));
applyStaticStrings();

const aiRoleToggle=$('#aiRoleToggle');
const aiRoleBody=$('#aiRoleBody');
if(aiRoleToggle && aiRoleBody){
  aiRoleToggle.addEventListener('click',()=>{
    const willOpen=aiRoleBody.hidden;
    aiRoleBody.hidden=!willOpen;
    aiRoleToggle.setAttribute('aria-expanded',String(willOpen));
    const symbol=aiRoleToggle.querySelector('.accordion-symbol');
    if(symbol) symbol.textContent=willOpen?'−':'+';
  });
}

function show(view){[home,loading,result].forEach(v=>v.classList.remove('active'));view.classList.add('active');}
function escapeHTML(s=''){return String(s).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));}
function confidenceLabel(c,status){const d=STRINGS[uiLang];if(status==='citation_mismatch')return d.conf_mismatch;if(status==='insufficient_evidence')return d.conf_none;if(status==='specialist_review')return d.conf_specialist;return c==='high'?d.conf_high:c==='medium'?d.conf_medium:d.conf_low;}
function showError(msg){errorText.textContent=msg;errorBanner.hidden=false;}
function hideError(){errorBanner.hidden=true;}
function sourceKind(m){const d=STRINGS[uiLang];return m.source_type==='quran'?d.source_quran:m.source_type==='hadith'?d.source_hadith:d.source_unknown;}
function localizedClaimText(claim, key){const display=claim.display||{};return (display[uiLang]&&display[uiLang][key])||claim[key]||'';}
function traceDetail(step){const d=STRINGS[uiLang]; return d.trace[step.detail_key] || step.detail || '';}
function retrievalLabel(trace={}){const d=STRINGS[uiLang];const r=trace.retrieval||'';if(r==='exact_phrase'||r==='explicit_quran_reference'||r==='explicit_reference_verification')return d.exact;if(r==='curated_evaluation_link')return d.curated;if(r==='quranpedia_live_reference')return d.live_quran;if(r==='dorar_live_api')return d.live_hadith;if(r==='hybrid_ai_semantic_lexical')return uiLang==='ar'?'استرجاع دلالي بالذكاء الاصطناعي + تحقق نصي':'AI semantic retrieval + lexical verification';if(r==='semantic_candidate_verified_by_gate')return uiLang==='ar'?'مرشح دلالي قوي اجتاز بوابة الصلة':'Strong semantic candidate that passed the relevance gate';return d.hybrid;}
function signalLabel(score, exact=false){const d=STRINGS[uiLang];if(exact)return d.signal_exact;const n=Number(score);return n>=85?d.signal_strong:n>=65?d.signal_medium:d.signal_low;}
function safeUrl(url=''){try{const u=new URL(url,window.location.origin);return ['http:','https:'].includes(u.protocol)?u.href:'#';}catch{return '#';}}

async function loadStats(){
  try{
    const r=await fetch('/api/stats'); if(!r.ok) return;
    const s=await r.json(); const el=$('#mvpStats');
    el.textContent=uiLang==='ar'?`${s.source_registry_entries} عائلات مصادر معتمدة · ${s.live_sources.length} وصلات مباشرة · ${s.robustness_evaluation_cases} حالة اختبار`:`${s.source_registry_entries} approved source families · ${s.live_sources.length} live connectors · ${s.robustness_evaluation_cases} robustness cases`;
  }catch{}
}
loadStats();

function startLoading(){
  clearInterval(loadingTimer); const d=STRINGS[uiLang]; const steps=[d.loading_step_1,d.loading_step_2,d.loading_step_3]; let i=0; loadingStep.textContent=steps[0];
  loadingTimer=setInterval(()=>{i=(i+1)%steps.length;loadingStep.textContent=steps[i];},1100);
}
function stopLoading(){clearInterval(loadingTimer);loadingTimer=null;}

const ANALYZE_TIMEOUT_MS=18000;
async function analyze(){
  const text=input.value.trim(); if(!text){input.focus();return;}
  hideError();show(loading);startLoading();
  const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),ANALYZE_TIMEOUT_MS);
  try{
    const r=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,mode:'auto',lang:'auto'}),signal:controller.signal});
    if(!r.ok){let detail='';try{detail=(await r.json()).detail||'';}catch{}throw new Error(detail||'API error');}
    const data=await r.json();lastPayload=data;render(data);show(result);
  }catch(e){show(home);showError(e.name==='AbortError'?STRINGS[uiLang].error_timeout:STRINGS[uiLang].error_generic);}finally{clearTimeout(timeout);stopLoading();}
}

function buildSourceBlock(m){
  const d=STRINGS[uiLang]; const trace=m.match_trace||{}; const title=uiLang==='en'?(m.title_en||m.title_ar):(m.title_ar||m.title_en); const context=uiLang==='en'?(m.context_en||m.context_ar):(m.context_ar||m.context_en);
  const el=document.createElement('section');el.className='evidence';
  const head=document.createElement('div');head.className='evidence-head';
  const headText=document.createElement('div');headText.innerHTML=`<b class="evidence-title">${escapeHTML(title)}</b><div class="evidence-ref">${escapeHTML(m.reference||'')}</div><div class="source-kind">${escapeHTML(sourceKind(m))}</div>`;
  const link=document.createElement('a');link.target='_blank';link.rel='noopener noreferrer';link.href=safeUrl(m.source_url);link.textContent=d.open_source;
  head.append(headText,link);el.appendChild(head);

  const sourceBlock=document.createElement('div');sourceBlock.className='source-block';
  const primaryLabel=document.createElement('div');primaryLabel.className='source-label';primaryLabel.textContent=d.primary_text;sourceBlock.appendChild(primaryLabel);
  const primary=document.createElement('div');primary.className='quote arabic';primary.dir='rtl';primary.textContent=m.text_ar||'';sourceBlock.appendChild(primary);
  if(uiLang==='en' && m.text_en){
    const trans=document.createElement('div');trans.className='translation-block';
    const transLabel=document.createElement('div');transLabel.className='source-label';transLabel.textContent=m.source_type==='quran'?d.approved_translation:d.display_rendering;
    const transText=document.createElement('div');transText.className='quote';transText.dir='ltr';transText.textContent=m.text_en;trans.append(transLabel,transText);sourceBlock.appendChild(trans);
  }
  el.appendChild(sourceBlock);

  if(context){const contextPanel=document.createElement('div');contextPanel.className='context-panel';contextPanel.innerHTML=`<b>${escapeHTML(d.context_label)}</b><p class="context">${escapeHTML(context)}</p>`;el.appendChild(contextPanel);}

  const meta=document.createElement('div');meta.className='evidence-meta';
  const addMeta=(txt,cls='')=>{if(!txt)return;const s=document.createElement('span');s.textContent=txt;if(cls)s.className=cls;meta.appendChild(s);};
  if(Number.isFinite(Number(m.lexical_score))) addMeta(`${d.match_score_label}: ${signalLabel(m.lexical_score, !!trace.exact_phrase)}`);
  if(Number.isFinite(Number(m.semantic_score)) && trace.ai_assisted) addMeta(`${d.ai_semantic_label}: ${signalLabel(m.semantic_score)}`,'ai-chip');
  addMeta(`${d.method}: ${retrievalLabel(trace)}`);
  if(trace.keyword_hits) addMeta(`${d.keywords}: ${trace.keyword_hits}`);
  if(m.source_type==='hadith' && (m.grading_ar||m.grading_en||m.hadith_grading_ar)) addMeta(`${d.grading}: ${uiLang==='ar'?(m.grading_ar||m.hadith_grading_ar||m.grading_en):(m.grading_en||m.hadith_grading_ar||m.grading_ar)}`);
  if(m.translation_source && uiLang==='en') addMeta(`${d.translation_source}: ${m.translation_source}`);
  if(m.source_platform) addMeta(m.source_platform);
  if(m.live_source) addMeta(d.live_source,'live-chip');
  el.appendChild(meta);return el;
}

function aiContributionText(ai={}){
  if(!ai || !ai.contribution) return '';
  const ar=uiLang==='ar';
  const map={
    semantic_recovery: ar?'وجد الذكاء الاصطناعي هذا المصدر بالمعنى رغم أن المطابقة اللفظية وحدها لم ترفعه ضمن أفضل النتائج. بعد ذلك تحققت طبقة مستقلة من الصياغة والمصدر قبل عرضه.':'AI recovered this source by meaning even though the lexical-only baseline did not surface it among the top results. An independent layer then checked wording and provenance before display.',
    semantic_ranking: ar?'رتّب الذكاء الاصطناعي المصادر المرشحة بحسب المعنى، ثم أكدت طبقة مستقلة المطابقة النصية والمصدر قبل عرض النتيجة.':'AI ranked candidate sources by meaning, then an independent layer verified wording and provenance before the result was shown.',
    reference_first: ar?'المرجع الصريح هو الذي حدد المصدر أولًا؛ لم يُسمح للذكاء الاصطناعي باستبداله. استُخدمت الإشارة الدلالية فقط كمقارنة مساعدة.':'The explicit citation selected the source first; AI was not allowed to replace it. The semantic signal was used only as a secondary comparison.',
    candidate_rejected: ar?'بحث الذكاء الاصطناعي دلاليًا داخل المصادر المعتمدة، لكن المرشح لم يجتز بوابة الصلة والتحقق؛ لذلك لم ينسب بيّن أي مصدر للادعاء.':'AI searched the approved sources by meaning, but the candidate did not pass the relevance/verification gate, so BAYYIN attributed no source.',
    no_candidate: ar?'لم يجد الاسترجاع الدلالي مرشحًا كافيًا، لذلك امتنع بيّن عن إظهار مصدر غير موثوق.':'Semantic retrieval did not find a sufficient candidate, so BAYYIN abstained from showing an unreliable source.',
    safety_override: ar?'يمكن للذكاء الاصطناعي استرجاع مواد ذات صلة، لكن بوابة الأمان تمنع تحويل ذلك إلى حكم شرعي آلي وتُحيل الحالة للمختص.':'AI may retrieve related material, but the safety gate prevents that from becoming an automated religious ruling and routes the case for specialist review.',
    lexical_or_curated_resolution: ar?'حُسمت هذه الحالة بمرجع مباشر أو تحقق نصي حتمي؛ لا يفرض بيّن استخدام الذكاء الاصطناعي عندما لا تكون هناك حاجة إليه.':'This case was resolved by a direct reference or deterministic text verification; BAYYIN does not force AI into a result when it is not needed.'
  };
  return map[ai.contribution]||'';
}

function aiModelLabel(ai={}){
  const d=STRINGS[uiLang];
  const b=ai.backend||'disabled';
  const label=b==='multilingual_embeddings'?'multilingual embeddings':(b==='lsa'?'offline LSA NLP':b);
  return `${d.ai_model_prefix}: ${label}`;
}

function render(data){
  const d=STRINGS[uiLang];
  const claimCount=$('#claimCount'); const reviewRate=$('#reviewRate'); const languageBadge=$('#languageBadge');
  claimCount.textContent=d.claims_meta(data.claims_count); claimCount.hidden=data.claims_count<=1;
  reviewRate.hidden=true;
  languageBadge.textContent=data.lang==='ar'?d.input_lang_ar:d.input_lang_en;
  claimsList.innerHTML='';
  data.claims.forEach(claim=>{
    const node=template.content.cloneNode(true);const card=node.querySelector('.claim-card');card.classList.add(`status-${claim.status}`);
    const icon=node.querySelector('.status-icon');icon.textContent=d.statusIcons[claim.status]||'•';
    node.querySelector('.status-label').textContent=localizedClaimText(claim,'label');
    node.querySelector('.claim-text').textContent=claim.claim;
    node.querySelector('.confidence').textContent=confidenceLabel(claim.confidence,claim.status);
    node.querySelector('.reason').textContent=localizedClaimText(claim,'reason');

    const ragBox=node.querySelector('.rag-box');
    if(claim.rag_explanation?.used && claim.rag_explanation?.text){
      ragBox.hidden=false;
      ragBox.querySelector('.rag-title').textContent=d.rag_title;
      ragBox.querySelector('.rag-text').textContent=claim.rag_explanation.text;
      const refs=(claim.rag_explanation.evidence_refs||[]).filter(Boolean);
      ragBox.querySelector('.rag-refs').textContent=refs.length?`${d.rag_refs}: ${refs.join(' · ')}`:'';
    }

    const processBox=node.querySelector('.process-box');
    const processBody=node.querySelector('.process-body');
    const contribution=node.querySelector('.ai-contribution-text');
    const modelNote=node.querySelector('.ai-model-note');
    if(claim.ai_explanation){
      contribution.textContent=aiContributionText(claim.ai_explanation);
      modelNote.textContent=aiModelLabel(claim.ai_explanation);
      if(claim.ai_explanation.value_added_over_lexical_baseline) processBox.classList.add('ai-value-added');
      if(claim.ai_explanation.gate?.includes('blocked')) processBox.classList.add('ai-gate-blocked');
    } else {
      contribution.textContent=uiLang==='ar'?'تم التحقق من هذه الحالة دون حاجة إلى استرجاع دلالي إضافي.':'This case was verified without requiring additional semantic retrieval.';
      modelNote.textContent='';
    }

    const list=node.querySelector('.evidence-list');
    let visibleMatches=claim.matches||[];
    if(claim.status==='source_match' || claim.status==='possible_lead' || claim.status==='citation_mismatch') visibleMatches=visibleMatches.slice(0,1);
    else if(claim.status==='source_linked' && claim.curated_reference?.source_ids?.length) visibleMatches=visibleMatches.slice(0,claim.curated_reference.source_ids.length);
    else visibleMatches=visibleMatches.slice(0,2);
    if(!visibleMatches.length){const empty=document.createElement('div');empty.className='empty-source';empty.textContent=d.no_evidence;list.appendChild(empty);} else visibleMatches.forEach(m=>list.appendChild(buildSourceBlock(m)));

    const traceSteps=node.querySelector('.trace-steps');
    (claim.trace||[]).forEach(step=>{const el=document.createElement('div');el.className='trace-step';el.innerHTML=`<b>${escapeHTML(step.step.toUpperCase())}</b><span>${escapeHTML(traceDetail(step))}</span>`;traceSteps.appendChild(el);});
    const toggle=node.querySelector('.process-toggle');
    toggle.addEventListener('click',()=>{const willOpen=processBody.hidden;processBody.hidden=!willOpen;toggle.setAttribute('aria-expanded',String(willOpen));toggle.querySelector(':scope > b').textContent=willOpen?'−':'+';});

    node.querySelectorAll('[data-help]').forEach(btn=>btn.addEventListener('click',async()=>{try{await fetch('/api/feedback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({input_text:claim.claim,result_status:claim.status,helpful:btn.dataset.help==='true'})});btn.textContent='✓';btn.disabled=true;}catch{}}));
    claimsList.appendChild(node);
  });
  applyStaticStrings();
}

$('#analyzeBtn').addEventListener('click',analyze);
$('#backBtn').addEventListener('click',()=>{hideError();show(home);input.focus();});
$('#errorDismiss').addEventListener('click',hideError);
input.addEventListener('input',()=>$('#charCount').textContent=`${input.value.length} / 8000`);
input.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter')analyze();});
document.querySelectorAll('[data-demo]').forEach(btn=>btn.addEventListener('click',async()=>{try{hideError();const r=await fetch(`/api/demo/${btn.dataset.demo}?lang=${uiLang}`);if(!r.ok) throw new Error('demo');const demo=await r.json();input.value=demo.text;input.dispatchEvent(new Event('input'));await analyze();}catch{show(home);showError(STRINGS[uiLang].error_generic);}}));
