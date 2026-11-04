"""Offline evidence accounting and diagnostic preparation. No client/network imports.

Preserve every preparation in a new timestamped directory. Model-facing materials
contain frozen source packets, never the approved full-sentence reference.
"""
import copy
import datetime as dt
import hashlib
import html
import json
from pathlib import Path

B = Path(__file__).resolve().parent
R = B.parents[2]
A = R / 'experiments/analyses'
SOURCE = '20261030T085346443103Z'
URL = 'http://127.0.0.1:8767/reports/effect-ledger-20261031/report.html'

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def save(p, value):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf8')

def load(p, hashes):
    hashes[p.relative_to(R).as_posix()] = digest(p)
    return json.loads(p.read_text(encoding='utf8'))

def proposal_packet(packet, morph, decision, no_change_review=None):
    """Validate a proposed *selection*, not linguistic correctness. Never bypass checks.

    No after text or free-form answer-bearing instructions accepted. The production
    worker is not called; binding/semantic verification remains a separate prerequisite.
    """
    allowed = {'word_id', 'card_id', 'form_index', 'morph_index'}
    cards = {c['id']: c for c in packet['cards']}
    words = {w['uid']: w for w in morph['words']}
    if not isinstance(decision, list):
        raise ValueError('reviewed_selection_required')
    if not decision:
        if not isinstance(no_change_review,dict) or not all(no_change_review.get(k) for k in ('reviewed_by','basis')):
            raise ValueError('empty_pending_is_not_reviewed_no_change')
        return {'packet':copy.deepcopy(packet),'selection_override':[],
                'status':'reviewed_no_change_recorded','review':copy.deepcopy(no_change_review),
                'worker_policy':'skip_and_record_unchanged_zero_calls','runnable':False,
                'full_reference_supplied':False}
    seen = set()
    for t in decision:
        if set(t) != allowed:
            raise ValueError('only_binding_fields_allowed')
        if t['card_id'] not in cards or t['word_id'] not in words:
            raise ValueError('card_must_already_be_delivered_and_word_exist')
        c, w = cards[t['card_id']], words[t['word_id']]
        if type(t['form_index']) is not int or not 0 <= t['form_index'] < len(c['forms']):
            raise ValueError('invalid_form_index')
        if type(t['morph_index']) is not int or not 0 <= t['morph_index'] < len(w['morphs']):
            raise ValueError('invalid_morph_index')
        if w['morphs'][t['morph_index']][1] not in ('EF', 'EC', 'ETM', 'ETN', 'JKS', 'JKO', 'JKB', 'JX', 'JKG', 'JC'):
            raise ValueError('unsupported_target_component')
        position = (t['word_id'], t['morph_index'])
        if position in seen:
            raise ValueError('overlapping_targets')
        seen.add(position)
    return {'packet': copy.deepcopy(packet), 'selection_override': copy.deepcopy(decision),
            'status': 'binding_validated_only', 'semantic_review': 'pending',
            'runnable': False, 'full_reference_supplied': False}

