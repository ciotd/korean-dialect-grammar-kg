"""Versioned integrated grammar experiment. Requires explicit --execute."""
import argparse
import collections
import datetime as dt
import json
import re
from pathlib import Path
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'local/python')]
from kg_pipeline.integrated import (IntegratedReader,observe_units,analysis_contract,bind_analysis,
    retrieve_packet,ANALYSIS_PROMPT,GENERATION_PROMPT,GENERATION_SCHEMA,require)
from kg_pipeline.io import Qwen,read,save,sha,dumps,load_jsonl
from kg_pipeline.validation import validate_schema
from kg_pipeline.runner import register_run
from kg_runtime.morphology import Morphology
from research_management.work import WorkStore


def execute(args):
    graph=read(args.graph);reader=IntegratedReader(graph);rows=load_jsonl(args.inputs)
    prompt_path=getattr(args,'analysis_prompt',None)
    analysis_prompt=Path(prompt_path).read_text(encoding='utf8') if prompt_path else ANALYSIS_PROMPT
    require(bool(analysis_prompt.strip()),'Empty analysis prompt')
    require(rows and len({r['id'] for r in rows})==len(rows),'Duplicate/empty inputs')
    require(all(re.fullmatch(r'[A-Za-z0-9_-]+',r['id']) for r in rows),'Unsafe input ID')
    require(args.max_calls>=2*len(rows),'Budget does not cover analysis plus generation')
    end=dt.datetime.fromisoformat(args.deadline);require(end.tzinfo and end>dt.datetime.now(dt.timezone.utc),'Deadline expired or missing timezone')
    program_id='integrated_grammar_20261106';prior_calls=0
    for cfg in (ROOT/'experiments/runs').glob('*_integrated_grammar_*/config.json'):
        if read(cfg).get('program_id')==program_id:prior_calls+=len(list((cfg.parent/'private/records').rglob('meta.json')))
    require(prior_calls+2*len(rows)<=200,'This task has a cumulative 200-call limit; preserve budget for requested regression')
    stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out=ROOT/'experiments/runs'/(stamp+'_integrated_grammar_'+args.phase);(out/'private').mkdir(parents=True,exist_ok=False)
    shutil.copy2(args.inputs,out/'private/inputs.jsonl');shutil.copy2(args.graph,out/'private/graph.json')
    save(out/'config.json',{'phase':args.phase,'dataset_role':'regression_exposed' if args.phase=='regression' else 'development_exposed',
        'input_count':len(rows),'input_sha256':sha(Path(args.inputs).read_bytes()),'kg_dataset':graph['version'],
        'metric_contract':'integrated_grammar_v1','program_id':program_id,'program_prior_calls':prior_calls,'program_total_call_limit':200,
        'model_id':args.model,'graph_sha256':sha(Path(args.graph).read_bytes()),'max_calls':args.max_calls,
        'deadline':args.deadline,'deadline_policy':'no_new_calls_after_deadline','seed':args.seed,
        'automatic_retries':0,'final_writer':'Qwen_raw_output','knowledge_character_budget':args.char_budget,
        'reference_answers_in_request':False,'naturalness':'not_evaluated','baseline':'development integration, not causal KG comparison',
        'analysis_prompt_variant':'explicit_file' if prompt_path else 'default',
        'analysis_prompt_sha256':sha(analysis_prompt.encode())})
    (out/'analysis_prompt.txt').write_text(analysis_prompt,encoding='utf-8')
    (out/'generation_prompt.txt').write_text(GENERATION_PROMPT,encoding='utf-8')
    save(out/'generation.schema.json',GENERATION_SCHEMA);save(out/'kg_hashes.json',{'graph':sha(Path(args.graph).read_bytes())})
    hashes={}
    for rel in ['tools/run_integrated_grammar.py','src/kg_pipeline/integrated.py','src/kg_pipeline/io.py','src/kg_pipeline/validation.py','src/kg_runtime/morphology.py']:
        source=ROOT/rel;dest=out/'code_snapshot'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest);hashes[rel]=sha(source.read_bytes())
    save(out/'code_hashes.json',hashes);register_run(ROOT,out)
    results=[];calls=0;consecutive=0;start=time.perf_counter();stop=None
    work=WorkStore(ROOT)
    def progress_event(done,status,message):
        try:work.task({'id':out.name,'title':'9분야 통합 '+args.phase,'actor':'Qwen / 연구 리드','stage':'분석→조회→문장 생성',
                      'status':status,'done':done,'total':len(rows),'unit':'입력','unit_key':out.name,'message':message})
        except Exception as exc:save(out/'progress_registration_error.json',{'error_type':type(exc).__name__})
    progress_event(0,'running','실제 호출을 시작합니다. 3개 입력 완료 후 측정 속도로 남은 시간을 계산합니다.')
    try:
        client=Qwen(ROOT/'test.py',model=args.model,timeout=120);save(out/'server_models.json',client.models)
        morph=Morphology()
        for row in rows:
            if dt.datetime.now(dt.timezone.utc)>=end or calls+2>args.max_calls or prior_calls+calls+2>200:stop='deadline_or_budget';break
            if consecutive>=3:stop='consecutive_failures';break
            t0=time.perf_counter();rd=out/'private/records'/row['id']
            result={'id':row['id'],'input_text':row['text'],'output_text':None,'status':'started','stage':'morphology'}
            save(rd/'input.json',row)
            try:
                observed=morph.analyze(row['text']);save(rd/'morphology.json',observed)
                units=observe_units(observed);require(units,'No analyzable units');save(rd/'units.json',units)
                schema=analysis_contract(reader,units);save(rd/'analysis.schema.json',schema)
                result['stage']='analysis';calls+=1
                raw=client.call('integrated_analysis',analysis_prompt,{'text':row['text'],'units':units},schema,rd/'analysis',8192,args.seed)
                validate_schema(raw,schema);bound=bind_analysis(units,raw);save(rd/'bound_analysis.json',bound)
                result['stage']='retrieval';packet,traces=retrieve_packet(reader,row['text'],bound,args.char_budget)
                save(rd/'retrieval.json',traces);save(rd/'generation_packet.json',packet)
                require('expected_surface' not in dumps(packet),'Diagnostic answer leak')
                if dt.datetime.now(dt.timezone.utc)>=end:raise TimeoutError('Deadline before generation')
                result['stage']='generation';calls+=1
                response=client.call('integrated_generation',GENERATION_PROMPT,packet,GENERATION_SCHEMA,rd/'generation',4096,args.seed)
                validate_schema(response,GENERATION_SCHEMA)
                result.update(output_text=response['output_text'],model_status=response['status'],used_rule_ids=response['used_rule_ids'])
                delivered={a['rule_id'] for a in packet['verified_scope_knowledge']}
                result['undeclared_rule_ids']=sorted(set(response['used_rule_ids'])-delivered)
                result.update(status='generated_requires_human_review' if response['output_text'].strip() else 'failed',
                    unchanged=response['output_text']==row['text'],unit_count=len(units),
                    unit_kinds=dict(collections.Counter(u['kind'] for u in units)),
                    delivered_knowledge=len(packet['verified_scope_knowledge']),related_source_count=len(packet['related_unprocessed_sources']),
                    delivery_omissions=packet['delivery_omissions'],rule_ids=sorted(delivered))
                # Diagnostics never replace or edit the raw model output.
                after=morph.analyze(response['output_text'])
                past=lambda m:sum(t['base_tag']=='EP' and t['form'] in ('았','었','였') for t in m['tokens'])
                result['observational_warnings']=(['past_marker_count_decreased'] if past(after)<past(observed) else [])+(['undeclared_rule_id'] if result['undeclared_rule_ids'] else [])
                result['diagnostic_limit']='Kiwi counts and self-reported rule IDs are not semantic correctness or naturalness scores'
                consecutive=0 if result['status']!='failed' else consecutive+1
            except KeyboardInterrupt:
                stop='interrupted';result.update(status='interrupted')
                save(out/'interruption.json',{'input_id':row['id'],'stage':result['stage'],'calls_started':calls})
            except Exception as exc:
                if result.get('output_text') is not None:
                    result.update(diagnostic_error_type=type(exc).__name__);consecutive=0
                else:
                    result.update(status='failed',error_type=type(exc).__name__,error_detail=str(exc)[:400]);consecutive+=1
            result['total_seconds']=round(time.perf_counter()-t0,4);save(rd/'result.json',result);results.append(result)
            save(out/'private/results.json',results)
            progress={'done':len(results),'total':len(rows),'id':row['id'],'status':result['status'],
                      'elapsed_seconds':round(time.perf_counter()-start,1),'eta_seconds':round((time.perf_counter()-start)/len(results)*(len(rows)-len(results)),1)}
            save(out/'progress.json',progress);print(dumps(progress),flush=True)
            progress_event(len(results),'running',row['id']+' 처리: '+result['status'])
            if stop:break
    except KeyboardInterrupt:
        stop='interrupted';save(out/'interruption.json',{'stage':'setup_or_between_inputs','calls_started':calls})
    except Exception as exc:
        stop='setup_failure';save(out/'failure.json',{'error_type':type(exc).__name__})
    finally:
        save(out/'private/results.json',results)
        metas=[read(p) for p in (out/'private/records').rglob('meta.json')]
        metrics={'records':len(results),'planned_inputs':len(rows),'unattempted_inputs':len(rows)-len(results),
            'valid_output_records':sum(r['status']=='generated_requires_human_review' for r in results),
            'changed_records':sum(r.get('output_text') is not None and r['output_text']!=r['input_text'] for r in results),
            'actual_text_changes':sum(r.get('output_text') is not None and r['output_text']!=r['input_text'] for r in results),
            'status_counts':dict(collections.Counter(r['status'] for r in results)),
            'failure_stages':dict(collections.Counter(r['stage'] for r in results if r['status']=='failed')),
            'model_review_requested':sum(r.get('model_status')=='needs_review' for r in results),
            'api_attempts':len(metas),'calls_counted':calls,'analysis_calls':sum(m.get('stage')=='integrated_analysis' for m in metas),
            'generation_calls':sum(m.get('stage')=='integrated_generation' for m in metas),
            'reported_usage':{k:sum((m.get('usage') or {}).get(k,0) or 0 for m in metas) for k in ('prompt_tokens','completion_tokens','total_tokens')},
            'calls_without_usage':sum(not m.get('usage') for m in metas),'wall_seconds':round(time.perf_counter()-start,3),
            'usage_completeness':'complete' if metas and all(m.get('usage') for m in metas) else 'partial_or_absent_reported_sum_only',
            'stop_reason':stop,'naturalness':None,'independent_accuracy':None}
        if stop and stop!='interrupted':save(out/'failure.json',{**(read(out/'failure.json') if (out/'failure.json').exists() else {}),'stop_reason':stop})
        save(out/'metrics.json',metrics)
        save(out/'postflight.json',{'graph_unchanged':sha(Path(args.graph).read_bytes())==read(out/'config.json')['graph_sha256'],
            'code_unchanged':all(sha((ROOT/rel).read_bytes())==h for rel,h in hashes.items())})
        save(out/'artifact_hashes.json',{p.relative_to(out).as_posix():sha(p.read_bytes()) for p in out.rglob('*') if p.is_file()})
        register_run(ROOT,out)
        progress_event(len(results),'failed' if stop else 'completed','모든 기록 저장. 자연스러움은 별도 검토 필요.' if not stop else '중단: '+stop)
    print(dumps({'run_id':out.name,'directory':str(out),'metrics':metrics}),flush=True)
    return out,metrics


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true',required=True)
    p.add_argument('--graph',required=True);p.add_argument('--inputs',required=True);p.add_argument('--phase',choices=['smoke','development','regression','repair'],required=True)
    p.add_argument('--analysis-prompt',help='Explicit analysis-only comparison prompt, frozen in the run')
    p.add_argument('--model',default='Qwen3.8-27B');p.add_argument('--deadline',required=True);p.add_argument('--max-calls',type=int,required=True)
    p.add_argument('--seed',type=int,default=20261106);p.add_argument('--char-budget',type=int,default=24000)
    args=p.parse_args();_,metrics=execute(args)
    if metrics['stop_reason']:sys.exit(2)
