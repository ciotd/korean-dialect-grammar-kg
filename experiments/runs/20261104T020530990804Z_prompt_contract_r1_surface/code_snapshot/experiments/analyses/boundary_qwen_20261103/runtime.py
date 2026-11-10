"""Morpheme-indexed boundaries; shared KG queries; Qwen owns final sentence."""
import copy,hashlib,json,importlib.util
from pathlib import Path
H=Path(__file__).resolve().parent;ROOT=H.parents[2]
s=importlib.util.spec_from_file_location('boundary_parent',ROOT/'experiments/analyses/condition_followup_20261103/runtime.py');prior=importlib.util.module_from_spec(s);s.loader.exec_module(prior)
bridge=prior.bridge;base=prior.parent.scope.base;obj=base.obj
PRED={'VV','VA','VX','VCP','VCN','XSV','XSA'};NOUN={'NNG','NNP','NNB','NP','NR'}
PROMPT=base.PROMPT+'''
target_word_id, question_word_id, evidence_word_ids는 W1 같은 어절 번호만 쓴다. W1:M0 형태소 번호는 scope의 경계/head/소속 ID에서만 쓴다.
scope.boundary_links에는 제공된 경계 ID마다 관계와 head_id를 답한다. ID는 어절과 형태소 순번으로 구별한다. 한 어절 안 경계가 여러 개면 각각 답한다.
관계는 해당 어미가 형성하는 기능: auxiliary=본용언과 보조용언 연결, linked=이어진절 또는 용언을 꾸미는 부사절, quoted=인용절, nominal=명사화 또는 내포의문절, adnominal=관형절, unknown=미확정.
head_id는 바로 연결되는 용언 또는 명사 ID다. 어절 내부 보조용언도 별도 ID로 제공된다. source_host와 head가 같으면 안 된다. 관형절 전체 안에 있는 연결어미를 관형 어미로 분류하지 않는다.
EC 바로 뒤 같은 어절 또는 다음 어절에 VX가 관찰되면, 그 보조용언과 연결하거나 형태 분석이 의심될 때 unknown을 답한다. 그 VX를 건너뛰어 뒤의 용언으로 연결하지 않는다. 이는 이번 분석기의 관찰 형태를 기준으로 한 처리 계약이다.
ETN 뒤 조사가 붙어도 해당 경계는 명사화다. EC로 분석된 내포의문절은 nominal일 수 있다. VX 보조용언으로 바로 연결되는 관계를 일반 linked로 뭉개지 않는다. 형태 분석과 뜻이 충돌하면 unknown/null로 남긴다.
question_owner_id는 선택한 의문사가 속한 절의 용언 ID다. 별도 안긴절이면 그 절의 용언을 답한다. 판정질문이거나 의문사를 선택하지 않았으면 null. 불명확해도 null. 소속 관계는 코드가 이 답과 연결 사슬을 대조하므로 같은 내용을 중복 분류하지 않는다.
auxiliary_class는 목표의 마지막 용언이 VX인 경우에만 verb/adjective 중 의미 성격을 판단하며, 불확실하면 null이다. 나머지 경우 null.
'''

def inventory(morph):
 hosts=[];bounds=[];order=0
 for w in morph['words']:
  last=None
  for i,(f,t) in enumerate(w['morphs']):
   tag=t.split('-')[0];id=f"{w['uid']}:M{i}";order+=1
   if tag in PRED|NOUN:
    h={'id':id,'word_id':w['uid'],'morph_index':i,'form':f,'tag':tag,'order':order,'kind':'predicate' if tag in PRED else 'nominal'};hosts.append(h)
    if tag in PRED:last=id
   if tag in ('EC','ETM','ETN'):bounds.append({'id':id,'word_id':w['uid'],'morph_index':i,'form':f,'tag':tag,'order':order,'source_host':last})
 snapshot=hashlib.sha256(json.dumps(morph['words'],ensure_ascii=False,sort_keys=True).encode()).hexdigest()
 return hosts,bounds,snapshot