def build():
    hashes = {}
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out = B / 'private/preparations' / stamp
    out.mkdir(parents=True, exist_ok=False)
    def src(name, file='summary.json'):
        return load(A / name / 'private' / file, hashes)
    delivery = src('card_delivery_20261030')
    content = src('card_content_experiment_20261030')
    scope = src('scoped_repair_20261030')
    alignment = src('contract_alignment_20261030')
    register = src('register_connective_20261030')
    functions = src('controlled_delivery_20261031', 'replay_summary.json')
    for name in ('card_delivery_20261030','card_content_experiment_20261030','scoped_repair_20261030',
                 'contract_alignment_20261030','register_connective_20261030','controlled_delivery_20261031',
                 'bottleneck_audit_20261030'):
        p = A/name/'README.md'; hashes[p.relative_to(R).as_posix()] = digest(p)
    d=delivery['conditions'];c=content['conditions'];s=scope['conditions'];g=register['counts']
    ledger = [
      {'id':'delivery','title':'관련 카드를 더 전달', 'source':'card_delivery_20261030',
       'question':'관련 카드를 전달하면 원하는 변환으로 이어지는가?',
       'design':'26문장, 기존/변경 전달을 같은 시점에 비교. 카드 교체 전체 효과.',
       'measurement':{k:d[k] for k in ('control_single','promoted_single','control_multi','promoted_multi')},
       'observed':f"추가 카드 선택은 두 방식 각각 {d['promoted_single']['promoted_selected']}·{d['promoted_multi']['promoted_selected']}건, 최종 반영은 각각 {d['promoted_single']['promoted_applied']}·{d['promoted_multi']['promoted_applied']}건.",
       'verdict':'전달만으로 해결하지 못함',
       'limit':'이 26문장·당시 카드/코드의 결과다. 모든 검색 개선이 무효라는 뜻은 아니다.',
       'next':'같은 카드 추가 실험을 그대로 반복하지 않는다. 선택·조합 실패를 분리한다.'},
      {'id':'content','title':'카드 내용과 변환 설명 보완','source':'card_content_experiment_20261030',
       'question':'내용을 명확히 하면 카드 사용과 출력이 달라지는가?',
       'design':'50문장, v2/v3 × Single/Multi 동시 비교. 설명 추가와 관리 정보 정리를 함께 변경.',
       'measurement':{k:c[k] for k in ('v2_single','v3_single','v2_multi','v3_multi')},
       'observed':f"문장 변경 수: Single {c['v2_single']['changed']}→{c['v3_single']['changed']}, Multi {c['v2_multi']['changed']}→{c['v3_multi']['changed']}. 잘못된 활용도 함께 출력됨.",
       'verdict':'카드 사용 변화 확인 / 자연스러움 개선 미확인',
       'limit':'변경 수는 정답 수가 아니다. 두 종류의 내용 변경 효과는 분리되지 않았다.',
       'next':'내용 수정이 전부 무효였다고 되돌리지 않는다. 선택 후 활용을 따로 확인한다.'},
      {'id':'scope','title':'요 → 예 교체 범위 연결','source':'scoped_repair_20261030',
       'question':'요 앞의 활용을 잃는 특정 오류를 막았는가?',
       'design':'저장 응답 재검증 + 별도 새 실행. 새 실행 전후는 다른 시점.',
       'measurement':{'scope_applied_checks':scope['scope_applied_checks'],'scope_violations':scope['scope_violations'], 'conditions':s},
       'observed':f"실제 적용 {scope['scope_applied_checks']}곳에서 지정 범위 위반 {scope['scope_violations']}건. 새 실행 무출력 Single {s['old_single']['no_output']}→{s['new_single']['no_output']}, Multi {s['old_multi']['no_output']}→{s['new_multi']['no_output']}.",
       'verdict':'특정 조합 처리 확인 / 전체 실패는 남음',
       'limit':'20곳은 선택되어 적용된 자리만의 수치다. 전체 문장 자연스러움이나 실패 증가의 원인 증명이 아니다.',
       'next':'확인된 부분 교체 동작은 보존한다. 나머지 어미까지 해결했다고 확대하지 않는다.'},
      {'id':'alignment','title':'분석값·편집 처리 연결','source':'contract_alignment_20261030',
       'question':'분석 보정의 효과를 분리해 확인했는가?',
       'design':'저장된 선택·응답을 고정한 재검증. 새 조회·선택 없음.',
       'measurement':{'analysis_changed_inputs':len(alignment['analysis_changed_input_ids']), 'modes':alignment['modes']},
       'observed':f"분석값 {len(alignment['analysis_changed_input_ids'])}문장 변경. 분석 보정 추가 전후의 최종 문자열 변화는 0건(기존 보고서의 직접 대조).",
       'verdict':'새 검색·선택에 미치는 효과는 미검증',
       'limit':'선택을 고정했으므로 분석이 중요하지 않다는 근거로 사용할 수 없다.',
       'next':'분석 보정이 검색·선택을 바꾸는 효과는 별도 비교 대상으로 남긴다.'},
      {'id':'register','title':'말높임·연결어미 대조와 새 분석','source':'register_connective_20261030',
       'question':'여러 보완을 합친 실행에서 무엇이 달라졌는가?',
       'design':'새 분석부터 전수 실행. 이전과 분석·선별·프롬프트·검사 등이 함께 달라진 역사적 비교.',
       'measurement':g,
       'observed':f"무출력 Single {g['single_old']['no_output']}→{g['single_new']['no_output']}, Multi {g['multi_old']['no_output']}→{g['multi_new']['no_output']}. 변경 수는 Single 30, Multi 31로 동일.",
       'verdict':'무출력 감소 관찰 / 개별 수정의 원인은 분리 불가',
       'limit':'잘못된 변경을 막은 효과와 올바른 생성 능력을 구별해야 한다.',
       'next':'여러 변경을 더 묶기보다 같은 분석·카드로 단계별 도움을 비교한다.'},
      {'id':'functions','title':'추천·적용 판단 기준 통일','source':'controlled_delivery_20261031',
       'question':'같은 조건을 다르게 읽던 충돌을 고쳤는가?',
       'design':'최신 저장 응답100개 재검증. 실제 새 Qwen 비교는 미실행.',
       'measurement':functions,
       'observed':f"최종 문장 변화 Single {len(functions['arms']['single']['output_changes'])}건, Multi {len(functions['arms']['multi']['output_changes'])}건. 새 생성 0회.",
       'verdict':'검사 충돌 수정 확인 / 새 생성 효과 미검증',
       'limit':'말이소 반영이 승인 표현 마이소의 자연스러움을 확보했다는 뜻은 아니다.',
       'next':'준비된 설명 도움·조합 도움 비교에 공통으로 적용한다.'},
    ]
    # Reuse previous assessments explicitly as historical; do not relabel them as new diagnoses.
    historical = src('bottleneck_audit_20261030','notes.json')
    latest = src('register_connective_20261030','cases.json')
    latest_by = {x['id']:x for x in latest}
    inputs_file = R/'data/derived_private/standard_inputs_50_20261029_v2/inputs.jsonl'
    hashes[inputs_file.relative_to(R).as_posix()] = digest(inputs_file)
    inputs = [json.loads(x) for x in inputs_file.read_text(encoding='utf8').splitlines() if x.strip()]
    assert len(inputs)==50 and len({x['id'] for x in inputs})==50
    source_cards = R/'knowledge/authored/kg_cards_20261030_v3/cards.json'
    card_data = load(source_cards,hashes); card_by={c['id']:c for c in card_data['cards']}
    cases=[];counts={'inputs':50,'actual_record_links':0,'multi_decisions_available':0,'multi_decisions_missing':0,
                    'selection_targets_reviewed':0,'ready_live_probes':0,'new_model_calls':0}
    for rec in inputs:
        ident=rec['id']; shared=R/'experiments/batches'/SOURCE/'private/shared'/ident
        packet=load(shared/'reference_packet.json',hashes);morph=load(shared/'morphology.json',hashes)
        retrieval=load(shared/'retrieval_raw.json',hashes)
        assert packet['input']==rec['text']==morph['text']==latest_by[ident]['input']
        assert all(card_by[c['id']]==c for c in packet['cards'])
        # Model-facing source-only boundary bundle. No reference sentence / historic notes.
        save(out/'model_inputs'/ident/'source_packet.json',packet)
        save(out/'model_inputs'/ident/'morphology.json',morph)
        current={}
        for arm in ('single','multi'):
            record=R/'experiments/runs'/f'{SOURCE}_cards_{arm}_regression/private/records'/ident
            result=load(record/'result.json',hashes);counts['actual_record_links']+=1
            current[arm]={'output':result.get('output_text'),'status':result.get('status'),
                          'error':result.get('error'),'record':record.relative_to(R).as_posix(),
                          'selected_rules':result.get('selected_rules',[]),'applied_rules':result.get('applied_rules',[])}
            if arm=='multi':
                f=record/'agent_call/parsed.json'
                if f.exists():
                    dec=load(f,hashes);counts['multi_decisions_available']+=1
                    # Free text in old decisions may contain translations. Keep it out
                    # of the source-only runtime materials; future compiler must rebuild it.
                    save(out/'archive_only'/ident/'saved_multi_decision.json',dec)
                else:
                    counts['multi_decisions_missing']+=1
        save(out/'selection_review'/f'{ident}.json',{'input_id':ident,'status':'pending','targets':[],
             'reason':'원래 모델 선택을 올바른 선택으로 간주하지 않음. 카드·위치·형태의 별도 검토가 필요.',
             'allowed_target_fields':['word_id','card_id','form_index','morph_index'],
             'reference_sentence_must_not_enter_model_packet':True})
        cases.append({'id':ident,'input':rec['text'],'approved_reference':latest_by[ident]['reference'],
                      'historical_finding':historical[ident], 'historical_source_batch':'20261030T062819598143Z_scoped',
                      'current_source_batch':SOURCE,'current':current,'retrieved_card_count':len(retrieval['retrieved_ids']),
                      'delivered_card_count':len(packet['cards']), 'selection_review':'pending',
                      'diagnostic_bundle':(out/'model_inputs'/ident).relative_to(R).as_posix()})
    # Three worked questions, not a replacement for the all-50 preparation.
    examples=[]
    for ident,cid,word,mi in [('DEV002','GS_END_DECL_HRA_09','W5',2),
                             ('DEV026','GS_END_DECL_YE_01','W5',2),
                             ('NEW004','GS_END_Q_YE_01','W3',3)]:
        shared=R/'experiments/batches'/SOURCE/'private/shared'/ident
        packet=load(shared/'reference_packet.json',hashes);ret=load(shared/'retrieval_raw.json',hashes)
        delivered=cid in {c['id'] for c in packet['cards']}
        examples.append({'id':ident,'card_id':cid,'card_title':card_by[cid]['title'],
                         'in_kg':True,'retrieved':cid in ret['retrieved_ids'],'delivered':delivered,
                         'candidate_binding':{'word_id':word,'card_id':cid,'form_index':0,'morph_index':mi},
                         'status':'candidate_not_semantically_certified',
                         'next_test':('selection_or_instruction_comparison_after_review' if delivered else 'knowledge_applicability_review_before_delivery_intervention'),
                         'limitation':'카드 존재만 확인. 실제 적용 가능성이나 현대 용법을 인증하지 않음.'})
    # A real binding fixture exercises the guard; do not call it an approved intervention.
    p=json.loads((out/'model_inputs/DEV026/source_packet.json').read_text(encoding='utf8'))
    m=json.loads((out/'model_inputs/DEV026/morphology.json').read_text(encoding='utf8'))
    fixture=proposal_packet(p,m,[examples[1]['candidate_binding']])
    save(out/'fixtures/binding_only_DEV026.json',fixture)
    protocol={
      'scope':'offline preparation only; no new KG/production generation changes; no model calls',
      'source_batch':SOURCE, 'population':'all 50 exposed regression inputs; no representative-only exclusion',
      'existing_experiment':{'path':'experiments/analyses/controlled_delivery_20261031/run.py',
          'state':'prepared_not_run','question':'explanation vs composition aid','conditions':'control/explanation/composition x single/multi',
          'limitation':'tests aids, not proof of a unique root cause; keep distinct from forced-selection diagnostic'},
      'next_probe':{'name':'reviewed_selection_worker_pair','state':'protocol_and_source_bundles_prepared_not_runnable',
          'question':'With the same available cards, does a reviewed selection change the worker result?',
          'control':'saved planner selection revalidated under one frozen current contract',
          'treatment':'reviewed card/form/word/morph selection; no full translated words or sentences',
          'fixed':['original input','saved analysis','full ordered delivered cards','worker prompt','model settings','application checks'],
          'allowed_difference':['selection bindings and dependent plan IDs/instructions'],
          'instruction_policy':'rebuild instruction/reason/after/action/edit groups/dependencies by the SAME source/card-based compiler in both arms; never pass saved free-text decisions directly',
          'cards_policy':'full identical cards to both arms; do not vary used-card subset with the plan',
          'architecture':'Multi worker only. Splitting Single adds a step and is not a clean same-architecture intervention.',
          'missing_card_policy':'not eligible for selection-only pair; record separate missing-delivery/knowledge review, do not silently insert card',
          'missing_response_policy':'keep listed as unavailable; not reconstructed from gold',
          'no_change_policy':'distinguish pending empty from reviewed no-change; reviewed no-change skips worker and records unchanged with zero worker calls; report both paired-case outcomes and actual-call denominators',
          'historical_comparison':'new full-card worker differs from historical selected-card worker; compare NEW control vs NEW treatment only, not new vs historical for causal effect',
          'reference_exposure':'reviewed selections may be informed by approved references; diagnostic upper-assistance condition, not automatic selector performance or unseen generalization',
          'block_policy':'if reviewed selection fails the unchanged checks, record pre-worker block and inspect it; do not disable validator',
          'instruction_only_pair':'when bindings already match, compare instruction wording separately; do not label it selection improvement',
          'repeats':'predeclare at least 3 paired repetitions for variability checks; alternate order; total calls depends on eligible plans, report denominator',
          'success':'target expression/meaning/tense/honorific preserved and user-acceptable; output change alone not success',
          'inference':'success suggests selection contributes; failure alone does not prove KG wrong, inspect worker raw result vs application rejection',
          'prerequisites':['review targets across all50','build and validate paired current plans','freeze runner','restore Qwen service']},
      'held_out_test':'separate new sentences after a reusable fix; not generated or evaluated in this task',
      'reference_policy':'human-approved modern target variety; approved sentences in review material only, not model_inputs',
      'reviewer':'main Codex synthesis of existing artifacts; not a new independent linguistic review'}
    # Snapshot all material used for conclusions; historical sources can be rechecked.
    for package in ('kg_runtime','kg_pipeline'):
        for f in (R/'src'/package).glob('*'):
            if f.suffix in ('.py','.json'):hashes[f.relative_to(R).as_posix()]=digest(f)
    for name in ('prepare.py','verify.py','README.md'):
        f=B/name;hashes[f.relative_to(R).as_posix()]=digest(f)
    save(out/'ledger.json',ledger);save(out/'cases.json',cases);save(out/'examples.json',examples)
    save(out/'protocol.json',protocol);save(out/'summary.json',counts);save(out/'source_hashes.json',hashes)
    for rel,h in hashes.items():assert digest(R/rel)==h,rel
    save(B/'private/latest.json',{'preparation':out.relative_to(R).as_posix(),'report_url':URL})
    render(out,ledger,cases,examples,counts)
    save(out/'verification.json',{'all_50_linked':len(cases)==50,'source_hashes_checked':len(hashes),
        'all_100_actual_records_linked':counts['actual_record_links']==100,'cards_exact_existing_content':True,
        'new_model_calls':0,'new_kg_queries':0,'new_generation_results':0,
        'reviewed_counterfactual_plans':0,'live_probe_ready':False,
        'fixture_semantics_certified':False})
    print(json.dumps({'preparation':str(out),'summary':counts},ensure_ascii=False))
    return out

