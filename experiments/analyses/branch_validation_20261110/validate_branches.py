"""Offline contract replay: not a natural-language accuracy evaluation."""
import collections
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from kg_pipeline.integrated import IntegratedReader
from kg_pipeline.delivery_normalization import normalize_delivery,EXACT_REPLACEMENTS,VERSION

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def states(query):
    return {x['rule_id']:{'state':x['state'],'missing_relations':x['missing_relations'],
        'branches':[(b['id'],b['state'],b['checks']) for b in x['branches']]}
        for key in ('eligible','unresolved','rejected') for x in query[key]}

def check_delivery(reader,rid,p):
    """Nonempty checks for every rule, with explicit form count and fields."""
    props=reader.rules[rid]['node']['properties'];checks={}
    expected=[]
    for key in ('limitations','limits'):
        value=props.get(key)
        if value not in (None,'',[]) and value not in expected:expected.append(copy.deepcopy(value))
    limits=expected[0] if len(expected)==1 else expected if expected else ''
    normalized=normalize_delivery({'rule_id':rid,'limitations':limits})['limitations']
    checks['limitations']=p.get('limitations')==normalized
    checks['instruction']=p.get('instruction')==props.get('instruction',props.get('meaning',props.get('summary','')))
    checks['preserve']=p.get('preserve')==props.get('preserve',[])
    checks['rule_type']=p.get('rule_type')==props.get('rule_type','conversion')
    edges=reader.links(rid,'REALIZES');forms=p.get('forms',[])
    checks['form_count']=len(edges)==len(forms)
    for i,e in enumerate(edges):
        fp=reader.nodes[e['target']]['properties'];form=forms[i] if i<len(forms) else {}
        for key in ('form','allomorphs','includes_copula','unit','operation','surface_postcondition'):
            if key in fp:checks[f'forms/{i}/{key}']=form.get(key)==fp[key]
        if 'composition' in fp:
            checks[f'forms/{i}/composition']=form.get('composition')==fp['composition'] or (
                reader.graph_storage_format=='execution_graph_with_external_audit_v1' and
                fp['composition']==p.get('instruction') and 'composition' not in form)
    for key in ('target','generation_operation','surface_postcondition','operation'):
        if key in props:checks[key]=p.get(key)==props[key]
    return checks

