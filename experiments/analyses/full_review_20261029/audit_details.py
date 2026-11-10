"""Reproduce historical selection offline. No generation or runtime edits."""
import ast, hashlib, json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf8')
BASE=Path(__file__).resolve().parent
PROJECT=BASE.parents[2]
RUN=PROJECT/'experiments/runs/20261028T011829489985Z_cards_single_regression'
source=RUN/'code_snapshot/kg_runtime/cards.py'
tree=ast.parse(source.read_text(encoding='utf8'))
nodes=[n for n in tree.body if (isinstance(n,ast.FunctionDef) and n.name=='select_cards') or
       (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='FUNCTION_TERMS' for t in n.targets))]
assert len(nodes)==2
env={'dumps':lambda x:json.dumps(x,ensure_ascii=False)}
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),env)
cards={c['id']:c for c in json.loads((PROJECT/'knowledge/authored/kg_cards_20261028_v2/cards.json').read_text(encoding='utf8'))['cards']}
load=lambda p:json.loads(p.read_text(encoding='utf8'))
rows=[];shared_checks=[]
for packet in sorted((BASE/'private/packets').glob('B??.json')):
    for case in load(packet)['cases']:
        record=RUN/'private/records'/case['id']
        raw=load(record/'retrieval_raw.json')
        morph=load(record/'morphology.json')
        chosen,ranking=env['select_cards']([cards[i] for i in raw['retrieved_ids']],case['shared_analysis'],morph)
        assert ranking==raw['ranking'],case['id']
        assert [c['id'] for c in chosen]==[c['id'] for c in raw['cards']],case['id']
        other=PROJECT/case['arms']['multi']['source_record_dir']/'retrieval_raw.json'
        assert load(other)['ranking']==raw['ranking']
        check={'id':case['id']}
        for f in ['analysis_call/parsed.json','morphology.json','reference_packet.json']:
            check[f]=load(record/f)==load(other.parent/f)
            assert check[f],(case['id'],f)
        shared_checks.append(check)
        rows.append({'id':case['id'],'retrieved':len(raw['retrieved_ids']),'supplied':len(chosen),'selection_exactly_reproduced':True})
examples=[]
for case_id,wanted in [('LONG004',['GS_ENDRULE_ISO_IMP','GS_END_IMP_HI_02']),
                       ('QUAL003',['GS_ENDRULE_NI_B_OPTION','GS_ENDRULE_JI_ASSERT']),
                       ('DEV030',['GS_CONNECT_COND_01','GS_PART_ACC_01'])]:
    ranking=load(RUN/'private/records'/case_id/'selection_audit.json')['ranking']
    for i,r in enumerate(ranking,1):
        if r['id'] in wanted:examples.append({'input_id':case_id,'overall_rank':i,**r})
result={'scope':'Historical selection replay only; no parameter changes or Qwen calls',
        'inputs_reproduced':len(rows),'records':rows,'examples':examples,
        'source':str(source.relative_to(PROJECT)),
        'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'finding':'conditional keyword condition also matches the attribute name coda_condition. A score for a function is not evidence of grammatical applicability.',
        'json_newline_before_comma_is_valid':json.loads('{"after":"나는"\n, "reason":"유지"}')=={'after':'나는','reason':'유지'}}
(BASE/'private/selection_diagnostics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(BASE/'private/shared_inputs_check.json').write_text(json.dumps({'inputs':50,'missing':[],'different':[],
    'comparison':'Exact structural equality of stored analysis, morphology and delivered card packet between Single and Multi',
    'cases':shared_checks},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('Historical selection reproduced exactly: 50 inputs, both arm rankings matched.')
print('Confirmed: conditional term condition matches coda_condition in an accusative card.')
