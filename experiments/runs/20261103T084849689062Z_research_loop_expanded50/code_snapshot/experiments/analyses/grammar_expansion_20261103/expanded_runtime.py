"""Two construction queries over one graph; no module-wide card dump."""
import copy,importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
s=importlib.util.spec_from_file_location('scope_expanded',HERE/'scope_runtime.py');scope=importlib.util.module_from_spec(s);s.loader.exec_module(scope)
bridge=scope.bridge
bridge.GRAPH=ROOT/'knowledge/authored/semantic_grammar_20261103_r1/private/graph.json'
bridge.DEFINITIONS['source_final']=('Kiwi 관찰 종결어미',{'아요':'아요','어요':'어요','네요':'네요','거든요':'거든요','other':'기타'})
bridge.MACHINE.add('source_final')
PROMPT=scope.PROMPT
schema_and_payload=scope.schema_and_payload

def analyze_response(graph,raw,morph,uid):
 a,_=scope.analyze_response(graph,raw,morph,uid);c=a['clauses'][0];final=c['morphology']['source_final']
 c['features']['source_final']=final if final in graph['feature_schema']['source_final'] else 'other'
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
  action['expected_surface_basis']='documented_hae_plus_yo_ye_structure; bounded noncopular endings only'
 return compact,enhanced
