"""Paired forced-selection diagnosis. Never modifies production KG or reference data."""
import argparse,copy,datetime as dt,sys,time,threading,platform,subprocess,shutil
from pathlib import Path
from collections import Counter
from concurrent.futures import ThreadPoolExecutor,as_completed
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[2]
sys.path[:0]=[str(ROOT/'local/python'),str(ROOT/'src'),str(HERE)]
from kg_pipeline.io import read,save,sha,dumps,load_jsonl,Qwen
from kg_runtime import card_pipeline as cp
from kg_pipeline.runner import register_run
from research_management.work import WorkStore
from review import REVIEW
SOURCE=ROOT/'experiments/batches/20261030T085346443103Z/private/shared'
OLD=ROOT/'experiments/runs/20261030T085346443103Z_cards_multi_regression/private/records'
INPUT=ROOT/'data/derived_private/standard_inputs_50_20261029_v2/inputs.jsonl'
ARMS=('saved','reviewed')
PROMPT=cp.GENERATOR
NOTE='bindings의 원문 위치에 해당 카드 forms[form_index]의 형태를 조합한다. 카드의 rewrite 범위에 따라 바꾸고 나머지 어휘·시제·부정·높임·문장부호는 보존한다. 조합할 수 없으면 needs_review로 답한다.'
def hashobj(x): return sha(dumps(x).encode())
def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def source_files():
    files=[INPUT,HERE/'runner.py',HERE/'review.py',HERE/'test_probe.py']
    files+=list((ROOT/'src/kg_runtime').glob('*.py'))+list((ROOT/'src/kg_runtime').glob('*.json'))
    files+=list((ROOT/'src/kg_pipeline').glob('*.py'))
    for row in load_jsonl(INPUT):
        files += [SOURCE/row['id']/'reference_packet.json',SOURCE/row['id']/'morphology.json',OLD/row['id']/'agent_call/parsed.json']
    return {str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in files if p.exists()}
def normalized_decision(raw,ctx):
    result=copy.deepcopy(raw);result['request_id']=ctx['request_id'];result['reason']='동일 편집 지시 형식으로 선택 계획을 재구성함.'
    for e in result['edits']:
        e['after']='';e['instruction']=NOTE;e['reason']='선택 카드와 원문 위치를 고정한 조합 진단.'
    return result

def compile_case(row):
    key=row['id'];p=read(SOURCE/key/'reference_packet.json');m=read(SOURCE/key/'morphology.json')
    assert row['text']==m['text']==p['input'], ('source_mismatch',key)
    ctx=cp.context(m,p['cards'],p['grammar'],key)
    common={k:copy.deepcopy(p[k]) for k in ('input','words','grammar','analysis_review','cards','candidate_guidance')}
    common['contract_context']=ctx
    targets,disposition,note=REVIEW[key]; by={w['uid']:w for w in m['words']};cards={c['id']:c for c in p['cards']}
    selected=[];missing=[];rows=[]
    for t in targets:
        word,mi,card,fi=t.split('/');mi=int(mi);fi=int(fi)
        if card not in cards:
            missing.append({'target':t,'reason':'not_in_delivered_cards'});continue
        assert 0<=mi<len(by[word]['morphs']) and 0<=fi<len(cards[card]['forms']),t
        tag=by[word]['morphs'][mi][1].split('-')[0]
        binding={'card_id':card,'form_index':fi,'source_word_id':word,'morph_index':mi,'component':'particle' if tag.startswith('J') else 'ending'}
        # Review targets are independent; preserve each separate source location.
        selected.append({'edit_id':'R'+str(len(selected)+1),'word_ids':[word],'bindings':[binding],'depends_on':[],'action':'apply','instruction':NOTE,'after':'','reason':''})
        rows.append({'word_id':word,'source':by[word]['surface'],'morph_index':mi,'morph':by[word]['morphs'][mi], 'card_id':card,'target_form':cards[card]['forms'][fi], 'card_title':cards[card]['title']})
    case={'id':key,'input':row['text'],'disposition':disposition,'scope_note':note,'reviewed_targets':rows,'missing_targets':missing,'common':common,'morphology':m,'arms':{}}
    for arm in ARMS:
        path=OLD/key/'agent_call/parsed.json'
        if arm=='saved' and not path.exists():case['arms'][arm]={'status':'saved_selection_unavailable'};continue
        if arm=='reviewed' and not selected:
            case['arms'][arm]={'status':'review_not_eligible','reason':disposition};continue
        raw=read(path) if arm=='saved' else {'request_id':ctx['request_id'],'edits':selected,'reason':''}
        decision=normalized_decision(raw,ctx)
        item={'decision':decision}
        try:
            plan=cp.bind_plan(decision,m,p['cards'],realize=False,analysis=p['grammar'],input_id=key)
            item['plan']=plan
            item['status']='ready' if any(e['outcome']=='planned' for e in plan['edits']) else 'preworker_blocked' if any(e['issues'] for e in plan['edits']) else 'no_planned_edit'
            # Retain only source/selection fields. No algorithmically composed answers.
            visible={'plan_id':plan['plan_id'],'edits':[{k:copy.deepcopy(e[k]) for k in ('edit_id','word_ids','bindings','depends_on','action','instruction','before','after')} for e in plan['edits']]}
            item['payload']={**copy.deepcopy(common),'plan':visible}
            item['payload_hash']=hashobj(item['payload'])
        except Exception as exc:item.update(status='plan_validation_failed',error=str(exc))
        case['arms'][arm]=item
    case['common_hash']=hashobj(common)
    # Ignore arbitrary edit names; retain grouping, decisions, bindings and dependencies.
    def shape(a):
        d=case['arms'][a].get('decision',{}).get('edits',[])
        ids={e['edit_id']:i for i,e in enumerate(d)}
        return [{'words':e['word_ids'],'bindings':e['bindings'],'action':e['action'],'depends':[ids.get(x,x) for x in e['depends_on']]} for e in d]
    case['same_selection']=shape('saved')==shape('reviewed') if selected else None
    return case

