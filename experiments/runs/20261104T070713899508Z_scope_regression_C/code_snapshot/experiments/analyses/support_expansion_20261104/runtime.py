"""Reuse boundary analysis and graph reader; add observed nominal scope, not sentence rules."""
from pathlib import Path
import importlib.util,copy
H=Path(__file__).resolve().parent;ROOT=H.parents[2]
s=importlib.util.spec_from_file_location('boundary_parent',ROOT/'experiments/analyses/boundary_qwen_20261103/runtime.py');parent=importlib.util.module_from_spec(s);s.loader.exec_module(parent)
base=parent.base;bridge=parent.bridge
bridge.GRAPH=ROOT/'knowledge/authored/semantic_grammar_20261104_r7/private/graph.json'
bridge.DEFINITIONS['source_final'][1].update({'예요':'예요','에요':'에요'})
bridge.MACHINE.add('nominal_kind');bridge.DEFINITIONS['nominal_kind']=('관찰 명사 종류',{'lexical_nominal':'일반명사·대명사·수사','bound_nominal':'의존명사','not_nominal':'명사서술아님','unknown':'미확정'})
PROMPT=parent.PROMPT
schema_and_payload=parent.schema_and_payload
GENERATION_PROMPT=parent.GENERATION_PROMPT
GENERATION_SCHEMA=parent.GENERATION_SCHEMA

def nominal_kind(word):
 ps=word['morphs'];indexes=[i for i,(f,t) in enumerate(ps) if t.split('-')[0]=='VCP']
 if not indexes:return 'not_nominal'
 if len(indexes)!=1:return 'unknown'
 tags=[t.split('-')[0] for f,t in ps[:indexes[0]]]
 if 'NNB' in tags:return 'bound_nominal'
 if tags and all(t in ('NNG','NNP','NP','NR','XSN','XPN') for t in tags):return 'lexical_nominal'
 return 'unknown'

def analyze_response(graph,raw,morph,uid):
 a,initial=parent.analyze_response(graph,raw,morph,uid);c=a['clauses'][0]
 w=next(w for w in morph['words'] if w['uid']==uid)
 observed=nominal_kind(w)
 c['features']['nominal_kind']=None if observed=='unknown' else observed;c['feature_bindings']['nominal_kind']={'clause_id':c['id'],'predicate_id':c['predicate']['id'],'origin':'kiwi_observed_nominal_tags','observed_classification':observed}
 project=parent.prior.projector_factory(raw['scope']['auxiliary_class'])
 traces=[bridge.trace(graph,a,morph,projector=project,construction=n['id']) for n in graph['nodes'] if n['type']=='GrammarConstruction']
 for t in traces:
  if t['retrieval']['clauses'][0]['state']=='out_of_slice':t['packet']['clauses'][0]['readiness']='out_of_slice'
 ready=[t for t in traces if t['packet']['clauses'][0]['readiness']=='ready_for_generation_trial'];matched=[t for t in traces if t['retrieval']['clauses'][0]['state']=='eligible'];unknown=[t for t in traces if t['retrieval']['clauses'][0]['state']=='unresolved'];missing=[t for t in traces if t['retrieval']['clauses'][0]['state']=='no_matching_usage']
 chosen=copy.deepcopy((ready or matched or unknown or missing or traces)[0])
 if len(ready)>1:chosen['packet']['clauses'][0].update(readiness='needs_analysis',needs_analysis=['multiple_constructions_require_selection'])
 chosen['construction_queries']=traces;chosen['condition_provenance']=initial.get('condition_provenance',{})
 chosen['diagnosis_axes']={'structural_issues':a.get('adapter_diagnostics',[]),'all_analysis_issues':sorted({x for t in traces for x in t['packet']['clauses'][0]['needs_analysis']}),'construction_states':{t['retrieval']['construction_id']:t['retrieval']['clauses'][0]['state'] for t in traces},'selected_state_policy':'ready > eligible > unresolved > no_matching_usage > out_of_slice'}
 for n in graph['nodes']:
  if n['id'].startswith('COND_SUP_'):chosen['condition_provenance'][n['id']]=copy.deepcopy(n['properties'])
 return a,chosen

def generation_payload(a,tr,morph):
 compact,enhanced=parent.generation_payload(a,tr,morph)
 if tr['retrieval']['construction_id']=='SEM_CX_SUP_POLITE_Q_EO':
  act=enhanced['actions'][0]
  if not act['target'].endswith('요'):raise ValueError('source_EO_surface_mismatch')
  act['expected_surface']=act['target'][:-1]+'예';act['expected_surface_basis']='documented_polite_question_hae_plus_ye; diagnostic only'
 if tr['retrieval']['construction_id']=='SEM_CX_SUP_COP_PRESENT':
  act=enhanced['actions'][0];nominal=act['nominal'];cp=ord(nominal[-1]);consonant=0xac00<=cp<=0xd7a3 and (cp-0xac00)%28!=0
  act['copula_surface_candidates']=[nominal+'이라예'] if consonant else [nominal+'라예',nominal+'이라예']
  act['copula_surface_basis']='structure-derived diagnostic candidates, not direct attestation of every noun'
  act['composition']=list(act['composition'])+['includes_copula=false: 라예에는 계사 이-가 없다. 받침 있는 명사 뒤는 이+라예를 결합한다. 모음 뒤 계사 축약은 일반 한국어 조합으로 판단한다. 관찰된 선어말에 없는 -시-를 새로 넣지 않는다.']
  act['honorific_model_judgment']=act['preserve'].get('subject_honorific')
  act['preserve']['subject_honorific']='not_marked_on_predicate'
 return compact,enhanced
preservation_check=parent.preservation_check
