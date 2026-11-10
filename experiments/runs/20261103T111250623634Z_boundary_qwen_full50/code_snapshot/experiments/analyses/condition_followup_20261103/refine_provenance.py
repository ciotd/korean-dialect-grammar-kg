"""Reviewer corrections after the frozen r3 model run; no grammar expansion."""
import json,copy,hashlib,importlib.util
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[2]
P=R/'knowledge/authored/semantic_grammar_20261103_r3/private/graph.json';O=R/'knowledge/authored/semantic_grammar_20261103_r4/private'
def read(p):return json.loads(p.read_text('utf8'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n','utf8')
def main():
 g=read(P);before=copy.deepcopy(g);ns={n['id']:n for n in g['nodes']};cache=read(Path('C:/Users/ciot28/Documents/Codex/2026-10-13/ciotd-odor-complaint-dialect-rag-kg/work/source_audit/D02.json'))
 def evidence(id,page,quote,meaning):
  text=cache[page-1]['text'];start=text.index(quote);p=copy.deepcopy(ns['EV_DECL_CLASSIFICATION']['properties'])
  p.update(pdf_page=page,quote=quote,start=start,end=start+len(quote),page_text_sha256=hashlib.sha256(text.encode()).hexdigest(),evidence_kind='source_statement_or_attested_context',builder_paraphrase=meaning)
  ns[id]={'id':id,'type':'Evidence','properties':p}
 def edge(a,rel,b,role):
  g['edges'].append({'id':'E_R4_'+hashlib.sha256(json.dumps([a,rel,b,role]).encode()).hexdigest()[:18],'source':a,'relation':rel,'target':b,'evidence_role':role})
 evidence('EV_DECL_EXCLAMATION_CONTEXT',202,'아!정말 거 잔치 잘했네예.','감탄사와 함께 쓰인 한 용례. 모든 네예가 감탄이라는 뜻은 아님.')
 evidence('EV_DECL_LEVEL_VARIATION',58,'해예체 종결어미는 해요체와 마찬가지로 하게체를 제외한 모든 등급\n에서 유동적으로 쓰이고 있다.','비격식 높임형이라는 범주만 대응. 상황별 높임 정도가 같다는 보장은 아님.')
 evidence('EV_DECL_INPUT_FORMS',203,'해요체 -요,-네요,-데요,-라요,-래요,-세요,-제요 –지요,\n-지러요,-거든요,-께요,-(ㄹ)끼요,-니더요,-ㅂ니더요','표47의 입력 쪽 종결형 목록. 실제 변환 조건은 별도 해석.')
 evidence('EV_DECL_INPUT_EO',203,'-아/어요 1,137 838 260 291 170 876 1,205 561 433 1,147 678 7,596','같은 페이지 해요체 아/어요 관찰. 숫자는 문헌집계이며 독립 증거 수 아님.')
 evidence('EV_DECL_CLASSIFICATION_WIDTH',75,'국어대사전 에서는 서술법을 “어미 변화의 하나,평서법,감탄법,약속법 따위이다.”라고\n명시하면서 서술법 내에 다양한 문장 종결법이 포함된 것으로 기술하고 있다.','이 문헌의 서술법은 현재 statement 라벨보다 넓다. 실험에서 약속 등을 아직 제외한 결정과 구별.')
 changes=[]
 for n in list(ns.values()):
  id=n['id'];p=n['properties']
  if id.startswith('COND_DECL_'):
   if p['feature']=='speech_act':
    p['evidence_ids'].append('EV_DECL_CLASSIFICATION_WIDTH');edge(id,'INTERPRETS_SOURCE','EV_DECL_CLASSIFICATION_WIDTH','broader_source_classification')
    if 'exclamation' in p['allowed']:
     p['evidence_ids']=['EV_DECL_EXCLAMATION_CONTEXT' if x=='EV_DECL_NE_YE' else x for x in p['evidence_ids']]
     for e in g['edges']:
      if e['source']==id and e['relation']=='INTERPRETS_SOURCE' and e['target']=='EV_DECL_NE_YE':
       changes.append({'replaced_edge':copy.deepcopy(e),'reason':'감탄사의 문맥까지 포함한 별도 인용으로 연결'});e['target']='EV_DECL_EXCLAMATION_CONTEXT';e['id']='E_R4_'+hashlib.sha256(json.dumps([id,e['relation'],e['target']]).encode()).hexdigest()[:18]
   elif p['feature']=='source_final':
    eid='EV_DECL_INPUT_EO' if '어요' in p['allowed'] else 'EV_DECL_INPUT_FORMS';p['evidence_ids'].append(eid);edge(id,'INTERPRETS_SOURCE',eid,'source_input_form')
    for e in g['edges']:
     if e['source']==id and e['relation']=='INTERPRETS_SOURCE' and e['target']!=eid:
      e['evidence_role']='correspondence_structure' if e['target']=='EV_DECL_STRUCTURE' else 'target_form_attestation_secondary_wiki' if e['target']=='EV_DECL_EO_YE' else 'target_form_attestation'
  if id.startswith('SEM_DECL_') and n['type']=='SemanticRule':
   edge(id,'PRESERVATION_LIMITED_BY','EV_DECL_LEVEL_VARIATION','informal_honorific_category_not_equal_contextual_degree')
   edge(id,'EVIDENCE_ROLE','EV_DECL_HON_SI','same_morpheme_sequence_other_speech_act')
   edge(id,'EVIDENCE_ROLE','EV_DECL_ADDRESSEE','other_section_parallel_statement')
 g['nodes']=list(ns.values());g['version']='semantic_grammar_20261103_r4'
 for n in before['nodes']:
  if n['type']=='Condition':
   for k in ('feature','operator','allowed'):assert ns[n['id']]['properties'][k]==n['properties'][k]
  else:assert ns[n['id']]==n
 assert len({e['id'] for e in g['edges']})==len(g['edges'])
 for e in g['edges']:assert e['source'] in ns and e['target'] in ns
 save(O/'graph.json',g);save(O/'change_ledger.json',{'parent_sha256':hashlib.sha256(P.read_bytes()).hexdigest(),'changes':changes,'executable_grammar_unchanged':True,'purpose':'reviewed provenance corrections only; r3 model-run snapshot preserved'})
 # Replay every model answer against both graph versions; no new Qwen calls.
 run=R/'experiments/runs/20261103T093451123726Z_research_loop_followup50';rows=[]
 # Reuse exactly the runtime that produced the compared run, not later guard fixes.
 s=importlib.util.spec_from_file_location('provenance_replay_runtime',H/'runtime.py');rt=importlib.util.module_from_spec(s)
 frozen=run/'code_snapshot/experiments/analyses/condition_followup_20261103/runtime.py'
 exec(compile(frozen.read_text('utf8'),str(frozen),'exec'),rt.__dict__)
 for td in sorted((run/'private/records').glob('*/targets/*')):
  raw=read(td/'analysis_call/parsed.json');target=read(td/'target.json');old=read(td/'trace.json')
  a,t=rt.analyze_response(g,raw,target['morph'],target['uid'])
  def signature(tr):return [(x['retrieval']['construction_id'],x['retrieval']['clauses'][0]['state'],x['packet']['clauses'][0]['readiness'],x['packet']['clauses'][0]['choices']) for x in tr['construction_queries']]
  assert signature(old)==signature(t)
  rows.append({'id':td.parents[1].name,'target_id':td.name,'query_choices_and_readiness_identical':True})
 save(O/'fixed_analysis_replay.json',{'qwen_calls':0,'positions':len(rows),'same_choices_and_readiness':True,'rows':rows,'limitation':'Provenance-only replay, not a new generation or naturalness experiment.'})
 print(json.dumps({'graph_nodes':len(ns),'graph_edges':len(g['edges']),'replayed_positions':len(rows),'qwen_calls':0}))
if __name__=='__main__':main()
