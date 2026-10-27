"""CLI: one frozen run, no automatic tuning/retry, private per-input provenance."""
import argparse
import concurrent.futures
import datetime as dt
import json
import platform
import shutil
import subprocess
import time
import traceback
from pathlib import Path
from . import __version__
from .contracts import ANALYSIS,GENERATION,ANALYSIS_PROMPT,GENERATION_PROMPT
from .io import Qwen,Neo4j,load_jsonl,read,save,sha,dumps
from .mapping import map_concepts
from .retrieval import load_catalog,retrieve
from .selection import select_evidence
from .validation import validate_analysis,validate_generation

DATASET='kg_v3_evidence_20261019_r2'
INPUT_SHA='182dad5a3294534775bce4f4c7bd6b0a2fa22286cff3189f786f08eadcda5dff'

def execute_record(record,client,neo,catalog,config,out):
    folder=out/'private'/'records'/record['id'];folder.mkdir(parents=True,exist_ok=False)
    result={'id':record['id'],'input_text':record['text'],'status':'started','output_text':None,'stage_seconds':{},'human_evaluation':None}
    start=time.perf_counter();stage='analysis';save(folder/'input.json',record)
    try:
        t=time.perf_counter()
        analysis=client.call('analysis',ANALYSIS_PROMPT,{'input_id':record['id'],'text':record['text']},ANALYSIS,folder/'analysis_call',config['analysis_max_tokens'],config['seed'])
        checks=validate_analysis(analysis,record['text'],record['id'],ANALYSIS);save(folder/'analysis_checks.json',checks)
        result['stage_seconds'][stage]=time.perf_counter()-t
        stage='mapping';t=time.perf_counter();mapping=map_concepts(analysis,catalog);save(folder/'mapping.json',mapping)
        result['stage_seconds'][stage]=time.perf_counter()-t
        stage='retrieval';t=time.perf_counter();raw=retrieve(neo,mapping,DATASET,config['neighbor_limit']);save(folder/'retrieval_raw.json',raw)
        result['stage_seconds'][stage]=time.perf_counter()-t
        stage='selection';t=time.perf_counter();packet,audit=select_evidence(raw,analysis,mapping,config['packet_max_chars'],config['packet_max_items'])
        save(folder/'reference_packet.json',packet);save(folder/'selection_audit.json',audit)
        result['stage_seconds'][stage]=time.perf_counter()-t
        result.update(concepts=len(mapping['selected_concept_ids']),claim_paths=len(raw['claim_paths']),
           reference_count=sum(e['role']=='realization_reference' for e in packet['evidence']),
           constraint_count=sum(e['role']=='constraint' for e in packet['evidence']),
           raw_chars=audit['raw_chars'],packet_chars=audit['packet_chars'],mapping_failures=mapping['mapping_failures'],
           neighborhood_limit_reached=raw['neighborhood_limit_reached'],analysis_warnings=checks['warnings'])
        stage='generation';t=time.perf_counter()
        user={'input_id':record['id'],'input_text':record['text'],'analysis':analysis,'reference_packet':packet}
        generated=client.call('generation',GENERATION_PROMPT,user,GENERATION,folder/'generation_call',config['generation_max_tokens'],config['seed'])
        verified=validate_generation(generated,record['text'],record['id'],analysis,packet,checks,GENERATION)
        save(folder/'generation_checks.json',verified);result['stage_seconds'][stage]=time.perf_counter()-t
        result.update(output_text=generated['output_text'],edit_count=verified['edit_count'],unresolved=generated['unresolved'],
          status='generated_requires_human_review' if verified['changed'] else 'unchanged')
    except Exception as e:
        result.update(status=stage+'_failed',error_type=type(e).__name__,error=str(e)[:700])
        # Traceback contains code paths, never client credential object representations.
        (folder/'traceback.txt').write_text(traceback.format_exc(),encoding='utf-8')
    result['total_seconds']=round(time.perf_counter()-start,4)
    result['calls']=[read(p) for p in sorted(folder.glob('*_call/meta.json'))]
    save(folder/'result.json',result)
    return result

