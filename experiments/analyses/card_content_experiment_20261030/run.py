"""Paired v2/v3 content experiment; frozen latest delivered IDs, no new analysis."""
import argparse, concurrent.futures as cf, copy, datetime as dt, json, shutil, sys, threading, time
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2]
sys.path[:0]=[str(ROOT/'local/python'),str(ROOT/'src')]
from kg_pipeline.io import Qwen,read,save,sha,dumps,load_jsonl
from kg_pipeline.runner import metrics,register_run
from kg_runtime import card_pipeline as cp,card_experiment as ce
from kg_runtime.card_content import CardContent
from kg_runtime.cards import VERSION
from research_management.work import WorkStore

OLD='20261030T020345468863Z';NEW='kg_cards_20261030_v3'
INPUTS=ROOT/'data/derived_private/standard_inputs_50_20261029_v2/inputs.jsonl'
CONDITIONS=[('v2','single'),('v3','single'),('v2','multi'),('v3','multi')]

def projected_packet(packet,morph,record_id,content):
    result=copy.deepcopy(packet)
    result['cards'],audit=content.project_cards(packet['cards'])
    result['contract_context']=cp.context(morph,result['cards'],result['grammar'],record_id)
    assert [c['id'] for c in result['cards']]==[c['id'] for c in packet['cards']]
    assert {k:v for k,v in result.items() if k not in ('cards','contract_context')}=={k:v for k,v in packet.items() if k not in ('cards','contract_context')}
    assert result['contract_context']['user_restrictions']==packet['contract_context']['user_restrictions']
    return result,audit

def freeze_plan():
    content=CardContent(ROOT,NEW);records=load_jsonl(INPUTS)
    assert len(records)==50 and len({r['id'] for r in records})==50
    delivery=read(ROOT/'experiments/analyses/card_delivery_20261030/private/active_run.json')
    promoted=ROOT/'experiments/batches'/delivery['batch']/'private/shared/promoted'
    rows=[]
    for record in records:
        source=promoted/record['id']
        origin='previous_promoted_delivery' if source.exists() else 'original_delivery'
        if not source.exists():source=ROOT/'experiments/batches'/OLD/'private/shared'/record['id']
        assert read(source/'input.json')['text']==record['text']
        info=read(source/'shared.json');row={'id':record['id'],'origin':origin,'source':str(source.relative_to(ROOT)),
            'analysis_ok':info['ok'],'hashes':{str(p.relative_to(source)):sha(p.read_bytes()) for p in source.rglob('*') if p.is_file()}}
        if info['ok']:
            packet=read(source/'reference_packet.json');morph=read(source/'morphology.json')
            assert packet['input']==record['text']
            assert packet['contract_context']==cp.context(morph,packet['cards'],packet['grammar'],record['id'])
            revised,audit=projected_packet(packet,morph,record['id'],content)
            row.update(selected_ids=audit['selected_ids'],card_count=len(packet['cards']),
                revised_directional_ids=[c['id'] for c in revised['cards'] if 'rewrite' in c])
        rows.append(row)
    # Generation logic, prompts and validators must match the preceding experiment.
    oldhash=read(ROOT/'experiments/runs'/f'{OLD}_cards_single_regression/code_hashes.json')
    unchanged=['kg_runtime/card_pipeline.py','kg_runtime/edit_contract.py','kg_pipeline/io.py']
    for rel in unchanged:assert sha((ROOT/'src'/rel).read_bytes())==oldhash[rel],rel
    plan={'version':'card_content_pair_v1','baseline_batch':OLD,'delivery_batch':delivery['batch'],
        'generation_versions':{'v2':VERSION,'v3':NEW},'input_sha256':sha(INPUTS.read_bytes()),'rows':rows,
        'input_count':50,'analysis_successes':sum(r['analysis_ok'] for r in rows),
        'conditions':[v+'_'+a for v,a in CONDITIONS],'new_analysis_calls':0,'new_retrieval_queries':0,
        'reference_policy':'Approved references informed prior delivery and card authoring; not included in generation requests; regression, not unseen test.',
        'intervention':'Only delivered card content and its dependent request identifier differ between v2/v3.',
        'fixed':'Input, Kiwi, grammar analysis, retrieved graph, selected card IDs/order/forms, prompts, validators, seed, temperature.',
        'limitations':'One paired run; remote nondeterminism and load remain. Old analysis failure retained. No naturalness accuracy without human review.',
        'files':{str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in [INPUTS,ROOT/'knowledge/authored'/VERSION/'cards.json',
            ROOT/'knowledge/authored'/NEW/'cards.json',ROOT/'knowledge/authored'/NEW/'provenance.json',ROOT/'knowledge/authored'/NEW/'manifest.json']}}
    dest=BASE/'private/plan.json'
    if dest.exists():assert read(dest)==plan,'frozen_plan_changed'
    else:save(dest,plan)
    return plan

