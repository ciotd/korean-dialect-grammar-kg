"""Offline trace and version checks; never call a model or repair an output."""
import json, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'local/python')]
from kg_pipeline.io import read,save,sha
from kg_pipeline.kiwi_default import scope_contract,validate_scope,frozen_clauses
from kg_pipeline.validation import validate_schema
from kg_pipeline.multi_agent import check_writer

def verify(run):
    old=ROOT/'experiments/runs/20261107T085310855815Z_kiwi_default_development'
    current=read(run/'config.json');prior=read(old/'config.json')
    conditions=['model_id','seed','temperature','top_p','enable_thinking','graph_sha256','knowledge_character_budget']
    same={k:current[k]==prior[k] for k in conditions}
    same['focused_prompts']=({k:v for k,v in current['prompt_sha256'].items() if k.startswith('kiwi_focused/')}==
                             {k:v for k,v in prior['prompt_sha256'].items() if k.startswith('kiwi_focused/')})
    same['code_hashes']=read(run/'code_hashes.json')==read(old/'code_hashes.json')
    rows=[json.loads(s) for s in (run/'private/inputs.jsonl').read_text(encoding='utf8').splitlines() if s.strip()]
    results=read(run/'private/results.json');by={r['source_input_id']:r for r in results}
    failed=[]
    for row in rows:
        r=by.get(row['id'])
        if not r or r.get('pipeline_completed'):continue
        diagnosis={'id':row['id'],'stage':r.get('last_stage'),'type':r.get('error_type'),'offline_replay_only':True}
        if r.get('last_stage')=='shared_scope':
            p=run/'private/shared'/row['id']/'scope/parsed.json'
            if p.exists():
                try:
                    x=read(p);validate_schema(x,scope_contract(row['text']));clauses=frozen_clauses(row['text'],x);validate_scope(row['text'],clauses)
                    diagnosis['scope_contract']='passed; failure may be in later structure preparation'
                except Exception as exc:diagnosis['reproduced_error']=str(exc)
        else:
            p=run/'private/records'/(row['id']+'_kiwi_focused')
            diagnosis['saved_failure_files']=[f.relative_to(run).as_posix() for f in p.rglob('*failure*') if f.is_file()]
            if r.get('last_stage')=='writer_validation':
                try:check_writer(read(p/'writer/parsed.json'),read(p/'selected_knowledge.json'),read(p/'prepared_structure.json')['clauses'])
                except Exception as exc:diagnosis['reproduced_error']=str(exc)
        failed.append(diagnosis)
    manifest=read(run/'artifact_hashes.json')
    bad=[p for p,h in manifest.items() if not (run/p).exists() or sha((run/p).read_bytes())!=h]
    writer=[]
    for r in results:
        if r.get('pipeline_completed'):
            response=read(run/'private/records'/r['id']/'writer/response.json')
            # Transport stores the native OpenAI response body.
            raw=json.loads(response['choices'][0]['message']['content'])
            writer.append({'id':r['source_input_id'],'native_response_equals_final':raw['output_text']==r['output_text']})
    value={'run':run.name,'same_as_latest_development':same,'prior_scope_difference':'This run newly calls scope for all inputs; prior comparison replayed scope.',
      'unique_inputs':len({r['id'] for r in rows}),'attempted':len(by),'planned':len(rows),
      'missing_input_ids':[r['id'] for r in rows if r['id'] not in by],
      'unexpected_input_ids':sorted(set(by)-{r['id'] for r in rows}),
      'frozen_dataset_identical':sha((run/'private/inputs.jsonl').read_bytes())==sha((ROOT/'data/derived_private/standard_inputs_50_20261029_v2/inputs.jsonl').read_bytes()),
      'postflight':read(run/'postflight.json'),'artifact_count':len(manifest),'artifact_mismatches':bad,
      'native_writer_checks':writer,'failed_case_diagnoses':failed,'quality_accuracy':None}
    save(HERE/'private/verification.json',value)
    print(json.dumps({k:v for k,v in value.items() if k!='native_writer_checks'},ensure_ascii=False))
    return value

if __name__=='__main__':verify(Path(sys.argv[1]).resolve())
