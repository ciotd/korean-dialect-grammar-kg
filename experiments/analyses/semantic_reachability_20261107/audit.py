"""Natural-sentence reachability audit. No model calls or graph changes."""
import collections
import copy
import datetime as dt
import html
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'local/python')]
from kg_pipeline.integrated import IntegratedReader,observe_units,retrieve_packet,analysis_contract
from kg_pipeline.io import read,save,dumps,sha
from kg_runtime.morphology import Morphology
from cases import PROBES,GOALS

HERE=Path(__file__).resolve().parent
BASE=ROOT/'experiments/runs/20261106T052943610843Z_integrated_grammar_regression/private/records'

LABELS={'source_form':'입력 형태','source_final':'마지막 어미','lemma':'기본 어간·낱말','unit_kind':'분석 단위',
'speech_act':'문장이 하는 일','addressee_level':'상대방에게 쓰는 높임','question_kind':'질문 종류','clause_role':'문장 안 역할',
'predicate_class':'동사·형용사·계사 구별','prefinal_type':'선어말어미 종류','prefinal_sequence':'선어말어미 순서',
'subject_honorific':'주어 높임','tense':'시간 의미','polarity':'긍정·부정','semantic_function':'해당 부분의 뜻',
'auxiliary_kind':'보조용언의 기능','voice':'능동·피동·사동','root_tag':'본용언·보조용언 형태표지','morph_tag':'품사 표지','ending_tag':'어미 위치 표지',
'nominal_kind':'명사의 종류','nominal_host':'조사가 붙은 명사','main_predicate':'본동작','auxiliary_predicate':'보조동작','left_predicate':'앞절 서술어','right_predicate':'뒤절 서술어'}
VALUES={'statement':'평서','information_question':'답을 묻는 질문','request':'부탁','command':'명령','prohibition':'금지','suggestion':'함께 하자는 제안','promise':'약속','exclamation':'감탄','plain':'반말','polite':'해요체 높임','formal':'격식 높임','main':'바깥 주절','embedded':'안긴절','quoted':'인용절','wh':'구체적인 답 질문','polar':'예/아니오 질문','confirmation':'확인 질문','verb':'동사','adjective':'형용사','copula':'이다','negative_copula':'아니다','absent':'없음','present':'있음/현재','past':'과거','negative':'부정','positive':'긍정','recipient':'받는 대상','comitative':'동반','comparison':'비교','condition':'조건','reason':'이유','sequence':'순서','interrogative':'의문사','benefactive':'남을 위해 하는 행동','progressive':'진행','resultative':'결과·완료','other':'그 밖의 기능','unknown':'미확정','none':'해당 없음','eoss':'-었- 계열','si':'-시-','si_eoss':'-시- + -었-','predicate':'서술어 단위','construction':'본용언+보조용언 구성','particle':'조사 단위','connector':'연결·전성 어미','nominal':'명사류 단위','purpose':'목적','simultaneity':'동시','intention':'의도','quotation':'인용','become_auxiliary':'-게 되다 구성'}


def relevant(reader,unit,features,rid):
    trace=reader.query(unit,features)
    return next((h for key in ('eligible','unresolved','rejected') for h in trace[key] if h['rule_id']==rid),None),trace


def hard_mismatches(reader,unit,rid):
    mismatches=[]
    for branch in reader.rules[rid]['branches']:
        wrong=[]
        for key,allowed in branch['conditions'].items():
            if key=='predicate_class':continue  # Qwen can override Kiwi's class.
            if key in unit['observed'] and unit['observed'][key] not in allowed:
                wrong.append({'feature':key,'observed':unit['observed'][key],'allowed':allowed})
        mismatches.append(wrong)
    return min(mismatches,key=len)


def best_target(reader,units,goal):
    candidates=[u for u in units if u['kind']==goal['kind'] and goal['target'] in u['text']]
    if not candidates:return None
    rid=goal['rule_id']
    if not rid:return candidates[0]
    def score(u):
        h,_=relevant(reader,u,u['features'],rid)
        return (0 if h and h['state']=='eligible' else 1,len(hard_mismatches(reader,u,rid)),
                min((sum(c['state']!='true' for c in b['checks']) for b in h['branches']),default=999) if h else 999)
    return min(candidates,key=score)


