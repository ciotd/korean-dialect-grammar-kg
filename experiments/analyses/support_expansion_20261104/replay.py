"""Same saved Qwen judgments, new graph/adapter: no model calls and no gold text."""
import collections,json
from pathlib import Path
import runtime as rt
from kg_pipeline.io import read,save,sha
H=Path(__file__).resolve().parent;R=H.parents[2]
BASE=R/'experiments/runs/20261103T111250623634Z_boundary_qwen_full50'
def main():
 graph=read(rt.bridge.GRAPH);rows=[]
 for record in read(BASE/'private/results.json'):
  for previous in record['targets']:
   uid=previous['target_id'];d=BASE/'private/records'/record['id']/'targets'/uid
   target=read(d/'target.json');raw=read(d/'analysis_call/parsed.json')
   a,tr=rt.analyze_response(graph,raw,target['morph'],uid);p=tr['packet']['clauses'][0]
   rows.append({'id':record['id'],'target_id':uid,'input':record['input_text'],'before':previous['readiness'],'after':p['readiness'],'rules':[x['rule_id'] for x in p['choices']],'needs':p['needs_analysis'],'analysis':a,'trace':tr})
 assert len(rows)==62 and len({(r['id'],r['target_id']) for r in rows})==62
 assert all(r['after']=='ready_for_generation_trial' for r in rows if r['before']=='ready_for_generation_trial')
 save(H/'private/replay62_r7.json',rows)
 summary={'baseline':BASE.name,'graph_version':graph['version'],'graph_sha256':sha(rt.bridge.GRAPH.read_bytes()),'model_calls':0,'before':dict(collections.Counter(r['before'] for r in rows)),'after':dict(collections.Counter(r['after'] for r in rows)),'newly_ready':[{'id':r['id'],'target_id':r['target_id']} for r in rows if r['after']=='ready_for_generation_trial' and r['before']!='ready_for_generation_trial']}
 save(H/'private/replay_summary_r7.json',summary);print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