def prepare():
    rows=load_jsonl(INPUT);assert len(rows)==50 and {r['id'] for r in rows}==set(REVIEW)
    cases=[compile_case(r) for r in rows]
    save(HERE/'private/review.json',[{k:v for k,v in c.items() if k not in ('common','morphology','arms')} for c in cases])
    save(HERE/'private/prepared.json',cases)
    summary={'at':now(),'records':50,'reviewed_cases':sum(bool(c['reviewed_targets']) for c in cases),'missing_targets':[{'id':c['id'],**x} for c in cases for x in c['missing_targets']], 'arms':{a:dict(Counter(c['arms'][a]['status'] for c in cases)) for a in ARMS},'same_selection_cases':sum(c['same_selection'] is True for c in cases)}
    save(HERE/'private/preparation.json',summary)
    WorkStore(ROOT).task({'id':'selection-probe-20261102','title':'50문장 선택 비교 진단 실험','actor':'Codex 총괄','stage':'비교 선택표 검증','status':'running','done':50,'total':50,'unit':'문장','unit_key':'selection_review','message':'전체 위치 검토 완료. 전달되지 않은 목표는 별도 제외하고 같은 검사로 양쪽 계획을 확인했습니다.'})
    print(dumps(summary),flush=True);return cases

class Progress:
    def __init__(self,total):
        self.total=total;self.done=0;self.calls=0;self.lock=threading.Lock();self.stop=threading.Event()
        self.thread=threading.Thread(target=self.beat,daemon=True);self.publish();self.thread.start()
    def publish(self):
        WorkStore(ROOT).task({'id':'selection-probe-20261102','title':'50문장 선택 비교 진단 실험','actor':'Qwen 실행기','stage':'Qwen 선택 비교 실행','status':'running','done':self.done,'total':self.total,'unit':'처리 기록','unit_key':'paired_probe_records','message':f'50문장 × 두 선택 방식 × 3회. 완료 {self.done}/{self.total}; 실제 요청 완료 {self.calls}회. 제외·차단도 기록하며 성공으로 세지 않습니다.'})
    def beat(self):
        while not self.stop.wait(15):
            with self.lock:self.publish()
    def tick(self,result):
        with self.lock:self.done+=1;self.calls+=result['worker_calls'];self.publish()
    def close(self):self.stop.set();self.thread.join()