def goal_check(reader,units,goal,packet):
    out=copy.deepcopy(goal);rid=goal['rule_id'];unit=best_target(reader,units,goal)
    out['judgment_basis']='lead interpretation of input; not an independent gold label'
    if not rid:
        out['status']='knowledge_scope_not_supported';out['fix']='목표 표현·용법을 문헌과 확인하여 새 규칙 또는 기존 규칙의 적용 범위를 설계한다. 단순 조건 삭제는 하지 않는다.'
        if unit:out['unit_id']=unit['id'];out['actual_features']=unit['features']
        return out
    if not unit:
        out['status']='target_unit_not_found';out['fix']='분석기가 만든 단위와 문장의 실제 위치를 대조하고 대상 추출을 보완한다. 모델 의미 판단을 바꿔도 없는 단위는 생기지 않는다.';return out
    hit,trace=relevant(reader,unit,unit['features'],rid)
    out.update(unit_id=unit['id'],actual_target=unit['text'],actual_features=unit['features'],actual_relations=unit.get('relations',{}),
               hit=hit,hard_mismatches=hard_mismatches(reader,unit,rid),actual_eligible=[x['rule_id'] for x in trace['eligible']])
    if hit and hit['state']=='eligible':
        delivered=any(a['unit_id']==unit['id'] and a['rule_id']==rid for a in packet['verified_scope_knowledge'])
        out.update(status='reached_and_delivered' if delivered else 'reached_not_delivered',fix='조회 이후의 결합·생성은 별도 확인한다.' if delivered else '전달 예산과 우선순위 때문에 빠진 것인지 확인한다.')
        return out
    original=unit['features'];changed={k:{'before':original.get(k),'diagnostic_value':v} for k,v in goal['expected_meaning'].items() if original.get(k)!=v}
    single=[]
    for k,v in goal['expected_meaning'].items():
        h,_=relevant(reader,unit,{**original,k:v},rid)
        if h and h['state']=='eligible' and k in changed:single.append(k)
    diagnostic,_=relevant(reader,unit,{**original,**goal['expected_meaning']},rid)
    out.update(diagnostic_meaning_changes=changed,single_meaning_change_enables=single,
               diagnostic_meaning_only_state=diagnostic['state'] if diagnostic else 'not_dispatched',
               diagnostic_warning='수동 의미 보충 실험. 실제 Qwen 재분석 결과나 수정 채택이 아님.')
    if out['hard_mismatches']:
        out.update(status='observed_form_or_rule_scope_mismatch',fix='실제 형태 표지와 규칙이 기대한 표지를 대조한다. 분석기 정규화 문제인지, 원래 이 규칙 밖의 용법인지 구분한 뒤 입력 연결 또는 규칙 설명을 수정한다.')
    elif diagnostic and diagnostic['state']=='eligible':
        out.update(status='meaning_judgment_candidate',fix='문맥 해석을 먼저 검토한다. 수동 의미값 보충만으로 후보가 되므로 분석 질문·값 정의를 보완하는 비교 실험 대상이다.')
    elif diagnostic and diagnostic['missing_relations']:
        out.update(status='relation_binding_missing',fix='같은 문장 안의 실제 명사·본용언·보조용언·앞뒤 절을 지목하는 연결이 빠졌는지 확인한다. 존재하는 후보 관계를 모델에 보여 주고 선택하게 하는 개선을 검토한다.')
    else:
        out.update(status='combined_or_unresolved',fix='미확정 특징·뜻 해석·규칙 범위가 함께 남아 있다. 이 표만으로 모델 오류라고 확정하지 않고 원문 위치와 조건을 대조한다.')
    return out


