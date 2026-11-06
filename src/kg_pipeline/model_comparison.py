"""Sequential generation comparison using immutable, previously observed requests.

No network in freeze/preflight. Existing Qwen transport records raw responses;
only explicitly executed runs access environment credentials. No analysis calls,
answer injection, text repair, silent option fallback, or automatic retry.
"""
import argparse
import collections
import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil
import time
import urllib.request

from .io import Qwen, dumps, load_jsonl, read, save, sha
from .validation import validate_schema

ROOT = Path(__file__).resolve().parents[2]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(value):
    return sha(dumps(value).encode('utf8'))


def stamp():
    return dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')


def check_packet(packet, text):
    require(packet['text']==text, 'Packet/input mismatch')
    seen=set()
    for a in packet['actions']:
        require(a['target_id'] not in seen, 'Duplicate action target')
        seen.add(a['target_id'])
        span=a['span']
        require(len(span)==2 and all(type(v) is int for v in span), 'Invalid target span')
        start,end=span
        require(0<=start<end<=len(text) and text[start:end]==a['target'], 'Target span mismatch')


def freeze(source, arm, destination):
    """Import all inputs from the existing easy-pilot N/T/J saved requests."""
    source, destination = Path(source).resolve(), Path(destination).resolve()
    require(arm in ('N', 'T', 'J'), 'Supported importer: easy-pilot N/T/J only')
    require(not destination.exists(), 'Never overwrite a frozen bundle')
    rows = load_jsonl(source/'private/inputs.jsonl')
    require(rows and len({r['id'] for r in rows}) == len(rows), 'Empty/duplicate IDs')
    evidence, items = {}, []
    config = read(source/'config.json')
    require(config.get('arms') == ['N', 'T', 'J'], 'Not an easy-pilot source')
    graph = source/'private/graph.json'
    for row in rows:
        require(re.fullmatch(r'[A-Za-z0-9_-]+', row['id']), 'Unsafe input ID')
        base = source/'private/records'/row['id']
        rp = base/arm/'generation_call/request.json'
        request = read(rp)  # Missing request is an error, never silently drop input.
        require([m['role'] for m in request['messages']] == ['system', 'user'], 'Unexpected messages')
        wire = request['messages'][1]['content']
        common = json.loads(wire.split('\n\n문법 참고 정보:\n', 1)[0])
        require(common['text'] == row['text'], 'Input/request mismatch')
        require('expected_surface' not in wire, 'Diagnostic answer field in request')
        analysis_paths = sorted((base/'analysis').rglob('*.json'))
        require(analysis_paths, 'Missing frozen analysis evidence')
        paths = [rp, base/'packet.json', base/'traces.json', *analysis_paths]
        for p in paths:
            evidence[p.relative_to(source).as_posix()] = sha(p.read_bytes())
        packet = read(base/'packet.json')
        check_packet(packet,row['text'])
        items.append({'id':row['id'], 'text':row['text'], 'messages':request['messages'],
                      'schema':request['response_format']['json_schema']['schema'],
                      'request_name':request['response_format']['json_schema']['name'],
                      'analysis_sha256':digest(common['analysis']),
                      'supported_targets':len(packet['actions']),
                      'known_delivery_defect':row.get('known_delivery_defect', False)})
    evidence['config.json'] = sha((source/'config.json').read_bytes())
    evidence['private/graph.json'] = sha(graph.read_bytes())
    evidence['private/inputs.jsonl'] = sha((source/'private/inputs.jsonl').read_bytes())
    bundle = {'format':'fixed_generation_v1', 'source_run':source.name, 'source_arm':arm,
              'role':'development_diagnostic_not_independent_evaluation',
              'selection':'all_source_inputs_no_action_filter', 'items':items,
              'source_files':evidence, 'analysis_model':config.get('model_id'),
              'kg_sha256':sha(graph.read_bytes()), 'knowledge_policy':'unchanged_saved_request'}
    destination.mkdir(parents=True)
    for relative in evidence:
        target = destination/'evidence'/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source/relative, target)
    save(destination/'bundle.json', bundle)
    save(destination/'manifest.json', {'bundle_sha256':sha((destination/'bundle.json').read_bytes()),
                                      'source_files':evidence})
    return {'inputs':len(items), 'bundle':str(destination), 'network_calls':0}