def main():
    pointer=read(ROOT/'knowledge/authored/semantic_grammar_20261107_separated_r1/latest.json')
    gp=ROOT/pointer['graph'];graph=read(gp);reader=IntegratedReader(graph)
    spec=importlib.util.spec_from_file_location('kg_pipeline.before_integrated',HERE/'private/before/integrated.py')
    oldmod=importlib.util.module_from_spec(spec);spec.loader.exec_module(oldmod)
    old=oldmod.IntegratedReader(graph)
    normalization_matches={rid:{text:reader.rules[rid]['node']['properties'].get('limitations','').count(text) for text in changes}
                           for rid,changes in EXACT_REPLACEMENTS.items()}
    assert all(count==1 for changes in normalization_matches.values() for count in changes.values()),'Normalization no longer matches pinned graph'
    path_checks=[]
    for rid,r in reader.rules.items():
        scope_ids=[e['id'] for e in reader.links(r['family'],'SUPPORTED_IN')]
        for b,previous in zip(r['branches'],old.rules[rid]['branches']):
            assert b['conditions']==previous['conditions']
            assert [i for i in b['path_edge_ids'] if i not in scope_ids]==previous['path_edge_ids']
            assert all(i in b['path_edge_ids'] for i in scope_ids)
            path_checks.append(b['id'])
    cases=ROOT/'experiments/analyses/kg_understanding_audit_20261107/private/20261107T031711223906Z/reader_contract_cases.jsonl'
    rows=[];payloads={};branch_payloads={};coverage=collections.defaultdict(collections.Counter)
    for line in cases.read_text(encoding='utf-8').splitlines():
        c=json.loads(line);f=c['features'];rid=c['rule_id']
        required=reader.rules[rid]['node']['properties'].get('required_relations',[])
        u={'id':c['case_id'],'kind':f['unit_kind'],'span':[0,1],'text':'검','morphs':[],
           'relations':{k:['synthetic_target'] for k in required if k!=c.get('missing_relation')}}
        q=reader.query(u,f);before=old.query(u,f);current=states(q).get(rid)
        state=current['state'] if current else 'not_dispatched_for_unit_kind'
        expected=c['expected_contract_state']
        row={'case_id':c['case_id'],'rule_id':rid,'branch_id':c['target_branch_id'],'mode':c['mode'],
             'expected':expected,'actual':state,'passed':state==expected,'decisions_unchanged':states(q)==states(before)}
        rows.append(row);coverage[c['target_branch_id']][c['mode']]+=1
        if state=='eligible' and c['target_branch_id'] not in branch_payloads:
            hit=next(h for h in q['eligible'] if h['rule_id']==rid)
            branch_payloads[c['target_branch_id']]=reader.payload(u,hit)
        if rid not in payloads and state=='eligible':
            hit=next(h for h in q['eligible'] if h['rule_id']==rid)
            oldhit=next(h for h in before['eligible'] if h['rule_id']==rid)
            payloads[rid]={'before':old.payload(u,oldhit),'after':reader.payload(u,hit)}
    allbranches={b['id'] for r in reader.rules.values() for b in r['branches']}
    source_checks=[]
    for rid,pair in payloads.items():
        props=reader.rules[rid]['node']['properties'];p=pair['after']
        checks=check_delivery(reader,rid,p)
        source_checks.append({'rule_id':rid,'delivery_fields_pass':all(checks.values()),'field_count':len(checks),'checks':checks,'changed':pair['before']!=pair['after']})
    summary={'rules':len(reader.rules),'branches':len(allbranches),'covered_branches':len(coverage),
       'logic_cases_reused':len(rows),'logic_passed':sum(r['passed'] for r in rows),
       'decisions_unchanged':all(r['decisions_unchanged'] for r in rows),
       'delivery_rules_checked':len(source_checks),'delivery_fields_passed':sum(r['delivery_fields_pass'] for r in source_checks),
       'payload_changed_rules':sum(r['changed'] for r in source_checks),
       'delivery_fields_checked':sum(r['field_count'] for r in source_checks),
       'branch_payloads':len(branch_payloads),
       'unit_dispatch_cases':sum(r['expected']=='not_dispatched_for_unit_kind' for r in rows),
       'branch_evaluation_cases':sum(r['expected']!='not_dispatched_for_unit_kind' for r in rows),
       'uncovered_branches':sorted(allbranches-set(coverage)),
       'modes':dict(collections.Counter(r['mode'] for r in rows)),
       'graph_sha256':hashlib.sha256(gp.read_bytes()).hexdigest(),
       'code_sha256':hashlib.sha256((ROOT/'src/kg_pipeline/integrated.py').read_bytes()).hexdigest(),
       'normalization_version':VERSION,
       'code_hashes':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in [
           'src/kg_pipeline/integrated.py','src/kg_pipeline/delivery_normalization.py',
           'experiments/analyses/branch_validation_20261110/validate_branches.py',
           'experiments/analyses/branch_validation_20261110/private/before/integrated.py']},
       'path_checks':len(path_checks),'normalization_exact_matches':normalization_matches,
       'fixtures_sha256':hashlib.sha256(cases.read_bytes()).hexdigest(),
       'qwen_calls':0,'natural_language_accuracy':None,
       'warning':'기대값은 기존 KG 명세의 논리값이다. 문법 지식의 타당성과 자연스러운 번역을 인증하지 않는다.'}
    save(HERE/'private/logic_results.json',rows);save(HERE/'private/delivery_comparison.json',payloads)
    save(HERE/'private/delivery_checks.json',source_checks);save(HERE/'private/branch_coverage.json',coverage)
    save(HERE/'private/branch_payloads.json',branch_payloads)
    save(HERE/'summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False))
    assert not summary['uncovered_branches'] and summary['decisions_unchanged']
    assert summary['logic_passed']==len(rows) and summary['delivery_fields_passed']==len(source_checks)

if __name__=='__main__':main()
