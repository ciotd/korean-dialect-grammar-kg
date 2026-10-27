"""Derive reproducible audit/comparison without modifying any run artifact."""
import argparse,collections,json,statistics,sys
from pathlib import Path
PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/'src'))
from kg_pipeline.io import read,save,load_jsonl,sha
from kg_pipeline.validation import locate
from research_management.core import Registry
OLD='20261023T090255985956Z_qwen_kg_first50'
OUT=PROJECT/'experiments/analyses/redesign_20261024/private'

def load(path,default=None):return read(path) if path.is_file() else default

def old_audit():
    folder=PROJECT/'experiments/runs'/OLD;rows=read(folder/'private/results.json');audit=[]
    for r in rows:
        f=folder/'private/records'/r['id'];a=load(f/'analysis_call/parsed.json',{});packet=load(f/'reference_packet.json',{})
        selected=[e for e in packet.get('evidence',[]) if e['role']=='realization_reference'];issues=[]
        clauses={c['cid']:c for c in a.get('clauses',[])}
        for unit in a.get('units',[]):
            try:
                span=locate(r['input_text'],unit['anchor']);parent=clauses.get(unit['cid'])
                if parent:
                    ps=locate(r['input_text'],parent['anchor'])
                    if not ps[0]<=span[0]<span[1]<=ps[1]:issues.append({'kind':'unit_outside_clause','uid':unit['uid'],'unit':unit['anchor'],'clause':parent['anchor'],'actual_span':span,'parent_span':ps})
            except ValueError as e:issues.append({'kind':'anchor_not_in_input','uid':unit['uid'],'unit':unit['anchor'],'error':str(e)})
        decisions=load(f/'selection_audit.json',{}).get('decisions',[])
        blockers=collections.Counter(c['condition'] for d in decisions if d.get('decision')=='deferred' for c in d.get('conditions',[]) if not c.get('matched'))
        stage='analysis' if r['status']=='analysis_failed' else 'selection' if not selected else 'generation'
        diagnosis=('원문 구간·절 연결 검사에서 중단. 그 이후 조회·생성은 실행되지 않음.' if stage=='analysis' else
          '변환용 근거가 0개여서 생성기의 변경 가능 범위가 없었음. 모든 보존이 언어 오류라는 뜻은 아님.' if not selected else
          '참고 근거를 받은 뒤 생성기가 보존 또는 변경을 선택함. 관련성과 의미 보존은 사례별 검토 필요.')
        if r['id'] in ('DEV003','DEV005'):diagnosis='완료 보조용언 근거가 해당 형용사 종결부에 선택됨. 생성기가 호환되지 않는다고 판단하여 보존함. 관련 없는 근거 선택이 확인됨.';stage='selection'
        if r['id']=='DEV026':diagnosis='조금→쪼께만을 선택하고 적용. 제한 의미의 만이 추가되는 대응 문제. 새 실행층은 조금만에만 이 후보를 허용함.';stage='selection'
        audit.append({'id':r['id'],'input':r['input_text'],'status':r['status'],'first_observed_problem_or_limit_stage':stage,
          'diagnosis':diagnosis,'confirmed_structural_issues':issues,'actual_error':r.get('error'),'reference_count':len(selected),
          'selected_references':[{'claim':e['claim_id'],'atom':e['atom_id'],'target':e['target_uid'],'forms':e.get('forms')} for e in selected],
          'blocked_condition_counts':dict(blockers),'generator':load(f/'generation_call/parsed.json'),
          'artifacts':{name:str((f/path).relative_to(PROJECT)) for name,path in [('analysis','analysis_call/parsed.json'),('selection','selection_audit.json'),('generation','generation_call/parsed.json')] if (f/path).exists()},
          'quality_gold_available':False})
    save(OUT/'previous50_audit.json',audit)
    return audit

