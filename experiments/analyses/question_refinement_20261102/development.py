"""Manual examples for interface tests, not translation gold or model outputs."""
import copy
from sources import HERE,ROOT,read,dump
from query import Reader

def example(key,text,target,kind='polar',pc='verb',pf='none',lemma='웃다',stem='웃',final='어',nominal=None,wh=None):
 t=text.index(target);features={'clause_role':'main','speech_act':'information_question','addressee_level':'plain','question_kind':kind,
  'predicate_class':pc,'prefinal_type':pf,'tense':'past' if pf=='eoss' else 'present','subject_honorific':'absent','polarity':'positive'}
 morphology={'predicate_id':'p1','lemma':lemma,'stem':stem,'prefinals':['었'] if pf=='eoss' else [],'source_final':final,
  'alignment':'whole_predicate_recomposition','origin':'builder_manual_annotation_not_model_output'}
 if nominal:morphology.update(nominal=nominal,nominal_end='consonant_final_nominal' if (ord(nominal[-1])-0xac00)%28 else 'vowel_final_nominal')
 c={'id':'c1','span':[0,len(text)],'target_span':[t,t+len(target)],'target_text':target,'features':features,
  'feature_bindings':{k:{'clause_id':'c1','predicate_id':'p1' if k in ('predicate_class','prefinal_type','tense','subject_honorific','polarity') else None,'origin':'builder_manual_annotation'} for k in features},
  'predicate':{'id':'p1','clause_id':'c1','span':[t,t+len(target)],'surface':target,'origin':'builder_manual_annotation'},
  'ending_slot':{'id':'end1','predicate_id':'p1','clause_id':'c1','boundary_status':'whole_predicate_recomposition'},'morphology':morphology,'question_variable':None}
 if wh:
  p=text.index(wh);c['question_variable']={'id':'q1','span':[p,p+len(wh)],'surface':wh,'role':'asked_information','clause_id':'c1','scope_clause_id':'c1'}
 return {'id':key,'purpose':'manual_development_contract_case_not_translation_gold','analysis':{'text':text,'origin':'builder_manual_annotation','clauses':[c]}}

def cases():
 rows=[
 example('Q01','너 지금 웃어?','웃어'),
 example('Q02','왜 웃어?','웃어',kind='wh',wh='왜'),
 example('Q03','오늘 국이 짜?','짜',pc='adjective',lemma='짜다',stem='짜',final='아'),
 example('Q04','어제 뭐 먹었어?','먹었어',kind='wh',pf='eoss',lemma='먹다',stem='먹',wh='뭐'),
 example('Q05','그 사람이 학생이야?','학생이야',pc='copula',lemma='이다',stem='이',final='야',nominal='학생'),
 example('Q06','그 사람이 의사야?','의사야',pc='copula',lemma='이다',stem='이',final='야',nominal='의사'),
 example('Q07','누가 학생이야?','학생이야',kind='wh',pc='copula',lemma='이다',stem='이',final='야',nominal='학생',wh='누가'),
 example('Q08','누가 의사야?','의사야',kind='wh',pc='copula',lemma='이다',stem='이',final='야',nominal='의사',wh='누가'),
 example('Q09','그 사람이 학생이었어?','학생이었어',pc='copula',pf='eoss',lemma='이다',stem='이',nominal='학생'),
 example('Q10','누가 의사였어?','의사였어',kind='wh',pc='copula',pf='eoss',lemma='이다',stem='이',nominal='의사',wh='누가'),
 example('Q11','아까 어디 갔어?','갔어',kind='wh',pf='eoss',lemma='가다',stem='가',wh='어디'),
 example('Q12','짐이 무거워?','무거워',pc='adjective',lemma='무겁다',stem='무겁',final='어')]
 rows[10]['analysis']['clauses'][0]['morphology']['prefinals']=['았']
 # Same text, explicitly different manually assigned interpretations.
 amb=example('Q13','뭐 먹었어?','먹었어',pf='eoss',lemma='먹다',stem='먹')
 amb['analysis']['clauses'][0]['features']['question_kind']=None;rows.append(amb)
 neg=example('Q14','아직 밥 안 먹었어?','먹었어',pf='eoss',lemma='먹다',stem='먹');neg['analysis']['clauses'][0]['features']['polarity']='negative';rows.append(neg)
 request=example('Q15','빨리 안 와?','와',lemma='오다',stem='오',final='아');request['analysis']['clauses'][0]['features']['speech_act']='request';rows.append(request)
 incomplete=copy.deepcopy(rows[4]);incomplete['id']='Q16';incomplete['analysis']['clauses'][0]['morphology']['nominal_end']=None;rows.append(incomplete)
 for row in rows:
  for c in row['analysis']['clauses']:
   m=c['morphology'];m['source_alignment']={'target_span':c['target_span'][:],'surface':c['target_text'],'checked_by':'builder_manual_review','status':'manually_aligned',
    **{k:copy.deepcopy(m.get(k)) for k in ('lemma','stem','prefinals','source_final','nominal')}}
 return rows

def export(reader):
 rows=cases()
 for row in rows:
  row['retrieval']=reader.query(row['analysis']);row['packet']=reader.packet(row['analysis'],row['retrieval'])
 dump(HERE/'private/development.json',rows)
 old=read(ROOT/'experiments/analyses/semantic_kg_rebuild_20261102/private/easy_development.json');checks=[]
 for row in old:
  got=reader.query(row['analysis']);e=sorted({i['rule_id'] for c in got['clauses'] for i in c['eligible']});u=sorted({i['rule_id'] for c in got['clauses'] for i in c['unresolved']})
  checks.append({'id':row['id'],'expected_eligible':sorted(row['expected_eligible']),'actual_eligible':e,
   'expected_unresolved':sorted(row['expected_unresolved']),'actual_unresolved':u,
   'pass':e==sorted(row['expected_eligible']) and u==sorted(row['expected_unresolved'])})
 dump(HERE/'private/previous_case_comparison.json',checks)
 return rows,checks

if __name__=='__main__':export(Reader(read(HERE/'private/graph.json')))
