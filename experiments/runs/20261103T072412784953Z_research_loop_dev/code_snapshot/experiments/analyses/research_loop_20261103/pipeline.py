"""Experimental adapter v2. Original graph and frozen runs remain read-only."""
import copy,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'local/python'),str(ROOT/'experiments/analyses/condition_bridge_20261103')]
import bridge
from adapter import compact_packet,check_output
from contracts import GENERATION,GENERATION_PROMPT,obj
from kg_pipeline.validation import validate_schema

PROMPT=bridge.PROMPT+'''
이번에는 지정된 target_word_id 하나만 분석한다. 같은 문장 안 다른 서술어의 특징을 섞지 않는다.
정보를 묻는 질문에는, 잘 모르는 사실을 처음 묻는 질문과 참인지 확인하기 위해 실제 답을 기다리는 질문이 모두 포함된다. 명사+이다 또는 과거형이라는 이유로 '이미 아는 내용을 확인시킴'을 선택하지 않는다. 이미 아는 답에 동의를 요구하는 태도만 명확하면 그 선택지를 사용한다. 구별이 안되면 null.
'그분', '선생님' 같은 명사 존칭을 썼다는 사실과 대상 서술어 자체의 주체높임은 다른 정보다. 대상 서술어의 -시-나 높임 뜻의 용언이 있는지 판단한다. 높임 명사가 있다는 이유만으로 서술어에 높임이 실현되었다고 답하지 않는다.
시간 의미를 판단하되 실제 -었- 형태와 반드시 같을 필요는 없다. 실제 형태는 별도로 보존되므로 시간 해석 때문에 형태를 지우거나 추가하지 않는다.
평서문/명령문은 질문 유형을 null로 두어도 된다. 문장 끝의 물음표만으로 기능을 단정하지 않는다.
'''
PIECE_SCHEMA=obj({'replacement':{'type':'string'},'status':{'type':'string','enum':['generated','needs_review']},'reason':{'type':'string'}})
PIECE_PROMPT='''주어진 문장의 한 어절을 경상도 질문 종결형으로 조합한다. JSON replacement에는 바꿀 어절만 적는다. 다른 어휘를 바꾸거나 조사와 문장을 추가하지 않는다.
source_morphs의 어휘와 prefinals를 그대로 보존하고 source_final만 제공된 결합형으로 바꾼다. 시간 해석이 현재여도 실제 선어말 -었-이 있으면 삭제하지 않는다. 새 선어말을 넣지 않는다.
현재 계사 결합형이 includes_copula=true이면 nominal 뒤에 그 결합형을 붙인다. 이-를 다시 넣지 않는다. 과거 계사는 stem과 실제 선어말을 보존한다. 겹치는 부분이나 무관한 음절을 반복하지 않는다.
표준어의 일반적인 활용을 조합하되 새로운 방언 어간 축약은 만들지 않는다. supplied forms 외의 어미를 선택하지 않는다. 못 만들면 needs_review. 완성 문장 정답은 제공되지 않았다. JSON만 출력한다.'''

def sentence_targets(morph):
 """Use observed Kiwi sentence boundaries; no punctuation-derived function labels."""
 out=[]
 for word in morph['words']:
  if not any(t.split('-')[0]=='EF' for f,t in word['morphs']):continue
  sid=word['sentence'];tokens=[t for t in morph['tokens'] if t['sentence']==sid]
  start=min(t['start'] for t in tokens);end=max(t['end'] for t in tokens)
  local=copy.deepcopy(morph);local['text']=morph['text'][start:end]
  local['words']=[w for w in local['words'] if w['sentence']==sid];local['tokens']=copy.deepcopy(tokens)
  for w in local['words']:
   w['start']-=start;w['end']-=start
   for t in w['tokens']:t['start']-=start;t['end']-=start
  for t in local['tokens']:t['start']-=start;t['end']-=start
  out.append({'uid':word['uid'],'offset':start,'sentence_end':end,'original_span':[word['start'],word['end']],'morph':local})
 return out

def schema_and_payload(graph,morph,uid,context):
 schema,questions=bridge.contract(graph);schema=copy.deepcopy(schema)
 schema['properties']['target_word_id']={'type':'string','enum':[uid]}
 return schema,{'text':morph['text'],'context':context,'target_word_id':uid,'words':bridge.compact_morph(morph),'questions':questions}

def analyze_response(graph,raw,morph,uid):
 if raw['target_word_id']!=uid:raise ValueError('target_changed')
 analysis=bridge.assemble(graph,raw,morph)
 # The bridge's old explanatory labels stay stable; this is a prompt refinement,
 # not an unseen output correction or a change to the graph's policy.
 analysis['origin']='target_scoped_kiwi_and_qwen_defined_questions_v2'
 return analysis,bridge.trace(graph,analysis,morph)

def generation_payload(analysis,trace,morph):
 compact=compact_packet(analysis,trace['packet'],morph)
 if len(compact['actions'])!=1:raise ValueError('not_one_ready_action')
 action=compact['actions'][0]
 p=next(c for c in trace['packet']['clauses'] if c['readiness']=='ready_for_generation_trial')
 enhanced=copy.deepcopy(compact)
 enhanced['actions'][0].update(prefinals=p['morphology']['prefinals'],source_final=p['morphology']['source_final'])
 return compact,enhanced

def apply_piece(text,action,piece):
 if not isinstance(piece,str) or not piece.strip() or any(c.isspace() for c in piece):raise ValueError('replacement_not_single_word')
 if any(c in piece for c in '.!?\n\r'):raise ValueError('replacement_contains_sentence_punctuation')
 i,j=action['span']
 if text[i:j]!=action['target']:raise ValueError('stale_target')
 return text[:i]+piece+text[j:]

def preservation_check(morphology,output,payload):
 result=check_output(payload['text'],output,payload);a=payload['actions'][0];i,j=a['span']
 prefix=payload['text'][:i];suffix=payload['text'][j:]
 if 'outside_target_changed' in result['warnings']:return result
 piece=output[len(prefix):len(output)-len(suffix) if suffix else len(output)]
 observed=morphology.analyze(piece)
 src=[f for f,t in a['source_morphs'] if t.split('-')[0]=='EP']
 dst=[t['form'] for t in observed['tokens'] if t['base_tag']=='EP']
 normalize=lambda xs:['었' if x in ('았','었','였') else x for x in xs]
 if normalize(src)!=normalize(dst):result['warnings'].append('prefinal_observation_changed_or_kiwi_uncertain')
 if a.get('nominal') and any(f['includes_copula'] for f in a['forms']):
  allowed=[a['nominal']+f['selected_combining_form'] for f in a['forms'] if f['includes_copula'] and f['selected_combining_form']]
  if piece not in allowed:result['warnings'].append('integrated_copula_composition_mismatch')
 result.update(piece=piece,source_prefinals=src,output_kiwi_prefinals=dst,
  scope='Surface preservation checks; Kiwi dialect parsing may be wrong. No naturalness score.')
 return result
