"""Check the final token-to-governing-root fix on all 80 frozen inputs."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from kg_pipeline.integrated import observe_units
from kg_pipeline.io import read,save,load_jsonl,sha,dumps
HERE=Path(__file__).resolve().parent
RUN_IDS=['20261106T051728566435Z_integrated_grammar_development','20261106T052943610843Z_integrated_grammar_regression']

def main():
    rows=[]
    for run_id in RUN_IDS:
        run=ROOT/'experiments/runs'/run_id
        for source in load_jsonl(run/'private/inputs.jsonl'):
            rd=run/'private/records'/source['id'];rid=source['id']
            if not (rd/'morphology.json').exists():
                rows.append({'run_id':run_id,'id':rid,'status':'missing_morphology'});continue
            before=read(rd/'units.json');after=observe_units(read(rd/'morphology.json'))
            identity=lambda us:[(u['id'],u['word_id'],u['kind'],u['text'],u['span'],u['morphs']) for u in us]
            assert identity(before)==identity(after),'Unexpected target identity change '+rid
            changes=[]
            for a,b in zip(before,after):
                for k in set(a['observed'])|set(b['observed']):
                    if a['observed'].get(k)!=b['observed'].get(k):
                        changes.append({'unit_id':a['id'],'text':a['text'],'kind':a['kind'],'feature':k,
                                        'before':a['observed'].get(k),'after':b['observed'].get(k)})
            save(HERE/'private/observation_replay'/run_id/(rid+'.json'),after)
            rows.append({'run_id':run_id,'id':rid,'status':'replayed','same_unit_identity':True,'changes':changes})
    summary={'planned':80,'replayed':sum(r['status']=='replayed' for r in rows),
             'changed_inputs':sum(bool(r.get('changes')) for r in rows),
             'changed_features':sum(len(r.get('changes',[])) for r in rows),
             'code_sha256':sha((ROOT/'src/kg_pipeline/integrated.py').read_bytes()),
             'model_calls':0,'quality_effect':'not_measured','cases':rows}
    save(HERE/'private/observation_fix_summary.json',summary)
    print(dumps({k:v for k,v in summary.items() if k!='cases'}))

if __name__=='__main__':main()
