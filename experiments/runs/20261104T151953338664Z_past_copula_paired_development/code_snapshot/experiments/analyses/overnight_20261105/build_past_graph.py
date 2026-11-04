"""Add a bounded compositional candidate; retain all r7 facts and conditions."""
from pathlib import Path
import json,hashlib,copy
R=Path(__file__).resolve().parents[3];H=Path(__file__).resolve().parent
PARENT=R/'knowledge/authored/semantic_grammar_20261104_r7/private/graph.json'
OUT=R/'knowledge/authored/semantic_grammar_20261105_r10'
CX='SEM_CX_EXT_COP_PAST';RULE='SEM_EXT_COP_PAST_HAEYE'

def make():
 g=json.loads(PARENT.read_text('utf8'));old=copy.deepcopy(g);nodes={n['id']:n for n in g['nodes']}
 def node(id,t,**p):
  assert id not in nodes;nodes[id]={'id':id,'type':t,'properties':p};return id
 def edge(a,rel,b,**props):
  g['edges'].append({'id':'E_EXT_'+hashlib.sha256((a+'|'+rel+'|'+b).encode()).hexdigest()[:18],'source':a,'relation':rel,'target':b,**props})
 decision=node('DEC_EXT_COP_PAST','ImplementationDecision',title='과거 긍정/부정 계사 해체+예 조합의 제한된 실험',linguistic_fact=False,status='experimental_candidate',basis='D02 PDF203 construction description plus user-approved reference choice; exact generalized outputs are not direct quotations',user_reference_role='target variety preference, not sentence lookup or proof for all lexical combinations',preserve=['lexical_meaning','past_form','polarity','addressee_level'],excluded=['present negative copula','bound nominal','honorific si','questions','traditional iratt/airatt lexical replacement'])
 node(CX,'GrammarConstruction',title='과거 긍정·부정 계사 평서의 해예체',status='bounded_experimental_extension')
 scope={'clause_role':['main'],'speech_act':['statement'],'addressee_level':['polite'],'predicate_class':['copula','negative_copula'],'prefinal_sequence':['eoss'],'subject_honorific':['absent']}
 sid=node('SCOPE_EXT_COP_PAST','ProcessingScope',allowed=scope,basis='implementation_scope_not_linguistic_prohibition',decision_id=decision)
 edge(CX,'SUPPORTED_IN',sid);edge(sid,'DEFINED_BY_DECISION',decision)
 for mod in ('M02','M05','M06','M08','M11'):edge(CX,'IN_MODULE',mod)
 node(RULE,'SemanticRule',title='과거 계사 해체 부분 보존 + 예',meaning='과거 긍정·부정 서술과 상대높임을 유지하는 해예체 조합 후보',summary='원문의 계사·부정·과거 형태를 유지하고 해체 뒤 예를 결합',primary_evidence_ids=['EV_DECL_STRUCTURE'],supporting_evidence_ids=[],delivery_evidence_ids=['EV_DECL_STRUCTURE'],realization_basis='construction_generalization_and_user_target_preference_not_direct_attestation_of_each_surface',status='compositional_candidate_for_controlled_trial',generation_operation='replace_final_preserve_other_morphemes',preserve=['source_prefix','prefinals','polarity','subject_honorific','addressee_level'])
 edge(CX,'HAS_USAGE',RULE);edge(RULE,'SUPPORTED_BY','EV_DECL_STRUCTURE',evidence_role='primary');edge(RULE,'DEFINED_BY_DECISION',decision);edge(RULE,'REFINES_CANDIDATE','CAND_SUP_COP_NEG_PAST')
 for eid,role in [('EV_DECL_HON_SI','same_prefinal_other_predicate_class'),('EV_DECL_NE_YE','same_prefinal_other_ending'),('EV_DECL_GEODEUN_YE','same_prefinal_other_ending'),('EV_SUP_COP_TRAD_PAST','competing_traditional_realization')]:
  assert eid in nodes
  edge(RULE,'HAS_CONTEXT_EVIDENCE',eid,evidence_role=role,licenses_this_rule=False)
 for branch,pc,pol,nk in [('positive','copula','positive','lexical_nominal'),('negative','negative_copula','negative','not_nominal')]:
  bid=node(RULE+'/branch/'+branch,'ApplicabilityBranch',scope='same_clause');edge(RULE,'ANY_BRANCH',bid)
  conditions={**scope,'predicate_class':[pc],'source_final':['어요'],'polarity':[pol]}
  if branch=='positive':conditions['nominal_kind']=[nk]
  for key,vals in conditions.items():
   cid='COND_EXT_'+branch+'_'+key;node(cid,'Condition',feature=key,operator='in',allowed=vals,basis='implementation_trial_scope',evidence_ids=[],decision_id=decision)
   edge(bid,'ALL',cid);edge(cid,'DEFINED_BY_DECISION',decision)
   for val in vals:
    fid=next((n['id'] for n in nodes.values() if n['type']=='FeatureValue' and n['properties'].get('feature')==key and n['properties'].get('value')==val),None)
    if fid is None:fid=node('FV_EXT_'+key+'_'+val,'FeatureValue',feature=key,value=val)
    edge(cid,'ACCEPTS',fid)
 form=node('FORM_EXT_COP_PAST_HAEYE','Realization',form='-어예',unit='final_ending',composition='원문 계사/아니다의 해체 부분을 그대로 보존하고 상대높임 요만 예로 바꾼다. 원문의 았/었/였을 지우거나 계사 이-를 다시 넣지 않는다. 명사와 부정 의미를 유지한다.',allomorphs=[],includes_copula=False,surface_postcondition='original_target[:-1]+예 when original_target endswith 요')
 edge(RULE,'REALIZES',form);g['nodes']=list(nodes.values());g['version']='semantic_grammar_20261105_r10';g['generation_policy']['support_extension']='r7_plus_bounded_past_positive_negative_copula';g['generation_policy']['candidate_not_promoted']=True
 assert all(nodes[n['id']]==n for n in old['nodes']);assert all(e in g['edges'] for e in old['edges'])
 assert len({e['id'] for e in g['edges']})==len(g['edges']);assert all(e['source'] in nodes and e['target'] in nodes for e in g['edges'])
 return g,{'parent':str(PARENT),'parent_sha256':hashlib.sha256(PARENT.read_bytes()).hexdigest(),'old_nodes_unchanged':True,'old_edges_preserved':True,'new_nodes':len(g['nodes'])-len(old['nodes']),'new_edges':len(g['edges'])-len(old['edges']),'new_rules':[RULE],'neo4j_imported':False,'knowledge_status':'candidate generalization, not full-sentence attestation'}

if __name__=='__main__':
 g,ledger=make();(OUT/'private').mkdir(parents=True,exist_ok=True)
 for n,v in [('graph.json',g),('change_ledger.json',ledger)]:
  p=OUT/'private'/n
  if p.exists() and json.loads(p.read_text('utf8'))!=v:raise RuntimeError('Version already exists with different content')
  p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 (OUT/'README.md').write_text('# r10 과거·부정 계사 조합 후보\n\nr7의 기존 노드·관계를 보존하고 과거 긍정/부정 계사 평서의 해체+예 조합 후보를 추가했다. 문헌의 일반 구성 설명과 사용자 승인 선택을 바탕으로 한 연구자 일반화이며 각 완성형의 직접 문헌 인증이 아니다. 실험 후보이며 기본 KG로 채택하지 않았다. Neo4j 적재 미실행. 세부 데이터는 private에 보존.\n',encoding='utf8')
 print(json.dumps(ledger,ensure_ascii=False))
