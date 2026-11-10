"""Fresh Kiwi observations only. Never fill semantic values from KG conditions."""
import collections
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'local/python')]
from kg_runtime.morphology import Morphology
from kg_pipeline.integrated import IntegratedReader,observe_units

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')

def main():
    examples=read(HERE/'private/claude_examples.json')
    pointer=read(ROOT/'knowledge/authored/semantic_grammar_20261107_separated_r1/latest.json')
    reader=IntegratedReader(read(ROOT/pointer['graph']));morph=Morphology()
    branches={b['id']:(rid,b) for rid,r in reader.rules.items() for b in r['branches']}
    assert {e['branch_id'] for e in examples}==set(branches) and len(examples)==len(branches)
    rows=[]
    for e in examples:
        rid,branch=branches[e['branch_id']];assert rid==e['rule_id']
        for category in ('positive','negative','unknown'):
            case=e[category];text=case['text'];target=case['target']
            units=observe_units(morph.analyze(text));anchors=[]
            spans=[];start=0
            while target and (pos:=text.find(target,start))>=0:
                spans.append([pos,pos+len(target)]);start=pos+1
            # Keep every matching observed unit. No "best" feature fit selection.
            for u in units:
                matched=[s for s in spans if max(s[0],u['span'][0])<min(s[1],u['span'][1])]
                if u['kind'] not in branch['conditions']['unit_kind'] or not matched:continue
                observed={k:v for k,v in u['observed'].items() if k!='predicate_class'}
                mismatches=[{'feature':k,'observed':observed[k],'required':vs} for k,vs in branch['conditions'].items()
                    if k in observed and observed[k] not in (None,'unknown') and observed[k] not in vs]
                unknown=[k for k in branch['conditions'] if k not in observed or observed[k] in (None,'unknown')]
                anchors.append({'unit_id':u['id'],'kind':u['kind'],'construction_text':u['text'],'construction_span':u['span'],
                    'reviewer_target_spans':matched,
                    'morphs':u['morphs'],'observed':observed,'hard_mismatches':mismatches,
                    'needs_semantic_judgment':unknown,'required_relation_roles':reader.rules[rid]['node']['properties'].get('required_relations',[])})
            status='target_string_missing' if not spans else 'target_exists_no_supported_unit' if not anchors else 'observed_conditions_block_all' if all(a['hard_mismatches'] for a in anchors) else 'requires_meaning_and_relations'
            rows.append({'branch_id':e['branch_id'],'rule_id':rid,'category':category,'text':text,'target':target,
               'reviewer_reason':case['reason'],'reviewer_verdict':e['verdict'],'reviewer_issues':e['issues'],
               'status':status,'target_string_occurrences':len(spans),'matching_units':len(anchors),
               'anchors':anchors,'new_qwen_calls':0,'expected_translation':None})
    summary={'branches':len(examples),'sentences':len(rows),'reviewer_verdicts':dict(collections.Counter(e['verdict'] for e in examples)),
       'positive_observation_status':dict(collections.Counter(r['status'] for r in rows if r['category']=='positive')),
       'statuses_by_kind':{k:dict(collections.Counter(r['status'] for r in rows if r['category']==k)) for k in ('positive','negative','unknown')},
       'review_file_sha256':hashlib.sha256((HERE/'private/claude_examples.json').read_bytes()).hexdigest(),
       'qwen_calls':0,'linguistic_gold':False,
       'scope':'Claude 제안 171문장의 실제 Kiwi 형태 관찰. 의미·관계는 KG에서 채우지 않았다. Qwen 분석/번역 검사가 아님.'}
    save(HERE/'private/natural_observations.json',rows);save(HERE/'natural_summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':main()
