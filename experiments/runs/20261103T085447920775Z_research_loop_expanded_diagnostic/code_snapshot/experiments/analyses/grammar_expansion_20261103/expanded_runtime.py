"""Two construction queries over one graph; no module-wide card dump."""
import copy,importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
s=importlib.util.spec_from_file_location('scope_expanded',HERE/'scope_runtime.py');scope=importlib.util.module_from_spec(s);s.loader.exec_module(scope)
bridge=scope.bridge
bridge.GRAPH=ROOT/'knowledge/authored/semantic_grammar_20261103_r2/private/graph.json'
bridge.DEFINITIONS['source_final']=('Kiwi 관찰 종결어미',{'아요':'아요','어요':'어요','네요':'네요','거든요':'거든요','other':'기타'})
bridge.MACHINE.update({'source_final','prefinal_sequence'})
bridge.DEFINITIONS['prefinal_sequence']=('실제 선어말 순서',{'none':'없음','eoss':'었','si':'시','si_eoss':'시+었','other':'그 밖'})
PROMPT=scope.PROMPT
schema_and_payload=scope.schema_and_payload

def analyze_response(graph,raw,morph,uid):
 a,_=scope.analyze_response(graph,raw,morph,uid);c=a['clauses'][0];final=c['morphology']['source_final']
 c['features']['source_final']=final if final in graph['feature_schema']['source_final'] else 'other'
 pf=tuple('었' if x in ('았','었','였') else '시' if x in ('시','으시') else x for x in c['morphology']['prefinals'])
 c['features']['prefinal_sequence']={(): 'none',('었',):'eoss',('시',):'si',('시','었'):'si_eoss'}.get(pf,'other')
 c['feature_bindings']['prefinal_sequence']={'clause_id':c['id'],'predicate_id':c['predicate']['id'],'origin':'kiwi_observed_prefinal_sequence'}
 c['feature_bindings']['source_final']={'clause_id':c['id'],'predicate_id':c['predicate']['id'],'origin':'kiwi_observed_final_ending'}
 project=scope.projector_for(raw['scope']['auxiliary_class'])
 traces=[bridge.trace(graph,a,morph,projector=project,construction=n['id']) for n in graph['nodes'] if n['type']=='GrammarConstruction']
 ready=[t for t in traces if t['packet']['clauses'][0]['readiness']=='ready_for_generation_trial']
 if len(ready)>1:
  chosen=copy.deepcopy(ready[0]);chosen['packet']['clauses'][0].update(readiness='needs_analysis',needs_analysis=['multiple_constructions_require_selection'])
 else:
  # Pick a matched construction only; unmatched traces remain in the record.
  matched=[t for t in traces if t['retrieval']['clauses'][0]['state']=='eligible']
  chosen=copy.deepcopy((ready or matched or traces)[0])
 chosen['construction_queries']=traces
 return a,chosen

def generation_payload(analysis,trace,morph):
 compact,enhanced=scope.base.generation_payload(analysis,trace,morph)
 if trace['retrieval']['construction_id']=='SEM_CX_HAEYE_DECLARATIVE':
  action=enhanced['actions'][0]
  if not action['target'].endswith('요'):raise ValueError('haeye_source_surface_mismatch')
  action['expected_surface']=action['target'][:-1]+'예'
  action['evidence_interpretation']={'level':'compositional_application_not_exact_sentence_attestation','source_final':analysis['clauses'][0]['morphology']['source_final'],'observed_prefinals':analysis['clauses'][0]['morphology']['prefinals'],'terminal_host_role':analysis['clauses'][0]['morphology'].get('terminal_host',{}).get('host_role','lexical'),'preserved_subject_honorific':analysis['clauses'][0]['features'].get('subject_honorific'),'note':'원문 용례는 근거노드에, 이 문장 형태의 조합 판단은 실행 기록에 구분'}
  action['expected_surface_basis']='documented_hae_plus_yo_ye_structure; bounded noncopular endings only'
 return compact,enhanced

def preservation_check(morphology,output,payload):
 result=scope.base.preservation_check(morphology,output,payload)
 action=payload['actions'][0]
 if action.get('expected_surface') is not None and result.get('piece')==action['expected_surface']:
  result['warnings']=[w for w in result['warnings'] if w!='selected_ending_not_at_target_end']
  result['realization_check']='documented_surface_postcondition_matched_including_contraction'
 return result
