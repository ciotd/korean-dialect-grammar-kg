"""Phase1: saved-record restriction audit, no network/model calls or source mutation."""
from pathlib import Path
import json,sys,collections,re,hashlib,datetime
H=Path(__file__).resolve().parent;R=H.parents[2];sys.path.insert(0,str(R/'src'))
from kg_pipeline.io import read,save,sha
from research_management.work import WorkStore
SOURCE=R/'experiments/runs/20261104T013633051461Z_support_expansion_full50'

def extract_pieces(text,out,actions):
 if not actions:return [],out!=text
 pattern='^';cursor=0
 for a in sorted(actions,key=lambda a:a['span']):
  i,j=a['span'];assert i>=cursor and text[i:j]==a['target'];pattern+=re.escape(text[cursor:i])+'(.*?)';cursor=j
 pattern+=re.escape(text[cursor:])+'$';m=re.fullmatch(pattern,out,re.DOTALL)
 return (list(m.groups()),False) if m else ([],True)

def main():
 source_hashes=read(SOURCE/'artifact_hashes.json');bad=[k for k,v in source_hashes.items() if sha((SOURCE/k).read_bytes())!=v];assert not bad,bad
 rows=read(SOURCE/'private/results.json');assert len(rows)==50
 store=WorkStore(R);task={'id':'restriction_audit_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'),'title':'① 제한 위치 확인 / 50건 처리기록 대조','actor':'Lead audit code','stage':'기록별 제한·전달·원시응답 확인','status':'running','done':0,'total':50,'unit':'입력','unit_key':'record_audit','message':'새Qwen호출0·원본변경0'};store.task(task)
 cases=[];targets=[];gates=collections.Counter();all_forms_before=all_forms_after=0;condition_fail=collections.Counter();notes=[];features_preserve=[];masked_structural=[]
 for row in rows:
  d=SOURCE/'private/records'/row['id'];packet=read(d/'generation_packet.json');morph=read(d/'morphology.json');actions=packet['actions'];internal=read(d/'actions_internal.json');by={a['target_id']:a for a in actions}
  req=read(d/'generation_call/request.json');resp=read(d/'generation_call/response.json');parsed=json.loads(resp['choices'][0]['message']['content'])
  assert json.loads(req['messages'][1]['content'])==packet
  assert req['messages'][0]['content']==(SOURCE/'generation_prompt.txt').read_text('utf8')
  assert parsed==read(d/'generation_call/parsed.json') and parsed['output_text']==row['output_text']
  assert 'expected_surface' not in json.dumps(packet) and 'copula_surface_candidates' not in json.dumps(packet)
  ef_ids={w['uid'] for w in morph['words'] if any(t.split('-')[0]=='EF' for f,t in w['morphs'])}
  assert ef_ids=={t['target_id'] for t in row['targets']}
  pieces,outside=extract_pieces(row['input_text'],row['output_text'],actions);piece_map={a['target_id']:p for a,p in zip(sorted(actions,key=lambda a:a['span']),pieces)}
  ts=[]
  for t in row['targets']:
   uid=t['target_id'];td=d/'targets'/uid;trace=read(td/'trace.json');analysis=read(td/'analysis.json');p=trace['packet']['clauses'][0];q=trace['retrieval']['clauses'][0];queries=trace['construction_queries'];a=by.get(uid);eligible=[];scope=[];ready=[]
   for cq in queries:
    cr=cq['retrieval']['clauses'][0];cp=cq['packet']['clauses'][0]
    if cp['readiness']=='ready_for_generation_trial':ready.append(cq['retrieval']['construction_id'])
    eligible.extend({'construction':cq['retrieval']['construction_id'],'rule_id':x['rule_id'],'packet_state':cp['readiness']} for x in cr['eligible'])
    scope.extend({'construction':cq['retrieval']['construction_id'],**x} for x in cr['scope_failures'])
   routing={'out_of_slice':'construction_scope_excluded','no_matching_usage':'no_rule_satisfies_conditions','needs_analysis':'analysis_or_alignment_unresolved','ready_for_generation_trial':'delivered'}[t['readiness']]
   gates[routing]+=1
   for fail in scope:condition_fail[fail['feature']]+=1
   structural=trace.get('diagnosis_axes',{}).get('structural_issues',[])
   if structural and t['readiness']!='needs_analysis':masked_structural.append({'id':row['id'],'target_id':uid,'readiness':t['readiness'],'issues':structural})
   assert (a is not None)==(t['readiness']=='ready_for_generation_trial')
   fbefore=fafter=None
   if a:
    before=next(x for x in internal if x['target_id']==uid)['forms'];after=[f for f in before if f.get('selected_combining_form')];assert after==a['forms'];fbefore=len(before);fafter=len(after);all_forms_before+=fbefore;all_forms_after+=fafter
    assert all(a[k]==next(x for x in internal if x['target_id']==uid)[k] for k in ('stem','prefinals','source_final','rule_id','target','span','preserve'))
    for k,v in a['preserve'].items():
     if k in a['features'] and a['features'][k]!=v:features_preserve.append({'id':row['id'],'target_id':uid,'field':k,'preserve':v,'features':a['features'][k]})
    for note in p['context_notes']:notes.append({'id':row['id'],'target_id':uid,'note_id':note['id'],'title':note['title'],'meaning':note['meaning'],'sent_as_context_note':False})
   detail={'id':row['id']+'__'+uid,'input_id':row['id'],'target_id':uid,'target':row['input_text'][slice(*t['span'])],'span':t['span'],'readiness':t['readiness'],'route':routing,'selected_construction':trace['retrieval']['construction_id'],'query_state':q['state'],'features':analysis['clauses'][0]['features'],'needs_analysis':p['needs_analysis'],'structural_issues':structural,'all_constructions':[{'id':cq['retrieval']['construction_id'],'state':cq['retrieval']['clauses'][0]['state'],'readiness':cq['packet']['clauses'][0]['readiness'],'scope_failures':cq['retrieval']['clauses'][0]['scope_failures'],'narrowing':cq['retrieval']['clauses'][0]['narrowing']} for cq in queries],'eligible_across_constructions':eligible,'ready_constructions':ready,'delivered':a is not None,'action':a,'forms_before':fbefore,'forms_after':fafter,'replacement':piece_map.get(uid),'trace_path':str(td/'trace.json'),'analysis_path':str(td/'analysis.json'),'context_notes':p['context_notes']}
   targets.append(detail);ts.append(detail)
  other=[{'uid':w['uid'],'surface':w['surface'],'tags':[t for f,t in w['morphs']]} for w in morph['words'] if w['uid'] not in ef_ids and any(t.split('-')[0] in ('EC','ETM','ETN','JKS','JKO','JKB','JX') for f,t in w['morphs'])]
  case={'id':row['id'],'input_text':row['input_text'],'output_text':row['output_text'],'changed':row['input_text']!=row['output_text'],'action_count':len(actions),'target_count':len(ts),'targets':ts,'non_target_grammar_words':other,'outside_supported_spans_changed':outside,'warnings':row.get('checks',{}).get('warnings',[]),'request_path':str(d/'generation_call/request.json'),'response_path':str(d/'generation_call/response.json'),'packet_path':str(d/'generation_packet.json'),'raw_output_unchanged':True};cases.append(case)
  task.update(done=len(cases),message=row['id']+' 분석·전달·출력 결속');store.task(task)
 graph=read(SOURCE/'private/graph.json');counter=collections.Counter(n['type'] for n in graph['nodes'])
 summary={'source_run':SOURCE.name,'new_model_calls':0,'records':50,'targets':len(targets),'routing':dict(gates),'sentences_with_actions':sum(bool(c['action_count']) for c in cases),'sentences_without_actions':sum(not c['action_count'] for c in cases),'no_action_unchanged':sum(not c['action_count'] and not c['changed'] for c in cases),'with_action_unchanged':sum(bool(c['action_count']) and not c['changed'] for c in cases),'changed_records':sum(c['changed'] for c in cases),'forms_before':all_forms_before,'forms_after':all_forms_after,'forms_removed':all_forms_before-all_forms_after,'multiple_ready_targets':sum(len(t['ready_constructions'])>1 for t in targets),'eligible_but_not_delivered':[t['id'] for t in targets if t['eligible_across_constructions'] and not t['delivered']],'preserve_features_differences':features_preserve,'context_note_occurrences_omitted':len(notes),'omitted_note_ids':dict(collections.Counter(n['note_id'] for n in notes)),'structural_issues_other_route':masked_structural,'outside_changed_records':sum(c['outside_supported_spans_changed'] for c in cases),'graph_node_types':dict(counter),'snapshot_files_verified':len(source_hashes),'interpretation':'observed routing and restrictions; not counterfactual effect or linguistic accuracy'}
 summary['delivered_but_unchanged_targets']=[t['id'] for t in targets if t['delivered'] and t['target']==t['replacement']]
 summary['needs_analysis_masked_by_route']=[{'id':t['id'],'route':t['route'],'needs_analysis':t['needs_analysis']} for t in targets if t['needs_analysis'] and t['route']!='analysis_or_alignment_unresolved']
 for t in targets:
  t['display_selected_construction']=None if all(q['state']=='out_of_slice' for q in t['all_constructions']) else t['selected_construction']
  t['display_selection_note']='all four out of scope; recorded selection is tie default, not applicable construction' if t['display_selected_construction'] is None else 'recorded selected construction'
 save(H/'private/cases.json',cases);save(H/'private/targets.json',targets);save(H/'private/summary.json',summary);save(H/'private/omitted_context_notes.json',notes)
 save(H/'private/validation.json',{'source_manifest_verified':len(source_hashes),'records':50,'targets':len(targets),'request_packet_equal':50,'raw_parsed_stored_equal':50,'EF_target_set_equal':50,'forms_filter_reproduced':sum(t['delivered'] for t in targets),'source_manifest_still_equal':all(sha((SOURCE/k).read_bytes())==v for k,v in source_hashes.items()),'graph_and_source_modified':False})
 task.update(status='completed',message='50입력·62위치 결속 완료. 독립 검토와 해석은 별도.');store.task(task)
 print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
