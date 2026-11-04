"""Fresh Qwen regression with frozen v3 knowledge and new scoped composition."""
import concurrent.futures as cf,datetime as dt,json,shutil,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2];sys.path[:0]=[str(ROOT/'local/python'),str(ROOT/'src')]
from kg_pipeline.io import Qwen,read,save,sha,load_jsonl
from kg_pipeline.runner import register_run,metrics
from kg_runtime import card_experiment as ce,card_pipeline as cp
from research_management.live import BatchProgress

def main():
    previous=read(ROOT/'experiments/analyses/card_content_experiment_20261030/private/active_run.json')
    oldroot=ROOT/'experiments/batches'/previous['batch'];input_source=oldroot/'private/inputs.jsonl';records=load_jsonl(input_source)
    assert len(records)==50 and len({r['id'] for r in records})==50
    oldrun=ROOT/'experiments/runs'/previous['runs']['v3_single']
    # Original graph, cards, prompts, call client, and analyzer must remain unchanged.
    oldhash=read(oldrun/'code_hashes.json')
    for rel in ('kg_runtime/card_pipeline.py','kg_pipeline/io.py','kg_runtime/morphology.py','kg_runtime/cards.py'):
        assert sha((ROOT/'src'/rel).read_bytes())==oldhash[rel],rel
    for rel,h in read(oldrun/'kg_hashes.json').items():assert sha((ROOT/rel).read_bytes())==h,rel
    source_hashes={str(p.relative_to(oldroot)):sha(p.read_bytes()) for p in (oldroot/'private/shared/v3').rglob('*') if p.is_file()}
    client=Qwen(ROOT/'test.py');assert client.model==read(oldrun/'config.json')['model_id']
    batch=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'_scoped';root=ROOT/'experiments/batches'/batch
    root.mkdir(parents=True,exist_ok=False);inputs=root/'private/inputs.jsonl';inputs.parent.mkdir();shutil.copy2(input_source,inputs)
    protocol={'batch':batch,'source_batch':previous['batch'],'historical_baselines':{a:previous['runs']['v3_'+a] for a in ('single','multi')},
        'fixed':'50 inputs, stored Kiwi/Qwen analysis, actual v3 cards/IDs/order/forms, graph retrieval, generation prompt, model call parameters',
        'changed':'generic scoped surface-tail operation, deterministic composition/validation, version-derived identifiers and resulting worker plans',
        'comparison':'historical before/after, not simultaneous old-runtime control; separate saved-response replay isolates software behavior',
        'scope':'2 existing card instructions; no new dialect knowledge; no fresh analysis or retrieval',
        'baseline_costs_not_new':True,'workers':2,'automatic_retries':0,'source_hashes':source_hashes,
        'runner_sha256':sha(Path(__file__).read_bytes()),'scope_config_sha256':sha((ROOT/'src/kg_runtime/card_operations.json').read_bytes())}
    save(root/'protocol.json',protocol)
    outs={a:ce.prepare(ROOT,inputs,a,client,batch,'regression','kg_cards_20261030_v3') for a in ('single','multi')}
    for a,out in outs.items():
        config=read(out/'config.json');config.update(experiment_family='scoped_surface_tail_v1',analysis_policy='frozen_cached_analysis_no_new_calls',
            evaluation_protocol='historical_v3_scoped_surface_tail_v1',metric_contract='cached_analysis_generation_only_v1',
            source_batch=previous['batch'],historical_baseline=protocol['historical_baselines'][a],
            cost_policy='new generation calls only; old analysis excluded',new_retrieval_queries=0,
            realization_policy='Qwen selects card and proposes surface; registered exact operation composes final surface, raw proposals and repairs retained')
        save(out/'config.json',config);shutil.copy2(__file__,out/'intervention_runner.py');save(out/'private/intervention_protocol.json',protocol)
        save(out/'freeze.json',{'time':dt.datetime.now(dt.timezone.utc).isoformat(),'config_sha256':sha((out/'config.json').read_bytes()),
            'code_hashes_sha256':sha((out/'code_hashes.json').read_bytes()),'runner_sha256':sha((out/'intervention_runner.py').read_bytes())})
        register_run(ROOT,out)
    save(BASE/'private/active_run.json',{'batch':batch,'root':str(root),'runs':{a:o.name for a,o in outs.items()},'baselines':protocol['historical_baselines']})
    results={a:[] for a in outs};started=time.perf_counter()
    print('BATCH '+batch+' | 50 inputs x Single/Multi | frozen v3 cards',flush=True)
    with BatchProgress(ROOT,batch,len(records)) as progress:
        progress.tasks['analysis']['title']='저장된 분석·카드 목록 재사용 확인';progress.start('analysis')
        for r in records:
            source=oldroot/'private/shared/v3'/r['id'];target=root/'private/shared'/r['id'];shutil.copytree(source,target)
            if read(target/'shared.json')['ok']:
                packet=read(target/'reference_packet.json');old_context=packet['contract_context']
                packet['contract_context']=cp.context(read(target/'morphology.json'),packet['cards'],packet['grammar'],r['id'])
                assert old_context['user_restrictions']==packet['contract_context']['user_restrictions']
                save(target/'reference_packet.json',packet);save(target/'contract_upgrade.json',{'old':old_context,'new':packet['contract_context'],'cards_and_analysis_unchanged':True})
            progress.completed_item('analysis',r['id'],'저장 기록 재사용; 새 모델 분석 없음')
        def job(r,a):
            result=ce.generate(r,a,client,root/'private/shared'/r['id'],outs[a])
            result['reused_analysis_seconds']=result['shared_analysis_seconds'];result['shared_analysis_seconds']=0
            result['total_seconds']=result['incremental_generation_seconds'];result['calls']=[c for c in result['calls'] if c['stage']!='analysis']
            result['stage_seconds']={k:v for k,v in result['stage_seconds'].items() if k not in ('analysis','retrieval')}
            result.update(analysis_reused=True,kg_queries=0,scope_operation='surface_tail_v1')
            save(outs[a]/'private/records'/r['id']/'result.json',result);return a,result
        progress.start('single');progress.start('multi')
        with cf.ThreadPoolExecutor(max_workers=2) as pool:
            jobs=[pool.submit(job,r,a) for i,r in enumerate(records) for a in (('single','multi') if i%2==0 else ('multi','single'))]
            for future in cf.as_completed(jobs):
                a,r=future.result();results[a].append(r);progress.completed_item(a,r['id'],r['status']);print(r['id']+' '+a+' '+r['status'],flush=True)
        wall=time.perf_counter()-started;progress.start('finalize');order={r['id']:i for i,r in enumerate(records)};calls=[]
        assert all(sha((oldroot/rel).read_bytes())==h for rel,h in source_hashes.items())
        for a,out in outs.items():
            rows=sorted(results[a],key=lambda r:order[r['id']]);save(out/'private/results.json',rows)
            m=metrics(rows,wall);m.update(wall_seconds=None,shared_batch_wall_seconds=wall,evaluation_note='Execution counts only; scoped corrections are program-produced, native quality unscored.',cost_note='Historical analysis costs excluded.')
            save(out/'metrics.json',m)
            checks={'input_unchanged':sha(inputs.read_bytes())==read(out/'config.json')['input_sha256'],
                'code_unchanged':all(sha((ROOT/'src'/rel).read_bytes())==h for rel,h in read(out/'code_hashes.json').items()),
                'kg_unchanged':all(sha((ROOT/rel).read_bytes())==h for rel,h in read(out/'kg_hashes.json').items()),'source_records_unchanged':True}
            save(out/'postflight.json',checks);assert all(checks.values()),checks
            save(out/'artifact_hashes.json',{str(p.relative_to(out)):sha(p.read_bytes()) for p in out.rglob('*') if p.is_file() and p.name!='artifact_hashes.json'})
            calls.extend(c for r in rows for c in r['calls']);register_run(ROOT,out)
        save(root/'resources.json',{'physical_api_attempts':len(calls),'physical_total_tokens':sum((c.get('usage') or {}).get('total_tokens',0) for c in calls),
            'wall_seconds':wall,'new_analysis_calls':0,'new_retrieval_queries':0,'input_count':50,'conditions':2})
        progress.completed_item('finalize',batch,'100개 결과·버전·비용 저장 완료')
    print('COMPLETE '+batch,flush=True)
if __name__=='__main__':main()
