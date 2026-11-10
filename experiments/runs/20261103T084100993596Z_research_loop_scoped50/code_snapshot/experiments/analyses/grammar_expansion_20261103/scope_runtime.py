"""Target-specific scope binding; semantic labels remain model judgments, not facts."""
import copy,importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
s=importlib.util.spec_from_file_location('stable_pipeline',ROOT/'experiments/analyses/research_loop_20261103/pipeline.py')
base=importlib.util.module_from_spec(s);s.loader.exec_module(base)
bridge=base.bridge
PROMPT=base.PROMPT+"""
추가 scope에는 절 연결을 분석한다. boundary_words에 주어진 모든 어절을 한 번씩 boundary_links에 넣고, 그 안의 연결·관형·명사형 어미가 만드는 관계를 적는다.
relation은 adnominal(관형절), nominal(명사절), quoted(인용), linked(이유·조건·순서 등 이어진 절), auxiliary(본용언+보조용언), unknown 중 하나다.
head_word_id는 그 관계가 연결되는 실제 뒤쪽 어절이다. 보조용언이면 바로 다음 보조용언 어절 또는 같은 어절, 관형절이면 꾸밈을 받는 명사 어절, 나머지는 연결되는 서술어다.
question_scope는 선택한 question_word_id가 지금 target의 질문에서 구하는 정보이면 target, 다른 절 안의 미지정보이면 other, 판정질문이면 none, 불명확하면 unknown.
'누가 왔는지 알아?'는 누가를 바깥 질문의 의문사로 자동 선택하지 않는다. '아까 산 책을 어디에 뒀어?'에서는 어디가 바깥 질문에 연결된다.
auxiliary_class는 target 어절의 마지막 용언이 VX일 때 그 용언의 동사/형용사 성격을 verb/adjective로, 불확실하거나 VX가 아니면 null로 쓴다. '싶다/있다'를 일괄 동사로 처리하지 않는다.
"""
RELATIONS=['adnominal','nominal','quoted','linked','auxiliary','unknown']
def boundaries(morph):
 return [w for w in morph['words'] if any(t.split('-')[0] in ('EC','ETM','ETN') for f,t in w['morphs'])]
def schema_and_payload(graph,morph,uid,context):
 schema,user=base.schema_and_payload(graph,morph,uid,context);ids=[w['uid'] for w in morph['words']]
 schema['properties']['scope']=base.obj({'boundary_links':{'type':'array','items':base.obj({'word_id':{'type':'string','enum':ids},'relation':{'type':'string','enum':RELATIONS},'head_word_id':{'type':['string','null'],'enum':ids+[None]}})},'question_scope':{'type':'string','enum':['target','other','none','unknown']},'auxiliary_class':{'type':['string','null'],'enum':['verb','adjective',None]}})
 schema['required'].append('scope');user['boundary_words']=[{'id':w['uid'],'text':w['surface'],'morphs':w['morphs']} for w in boundaries(morph)]
 return schema,user

def projector_for(auxiliary_class):
 def project(word):
  ps=word['morphs'];hosts=[i for i,(f,t) in enumerate(ps) if t.split('-')[0] in ('VV','VA','VX','VCP','VCN','XSV','XSA')]
  if not hosts or ps[hosts[-1]][1].split('-')[0]!='VX':return bridge.projected(word)
  if auxiliary_class not in ('verb','adjective'):raise ValueError('auxiliary_class_unresolved')
  i=hosts[-1]
  if any(t.split('-')[0] not in ('EP','EF') for f,t in ps[i+1:]):raise ValueError('auxiliary_final_chain_unsupported')
  virtual=copy.deepcopy(word);tag='VV' if auxiliary_class=='verb' else 'VA'
  virtual['morphs']=[[ps[i][0],tag]]+ps[i+1:]
  m,pc,pf=bridge.old_projected(virtual)
  m.update(projection_operation='terminal_auxiliary_with_preserved_source_chain',source_morphs=copy.deepcopy(ps),auxiliary_class_origin='qwen_semantic_choice',auxiliary_index=i)
  return m,pc,pf
 return project

def scope_check(raw,morph,uid):
 scope=raw['scope'];words={w['uid']:w for w in morph['words']};expected={w['uid'] for w in boundaries(morph)}
 links=scope['boundary_links'];seen=[x['word_id'] for x in links];issues=[]
 if len(seen)!=len(set(seen)) or set(seen)!=expected:issues.append('boundary_coverage_mismatch')
 for link in links:
  w=words.get(link['word_id']);h=words.get(link['head_word_id']);r=link['relation']
  if not w or not h or r=='unknown':issues.append('boundary_relation_unresolved');continue
  tags={t.split('-')[0] for f,t in w['morphs']}
  if h['start']<w['start']:issues.append('backward_boundary_head')
  if r=='adnominal' and ('ETM' not in tags or not any(t.split('-')[0] in ('NNG','NNP','NNB','NP') for f,t in h['morphs'])):issues.append('adnominal_structure_mismatch')
  if r=='nominal' and not tags.intersection({'ETN','EC'}):issues.append('nominal_structure_mismatch')
  if r in ('quoted','linked') and 'EC' not in tags:issues.append('clause_connection_mismatch')
  if r=='auxiliary':
   if 'EC' not in tags or not any(t.split('-')[0]=='VX' for f,t in h['morphs']):issues.append('auxiliary_structure_mismatch')
   between=[x for x in morph['words'] if w['end']<=x['start']<h['start']]
   if between:issues.append('nonadjacent_auxiliary_unresolved')
 qkind=raw['judgments'].get('question_kind');q=raw.get('question_word_id')
 if qkind==bridge.DEFINITIONS['question_kind'][1]['wh']:
  if scope['question_scope']!='target' or q not in words:issues.append('question_scope_unresolved')
  else:
   for link in links:
    if link['relation'] in ('nominal','quoted') and link['word_id'] in words and words[q]['end']<=words[link['word_id']]['end']:issues.append('question_inside_embedded_or_quoted_span')
 elif scope['question_scope'] not in ('none','unknown'):issues.append('question_scope_kind_conflict')
 return sorted(set(issues))

def analyze_response(graph,raw,morph,uid):
 schema,_=schema_and_payload(graph,morph,uid,morph['text']);base.validate_schema(raw,schema)
 if raw['target_word_id']!=uid:raise ValueError('target_changed')
 project=projector_for(raw['scope']['auxiliary_class']);minimal={k:v for k,v in raw.items() if k!='scope'}
 a=bridge.assemble(graph,minimal,morph,projector=project)
 issues=scope_check(raw,morph,uid)
 a.pop('adapter_diagnostics',None)
 if issues:a['adapter_diagnostics']=issues
 a['scope_links']={'model_output':copy.deepcopy(raw['scope']),'structural_issues':issues,'status':'structure_checked_semantics_model_judged','limits':'Not a gold parse. Embedded-question WH transfer remains excluded.'}
 a['origin']='target_scoped_qwen_links_kiwi_positions_v3'
 return a,bridge.trace(graph,a,morph,projector=project)