def adjacent_auxiliary(boundary,hosts,morph):
 if boundary['tag']!='EC':return None
 following=next((h for h in hosts if h['order']>boundary['order']),None)
 positions={w['uid']:i for i,w in enumerate(morph['words'])}
 if following and following['tag']=='VX' and positions[following['word_id']]-positions[boundary['word_id']] in (0,1):return following
 return None

def schema_and_payload(graph,morph,uid,context):
 schema,user=base.schema_and_payload(graph,morph,uid,context);hosts,bounds,snapshot=inventory(morph);fields={}
 word_ids=[w['uid'] for w in morph['words']]
 schema['properties']['evidence_word_ids']={'type':'array','items':{'type':'string','enum':word_ids}}
 schema['properties']['question_word_id']={'type':['string','null'],'enum':word_ids+[None]}
 for b in bounds:
  rel={'ETM':['adnominal','unknown'],'ETN':['nominal','unknown'],'EC':['auxiliary','linked','quoted','nominal','unknown']}[b['tag']]
  heads=[h['id'] for h in hosts if h['order']>b['order'] and (h['kind']=='nominal' if b['tag']=='ETM' else True)]
  variants=[];options={};adjacent=adjacent_auxiliary(b,hosts,morph)
  for relation in rel:
   choices=[]
   for h in hosts:
    if h['id'] not in heads:continue
    if adjacent and (relation!='auxiliary' or h['id']!=adjacent['id']):continue
    if relation=='auxiliary' and (h['tag']!='VX' or any(b['order']<x['order']<h['order'] for x in hosts)):continue
    if relation in ('linked','quoted') and h['kind']!='predicate':continue
    if b['tag']=='EC' and relation not in ('auxiliary','unknown') and h['tag']=='VX' and not any(b['order']<x['order']<h['order'] for x in hosts):continue
    if relation=='unknown':continue
    choices.append(h['id'])
   if choices or relation=='unknown':
    options[relation]=choices+[None] if relation=='unknown' else choices
    variants.append(obj({'relation':{'type':'string','enum':[relation]},'head_id':{'type':['string','null'],'enum':options[relation]}}))
  fields[b['id']]={'anyOf':variants};b['structural_head_options']=options
 schema['properties']['scope']=obj({'boundary_links':obj(fields),'question_owner_id':{'type':['string','null'],'enum':[h['id'] for h in hosts if h['kind']=='predicate']+[None]},'auxiliary_class':{'type':['string','null'],'enum':['verb','adjective',None]}})
 schema['required'].append('scope');user.update(boundary_inventory=bounds,head_inventory=hosts,morphology_snapshot_sha256=snapshot,target_host_id=next((h['id'] for h in reversed(hosts) if h['word_id']==uid and h['kind']=='predicate'),None))
 return schema,user

