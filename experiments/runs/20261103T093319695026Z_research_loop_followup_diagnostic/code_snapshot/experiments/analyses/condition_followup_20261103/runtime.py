"""Typed boundary questions, explicit unknown categories, independent scope diagnostics."""
import copy,importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
s=importlib.util.spec_from_file_location('expanded_followup_parent',ROOT/'experiments/analyses/grammar_expansion_20261103/expanded_runtime.py');parent=importlib.util.module_from_spec(s);s.loader.exec_module(parent)
bridge=parent.bridge
bridge.GRAPH=ROOT/'knowledge/authored/semantic_grammar_20261103_r3/private/graph.json'
PROMPT=parent.PROMPT+"""
이번 boundary_links는 배열이 아니라 주어진 경계ID를 키로 하는 객체다. 각 키에 relation/head_word_id만 답한다. 선택지는 관찰된 EC/ETM/ETN에 따른 구조상 후보이고, 의미의 정답이 아니다. unknown/null도 가능하다.
관형절 전체에 포함된 연결어미를 관형사형 어미로 바꾸어 분류하지 않는다. 각 경계 자체의 관계와 바로 연결되는 head를 답한다.
ETN+조사가 붙은 명사화는 nominal로 답할 수 있다. ETN+의가 뒤 명사를 꾸미더라도 ETM 관형절과 구별한다.
보조용언 범주가 불명확하면 null을 유지한다. 다른 필드에서 이미 미지원 요청/명령으로 분석됐다는 이유로 동사/형용사 값을 추측해서 채우지 않는다.
"""
def schema_and_payload(graph,morph,uid,context):
 schema,user=parent.schema_and_payload(graph,morph,uid,context);fields={};ids=[w['uid'] for w in morph['words']]
 for w in parent.scope.boundaries(morph):
  tags={t.split('-')[0] for f,t in w['morphs']};rel={'unknown'}
  if 'ETM' in tags:rel.add('adnominal')
  if 'ETN' in tags:rel.add('nominal')
  if 'EC' in tags:rel.update(('linked','auxiliary','quoted','nominal'))
  fields[w['uid']]=parent.scope.base.obj({'relation':{'type':'string','enum':sorted(rel)},'head_word_id':{'type':['string','null'],'enum':ids+[None]}})
 schema['properties']['scope']['properties']['boundary_links']=parent.scope.base.obj(fields)
 user['boundary_response_format']='fixed_object_by_observed_word_id; select each direct relationship, not containing-clause label'
 return schema,user

def projector_factory(auxiliary_class):
 original=parent.scope.projector_for(auxiliary_class)
 def project(word):
  try:return original(word)
  except ValueError as exc:
   if str(exc)!='auxiliary_class_unresolved':raise
   ps=word['morphs'];hosts=[i for i,(f,t) in enumerate(ps) if t.split('-')[0] in ('VV','VA','VX','VCP','VCN','XSV','XSA')];i=hosts[-1]
   tail=ps[i+1:]
   if not tail or tail[-1][1].split('-')[0]!='EF' or any(t.split('-')[0]!='EP' for f,t in tail[:-1]):raise ValueError('auxiliary_final_chain_unsupported')
   pf=[f for f,t in tail[:-1]];stem=ps[i][0]
   m={'predicate_id':'p1','lemma':stem+'다','stem':stem,'prefinals':pf,'source_final':tail[-1][0],'alignment':'whole_predicate_recomposition','origin':'kiwi_token_projection','source_morphs':copy.deepcopy(ps),'terminal_host':{'form':stem,'original_tag':ps[i][1],'morph_index':i,'host_role':'auxiliary'},'auxiliary_class_origin':'qwen_unresolved','projection_operation':'preserve_observed_VX_without_inventing_category'}
   m['source_alignment']={'target_span':[word['start'],word['end']],'surface':word['surface'],'checked_by':'kiwi_token_projection','status':'machine_aligned_not_human_verified',**{k:copy.deepcopy(m.get(k)) for k in ('lemma','stem','prefinals','source_final','nominal')}}
   return m,None,'none' if not pf else 'eoss' if len(pf)==1 and pf[0] in ('았','었','였') else 'other'
 return project

def analyze_response(graph,raw,morph,uid):
 schema,_=schema_and_payload(graph,morph,uid,morph['text']);parent.scope.base.validate_schema(raw,schema)
 converted=copy.deepcopy(raw);converted['scope']['boundary_links']=[dict(word_id=k,**v) for k,v in raw['scope']['boundary_links'].items()]
 a,tr=parent.analyze_response(graph,converted,morph,uid,projector_factory=projector_factory)
 a['origin']='typed_boundary_questions_and_separate_scope_v5';a['response_contract']='observed_boundary_keyed_object'
 if a['clauses'][0]['features']['predicate_class'] is None:a['clauses'][0]['feature_bindings']['predicate_class']['origin']='qwen_unresolved_with_observed_VX_morphology'
 project=projector_factory(raw['scope']['auxiliary_class'])
 queries=[bridge.trace(graph,a,morph,projector=project,construction=n['id']) for n in graph['nodes'] if n['type']=='GrammarConstruction']
 for t in queries:
  q=t['retrieval']['clauses'][0];p=t['packet']['clauses'][0]
  p['analysis_diagnostics']=list(p['needs_analysis'])
  if q['state']=='out_of_slice':p['readiness']='out_of_slice' # Keep diagnostics; do not pretend the grammar is now supported.
 ready=[t for t in queries if t['packet']['clauses'][0]['readiness']=='ready_for_generation_trial']
 if len(ready)>1:
  selected=copy.deepcopy(ready[0]);selected['packet']['clauses'][0].update(readiness='needs_analysis',needs_analysis=['multiple_constructions_require_selection'])
 else:
  matched=[t for t in queries if t['retrieval']['clauses'][0]['state']=='eligible'];unresolved=[t for t in queries if t['retrieval']['clauses'][0]['state']=='unresolved']
  selected=copy.deepcopy((ready or matched or unresolved or queries)[0])
 selected['construction_queries']=queries
 selected['diagnosis_axes']={'construction_states':{t['retrieval']['construction_id']:t['retrieval']['clauses'][0]['state'] for t in queries},'structural_issues':a.get('adapter_diagnostics',[]),'unknown_features':[k for k,v in a['clauses'][0]['features'].items() if v is None],'scope_and_analysis_are_not_exclusive':True}
 return a,selected

generation_payload=parent.generation_payload
preservation_check=parent.preservation_check
