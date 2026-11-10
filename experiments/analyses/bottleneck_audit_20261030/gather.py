"""Read saved evidence only. No model, database writes, or pipeline execution."""
import hashlib,importlib.util,json,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2];P=BASE/'private';P.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'src'))
from research_management.work import WorkStore
HASHES={}
def read(p):
    b=p.read_bytes();HASHES[str(p.relative_to(ROOT))]=hashlib.sha256(b).hexdigest();return json.loads(b)
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    active=read(ROOT/'experiments/analyses/scoped_repair_20261030/private/active_run.json')
    old=read(ROOT/'experiments/analyses/claude_comparison_20261030/private/cases.json');oldby={c['id']:c for c in old}
    current=read(ROOT/'experiments/analyses/scoped_repair_20261030/private/cases.json')
    catalog=read(ROOT/'knowledge/authored/kg_cards_20261030_v3/cards.json');cards={c['id']:c for c in catalog['cards']}
    result=[]
    for c in current:
        row={k:c[k] for k in ('id','input','reference')};row['arms']={};row['reference_changes']=oldby[c['id']]['claude']['changes']
        row['families']=[{k:f[k] for k in ('key','label','limit','source_excerpts')}|{'candidate_ids':[t['card_id'] for t in f['traces']]} for f in oldby[c['id']]['families']]
        for arm,runid in active['runs'].items():
            folder=ROOT/'experiments/runs'/runid/'private/records'/c['id']
            r=read(folder/'result.json');v={'output':r['output_text'],'status':r['status'],'error':r.get('error'),'record':str(folder.relative_to(ROOT)),'calls':r['calls']}
            for name,key in [('reference_packet.json','packet'),('retrieval_raw.json','retrieval'),('mapping.json','mapping'),('morphology.json','morphology'),('final_plan.json','plan'),('transformation_plan.json','planner_plan'),('agent_call/parsed.json','raw_agent'),('generation_call/parsed.json','raw_worker')]:
                if (folder/name).exists():v[key]=read(folder/name)
            if 'packet' in v:
                delivered={x['id'] for x in v['packet']['cards']}
                assert all(x==cards[x['id']] for x in v['packet']['cards'])
                v['delivered_ids']=list(x['id'] for x in v['packet']['cards'])
            else:delivered=set();v['delivered_ids']=[]
            rawed=v.get('raw_agent',{}).get('edits',[]);ed=v.get('plan',{}).get('edits',[])
            selected={b['card_id'] for e in rawed for b in e.get('bindings',[])}
            applied={b['card_id'] for e in ed if e['outcome']=='applied' for b in e.get('bindings',[])}
            v['selected_ids']=sorted(selected);v['applied_ids']=sorted(applied)
            paths=v.get('retrieval',{}).get('paths',[])
            v['candidate_trace']={}
            for f in row['families']:
                for cid in f['candidate_ids']:
                    assert cid in cards
                    ps=[p for p in paths if p['rule_id']==cid]
                    state='applied_somewhere' if cid in applied else 'selected' if cid in selected else 'delivered_not_selected' if cid in delivered else 'retrieved_not_delivered' if ps else 'analysis_stopped' if r['status']=='analysis_failed' else 'not_retrieved'
                    v['candidate_trace'][cid]={'stage':state,'paths':ps,'card':cards[cid]}
            # Details retained for traceability; UI will show readable summaries, not raw JSON.
            row['arms'][arm]=v
        result.append(row)
    assert len(result)==50
    save(P/'evidence.json',result);save(P/'input_hashes.json',HASHES)
    save(P/'scope.json',{'latest_batch':active['batch'],'records':50,'conditions':2,'new_model_calls':0,'new_KG_queries':0,'changes':'analysis artifacts only; no cards or pipeline modifications','family_mapping':'reused prior analyst candidate map; related form does not prove applicability; reference_changes not an exhaustive linguistic alignment'})
    print('Saved evidence for 50 inputs / 100 actual records; no new calls')
if __name__=='__main__':main()
