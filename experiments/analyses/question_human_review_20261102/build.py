"""Prepare all 16 existing cases for native-speaker review, without model calls."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
INPUT=ROOT/'experiments/analyses/question_refinement_20261102/private'
VERSION='question_human_review_20261102_v1'
def read(p):return json.loads(p.read_text('utf8'))
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
# These complete forms are authored hypotheses, not attested sentences or outputs.
MANUAL={
 'Q01':('지금 웃고 있는지 사실을 묻습니다. 비꼬거나 나무라는 상황은 아닙니다.','응, 웃고 있어 / 아니, 안 웃어.','너 지금 웃나?','웃어 → 웃나','이 뜻으로 편하게 묻는 말로 들리나요?'),
 'Q02':('상대가 웃는 이유를 알고 싶습니다.','재미있는 이야기를 들었어.','왜 웃노?','웃어 → 웃노','이유를 묻는 뜻과 반말이 유지되나요?'),
 'Q03':('국이 짠지 아닌지 상대에게 묻습니다.','응, 짜 / 아니, 안 짜.','오늘 국이 짜나?','짜 → 짜나','상대에게 묻는 말인가요, 혼잣말처럼 들리나요?'),
 'Q04':('어제 먹은 음식의 종류를 묻는 상황으로 잡았습니다.','어제 국수 먹었어.','어제 뭐 먹었노?','먹었어 → 먹었노','먹었노가 자연스러운지 봐 주세요. 다른 어휘형을 선호하면 대안에 적어 주세요.'),
 'Q05':('그 사람이 학생인지 아닌지 묻습니다.','응, 학생이야 / 아니야.','그 사람이 학생이가?','학생이야 → 학생이가','학생이가로 묻는 것이 자연스러운가요?'),
 'Q06':('그 사람이 의사인지 아닌지 묻습니다.','응, 의사야 / 아니야.','그 사람이 의사가?','의사야 → 의사가','질문 끝의 의사가가 자연스러운가요? 뒤에 말이 더 있어야 할 것처럼 들리나요?'),
 'Q07':('여러 사람 중 학생이 누구인지 묻습니다.','저 사람이 학생이야.','누가 학생이고?','학생이야 → 학생이고','대상을 묻는 말로 자연스럽나요?'),
 'Q08':('여러 사람 중 의사가 누구인지 묻습니다.','저 사람이 의사야.','누가 의사고?','의사야 → 의사고','누가와 의사고의 조합이 자연스러운가요?'),
 'Q09':('그 사람이 과거에 학생이었는지 묻습니다.','응, 그때는 학생이었어.','그 사람이 학생이었나?','학생이었어 → 학생이었나','과거를 묻는 뜻과 표현이 자연스러운가요?'),
 'Q10':('그 당시 의사였던 사람이 누구인지 묻습니다.','그때는 저 사람이 의사였어.','누가 의사였노?','의사였어 → 의사였노','의사였노라는 완성형을 특히 확인해 주세요. 문헌의 일반 조건으로 구성한 후보입니다.'),
 'Q11':('상대가 조금 전에 갔던 장소를 묻습니다.','아까 가게에 갔어.','아까 어디 갔노?','갔어 → 갔노','과거의 장소를 묻는 뜻이 유지되나요?'),
 'Q12':('짐이 무거운지 아닌지 묻습니다.','응, 무거워 / 아니, 가벼워.','짐이 무겁나?','무거워 → 무겁나','무겁나가 자연스러운가요? 더 자연스러운 표현이 있다면 적어 주세요.'),
 'Q14':('아직 밥을 먹지 않은 상태인지 묻습니다. 식사를 재촉하는 상황은 아닙니다.','아직 안 먹었어 / 벌써 먹었어.','아직 밥 안 먹었나?','먹었어 → 먹었나','안 먹었나가 미식사 여부를 묻는 뜻으로 자연스러운가요?'),
 'Q15':('상대에게 빨리 오라고 재촉합니다. 올지 말지 정보를 묻는 상황은 아닙니다.','상대가 빨리 오거나, 곧 간다고 답합니다.','빨리 안 오나?','와 → 오나','질문 모양이어도 재촉으로 들리는지 확인해 주세요. 현재 KG의 지원 범위 밖 참고 후보입니다.')}

def build():
 source=read(INPUT/'development.json');spec=read(INPUT/'spec.json');rules={r['id']:r for r in spec['rules']}
 rows=[]
 for src in source:
  key=src['id'];c=src['analysis']['clauses'][0];packet=src['packet']['clauses'][0]
  row={'id':key,'input':src['analysis']['text'],'original_status':packet['readiness'],'original_features':c['features'],
   'candidate_author':'lead_assistant_manual_composition','qwen_output':False,'human_status':'unreviewed','candidates':[]}
  if key=='Q16':
   row.update(duplicate_of='Q05',notice='Q05와 같은 원문입니다. 명사의 받침 분석값이 빠진 경우를 시험하는 사례라 별도 언어 평가를 받지 않습니다. Q05 의견을 참조하되 이 기술 검사를 통과한 것으로 간주하지 않습니다.')
  elif key=='Q13':
   row['notice']='문맥 없는 원문은 뜻을 하나로 확정하지 않습니다. 아래 두 상황을 따로 검토해 주세요. 시스템이 두 후보를 실제 선택했다는 뜻은 아닙니다.'
   for suffix,kind,meaning,answer,text,rid in [
    ('A','polar','무언가를 먹기는 했는지 묻습니다. 음식 종류는 중요하지 않습니다.','뭐 좀 먹었어 / 아무것도 안 먹었어.','뭐 먹었나?','SEM_Q_V_POLAR'),
    ('B','wh','먹은 음식이 무엇인지 묻습니다.','빵 먹었어.','뭐 먹었노?','SEM_Q_V_WH')]:
    row['candidates'].append({'id':key+suffix,'meaning':meaning,'expected_answer':answer,'text':text,'change':'먹었어 → '+('먹었나' if kind=='polar' else '먹었노'),
     'question':'이 상황에서 이 표현이 자연스럽고 뜻도 맞나요?','basis':'conditional_manual_hypothesis_not_actual_selected_rule','rule_id':rid,'assumed_question_kind':kind})
  else:
   meaning,answer,text,change,question=MANUAL[key]
   rid=packet['choices'][0]['rule_id'] if packet['choices'] else None
   row['candidates']=[{'id':key,'meaning':meaning,'expected_answer':answer,'text':text,'change':change,'question':question,'rule_id':rid,
    'basis':'manual_composition_from_retrieved_rule' if rid else 'manual_reference_outside_current_scope',
    'evidence_ids':rules[rid]['primary_evidence_ids'] if rid else ['EV_Q_FUNCTION_BOUNDARY']}]
   row['notice']=('일반 규칙을 적용해 만든 완성형입니다. 이 문장 자체가 문헌에서 확인됐거나 자연스럽다고 검증된 것은 아닙니다.' if key in ('Q09','Q10') else '')
  for cand in row['candidates']:
   cand.setdefault('evidence_ids',rules[cand['rule_id']]['primary_evidence_ids'] if cand['rule_id'] else [])
   cand['source_locations']=[{'id':eid,'doc':spec['evidence'][eid]['document_id'],'page':spec['evidence'][eid]['pdf_page']} for eid in cand['evidence_ids']]
   # All candidates edit only the original whole-predicate target. No answers are
   # silently obtained from a model or dictionary substitution.
   left,right=c['target_span'];before,after=row['input'][:left],row['input'][right:]
   assert cand['text'].startswith(before) and (not after or cand['text'].endswith(after))
   cand['target_span']=c['target_span'];cand['original_target']=c['target_text']
  rows.append(row)
 payload={'version':VERSION,'purpose':'development_native_review_before_model_trial_not_blind_evaluation',
  'source_hashes':{str(INPUT/p):sha(INPUT/p) for p in ('development.json','spec.json','graph.json')},
  'question_context':'반말을 쓰는 가까운 사이. Q15를 제외하면 정보를 묻는 상황으로 검토. 억양은 따로 제시하지 않음.',
  'policy':'후보는 확정 정답이 아님. 완성 문장을 KG 룰이나 프롬프트 예시로 자동 입력하지 않음. 사용자 의견은 조건·형태·대안 검토에 사용하며 별도 변경 기록 후 반영.',
  'known_issue':{'id':'Q15_POLARITY','case':'Q15','location':'original_features.polarity','observed':'positive','input_has':'안 와',
   'assessment':'기존 수작업 분석의 부정 표지가 입력과 불일치. 후보는 안을 보존. 이번에는 기존 기록을 수정하지 않음.',
   'next_action':'후속 분석 기준 수정 시 부정=negative로 교정하고 재검증. 사용자에게 긍정/부정 판정을 떠넘기지 않음.'},'rows':rows}
 raw=json.dumps(payload,ensure_ascii=False,sort_keys=True).encode();payload['review_set_hash']=hashlib.sha256(raw).hexdigest()
 dump(HERE/'private/review_set.json',payload)
 table=['# 질문 16건 검토표','', '후보는 총괄이 작성한 미확정 표현이며 Qwen 출력이 아닙니다. Q13은 두 상황, Q16은 Q05 중복 기술 사례입니다.','',
  '| ID | 표준어 | 이번에 가정한 뜻 | 검토용 후보 | 확인할 점 |','|---|---|---|---|---|']
 for row in rows:
  if not row['candidates']:table.append(f"| {row['id']} | {row['input']} | Q05와 동일 | Q05 참조 | 분석 누락 검사; 중복 평가 없음 |");continue
  for c in row['candidates']:table.append('| '+' | '.join((c['id'],row['input'],c['meaning'],c['text'],c['question']))+' |')
 (HERE/'private/review_table.md').write_text('\n'.join(table)+'\n',encoding='utf8')
 html=(HERE/'template.html').read_text('utf8').replace('@@DATA@@',json.dumps(payload,ensure_ascii=False).replace('<','\\u003c'))
 (HERE/'private/review.html').write_text(html,encoding='utf8')
 print(json.dumps({'cases':len(rows),'distinct_inputs':len({r['input'] for r in rows}),'judgment_units':sum(len(r['candidates']) for r in rows),'review_set_hash':payload['review_set_hash']},ensure_ascii=False))
 return payload
if __name__=='__main__':build()
