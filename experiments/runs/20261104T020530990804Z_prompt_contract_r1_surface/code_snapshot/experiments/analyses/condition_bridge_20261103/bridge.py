"""Schema-derived analysis contract. No dialect rules or example lookup table."""
import copy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRIOR = ROOT/'experiments/analyses/question_pipeline_20261103'
sys.path.insert(0, str(PRIOR))
from adapter import GRAPH, RuntimeReader, projected as old_projected, compact_morph
from query import Reader
from contracts import obj
from kg_pipeline.io import read
from kg_pipeline.validation import validate_schema

# Definitions of analysis vocabulary, not eligibility/realization rules.
# Allowed values and actual condition IDs are read from the graph.
DEFINITIONS = {
 'clause_role': ('판단 대상 절의 역할', {'main':'독립된 주절','embedded':'다른 절 안에 포함된 절','quoted':'인용된 절'}),
 'speech_act': ('실제 발화 목적. 정보 요청과 행동 요청을 혼동하지 않는다.', {
  'information_question':'정보를 묻는 질문','statement':'사실을 서술함','request':'상대의 행동을 요구하거나 재촉함',
  'rhetorical_question':'답을 요구하지 않는 수사적 질문','confirmation':'이미 아는 내용을 확인시킴',
  'suggestion':'함께 행동하자고 제안함','exclamation':'감탄을 나타냄','self_question':'스스로에게 묻는 질문'}),
 'addressee_level': ('듣는 사람을 대하는 종결 표현. 주체 높임과 구별한다.', {'plain':'비높임 종결','polite':'높임 종결'}),
 'question_kind': ('답으로 무엇을 구하는가. 의문사 글자만으로 판단하지 않는다.', {'polar':'사실 여부를 예 아니오로 답함','wh':'누구 어디 왜 무엇 등의 구체적인 정보를 답함'}),
 'predicate_class': ('Kiwi가 분석한 대상 서술어의 품사', {'verb':'동사','adjective':'형용사','copula':'이다 명사 서술','negative_copula':'아니다 부정 서술'}),
 'prefinal_type': ('대상 서술어에서 관찰된 선어말 형태. 시간 의미와 구별한다.', {'none':'선어말 없음','eoss':'았 었 였 계열 하나','gess':'겠 계열','deo':'더 계열','other':'그 밖의 형태 또는 결합'}),
 'tense': ('문장이 나타내는 시간. 형태가 없는 경우에도 시간 표현과 문맥을 함께 본다.', {'past':'과거','present':'현재','future':'미래'}),
 'subject_honorific': ('서술어 주체를 높이는가. 시 형태뿐 아니라 주무시다 계시다 같은 높임 어휘도 포함. 듣는 사람 높임과 구별한다.', {'absent':'주체를 높이지 않음','present':'주체를 높임'}),
 'polarity': ('서술 내용의 긍정 부정. 안 못 아니다 등의 범위도 본다.', {'positive':'긍정','negative':'부정'}),
}
MACHINE = {'predicate_class','prefinal_type'}
PRESERVE = {'tense','polarity'}  # Existing Reader.packet interface requirements.
PROMPT = '''표준어 문장의 분석만 수행한다. 번역, 방언 어미 선택, KG ID 생성은 하지 않는다.
입력의 questions에는 실제 KG 조건/보존 정보에 필요한 질문과 선택지가 있다. 각 항목은 선택지 문구 그대로 답하고, 판단이 어려우면 null을 사용한다.
정보를 얻기 위한 질문은 '정보를 묻는 질문'이다. request라는 영어 단어의 일상적 의미와 혼동하지 말라. 행동 요청은 상대에게 행동을 시키거나 재촉하는 기능이다.
예: '몇 장 남았어?'는 구체적인 정보를 묻는다. '전화 좀 받아 줄래?'는 보통 행동을 요청한다. '벌써 끝났어?'는 사실 여부를 묻는다. 이 예시는 분류 설명이며 번역 예시가 아니다.
문맥 없는 문장은 일반적인 해석을 사용하되 실제로 두 해석이 경쟁하면 null로 남긴다. 확인을 구하는 모든 예/아니오 질문을 confirmation으로 분류하지 말라.
target_word_id는 문장 끝 서술어의 실제 어절 ID다. question_word_id는 구체적인 답을 묻는 말의 어절 ID다. 품사·선어말과 위치는 코드가 Kiwi에서 연결하므로 다시 작성하지 않는다. 주체 높임은 형태와 어휘 의미를 함께 판단한다.
judgments에는 제공된 질문에만 답한다. evidence_word_ids에는 판단에 사용한 어절 ID를 적는다. note는 40자 이내로 짧게 쓰고 장문 추론은 쓰지 않는다. JSON만 반환한다.'''

