"""Paired morphology-provider comparison with unchanged downstream workers."""
import argparse, collections, datetime as dt, platform, shutil, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'local/python'),str(ROOT/'tools')]
from kg_pipeline.io import Qwen,read,save,sha,load_jsonl,dumps
from kg_pipeline.integrated import IntegratedReader
from kg_pipeline.multi_agent import PROMPTS,TAG_MEANINGS,run_sentence
from kg_pipeline.morphology_control import anchors,contract,kiwi_rows,frozen_clauses,prepare,MORPH_PROMPT
from kg_pipeline.runner import register_run
from research_management.work import WorkStore
from run_qwen_multi import GuardedClient,RunLimitReached

def execute(args):
    if not args.execute:raise ValueError('Explicit execution required')
    source=Path(args.source).resolve();rows=load_jsonl(source/'private/inputs.jsonl')
    if len(rows)!=6 or len({r['id'] for r in rows})!=6:raise ValueError('Expected frozen six development inputs')
    end=dt.datetime.fromisoformat(args.deadline)
    if end.tzinfo is None or end<=dt.datetime.now(dt.timezone.utc):raise ValueError('Invalid deadline')
    for r in rows:
        if not __import__('re').fullmatch('[A-Za-z0-9_-]+',r['id']):raise ValueError('Unsafe input ID')
    stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out=ROOT/'experiments/runs'/(stamp+'_morphology_control_development');out.mkdir(parents=True)
    (out/'private').mkdir();shutil.copy2(source/'private/inputs.jsonl',out/'private/inputs.jsonl')
    graph_path=ROOT/read(ROOT/'knowledge/authored/semantic_grammar_20261107_separated_r1/latest.json')['graph']
    graph=read(graph_path);reader=IntegratedReader(graph);shutil.copy2(graph_path,out/'private/graph.json')
    for name in ('audit.json','manifest.json'):
        shutil.copy2(graph_path.parent/name,out/'private'/('kg_'+name))
    from kg_pipeline.separated_graph import restore
    restore(graph,read(graph_path.parent/'audit.json'))
    manifest=read(graph_path.parent/'manifest.json')
    if sha(graph_path.read_bytes())!=manifest['graph_sha256'] or sha((graph_path.parent/'audit.json').read_bytes())!=manifest['audit_sha256']:raise ValueError('KG manifest mismatch')
    config={'program_id':'morphology_control_20261107','dataset_role':'development_exposed','model_id':args.model,
        'input_sha256':sha((out/'private/inputs.jsonl').read_bytes()),'graph_sha256':sha(graph_path.read_bytes()),
        'source_run':source.name,'seed':20261107,'max_calls':42,'deadline':args.deadline,
        'automatic_retries':0,'max_analysis_repairs':0,'max_generation_repairs':0,
        'final_writer':'Qwen_raw_output','reference_answers_in_request':False,'knowledge_character_budget':18000,
        'changed_factor':'word_morpheme_form_and_tag_provider','common_unit_adapter':'observe_units',
        'frozen_clause_source':'prior_initial_Qwen_structure_not_gold','unknown_is_not_inferred_absent':True,
        'temperature':0,'top_p':1,'enable_thinking':False,'sampling_repeat_count':1,
        'prompt_sha256':{k:sha(v.encode()) for k,v in {**PROMPTS,'morphology':MORPH_PROMPT}.items()},
        'python_version':platform.python_version(),'naturalness':'not_evaluated'}
    save(out/'config.json',config)
    paths=['tools/run_morphology_control.py','tools/run_qwen_multi.py','src/kg_pipeline/morphology_control.py',
        'src/kg_pipeline/multi_agent.py','src/kg_pipeline/integrated.py','src/kg_pipeline/io.py','src/kg_pipeline/validation.py',
        'src/kg_pipeline/separated_graph.py','src/kg_pipeline/runner.py','src/research_management/core.py','src/research_management/work.py']
    hashes={}
    for rel in paths:
        dest=out/'code_snapshot'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,dest);hashes[rel]=sha((ROOT/rel).read_bytes())
    save(out/'code_hashes.json',hashes)
    for k,v in {**PROMPTS,'morphology':MORPH_PROMPT}.items():
        p=out/'prompts'/(k+'.txt');p.parent.mkdir(exist_ok=True);p.write_text(v,encoding='utf8')
    register_run(ROOT,out);work=WorkStore(ROOT);start=time.perf_counter();results=[];client=None;stop=None;failed={'qwen':0,'kiwi':0}
    def progress(status,message):
        elapsed=time.perf_counter()-start
        value={'done':len(results),'total':12,'elapsed_seconds':round(elapsed,1),
            'eta_seconds':round(elapsed/len(results)*(12-len(results)),1) if len(results)>=3 else None,
            'eta_basis':'observed_average_after_three_branches','status':status,'message':message}
        save(out/'progress.json',value);print(dumps(value),flush=True)
        try:work.task({'id':out.name,'title':'형태 분석만 바꾼 6문장 비교','actor':'Qwen·Kiwi / 연구 리드',
            'stage':'형태→동일 의미·KG·작성·검토','status':status,'done':len(results),'total':12,'unit':'경로',
            'unit_key':out.name,'message':message})
        except Exception as e:save(out/'progress_registration_error.json',{'error_type':type(e).__name__})
    try:
        from kiwipiepy import Kiwi
        import kiwipiepy
        t=time.perf_counter();kiwi=Kiwi(num_workers=1);config['kiwi_initialization_seconds']=time.perf_counter()-t
        config['kiwi_package_version']=kiwipiepy.__version__;save(out/'config.json',config)
        transport=Qwen(ROOT/'test.py',model=args.model,timeout=120);save(out/'server_models.json',transport.models)
        client=GuardedClient(transport,end,42,4);progress('running','조건 고정 완료; 동일 원문으로 두 경로를 번갈아 실행')
        for index,row in enumerate(rows):
            words=anchors(row['text']);source_file=source/'private/records'/row['id']/'structure/parsed.json'
            clause_raw=read(source_file);clauses=frozen_clauses(row['text'],clause_raw)
            save(out/'private/frozen'/row['id']/'clauses.json',{'clauses':clauses,'source_file':str(source_file),'sha256':sha(source_file.read_bytes())})
            for backend in (['qwen','kiwi'] if index%2==0 else ['kiwi','qwen']):
                if any(v>=3 for v in failed.values()):stop='three_consecutive_failures_in_one_backend';break
                if dt.datetime.now(dt.timezone.utc)>=end:stop='deadline';break
                rd=out/'private/records'/(row['id']+'_'+backend);t0=time.perf_counter();client.begin_input()
                result={'id':row['id'],'backend':backend,'input_text':row['text'],'output_text':None,'status':'started','pipeline_completed':False}
                save(rd/'input.json',row);save(rd/'common_anchors.json',words)
                try:
                    t=time.perf_counter()
                    if backend=='qwen':raw=client.call('controlled_morphology',MORPH_PROMPT,{'text':row['text'],'words':words,'tag_definitions':TAG_MEANINGS},contract(words),rd/'morphology',4096,config['seed'])
                    else:raw=kiwi_rows(row['text'],words,kiwi)
                    save(rd/'morphology_rows.json',raw)
                    morphology_seconds=time.perf_counter()-t
                    prepared=prepare(row['text'],words,raw,clauses,backend)
                    result.update(run_sentence(client,reader,row['text'],rd,seed=config['seed'],char_budget=18000,
                        max_repairs=0,max_analysis_repairs=0,prepared_structure=prepared))
                    result.update(pipeline_completed=True,morphology_seconds=morphology_seconds,unit_count=len(prepared['units']))
                    failed[backend]=0
                except KeyboardInterrupt:stop='interrupted';result.update(status='interrupted',error_type='KeyboardInterrupt');failed[backend]+=1
                except RunLimitReached as e:stop=str(e);result.update(status='failed',error_type=type(e).__name__);failed[backend]+=1
                except Exception as e:result.update(status='failed',error_type=type(e).__name__);failed[backend]+=1
                result.update(api_attempts=client.input_calls,total_seconds=time.perf_counter()-t0)
                stagefile=rd/'pipeline_stage.json';result['last_stage']=read(stagefile)['stage'] if stagefile.exists() else 'morphology'
                save(rd/'result.json',result);results.append(result);save(out/'private/results.json',results)
                progress('running',row['id']+' / '+backend+': '+result['status'])
                if stop:break
            if stop:break
    except KeyboardInterrupt:stop='interrupted'
    except Exception as e:stop='setup_or_iteration_failure';save(out/'failure.json',{'error_type':type(e).__name__})
    finally:
        save(out/'private/results.json',results)
        metas=[read(p) for p in (out/'private/records').rglob('meta.json')]
        by={}
        for backend in ('qwen','kiwi'):
            rr=[r for r in results if r['backend']==backend];mm=[read(p) for d in (out/'private/records').glob('*_'+backend) for p in d.rglob('meta.json')]
            by[backend]={'records':len(rr),'complete':sum(r['pipeline_completed'] for r in rr),'api_attempts':sum(r['api_attempts'] for r in rr),
                'record_seconds':sum(r['total_seconds'] for r in rr),'reported_usage':{k:sum((m.get('usage') or {}).get(k,0) or 0 for m in mm) for k in ('prompt_tokens','completion_tokens','total_tokens')},
                'calls_without_usage':sum(not m.get('usage') for m in mm),'delivered_candidates':sum(r.get('delivered_candidates',0) for r in rr)}
        complete_pairs=sum(all(any(r['id']==row['id'] and r['backend']==b and r['pipeline_completed'] for r in results) for b in ('qwen','kiwi')) for row in rows)
        metrics={'records':len(results),'planned_records':12,'unattempted_records':12-len(results),'complete_pairs':complete_pairs,'by_backend':by,'api_attempts':client.calls_started if client else 0,
            'transport_meta_records':len(metas),'wall_seconds':time.perf_counter()-start,'stop_reason':stop,'naturalness':None,'independent_accuracy':None}
        save(out/'metrics.json',metrics);save(out/'postflight.json',{'graph_unchanged':sha(graph_path.read_bytes())==config['graph_sha256'],
            'code_unchanged':all(sha((ROOT/p).read_bytes())==h for p,h in hashes.items())})
        progress('failed' if stop else 'completed',stop or '양쪽 출력 저장; 품질은 별도 검토')
        save(out/'artifact_hashes.json',{str(p.relative_to(out)):sha(p.read_bytes()) for p in out.rglob('*') if p.is_file() and p.name!='artifact_hashes.json'})
        register_run(ROOT,out)
        save(ROOT/'experiments/analyses/morphology_control_20261107/latest.json',{'run':str(out.relative_to(ROOT))})
    print(out,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true',required=True);p.add_argument('--source',required=True);p.add_argument('--deadline',required=True);p.add_argument('--model',default='Qwen3.8-27B');execute(p.parse_args())