def structural_check(raw,morph,uid):
 hosts,bounds,snapshot=inventory(morph);hs={h['id']:h for h in hosts};links=raw['scope']['boundary_links'];issues=[];edges=[]
 target=next((h['id'] for h in reversed(hosts) if h['word_id']==uid and h['kind']=='predicate'),None)
 for b in bounds:
  v=links[b['id']];head=hs.get(v['head_id']);rel=v['relation'];src=hs.get(b['source_host'])
  if rel=='unknown' or head is None:issues.append('boundary_relation_unresolved');continue
  if src is None:issues.append('boundary_source_host_unresolved');continue
  adjacent=adjacent_auxiliary(b,hosts,morph)
  if adjacent and (rel!='auxiliary' or head['id']!=adjacent['id']):issues.append('adjacent_VX_skipped_requires_review')
  if head['order']<=b['order']:issues.append('backward_or_self_boundary')
  if rel=='auxiliary':
   intervening=[h for h in hosts if b['order']<h['order']<head['order']]
   if b['tag']!='EC' or head['tag']!='VX' or intervening:issues.append('auxiliary_structure_mismatch')
  if rel in ('linked','quoted') and head['kind']!='predicate':issues.append('clause_head_not_predicate')
  if b['tag']=='EC' and head['tag']=='VX' and rel!='auxiliary' and not any(b['order']<h['order']<head['order'] for h in hosts):issues.append('adjacent_nonauxiliary_relation_to_VX_requires_review')
  if rel=='adnominal' and (b['tag']!='ETM' or head['kind']!='nominal'):issues.append('adnominal_structure_mismatch')
  edges.append({'boundary_id':b['id'],'source_host':src['id'],'head_id':head['id'],'relation':rel})
 for e in edges:
  if hs[e['head_id']]['tag']=='VX' and e['relation']!='auxiliary' and not any(x['relation']=='auxiliary' and x['head_id']==e['head_id'] for x in edges):issues.append('remote_auxiliary_head_chain_unresolved')
 # Within a terminal word, only an explicitly linked auxiliary chain is supported.
 for e in edges:
  if hs[e['source_host']]['word_id']==uid and e['source_host']!=target:
   if e['relation']!='auxiliary' or hs[e['head_id']]['word_id']!=uid:issues.append('internal_terminal_chain_unresolved')
 chain={target};changed=True
 while changed:
  old=set(chain);chain.update(e['source_host'] for e in edges if e['relation']=='auxiliary' and e['head_id'] in chain);changed=old!=chain
 if raw['judgments'].get('question_kind')==bridge.DEFINITIONS['question_kind'][1]['wh']:
  if raw['scope']['question_owner_id'] not in chain:issues.append('question_owner_not_target_or_auxiliary_chain')
 return sorted(set(issues)),edges,chain,snapshot

def analyze_response(graph,raw,morph,uid):
 schema,_=schema_and_payload(graph,morph,uid,morph['text']);base.validate_schema(raw,schema)
 project=prior.projector_factory(raw['scope']['auxiliary_class']);a=bridge.assemble(graph,{k:v for k,v in raw.items() if k!='scope'},morph,projector=project)
 issues,edges,chain,snapshot=structural_check(raw,morph,uid);a.pop('adapter_diagnostics',None)
 if issues:a['adapter_diagnostics']=issues
 a.update(origin='qwen_per_morpheme_boundary_v6',scope_links={'model_output':raw['scope'],'edges':edges,'structural_issues':issues,'morphology_snapshot_sha256':snapshot,'meaning_correctness':'model_judgment_not_gold'})
 c=a['clauses'][0];f=c['features'];final=c['morphology']['source_final'];f['source_final']=final if final in graph['feature_schema']['source_final'] else 'other'
 pf=tuple('었' if x in ('았','었','였') else '시' if x in ('시','으시') else x for x in c['morphology']['prefinals']);f['prefinal_sequence']={(): 'none',('었',):'eoss',('시',):'si',('시','었'):'si_eoss'}.get(pf,'other')
 for k in ('source_final','prefinal_sequence'):c['feature_bindings'][k]={'clause_id':c['id'],'predicate_id':'p1','origin':'kiwi_observed_morphology'}
 c['feature_bindings']['predicate_class']['origin']='qwen_auxiliary_class_with_observed_VX' if c['morphology'].get('terminal_host',{}).get('original_tag','').startswith('VX') else 'kiwi_observed_predicate_class'
 if f['predicate_class'] is None:c['feature_bindings']['predicate_class']['origin']='qwen_unresolved_with_observed_VX'
 if c['feature_bindings']['subject_honorific']['origin']=='qwen_defined_choice_to_graph_value':c['feature_bindings']['subject_honorific']['origin']='model_judgment_no_observable_si'
 observed=[]
 if not issues:
  for w in morph['words']:
   current=None
   for i,(form,tag) in enumerate(w['morphs']):
    if tag.split('-')[0] in PRED:current=f"{w['uid']}:M{i}"
    if current in chain and tag.split('-')[0]=='EP' and form in ('시','으시'):observed.append({'word_id':w['uid'],'morph_index':i,'form':form})
 if observed:f['subject_honorific']='present';c['feature_bindings']['subject_honorific'].update(origin='observed_si_in_explicit_auxiliary_chain',evidence_morphemes=observed)
 if c.get('question_variable'):c['question_variable']['source_owner_host_id']=raw['scope']['question_owner_id']
 traces=[bridge.trace(graph,a,morph,projector=project,construction=n['id']) for n in graph['nodes'] if n['type']=='GrammarConstruction']
 for t in traces:
  q=t['retrieval']['clauses'][0];p=t['packet']['clauses'][0]
  if q['state']=='out_of_slice':p['readiness']='out_of_slice'
 ready=[t for t in traces if t['packet']['clauses'][0]['readiness']=='ready_for_generation_trial'];matched=[t for t in traces if t['retrieval']['clauses'][0]['state']=='eligible'];unknown=[t for t in traces if t['retrieval']['clauses'][0]['state']=='unresolved']
 selected=copy.deepcopy((ready or matched or unknown or traces)[0])
 if len(ready)>1:selected['packet']['clauses'][0].update(readiness='needs_analysis',needs_analysis=['multiple_constructions_require_selection'])
 selected['construction_queries']=traces;selected['diagnosis_axes']={'structural_issues':issues,'all_analysis_issues':sorted({x for t in traces for x in t['packet']['clauses'][0]['needs_analysis']}),'construction_states':{t['retrieval']['construction_id']:t['retrieval']['clauses'][0]['state'] for t in traces}}
 selected['condition_provenance']={n['id']:{'basis':n['properties'].get('basis'),'evidence_ids':n['properties'].get('evidence_ids',[]),'decision_id':n['properties'].get('decision_id'),'edges':[e for e in graph['edges'] if e['source']==n['id'] and e['relation'] in ('INTERPRETS_SOURCE','DEFINED_BY_DECISION')]} for n in graph['nodes'] if n['id'].startswith('COND_DECL_')}
 return a,selected

