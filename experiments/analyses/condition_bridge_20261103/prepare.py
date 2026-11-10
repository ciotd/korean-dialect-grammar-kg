"""Freeze development inputs and builder analysis references before API calls."""
import copy
import datetime
import json
from bridge import HERE,ROOT,GRAPH,inventory,contract
from kg_pipeline.io import read,save,sha
from kg_runtime.morphology import Morphology
from research_management.work import WorkStore

SOURCE=ROOT/'experiments/analyses/question_refinement_20261102/private/development.json'

def cases():
 out=[]
 for old in read(SOURCE):
  c=old['analysis']['clauses'][0];f=copy.deepcopy(c['features'])
  if old['id']=='Q15':f['polarity']='negative'
  allowed={k:[v] for k,v in f.items()}
  if old['id']=='Q13':allowed['question_kind']=[None,'wh','polar']
  if old['id']=='Q15':
   allowed['speech_act']=['request','information_question',None]
   allowed['question_kind']=['polar',None]
  out.append({'id':old['id'],'text':old['analysis']['text'],'group':'previous_development',
   'target':c['target_text'],'accepted_features':allowed,
   'diagnostic_only':old['id'] in ('Q13','Q15','Q16'),
   'reference_basis':'builder previous analysis; Q13/Q15 retain competing readings; Q16 duplicate technical case'})
 specifications=[
 ('너 지금 기다려?','기다려',{}),
 ('왜 기다려?','기다려',{'question_kind':'wh'}),
 ('어제 영화 봤어?','봤어',{'prefinal_type':'eoss','tense':'past'}),
 ('어제 어디 걸었어?','걸었어',{'question_kind':'wh','prefinal_type':'eoss','tense':'past'}),
 ('오늘 바람이 차가워?','차가워',{'predicate_class':'adjective'}),
 ('어제 방이 추웠어?','추웠어',{'predicate_class':'adjective','prefinal_type':'eoss','tense':'past'}),
 ('그분이 가수야?','가수야',{'predicate_class':'copula'}),
 ('누가 반장이야?','반장이야',{'predicate_class':'copula','question_kind':'wh'}),
 ('그 사람이 배우였어?','배우였어',{'predicate_class':'copula','prefinal_type':'eoss','tense':'past'}),
 ('누가 회장이었어?','회장이었어',{'predicate_class':'copula','question_kind':'wh','prefinal_type':'eoss','tense':'past'}),
 ('아직 숙제 안 했어?','했어',{'prefinal_type':'eoss','tense':'past','polarity':'negative'}),
 ('누가 먼저 도착했어?','도착했어',{'question_kind':'wh','prefinal_type':'eoss','tense':'past'}),
 ('지금 기다려요?','기다려요',{'addressee_level':'polite'}),
 ('할머니께서 주무셨어?','주무셨어',{'prefinal_type':'eoss','tense':'past','subject_honorific':'present'}),
 ('그 사람이 학생이 아니야?','아니야',{'predicate_class':'negative_copula','polarity':'negative'}),
 ('조용히 문 좀 닫아.','닫아',{'speech_act':'request','question_kind':None}),
 ]
 for i,(text,target,changes) in enumerate(specifications,1):
  f={'clause_role':'main','speech_act':'information_question','addressee_level':'plain','question_kind':'polar',
     'predicate_class':'verb','prefinal_type':'none','tense':'present','subject_honorific':'absent','polarity':'positive'}
  f.update(changes)
  out.append({'id':f'N{i:02d}','text':text,'target':target,'group':'new_boundary' if i>=13 else 'new_core',
   'accepted_features':{k:[v] for k,v in f.items()},'diagnostic_only':False,
   'reference_basis':'builder linguistic interpretation fixed before model calls; not independently human validated'})
 return out

def main():
 if (HERE/'private/preparation.json').exists():raise SystemExit('Already frozen; do not overwrite')
 rows=cases();graph=read(GRAPH);audit=inventory(graph);schema,questions=contract(graph)
 save(HERE/'private/cases.json',rows);save(HERE/'private/condition_inventory.json',audit)
 save(HERE/'private/analysis.schema.json',schema);save(HERE/'private/model_questions.json',questions)
 morphology=Morphology();morphs={r['id']:morphology.analyze(r['text']) for r in rows}
 save(HERE/'private/kiwi_inputs.json',morphs)
 files=[GRAPH,SOURCE,HERE/'private/cases.json',HERE/'private/kiwi_inputs.json']
 save(HERE/'private/preparation.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'files':{str(p):sha(p.read_bytes()) for p in files},'records':len(rows),'distinct_texts':len({r['text'] for r in rows}),
  'generation_calls_planned':0,'arms':['baseline','bridge'],'planned_analysis_calls':len(rows)*2,
  'gold_policy':'builder references only; no dialect answers or reference features in model input',
  'new_input_policy':'new to this experiment; not a statistically independent final evaluation set'})
 WorkStore(ROOT).task({'id':'condition_bridge_20261103','title':'KG 조건과 분석 연결 검증','actor':'Codex 연구 리드',
  'stage':'조건 확인 및 입력 동결','status':'running','done':1,'total':4,'unit':'단계','message':'7조건 확인, 기존16+새16 입력 확정. 모델 호출 전.'})
 print(json.dumps({'cases':len(rows),'distinct':len({r['text'] for r in rows}),'conditions':len(audit['conditions']),
  'features':[(r['feature'],r['provider'],r['role']) for r in audit['rows']]},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