def metrics(results,wall):
    from collections import Counter
    import statistics
    calls=[c for r in results for c in r['calls']]
    usage={k:sum(c.get('usage',{}).get(k,0) or 0 for c in calls if c.get('usage')) for k in ('prompt_tokens','completion_tokens','total_tokens')}
    valid=[r for r in results if r['status'] in ('generated_requires_human_review','unchanged')]
    raw=sum(r.get('raw_chars',0) for r in results);packet=sum(r.get('packet_chars',0) for r in results)
    return {'records':len(results),'status_counts':dict(Counter(r['status'] for r in results)),
      'valid_output_records':len(valid),'changed_records':sum(r['status']=='generated_requires_human_review' for r in results),
      'records_with_realization_reference':sum(r.get('reference_count',0)>0 for r in results),
      'records_with_claim_paths':sum(r.get('claim_paths',0)>0 for r in results),
      'api_attempts':len(calls),'api_failures':sum(c['status']=='failed' for c in calls),'automatic_retries':0,
      'reported_usage':usage,'calls_with_usage':sum(bool(c.get('usage')) for c in calls),'calls_without_usage':sum(not c.get('usage') for c in calls),
      'wall_seconds':round(wall,3),'mean_record_seconds':round(statistics.mean(r['total_seconds'] for r in results),3),
      'median_record_seconds':round(statistics.median(r['total_seconds'] for r in results),3),
      'retrieval_chars_total':raw,'packet_chars_total':packet,'char_reduction_fraction':round(1-packet/raw,5) if raw else None,
      'neighborhood_limit_records':sum(r.get('neighborhood_limit_reached',False) for r in results),
      'error_types':dict(Counter(r.get('error_type') for r in results if r.get('error_type'))),
      'accuracy':None,'naturalness':None,'evidence_appropriateness':None,
      'evaluation_note':'No gold labels or independent human scores. Counts measure execution and coverage, not linguistic accuracy or KG causal benefit.'}

