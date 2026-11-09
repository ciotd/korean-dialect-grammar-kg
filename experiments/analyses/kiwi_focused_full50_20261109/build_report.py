"""Read frozen run artifacts and render a human-readable regression report.

No generation, reference-based scoring, mutation of run artifacts or inferred
quality metrics. Model warnings and use declarations are labelled as such.
"""
import argparse, collections, csv, hashlib, html, json, shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
E = lambda x: html.escape(str(x if x is not None else '미확정'))
def read(p, default=None):
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else default
def save(p, x):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def table(headers, rows):
    return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+E(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(c)+'</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def link(p, label): return '<a href="'+E(p.resolve().as_uri())+'">'+E(label)+'</a>'

FIELDS = {'speech_act':'문장 기능','question_type':'질문 종류','addressee_level':'듣는 사람에게 쓰는 말투',
 'subject_honorific':'행동 주체 높임','past_form':'과거 형태 유무','tense_semantics':'시간 의미','question_kind':'질문 종류',
 'tense':'시간 의미','auxiliary_kind':'보조동작의 뜻','clause_role':'절의 역할','predicate_class':'서술어 종류',
 'source_form':'대상 형태','source_final':'끝맺는 형태','prefinal_sequence':'어미 앞의 시제·높임 형태',
 'lemma':'어간·기본형','polarity':'긍정·부정','semantic_function':'뜻의 종류','unit_kind':'분석 단위',
 'ending_tag':'어미 종류','morph_tag':'형태 종류','nominal_end':'명사의 끝소리','nominal_kind':'명사 종류',
 'main_predicate':'본동작','auxiliary_predicate':'보조동작','nominal_host':'조사가 붙는 명사',
 'wh_in_same_clause':'같은 절의 의문 표현','governing_predicate':'연결된 서술어'}
VALUES = {'statement':'평서','information_question':'질문','request':'요청','prohibition':'금지','promise':'약속',
 'command':'명령','plain':'반말','polite':'존댓말','formal':'격식체','present':'있음','absent':'없음',
 'none':'해당 없음','unknown':'미확정','past':'과거','future':'미래','verb':'동사','adjective':'형용사',
 'copula':'계사','negative_copula':'부정 계사','main':'주절','adnominal':'명사를 꾸미는 절',
 'predicate':'서술 표현','nominal':'명사류','particle':'조사','connector':'절을 잇거나 꾸미는 어미',
 'construction':'여러 말이 합쳐진 구성','benefactive':'상대를 위해 하는 동작','progressive':'진행',
 'trial':'시도','negative':'부정','positive':'긍정','wh':'의문사 질문','polar':'예·아니오 질문',
 'true':'조건에 맞음','false':'조건에 맞지 않음','unresolved':'미확정',
 'analysis_disagreement':'분석에 이견이 있어 전달 보류','character_budget':'전달 길이 제한',
 'condition_mismatch':'조건 불일치','missing_relation':'필요한 관계 없음',
 'eoss':'-았/었-','si':'-시-','si_eoss':'-시- + -았/었-','EF':'종결어미','EC':'연결어미','ETM':'관형형 어미',
 'lexical_nominal':'일반 명사류','not_nominal':'명사류 아님','consonant':'자음 끝','vowel':'모음 끝',
 'exclamation':'감탄','suggestion':'제안·청유','confirmation':'확인 질문','active':'능동','passive':'피동',
 'attempt':'시도','state':'상태','obligation':'의무','desire':'바람','other':'기타','interrogative':'의문 표현',
 'non_interrogative':'의문 표현 아님','indefinite':'부정칭','reflexive':'재귀 표현'}
STAGES={'shared_scope':'절 범위 분석·검사(생성 전)','meaning_model_call':'의미·관계 분석 응답',
 'meaning_binding':'분석값과 KG 조건 연결','kg_retrieval':'KG 조건 조회','candidate_delivery':'조회 지식 전달',
 'writer_model_call':'방언 문장 작성 응답','writer_validation':'작성 응답 형식 검사',
 'reviewer_model_call':'별도 검사 응답','review_evidence_validation':'검사 의견의 인용 확인','completed':'전체 처리 완료'}
def val(v):
    if v is None: return '미확정'
    if isinstance(v, list): return ' / '.join(val(i) for i in v) or '없음'
    return VALUES.get(str(v), str(v))
def pair(k, v):
    # present is not always "present tense"; only interpret by field.
    x = '현재' if k in ('tense','tense_semantics') and v=='present' else val(v)
    return E(FIELDS.get(k, k))+': '+E(x)
def bars(items, unit='건'):
    maximum=max([v for _,v in items]+[1])
    return ''.join('<div class="barrow"><span>'+E(k)+'</span><div class="track"><i style="width:'+str(v/maximum*100)+'%"></i></div><b>'+E(f'{v:,} {unit}')+'</b></div>' for k,v in items)
def list_text(items): return '<ul>'+''.join('<li>'+E(x)+'</li>' for x in items)+'</ul>' if items else '<p class="muted">기록 없음</p>'

def build(run):
    out=HERE/'private';out.mkdir(exist_ok=True)
    inp=[json.loads(s) for s in (run/'private/inputs.jsonl').read_text(encoding='utf-8').splitlines() if s.strip()]
    results=read(run/'private/results.json',[]);by={x['source_input_id']:x for x in results}
    config=read(run/'config.json');metrics=read(run/'metrics.json',{});progress=read(run/'progress.json',{})
    refpath=ROOT/'experiments/analyses/claude_comparison_20261030/private/translations.json'
    refs={x['id']:x['translation'] for x in read(refpath,{'rows':[]})['rows']}
    notes=read(out/'analyst_notes.json',{})
    cases=[];stagecost=collections.defaultdict(lambda: {'calls':0,'tokens':0,'seconds':0.,'missing_usage':0})
    for p in (run/'private').rglob('meta.json'):
        m=read(p);s=m.get('stage','unknown');d=stagecost[s];d['calls']+=1
        d['tokens']+=(m.get('usage') or {}).get('total_tokens',0) or 0
        d['seconds']+=m.get('seconds',0) or 0;d['missing_usage']+=not bool(m.get('usage'))
    stagecost={k:stagecost[k] for k in ['kiwi_scope','multi_meaning','multi_writer','multi_reviewer'] if k in stagecost} | {k:v for k,v in stagecost.items() if k not in ['kiwi_scope','multi_meaning','multi_writer','multi_reviewer']}
    writer_equal=[];request_checks=[]
    for i,row in enumerate(inp,1):
        r=by.get(row['id'],{});rd=run/'private/records'/(row['id']+'_kiwi_focused')
        bound=read(rd/'bound_analysis.json',[]);sel=read(rd/'selected_knowledge.json',[])
        packet=read(rd/'retrieval_packet.json',{});trace=read(rd/'retrieval.json',[]);draft=read(rd/'writer/parsed.json',{})
        output=r.get('output_text');raw=draft.get('output_text')
        complete=r.get('pipeline_completed',False)
        if complete: writer_equal.append(output==raw)
        state='unattempted' if not r else ('failed' if not complete else ('same' if output==row['text'] else 'changed'))
        c={'number':i,'id':row['id'],'source':row['text'],'reference':refs.get(row['id']),
           'output':output,'writer_draft':raw,'complete':complete,'state':state,'seconds':r.get('total_seconds'),
           'selected_count':len(sel),'used_count':len(draft.get('used_action_ids',[])),
           'unresolved_count':len(packet.get('unresolved',[])),
           'stage':r.get('last_stage'),'error_type':r.get('error_type'),
           'model_review':r.get('review',{}),'model_changes':draft.get('model_knowledge_changes',[]),
           'bound':bound,'selected':sel,'retrieval':trace,'packet':packet,'draft':draft,'note':notes.get(row['id'])}
        cases.append(c)
    for p in (run/'private').rglob('request.json'):
        q=read(p);payload=json.loads(q['messages'][1]['content'])
        def forbidden(x):
            if isinstance(x,dict): return any(k in ('reference','reference_answer','gold','translation','approved_reference','check') or forbidden(v) for k,v in x.items())
            if isinstance(x,list): return any(forbidden(v) for v in x)
            return False
        request_checks.append(not forbidden(payload))
    counts=collections.Counter(c['state'] for c in cases)
    summary={'run_id':run.name,'input_count':len(inp),'completed':sum(c['complete'] for c in cases),
      'states':dict(counts),'with_delivered_knowledge':sum(c['complete'] and c['selected_count']>0 for c in cases),
      'any_stage_with_delivered_knowledge':sum(c['selected_count']>0 for c in cases),
      'without_delivered_knowledge':sum(c['complete'] and c['selected_count']==0 for c in cases),
      'with_unresolved':sum(c['unresolved_count']>0 for c in cases),'model_reported_use':sum(c['used_count']>0 for c in cases),
      'model_review_flagged':sum(bool(c['model_review'].get('issues')) for c in cases),
      'stage_cost':dict(stagecost),'metrics':metrics,'quality_accuracy':None,
      'validation':{'raw_writer_matches_all_completed':all(writer_equal),'checked_outputs':len(writer_equal),
      'no_reference_fields_in_request_payloads':all(request_checks),'checked_requests':len(request_checks)},
      'reference_path':refpath.relative_to(ROOT).as_posix(),'reference_sha256':sha(refpath),'input_sha256':sha(run/'private/inputs.jsonl')}
    if (run/'artifact_hashes.json').exists():
        hh=read(run/'artifact_hashes.json');bad=[p for p,h in hh.items() if not (run/p).exists() or sha(run/p)!=h]
        summary['validation'].update(artifact_files=len(hh),artifact_mismatches=bad)
    save(out/'summary.json',summary);save(out/'cases.json',cases)
    with (out/'outputs.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['번호','ID','표준어 원문','사용자 승인 참조','Qwen 최종 출력','작성 초안(실패 시 확인용)','전체 처리 완료','전달 지식 수','사용 신고 수'])
        for c in cases:w.writerow([c['number'],c['id'],c['source'],c['reference'],c['output'],c['writer_draft'],c['complete'],c['selected_count'],c['used_count']])
    state_label={'same':'원문과 동일','changed':'출력 변경','failed':'처리 실패','unattempted':'아직 미실행'}
    overview=[];details=[];heat=[]
    for c in cases:
        cid=c['id'];rd=run/'private/records'/(cid+'_kiwi_focused');index={u['id']:u['text'] for u in c['bound']}
        stage_paths=[run/'private/shared'/cid/'common_structure.json',rd/'bound_analysis.json',rd/'retrieval_packet.json',rd/'writer/parsed.json',rd/'review_validation.json']
        heat.append([f'<a href="#case-{cid}">{cid}</a>']+['<span style="color:#137867">● 기록 있음</span>' if p.exists() else '<span class="muted">— 기록 없음</span>' for p in stage_paths])
        tags=[c['state']]+(['no_knowledge'] if c['complete'] and c['selected_count']==0 else [])+(['unresolved'] if c['unresolved_count'] else [])
        attrs=' data-tags="'+E(' '.join(tags))+'" data-search="'+E(cid+' '+c['source']+' '+str(c['output']))+'"'
        shown_output=E(c['output']) if c['output'] is not None else ('<b>미완료 초안</b><br>'+E(c['writer_draft'])+'<small>후속 처리 실패. 완료 출력에 포함하지 않음.</small>' if c['writer_draft'] else '최종 출력 없음')
        overview.append('<tr'+attrs+'><td><a href="#case-'+cid+'">'+str(c['number'])+' · '+cid+'</a><small>'+state_label[c['state']]+'</small></td><td>'+E(c['source'])+'</td><td>'+E(c['reference'])+'</td><td>'+shown_output+'</td><td>'+str(c['selected_count'])+' / '+str(c['used_count'])+'</td></tr>')
        b='<details class="case" id="case-'+cid+'"'+attrs+'><summary>'+str(c['number'])+' · '+cid+' — '+E(c['source'])+' <span class="badge">'+state_label[c['state']]+'</span></summary>'
        b+='<div class="triptych"><div><h4>표준어 원문</h4><p>'+E(c['source'])+'</p></div><div><h4>사용자 승인 참조</h4><p>'+E(c['reference'])+'</p></div><div><h4>Qwen 최종 출력</h4><p>'+E(c['output'] if c['output'] is not None else '최종 출력 없음')+'</p></div></div>'
        if not c['complete'] and c['state']=='failed':b+='<p class="alert">실패 위치: '+E(STAGES.get(c['stage'],c['stage']))+' · '+E(c['error_type'])+'. '+('작성 초안은 남았지만 완료 결과로 세지 않습니다: '+E(c['writer_draft']) if c['writer_draft'] else '작성 초안도 없습니다.')+'</p>'
        if c['note']:b+='<div class="note"><b>실제 기록을 읽고 확인한 내용</b>'+list_text(c['note'] if isinstance(c['note'],list) else [c['note']])+'</div>'
        b+='<h3>① 문장을 어떻게 읽었나?</h3><p>형태는 Kiwi가 읽었습니다. 기능·관계·시간 의미는 Qwen의 판단이며, 아래 표 자체가 정답이라는 뜻은 아닙니다.</p>'
        scope=read(run/'private/shared'/cid/'scope/parsed.json',{})
        scope_req=read(run/'private/shared'/cid/'scope/request.json',{})
        if scope_req and scope.get('clauses'):
            words=json.loads(scope_req['messages'][1]['content'])['words'];word_by={w['id']:w for w in words}
            clrows=[]
            for cl in scope['clauses']:
                left=word_by.get(cl.get('start_word'));right=word_by.get(cl.get('end_word'))
                phrase=c['source'][left['span'][0]:right['span'][1]] if left and right else '원문 위치를 찾지 못함'
                clrows.append([E(cl['id']),E(phrase),E(cl.get('parent_id') or '상위 절 없음')])
            b+='<details'+(' open' if not c['complete'] else '')+'><summary>Qwen이 나눈 절 범위</summary>'+table(['절 ID','해당 원문','상위 절 ID'],clrows)+'</details>'
        units=[]
        for u in c['bound']:
            if u['kind'] not in ('predicate','construction','connector','particle','nominal'):continue
            fs=u.get('features',{});keys=['lemma','source_final','speech_act','question_type','question_kind','past_form','tense','tense_semantics','addressee_level','subject_honorific','auxiliary_kind','clause_role']
            desc='<br>'.join(pair(k,fs[k]) for k in keys if k in fs)
            relations='<br>'.join(E(FIELDS.get(k,k))+': '+E(' / '.join(index.get(v,v) for v in vs)) for k,vs in u.get('relations',{}).items()) or '연결 기록 없음'
            morph=' + '.join(str(m[0]) for m in u.get('morphs',[]))
            units.append([E(u['text'])+'<small>'+E(u['id'])+' · '+E(val(u['kind']))+'</small>',E(morph),desc,relations])
        b+=table(['위치·종류','형태 분리','저장된 분석값','다른 부분과의 관계'],units)
        b+='<h3>② KG에서 찾은 내용 중 무엇을 전달했나?</h3><p>아래는 생성 요청에 실제 들어간 지식입니다. “사용”은 작성자의 신고이며 올바른 적용을 뜻하지 않습니다.</p>'
        deliveries=[]
        for a in c['selected']:
            d=next((d for d in c['draft'].get('decisions',[]) if d['action_id']==a['action_id']),{})
            cond='<br>'.join(pair(x['feature'],x['value']) for x in a.get('conditions',[]))
            deliveries.append([E(a['source_text'])+'<small>'+E(a['rule_id'])+'</small>',E(a['instruction'])+'<small>보존: '+E(' · '.join(a.get('preserve',[])))+'</small>',cond,E({'applied':'사용 신고','not_used':'미사용 신고'}.get(d.get('decision'),d.get('decision','신고 없음')))+'<br>'+E(d.get('reason',''))])
        b+=table(['적용 위치·규칙 ID','실제로 전달한 설명','맞았다고 기록된 조건','작성자의 선택과 이유'],deliveries) if deliveries else '<p class="alert">생성 단계에 전달된 실행 지식이 없습니다. 이 경우에도 작성자는 자체 학습 지식으로 변환할 수 있도록 지시받습니다.</p>'
        pending=[]
        for t in c['retrieval']:
            for u in t.get('unresolved',[]):
                checks=[pair(x['feature'],x.get('value'))+' (허용: '+E(val(x.get('allowed')))+')' for br in u.get('branches',[]) for x in br.get('checks',[]) if x.get('state')=='unknown']
                pending.append([E(index.get(t['unit_id'],t['unit_id'])),E(u['rule_id']),'<br>'.join(checks) or E(u.get('state','미확정'))])
        if pending:b+='<details><summary>조건을 정하지 못해 전달하지 못한 후보 '+str(len(pending))+'개</summary>'+table(['위치','규칙 ID','확인되지 않은 값'],pending)+'</details>'
        omitted=[a for a in c['packet'].get('delivery_omissions',[]) if 'rule_id' in a]
        if omitted:b+='<details><summary>조회 이후 전달에서 제외된 실행 지식 '+str(len(omitted))+'개</summary>'+table(['위치','규칙 ID','제외 이유'],[[E(index.get(a.get('unit_id'),a.get('unit_id'))),E(a['rule_id']),E(val(a.get('reason')))] for a in omitted])+'</details>'
        b+='<p class="muted">별도로 찾은 미정제 자료 '+str(len(c['packet'].get('related_unprocessed_sources',[])))+'개는 적용 가능한 규칙으로 전달하지 않았습니다. 관계·조건 불일치 등 전체 조회 기록은 아래 원본 링크에서 확인할 수 있습니다.</p>'
        b+='<h3>③ 생성과 검사에서 무슨 일이 있었나?</h3><h4>작성자가 자체 지식으로 바꿨다고 신고한 내용</h4>'+list_text(c['model_changes'])
        issues=c['model_review'].get('issues',[])
        b+='<h4>Qwen 검사 담당의 의견 — 사실 확인 전</h4><p class="muted">검사 모델도 잘못 지적할 수 있습니다. 경고 수를 오류율로 계산하지 않으며, 이번 실행에서는 경고를 받아 자동 재작성하지 않았습니다.</p>'
        b+=table(['원문 구절','출력 구절','검사 모델의 주장','제안'],[[E(x.get('source_quote')),E(x.get('output_quote')),E(x.get('problem')),E(x.get('suggestion'))] for x in issues]) if issues else '<p>저장된 검사 의견이 없습니다. 오류가 없다는 보증은 아닙니다.</p>'
        b+='<details><summary>기술 근거가 필요할 때 열기</summary><p>'+ ' · '.join(link(rd/p,l) for p,l in [('bound_analysis.json','분석 원본'),('retrieval.json','전체 조건·경로'),('writer/request.json','실제 생성 요청'),('writer/parsed.json','작성자 응답'),('result.json','처리 결과')] if (rd/p).exists())+'</p></details></details>'
        details.append(b)
    stage_names={'kiwi_scope':'절 범위 읽기','multi_meaning':'의미·관계 판단','multi_writer':'방언 문장 작성','multi_reviewer':'별도 오류 검사'}
    done=sum(c['complete'] for c in cases);finished=(run/'metrics.json').exists()
    header='50문장 재실험 결과' if finished else '50문장 실행 중 — 중간 결과'
    runtime=metrics.get('wall_seconds',progress.get('elapsed_seconds',0))
    content=f'''<header><p class="eyebrow">2026.11.09 · 전체 문장 회귀 실험</p><h1>{header}</h1><p>Kiwi가 형태를 읽고, Qwen이 뜻과 관계를 판단한 뒤 KG 지식을 받아 문장 전체를 작성했습니다. 최근 보완한 <b>본동작·보조동작 연결 질문</b>을 적용했습니다.</p><p class="alert">끝까지 처리된 문장 {done}/50건입니다. 이 숫자는 번역 정확도가 아닙니다. 새로 논의한 분석 워커 추가·생성 계획 워커는 이번 실행에 넣지 않았습니다.</p><nav><a href="#results">50문장 나란히 보기</a><a href="#flow">실제 처리 순서</a><a href="#cost">호출·토큰·시간</a><a href="#findings">확인한 문제와 다음 작업</a></nav></header>'''
    if notes:
        content+='<section><h2>먼저 읽을 핵심</h2><p><b>일부 요청·계사 표현은 방언으로 바뀌었지만, 높임을 없애거나 다른 문법 자리를 잘못 바꾸는 문제는 남았습니다.</b> 이번 기록에서는 원인이 하나가 아닙니다. 반말을 격식체로 읽어 규칙을 놓친 경우, 규칙을 받고도 사용하지 않은 경우, 보존 지시를 받고도 자체 판단으로 반말로 바꾼 경우를 구분할 수 있습니다.</p><p>따라서 이번 실행을 품질 개선 완료로 보지 않습니다. 먼저 50문장 표에서 관심 문장을 고르고, ID를 눌러 어느 단계부터 어긋났는지 확인해 주세요.</p></section>'
    content+='<section class="cards">'+''.join('<div><b>'+E(v)+'</b><span>'+E(k)+'</span></div>' for k,v in [('처리 완료',str(done)+'/50'),('출력 변경',counts['changed']),('원문 동일',counts['same']),('처리 실패',counts['failed']),('완료 중 지식 전달 있음',summary['with_delivered_knowledge']),('진행 시간',f'{runtime/60:.1f}분')])+'</section>'
    content+='<section id="flow"><h2>문장 하나는 이 순서로 처리했습니다</h2><p>KG는 조건에 맞는 지식을 찾는 역할입니다. 문장을 실제로 쓰는 담당자는 Qwen입니다. 작성 뒤 다른 호출로 검사하지만 검사 결과로 출력을 덮어쓰지 않았습니다.</p><iframe title="실제 실행 흐름" src="pipeline.html"></iframe><p><a href="pipeline.html" target="_blank">흐름도를 크게 열기</a></p><div class="flow"><span>50개 표준어</span>→<span>형태·절·뜻 분석</span>→<span>조건에 맞는 KG 지식</span>→<span>Qwen 전체 문장</span>→<span>원본 그대로 기록</span></div></section>'
    content+='<section><h2>숫자가 말해 주는 것과 말해 주지 않는 것</h2>'+bars([('출력이 원문과 달라짐',counts['changed']),('출력이 원문과 같음',counts['same']),('전체 처리 실패',counts['failed']),('아직 미실행',counts['unattempted'])])+'<p>띄어쓰기·문장부호 하나만 달라도 “변경”으로 셉니다. 바뀐 문장이 자연스럽다는 뜻은 아닙니다. 참조 문장과 다르다고 자동으로 오답 처리하지 않았습니다.</p></section>'
    content+='<section><details><summary><b>50문장이 어느 단계까지 갔는지 한눈에 보기</b></summary><p>초록 표시는 해당 단계의 기록이 있다는 뜻입니다. 언어 분석이나 출력이 올바르다는 뜻은 아닙니다. 초안은 있지만 뒤 단계에서 실패한 경우도 구분해서 볼 수 있습니다.</p>'+table(['문장','절 범위 확정','의미 연결 저장','KG 조회 저장','작성 초안','검사 처리 기록'],heat)+'</details></section>'
    paired=[];case_by={c['id']:c for c in cases}
    for stem,focus in [('ADVCE001','정차하나요 / 정차했나요'),('ADVCE002','계세요 / 계셨어요'),('ADVCE003','제가 닫다 / 저절로 닫히다'),('ADVCE005','동료예요 / 동료를 도와요'),('ADVCE006','저는 / 나는'),('ADVCE008','지금 읽고 있는 / 전에 읽던'),('ADVCE010','물음표 / 마침표')]:
        a=case_by[stem+'A'];b=case_by[stem+'B']
        paired.append([E(focus),E(a['source'])+'<hr><b>'+E(a['output'] or '아직 완료 출력 없음')+'</b>',E(b['source'])+'<hr><b>'+E(b['output'] or '아직 완료 출력 없음')+'</b>'])
    content+='<section><details><summary><b>비슷한 문장 쌍에서 무엇이 달라졌는지 비교하기</b></summary><p>위는 표준어 입력, 아래 굵은 글씨는 이번 출력입니다. 과거·높임·뜻 차이가 남았는지 직접 비교해 볼 수 있습니다. 각각 한 번 실행한 결과이며 자동 정답 판정은 하지 않았습니다.</p>'+table(['비교할 입력 차이','A 문장 → 출력','B 문장 → 출력'],paired)+'</details></section>'
    content+='<section id="results"><h2>50문장: 원문 · 승인 참조 · 실제 출력</h2><p>승인 참조는 사용자가 앞서 승인한 Claude 번역입니다. <b>모델에게 답으로 전달하지 않았습니다.</b> ID를 누르면 그 문장의 분석→조회→전달→생성을 확인할 수 있습니다. 전달/사용 열에서 사용은 모델의 자기 신고입니다.</p><div class="controls"><input id="search" placeholder="문장이나 ID로 검색" aria-label="문장 검색"><select id="filter" aria-label="조건 선택"><option value="all">모두 보기</option><option value="changed">원문과 달라진 출력</option><option value="same">원문 그대로</option><option value="failed">처리 실패</option><option value="no_knowledge">전달된 지식 없음</option><option value="unresolved">미확정 조건 있음</option></select><b id="visible"></b><a href="outputs.csv">엑셀용 CSV</a></div><div class="scroll"><table class="outputs"><thead><tr><th>ID / 처리</th><th>표준어 원문</th><th>사용자 승인 참조</th><th>Qwen 최종 출력</th><th>전달 / 사용</th></tr></thead><tbody id="overview">'+''.join(overview)+'</tbody></table></div></section>'
    content+='<section id="cost"><h2>어디에 호출과 토큰을 썼나?</h2><p>네 담당자는 서로 다른 모델이 아니라 같은 Qwen을 역할별로 호출한 것입니다. 아래는 서버 응답에 기록된 사용량입니다. 시간 합은 각 호출의 시간이며 전체 경과 시간과 다를 수 있습니다.</p>'+bars([(stage_names.get(k,k),v['tokens']) for k,v in stagecost.items()],'토큰')+table(['담당','응답 메타 기록','입출력 토큰 합','호출 시간 합'],[[E(stage_names.get(k,k)),str(v['calls']),f"{v['tokens']:,}",f"{v['seconds']:.1f}초"] for k,v in stagecost.items()])+'<p>전체 시도 '+str(metrics.get('api_attempts','집계 중'))+'회 · 토큰 사용량 없는 응답 '+str(metrics.get('calls_without_usage','집계 중'))+'개. 금전 비용은 계산하지 않았습니다.</p></section>'
    content+='<section id="findings"><h2>확인한 문제와 다음 작업</h2><p>아래는 연구 리드가 실제 출력과 요청을 대조한 사례입니다. 전체 50건의 자연스러움 판정을 대신하지 않습니다. 이번 실행 중 코드·KG·지시문은 고정했습니다.</p>'
    content+=table(['사례','확인 내용'],[[f'<a href="#case-{E(k)}">{E(k)}</a>',list_text(v if isinstance(v,list) else [v])] for k,v in notes.items()]) if notes else '<p>아직 사례별 수동 대조를 마치지 않았습니다.</p>'
    content+='<p>다음은 같은 오류를 묶어 <b>① 분석값부터 잘못됐는지 ② 맞는 지식을 찾지 못했는지 ③ 전달된 내용을 작성자가 따르지 않았는지</b> 나눕니다. 생성 오류를 분석 워커 추가만으로 해결된다고 가정하지 않습니다. 문헌 지식 추가나 모델 역할 변경이 필요하면 변경 이유·비교 조건을 먼저 제시합니다.</p></section>'
    content+='<section><h2>문장별 처리 기록</h2><p>필요한 문장만 펼쳐 보세요. 영어 코드와 긴 원본 자료는 가장 아래의 기술 근거 링크로 분리했습니다.</p>'+''.join(details)+'</section>'
    validation=summary['validation']
    content+='<section><h2>재현 정보와 확인 범위</h2>'+table(['항목','기록'],[[E('실행 ID'),E(run.name)],[E('분석 방식'),E('Kiwi + Qwen 절 범위 + Qwen 의미·관계(명시 연결 질문)')],[E('생성·검사'),E('Qwen 전체 문장 작성 / 별도 Qwen 검사 / 자동 수정 0회')],[E('모델·설정'),E(config['model_id']+' · 온도 0 · seed '+str(config['seed']))],[E('데이터 용도'),E('이미 개선에 사용한 50건의 회귀 검사. 독립 최종 평가 아님.')],[E('원시 작성 출력 = 완료 결과'),E(str(validation['checked_outputs'])+'건 대조 / '+str(validation['raw_writer_matches_all_completed']))],[E('모델 요청에 참조 필드 없음'),E(str(validation['checked_requests'])+'개 대조 / '+str(validation['no_reference_fields_in_request_payloads']))],[E('기록 파일 해시 확인'),E(str(validation.get('artifact_files','진행 중'))+'개 / 불일치 '+str(len(validation.get('artifact_mismatches',[]))))]])+'<p>'+link(run/'config.json','실행 설정')+' · '+link(run/'metrics.json','원본 집계')+' · '+link(out/'summary.json','보고서 집계')+' · '+link(HERE/'PLAN.md','실험 범위와 종료 기준')+'</p><p>이번 보고서의 사례 해석은 연구 리드의 기록 대조입니다. 추가 Claude·Codex 독립 검토나 사람의 블라인드 품질 평가는 수행한 것으로 표시하지 않습니다.</p></section>'
    css='''*{box-sizing:border-box}html{scroll-behavior:auto}body{margin:0;background:#eef3f8;color:#172a40;font:16px/1.75 "Malgun Gothic",sans-serif}main{max-width:1450px;margin:auto;padding:32px}header,section{background:white;border:1px solid #dbe4ed;border-radius:18px;padding:28px;margin-bottom:22px}h1{font-size:36px;line-height:1.3}h2{font-size:25px;color:#173c5f}h3{margin-top:28px}h4{margin:8px 0;color:#255c7c}p{max-width:1100px}.eyebrow{color:#197277;font-weight:700}a{color:#075fab}nav,.controls{display:flex;flex-wrap:wrap;gap:16px;align-items:center}nav a{background:#edf5fb;padding:9px 15px;border-radius:8px;text-decoration:none}.cards{display:grid;grid-template-columns:repeat(6,1fr);gap:14px}.cards div{border-left:4px solid #23948a;padding-left:15px}.cards b{font-size:30px;display:block}.cards span{font-size:14px}.alert,.note{background:#fff5e8;border-left:4px solid #dd931e;padding:16px}.muted,small{color:#5c6f80}small{display:block;font-size:12px;overflow-wrap:anywhere}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}th{background:#eaf2f8;text-align:left;white-space:nowrap}td,th{padding:13px;border:1px solid #dce4eb;vertical-align:top}td{overflow-wrap:anywhere}.outputs{table-layout:fixed;min-width:950px}.outputs th:nth-child(1){width:150px}.outputs th:last-child{width:85px}.case{border:1px solid #cddde8;border-radius:12px;padding:18px;margin:16px 0;scroll-margin-top:12px}.case>summary{font-weight:700;cursor:pointer}.badge{font-size:12px;background:#edf3f8;padding:4px 8px;border-radius:5px}.triptych{display:grid;grid-template-columns:repeat(3,1fr);gap:15px;margin-top:20px}.triptych>div{background:#f1f7fa;padding:16px;border-radius:10px}.triptych>div:last-child{background:#eaf5ef}.triptych p{font-size:19px}.barrow{display:grid;grid-template-columns:190px 1fr 140px;align-items:center;gap:14px;margin:14px 0}.track{background:#eaf0f5;height:20px;border-radius:4px}.track i{display:block;background:#238b8d;height:100%;border-radius:4px}.barrow b{text-align:right}.flow{display:flex;flex-wrap:wrap;align-items:center;gap:10px}.flow span{padding:12px;border-radius:8px;background:#eaf4f7}input,select{font:inherit;padding:9px;border:1px solid #bacbd9;border-radius:6px}iframe{width:100%;height:520px;border:1px solid #dae4ed;border-radius:12px}details details{margin:15px 0}li{margin:6px 0}@media(max-width:850px){main{padding:12px}section,header{padding:18px}.cards{grid-template-columns:repeat(2,1fr)}.triptych{grid-template-columns:1fr}.barrow{grid-template-columns:125px 1fr 95px;font-size:13px}}@media print{.controls,iframe{display:none}body{background:white}main{padding:0}section,header{break-inside:avoid}.case{break-inside:auto}}'''
    js='''const search=document.getElementById('search'),filter=document.getElementById('filter');function update(){let n=0;document.querySelectorAll('[data-search]').forEach(el=>{let show=el.dataset.search.toLowerCase().includes(search.value.toLowerCase())&&(filter.value==='all'||el.dataset.tags.split(' ').includes(filter.value));el.hidden=!show;if(show&&el.tagName==='TR')n++;});document.getElementById('visible').textContent=n+' / 50건';}search.addEventListener('input',update);filter.addEventListener('change',update);function reveal(){let id=decodeURIComponent(location.hash.slice(1)),el=document.getElementById(id);if(el&&el.classList.contains('case')){search.value='';filter.value='all';update();el.open=true;el.scrollIntoView();}}window.addEventListener('hashchange',reveal);update();reveal();'''
    (out/'report.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>최근 보완 방식 · 50문장 결과</title><style>'+css+'</style><main>'+content+'</main><script>'+js+'</script></html>',encoding='utf-8')
    shutil.copy2(ROOT/'.archify/workflow-full50-20261109-1210/pipeline.html',out/'pipeline.html')
    save(HERE/'latest.json',{'run':run.relative_to(ROOT).as_posix(),'report':(out/'report.html').relative_to(ROOT).as_posix()})
    print(json.dumps({k:v for k,v in summary.items() if k not in ('stage_cost','metrics')},ensure_ascii=False))
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);args=p.parse_args();build(args.run.resolve())