def check_plan(plan):
    for rel,h in plan['files'].items():assert sha((ROOT/rel).read_bytes())==h,rel
    for row in plan['rows']:
        for rel,h in row['hashes'].items():assert sha((ROOT/row['source']/rel).read_bytes())==h,rel

class Progress:
    def __init__(self,batch,total):
        self.store=WorkStore(ROOT);self.lock=threading.RLock();self.stop=threading.Event()
        self.data={'id':batch+'-content','title':'이전·새 카드 내용 비교 · 50문장 Single/Multi','actor':'Qwen 실행기',
            'stage':'카드 내용만 바꾼 생성 비교','status':'running','done':0,'total':total,'unit':'문장·조건 조합','unit_key':batch,
            'message':'49개 분석 재사용, 기존 분석 실패 1개 포함. 50 × 4조건.'}
    def publish(self):self.store.task(self.data)
    def __enter__(self):
        self.publish();self.thread=threading.Thread(target=self.heartbeat,daemon=True);self.thread.start();return self
    def heartbeat(self):
        while not self.stop.wait(20):
            with self.lock:self.publish()
    def done(self,label):
        with self.lock:self.data['done']+=1;self.data['message']=label;self.publish()
    def __exit__(self,typ,exc,tb):
        self.stop.set();self.thread.join(2);self.data['status']='failed' if typ else 'completed';self.publish()

