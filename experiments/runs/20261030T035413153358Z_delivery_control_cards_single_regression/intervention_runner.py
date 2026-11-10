"""Frozen-analysis, fixed-budget card-delivery intervention. No KG edits."""
import argparse, concurrent.futures as cf, copy, datetime as dt, json, shutil, sys, threading, time
from pathlib import Path
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[2]
sys.path[:0]=[str(ROOT/'local/python'),str(ROOT/'src')]
from kg_pipeline.io import Qwen,read,save,sha,dumps,load_jsonl
from kg_pipeline.runner import metrics,register_run
from kg_runtime import card_pipeline as cp
from kg_runtime import card_experiment as ce
from kg_runtime.edit_contract import role
from research_management.work import WorkStore

OLD='20261030T020345468863Z'
FAMILIES={'neye','raye','aeye','promise_ye','kkaye','ji_q','ji_d','geodeunye'}
GOLD=ROOT/'data/derived_private/gyeongsang_reference50_20261030_v1'
INPUTS=ROOT/'data/derived_private/standard_inputs_50_20261029_v2/inputs.jsonl'

def replace_cards(packet,raw,by,promote,protect):
    """Replace lowest-ranked unprotected candidates in place; retain count/order otherwise."""
    chosen=copy.deepcopy(packet['cards']);old={c['id'] for c in chosen}
    promote=list(dict.fromkeys(promote))
    if any(i not in raw['retrieved_ids'] for i in promote):raise ValueError('promotion_not_retrieved')
    if any(i in old for i in promote):raise ValueError('promotion_already_delivered')
    ranks={x['id']:x for x in raw['ranking']}
    eligible=sorted((c for c in chosen if c['id'] not in protect and role(c)!='restriction'),
        key=lambda c:(ranks[c['id']]['score'],-next(j for j,x in enumerate(chosen) if x['id']==c['id'])))
    if len(eligible)<len(promote):raise ValueError('insufficient_replaceable_cards')
    swaps=[]
    for cid,removed in zip(promote,eligible):
        index=next(j for j,x in enumerate(chosen) if x['id']==removed['id'])
        chosen[index]=copy.deepcopy(by[cid])
        swaps.append({'position':index,'added':cid,'removed':removed['id'],'removed_score':ranks[removed['id']]['score']})
    assert len(chosen)==len(packet['cards']) and len({c['id'] for c in chosen})==len(chosen)
    return chosen,swaps

def prepare_plan():
    cards_path=ROOT/'knowledge/authored/kg_cards_20261028_v2/cards.json'
    by={c['id']:c for c in read(cards_path)['cards']}
    cases=read(ROOT/'experiments/analyses/claude_comparison_20261030/private/cases.json')
    rows=[]
    for case in cases:
        folder=ROOT/'experiments/batches'/OLD/'private/shared'/case['id']
        info=read(folder/'shared.json')
        protected={t['card_id'] for f in case['families'] for t in f['traces']}
        promote=list(dict.fromkeys(t['card_id'] for f in case['families'] if f['key'] in FAMILIES
            for t in f['traces'] if t['stage']=='filtered_out' and t['card_id']!='GS_PROFILE_HAEYE'))
        entry={'id':case['id'],'input':case['input'],'promoted':promote,'protected':sorted(protected),'swaps':[],
               'disposition':'cached_analysis_failed' if not info['ok'] else 'no_delivery_change',
               'shared_origin':str(folder.relative_to(ROOT)),
               'frozen_shared_hashes':{str(f.relative_to(folder)):sha(f.read_bytes()) for f in folder.rglob('*') if f.is_file()}}
        if promote:
            packet=read(folder/'reference_packet.json');raw=read(folder/'retrieval_raw.json')
            chosen,swaps=replace_cards(packet,raw,by,promote,protected)
            entry.update(disposition='paired_rerun',swaps=swaps,original_count=len(packet['cards']),changed_count=len(chosen),
                         original_ids=[c['id'] for c in packet['cards']],changed_ids=[c['id'] for c in chosen])
        rows.append(entry)
    plan={'version':'delivery_probe_v1','baseline_batch':OLD,'all_inputs':50,'eligible_inputs':sum(r['disposition']=='paired_rerun' for r in rows),
          'families':sorted(FAMILIES),'rows':rows,'cards_sha256':sha(cards_path.read_bytes()),
          'input_sha256':sha(INPUTS.read_bytes()),'gold_sha256':sha((GOLD/'references.jsonl').read_bytes()),
          'hypothesis':'Delivery of already-retrieved related cards may change selection and realization.',
          'interpretation':'Oracle-informed diagnostic intervention, not a deployable input-only retriever. Fixed count replacement changes both added and removed cards; token length is measured, not matched.',
          'unchanged':'frozen Kiwi/Qwen analysis, graph retrieval, card contents, prompts, validators, model settings',
          'evaluation':'whole-sentence exact reference match is descriptive only; selection/application/output differences are not naturalness accuracy'}
    dest=BASE/'private/plan.json'
    if dest.exists():assert read(dest)==plan,'plan_changed_after_freeze'
    else:save(dest,plan)
    return plan

