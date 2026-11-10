"""Prepare all 50 frozen inputs for both independent reviewers; no experiments."""
import json, hashlib, re, sys
from pathlib import Path
from datetime import datetime, timezone
sys.stdout.reconfigure(encoding='utf-8')
P=Path('G:/Work/00_projects/active/hyperscale_AI/02_research/KG')
BASE=P/'experiments/analyses/full_review_20261029'
OUT=BASE/'private';OUT.mkdir(parents=True,exist_ok=True)
PACK=OUT/'packets';PACK.mkdir(exist_ok=True)
BATCH='20261028T011829489985Z'
hashes={}
def read(f):
    hashes[f.relative_to(P).as_posix()]=hashlib.sha256(f.read_bytes()).hexdigest()
    return json.loads(f.read_text(encoding='utf-8'))
def optional(f,default=None):return read(f) if f.is_file() else default
def save(f,obj):f.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
rows={a:read(P/f'experiments/runs/{BATCH}_cards_{a}_regression/private/results.json') for a in ['single','multi']}
assert all(len(v)==50 for v in rows.values())
by={a:{r['id']:r for r in rs} for a,rs in rows.items()}
assert set(by['single'])==set(by['multi'])
allcards={c['id']:c for c in read(P/'knowledge/authored/kg_cards_20261028_v2/cards.json')['cards']}
cases=[]
for ident,raw in by['single'].items():
    assert raw['input_text']==by['multi'][ident]['input_text']
    ds={a:P/f'experiments/runs/{BATCH}_cards_{a}_regression/private/records/{ident}' for a in by}
    packets={a:read(d/'reference_packet.json') for a,d in ds.items()}
    assert packets['single']==packets['multi']
    pp=packets['single'];referenced=set();arms={}
    for arm,d in ds.items():
        r=by[arm][ident];draft=optional(d/'agent_call/parsed.json');final=optional(d/'final_plan.json')
        worker=optional(d/'generation_call/parsed.json') if arm=='multi' else None
        for value in [draft,final,worker]:
            referenced.update(re.findall(r'GS_[A-Z0-9_]+',json.dumps(value,ensure_ascii=False)))
        calls=[]
        for mp in sorted(d.glob('*_call/meta.json')):
            meta=read(mp)
            entry={'stage':mp.parent.name,'finish_reason':meta.get('finish_reason'),'http_status':meta.get('http_status')}
            if meta.get('finish_reason')=='length':
                resp=read(mp.with_name('response.json'));text=resp['choices'][0]['message'].get('content') or ''
                entry.update(content_chars=len(text),trailing_whitespace=len(text)-len(text.rstrip()),
                             raw_start_excerpt=text[:800],raw_end_nonwhitespace_excerpt=text.rstrip()[-800:],
                             excerpt_only=True)
            calls.append(entry)
        retrieval=read(d/'retrieval_raw.json')
        selected={k for e in (final or draft or {}).get('edits',[]) for k in e.get('rule_ids',[])}
        paths={k:[x for x in retrieval['paths'] if x['rule_id']==k] for k in selected}
        arms[arm]={'output':r['output_text'],'status':r['status'],'error':r.get('error'),
                   'draft':draft,'worker_response':worker,'final_plan':final,'call_facts':calls,
                   'selected_path_examples':{k:v[:2] for k,v in paths.items()},
                   'selected_path_total_counts':{k:len(v) for k,v in paths.items()},
                   'source_record_dir':d.relative_to(P).as_posix()}
    cases.append({'id':ident,'input':raw['input_text'],'words':pp['words'],'shared_analysis':pp['grammar'],
                  'supplied_card_ids':[c['id'] for c in pp['cards']],
                  'referenced_card_ids':sorted(referenced),'arms':arms})
frozen=P/f'experiments/runs/{BATCH}_cards_single_regression/code_snapshot/kg_runtime/card_pipeline.py'
code=frozen.read_text(encoding='utf-8');hashes[frozen.relative_to(P).as_posix()]=hashlib.sha256(frozen.read_bytes()).hexdigest()
manifest=[]
for start in range(0,50,10):
    part=cases[start:start+10];n=start//10+1;bid=f'B{n:02}'
    supplied={k for c in part for k in c['supplied_card_ids']};refs={k for c in part for k in c['referenced_card_ids']}
    obj={'batch_id':bid,'source_experiment_batch':BATCH,'dataset_version':'standard_inputs_50_20261023_v1',
         'scope':'10 inputs, both Single and Multi historical executions. No new generation. Both reviewers inspect every input.',
         'evidence_limits':['KG paths are evidence linkage examples, not chronological traversal logs.',
                            'Full conditions are provided for cards cited in drafts/plans. For other supplied candidates, id/title/forms only; request specific conditions before judging retrieval completeness.',
                            'Failed truncated response excerpts are not complete responses. Never treat null outputs as successful translations.',
                            'No human scores, preferred outputs, or lead screening notes are included in this first independent pass.',
                            'One later revised input exists, but all records here use the actual historical v1 source.'],
         'cards_referenced_full':{k:allcards[k] for k in sorted(refs) if k in allcards},
         'unknown_referenced_ids':sorted(refs-set(allcards)),
         'other_supplied_card_index':[{k:allcards[i][k] for k in ['id','title','forms']} for i in sorted(supplied-refs)],
         'frozen_pipeline_source':code,'cases':part}
    f=PACK/f'{bid}.json';save(f,obj)
    manifest.append({'batch_id':bid,'ids':[c['id'] for c in part],'file':f.relative_to(P).as_posix(),
                     'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'characters':len(f.read_text(encoding='utf-8'))})
assert len({c['id'] for c in cases})==50
assert all(hashlib.sha256((P/f).read_bytes()).hexdigest()==h for f,h in hashes.items())
save(OUT/'manifest.json',{'created_utc':datetime.now(timezone.utc).isoformat(),'inputs':50,'executions':100,
     'batches':manifest,'source_sha256':hashes,'source_files_unchanged':True,'reviewer_outputs_are_ai_not_human':True})
save(OUT/'progress.json',{'prepared_inputs':50,'codex_reviewed_inputs':0,'claude_reviewed_inputs':0,'lead_crosschecked_inputs':0,
     'experiments_run':0,'kg_or_runtime_modified':False})
print(json.dumps({'prepared':50,'executions':100,'packets':manifest,'source_files_checked':len(hashes)},ensure_ascii=False,indent=2))