def coverage():
    root=PROJECT/'knowledge/authored/kg_v3_evidence_20261019_r2'
    nodes=load_jsonl(root/'graph/nodes.jsonl');edges=load_jsonl(root/'graph/edges.jsonl');by={n['id']:n for n in nodes}
    ledger=read(PROJECT/'knowledge/authored/kg_runtime_20261024/coverage_ledger.json')
    modules=[]
    for n in nodes:
        if n['type']!='Module':continue
        members=[e['source'] for e in edges if e['relation']=='in_module' and e['target']==n['id']]
        atoms=[x for x in ledger if x['id'] in members]
        modules.append({'id':n['id'],'title':n['title'],'nodes':len(members),'atoms':len(atoms),
          'kinds':dict(collections.Counter(x['kind'] for x in atoms)),'compiled':sum(x['status']=='implemented' for x in atoms)})
    for x in ledger:
        rid=x['id']
        if x['status']=='implemented':x['explanation']='해당 ID에 원문 구간을 지정하는 조건과 표면형 조합 코드가 연결됨. 전체 언어학적 정당성 인증을 뜻하지 않음.'
        elif rid.startswith('GS_CONJ_'):x['explanation']='활용 부류 설명은 있으나 해당 어휘의 표준형→방언 어간/활용형 대조와 합성 코드가 없음. Kiwi의 표준어 join만으로 방언 활용을 보장할 수 없음.'
        elif rid.startswith('GS_GEORO_BLOCK'):x['explanation']='바꿔 쓰는 규칙보다 다른 -거로 규칙의 적용을 막는 제약. -거로 실행기와 함께 결합해야 하며 단독 출력 변환은 없음.'
        elif rid.startswith('GS_GEORO_'):x['explanation']='목적·정도·결과·도급·사동 등을 구별할 절 관계와 의미 범위 판정기가 필요. 새 간결한 입력 계약에는 이 판정 필드가 없으므로 현재 실행기에 연결하지 않음.'
        elif rid=='GS_ENDRULE_YEO_SCOPE':x['explanation']='해여의 문헌별 화계 해석이 미확정. 이전 사용자 지시에 따라 확인되지 않은 해여형을 이번 실행에서 제외.'
        elif rid=='GS_ENDRULE_Q_INDEF':x['explanation']='누구/어디가 실제 의문사인지 부정칭인지 구별하는 선택 제약. 나/노 후보의 문맥 판단 지시에는 반영했으나 별도 변환 규칙으로 계산하지 않음.'
        elif rid.startswith('GS_ENDRULE_'):x['explanation']='아래 match·block·forms는 원래 설계값이다. 이 어미군의 표준어 대응/형태 결합 실행기와 긍정·부정 사례 검사는 아직 작성되지 않음. 모든 자료가 부족하다는 판정이 아니라 구체적인 구현 미완료다.'
        elif x['kind']=='realization_inventory':x['explanation']='형태 목록 또는 활용 칸. 특정 표준어 입력 위치와 기능을 연결하는 실행 코드가 없으며 목록의 모든 형태를 자유 치환 후보로 사용하지 않음.'
        elif x['kind']=='classification':x['explanation']='분류·개념 관계용 자료. 그 자체로 바꿀 문자열을 지정하지 않음.'
        else:x['explanation']='문헌 관찰 또는 예시이며 입력 기능→대상 구간→출력 구성의 대응 코드가 없음. 관찰의 누락이 아니라 실행 명세 미구축으로 기록함.'
    result={'modules':modules,'ledger':ledger,'node_types':dict(collections.Counter(n['type'] for n in nodes)),
      'all_runtime_active':dict(collections.Counter(str(n['properties'].get('runtime_active')) for n in nodes)),
      'old_claim_ids':[n['id'] for n in nodes if n['type']=='Claim'],'node_count':len(nodes),'edge_count':len(edges),
      'statistics':read(PROJECT/'knowledge/authored/kg_runtime_20261024/statistics.json')}
    save(OUT/'coverage_audit.json',result);return result