class Progress:
    def __init__(self,batch,total):
        self.store=WorkStore(ROOT);self.lock=threading.RLock();self.stop=threading.Event()
        self.data={'id':batch+'-delivery','title':'카드 전달만 바꾼 기존/변경 비교','actor':'Qwen 실행기','stage':'생성 비교',
            'status':'running','done':0,'total':total,'unit':'문장·방식 조합','unit_key':batch,'message':'분석을 재사용하고 생성만 비교합니다.'}
    def publish(self):self.store.task(self.data)
    def __enter__(self):
        self.publish();self.thread=threading.Thread(target=self.heartbeat,daemon=True);self.thread.start();return self
    def heartbeat(self):
        while not self.stop.wait(20):
            with self.lock:self.publish()
    def done(self,label):
        with self.lock:
            self.data['done']+=1;self.data['message']=label;self.publish()
    def __exit__(self,typ,exc,tb):
        self.stop.set();self.thread.join(2)
        self.data['status']='failed' if typ else 'completed';self.publish()

def check_frozen(plan):
    assert sha(INPUTS.read_bytes())==plan['input_sha256']
    assert sha((GOLD/'references.jsonl').read_bytes())==plan['gold_sha256']
    assert sha((ROOT/'knowledge/authored/kg_cards_20261028_v2/cards.json').read_bytes())==plan['cards_sha256']
    old=ROOT/'experiments/runs'/f'{OLD}_cards_single_regression'
    for rel,h in read(old/'code_hashes.json').items():
        if rel.startswith(('kg_runtime/','kg_pipeline/')):assert sha((ROOT/'src'/rel).read_bytes())==h,rel
    for row in plan['rows']:
        for rel,h in row['frozen_shared_hashes'].items():assert sha((ROOT/row['shared_origin']/rel).read_bytes())==h

