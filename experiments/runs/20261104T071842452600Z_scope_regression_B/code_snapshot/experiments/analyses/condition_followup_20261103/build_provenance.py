"""Add condition-level provenance without changing any accepted feature values."""
import json,copy,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
PARENT=ROOT/'knowledge/authored/semantic_grammar_20261103_r2/private/graph.json';OUT=ROOT/'knowledge/authored/semantic_grammar_20261103_r3'
def read(p):return json.loads(p.read_text('utf8'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n','utf8')
def main():
 g=read(PARENT);before=copy.deepcopy(g);nodes={n['id']:n for n in g['nodes']};mapping=[]
 def add(id,type,**p):nodes[id]={'id':id,'type':type,'properties':p};return id
 def edge(a,r,b,**p):
  id='E_PROV_'+hashlib.sha256(json.dumps([a,r,b]).encode()).hexdigest()[:18]
  x={'id':id,'source':a,'relation':r,'target':b,**p}
  if x not in g['edges']:g['edges'].append(x)
 add('DEC_DECL_OBSERVED_FINAL','ImplementationDecision',title='Kiwi 관찰 종결형으로 표준어 입력 위치를 연결',reason='문헌의 요/예 구성을 입력 분석기의 정규화된 EF에 대응한다. 아요를 어요로 정규화하는 것은 분석기 계약이지 방언 문헌 진술이 아니다.',code_reference='src/kg_runtime/morphology.py; grammar_expansion_20261103/expanded_runtime.py',linguistic_fact=False)
 add('DEC_DECL_PREFINAL_SCOPE','ImplementationDecision',title='첫 실험의 선어말 지원 범위',reason='없음·었·시·시+었을 우선 지원한다. 문헌이 이 네 경우만 허용한다고 주장하지 않는다. 그 밖은 비문이 아니라 미지원이다.',allowed=['none','eoss','si','si_eoss'],linguistic_fact=False)
 add('DEC_DECL_FUNCTION_LABELS','ImplementationDecision',title='서술법을 모델의 평서·감탄 라벨에 대응',reason='원문 서술법 분류와 보존할 네 표현을 모델 라벨에 연결한 해석이다. 모든 감탄 표현을 네예로 바꾸지 않는다.',linguistic_fact=False)
 src=read(ROOT/'knowledge/authored/kg_v3_evidence_20261019_r2/provenance/sources.json');source=next(x for x in src if x['id']=='D02')
 cache=Path('C:/Users/ciot28/Documents/Codex/2026-10-13/ciotd-odor-complaint-dialect-rag-kg/work/source_audit/D02.json');text=read(cache)[202]['text'];quote='<표 47> 해요체/해예체/해여체 서술법 종결어미';start=text.index(quote)
 pdf=Path('C:/Users/ciot28/Downloads/1')/source['filename'];assert hashlib.sha256(pdf.read_bytes()).hexdigest()==source['sha256']
 add('EV_DECL_CLASSIFICATION','Evidence',document_id='D02',pdf_page=203,page_system='PDF 1-based',quote=quote,start=start,end=start+len(quote),page_text_sha256=hashlib.sha256(text.encode()).hexdigest(),source_pdf_sha256=source['sha256'],source_family=source['policy']['family'],evidence_kind='source_section_classification',builder_paraphrase='표47은 해예 종결형들을 서술법 아래 정리한다. 현대 모델의 기능 라벨과 동일한 분류라는 뜻은 아니다.',source_scope='기존 경북 대계 문헌 자료; 분류명과 라벨 대응을 구별')
 text=read(cache)[200]['text'];quote='해요체,해예체,해여체는 대부분 해체의 종결어미와 결합하여 [+높임]의\n자질을 갖는다.';start=text.index(quote)
 add('EV_DECL_ADDRESSEE_DECL_SECTION','Evidence',document_id='D02',pdf_page=201,page_system='PDF 1-based',quote=quote,start=start,end=start+len(quote),page_text_sha256=hashlib.sha256(text.encode()).hexdigest(),source_pdf_sha256=source['sha256'],source_family=source['policy']['family'],evidence_kind='source_statement',builder_paraphrase='서술법 장의 해요·해예·해여 상대높임 설명. 모든 입력 변환을 보장하는 문장은 아니다.')
 for n in list(nodes.values()):
  if not n['id'].startswith('COND_DECL_'):continue
  p=n['properties'];feature=p['feature'];ev=[]
  if feature=='prefinal_sequence':kind='implementation_scope';decision='DEC_DECL_PREFINAL_SCOPE';note='허용목록은 이번 구현범위. 문헌의배타적금지/허용으로승격하지않음.'
  elif feature=='source_final':
   kind='source_interpretation_with_analyzer_mapping';decision='DEC_DECL_OBSERVED_FINAL';note='해체+요/예구성과관찰용례를실제분석EF에대응.'
   ev=['EV_DECL_STRUCTURE']+({'어요':['EV_DECL_A_YE','EV_DECL_EO_YE'],'네요':['EV_DECL_NE_YE'],'거든요':['EV_DECL_GEODEUN_YE']}[next(x for x in p['allowed'] if x!='아요')])
  else:
   assert feature=='speech_act';kind='source_classification_with_label_interpretation';decision='DEC_DECL_FUNCTION_LABELS';note='문헌서술법을모델평서라벨로해석; 네요는원래발견/감탄기능보존.';ev=['EV_DECL_CLASSIFICATION']+(['EV_DECL_NE_YE'] if 'exclamation' in p['allowed'] else [])
  p.update(basis=kind,basis_explanation=note,decision_id=decision,evidence_ids=ev)
  edge(n['id'],'DEFINED_BY_DECISION',decision)
  for eid in ev:edge(n['id'],'INTERPRETS_SOURCE',eid,evidence_role='label_mapping' if feature=='speech_act' else 'analyzer_form_mapping')
  mapping.append({'condition_id':n['id'],'feature':feature,'allowed':p['allowed'],'kind':kind,'evidence_ids':ev,'decision_id':decision,'reason':note})
 scope=nodes['SCOPE_HAEYE_DECLARATIVE_R1'];scope['properties']['field_basis']={
  'clause_role':{'kind':'implementation_scope','reason':'독립 주절부터 연결하는 구현범위'},
  'speech_act':{'kind':'interpretation','evidence_ids':['EV_DECL_CLASSIFICATION'],'decision_id':'DEC_DECL_FUNCTION_LABELS'},
  'addressee_level':{'kind':'source_interpretation','evidence_ids':['EV_DECL_STRUCTURE','EV_DECL_ADDRESSEE_DECL_SECTION']},
  'predicate_class':{'kind':'implementation_scope','reason':'용언먼저;계사불허주장이아님'},
  'prefinal_sequence':{'kind':'implementation_scope','decision_id':'DEC_DECL_PREFINAL_SCOPE'},
  'subject_honorific':{'kind':'compositional_generalization','evidence_ids':['EV_DECL_HON_SI'],'reason':'의문용례의높임결합을일반구성으로해석;전부직접관찰아님'}}
 for eid in ('EV_DECL_CLASSIFICATION','EV_DECL_STRUCTURE','EV_DECL_ADDRESSEE_DECL_SECTION','EV_DECL_HON_SI'):edge(scope['id'],'INTERPRETS_SOURCE',eid,evidence_role='scope_field_interpretation')
 for n in list(nodes.values()):
  if n['id'].startswith('SEM_DECL_') and n['type']=='SemanticRule':edge(n['id'],'PRESERVATION_SUPPORTED_BY','EV_DECL_ADDRESSEE_DECL_SECTION',evidence_role='preserve_addressee_level')
 edge(scope['id'],'DEFINED_BY_DECISION','DEC_DECL_PREFINAL_SCOPE');edge(scope['id'],'DEFINED_BY_DECISION','DEC_DECL_FUNCTION_LABELS')
 g['version']='semantic_grammar_20261103_r3';g['nodes']=list(nodes.values())
 for n in before['nodes']:
  if n['type']=='Condition':assert all(nodes[n['id']]['properties'][k]==n['properties'][k] for k in ('feature','operator','allowed'))
  elif n['type']=='ProcessingScope':assert nodes[n['id']]['properties']['allowed']==n['properties']['allowed']
  else:assert nodes[n['id']]==n
 assert all(e in g['edges'] for e in before['edges'])
 for e in g['edges']:assert e['source'] in nodes and e['target'] in nodes
 save(OUT/'private/graph.json',g);save(OUT/'private/condition_mapping.json',mapping);save(OUT/'private/change_ledger.json',{'parent_sha256':hashlib.sha256(PARENT.read_bytes()).hexdigest(),'executable_conditions_unchanged':True,'existing_rules_forms_unchanged':True,'new_nodes':len(nodes)-len(before['nodes']),'condition_count':len(mapping),'purpose':'provenance_only; no new dialect rule or accepted grammar range'})
 print('graph',len(nodes),len(g['edges']),'conditions_with_basis',len(mapping))
if __name__=='__main__':main()