def inventory(graph):
 reader=RuntimeReader(graph, {'text':'','words':[]})
 rows=[]
 for key,values in graph['feature_schema'].items():
  conditions=[n['id'] for n in graph['nodes'] if n['type']=='Condition' and n['properties']['feature']==key]
  scope=[e['target'] for e in reader.scope_edges if key in reader.nodes[e['target']]['properties']['allowed']]
  feature_nodes=[n['id'] for n in graph['nodes'] if n['type']=='FeatureValue' and n['properties']['feature']==key]
  usage_edges=[e['id'] for e in graph['edges'] if e['relation']=='ALL' and e['target'] in conditions]
  relevant=bool(conditions or scope or key in PRESERVE)
  definition=DEFINITIONS.get(key)
  missing=[v for v in values if not definition or v not in definition[1]]
  rows.append({'feature':key,'values':values,'condition_ids':conditions,'scope_ids':scope,
    'feature_node_ids':feature_nodes,'condition_usage_edge_ids':usage_edges,'needed':relevant,
    'provider':'kiwi_observation' if key in MACHINE else 'kiwi_positive_and_qwen_semantics' if key=='subject_honorific' else 'qwen_semantic_judgment',
    'role':'usage_condition' if conditions else 'implementation_scope' if scope else 'preservation_only',
    'question':definition[0] if definition else None,'undefined_values':missing,
    'state':'definition_required' if relevant and missing else 'connected' if relevant else 'not_requested'})
 return {'graph_version':graph['version'],'construction_id':reader.family,'rows':rows,
  'conditions':[n for n in graph['nodes'] if n['type']=='Condition'],
  'scope':reader.policy,'observation_nodes':[n['id'] for n in graph['nodes'] if n['type']=='UsageObservation'],
  'limitations':['One grammar construction exists in this refined slice; this is not a general construction linker.',
    '7 conditions are executable via ACCEPTS/ALL. ProcessingScope is an implementation boundary, not a dialect prohibition.',
    'Realization composition and context observations remain descriptive text; this stage does not turn them into executable generation rules.',
    'Analysis definitions are an explicit adapter vocabulary. New feature semantics require a provider/definition, never silent exclusion.']}

def contract(graph):
 audit=inventory(graph)
 if any(r['state']=='definition_required' for r in audit['rows']):
  raise ValueError('graph_analysis_definition_required')
 keys=[r['feature'] for r in audit['rows'] if r['needed'] and r['provider']!='kiwi_observation']
 fields={k:{'type':['string','null'],'enum':[DEFINITIONS[k][1][v] for v in graph['feature_schema'][k]]+[None]} for k in keys}
 schema=obj({'target_word_id':{'type':['string','null']},'question_word_id':{'type':['string','null']},
  'judgments':obj(fields),'evidence_word_ids':{'type':'array','items':{'type':'string'},'maxItems':8},
  'note':{'type':'string','maxLength':40}})
 questions=[{'field':k,'question':DEFINITIONS[k][0],'choices':fields[k]['enum']} for k in keys]
 return schema,questions

def payload(graph,morph):
 _,questions=contract(graph)
 return {'text':morph['text'],'words':compact_morph(morph),'questions':questions}

def projected(word):
 parts=word['morphs'];derived=[i for i,(f,t) in enumerate(parts) if t.split('-')[0] in ('XSV','XSA')]
 if not derived:return old_projected(word)
 if len(derived)!=1:raise ValueError('multiple_derivational_predicates')
 i=derived[0]
 if not i or any(t.split('-')[0] not in ('NNG','NNP','XR','XPN') for f,t in parts[:i]):
  raise ValueError('unsupported_derivational_base')
 normalized=copy.deepcopy(word)
 normalized['morphs']=[[''.join(f for f,t in parts[:i+1]),'VV' if parts[i][1].split('-')[0]=='XSV' else 'VA']]+parts[i+1:]
 m,pc,pf=old_projected(normalized)
 m['projection_operation']='join_kiwi_nominal_root_and_predicate_derivational_suffix'
 m['source_morphs']=copy.deepcopy(parts)
 return m,pc,pf

class BridgeReader(RuntimeReader):
 def __init__(self,graph,morph,projector=None,construction=None):
  Reader.__init__(self,graph,construction) if construction else Reader.__init__(self,graph)
  self.morph=copy.deepcopy(morph);self.projector=projector or projected
 def morphology_status(self,c):
  needs,m=Reader.morphology_status(self,c)
  if not m or m.get('origin')!='kiwi_token_projection':return needs,m
  words=[w for w in self.morph['words'] if [w['start'],w['end']]==c['target_span'] and w['surface']==c['target_text']]
  if len(words)!=1:return needs+['kiwi_word_alignment_missing'],m
  expected,pc,pf=self.projector(words[0])
  if m!=expected:return needs+['kiwi_projection_mismatch'],m
  needs=[x for x in needs if x!='source_alignment_review']
  if c['features'].get('predicate_class')!=pc:needs.append('predicate_projection_disagreement')
  if c['features'].get('prefinal_type')!=pf:needs.append('prefinal_projection_disagreement')
  return sorted(set(needs)),m