def run():
    stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out=HERE/'private'/stamp;out.mkdir(parents=True,exist_ok=False)
    pointer=read(ROOT/'knowledge/authored/semantic_grammar_20261107_separated_r1/latest.json');graph=read(ROOT/pointer['graph']);reader=IntegratedReader(graph)
    assert {x[0] for x in PROBES}==set(reader.rules),'Probe coverage must include every actual rule'
    sources={}
    for rel in ('src/kg_pipeline/integrated.py','src/kg_pipeline/separated_graph.py','src/kg_runtime/morphology.py'):
        sources[rel]=sha((ROOT/rel).read_bytes());dest=out/'code_snapshot'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,dest)
    for name in ('cases.py','audit.py','PLAN.md'):shutil.copy2(HERE/name,out/name)
    save(out/'config.json',{'graph':pointer['graph'],'graph_sha256':sha((ROOT/pointer['graph']).read_bytes()),'codes':sources,
          'scope':'56 rule contents/57 branches; all regression50 plus saved analysis coverage','new_qwen_calls':0,
          'qwen_availability':'connection attempt returned URLError; no server-fault diagnosis','expectation_role':'lead_authored_diagnostic_not_gold'})
    # Real, previously returned Qwen analysis; never fill missing fields here.
    coverage={rid:{'eligible_units':0,'unresolved_units':0,'example_records':[]} for rid in reader.rules}
    records_count=0;unit_count=0
    for p in sorted((ROOT/'experiments/runs').glob('*_integrated_grammar_*/private/records/*/bound_analysis.json')):
        units=read(p);records_count+=1;unit_count+=len(units)
        for u in units:
            trace=reader.query(u,u['features'])
            for state,key in [('eligible','eligible_units'),('unresolved','unresolved_units')]:
                for hit in trace[state]:
                    item=coverage[hit['rule_id']];item[key]+=1
                    if state=='eligible' and len(item['example_records'])<3:item['example_records'].append({'record':p.parents[3].name+'/'+p.parent.name,'unit_id':u['id'],'text':u['text']})
    save(out/'recorded_rule_coverage.json',coverage)
    morphology=Morphology();probes=[]
    for i,(rid,text,target) in enumerate(PROBES,1):
        morph=morphology.analyze(text);units=observe_units(morph);kind=reader.rules[rid]['branches'][0]['conditions']['unit_kind'][0]
        candidates=[u for u in units if u['kind']==kind and target in u['text']]
        if not candidates:status='target_not_created';wrong=[];best=None
        else:
            best=min(candidates,key=lambda u:len(hard_mismatches(reader,u,rid)));wrong=hard_mismatches(reader,best,rid)
            status='observed_condition_block' if wrong else 'observation_ready_meaning_unchecked'
        item={'case_id':f'PROBE{i:03}','rule_id':rid,'text':text,'target':target,'kind':kind,'status':status,'mismatches':wrong,'observed_unit':best,
              'new_qwen_analysis':False,'grammar_certified':False}
        probes.append(item);save(out/'probes'/f'PROBE{i:03}.json',{'case':item,'morphology':morph,'units':units,'analysis_schema':analysis_contract(reader,units)})
    save(out/'natural_probes.json',probes)
    rows=[];all_ids={read(p)['id'] for p in BASE.glob('*/input.json')};assert all_ids==set(GOALS)
    for path in sorted(BASE.glob('*/input.json')):
        inp=read(path);bound=path.parent/'bound_analysis.json';record={'id':inp['id'],'input':inp['text'],'expectation_status':'lead_diagnostic_requires_semantic_review'}
        for g in GOALS[inp['id']]:assert g['rule_id'] is None or g['rule_id'] in reader.rules
        if not bound.exists():
            record.update(status='analysis_unavailable',goals=[{**g,'status':'analysis_unavailable','fix':'先 확인: 당시 분석 실패 기록. 정상 분석이 확보되어야 조건 조회를 검증할 수 있다.'} for g in GOALS[inp['id']]])
        else:
            units=read(bound);packet,traces=retrieve_packet(reader,inp['text'],units)
            record.update(status='audited',goals=[goal_check(reader,units,g,packet) for g in GOALS[inp['id']]],
                 all_actual_rule_ids=sorted({x['rule_id'] for x in packet['verified_scope_knowledge']}),
                 input_sha256=sha(path.read_bytes()),analysis_sha256=sha(bound.read_bytes()))
            save(out/'records'/inp['id']/'actual_trace.json',{'input':inp,'units':units,'traces':traces,'packet':packet})
        if (path.parent/'result.json').exists():record['historical_output']=read(path.parent/'result.json').get('output_text')
        save(out/'records'/inp['id']/'judgment.json',record);rows.append(record)
    save(out/'regression50.json',rows)
    counts=collections.Counter(g['status'] for r in rows for g in r['goals'])
    summary={'run_id':stamp,'regression_inputs':len(rows),'recorded_analyses':records_count,'recorded_units':unit_count,
       'rules_total':len(reader.rules),'rules_reached_on_saved_analysis':sum(x['eligible_units']>0 for x in coverage.values()),
       'probe_sentences':len(probes),'probe_states':dict(collections.Counter(p['status'] for p in probes)),
       'reviewed_target_goals':sum(len(r['goals']) for r in rows),'goal_states':dict(counts),
       'meaning_only_diagnostic_enablements':sum(g.get('diagnostic_meaning_only_state')=='eligible' for r in rows for g in r['goals']),
       'fresh_qwen_calls':0,'kg_modified':False,'independent_linguistic_accuracy':None}
    save(out/'summary.json',summary);save(HERE/'latest.json',{'directory':str(out.relative_to(ROOT)),**summary})
    print(dumps(summary))
    print('PROBE BLOCKS:')
    for p in probes:
        if p['status']!='observation_ready_meaning_unchecked':print(dumps({k:p[k] for k in ('rule_id','text','status','mismatches')}))
    print('REGRESSION FAILURES:')
    for row in rows:
        for g in row['goals']:
            if g['status'] not in ('reached_and_delivered','knowledge_scope_not_supported'):
                print(dumps({'id':row['id'],'target':g['target'],'rule_id':g['rule_id'],'status':g['status'],
                      'hard':g.get('hard_mismatches'),'changes':g.get('diagnostic_meaning_changes'),
                      'missing':g.get('hit',{}).get('missing_relations') if g.get('hit') else None}))
    return out


if __name__=='__main__':run()
