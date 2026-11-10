"""Compute trace/control checks, never infer dialect quality from changed text."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from kg_pipeline.io import read,save,sha,load_jsonl,dumps

def assess(run):
    inputs=load_jsonl(run/'private/inputs.jsonl');results=read(run/'private/results.json');index={(r['source_input_id'],r['policy']):r for r in results}
    policies=read(run/'config.json')['policies']
    summary={'run':run.name,'policies':policies,'checks':{},'cases':[],'connection_denominator':sum('construction_act' in r.get('check',{}) for r in inputs)}
    control_pairs=[];wire_no_check=[];writer_matches=[];corpus=[]
    for inp in inputs:
        case={'id':inp['id'],'source':inp['text'],'expected':inp.get('check',{}),'policies':{}}
        controls=[]
        for policy in policies:
            r=index.get((inp['id'],policy))
            if r is None:continue
            rd=run/'private/records'/r['id'];b=read(rd/'bound_analysis.json') if (rd/'bound_analysis.json').exists() else []
            selected=read(rd/'selected_knowledge.json') if (rd/'selected_knowledge.json').exists() else []
            draft=read(rd/'writer/parsed.json') if (rd/'writer/parsed.json').exists() else {}
            expected=inp.get('check',{});cx=[u for u in b if u['kind']=='construction']
            ok=None
            if expected.get('construction_act'):
                ok=bool(cx) and all(u['features'].get('speech_act')==expected['construction_act'] and
                    all(u.get('relations',{}).get(role) for role in expected.get('required_relations',[])) and not u.get('relation_issues') for u in cx)
            p={'complete':r.get('pipeline_completed',False),'output':r.get('output_text'),'connection_match':ok,
                'constructions':[{'text':u['text'],'act':u['features'].get('speech_act'),'auxiliary_kind':u['features'].get('auxiliary_kind'),
                    'relations':u.get('relations',{}),'issues':u.get('relation_issues',[])} for u in cx],
                'delivered':[{'id':a['rule_id'],'target':a['source_text'],'instruction':a['instruction'],
                    'source_form_literal':a.get('source_form_literal'),'applied':a['action_id'] in draft.get('used_action_ids',[]),
                    'reason':next((d['reason'] for d in draft.get('decisions',[]) if d['action_id']==a['action_id']),None)} for a in selected],
                'analysis_objections':[{'text':u['text'],'issues':u.get('analysis_issues',[]),'objections':u.get('structural_objections',[])} for u in b if u.get('analysis_issues') or u.get('structural_objections')]}
            if (rd/'prepared_structure.json').exists():
                st=read(rd/'prepared_structure.json');p['missing_coverage']=st.get('missing_coverage',[])
            case['policies'][policy]=p
            if (rd/'control_input.json').exists():controls.append(read(rd/'control_input.json'))
            if r.get('pipeline_completed'):writer_matches.append(draft.get('output_text')==r.get('output_text'))
            for request in rd.rglob('request.json'):
                q=read(request);payload=json.loads(q['messages'][1]['content'])
                wire_no_check.append('check' not in payload and 'construction_act' not in dumps(payload))
        if len(controls)==2:control_pairs.append(controls[0]==controls[1])
        summary['cases'].append(case)
    for request in (run/'private/shared').rglob('request.json'):
        q=read(request);payload=json.loads(q['messages'][1]['content']);wire_no_check.append('check' not in payload and 'construction_act' not in dumps(payload))
    summary['checks']={'all_available_control_pairs_identical':all(control_pairs),'checked_pairs':len(control_pairs),
        'raw_writer_equals_final_for_completed':all(writer_matches),'checked_outputs':len(writer_matches),
        'no_local_expectation_fields_in_requests':all(wire_no_check),'checked_requests':len(wire_no_check)}
    summary['connection_matches']={p:sum(c['policies'].get(p,{}).get('connection_match') is True for c in summary['cases']) for p in policies}
    summary['not_quality_metrics']=True
    save(HERE/'private'/('assessment_'+run.name+'.json'),summary)
    return summary

if __name__=='__main__':
    run=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/read(HERE/'latest_development.json')['run']
    result=assess(run);print(dumps({k:v for k,v in result.items() if k!='cases'}))
