"""Add explicit copular declarative / polite EO-question conditions, preserving r4."""
from pathlib import Path
import json,hashlib,copy
H=Path(__file__).resolve().parent;R=H.parents[2];PARENT=R/'knowledge/authored/semantic_grammar_20261103_r4/private/graph.json';OUT=R/'knowledge/authored/semantic_grammar_20261104_r6'
C=Path('C:/Users/ciot28/Documents/Codex/2026-10-13/ciotd-odor-complaint-dialect-rag-kg/work/source_audit')
def read(p):return json.loads(p.read_text('utf8'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n','utf8')
def main():
 g=read(PARENT);old=copy.deepcopy(g);ns={n['id']:n for n in g['nodes']};ss={s['id']:s for s in read(R/'knowledge/authored/kg_v3_evidence_20261019_r2/provenance/sources.json')}
 def node(id,t,**p):
  assert id not in ns,id
  ns[id]={'id':id,'type':t,'properties':p};return id
 def edge(a,r,b,**p):
  e={'id':'E_SUP_'+hashlib.sha256(json.dumps([a,r,b]).encode()).hexdigest()[:18],'source':a,'relation':r,'target':b,**p}
  if e not in g['edges']:g['edges'].append(e)
 def ev(id,d,p,q,meaning):
  text=read(C/f'{d}.json')[p-1]['text'];i=text.index(q);src=ss[d];pdf=Path('C:/Users/ciot28/Downloads/1')/src['filename'];assert hashlib.sha256(pdf.read_bytes()).hexdigest()==src['sha256']
  return node(id,'Evidence',document_id=d,pdf_page=p,page_system='PDF 1-based',quote=q,start=i,end=i+len(q),page_text_sha256=hashlib.sha256(text.encode()).hexdigest(),source_pdf_sha256=src['sha256'],source_family=src['policy']['family'],builder_paraphrase=meaning,evidence_kind='source_statement_or_example')
 ev('EV_SUP_COP_DIRECT','D02',199,'저거 아부지는 차암 저승서는 왕이라예.','긍정 계사 공손 평서 직접 용례')
 ev('EV_SUP_COP_RA','D02',198,'‘-라’는 계사와 결합하는데','계사 뒤 라 결합. 이 문장만으로 현재 높임형 전체가 직접 확인되는 것은 아님')
 ev('EV_SUP_COP_RAYE','D05',26,"'-이에요'는 '-이라요, (이래요[87])'라고 말하며 '-이에예'를 '-이라예'로라고 말한다 젊은 세대들은 '-이라요/-이라예'를 점점\n사용하지 않고 있다.",'긍정 현재 계사 해예형과 세대 변화. 위키 계통 자료이며 논문과 별도 출처')
 ev('EV_SUP_COP_EXAMPLE','D05',26,'싱싱한 과일이라예.','공손한 명사 서술 용례')
 ev('EV_SUP_COP_STANDARD_VARIATION','D04',21,'40대 이하부터 사용자가 급격히 줄어들고 표준어를 쓴다.','전통 라 활용과 표준형 사용 차이를 기록; 정확한 현대 사용비율은 이 진술로 산정 불가')
 ev('EV_SUP_COP_TRAD_PAST','D04',22,'-이라예-이랐어예아이라예아이랐어예','전통 현재/과거 긍정/부정 표. 이랐/아이랐을 강제하지 않고 후보 자료로 보존')
 ev('EV_SUP_POLITE_ALL_FUNCTIONS','D05',26,'해예체-어/아예-어/아예-어/아예-어/아예','표의 평서·명령·청유·의문 열 모두 어/아예. 이번 실행에서는 의문만 추가; PDF 표 육안 대조')
 ev('EV_SUP_QUESTION_HON','D02',57,'직접 보셨어예?','주체높임·과거·해예 질문 직접 용례')
 ev('EV_SUP_QUESTION_REGISTER','D02',214,'‘-요,-예’형태 중 하나와 결합해서\n쓰이면 해체보다 높은 등급이 된다.','의문법의 상대높임 결합 설명')
 decision=node('DEC_SUP_BOUNDED_EXTENSION','ImplementationDecision',title='해예체의 첫 지원 범위 확장',linguistic_fact=False,reason='새로운 어간 대체 없이 긍정 현재 계사·어요 질문만 연결. 과거·부정은 후속 후보로 보존. 완성형은 Qwen이 작성. 50개 정답 문장은 조건·프롬프트에 넣지 않는다.',deferred=['명령·약속·나요·ㄹ까요','현재 부정계사','의문사 소속 및 계세요 분석 충돌'])
 def cond(cx,key,vals,evs):
  id='COND_SUP_'+hashlib.sha256(json.dumps([cx,key,vals]).encode()).hexdigest()[:16]
  node(id,'Condition',feature=key,operator='in',allowed=vals,basis='source_interpretation_and_bounded_implementation',evidence_ids=evs,decision_id=decision)
  edge(id,'DEFINED_BY_DECISION',decision)
  for e in evs:edge(id,'INTERPRETS_SOURCE',e)
  for v in vals:
   found=next((n['id'] for n in ns.values() if n['type']=='FeatureValue' and n['properties'].get('feature')==key and n['properties'].get('value')==v),None)
   if found is None:found=node('FEATURE_SUP_'+hashlib.sha256((key+':'+v).encode()).hexdigest()[:16],'FeatureValue',feature=key,value=v)
   edge(id,'ACCEPTS',found)
  return id
 def rule(suffix,title,pc,pf,final,acts,ending,evs,composition,basis):
  rid='SEM_SUP_'+suffix;cx='SEM_CX_SUP_'+suffix
  node(cx,'GrammarConstruction',title=title,status='bounded_development_slice');scope='SCOPE_SUP_'+suffix
  allowed={'clause_role':['main'],'speech_act':acts,'addressee_level':['polite'],'predicate_class':pc,'prefinal_sequence':pf,'subject_honorific':['absent','present']}
  node(scope,'ProcessingScope',allowed=allowed,basis='implementation_scope_not_linguistic_prohibition',field_basis={k:{'kind':'source_interpretation_with_implementation_scope','evidence_ids':evs,'decision_id':decision} for k in allowed});edge(cx,'SUPPORTED_IN',scope);edge(scope,'DEFINED_BY_DECISION',decision)
  for ev in evs:edge(scope,'INTERPRETS_SOURCE',ev)
  for mod in ['M05','M06','M08','M11']:edge(cx,'IN_MODULE',mod)
  node(rid,'SemanticRule',title=title,meaning='원래 문장 기능·시제·높임을 유지하는 해예체 선택지',summary=title,status='source_interpreted_candidate',realization_basis=basis,primary_evidence_ids=evs,supporting_evidence_ids=[],preserve=['source_prefix','prefinals','polarity','subject_honorific','addressee_level'],generation_operation='replace_final_preserve_other_morphemes')
  edge(cx,'HAS_USAGE',rid);branch=rid+'/branch/0';node(branch,'ApplicabilityBranch',scope='same_clause');edge(rid,'ANY_BRANCH',branch)
  for key,vals in {**allowed,'source_final':final,**({'nominal_kind':['lexical_nominal']} if suffix=='COP_PRESENT' else {})}.items():edge(branch,'ALL',cond(cx,key,vals,evs))
  for ev in evs:edge(rid,'SUPPORTED_BY',ev,evidence_role='primary')
  f='FORM_SUP_'+suffix;node(f,'Realization',form='-'+ending,unit='final_ending',composition=composition,allomorphs=[],includes_copula=False,operation='replace_final_ending_preserve_stem_and_prefinals');edge(rid,'REALIZES',f)
  return rid
 g['feature_schema']['nominal_kind']=['lexical_nominal','bound_nominal','not_nominal','unknown']
 g['feature_schema']['source_final']=list(dict.fromkeys(g['feature_schema']['source_final']+['예요','에요']))
 rule('COP_PRESENT','긍정 현재 명사 서술의 라예',['copula'],['none'],['예요','에요'],['statement'],'라예',['EV_SUP_COP_DIRECT','EV_SUP_COP_RA','EV_SUP_COP_RAYE','EV_SUP_COP_EXAMPLE','EV_DECL_STRUCTURE'],'명사와 계사 이-를 보존하고 현재 종결 에요/예요를 라예로 바꾼다. 이-는 별도 어간이므로 중복하지 않는다. 일반적인 계사 축약은 Qwen이 판단한다. 과거에 이 규칙을 적용하지 않는다.','source_mapping_plus_morphological_composition; vowel contraction is not a separately attested dialect rule')
 node('CAND_SUP_COP_NEG_PAST','ResearchCandidate',title='과거 긍정·부정 계사 해예형 연결 후보',runtime_active=False,status='requires_further_evidence',reason='일반 해체+예 설명만으로 모든 조합을 인증하지 않음. 과거 이랐/아이랐 관찰과 표준어형 결합 추론을 분리해 후속 검토')
 edge('CAND_SUP_COP_NEG_PAST','SUPPORTED_BY','EV_SUP_COP_TRAD_PAST',evidence_role='documented_traditional_alternative_not_runtime_permission')
 rule('POLITE_Q_EO','어요로 끝나는 공손한 정보 질문',['verb','adjective'],['none','eoss','si','si_eoss'],['어요','아요'],['information_question'],'어예',['EV_SUP_POLITE_ALL_FUNCTIONS','EV_SUP_QUESTION_HON','EV_SUP_QUESTION_REGISTER','EV_DECL_STRUCTURE'],'질문 기능을 유지하고 -아/어요의 해체 부분과 실제 선어말을 보존하여 예를 결합한다. 문장부호 유지. 나요·ㄹ까요·명령으로 확대하지 않는다.','documented_question_construction_plus_compositional_generalization')
 # Cross-reference actual prior concept/card identities; they are not runtime certification.
 legacy={x['id']:x for x in map(json.loads,(R/'knowledge/authored/kg_v3_evidence_20261019_r2/graph/nodes.jsonl').read_text('utf8').splitlines())}
 for cid,rids in {'GS_ENDRULE_RA_COP':['SEM_SUP_COP_PRESENT'],'GS_END_DECL_YE_04':['SEM_SUP_COP_PRESENT'],'GS_PROFILE_HAEYE':['SEM_SUP_POLITE_Q_EO']}.items():
  assert cid in legacy
  if cid not in ns:node(cid,legacy[cid]['type'],title=legacy[cid].get('title') or legacy[cid]['properties'].get('original_spec',{}).get('_title'),origin='inherited_identity_only')
  for rid in rids:edge(cid,'DESCRIBES_USAGE',rid)
 g['nodes']=list(ns.values());g['version']='semantic_grammar_20261104_r6';g['generation_policy']['support_extension']='positive_copular_present_and_polite_EO_questions';g['generation_policy']['final_writer']='Qwen'
 assert all(ns[n['id']]==n for n in old['nodes']);assert all(e in g['edges'] for e in old['edges'])
 assert len(ns)==len(g['nodes']);assert all(e['source'] in ns and e['target'] in ns for e in g['edges'])
 save(OUT/'private/graph.json',g);save(OUT/'private/change_ledger.json',{'parent_sha256':hashlib.sha256(PARENT.read_bytes()).hexdigest(),'preserved_nodes':len(old['nodes']),'preserved_edges':len(old['edges']),'new_rules':2,'new_nodes':len(ns)-len(old['nodes']),'new_edges':len(g['edges'])-len(old['edges']),'exact_past_combinations':'not_direct_attestation; compositional_candidates','neo4j_imported':False})
 print('graph',len(ns),len(g['edges']),'rules',sum(n['type']=='SemanticRule' for n in ns.values()))
if __name__=='__main__':main()
