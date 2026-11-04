"""Read-only audit of stored experiments. No Qwen calls or production writes."""
import json, hashlib, sys
from pathlib import Path
from collections import Counter
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'src'))
from research_management.work import WorkStore
P=HERE/'private'; P.mkdir(parents=True,exist_ok=True)
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x): p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
source=ROOT/read(ROOT/'experiments/analyses/selection_probe_20261102/private/latest.json')['root']
cases=read(source/'prepared.json'); results=read(source/'results.json')
refs=read(ROOT/'experiments/analyses/effect_ledger_20261031/private/preparations/20261031T031655556269Z/cases.json')
refs={x['id']:x['approved_reference'] for x in refs}
assert len(cases)==50 and len(results)==300
assert len({(r['id'],r['arm'],r['repeat']) for r in results})==300
ws=WorkStore(ROOT)
ws.task(dict(id='pre-experiment-review-20261102',title='실험 전 원인·설계 검토',actor='Codex 총괄',stage='50건 기록 대조',status='running',done=0,total=50,unit='문장',unit_key='stored_audit',message='새 모델 실험 없이 저장된 300기록과 승인 참조를 연결합니다.'))
rows=[]
for i,c in enumerate(cases,1):
    rr=[r for r in results if r['id']==c['id']]
    assert len(rr)==6
    calls=sum(r['worker_calls'] for r in rr)
    row={'id':c['id'],'input':c['input'],'approved_reference':refs[c['id']],
         'prior_review_status':c['disposition'],'prior_review_scope':c['scope_note'],
         'same_selection':c['same_selection'],'reviewed_targets':c['reviewed_targets'],
         'missing_targets':c['missing_targets'],'delivered_card_ids':[a['id'] for a in c['common']['cards']],
         'selection':{a:c['arms'][a].get('decision',{}) for a in ('saved','reviewed')},
         'records':rr,'source':str(source.relative_to(ROOT))}
    save(P/'cases'/f"{c['id']}.json",row)
    flags={'no_reviewed_selection':not bool(c['reviewed_targets']),
           'model_abstained':any(e.get('raw_action')=='needs_review' for r in rr for e in r.get('edit_trace',[])),
           'program_blocked_apply':any(e.get('raw_action')=='apply' and e.get('outcome') not in ('applied','unchanged') for r in rr for e in r.get('edit_trace',[])),
           'program_repaired':any(e.get('repairs') for r in rr for e in r.get('edit_trace',[])),
           'call_failed':any(r['status']=='generation_failed' for r in rr)}
    rows.append({'id':c['id'],'input':c['input'],'reference':refs[c['id']],'calls':calls,
                 'review_status':c['disposition'],'same_selection':c['same_selection'],**flags,
                 'outputs':[{k:r.get(k) for k in ('arm','repeat','status','output_text','error')} for r in rr],
                 'case_file':f"cases/{c['id']}.json"})
    ws.task(dict(id='pre-experiment-review-20261102',title='실험 전 원인·설계 검토',actor='Codex 총괄',stage='50건 기록 대조',status='running',done=i,total=50,unit='문장',unit_key='stored_audit',message=f"{c['id']}: 6개 처리 기록 연결 완료. 품질 판정 완료를 뜻하지 않습니다."))
save(P/'index.json',rows)
stats={'inputs':len(rows),'records':len(results),'calls':sum(x['calls'] for x in rows),
       'case_flag_counts':{k:sum(bool(x[k]) for x in rows) for k in flags},
       'review_status_counts':dict(Counter(x['review_status'] for x in rows)),
       'status_counts':dict(Counter(r['status'] for r in results)),
       'note':'Flags overlap. They describe recorded processing, not established linguistic causes or accuracy.'}
save(P/'counts.json',stats)
files=[source/'prepared.json',source/'results.json',source/'summary.json',ROOT/'experiments/analyses/selection_probe_20261102/runner.py',ROOT/'experiments/analyses/selection_probe_20261102/review.py']
save(P/'source_hashes.json',{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
ws.task(dict(id='pre-experiment-review-20261102',title='실험 전 원인·설계 검토',actor='Codex 총괄',stage='독립 검토 및 원인 대조',status='running',message='50건 300기록 연결 완료. 두 검토자의 실제 근거·수정안과 이전 실험 중복 여부를 검토합니다.'))
print(json.dumps(stats,ensure_ascii=False))
