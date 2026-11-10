"""Kiwi-default pipeline; paired connection-policy development or full regression."""
import argparse,collections,datetime as dt,platform,re,shutil,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'local/python'),str(ROOT/'tools')]
from kg_pipeline.io import Qwen,read,save,sha,dumps,load_jsonl
from kg_pipeline.integrated import IntegratedReader
from kg_pipeline.delivery_normalization import VERSION as DELIVERY_VERSION
from kg_pipeline.multi_agent import run_sentence,PROMPTS
from kg_pipeline.kiwi_default import initial_structure,SCOPE_PROMPT,prompts,focused_prompts
from kg_pipeline.separated_graph import restore
from kg_pipeline.runner import register_run
from research_management.work import WorkStore
from run_qwen_multi import GuardedClient,RunLimitReached,output_availability

HERE=ROOT/'experiments/analyses/kiwi_default_20261107'

def execute(args):
    if not args.execute:raise ValueError('Explicit execution required')
    rows=load_jsonl(args.inputs)
    if not rows or len({r['id'] for r in rows})!=len(rows):raise ValueError('Empty/duplicate inputs')
    if any(not re.fullmatch('[A-Za-z0-9_-]+',r['id']) or not isinstance(r.get('text'),str) or not r['text'].strip() for r in rows):raise ValueError('Invalid input')
    paired=getattr(args,'paired',False);policy=getattr(args,'connection_policy','kiwi_improved')
    policies=([getattr(args,'comparison_policy','baseline'),policy] if paired else [policy])
    if len(set(policies))!=len(policies):raise ValueError('Compared policies must differ')
    reuse=Path(args.replay_structure) if getattr(args,'replay_structure',None) else None
    needed=len(rows)*((0 if reuse else 1)+3*len(policies))
    if args.max_calls<needed:raise ValueError('Budget must cover scope and downstream roles')
    end=dt.datetime.fromisoformat(args.deadline)
    if end.tzinfo is None or end<=dt.datetime.now(dt.timezone.utc):raise ValueError('Invalid deadline')
    stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out=ROOT/'experiments/runs'/(stamp+'_kiwi_default_'+args.phase);out.mkdir(parents=True)
    (out/'private').mkdir();shutil.copy2(args.inputs,out/'private/inputs.jsonl')
    graph_path=Path(args.graph) if getattr(args,'graph',None) else ROOT/read(ROOT/'knowledge/authored/semantic_grammar_20261107_separated_r1/latest.json')['graph']
    graph=read(graph_path);reader=IntegratedReader(graph);shutil.copy2(graph_path,out/'private/graph.json')
    for name in ('audit.json','manifest.json'):shutil.copy2(graph_path.parent/name,out/'private'/('kg_'+name))
    restore(graph,read(graph_path.parent/'audit.json'));manifest=read(graph_path.parent/'manifest.json')
    if sha(graph_path.read_bytes())!=manifest['graph_sha256'] or sha((graph_path.parent/'audit.json').read_bytes())!=manifest['audit_sha256']:raise ValueError('KG manifest mismatch')
    config={'program_id':'kiwi_default_20261107','phase':args.phase,'dataset_role':'regression_exposed' if args.phase=='regression' else 'development',
        'metric_contract':'kiwi_default_v1','policies':policies,'input_count':len(rows),'planned_records':len(rows)*len(policies),
        'model_id':args.model,'seed':args.seed,'temperature':0,'top_p':1,'enable_thinking':False,'max_calls':args.max_calls,
        'deadline':args.deadline,'input_sha256':sha(Path(args.inputs).read_bytes()),'graph_sha256':sha(graph_path.read_bytes()),
        'analysis_backend':'Kiwi_morphology_Qwen_scope_and_meaning','final_writer':'Qwen_raw_output',
        'automatic_retries':0,'max_analysis_repairs':0,'max_generation_repairs':0,'reference_answers_in_request':False,
        'paired_shared_scope':paired,'changed_factors':'connection_unknown_handling_meaning_relation_guidance_humility_delivery',
        'knowledge_character_budget':args.char_budget,'python_version':platform.python_version(),'sampling_repeat_count':1,
        'worker_roles':['scope','meaning','writer','diagnostic_reviewer'],
        'delivery_normalization_version':DELIVERY_VERSION}
    if reuse:
        prior=read(reuse/'config.json');artifacts=read(reuse/'artifact_hashes.json')
        if any(prior[k]!=config[k] for k in ('input_sha256','graph_sha256','model_id','seed')):raise ValueError('Structure replay input/KG/model/seed mismatch')
        config['structure_reuse']={'source_run':reuse.name,'source_artifact_manifest_sha256':sha((reuse/'artifact_hashes.json').read_bytes()),'new_scope_calls':0,'scope_cost_in_source_run_only':True}
    save(out/'config.json',config);hashes={}
    paths=['tools/run_kiwi_default.py','tools/run_qwen_multi.py','src/kg_pipeline/kiwi_default.py','src/kg_pipeline/morphology_control.py',
        'src/kg_pipeline/multi_agent.py','src/kg_pipeline/integrated.py','src/kg_pipeline/delivery_normalization.py','src/kg_pipeline/io.py','src/kg_pipeline/validation.py',
        'src/kg_pipeline/separated_graph.py','src/kg_pipeline/runner.py','src/research_management/core.py','src/research_management/work.py']
    for rel in paths:
        dest=out/'code_snapshot'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,dest);hashes[rel]=sha((ROOT/rel).read_bytes())
    save(out/'code_hashes.json',hashes)
    for label,ps in [('baseline',PROMPTS),('kiwi_improved',prompts()),('kiwi_focused',focused_prompts()),('common',{'scope':SCOPE_PROMPT})]:
        for key,value in ps.items():
            p=out/'prompts'/label/(key+'.txt');p.parent.mkdir(parents=True,exist_ok=True);p.write_text(value,encoding='utf8')
    config['prompt_sha256']={str(p.relative_to(out/'prompts')):sha(p.read_bytes()) for p in (out/'prompts').rglob('*.txt')};save(out/'config.json',config)
    register_run(ROOT,out);work=WorkStore(ROOT);start=time.perf_counter();results=[];client=None;stop=None;failures=0;scope_records=[]
    def progress(status,message):
        elapsed=time.perf_counter()-start;n=len(results);total=config['planned_records']
        value={'done':n,'total':total,'elapsed_seconds':round(elapsed,1),'eta_seconds':round(elapsed/n*(total-n),1) if n>=4 else None,
            'eta_basis':'observed_average_including_scope_after_four_paths','status':status,'message':message}
        save(out/'progress.json',value);print(dumps(value),flush=True)
        try:work.task({'id':out.name,'title':'Kiwi 기본 연결 보완 '+args.phase,'actor':'연구 리드 / Qwen','stage':'Kiwi·절→의미·KG→작성·진단',
            'status':status,'done':n,'total':total,'unit':'경로','unit_key':out.name,'message':message})
        except Exception as e:save(out/'progress_registration_error.json',{'error_type':type(e).__name__})
    try:
        from kiwipiepy import Kiwi
        import kiwipiepy
        t=time.perf_counter();kiwi=Kiwi(num_workers=1);config.update(kiwi_initialization_seconds=time.perf_counter()-t,kiwi_package_version=kiwipiepy.__version__);save(out/'config.json',config)
        transport=Qwen(ROOT/'test.py',model=args.model,timeout=120);save(out/'server_models.json',transport.models)
        client=GuardedClient(transport,end,args.max_calls,3);progress('running','새 절 구획과 형태를 공유한 비교 시작' if paired else 'Kiwi 기본 전체 연결 시작')
        for ix,row in enumerate(rows):
            if failures>=3:stop='three_consecutive_failed_inputs';break
            if dt.datetime.now(dt.timezone.utc)>=end:stop='deadline';break
            shared=out/'private/shared'/row['id'];t=time.perf_counter();client.begin_input()
            try:
                if reuse:
                    rel='private/shared/'+row['id']+'/common_structure.json';src=reuse/rel
                    if sha(src.read_bytes())!=artifacts.get(rel):raise ValueError('Shared structure snapshot hash mismatch')
                    prepared=read(src);save(shared/'common_structure.json',prepared)
                    save(shared/'structure_reuse.json',{'source':str(src),'sha256':sha(src.read_bytes()),'new_model_calls':0})
                else:prepared=initial_structure(client,row['text'],kiwi,shared,args.seed)
                scope_records.append({'id':row['id'],'complete':True,'seconds':time.perf_counter()-t,'api_attempts':client.input_calls})
            except (Exception,KeyboardInterrupt) as e:
                scope_records.append({'id':row['id'],'complete':False,'seconds':time.perf_counter()-t,'api_attempts':client.input_calls,'error_type':type(e).__name__})
                failures+=1
                for policy in policies:
                    r={'id':row['id']+'_'+policy,'source_input_id':row['id'],'policy':policy,'input_text':row['text'],
                        'output_text':None,'status':'failed','pipeline_completed':False,'error_type':type(e).__name__,'last_stage':'shared_scope','api_attempts':0}
                    results.append(r);save(out/'private/records'/r['id']/'result.json',r)
                save(out/'private/results.json',results);save(out/'scope_records.json',scope_records)
                progress('running',row['id']+': 공통 절 분석 실패; 양쪽 실패로 기록')
                if isinstance(e,KeyboardInterrupt):stop='interrupted';break
                if isinstance(e,RunLimitReached):stop=str(e);break
                continue
            save(out/'scope_records.json',scope_records)
            shared_hash=sha(dumps(prepared).encode())
            branch_failed=False
            for policy in (policies if ix%2==0 else list(reversed(policies))):
                rd=out/'private/records'/(row['id']+'_'+policy);t=time.perf_counter();client.begin_input();save(rd/'input.json',row)
                r={'id':row['id']+'_'+policy,'source_input_id':row['id'],'policy':policy,'input_text':row['text'],'output_text':None,'status':'started','pipeline_completed':False}
                save(rd/'control_input.json',{'common_structure_sha256':shared_hash,'source_text_sha256':sha(row['text'].encode()),
                    'graph_sha256':config['graph_sha256'],'seed':args.seed,'model':args.model})
                try:
                    if sha(dumps(prepared).encode())!=shared_hash:raise ValueError('Shared structure mutated')
                    r.update(run_sentence(client,reader,row['text'],rd,seed=args.seed,char_budget=args.char_budget,
                        max_repairs=0,max_analysis_repairs=0,prepared_structure=prepared,connection_policy=policy))
                    if sha(dumps(prepared).encode())!=shared_hash:raise ValueError('Shared structure mutated by policy')
                    r['pipeline_completed']=True
                except KeyboardInterrupt:stop='interrupted';r.update(status='interrupted',error_type='KeyboardInterrupt');branch_failed=True
                except Exception as e:
                    r.update(status='failed',error_type=type(e).__name__);branch_failed=True
                    if isinstance(e,RunLimitReached):stop=str(e)
                r.update(output_availability(rd,r));r.update(api_attempts=client.input_calls,total_seconds=time.perf_counter()-t)
                stage=rd/'pipeline_stage.json';r['last_stage']=read(stage)['stage'] if stage.exists() else 'structure_preparation'
                save(rd/'result.json',r);results.append(r);save(out/'private/results.json',results);progress('running',row['id']+' '+policy+': '+r['status'])
                if stop:break
            failures=failures+1 if branch_failed else 0
            if stop:break
    except KeyboardInterrupt:stop='interrupted'
    except Exception as e:stop='setup_or_iteration_failure';save(out/'failure.json',{'error_type':type(e).__name__})
    finally:
        save(out/'private/results.json',results);save(out/'scope_records.json',scope_records)
        metas=[read(p) for p in (out/'private').rglob('meta.json')];by={}
        for policy in policies:
            rr=[r for r in results if r['policy']==policy];mm=[read(p) for d in (out/'private/records').glob('*_'+policy) for p in d.rglob('meta.json')]
            by[policy]={'records':len(rr),'complete':sum(r['pipeline_completed'] for r in rr),'api_attempts':sum(r['api_attempts'] for r in rr),
                'branch_seconds':sum(r.get('total_seconds',0) for r in rr),'tokens':sum((m.get('usage') or {}).get('total_tokens',0) or 0 for m in mm)}
        metrics={'records':len(results),'planned_records':config['planned_records'],'unattempted_records':config['planned_records']-len(results),
            'valid_output_records':sum(r['pipeline_completed'] for r in results),'changed_records':sum(r['pipeline_completed'] and r['output_text']!=r['input_text'] for r in results),
            'by_policy':by,'scope_calls':sum(r['api_attempts'] for r in scope_records),'scope_complete':sum(r['complete'] for r in scope_records),
            'api_attempts':client.calls_started if client else 0,'transport_meta_records':len(metas),
            'reported_usage':{k:sum((m.get('usage') or {}).get(k,0) or 0 for m in metas) for k in ('prompt_tokens','completion_tokens','total_tokens')},
            'calls_without_usage':sum(not m.get('usage') for m in metas),'wall_seconds':time.perf_counter()-start,
            'stop_reason':stop,'naturalness':None,'independent_accuracy':None}
        if stop:save(out/'failure.json',{'stop_reason':stop})
        save(out/'metrics.json',metrics);save(out/'postflight.json',{'graph_unchanged':sha(graph_path.read_bytes())==config['graph_sha256'],
            'code_unchanged':all(sha((ROOT/p).read_bytes())==h for p,h in hashes.items())})
        progress('failed' if stop else 'completed',stop or '원시 출력 기록 완료; 원문 보존과 오류는 별도 판정')
        save(out/'artifact_hashes.json',{p.relative_to(out).as_posix():sha(p.read_bytes()) for p in out.rglob('*') if p.is_file() and p.name!='artifact_hashes.json'})
        register_run(ROOT,out);save(HERE/('latest_'+args.phase+'.json'),{'run':out.relative_to(ROOT).as_posix()})
    print(dumps({'run_id':out.name,'metrics':metrics}),flush=True)
    return out,metrics

def parser():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true',required=True)
    p.add_argument('--inputs',required=True);p.add_argument('--phase',choices=['development','regression','smoke'],required=True)
    p.add_argument('--paired',action='store_true');p.add_argument('--graph');p.add_argument('--model',default='Qwen3.8-27B')
    p.add_argument('--connection-policy',choices=['kiwi_improved','kiwi_focused'],default='kiwi_improved')
    p.add_argument('--comparison-policy',choices=['baseline','kiwi_improved'],default='baseline')
    p.add_argument('--replay-structure',help='Frozen common structure from a previous same-input/KG/model/seed run; no new scope calls')
    p.add_argument('--deadline',required=True);p.add_argument('--max-calls',type=int,required=True)
    p.add_argument('--seed',type=int,default=20261107);p.add_argument('--char-budget',type=int,default=18000)
    return p

if __name__=='__main__':
    _,m=execute(parser().parse_args())
    if m['stop_reason']:sys.exit(2)