def execute():
    plan=prepare_plan();check_frozen(plan)
    client=Qwen(ROOT/'test.py')
    oldconfig=read(ROOT/'experiments/runs'/f'{OLD}_cards_single_regression/config.json')
    assert client.model==oldconfig['model_id'],'served_model_changed'
    by={c['id']:c for c in read(ROOT/'knowledge/authored/kg_cards_20261028_v2/cards.json')['cards']}
    batch=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'_delivery'
    root=ROOT/'experiments/batches'/batch;root.mkdir(parents=True)
    selected=[r for r in plan['rows'] if r['disposition']=='paired_rerun']
    inputs=root/'private/inputs.jsonl';inputs.parent.mkdir(parents=True)
    inputs.write_text(''.join(json.dumps({'id':r['id'],'text':r['input']},ensure_ascii=False)+'\n' for r in selected),encoding='utf-8')
    save(root/'protocol.json',dict(plan,batch_id=batch,started_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        order='rotating four paired conditions per input; 2 concurrent workers; no automatic retries',
        plan_sha256=sha((BASE/'private/plan.json').read_bytes()),script_sha256=sha(Path(__file__).read_bytes())))
    outs={}
    for variant in ['control','promoted']:
        for arm in ['single','multi']:
            out=ce.prepare(ROOT,inputs,arm,client,batch+'_'+variant,'regression');outs[(variant,arm)]=out
            config=read(out/'config.json');config.update(intervention=variant,source_batch=OLD,
                experiment_family='card_delivery_probe_v1',analysis_policy='frozen_cached_analysis_no_new_calls',
                evaluation_protocol='user_approved_reference50_oracle_delivery_probe_v1',
                metric_contract='cached_analysis_generation_only_v1',test_exposure='user-approved regression references used to choose cards; not held-out',
                reference_sha256=plan['gold_sha256'],cost_policy='only physical generation calls; cached analysis excluded')
            save(out/'config.json',config);shutil.copy2(BASE/'run.py',out/'intervention_runner.py');shutil.copy2(BASE/'private/plan.json',out/'private/intervention_plan.json')
            save(out/'freeze.json',{'time':dt.datetime.now(dt.timezone.utc).isoformat(),'config_sha256':sha((out/'config.json').read_bytes()),'code_hashes_sha256':sha((out/'code_hashes.json').read_bytes()),'runner_sha256':sha((out/'intervention_runner.py').read_bytes())})
            register_run(ROOT,out)
    for row in selected:
        for variant in ['control','promoted']:
            folder=root/'private/shared'/variant/row['id'];shutil.copytree(ROOT/row['shared_origin'],folder)
            if variant=='promoted':
                packet=read(folder/'reference_packet.json');raw=read(folder/'retrieval_raw.json')
                chosen,swaps=replace_cards(packet,raw,by,row['promoted'],set(row['protected']));assert swaps==row['swaps']
                packet['cards']=chosen
                packet['contract_context']=cp.context(read(folder/'morphology.json'),chosen,packet['grammar'],row['id'])
                save(folder/'reference_packet.json',packet)
            save(folder/'delivery_audit.json',{'variant':variant,'swaps':row['swaps'] if variant=='promoted' else [],
                'original_retrieval_unchanged':True,'reference_packet_is_actual_delivery':True,
                'historical_retrieval_cards_are_pre_intervention':True})
    save(BASE/'private/active_run.json',{'batch':batch,'root':str(root),'runs':{v+'_'+a:o.name for (v,a),o in outs.items()}})
    print('BATCH '+batch+' | inputs '+str(len(selected))+' | four conditions',flush=True)
    results={k:[] for k in outs};started=time.perf_counter()
    def job(row,variant,arm):
        record={'id':row['id'],'text':row['input']}
        result=ce.generate(record,arm,client,root/'private/shared'/variant/row['id'],outs[(variant,arm)])
        result['reused_analysis_seconds']=result['shared_analysis_seconds']
        result['shared_analysis_seconds']=0;result['total_seconds']=result['incremental_generation_seconds']
        result['stage_seconds']={k:v for k,v in result['stage_seconds'].items() if k not in ('analysis','retrieval')}
        result['calls']=[c for c in result['calls'] if c['stage']!='analysis']
        result.update(intervention=variant,analysis_reused=True)
        save(outs[(variant,arm)]/'private/records'/row['id']/'result.json',result)
        return variant,arm,result
    with Progress(batch,len(selected)*4) as progress,cf.ThreadPoolExecutor(max_workers=2) as pool:
        tasks=[];conditions=[('control','single'),('promoted','single'),('control','multi'),('promoted','multi')]
        for i,row in enumerate(selected):
            order=conditions[i%4:]+conditions[:i%4]
            for v,a in order:tasks.append(pool.submit(job,row,v,a))
        for f in cf.as_completed(tasks):
            v,a,result=f.result();results[(v,a)].append(result)
            label=f"{result['id']} · {v}/{a} · {result['status']}"
            print(label,flush=True);progress.done(label)
    wall=time.perf_counter()-started;check_frozen(plan)
    order={x['id']:i for i,x in enumerate(selected)}
    allcalls=[]
    for (v,a),out in outs.items():
        rows=sorted(results[(v,a)],key=lambda x:order[x['id']]);save(out/'private/results.json',rows)
        m=metrics(rows,wall);m.update(wall_seconds=None,shared_batch_wall_seconds=wall,accuracy=None,naturalness=None,
            cost_note='Cached analysis cost excluded; shared server timing, not standalone throughput.')
        save(out/'metrics.json',m)
        save(out/'postflight.json',{'input_unchanged':sha(inputs.read_bytes())==read(out/'config.json')['input_sha256'],
            'code_unchanged':all(sha((ROOT/'src'/rel).read_bytes())==h for rel,h in read(out/'code_hashes.json').items()),
            'kg_unchanged':all(sha((ROOT/rel).read_bytes())==h for rel,h in read(out/'kg_hashes.json').items()),
            'frozen_analysis_checked':True,'cards_count_preserved':True})
        save(out/'artifact_hashes.json',{str(f.relative_to(out)):sha(f.read_bytes()) for f in out.rglob('*') if f.is_file() and f.name!='artifact_hashes.json'})
        allcalls.extend(c for row in rows for c in row['calls']);register_run(ROOT,out)
    save(root/'resources.json',{'physical_api_attempts':len(allcalls),'physical_total_tokens':sum((c.get('usage') or {}).get('total_tokens',0) for c in allcalls),
        'wall_seconds':wall,'new_analysis_calls':0,'rerun_inputs':len(selected),'conditions':4})
    print('COMPLETE '+batch,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');a=p.parse_args()
    if a.execute:execute()
    else:
        x=prepare_plan();check_frozen(x);print('FROZEN '+str(x['eligible_inputs'])+' / '+str(x['all_inputs']))