generation_payload=prior.generation_payload
preservation_check=prior.preservation_check
GENERATION_PROMPT='''표준어 입력 전체를 전달된 KG 문법 정보에 따라 경상도 방언 문장으로 생성한다. 최종 문장 전체를 output_text에 적는다.
actions에는 조건을 확인한 위치, 실제 형태소, 보존할 선어말, 바꿀 종결어미와 KG 결합형이 있다. 활용의 축약·불규칙은 네가 판단해 자연스러운 어절로 조합한다. 완성형 정답은 제공되지 않는다.
composition과 structure_evidence는 KG의 결합 설명이다. 설명 중 Kiwi 언급은 과거 구현 정보이며 이번 최종 문장은 네가 직접 생성한다. 음운 축약·불규칙만 적용하고 제공된 결합형 외의 방언 어미 변이를 만들지 않는다. 해체+예 구조에서는 해체 형태를 유지한다. forms는 적용 가능한 결합형만 포함한다.
각 action의 어휘·시제 형태·부정·주체높임·상대높임·문장 기능을 보존한다. 계사가 이미 포함된 결합형에는 이-를 중복하지 않는다. 원문 밖의 뜻이나 새로운 방언 규칙은 만들지 않는다.
현재 KG가 지원한 actions 위치만 고치고 그 밖의 글자·띄어쓰기·문장부호는 유지한다. 여러 actions가 있으면 한 번에 반영해 전체 문장을 반환한다. actions가 비어 있으면 원문 전체를 그대로 출력하고 status=unchanged로 답한다.
조합할 수 없으면 status=needs_review와 이유를 쓰고 가능한 출력도 보존한다. 생성하면 generated, 바뀌지 않았으면 unchanged. JSON만 출력한다.'''
GENERATION_SCHEMA=obj({'output_text':{'type':'string','maxLength':2000},'status':{'type':'string','enum':['generated','unchanged','needs_review']},'reason':{'type':'string','maxLength':500}})