def validate_profile(profile):
    fields = {'name','model','base_url_env','api_key_env','temperature','top_p','max_tokens',
              'seed','timeout_seconds','chat_template_kwargs','max_failures','repeats'}
    require(set(profile) == fields, 'Unexpected/missing profile fields')
    require(re.fullmatch(r'[A-Za-z0-9_-]+', profile['name']), 'Unsafe profile name')
    require(isinstance(profile['model'],str) and profile['model'].strip(), 'Explicit model required')
    for k in ('base_url_env','api_key_env'):
        require(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',profile[k]), 'Use environment variable names only')
    for k in ('max_tokens','timeout_seconds','max_failures','repeats'):
        require(type(profile[k]) is int and profile[k]>0, 'Invalid '+k)
    require(type(profile['seed']) is int or profile['seed'] is None, 'Invalid seed')
    require(type(profile['temperature']) in (int,float) and 0 <= profile['temperature'] <= 2, 'Invalid temperature')
    require(type(profile['top_p']) in (int,float) and 0 < profile['top_p'] <= 1, 'Invalid top_p')
    kwargs=profile['chat_template_kwargs']
    require(kwargs is None or (isinstance(kwargs,dict) and set(kwargs)<= {'enable_thinking'}
            and all(type(v) is bool for v in kwargs.values())), 'Unsupported template options')


def preflight(bundle_dir, profile):
    validate_profile(profile)
    folder=Path(bundle_dir)
    manifest=read(folder/'manifest.json'); bundle=read(folder/'bundle.json')
    require(sha((folder/'bundle.json').read_bytes())==manifest['bundle_sha256'], 'Bundle hash mismatch')
    require(bundle['source_files']==manifest['source_files'], 'Manifest mismatch')
    for relative, expected in manifest['source_files'].items():
        p=(folder/'evidence'/relative).resolve()
        require(p.is_relative_to((folder/'evidence').resolve()), 'Unsafe evidence path')
        require(sha(p.read_bytes())==expected, 'Evidence hash mismatch: '+relative)
    ids=[i['id'] for i in bundle['items']]
    require(ids and len(ids)==len(set(ids)), 'Invalid IDs')
    require(all(re.fullmatch(r'[A-Za-z0-9_-]+',i) for i in ids), 'Unsafe IDs')
    rows=load_jsonl(folder/'evidence/private/inputs.jsonl')
    require([(i['id'],i['text']) for i in bundle['items']]==[(r['id'],r['text']) for r in rows], 'Input set changed')
    for item in bundle['items']:
        base=folder/'evidence/private/records'/item['id']
        req=read(base/bundle['source_arm']/'generation_call/request.json')
        require(item['messages']==req['messages'] and item['schema']==req['response_format']['json_schema']['schema']
                and item['request_name']==req['response_format']['json_schema']['name'], 'Frozen request mismatch')
        check_packet(read(base/'packet.json'),item['text'])
    return bundle, {'inputs':len(ids), 'planned_generation_calls':len(ids)*profile['repeats'],
                    'analysis_calls':0, 'network_calls':0, 'bundle_sha256':manifest['bundle_sha256'],
                    'profile_sha256':digest(profile), 'endpoint_compatibility':'not_tested',
                    'selection':bundle['selection'], 'quality':'not_evaluated'}


def comparison_protocol(bundle_dir, profiles):
    """Bind planned models to one input bundle and common generation settings."""
    require(profiles, 'At least one planned model required')
    require(len({p['name'] for p in profiles})==len(profiles), 'Duplicate profile names')
    fixed_keys=('temperature','top_p','max_tokens','seed','repeats')
    fixed={k:profiles[0][k] for k in fixed_keys}
    for p in profiles:
        preflight(bundle_dir,p)
        require({k:p[k] for k in fixed_keys}==fixed, 'Generation settings differ; use a separate experiment')
        if 'qwen' in p['model'].lower():
            require(p['chat_template_kwargs']=={'enable_thinking':False}, 'Qwen baseline must explicitly disable thinking')
    bundle,checks=preflight(bundle_dir,profiles[0])
    return {'format':'model_comparison_protocol_v1','bundle_sha256':checks['bundle_sha256'],
            'source_arm':bundle['source_arm'],'fixed_settings':fixed,'profiles':profiles,
            'profile_specific_options':{p['name']:p['chat_template_kwargs'] for p in profiles},
            'comparison_scope':'generation_models_with_declared_template_options',
            'deadline_policy':'no_new_network_request_after_deadline_not_hard_completion_deadline'}


class ProfiledClient(Qwen):
    def __init__(self, profile):
        validate_profile(profile)
        self.profile=profile
        self.url=os.environ[profile['base_url_env']].rstrip('/')
        self.key=os.environ[profile['api_key_env']]
        require(self.url.startswith(('http://','https://')), 'Invalid endpoint')
        self.model=profile['model']; self.timeout=profile['timeout_seconds']

    def check_model(self):
        req=urllib.request.Request(self.url+'/models',headers={'Authorization':'Bearer '+self.key})
        with urllib.request.urlopen(req,timeout=self.timeout) as response:
            data=json.load(response)
        ids=[x['id'] for x in data['data']]
        require(self.model in ids, 'Explicit model not served; no fallback')
        return {'available_model_ids':ids, 'requested_model':self.model}

    def build_request(self, stage, prompt, user, schema, max_tokens, seed):
        p=self.profile
        request={'model':self.model,'messages':[{'role':'system','content':prompt}, {'role':'user','content':user}],
                 'temperature':p['temperature'],'top_p':p['top_p'],'max_tokens':max_tokens,
                 'response_format':{'type':'json_schema','json_schema':{'name':stage,'strict':True,'schema':schema}}}
        if seed is not None: request['seed']=seed
        if p['chat_template_kwargs'] is not None: request['chat_template_kwargs']=p['chat_template_kwargs']
        return request


def summarize(results, planned):
    metrics={'planned_generation_calls':planned,'attempted_generation_calls':len(results),
             'analysis_calls':0,'statuses':dict(collections.Counter(r['status'] for r in results)),
             'naturalness':'not_evaluated','usage':{}}
    for key in ('prompt_tokens','completion_tokens','total_tokens'):
        values=[(r.get('usage') or {}).get(key) for r in results]
        numeric=[v for v in values if isinstance(v,(int,float)) and not isinstance(v,bool)]
        metrics['usage'][key]={'observed_sum':sum(numeric) if numeric else None,
                              'missing_calls':len(values)-len(numeric)}
    return metrics


def execute(bundle_dir, profile, deadline, max_calls, protocol):
    started=time.perf_counter()
    bundle, checks=preflight(bundle_dir,profile)
    require(comparison_protocol(bundle_dir,protocol['profiles'])==protocol, 'Comparison protocol changed')
    require(profile in protocol['profiles'], 'Profile not declared in comparison protocol')
    end=dt.datetime.fromisoformat(deadline)
    require(end.tzinfo is not None and end>dt.datetime.now(dt.timezone.utc), 'Future timezone-aware deadline required')
    require(max_calls>=checks['planned_generation_calls'], 'Budget must cover all planned inputs/repeats')
    require(not profile['model'].startswith('REPLACE_'), 'Replace example model before execution')
    # Credentials are accessed only after offline validation succeeds.
    client=ProfiledClient(profile)
    out=ROOT/'experiments/runs'/(stamp()+'_model_generation_'+profile['name'])
    (out/'private').mkdir(parents=True,exist_ok=False)
    (out/'private/inputs.jsonl').write_text(''.join(dumps({'id':i['id'],'text':i['text']})+'\n' for i in bundle['items']),encoding='utf8')
    save(out/'config.json', {'phase':'development','dataset_role':bundle['role'],
          'metric_contract':'fixed_generation_v1','input_count':len(bundle['items']),
          'planned_records':checks['planned_generation_calls'],
          'input_sha256':sha((out/'private/inputs.jsonl').read_bytes()),
          'model_id':profile['model'],'kg_dataset':bundle['kg_sha256'],
          'source_run':bundle['source_run'],'source_arm':bundle['source_arm'],'profile':profile,
          'bundle_sha256':checks['bundle_sha256'],
          'analysis_model':bundle['analysis_model'],'analysis_policy':'frozen_source_analysis',
          'deadline':deadline,'deadline_policy':protocol['deadline_policy'],
          'protocol_sha256':digest(protocol),'max_calls':max_calls,'automatic_retries':0,'final_writer':'model_raw_output'})
    save(out/'preflight.json',checks);save(out/'private/bundle.json',bundle)
    save(out/'comparison_protocol.json',protocol)
    shutil.copytree(bundle_dir,out/'private/frozen_bundle')
    code_hashes={}
    for p in [Path(__file__),ROOT/'src/kg_pipeline/io.py',ROOT/'src/kg_pipeline/validation.py']:
        rel=p.relative_to(ROOT); dest=out/'code_snapshot'/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(p,dest);code_hashes[rel.as_posix()]=sha(p.read_bytes())
    save(out/'code_hashes.json',code_hashes)
    from .runner import register_run
    register_run(ROOT,out)
    results=[]; failures=0; stop=None; server_checks=0
    try:
        if dt.datetime.now(dt.timezone.utc)>=end:
            stop='deadline'
            raise TimeoutError('Deadline before server check')
        server_checks+=1
        save(out/'server_models.json',client.check_model())
        for repeat in range(profile['repeats']):
            for item in bundle['items']:
                if dt.datetime.now(dt.timezone.utc)>=end: stop='deadline';break
                if failures>=profile['max_failures']: stop='failure_limit';break
                folder=out/'private/records'/item['id']/str(repeat)
                result={'id':item['id']+'__'+str(repeat),'source_id':item['id'],'repeat':repeat,
                        'input_text':item['text'],'output_text':None,'supported_targets':item['supported_targets'],
                        'failure_reasons':[]}
                try:
                    value=client.call(item['request_name'],item['messages'][0]['content'],item['messages'][1]['content'],
                        item['schema'],folder,profile['max_tokens'],None if profile['seed'] is None else profile['seed']+repeat)
                    validate_schema(value,item['schema'])
                    result.update(output_text=value['output_text'],model_status=value.get('status'))
                    result['status']=('empty_output' if not value['output_text'].strip() else
                        'model_review_requested' if value.get('status')=='needs_review' else 'generated_requires_human_review')
                    result['unchanged']=value['output_text']==item['text']
                    if result['status']=='empty_output':result['failure_reasons'].append('empty_output')
                except Exception as exc:
                    result.update(status='generation_failed',error_type=type(exc).__name__)
                    result['failure_reasons'].append('generation_failed')
                meta=read(folder/'meta.json') if (folder/'meta.json').exists() else {}
                result.update(usage=meta.get('usage'),seconds=meta.get('seconds'),returned_model=meta.get('model'))
                if result['status']!='generation_failed' and result['returned_model']!=profile['model']:
                    result['status']='model_identity_mismatch'
                    result['failure_reasons'].append('model_identity_mismatch')
                if result['failure_reasons']:failures+=1
                save(folder/'result.json',result);results.append(result)
                save(out/'private/results.json',results)
                print(dumps({'done':len(results),'total':checks['planned_generation_calls'],'id':item['id'],'status':result['status']}),flush=True)
            if stop:break
    except Exception as exc:
        if stop is None:
            stop='setup_or_run_failure';save(out/'failure.json',{'error_type':type(exc).__name__})
    finally:
        save(out/'private/results.json',results)
        metrics=summarize(results,checks['planned_generation_calls']);metrics['stop_reason']=stop
        metrics.update(records=len(results), valid_output_records=sum(r['status'] in ('generated_requires_human_review','model_review_requested') for r in results),
                       api_attempts=len(results), generation_calls=len(results),
                       server_check_calls=server_checks,
                       wall_seconds=round(time.perf_counter()-started,4),
                       unattempted_records=checks['planned_generation_calls']-len(results),
                       execution_state='failed' if stop=='setup_or_run_failure' else 'interrupted' if stop else 'completed',
                       finished_after_deadline=dt.datetime.now(dt.timezone.utc)>end,
                       cost_scope='generation_only_frozen_analysis_cost_excluded')
        metrics['cli_exit_code']=2 if stop or failures else 0
        if stop and stop!='setup_or_run_failure':save(out/'interruption.json',{'reason':stop})
        save(out/'metrics.json',metrics)
        evidence_ok=True
        try:preflight(out/'private/frozen_bundle',profile)
        except Exception:evidence_ok=False
        save(out/'postflight.json',{'code_unchanged':all(sha((ROOT/p).read_bytes())==h for p,h in code_hashes.items()),
                                   'archived_evidence_unchanged':evidence_ok,
                                   'bundle_unchanged':sha((Path(bundle_dir)/'bundle.json').read_bytes())==checks['bundle_sha256']})
        save(out/'artifact_hashes.json',{p.relative_to(out).as_posix():sha(p.read_bytes()) for p in out.rglob('*') if p.is_file()})
        register_run(ROOT,out)
    return {'directory':str(out),**metrics}


def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='command',required=True)
    f=sub.add_parser('freeze');f.add_argument('--source',required=True);f.add_argument('--arm',choices=['N','T','J'],required=True);f.add_argument('--out',required=True)
    c=sub.add_parser('protocol');c.add_argument('--bundle',required=True);c.add_argument('--profiles',nargs='+',required=True);c.add_argument('--out',required=True)
    for name in ('preflight','run'):
        s=sub.add_parser(name);s.add_argument('--bundle',required=True);s.add_argument('--profile',required=True)
        if name=='run':
            s.add_argument('--protocol',required=True)
            s.add_argument('--execute',action='store_true',required=True);s.add_argument('--deadline',required=True);s.add_argument('--max-calls',type=int,required=True)
    a=p.parse_args()
    if a.command=='freeze':result=freeze(a.source,a.arm,a.out)
    elif a.command=='protocol':
        require(not Path(a.out).exists(),'Never overwrite a comparison protocol')
        result=comparison_protocol(a.bundle,[read(p) for p in a.profiles]);save(a.out,result)
    elif a.command=='preflight':result=preflight(a.bundle,read(a.profile))[1]
    else:result=execute(a.bundle,read(a.profile),a.deadline,a.max_calls,read(a.protocol))
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if a.command=='run' and result['cli_exit_code']:raise SystemExit(result['cli_exit_code'])


if __name__=='__main__':main()
