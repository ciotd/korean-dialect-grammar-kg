"""Read-only localization of analysis conflicts, never bypass applicability gates."""
from pathlib import Path
import sys,json,collections,importlib.metadata
H=Path(__file__).resolve().parent;R=H.parents[2];sys.path[:0]=[str(H),str(R/'src'),str(R/'local/python')]
import candidate_runtime as rt
from kg_pipeline.io import read,save,sha
from kiwipiepy import Kiwi
B=R/'experiments/runs/20261104T013633051461Z_support_expansion_full50/private/records'

def main():
 rows=[];struct=rt.parent.parent
 for td in sorted(B.glob('*/targets/*')):
  t=read(td/'target.json');a=read(td/'analysis.json');tr=read(td/'trace.json');raw=read(td/'analysis_call/parsed.json');hosts,bounds,snapshot=struct.inventory(t['morph'])
  issues=a.get('adapter_diagnostics',[]);links=raw['scope']['boundary_links'];unknown=[]
  for b in bounds:
   v=links[b['id']]
   if v['relation']=='unknown' or v['head_id'] is None:unknown.append({'boundary_id':b['id'],'source_host':b['source_host'],'boundary':b,'model_link':v,'target_word_id':t['uid'],'same_target_word':b['id'].split(':')[0]==t['uid'],'dependency_decision':'unproven_remains_blocking'})
  qs=tr.get('construction_queries',[tr]);eligible=[q['retrieval']['construction_id'] for q in qs if q['retrieval']['clauses'][0]['state']=='eligible']
  rows.append({'id':td.parent.parent.name,'target_id':td.name,'target':t['morph']['text'][slice(*a['clauses'][0]['target_span'])] if 'target_span' in a['clauses'][0] else tr['retrieval']['clauses'][0]['target_text'],'diagnostics':issues,'eligible_constructions':eligible,'readiness':tr['packet']['clauses'][0]['readiness'],'unresolved_boundaries':unknown,'observed_morphology':a['clauses'][0]['morphology'],'features':a['clauses'][0]['features'],'model_note':raw.get('note'),'analysis_hash':sha((td/'analysis.json').read_bytes()),'gate_changed':False})
 k=Kiwi(num_workers=1);nb=[]
 for text in ['선생님께서 자료를 읽고 계세요.','선생님께서 자료를 읽고 계셨어요.','어머니가 집에 계세요.','이 모임은 친목계예요.','친구들은 잘 지내고 있어요.']:
  ns=[{'score':score,'tokens':[{'form':t.form,'tag':t.tag,'start':t.start,'length':t.len} for t in ts]} for ts,score in k.analyze(text,top_n=5)]
  nb.append({'text':text,'candidates':ns,'contains_gyesi_predicate':any(t['form']=='계시' and t['tag'] in ('VV','VX') for n in ns for t in n['tokens'])})
 out=H/'private/analysis_diagnostic';save(out/'targets.json',rows);save(out/'kiwi_nbest.json',nb)
 summary={'targets':len(rows),'targets_with_structural_diagnostics':sum(bool(r['diagnostics']) for r in rows),'eligible_but_structurally_blocked':sum(bool(r['eligible_constructions']) and bool(r['diagnostics']) and r['readiness']!='ready_for_generation_trial' for r in rows),'diagnostics':dict(collections.Counter(d for r in rows for d in r['diagnostics'])),'kiwi_version':importlib.metadata.version('kiwipiepy'),'interpreter':sys.executable,'gate_changed':False,'automatic_morphology_repair':False}
 save(out/'summary.json',summary);print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
