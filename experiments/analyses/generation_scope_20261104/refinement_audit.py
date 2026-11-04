"""Read-only evidence assembly for approved-reference refinement; no model client."""
from pathlib import Path
import json,hashlib,datetime,sys,collections
H=Path(__file__).resolve().parent;R=H.parents[2];sys.path.insert(0,str(R/'src'))
from research_management.work import WorkStore
SOURCE=R/'experiments/runs/20261104T013633051461Z_support_expansion_full50'
def read(p):return json.loads(p.read_text('utf8'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n','utf8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out=H/'private/refinement'/stamp;out.mkdir(parents=True)
 follow=Path(read(H/'private/latest_reference_followup.json')['directory']);cases=read(follow/'cases.json')
 olddir=R/'experiments/analyses/claude_comparison_20261030/private';old={x['id']:x for x in read(olddir/'cases.json')};families=read(olddir/'family_evidence.json')
 graph_path=R/'knowledge/authored/semantic_grammar_20261104_r7/private/graph.json';graph=read(graph_path)
 assert graph==read(SOURCE/'private/graph.json')
 hashes={str(p):sha(p) for p in (follow/'cases.json',olddir/'cases.json',olddir/'family_evidence.json',graph_path)}
 task={'id':'reference_refinement_'+stamp,'title':'批准参照50→实际KG路径核对'.replace('批准参照50→实际KG路径核对','승인 참조50 → 실제 KG 경로 대조'),'actor':'연구 리드','stage':'자료 연결','status':'running','done':0,'total':50,'unit':'입력','unit_key':'reference_refinement_join'};store=WorkStore(R);store.task(task)
 for case in cases:
  base=SOURCE/'private/records'/case['id'];targets=[]
  for folder in sorted((base/'targets').iterdir()):
   a=read(folder/'analysis.json');tr=read(folder/'trace.json');p=tr['packet']['clauses'][0]
   targets.append({'target_id':folder.name,'source_target':read(folder/'target.json'),'features':a['clauses'][0]['features'],'analysis_diagnostics':a.get('adapter_diagnostics',[]),'scope_links':a.get('scope_links'),'diagnosis_axes':tr['diagnosis_axes'],'readiness':p['readiness'],'needs_analysis':p['needs_analysis'],'selected_rule_ids':[x['rule_id'] for x in p['choices']],'query_path':str(folder/'trace.json'),'analysis_path':str(folder/'analysis.json'),'construction_queries':[{'construction_id':t['retrieval']['construction_id'],'state':t['retrieval']['clauses'][0]['state'],'scope_failures':t['retrieval']['clauses'][0].get('scope_failures',[]),'scope_unknown':t['retrieval']['clauses'][0].get('scope_unknown',[]),'eligible_rules':[x.get('rule_id') for x in t['retrieval']['clauses'][0].get('eligible',[])]} for t in tr['construction_queries']]})
   for pth in (folder/'analysis.json',folder/'trace.json',folder/'target.json'):hashes[str(pth)]=sha(pth)
  case['current_targets']=targets
  case['historical_families']=[{'key':f['key'],'label':f['label'],'legacy_card_ids':[x['card_id'] for x in f['traces']],'legacy_source_refs':f.get('card_source_refs',{}),'limit':f.get('limit'),'scope':'20261030 historical association, not current applicability proof'} for f in old[case['id']]['families']]
  task['done']+=1;store.task(task)
 save(out/'cases.json',cases);save(out/'graph.json',graph);save(out/'historical_family_evidence.json',families)
 history=[]
 for root,names in [('support_expansion_20261104',['latest_handoff.json','latest_realization.json','latest_typed.json','latest_prefix.json','latest_prompt_contract_r1.json','latest_prompt_contract_r2.json']),('minimal_instruction_20261104',['latest.json','latest_word.json','latest_temperature.json'])]:
  for name in names:
   path=R/'experiments/analyses'/root/'private'/name
   if path.exists():history.append({'pointer':str(path),'runs':read(path)});hashes[str(path)]=sha(path)
 save(out/'prior_experiments.json',history)
 save(out/'manifest.json',{'created_utc':stamp,'count':50,'target_count':sum(len(x['current_targets']) for x in cases),'source_hashes':hashes,'model_calls':0,'kg_writes':0,'purpose':'reference-guided diagnosis, not new grammar certification'})
 save(H/'private/latest_refinement.json',{'directory':str(out)})
 task.update(status='completed',message='50입력·62종결 경로 연결. 검토·수정안 확정은 별도 진행.');store.task(task)
 for c in cases:print(c['id'],'|',','.join(f['key'] for f in c['historical_families']),'|','; '.join(t['target_id']+':'+t['readiness']+':'+','.join(t['selected_rule_ids'])+':'+','.join(t['needs_analysis']) for t in c['current_targets']))
 print('OUT',out)
if __name__=='__main__':main()