def summarize(folder):
    rows=read(folder/'private/results.json');m=read(folder/'metrics.json');details=[];stages=collections.defaultdict(list)
    for r in rows:
        f=folder/'private/records'/r['id'];raw=load(f/'retrieval_raw.json',{});packet=load(f/'reference_packet.json',{})
        for k,v in r['stage_seconds'].items():stages[k].append(v)
        mapping=load(f/'mapping.json',{})
        extra=load(f/'additional_retrieval.json')
        view_raw=dict(raw) if 'candidates' in raw else {'claim_path_count':len(raw.get('claim_paths',[])),
          'neighbor_count':len(raw.get('unreviewed_neighborhood',[])),'queries':raw.get('queries',[]),'full_artifact':str((f/'retrieval_raw.json').relative_to(PROJECT))}
        if extra:
            view_raw['additional_lookup']=extra
            view_raw['candidates']=list({c['candidate_id']:c for c in raw.get('candidates',[])+extra.get('candidates',[])}.values())
        view_packet={k:v for k,v in packet.items() if k!='available_concepts'}
        details.append({**r,'morphology':load(f/'morphology.json'),'mapping':{'selected_concept_ids':mapping.get('selected_concept_ids')},'retrieval':view_raw,
           'packet':view_packet,'agent':load(f/'agent_followup_call/parsed.json',load(f/'agent_call/parsed.json')),
           'initial_agent':load(f/'agent_call/parsed.json'),'plan':load(f/'transformation_plan.json'),
           'additional_candidate_gain':len({c['candidate_id'] for c in extra.get('candidates',[]) }-{c['candidate_id'] for c in raw.get('candidates',[])}) if extra else None,
           'final_plan':load(f/'final_plan.json'),'generation':load(f/'generation_call/parsed.json'),
           'packet_utf8_bytes':len(json.dumps(packet,ensure_ascii=False,separators=(',',':')).encode()) if packet else 0,
           'retrieval_utf8_bytes':len(json.dumps(raw,ensure_ascii=False,separators=(',',':')).encode()) if raw else 0})
    return {'run_id':folder.name,'config':read(folder/'config.json'),'metrics':m,'records':details,
       'stage_latency':{k:{'n':len(v),'mean':statistics.mean(v),'median':statistics.median(v),'sum':sum(v)} for k,v in stages.items()},
       'error_categories':dict(collections.Counter(r.get('error','').split(':')[0] for r in rows if r['status'].endswith('_failed'))),
       'versions':{'code':read(folder/'code_hashes.json'),'kg':read(folder/'kg_hashes.json'),'postflight':read(folder/'postflight.json')},
       'candidate_records':sum(bool(x['retrieval'].get('candidates')) for x in details),
       'packet_utf8_bytes_total':sum(x['packet_utf8_bytes'] for x in details),'retrieval_utf8_bytes_total':sum(x['retrieval_utf8_bytes'] for x in details)}

def main():
    p=argparse.ArgumentParser();p.add_argument('--batch');a=p.parse_args();old=old_audit();cov=coverage()
    if not a.batch:
        print('Audit saved: '+str(OUT));return
    bp=PROJECT/'experiments/batches'/a.batch;protocol=read(bp/'protocol.json')
    runs={k:summarize(PROJECT/'experiments/runs'/rid) for k,rid in protocol['runs'].items()}
    registry=Registry(PROJECT);registry.sync();verification=[registry.verify(OLD)]+[registry.verify(x['run_id']) for x in runs.values()]
    data={'previous':{'run_id':OLD,'metrics':read(PROJECT/'experiments/runs'/OLD/'metrics.json'),'config':read(PROJECT/'experiments/runs'/OLD/'config.json'),'audit':old},
          'coverage':cov,'runs':runs,'batch':protocol,'resources':read(bp/'resources.json'),'verification':verification,
          'comparison':registry.compare(runs['single']['run_id'],runs['multi']['run_id']),
          'quality':{'naturalness':None,'semantic_accuracy':None,'retrieval_accuracy':None,'reason':'No human ratings or gold labels'},
          'method_limits':['Historical baseline was run earlier; server revision/load unknown.',
            'Kiwi diagnostic changes the supplied token context and alignment instruction, not only a binary analyzer flag.',
            'Single/multi share candidates but planning/output roles differ; per-record latency includes live remote load.',
            '50 inputs are regression data. Original strings unchanged; not an independent held-out test.',
            'No KG-free or text-only retrieval control; cannot estimate the causal contribution of graph edges.']}
    save(OUT/'comparison.json',data)
    import random
    rng=random.Random(20261024);blind=[];key=[]
    for first in runs['single']['records']:
        second=next(r for r in runs['multi']['records'] if r['id']==first['id'])
        choices=[('single',first['output_text']),('multi',second['output_text'])];rng.shuffle(choices)
        blind.append({'id':first['id'],'input':first['input_text'],
           'choices':[{'label':chr(65+i),'output':v,'naturalness_1_to_5':None,'meaning_preserved':None,'unnecessary_change':None,'comment':''} for i,(_,v) in enumerate(choices)],
           'reviewer':None,'note':'Null output means execution failed, not a zero naturalness rating.'})
        key.append({'id':first['id'],'conditions':{chr(65+i):k for i,(k,_) in enumerate(choices)}})
    save(OUT/'blind_review.json',blind);save(OUT/'blind_review_key.json',key)
    print(json.dumps({k:{'run':v['run_id'],'statuses':v['metrics']['status_counts'],'calls':v['metrics']['api_attempts']} for k,v in runs.items()},ensure_ascii=False))

if __name__=='__main__':main()