def execute():
    plan=freeze_plan();check_plan(plan);content=CardContent(ROOT,NEW)
    client=Qwen(ROOT/'test.py')
    assert client.model==read(ROOT/'experiments/runs'/f'{OLD}_cards_single_regression/config.json')['model_id'],'served_model_changed'
    batch=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'_content'
    root=ROOT/'experiments/batches'/batch;root.mkdir(parents=True,exist_ok=False)
    inputs=root/'private/inputs.jsonl';inputs.parent.mkdir();shutil.copy2(INPUTS,inputs)
    save(root/'protocol.json',dict(plan,batch_id=batch,runner_sha256=sha(Path(__file__).read_bytes()),
        order='4-condition rotating order per input, workers2, no retries',started_at=dt.datetime.now(dt.timezone.utc).isoformat()))
    outs={}
    for variant,arm in CONDITIONS:
        out=ce.prepare(ROOT,inputs,arm,client,batch+'_'+variant,'regression',NEW if variant=='v3' else VERSION);outs[(variant,arm)]=out
        config=read(out/'config.json');config.update(intervention=variant,source_batch=OLD,
            experiment_family='card_content_pair_v1',analysis_policy='frozen_cached_analysis_no_new_calls',
            evaluation_protocol='fixed_delivery_card_content_pair_v1',metric_contract='cached_analysis_generation_only_v1',
            test_exposure=plan['reference_policy'],cost_policy='Physical generation calls only; cached analysis excluded',
            new_retrieval_queries=0,source_delivery_batch=plan['delivery_batch'])
        save(out/'config.json',config);shutil.copy2(__file__,out/'intervention_runner.py');save(out/'private/intervention_plan.json',plan)
        save(out/'freeze.json',{'time':dt.datetime.now(dt.timezone.utc).isoformat(),'config_sha256':sha((out/'config.json').read_bytes()),
            'code_hashes_sha256':sha((out/'code_hashes.json').read_bytes()),'runner_sha256':sha((out/'intervention_runner.py').read_bytes())})
        register_run(ROOT,out)
    for row in plan['rows']:
        for variant in ('v2','v3'):
            folder=root/'private/shared'/variant/row['id'];shutil.copytree(ROOT/row['source'],folder)
            if variant=='v3' and row['analysis_ok']:
                packet,audit=projected_packet(read(folder/'reference_packet.json'),read(folder/'morphology.json'),row['id'],content)
                save(folder/'reference_packet.json',packet);save(folder/'generation_projection.json',audit)
            save(folder/'reuse.json',{'source':row['source'],'analysis_reused':True,'variant':variant,'old_analysis_call_is_not_new':True})
    active={'batch':batch,'root':str(root),'runs':{v+'_'+a:o.name for (v,a),o in outs.items()}}
    save(BASE/'private/active_run.json',active);print('BATCH '+batch+' | 50 inputs x 4 conditions | 49 valid cached analyses',flush=True)
    records=load_jsonl(inputs);results={k:[] for k in outs};started=time.perf_counter()
    def job(record,v,a):
        result=ce.generate(record,a,client,root/'private/shared'/v/record['id'],outs[(v,a)])
        result['reused_analysis_seconds']=result['shared_analysis_seconds'];result['shared_analysis_seconds']=0
        result['total_seconds']=result['incremental_generation_seconds']
        result['stage_seconds']={k:x for k,x in result['stage_seconds'].items() if k not in ('analysis','retrieval')}
        result['calls']=[c for c in result['calls'] if c['stage']!='analysis']
        result.update(intervention=v,analysis_reused=True,kg_queries=0)
        save(outs[(v,a)]/'private/records'/record['id']/'result.json',result)
        return v,a,result
    with Progress(batch,201) as progress:
        with cf.ThreadPoolExecutor(max_workers=2) as pool:
            tasks=[]
            for i,record in enumerate(records):
                for v,a in CONDITIONS[i%4:]+CONDITIONS[:i%4]:tasks.append(pool.submit(job,record,v,a))
            for future in cf.as_completed(tasks):
                v,a,result=future.result();results[(v,a)].append(result)
                label=f"{result['id']} · {v}/{a} · {result['status']}"
                print(label,flush=True);progress.done(label)
        wall=time.perf_counter()-started;check_plan(plan);order={r['id']:i for i,r in enumerate(records)};allcalls=[]
        for (v,a),out in outs.items():
            rows=sorted(results[(v,a)],key=lambda r:order[r['id']]);save(out/'private/results.json',rows)
            m=metrics(rows,wall);m.update(wall_seconds=None,shared_batch_wall_seconds=wall,accuracy=None,naturalness=None,
                evaluation_note='Approved references exist; no human rating of new outputs. Changed/unchanged/failure are execution counts.',
                cost_note='Cached analysis excluded; shared server timing is not standalone throughput.')
            save(out/'metrics.json',m)
            checks={'input_unchanged':sha(inputs.read_bytes())==read(out/'config.json')['input_sha256'],
                'code_unchanged':all(sha((ROOT/'src'/rel).read_bytes())==h for rel,h in read(out/'code_hashes.json').items()),
                'kg_unchanged':all(sha((ROOT/rel).read_bytes())==h for rel,h in read(out/'kg_hashes.json').items()),
                'frozen_analysis_checked':True,'same_card_ids_order':True}
            save(out/'postflight.json',checks);assert all(checks.values()),checks
            save(out/'artifact_hashes.json',{str(f.relative_to(out)):sha(f.read_bytes()) for f in out.rglob('*') if f.is_file() and f.name!='artifact_hashes.json'})
            allcalls.extend(c for r in rows for c in r['calls']);register_run(ROOT,out)
        save(root/'resources.json',{'physical_api_attempts':len(allcalls),'physical_total_tokens':sum((c.get('usage') or {}).get('total_tokens',0) for c in allcalls),
            'wall_seconds':wall,'new_analysis_calls':0,'new_retrieval_queries':0,'inputs':50,'conditions':4,'cached_analysis_failure':'QUAL002'})
        progress.done('200개 결과·실패·설정·해시 저장 완료')
    print('COMPLETE '+batch,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    if args.execute:execute()
    else:
        plan=freeze_plan();check_plan(plan);print(dumps({'inputs':50,'valid_analysis':plan['analysis_successes'],'promoted_packets':sum(r['origin']=='previous_promoted_delivery' for r in plan['rows']),'new_calls':0}))
