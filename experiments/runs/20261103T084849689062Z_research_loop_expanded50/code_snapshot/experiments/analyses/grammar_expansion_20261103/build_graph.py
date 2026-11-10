import copy,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
PARENT=ROOT/'knowledge/authored/semantic_questions_20261102_r3/private/graph.json'
OUT=ROOT/'knowledge/authored/semantic_grammar_20261103_r1'
CACHE=Path('C:/Users/ciot28/Documents/Codex/2026-10-13/ciotd-odor-complaint-dialect-rag-kg/work/source_audit')
def read(p):return json.loads(p.read_text('utf8'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n','utf8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 g=read(PARENT);old=copy.deepcopy(g);nodes={n['id']:n for n in g['nodes']};edges=g['edges'];ledger=[]
 def node(id,type,**props):
  n={'id':id,'type':type,'properties':props}
  if id in nodes and nodes[id]!=n:raise ValueError('conflicting_node:'+id)
  nodes[id]=n;return id
 def edge(a,r,b,**props):
  e={'id':'E_'+hashlib.sha256(json.dumps([a,r,b],ensure_ascii=False).encode()).hexdigest()[:20],'source':a,'relation':r,'target':b,**props}
  if e not in edges:edges.append(e)
 def condition(key,values):
  id='COND_DECL_'+hashlib.sha256(json.dumps([key,values]).encode()).hexdigest()[:14]
  node(id,'Condition',feature=key,allowed=values,operator='in',basis='source_interpretation_and_explicit_experimental_scope')
  for v in values:
   found=next((n['id'] for n in nodes.values() if n['type']=='FeatureValue' and n['properties']=={'feature':key,'value':v}),None)
   f=found or node('FEATURE_DECL_'+hashlib.sha256((key+':'+v).encode()).hexdigest()[:14],'FeatureValue',feature=key,value=v)
   edge(id,'ACCEPTS',f)
  return id
 ss={s['id']:s for s in read(ROOT/'knowledge/authored/kg_v3_evidence_20261019_r2/provenance/sources.json')}
 def evidence(id,doc,p,quote,meaning):
  text=read(CACHE/(doc+'.json'))[p-1]['text'];start=text.find(quote)
  if start<0:raise ValueError('missing_quote:'+id)
  src=ss[doc];pdf=Path('C:/Users/ciot28/Downloads/1')/src['filename']
  if sha(pdf)!=src['sha256']:raise ValueError('source_pdf_changed')
  node(id,'Evidence',document_id=doc,pdf_page=p,page_system='PDF 1-based',quote=quote,start=start,end=start+len(quote),page_text_sha256=hashlib.sha256(text.encode()).hexdigest(),source_pdf_sha256=src['sha256'],source_family=src['policy']['family'],builder_paraphrase=meaning,evidence_kind='direct_source_description',source_scope='문헌의 지역·시기 범위를 보존. 모든 경상도 화자의 의무형이 아님.')
  ledger.append({'document':doc,'pdf_page':p,'quote_exact_match':True,'pdf_sha256_verified':True})
 evidence('EV_DECL_STRUCTURE','D02',203,'비격식체인 해요체,해예체,해여체는 대부분의 형태가 ‘해체+요/예/여’의\n구조를 가진다.','해체 형태와 상대높임 표현의 결합 구조. 생성된 모든 완성 문장을 직접 인용한 것은 아니다.')
 evidence('EV_DECL_A_YE','D02',205,'올라 앉아예.','-아예의 서술 용례.')
 evidence('EV_DECL_NE_YE','D02',202,'거 잔치 잘했네예.','과거 선어말 뒤 -네예 용례.')
 evidence('EV_DECL_GEODEUN_YE','D02',205,'근처를 가 봤거든예.','보조용언+과거+-거든예 용례.')
 evidence('EV_DECL_EO_YE','D05',27,'더 힘들어예.','-어예 서술 용례. 위키 전사 자료로 논문과 구별한다.')
 cx=node('SEM_CX_HAEYE_DECLARATIVE','GrammarConstruction',title='해요체 평서의 해예체 실현',status='bounded_development_slice',choice_policy='attested_regional_option_not_panregional_obligation')
 for mod in ('M05','M06','M08','M11'):edge(cx,'IN_MODULE',mod)
 scope=node('SCOPE_HAEYE_DECLARATIVE_R1','ProcessingScope',allowed={'clause_role':['main'],'speech_act':['statement','exclamation'],'addressee_level':['polite'],'predicate_class':['verb','adjective'],'prefinal_type':['none','eoss','other'],'subject_honorific':['absent','present']},basis='implementation_scope_not_linguistic_prohibition')
 edge(cx,'SUPPORTED_IN',scope)
 g['feature_schema']['source_final']=['아요','어요','네요','거든요','other']
 inherited={n['id']:n for n in [json.loads(l) for l in (ROOT/'knowledge/authored/kg_v3_evidence_20261019_r2/graph/nodes.jsonl').read_text('utf8').splitlines()]}
 for src,dst,eid in [('아요','아예','EV_DECL_A_YE'),('어요','어예','EV_DECL_EO_YE'),('네요','네예','EV_DECL_NE_YE'),('거든요','거든예','EV_DECL_GEODEUN_YE')]:
  rid='SEM_DECL_HAEYE_'+{'아요':'A','어요':'EO','네요':'NE','거든요':'GEODEUN'}[src]
  node(rid,'SemanticRule',title='-'+src+' → -'+dst,meaning='원래 평서 기능과 상대높임을 유지한 해예체 선택지',summary='확인된 종결 구성만 바꾸고 나머지 형태소를 보존',primary_evidence_ids=['EV_DECL_STRUCTURE',eid],supporting_evidence_ids=[],realization_basis='source_construction_plus_compositional_generalization_not_sentence_gold',status='source_interpreted_candidate',generation_operation='replace_final_preserve_other_morphemes',preserve=['source_prefix','prefinals','polarity','subject_honorific','addressee_level'],limits=['계사·부정계사·약속·명령·확인·회상형은 이 묶음 대상 아님','완성형은 조합 결과이며 원문 인용과 구별','정확한 원문 요→예 표면 불변식으로 교차 검사'])
  edge(cx,'HAS_USAGE',rid)
  for ev in ['EV_DECL_STRUCTURE',eid]:edge(rid,'SUPPORTED_BY',ev,evidence_role='primary')
  bid=node(rid+'/branch/0','ApplicabilityBranch',scope='same_clause');edge(rid,'ANY_BRANCH',bid)
  for key,vals in {'source_final':[src],'speech_act':['statement','exclamation'] if src=='네요' else ['statement']}.items():edge(bid,'ALL',condition(key,vals))
  f=node('FORM_DECL_'+dst,'Realization',form='-'+dst,unit='final_ending',composition='원문 마지막 EF만 선택 결합형으로 교체. 선어말과 어간을 보존하고 Kiwi로 결합.',allomorphs=[],surface_postcondition='original_target[:-1]+예 when original_target endswith 요')
  edge(rid,'REALIZES',f)
  for cid in ['G_REGISTER_MAP','G_REGISTER_VARIATION']:
   if cid not in inherited:raise ValueError('unknown_original_concept:'+cid)
   if cid not in nodes:
    orig=inherited[cid];node(cid,orig['type'],title=orig.get('title'),origin='inherited_identity_only')
   edge(cid,'DESCRIBES_USAGE',rid)
 g['version']='semantic_grammar_20261103_r1';g['nodes']=list(nodes.values());g['generation_policy']={'scope':'question_and_bounded_haeye_declarative','preserve_prefinal_morphemes':True,'lexeme_replacement':False,'new_statement_candidates':4,'legacy_question_rules_unchanged':True}
 assert all(nodes[n['id']]==n for n in old['nodes'])
 assert all(e in g['edges'] for e in old['edges'])
 save(OUT/'private/graph.json',g);save(OUT/'private/refinement_ledger.json',{'parent_sha256':sha(PARENT),'parent_nodes_preserved':len(old['nodes']),'parent_edges_preserved':len(old['edges']),'new_nodes':len(nodes)-len(old['nodes']),'new_edges':len(edges)-len(old['edges']),'reading':ledger,'visual_checked_pages':['D02:203','D02:205'],'interpretation':'Semantic extension from documented constructions; not all generated combinations directly attested. Regional metadata is retained, not a required user setting.'})
 print({'nodes':len(nodes),'edges':len(edges),'semantic_rules':sum(n['type']=='SemanticRule' for n in nodes.values())})
if __name__=='__main__':main()