def execute(case,arm,repeat,folder,client,seed):
    key=case['id'];record=folder/'private/records'/key;record.mkdir(parents=True,exist_ok=False)
    item=case['arms'][arm];m=case['morphology'];common=case['common'];start=time.perf_counter()
    result={'id':key,'input_text':case['input'],'output_text':None,'fallback_original':case['input'],'status':item['status'],'arm':arm,'repeat':repeat,'worker_calls':0,'stage_seconds':{},'human_evaluation':None,'changed':False,'same_selection':case['same_selection'],'reviewed_target_count':len(case['reviewed_targets']),'issues':[],'target_outcomes':[]}
    save(record/'input.json',{'id':key,'text':case['input']});save(record/'morphology.json',m);save(record/'reference_packet.json',common)
    if item.get('decision'):save(record/'agent_call/parsed.json',item['decision'])
    if item.get('plan'):save(record/'transformation_plan.json',item['plan'])
    if item.get('error'):result['error']=item['error']
    try:
        if item['status']!='ready':
            for e in item.get('plan',{}).get('edits',[]):result['issues'] += e['issues']
            return result
        result['worker_calls']=1
        answer=client.call('generation',PROMPT,item['payload'],cp.request_schema(cp.WORKER,'plan_id',item['plan']['plan_id']),record/'generation_call',6000,seed)
        cp.validate_schema(answer,cp.WORKER)
        final=cp.realize_plan(item['plan'],answer,m,common['cards'],analysis=common['grammar'],input_id=key)
        save(record/'final_plan.json',final)
        result['output_text']=cp.assemble(case['input'],final)
        result['changed']=result['output_text']!=case['input']
        result['issues']=[i for e in final['edits'] for i in e['issues']]
        result['status']='partial' if result['changed'] and result['issues'] else 'generated_requires_human_review' if result['changed'] else 'needs_review' if result['issues'] else 'unchanged'
        result['applied_edits']=sum(e['outcome']=='applied' for e in final['edits'])
        # Keep raw worker words distinct from retained/repaired final words.
        raw={e['edit_id']:e for e in answer['edits']}
        result['edit_trace']=[{'edit_id':e['edit_id'],'words':e['word_ids'],'bindings':e['bindings'],'before':e['before'],'raw':raw[e['edit_id']]['after'],'raw_action':raw[e['edit_id']]['action'],'after':e['after'],'outcome':e['outcome'],'issues':e['issues'],'repairs':e.get('repairs',[])} for e in final['edits']]
        for target in case['reviewed_targets']:
            matches=[e for e in final['edits'] if target['word_id'] in e['word_ids']]
            result['target_outcomes'].append({'word_id':target['word_id'],'morph_index':target['morph_index'],'reviewed_card':target['card_id'],'edits':[e['edit_id'] for e in matches],'applied_any_at_word':any(e['outcome']=='applied' for e in matches),'limitation':'mechanical edit at word, not naturalness or correct target realization'})
    except Exception as exc:
        result.update(status='generation_failed',output_text=None,changed=False,error=str(exc)[:300],error_type=type(exc).__name__)
    finally:
        result['stage_seconds']['total']=round(time.perf_counter()-start,4)
        meta=record/'generation_call/meta.json'
        if meta.exists():result['generation_meta']=read(meta);result['stage_seconds']['generation']=read(meta)['seconds']
        save(record/'result.json',result)
    return result