def main(args=None):
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True)
    p.add_argument('--credentials',type=Path,required=True);p.add_argument('--qwen-config',type=Path,required=True)
    p.add_argument('--phase',choices=['smoke','first50'],required=True);p.add_argument('--workers',type=int,default=2)
    a=p.parse_args(args)
    if not 1<=a.workers<=4:raise ValueError('workers must be 1..4')
    records=load_jsonl(a.inputs)
    if not records or len({r['id'] for r in records})!=len(records):raise ValueError('empty/duplicate input IDs')
    import re
    if any(not re.fullmatch(r'[A-Za-z0-9_-]+',r['id']) or not isinstance(r['text'],str) for r in records):raise ValueError('invalid input record')
    input_sha=sha(a.inputs.read_bytes())
    if a.phase=='first50' and (len(records)!=50 or input_sha!=INPUT_SHA):raise ValueError('frozen_50_input_mismatch')
    if a.phase=='smoke':
        frozen=a.project/'data/derived_private/standard_inputs_50_20261023_v1/inputs.jsonl'
        approved={r['text'] for r in load_jsonl(frozen)}
        if any(r['text'] in approved for r in records):raise ValueError('smoke_input_overlaps_frozen_50')
    stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out=a.project/'experiments/runs'/f'{stamp}_qwen_kg_{a.phase}';out.mkdir(parents=True,exist_ok=False)
    config={'version':__version__,'phase':a.phase,'kg_dataset':DATASET,'seed':20261023,'temperature':0,'top_p':1,'enable_thinking':False,
      'analysis_max_tokens':12000,'generation_max_tokens':5000,'timeout_seconds':180,'workers':a.workers,
      'packet_max_chars':24000,'packet_max_items':16,'neighbor_limit':1501,'automatic_retries':0,'input_sha256':input_sha,
      'input_count':len(records),'scope':'source_reference_pilot','region_filter':None,'model_checkpoint_revision':'not_exposed_by_server',
      'quantization':'not_exposed_by_server','vllm_version':'not_exposed_by_server','gpu':'not_exposed_by_server',
      'test_exposure':'50 inputs previously visible in conversation; NEW007 previously used as a design illustration. No first50 outcome tuning; not an unseen holdout.',
      'python':platform.python_version(),'platform':platform.platform()}
    save(out/'config.json',config)
    code=Path(__file__).parent
    for f in code.glob('*.py'):
        target=out/'code_snapshot'/f.name;target.parent.mkdir(exist_ok=True);shutil.copy2(f,target)
    tests=a.project/'tests/test_kg_pipeline.py'
    if tests.exists():shutil.copy2(tests,out/'code_snapshot/test_kg_pipeline.py')
    save(out/'code_hashes.json',{f.name:sha(f.read_bytes()) for f in sorted((out/'code_snapshot').glob('*.py'))})
    save(out/'analysis.schema.json',ANALYSIS);save(out/'generation.schema.json',GENERATION)
    (out/'analysis_prompt.txt').write_text(ANALYSIS_PROMPT,encoding='utf-8');(out/'generation_prompt.txt').write_text(GENERATION_PROMPT,encoding='utf-8')
    kg=a.project/'knowledge/authored'/DATASET
    save(out/'kg_hashes.json',{str(f.relative_to(kg)):sha(f.read_bytes()) for f in (kg/'graph/nodes.jsonl',kg/'graph/edges.jsonl',kg/'schema/schema.json')})
    private=out/'private';private.mkdir();shutil.copy2(a.inputs,private/'inputs.jsonl')
    try:
        client=Qwen(a.qwen_config,timeout=config['timeout_seconds']);neo=Neo4j(a.credentials)
        catalog=load_catalog(neo,kg,DATASET)
        config['model_id']=client.model;save(out/'config.json',config)
        save(out/'server_models.json',client.models)
        save(out/'preflight.json',{'live_nodes_equal_frozen':True,'live_relationships_equal_frozen':True,'node_count':len(catalog),'concept_count':sum(n['type'] in ('AnalysisConcept','GrammarFeature','Construction') for n in catalog.values()),'read_only':True})
    except Exception as e:
        save(out/'preflight_failure.json',{'error_type':type(e).__name__,'note':'Preflight failed before input experiment. Credentials omitted.'});raise
    save(out/'freeze.json',{'frozen_before_first_input_call':dt.datetime.now(dt.timezone.utc).isoformat(),
      'code_hashes_sha256':sha((out/'code_hashes.json').read_bytes()),'config_sha256':sha((out/'config.json').read_bytes()),'no_post_freeze_tuning':True})
    print('RUN '+str(out),flush=True);started=time.perf_counter();results=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
        futures={pool.submit(execute_record,r,client,neo,catalog,config,out):r['id'] for r in records}
        for f in concurrent.futures.as_completed(futures):
            r=f.result();results.append(r);print(dumps({'done':len(results),'of':len(records),'id':r['id'],'status':r['status'],'references':r.get('reference_count'),'seconds':r['total_seconds']}),flush=True)
    order={r['id']:i for i,r in enumerate(records)};results.sort(key=lambda r:order[r['id']])
    save(private/'results.json',results);m=metrics(results,time.perf_counter()-started);save(out/'metrics.json',m)
    tasks=[{'id':r['id'],'input':r['input_text'],'output':r['output_text'],'condition_hidden_id':sha((out.name+r['id']).encode())[:12],
      'meaning_preserved':None,'dialect_naturalness_1_to_5':None,'dialect_identifiable':None,'evidence_appropriate':None,'comment':None} for r in results]
    save(private/'human_review.json',tasks)
    frozen_hashes=read(out/'code_hashes.json')
    save(out/'postflight.json',{'source_code_unchanged_during_run':all(sha((code/name).read_bytes())==digest for name,digest in frozen_hashes.items() if name!='test_kg_pipeline.py'),
      'input_unchanged':sha(a.inputs.read_bytes())==input_sha,
      'kg_files_unchanged':all(sha((kg/name).read_bytes())==digest for name,digest in read(out/'kg_hashes.json').items())})
    from .report import render_report
    render_report(out)
    save(out/'artifact_hashes.json',{str(f.relative_to(out)):sha(f.read_bytes()) for f in sorted(out.rglob('*')) if f.is_file() and f.name!='artifact_hashes.json'})
    print('COMPLETE '+dumps({'run':str(out),'metrics':m}),flush=True)
if __name__=='__main__':main()
