"""Offline candidate: turn an existing KG surface check into concrete feedback.

Does not call a model, replace output, read references, or certify naturalness.
Only supports the already-declared r7 local 요→예 surface postcondition.
"""
import copy,hashlib,json
SUPPORTED='original_target[:-1]+예 when original_target endswith 요'
def fingerprint(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf8')).hexdigest()
def build_feedback(graph,packet,output):
 if not isinstance(output,str):raise ValueError('output_not_text')
 nodes={n['id']:n for n in graph['nodes']};findings=[]
 actions=packet.get('actions',[])
 # Unambiguous location is required; do not guess changed offsets after edits.
 if len(actions)!=1:return {'status':'not_inspected','reason':'requires_single_action_for_unambiguous_feedback','findings':[],'original_output':output}
 a=actions[0];start,end=a['span'];source=packet['text'];target=a['target']
 if not (0<=start<end<=len(source)) or source[start:end]!=target:raise ValueError('invalid_source_alignment')
 form_ids=[e['target'] for e in graph['edges'] if e['source']==a['rule_id'] and e['relation']=='REALIZES']
 if len(form_ids)!=1:return {'status':'not_inspected','reason':'ambiguous_or_missing_graph_realization','findings':[],'original_output':output}
 form=nodes[form_ids[0]]['properties']
 if form.get('surface_postcondition')!=SUPPORTED or not target.endswith('요'):
  return {'status':'not_inspected','reason':'no_supported_surface_contract','findings':[],'original_output':output}
 before,after=source[:start],source[end:]
 if not output.startswith(before) or (after and not output.endswith(after)) or len(output)<len(before)+len(after):
  return {'status':'needs_alignment_review','reason':'outside_action_changed','findings':[],'original_output':output}
 actual=output[len(before):len(output)-len(after) if after else len(output)]
 prefix=target[:-1]
 # Expected local form is computed ONLY for checking, never substituted or sent as a full answer.
 if actual!=prefix+'예':
  findings.append({'target_id':a['target_id'],'rule_id':a['rule_id'],'form_node_id':form_ids[0],'original_target':target,'actual_generated_target':actual,'failed_check':'declared_surface_preservation','source_prefix_to_preserve':prefix,'source_suffix':'요','permitted_replacement_suffix':'예','source_preserve_features':a.get('preserve',{}),'message':'실제 출력이 KG에 기록된 보존 조건과 다릅니다. 원문의 보존 부분을 유지하고 지정된 끝부분만 수정하세요.','basis':'existing_graph_surface_postcondition_not_reference_answer'})
 return {'status':'feedback_available' if findings else 'declared_contract_satisfied','findings':findings,'original_output':output,'binding':{'packet_sha256':fingerprint(packet),'graph_sha256':fingerprint(graph),'output_sha256':fingerprint(output)},'scope':'single_action_declared_surface_contract_only_not_semantic_or_dialect_accuracy'}

def retry_payload(graph,packet,output,feedback,arm):
 """Equal second-call opportunity: neutral reconsideration vs concrete diagnostic."""
 if arm not in ('neutral','specific'):raise ValueError('unknown_arm')
 if feedback['status']!='feedback_available':raise ValueError('not_feedback_eligible')
 if feedback.get('original_output')!=output:raise ValueError('feedback_output_mismatch')
 if feedback.get('binding')!={'packet_sha256':fingerprint(packet),'graph_sha256':fingerprint(graph),'output_sha256':fingerprint(output)}:raise ValueError('feedback_binding_mismatch')
 if build_feedback(graph,packet,output)!=feedback:raise ValueError('feedback_content_mismatch')
 value={'original_request':copy.deepcopy(packet),'previous_output':output,'instruction':'원문과 전달된 KG 규칙을 다시 확인하여 뜻·시제·높임을 보존한 문장 전체를 작성하세요.'}
 if arm=='specific':value['failed_checks']=copy.deepcopy(feedback['findings'])
 return value