def run(cases):
    stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    root=HERE/'private'/stamp;root.mkdir(parents=True,exist_ok=False)
    client=Qwen(ROOT/'test.py',timeout=180);print('MODEL '+client.model,flush=True)
    freeze=source_files();save(root/'freeze.json',freeze);save(root/'prepared.json',cases)
    for name in freeze:
        destination=root/'snapshot'/name;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/name,destination)
    save(root/'protocol.json',{'question':'selection plan vs same worker and same full cards','arms':list(ARMS),'repeats':3,'workers':2,'seed_by_repeat':[20261102+i for i in range(3)],'tuning':'none during frozen run','reference':'not sent; reviewed selection informed by exposed references','excluded':'unresolved reviewed targets are not successes; saved controls still executed if valid','partial':'compare target locations separately; no whole sentence naturalness claim','historical':'old outputs not causal control; rerun saved decisions with identical new compiler/full cards','intervention':'bindings, action, group, dependencies, omitted edits; not only one binding','instructions':'both arms regenerated by identical compiler','answer_leak':'no suffix projections or completed word targets in visible plans','cost':'worker-only; source analysis and planner costs excluded','runtime':'current frozen production checks and repairs preserved, no production changes'})
    folders={};configs={};results={}
    for repeat in range(3):
        for arm in ARMS:
            rid=f'{stamp}_selection_probe_{arm}_r{repeat+1}';folder=ROOT/'experiments/runs'/rid;folder.mkdir(parents=True,exist_ok=False)
            cfg={'version':'selection_probe_v1','architecture':'multi_worker_only','phase':'diagnostic','dataset_role':'regression','batch_id':stamp,'model_id':client.model,'model_checkpoint_revision':'not_exposed','input_count':50,'input_sha256':sha(INPUT.read_bytes()),'arm':arm,'repeat':repeat+1,'seed':20261102+repeat,'temperature':0,'top_p':1,'enable_thinking':False,'workers':2,'automatic_retries':0,'generation_max_tokens':6000,'metric_contract':'selection_probe_mechanical_v1','evaluation_protocol':'reviewed_selection_worker_pair','python':platform.python_version(),'KG_changes':False,'reference_exposed':True,'cost_scope':'worker only, excludes saved analysis/planning'}
            folders[repeat,arm]=folder;results[repeat,arm]=[];configs[repeat,arm]=cfg
            save(folder/'config.json',cfg);save(folder/'freeze.json',freeze);save(folder/'server_models.json',client.models)
            save(folder/'code_hashes.json',{k:v for k,v in freeze.items() if k.endswith('.py')})
            save(folder/'kg_hashes.json',{'delivered_cards':{c['id']:hashobj(c['common']['cards']) for c in cases}})
            save(folder/'validation_contract.json',{'version':cp.VERSION if hasattr(cp,'VERSION') else 'edit_contract_current','files':{k:v for k,v in freeze.items() if '/kg_runtime/' in k}})
            save(folder/'generation.schema.json',cp.WORKER)
            (folder/'generation_prompt.txt').write_text(PROMPT,encoding='utf-8')
            (folder/'private').mkdir(exist_ok=True);(folder/'private/inputs.jsonl').write_bytes(INPUT.read_bytes())
    save(HERE/'private/latest.json',{'root':str(root.relative_to(ROOT)),'run_ids':[p.name for p in folders.values()],'state':'running','started_at':now()})
    progress=Progress(300);t=time.perf_counter()
    def pair(case,repeat,index):
        sequence=ARMS if (repeat+index)%2==0 else tuple(reversed(ARMS));out=[]
        for arm in sequence:
            res=execute(case,arm,repeat+1,folders[repeat,arm],client,20261102+repeat);progress.tick(res);out.append((arm,res))
        return repeat,out
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(pair,c,r,i) for r in range(3) for i,c in enumerate(cases)]
            for fut in as_completed(futures):
                repeat,rows=fut.result()
                for arm,res in rows:results[repeat,arm].append(res)
                print(f'PROGRESS {progress.done}/300 calls={progress.calls} elapsed={time.perf_counter()-t:.1f}s',flush=True)
    finally:progress.close()
    post=source_files();unchanged=post==freeze;save(root/'postflight.json',{'source_and_runtime_unchanged':unchanged})
    order={c['id']:i for i,c in enumerate(cases)};allresults=[]
    for key,folder in folders.items():
        rows=sorted(results[key],key=lambda r:order[r['id']]);assert len(rows)==50
        save(folder/'private/results.json',rows);allresults.extend(rows)
        usage=Counter()
        for r in rows:usage.update({k:v for k,v in (r.get('generation_meta',{}).get('usage') or {}).items() if isinstance(v,(int,float))})
        metrics={'records':50,'valid_output_records':sum(r['status'] in ('unchanged','generated_requires_human_review','partial','needs_review') for r in rows),'changed_records':sum(r['status'] in ('generated_requires_human_review','partial') for r in rows),'statuses':dict(Counter(r['status'] for r in rows)),'actual_worker_calls':sum(r['worker_calls'] for r in rows),'usage':dict(usage),'summed_worker_seconds':sum(r['stage_seconds'].get('generation',0) for r in rows),'quality_accuracy':None,'naturalness':'human review pending','changed_is_not_correct':True}
        metrics.update(status_counts=metrics['statuses'],api_attempts=metrics['actual_worker_calls'],reported_usage=metrics['usage'],calls_with_usage=sum(bool(r.get('generation_meta',{}).get('usage')) for r in rows),calls_without_usage=sum(r['worker_calls'] and not r.get('generation_meta',{}).get('usage') for r in rows))
        save(folder/'metrics.json',metrics);save(folder/'postflight.json',{'source_and_runtime_unchanged':unchanged})
        save(folder/'artifact_hashes.json',{str(p.relative_to(folder)):sha(p.read_bytes()) for p in folder.rglob('*') if p.is_file() and p.name!='artifact_hashes.json'})
        register_run(ROOT,folder)
    save(root/'results.json',allresults);save(root/'summary.json',{'records':len(allresults),'actual_worker_calls':sum(r['worker_calls'] for r in allresults),'wall_seconds':time.perf_counter()-t,'source_and_runtime_unchanged':unchanged,'arms':{a:dict(Counter(r['status'] for r in allresults if r['arm']==a)) for a in ARMS}})
    save(HERE/'private/latest.json',{'root':str(root.relative_to(ROOT)),'run_ids':[p.name for p in folders.values()],'state':'completed','finished_at':now()})
    WorkStore(ROOT).task({'id':'selection-probe-20261102','title':'50문장 선택 비교 진단 실험','actor':'Codex 총괄','stage':'실행 완료·결과 대조','status':'running','done':0,'total':50,'unit':'문장','unit_key':'result_review','message':'300개 처리 기록 저장 완료. 실제 호출과 제외·차단을 나눠 확인합니다.'})
    print(dumps(read(root/'summary.json')),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true');args=parser.parse_args()
    cases=prepare()
    if args.run:run(cases)