def assemble(graph,raw,morph,projector=None):
 schema,_=contract(graph);validate_schema(raw,schema)
 words={w['uid']:w for w in morph['words']}
 if any(uid not in words for uid in raw['evidence_word_ids']):raise ValueError('evidence_word_not_found')
 if raw['target_word_id'] not in words:raise ValueError('target_unresolved_or_unknown')
 word=words[raw['target_word_id']];m,pc,pf=(projector or projected)(word)
 features={}
 for k,value in raw['judgments'].items():
  inverse={label:v for v,label in DEFINITIONS[k][1].items()}
  features[k]=inverse[value] if value is not None else None
 features.update(predicate_class=pc,prefinal_type=pf)
 observed_si=any(t.split('-')[0]=='EP' and f in ('시','으시') for f,t in word['morphs'])
 if observed_si:features['subject_honorific']='present'
 # Mechanical correction is explicit provenance, not a second model opinion.
 q=None
 if features.get('question_kind')=='wh':
  qw=words.get(raw['question_word_id'])
  if not qw:raise ValueError('question_word_unresolved_or_unknown')
  q={'id':'q1','span':[qw['start'],qw['end']],'surface':qw['surface'],'role':'asked_information','clause_id':'c1','scope_clause_id':'c1'}
 span=[word['start'],word['end']]
 analysis={'text':morph['text'],'origin':'kg_schema_guided_semantics_and_kiwi_observations','clauses':[{
  'id':'c1','span':[0,len(morph['text'])],'target_span':span,'target_text':word['surface'],'features':features,
  'feature_bindings':{k:{'clause_id':'c1','predicate_id':'p1' if k in ('predicate_class','prefinal_type','subject_honorific','tense','polarity') else None} for k in features},
  'predicate':{'id':'p1','clause_id':'c1','span':span,'surface':word['surface'],'origin':'kiwi_word_selected_by_qwen'},
  'ending_slot':{'id':'end1','clause_id':'c1','predicate_id':'p1','boundary_status':'whole_predicate_recomposition'},
  'question_variable':q,'morphology':m}]}
 c=analysis['clauses'][0]
 for k,b in c['feature_bindings'].items():
  b['origin']='kiwi_observed_morphology' if k in MACHINE else 'qwen_defined_choice_to_graph_value'
 if observed_si:c['feature_bindings']['subject_honorific']['origin']='kiwi_observed_si_overrides_semantic_choice'
 analysis['fusion_log']={'observed_si':observed_si,'qwen_subject_honorific':raw['judgments'].get('subject_honorific'),
  'final_subject_honorific':features['subject_honorific'],'absence_of_si_is_not_absence_of_honorific':True}
 # Exact function scope: do not silently turn a complex sentence into one main clause.
 boundaries=[w for w in morph['words'] if any(t.split('-')[0] in ('EC','ETM','ETN') for f,t in w['morphs'])]
 if boundaries:analysis['adapter_diagnostics']=['complex_construction_not_segmented']
 return analysis

def trace(graph,analysis,morph,projector=None,construction=None):
 reader=BridgeReader(graph,morph,projector,construction);query=reader.query(analysis);packet=reader.packet(analysis,query)
 f=analysis['clauses'][0]['features'];checks=[]
 for node in reader.conditions:
  p=node['properties'];v=f.get(p['feature']);known=isinstance(v,str)
  checks.append({'condition_id':node['id'],'feature':p['feature'],'observed':v,'allowed':p['allowed'],
    'state':'unknown' if not known else 'true' if v in p['allowed'] else 'false',
    'actual_accept_edges':[e['id'] for e in reader.links(node['id'],'ACCEPTS')],
    'feature_node':reader.feature_index.get((p['feature'],v)) if known else None})
 states={c['condition_id']:c for c in checks};branches=[]
 for bid,links in reader.branch_checks.items():
  cs=[states[e['target']] for e in links]
  branches.append({'branch_id':bid,'rule_id':reader.branch_owner[bid],
    'condition_state':'false' if any(c['state']=='false' for c in cs) else 'unknown' if any(c['state']=='unknown' for c in cs) else 'true',
    'condition_ids':[c['condition_id'] for c in cs],'failed_conditions':[c['condition_id'] for c in cs if c['state']=='false'],
    'unknown_conditions':[c['condition_id'] for c in cs if c['state']=='unknown']})
 if analysis.get('adapter_diagnostics'):
  for c in packet['clauses']:
   c['readiness']='needs_analysis';c['needs_analysis']+=analysis['adapter_diagnostics']
 return {'retrieval':query,'packet':packet,'all_condition_checks':checks,'all_branch_checks':branches,
  'feature_connections':[{'feature':k,'value':v,'origin':analysis['clauses'][0]['feature_bindings'][k]['origin'],
   'feature_node':reader.feature_index.get((k,v)) if isinstance(v,str) else None,
   'condition_ids':[n['id'] for n in reader.conditions if n['properties']['feature']==k],
   'scope_ids':[e['target'] for e in reader.scope_edges if k in reader.policy]} for k,v in f.items()]}