def render(out,ledger,cases,examples,counts):
    esc=lambda v:html.escape(str(v))
    status_name={'unchanged':'원문 유지','needs_review':'보류된 수정 있음',
                 'generated_requires_human_review':'변경 출력 · 품질 미평가','failed':'출력 실패','error':'출력 실패'}
    rows=''.join(f'<tr><td><b>{esc(x["title"])}</b><small>{esc(x["design"])}</small></td><td>{esc(x["observed"])}</td><td><b>{esc(x["verdict"])}</b><small>{esc(x["limit"])}</small></td><td>{esc(x["next"])}</td></tr>' for x in ledger)
    cards=''
    for c in cases:
        arms=''.join(f'<tr><td>{esc(a)}</td><td>{esc(c["current"][a]["output"] or "출력 없음")}</td><td>{esc(status_name.get(c["current"][a]["status"],c["current"][a]["status"]))}</td></tr>' for a in ('single','multi'))
        cards+=f'''<details class="case"><summary>{esc(c['id'])} · {esc(c['input'])}</summary>
        <p><b>사용자 승인 표현</b> {esc(c['approved_reference'])}</p>
        <p><b>이전 진단</b> {esc(c['historical_finding']['finding'])}</p>
        <p class="note">이전 진단은 10월30일 15:28 시작 실행의 기록입니다. 아래 최신 출력에 같은 진단이 여전히 맞는다고 자동 판정하지 않았습니다. 시각은 한국시간입니다.</p>
        <table><tr><th>방식</th><th>최신 실제 출력 (10월30일 17:53 시작 실행)</th><th>처리 상태</th></tr>{arms}</table>
        <p>실제 조회 {c['retrieved_card_count']}개 / 전달 {c['delivered_card_count']}개. 카드와 위치를 사람이 바로잡은 비교용 계획은 아직 검토 전입니다.</p></details>'''
    examples_html=''.join(f'<tr><td>{esc(x["id"])}</td><td>{esc(x["card_title"])}</td><td>{"있음" if x["retrieved"] else "없음"}</td><td>{"전달됨" if x["delivered"] else "전달 안 됨"}</td><td>{"선택·지시·조합을 구분해 확인" if x["delivered"] else "적용 가능한 카드인지부터 확인; 선택 단계만 고치는 실험에 바로 넣지 않음"}</td></tr>' for x in examples)
    body=f'''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>무엇을 고쳤고, 무엇을 아직 모르는가</title><link rel="stylesheet" href="report.css"><body><main>
    <header><p>기존 작업의 효과 정리 · 새 Qwen 호출 없음</p><h1>다시 분석하는 대신,<br>이미 한 수정의 효과를 구분했습니다.</h1><p>전체가 실패한 것도, 해결된 것도 아닙니다. 카드 사용은 달라졌고 일부 조합 오류는 고쳤지만, 자연스러운 전체 문장 생성은 아직 확인하지 못했습니다.</p><nav><a href="#ledger">수정별 결과</a><a href="#next">다음 실험</a><a href="#cases">50문장 기록</a><a href="/work">진행 화면</a></nav></header>
    <section><h2>이번에 완료한 일</h2><div class="flow"><span>기존 6개 수정 대조</span><b>→</b><span>50문장·100개 출력 연결</span><b>→</b><span>단계 하나만 바꿀 비교 준비</span></div><p>KG·카드·번역 코드는 추가로 수정하지 않았습니다. 기존 원본은 보존했습니다. 새 모델 실험이나 새 자연스러움 평가를 한 것은 아닙니다.</p></section>
    <section id="ledger"><h2>무엇은 효과가 있었고, 무엇은 아닌가</h2><table><tr><th>했던 수정</th><th>실제 관찰</th><th>지금 내릴 수 있는 결론</th><th>다음 처리</th></tr>{rows}</table><p class="note">수치는 각 실험 안에서만 비교합니다. 서로 다른 시점·분모의 수치를 하나의 정확도 그래프로 합치지 않습니다.</p></section>
    <section id="next"><h2>다음에는 무엇을 다르게 하나</h2><p><b>핵심 질문: 적절한 카드와 적용 위치를 정해 주면, 같은 Qwen 워커가 제대로 활용할 수 있는가?</b></p><div class="flow"><span>같은 문장·분석·카드</span><b>→</b><span>기존 선택 / 검토한 선택</span><b>→</b><span>같은 생성·검사</span></div>
    <ul><li>정답 문장이나 완성된 교체 단어는 전달하지 않습니다. 카드·형태 번호·원문 위치만 바꿉니다.</li><li>두 조건에 같은 카드 목록과 같은 지시 작성 방식을 씁니다. 선택과 설명을 함께 바꾸지 않습니다.</li><li>필요한 카드가 전달되지 않은 문장은 이 비교에 바로 넣을 수 없습니다. 목록에 남기고 별도 문제로 분류합니다.</li><li>검사에서 막히면 막힌 이유도 결과입니다. 통과시키려고 검사를 끄지 않습니다.</li><li>이 비교는 Multi의 생성 담당에서 먼저 설계합니다. Single을 강제로 나누면 구조까지 바뀌기 때문입니다.</li></ul>
        <p><b>준비 수준:</b> 50개 입력 묶음과 보관용 원본 Multi 응답 {counts['multi_decisions_available']}개를 연결했습니다. 원본 응답의 자유 문장은 그대로 모델에 보내지 않습니다. 검토가 끝난 수정 선택표는 0개이고, 새 비교 실행기는 아직 구현 전입니다.</p>
        <p>검토한 결과 ‘바꿀 부분 없음’도 유효한 결과입니다. 이때는 워커 호출을 생략하고 원문 유지·호출0회로 기록합니다. 아직 검토하지 않은 빈 선택표와 구분합니다. 과거 출력이 아닌, 새로 실행한 두 조건끼리 비교해야 합니다.</p>
    <p>이미 준비한 설명 도움/조합 도움 비교는 보존합니다. 이것은 ‘도움을 주면 달라지는가’를 묻는 실험이고, 위 비교는 ‘선택이 병목인가’를 묻는 진단입니다. 두 결과를 섞지 않습니다.</p>
    <table><tr><th>실제 예</th><th>관련 카드</th><th>조회</th><th>전달</th><th>먼저 할 일</th></tr>{examples_html}</table>
    <p class="note">위 세 사례는 설계 설명용입니다. 검사 대상은 계속 전체 50문장입니다. 카드가 존재한다고 그 문장에 맞는 규칙이라는 뜻은 아닙니다.</p>
    <h3>결과가 나오면 이렇게 판단합니다</h3><table><tr><th>관찰</th><th>다음 행동</th></tr><tr><td>검토한 선택에서만 목표 부분이 올바르게 바뀜</td><td>선택 단계의 기여 근거. 재사용 가능한 선택 방식 보완을 검토.</td></tr><tr><td>선택을 바로잡아도 워커가 활용을 잘못 만듦</td><td>카드의 결합 설명과 생성 담당을 구분해 확인. KG 전체 문제로 단정하지 않음.</td></tr><tr><td>워커 표현은 괜찮지만 검사에서 사라짐</td><td>적용 검사의 해당 조건을 대조. 전체 검사를 해제하지 않음.</td></tr><tr><td>두 선택이 이미 같음</td><td>선택 수정 효과를 주장할 수 없음. 지시문·활용 단계 비교로 이동.</td></tr></table></section>
    <section id="cases"><h2>50문장: 기존 진단과 최신 기록</h2><p>새로운 50개 진단을 작성한 것이 아니라, 이미 작성한 판단과 최신 실행 원본을 연결했습니다.</p><label>검색 <input id="search" placeholder="번호 또는 문장"></label><p id="count">50 / 50문장</p>{cards}</section>
    <footer><p>기존 Codex Reviewer가 비교 설계를 독립 검토했습니다. 기존 자유 지시문 재사용 금지, 검토된 원문 유지와 미검토 빈칸 구별, 새 조건끼리의 비교 원칙을 반영했습니다. 새 번역의 언어학적 품질을 평가한 것은 아닙니다.</p><p>다음 결정: 기존 선택과 검토한 선택을 비교할 구체 계획을 전체50 기준으로 확정할 것인지. Qwen 서버 복구는 실제 호출의 별도 전제입니다.</p></footer></main><script src="report.js"></script></body></html>'''
    public=B/'private';public.mkdir(exist_ok=True)
    css='''body{font-family:system-ui,"Malgun Gothic",sans-serif;background:#f4f7fb;color:#17283b;margin:0;line-height:1.75}main{max-width:1180px;margin:auto;padding:28px}header,section,footer{background:white;padding:28px;border-radius:14px;margin-bottom:22px}h1{font-size:32px;line-height:1.4}h2{font-size:23px}nav{display:flex;gap:20px;flex-wrap:wrap}a{color:#225c9e}table{border-collapse:collapse;width:100%;font-size:15px}td,th{padding:13px;text-align:left;vertical-align:top;border-bottom:1px solid #dfe6ee}th{background:#eaf1f9}small{display:block;color:#5a6775;margin-top:8px}.note{color:#5a6775;font-size:14px}details{border:1px solid #dfe6ee;border-radius:8px;padding:14px;margin:10px 0}summary{cursor:pointer;font-weight:600}.flow{display:flex;align-items:center;gap:12px;flex-wrap:wrap}.flow span{background:#edf5f6;border:1px solid #a8cccc;padding:12px;border-radius:8px}input{padding:10px;border:1px solid #a9b8ca;border-radius:6px;min-width:240px}@media(max-width:700px){main{padding:12px}header,section{padding:16px}table{display:block;overflow-x:auto}h1{font-size:26px}}'''
    js="""const search=document.getElementById('search'),cases=[...document.querySelectorAll('.case')];search.addEventListener('input',()=>{let n=0;const q=search.value.toLowerCase();for(const c of cases){c.hidden=!c.textContent.toLowerCase().includes(q);if(!c.hidden)n++;}document.getElementById('count').textContent=n+' / '+cases.length+'문장';});"""
    for name,text in [('report.html',body),('report.css',css),('report.js',js)]:
        (public/name).write_text(text,encoding='utf8');(out/name).write_text(text,encoding='utf8')

if __name__=='__main__':build()
