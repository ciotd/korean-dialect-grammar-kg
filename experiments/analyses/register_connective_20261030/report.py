"""Report actual saved experiment results; no naturalness/accuracy invented."""
import collections,hashlib,html,json,statistics,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2];P=BASE/'private';sys.path[:0]=[str(ROOT/'local/python'),str(ROOT/'src')]
from kg_runtime.compatibility import assess
E=lambda x:html.escape(str(x if x is not None else '출력 없음'))
HASHES={}
def read(p):
    raw=p.read_bytes();HASHES[str(p.relative_to(ROOT))]=hashlib.sha256(raw).hexdigest();return json.loads(raw)
def save(name,value):(P/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def optional(p):return read(p) if p.exists() else None
def table(head,rows):return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+E(x)+'</th>' for x in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>'
NAMES={'politeness_mismatch':'말높임 불일치','source_connective_mismatch':'연결어미 원형 불일치','explicit_source_ending_mismatch':'카드의 지정 원형과 불일치','final_card_on_nonfinal':'종결카드를 연결 위치에 사용',
 'predicate_kind_disagreement':'서술어 종류 불일치','source_suffix_composition_disagreement':'어휘·시제·접사 보존 미확인','function_not_supported':'문법 기능 불일치','function_unverified':'문법 기능 미확인',
 'scoped_operation_source_unavailable':'지정 교체 범위 밖','source_analysis_conflict':'Kiwi·Qwen 분석 충돌','function_evidence_insufficient':'화행 근거 부족','target_realization_unverified':'활용형 실현 미확인',
 'new_unjoined_jamo':'글자로 합쳐지지 않은 자음·모음','non_stop_finish:length':'답변을 끝내지 못하고 출력 길이 한도 도달','model_requested_hold':'모델이 변경 보류 요청',
 'invalid_target_index':'모델이 존재하지 않는 형태소 위치를 지정', 'particle_edit_changes_other_material':'조사를 바꾸며 다른 부분도 변경',
 'protected_punctuation_changed':'문장부호 변경','unlicensed_word_expansion':'지정 범위 밖 단어 추가','unresolved_card_condition':'확정하지 못한 카드 조건',
 'whole_word_not_suffix':'어미가 아닌 단어 전체를 변경','binding_not_ending':'어미가 아닌 위치를 어미로 지정','dependency_group_not_applied':'함께 필요한 다른 변경이 보류됨','user_restricted_conversion':'사용자가 제외한 변환'}
def collect(run,id):
    folder=ROOT/'experiments/runs'/run/'private/records'/id;r=read(folder/'result.json')
    result={'result':r,'path':str(folder.relative_to(ROOT))}
    for name,key in [('final_plan.json','plan'),('reference_packet.json','packet'),('morphology.json','morph'),('compatibility_selection.json','selection')]:
        result[key]=optional(folder/name)
    incidents=[]
    if result['plan'] and result['packet']:
        cards={c['id']:c for c in result['packet']['cards']};words={w['uid']:w for w in result['morph']['words']}
        units={u['word_id']:u for u in result['packet']['grammar']['units']}
        for edit in result['plan']['edits']:
            if edit['outcome']!='applied':continue
            codes=set()
            for b in edit['bindings']:
                info=assess(cards[b['card_id']],words[b['source_word_id']],units.get(b['source_word_id'],{}))
                codes.update(info['blocks'])
            if codes:incidents.append({'edit_id':edit['edit_id'],'before':edit['before'],'after':edit['after'],'codes':sorted(codes),'card_ids':edit['rule_ids']})
    result['applied_condition_flags']=incidents
    result['failure_details']=[{'stage':c.get('stage'),'error':c.get('error'),'finish_reason':c.get('finish_reason')} for c in r.get('calls',[]) if c.get('status')=='failed']
    if r['output_text'] is None and not result['failure_details']:result['failure_details']=[{'stage':r['status'],'error':r.get('error','unknown')}]
    return result

def main():
    active=read(P/'active_run.json');inputs=ROOT/'data/derived_private/standard_inputs_50_20261029_v2/inputs.jsonl'
    raw=inputs.read_bytes();HASHES[str(inputs.relative_to(ROOT))]=hashlib.sha256(raw).hexdigest();data=[json.loads(x) for x in raw.decode('utf8').splitlines()]
    ref=ROOT/'data/derived_private/gyeongsang_reference50_20261030_v1/references.jsonl';raw=ref.read_bytes();HASHES[str(ref.relative_to(ROOT))]=hashlib.sha256(raw).hexdigest();refs={r['id']:r for r in map(json.loads,raw.decode('utf8').splitlines())}
    rows=[]
    for record in data:
        r={'id':record['id'],'input':record['text'],'reference':refs[record['id']]['reference'],'arms':{}}
        assert r['input']==refs[r['id']]['input']
        for arm in ('single','multi'):
            r['arms'][arm]={period:collect(active[key][arm],r['id']) for period,key in [('old','baselines'),('new','runs')]}
            assert all(v['result']['input_text']==r['input'] for v in r['arms'][arm].values())
        rows.append(r)
    summary={'inputs':len(rows),'runs':active['runs'],'baselines':active['baselines'],'counts':{},'cost':{},'condition_flags':{},'errors':{},'held':{},'repairs':{}}
    for arm in ('single','multi'):
        for period in ('old','new'):
            key=arm+'_'+period;vs=[r['arms'][arm][period] for r in rows];rs=[v['result'] for v in vs]
            summary['counts'][key]={'changed':sum(x['output_text'] is not None and x['output_text']!=x['input_text'] for x in rs),'unchanged':sum(x['output_text']==x['input_text'] for x in rs),'no_output':sum(x['output_text'] is None for x in rs)}
            calls=[c for r in rs for c in r['calls'] if c['stage']!='analysis'];times=[r['incremental_generation_seconds'] for r in rs]
            summary['cost'][key]={'generation_calls':len(calls),'generation_tokens':sum((c.get('usage') or {}).get('total_tokens',0) for c in calls),'mean_generation_seconds':statistics.mean(times),'median_generation_seconds':statistics.median(times),'basis':'generation only; analysis excluded for historical comparability; different server load'}
            summary['condition_flags'][key]=dict(collections.Counter(code for v in vs for i in v['applied_condition_flags'] for code in i['codes']))
            summary['errors'][key]=dict(collections.Counter(x['error'] for v in vs if v['result']['output_text'] is None for x in v['failure_details']))
            summary['held'][key]=dict(collections.Counter(code for v in vs for e in (v['plan'] or {}).get('edits',[]) if e['outcome']=='needs_review' for code in {x['code'] for x in e['issues']}))
            summary['repairs'][key]=dict(collections.Counter(x['kind'] for v in vs for e in (v['plan'] or {}).get('edits',[]) for x in e.get('repairs',[])))
    summary['resources']=read(ROOT/'experiments/batches'/active['batch']/'resources.json')
    summary['quality']={'naturalness':None,'independent_human_evaluation':False,'causal_claim':False,'comparison':'historical combined intervention with new analysis; not isolated KG benefit'}
    post={a:read(ROOT/'experiments/runs'/run/'postflight.json') for a,run in active['runs'].items()};assert all(all(v.values()) for v in post.values())
    for rel,h in HASHES.items():assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==h,rel
    save('cases.json',rows);save('summary.json',summary);save('input_hashes.json',HASHES);save('postflight_summary.json',post)
    tests=read(P/'tests_preexperiment.json')
    notes=optional(P/'interpretation.json')
    h='<header><p class="eyebrow">말높임·연결어미 보완 후 · 실제 Qwen 50문장 × 두 방식</p><h1>고친 부분과<br>아직 실패하는 부분을 나눠 봤습니다.</h1><p>이번에는 Qwen 분석부터 새로 실행했습니다. 아래 문장은 저장 기록 재생이 아닌 실제 새 응답을 처리한 결과입니다.</p></header>'
    h+='<nav><a href="#summary">숫자로 확인</a><a href="#findings">핵심 사례</a><a href="#design">고친 부분</a><a href="#cases">50문장 비교</a><a href="#cost">호출·시간</a><a href="#next">남은 문제</a><a href="/work">진행 기록</a></nav>'
    h+='<p><b>Single:</b> Qwen이 카드 선택과 표현 작성을 한 번에 합니다. <b>Multi:</b> Qwen이 먼저 수정 계획을 만들고, 별도 호출에서 표현을 작성합니다. 두 방식은 같은 문장 분석과 카드 목록을 받습니다.</p>'
    h+='<section id="summary"><h2>먼저 구분해야 할 것</h2><p class="notice"><b>변경 수와 검사 통과는 자연스러움 점수가 아닙니다.</b> 기존 분석 보완까지 함께 적용하고 새 Qwen 분석을 수행했습니다. 따라서 이번 차이를 말높임·연결어미 수정 두 가지의 단독 효과라고 볼 수 없습니다.</p>'
    nums=[]
    for a in ('single','multi'):
        for p,label in [('old','이전 실제 실험'),('new','이번 실제 실험')]:
            v=summary['counts'][a+'_'+p];nums.append([a.title(),label,v['changed'],v['unchanged'],v['no_output']])
    h+=table(['방식','실험','원문과 다름','원문 유지','출력 없음'],nums)
    if notes:h+='<h3>이번 결과의 결론</h3><p>'+E(notes.get('conclusion',''))+'</p>'
    h+='<h3>같은 검사로 이전·이번 적용 결과를 대조</h3><p>실제로 반영된 편집만 셉니다. 아래 수치는 코드가 확인할 수 있는 조건 위반이며, 모든 문법 오류나 방언 오류의 개수가 아닙니다. 한 편집에 여러 문제가 있을 수 있습니다.</p>'
    codes=sorted(set().union(*(set(v) for v in summary['condition_flags'].values())))
    h+=table(['검사 항목','이전 Single','이번 Single','이전 Multi','이번 Multi'],[[E(NAMES.get(c,c))]+[summary['condition_flags'][k].get(c,0) for k in ('single_old','single_new','multi_old','multi_new')] for c in codes])
    h+='<p>검사에 걸린 변경은 반영하지 않으므로 위반 수가 줄어들 수 있습니다. 이것만으로 더 자연스러워졌다고 판단할 수 없습니다. 원문 유지 수와 실제 문장을 함께 봐야 합니다.</p>'
    h+='</section><section id="findings"><h2>처음 문제로 삼았던 두 문장</h2>'
    for id in ('NEW004','LONG004'):
        row=next(r for r in rows if r['id']==id);h+='<article><h3>'+E(id)+'</h3><p><b>표준어:</b> '+E(row['input'])+'</p>'
        h+=table(['구분','이전','이번'],[[a.title(),E(row['arms'][a]['old']['result']['output_text']),E(row['arms'][a]['new']['result']['output_text'])] for a in ('single','multi')])
        h+='<p><b>승인 표현:</b> '+E(row['reference'])+'</p></article>'
    if notes and notes.get('trace_findings'):
        h+='<h3>실패 지점을 실제 기록에서 확인한 사례</h3>'+table(['문장','관찰한 현상','끊긴 위치','다음에 확인할 해결 방법'],[[E(x[k]) for k in ('id','observed','stage','next')] for x in notes['trace_findings']])
    h+='</section><section id="design"><h2>실제로 고친 부분</h2>'+table(['기존 문제','이번 처리','남는 한계'],[
        ['공손한 질문에 반말 카드 선택','원문의 종결형과 카드의 화계 대조. 같은 조회 결과에서 공손한 후보를 먼저 전달','화계 전체를 동일시하지 않음. 해라·해 / 하이소·해예 외 불분명한 대응은 미확인'],
        ['-는데에 -지만 전용 카드 사용','M07의 명시적 A→B 원형과 실제 연결어미 대조','넓은 의미가 비슷해도 대체 근거가 없으면 그대로 유지될 수 있음'],
        ['확인 질문 전용 카드를 일반 질문에 추천','카드에 기록된 source_endings도 대조','원형 일치만으로 모든 문맥 조건이 확인되는 것은 아님'],
        ['선별 기준과 모델 안내가 다름','같은 후보 자격 함수를 공유','추천은 후보이며 정답 인증이 아님'],
        ['오아도·매개모음 탈락 같은 조합','오+아/우+어의 명백한 미축약 및 조건형의 원문 으 보존을 기록하며 조합','전체 방언 활용기를 만든 것은 아님'],
        ['운동하-의 하 같은 파생접사 누락','XSV·XSA도 보존 검사에 포함','Kiwi 재분석은 방언 정확성 판정기가 아님']])
    h+='<div class="flow"><span>새 Qwen 분석</span><b>→</b><span>실제 KG 조회</span><b>→</b><span>어절별 조건 맞는 후보 우선</span><b>→</b><span>Qwen 선택·활용</span><b>→</b><span>조건·보존 재검사</span></div><p>카드 721개와 KG 내용은 수정하지 않았습니다. 최대 48개는 이번에 유지한 전달 상한이며 최적값을 입증한 것이 아닙니다. 상한 안에서 어절별 대안 후보를 먼저 배치합니다.</p></section>'
    h+='<section id="cases"><h2>50문장 전체 비교</h2><div class="controls"><label>검색 <input id="search" placeholder="번호 또는 문장"></label><label><input id="different" type="checkbox"> 이전과 달라진 문장만</label><span id="count"></span></div>'
    for r in rows:
        diff=any(v['old']['result']['output_text']!=v['new']['result']['output_text'] for v in r['arms'].values())
        h+=f'<details class="case" id="{E(r["id"])}" data-different="{str(diff).lower()}"><summary>{E(r["id"])} · {E(r["input"])}</summary><p><b>사용자가 승인한 표현:</b> {E(r["reference"])}</p>'
        h+=table(['방식','이전 실제 출력','이번 실제 출력'],[[a.title(),E(v['old']['result']['output_text']),E(v['new']['result']['output_text'])] for a,v in r['arms'].items()])
        h+='<details><summary>어떤 카드를 선택했고 무엇이 적용·보류됐나</summary>'
        for arm,versions in r['arms'].items():
            v=versions['new'];h+='<h3>'+arm.title()+'</h3>'
            if v['result']['output_text'] is None:h+='<p>출력 실패: '+E(' / '.join(NAMES.get(x['error'],x['error']) for x in v['failure_details']))+'</p>'
            edits=(v['plan'] or {}).get('edits',[]);er=[]
            for e in edits:
                reason=' / '.join(NAMES.get(x['code'],x['code']) for x in e['issues']) or e.get('reason','')
                outcome={'applied':'반영','needs_review':'보류','kept':'유지','unchanged':'변경 없음'}.get(e['outcome'],e['outcome'])
                er.append([E(e['before']),E(e.get('proposed_after',e['after'])),E(e['after']),E(outcome),E(reason),E(', '.join(e['rule_ids']))])
            if er:h+=table(['원문 부분','Qwen 제안','처리 형태','결과','이유','카드'],er)
        selection=r['arms']['single']['new']['selection']
        if selection:
            h+='<h3>같은 조회 결과에서 찾은 대체 후보</h3>'+table(['원문 부분','추천 후보 ID','상태'],[[E(x['source']),E(', '.join(x['alternatives']) or '없음'),'후보 있음 · 추가 조건 확인 필요' if x['alternatives'] else '이번 조건으로 후보를 찾지 못함'] for x in selection['per_word']])
        h+='</details></details>'
    h+='</section><section id="cost"><h2>호출·토큰·시간</h2><p>이전 실험은 분석을 재사용했고 이번에는 새로 분석했습니다. 비교표에서는 양쪽 모두 분석 비용을 제외한 생성 단계만 표시합니다. 서버 부하와 모델 응답도 달라질 수 있습니다.</p>'
    h+=table(['방식','실험','생성 호출','생성 단계 토큰','입력당 생성 시간 평균'],[[a.title(),('이전' if p=='old' else '이번'),summary['cost'][a+'_'+p]['generation_calls'],format(summary['cost'][a+'_'+p]['generation_tokens'],','),f'{summary["cost"][a+"_"+p]["mean_generation_seconds"]:.1f}초'] for a in ('single','multi') for p in ('old','new')])
    resource=summary['resources'];h+=f'<p>이번 전체 실제 호출: <b>{resource["physical_api_attempts"]}회</b> · 전체 토큰: <b>{resource["physical_total_tokens"]:,}</b> · 두 방식과 공유 분석을 합친 실행 시간: <b>{resource["wall_seconds"]/60:.1f}분</b>. 금액·GPU 사용량은 측정하지 않았습니다. 사전 3문장 실행 비용은 이 수치에 포함하지 않습니다.</p></section>'
    h+='<section id="next"><h2>남은 문제와 다음 판단</h2>'
    failures=[[E(r['id']),a.title(),E(' / '.join(NAMES.get(x['error'],x['error']) for x in v['new']['failure_details']))] for r in rows for a,v in r['arms'].items() if v['new']['result']['output_text'] is None]
    if failures:h+='<h3>완성 출력이 없었던 경우</h3>'+table(['문장','방식','저장된 실패 원인'],failures)
    if notes:
        h+='<ul>'+''.join('<li>'+E(x)+'</li>' for x in notes['findings'])+'</ul><p><b>다음 제안:</b> '+E(notes['next'])+'</p>'
    else:h+='<p>결과별 검토 의견 작성 중. 현재 표는 실제 저장 결과입니다.</p>'
    h+=f'<p>프로그램 검사 {tests["tests"]}개 통과. 50개 입력·100개 결과 및 코드·KG 해시를 보존했습니다. 이번 세트는 이미 개선에 사용한 회귀 테스트셋이며 독립 최종 평가가 아닙니다.</p><p>판단 근거: 원문 → 분석 → 조회 → 추천 → 선택 → 적용/보류 기록. 승인 표현은 모델 입력에 제공하지 않았습니다.</p></section>'
    (P/'report.html').write_text('<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>말높임·연결어미 보완 Qwen 실험</title><link rel="stylesheet" href="report.css"><script defer src="report.js"></script></head><body><main>'+h+'</main></body></html>',encoding='utf8')
    oldcss=ROOT/'experiments/analyses/contract_alignment_20261030/private/report.css';(P/'report.css').write_bytes(oldcss.read_bytes())
    (P/'report.js').write_text("const q=document.getElementById('search'),d=document.getElementById('different'),rows=[...document.querySelectorAll('.case')];function filter(){let n=0;for(const r of rows){r.hidden=!(r.textContent.toLowerCase().includes(q.value.toLowerCase())&&(!d.checked||r.dataset.different==='true'));if(!r.hidden)n++;}document.getElementById('count').textContent=n+' / 50문장';}q.addEventListener('input',filter);d.addEventListener('change',filter);filter();",encoding='utf8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
