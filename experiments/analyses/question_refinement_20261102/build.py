"""Refine the existing six usages; preserve original versions and identity links."""
import copy,importlib.util,json
from sources import HERE,ROOT,BASE,read,dump,evidence
s=importlib.util.spec_from_file_location('previous_graph',ROOT/'experiments/analyses/semantic_kg_rebuild_20261102/semantic_graph.py');previous=importlib.util.module_from_spec(s);s.loader.exec_module(previous)
VERSION='semantic_questions_20261102_r3'
def build():
 spec=copy.deepcopy(read(ROOT/'knowledge/authored/semantic_foundation_20261102_r2/private/foundation.json'))
 spec['version']=VERSION;spec['knowledge_status']='source_context_reread_bounded_candidate_not_generation_validated'
 spec['feature_schema']['polarity']=['positive','negative']
 spec['feature_schema']['speech_act']+=['suggestion','exclamation','self_question']
 for e in spec['evidence'].values():
  if e['document_id']=='D02':e['source_scope']='1980년대 경북 대계 자료; 주7의 1차사업1979–1985. 개별 채록일과 구별.'
 additions={
 'EV_Q_V_EXAMPLES':evidence('D02',145,'아,그래.꼭 니가 그 말이 옳나?', '형용사 옳다에 -나가 결합한 본문 용례. 용언 분기의 직접 용례.'),
 'EV_Q_V_PAST':evidence('D02',145,'그,그 내 코를 말이여 낫게 한다디 어째 이래 됐노?', '본문에 -었- 계열과 -노가 함께 나타나는 용례.'),
 'EV_Q_TARGET_STYLE':evidence('D04',9,'이 어미들은 오직 해라체에서만 사용된다. 즉, 아래의 모든 동남 방언 예문들은 해라체(반말)다.', '이 절에서 다루는 네 어미는 해라체 문맥이다. 표준어 반말 입력을 이 체계로 옮기는 것은 연구의 대상 선택.', 'wiki_usage_explanation'),
 'EV_COP_PREFINAL_RULE':evidence('D04',11,"'~(이)가', '~(이)고'의 어간과 어말 어미 사이에 '-었-', '-겠-\n', '-더-' 등 선어말 어미가 붙으면 어말 어미가 ㄴ 계열 어미로 바뀐다.", '계사 계열 뒤 시상 선어말이 있을 때 ㄴ계열이 된다는 조건 진술. 실제 원문에서 과거 계사+노 예문을 확인한 것은 아님.', 'wiki_condition_statement'),
 'EV_Q_FUNCTION_BOUNDARY':evidence('D04',12,'판정 명령의문문: 퍼뜩 안오나? [빨리 안 와?]', '같은 -나라도 명령 기능일 수 있다. 이번 직접 정보 질문과 구별.', 'wiki_example'),
 'EV_Q_SI_EXCEPTION':evidence('D04',11,"단, 주체 높임법에 쓰이는 '-시-'는 그대로 '-가', '-고'가\n이어진다.", '같은 자료8쪽 표와 -시- 취급이 달라 이번 범위에서 확정하지 않음.', 'wiki_condition_statement'),
 'EV_Q_REGIONAL_VARIANT':evidence('D05',24,"'-나'는 경북 서부와 경남 서부에서 쓰이는 의문형 어미로 -나/노/가/고 대신 쓰인다.", '서부 변이 기술을 기본 체계의 모든 문장에 합치지 않는다. 해당 지역만 가능하다는 배타성은 검증하지 않았다.', 'wiki_regional_observation'),
 'EV_Q_RA_NONONE':evidence('D02',147,"(99ㄷ,ㄹ)은 의문사(무\n슨,어쩐)와 공기하면서 ‘-라’가 동일한 기능으로 쓰이지 않고 있다.", '라/로를 가/고와 언제나 일대일로 대응할 수 없다는 본문 논의.'),
 'EV_Q_EXISTENCE':evidence('D02',137,"계사나 ‘있다’,‘없다’등에서 결합하는 특성을 보여준다.", '있다·없다 뒤 -가 설명과 다른 쪽의 -나 용례를 함께 보존. 특정 형태의 유일성을 주장하지 않음.'),
 'EV_Q_EXISTENCE_NA':evidence('D02',145,'너 아부지 있나?', '있다+-나의 직접 용례. 별도 -가 설명이 있다고 이 용례 자체를 취소하지 않음.'),
 'EV_Q_SELF_QUESTION':evidence('D04',13,"이는 세 가지 의미로 쓰이는데, 해체에서 쓰이면 자기 자신\n에게 되묻는 의문어미이고, 문장 중간에서는 연결 어미 기능을 하며, 하게체에서 쓰이면 의문 어미 역할을 한다.", '유사한 ㄴ가/ㄴ고 형태의 기능과 높임 체계를 구별해야 함.', 'wiki_usage_explanation')}
 spec['evidence'].update(additions)
 spec['evidence'].update({
 'EV_Q_FUNCTION_BODY':evidence('D02',145,'의문사의 여부에 따라 설명 의문문\n과 판정 의문문으로 쓰인다.', '본문의 의문사 기준. 입력에서는 D04의 다의성 설명을 함께 고려해 실제 요구하는 답으로 분석한다.'),
 'EV_Q_V_WH_BODY':evidence('D02',145,'야들 너그 와 그래 시끄럽게 하노?', '설명 질문 -노의 직접 본문 용례.', 'source_example'),
 'EV_Q_HAGE':evidence('D02',138,'여기에 쓰인 ‘-가’는 해라체의 ‘-가’가 아닌 하게체의 ‘-ㄴ가’이다.', '것가의 해당 용례는 하게체 분석. 모든 가를 같은 종결로 합치지 않음.'),
 'EV_Q_GO_KKO':evidence('D04',13,'이게 와 니 까자고?(이게 왜 네 과자야?) → 무조건 대답해야 함\n이게 와 니 까자꼬?(이게 왜 네 과잘까?) → 혼잣말이라서 대답을 안 해도 됨', '위키가 제시한 -고/-꼬의 기능 대비 사례. 모든 발화로 보편화하지 않음.', 'wiki_example'),
 'EV_Q_JE_JI':evidence('D04',12,"경북 북부를 제외한 방언권은 '-지'가 판정 의문문에서 '-제', 설명 의문문에서 '-지'로 나타난다.", '지/제의 별도 질문 체계 기술. 모든 지/제 용법이 확인 질문이라는 뜻은 아님.', 'wiki_usage_explanation'),
 'EV_Q_ULJIN':evidence('D05',24,"중부 동해안 방언의 성조 비교(김차균) p.1116에서 '[울진] 이게에 누옷이고(누옷이노)?'라는 예문이 존재한다.", '위키의 울진 재인용 용례. 인용된 원문은 이번에 직접 확인하지 않음.', 'secondary_citation_within_wiki'),
 'EV_Q_RA_WIKI':evidence('D04',14,"형태소 사용 방법은 경남 방언을 알고 있다면 간단해서, '-(이)고/(이)가'를 써\n야 할 자리에 '-(이)로/(이)라'를 쓰면 된다.", '앞 문맥은 안동·청송. D02의 라 용례와 단순 일대일 대응 여부를 후속 대조.', 'wiki_usage_explanation'),
 'EV_Q_COP_NO_WIKI':evidence('D03',28,"옛 자료든 현대 구술 전사 자료든 무슨 자료를 봐도 '뭐노'와 같은 활용은 절대로, 실수로라도 사용하지 않는\n다.", '위키의 단정적 배제 주장. D02 계사+노 기록과 대조 보존하며 이 주장을 보편 금지로 채택하지 않음.', 'wiki_claim_not_adopted_as_universal'),
 'EV_Q_DEO_DADO':evidence('D02',146,'(98)의 ‘-다/도’는 표준형의 ‘-디’,‘-더냐’에 대응되는데,대부분 동사어간\n과 직접 결합하여 쓰이는 경우가 대부분인데,형용사어간과 결합하는 경우\n도 보인다(98ㅁ).', '회상 질문의 다른 실현 체계. -더-+-나/-노와의 관계는 후속 정제.')})
 for key in ('EV_Q_V_EXAMPLES','EV_Q_V_PAST','EV_Q_EXISTENCE_NA'):spec['evidence'][key]['evidence_kind']='source_example'
 for r in spec['rules']:
  # Research support limits remain in family ProcessingScope, not attested rule conditions.
  r['any_branches']=[{k:v for k,v in br.items() if k in ('question_kind','predicate_class','prefinal_type')} for br in r['any_branches']]
  r['limits']=['이번 직접 정보 질문 체계의 후보이며 모든 경상도 용법을 망라하지 않음.']
  r['primary_evidence_ids']=(['EV_Q_TAM','EV_Q_V_EXAMPLES','EV_Q_EXISTENCE_NA'] if r['id']=='SEM_Q_V_POLAR' else ['EV_Q_TAM','EV_Q_V_PAST','EV_Q_V_WH_BODY'] if r['id']=='SEM_Q_V_WH' else ['EV_COP_HOST'])
  r['supporting_evidence_ids']=['EV_Q_HOST','EV_Q_AMBIG','EV_Q_TARGET_STYLE']
  if 'C_PAST' in r['id']:
   r['primary_evidence_ids']=['EV_COP_PREFINAL_RULE']
   r['supporting_evidence_ids']+=['EV_Q_TAM']
   r['realization_basis']='application_of_cited_general_condition_not_directly_attested_full_sentence'
   if r['id'].endswith('POLAR'):r['primary_evidence_ids'].append('EV_COP_PAST')
   r['title']=r['title'].replace('과거 계사','-었- 계열이 있는 계사')
   for form in r['forms']:form['composition']='입력의 계사와 -었- 계열을 보존하고 종결어미만 조합한다. 이랐- 등 별도 방언 선어말형은 선택하지 않는다. 이 조합 전략의 현대 자연스러움은 미검증.'
  else:r['realization_basis']='source_condition_and_examples_not_heldout_translation_gold'
  if r['id']=='SEM_Q_C_POLAR':r['primary_evidence_ids'].append('EV_COP_ALLOMORPH')
  if r['id']=='SEM_Q_C_WH':r['primary_evidence_ids'].append('EV_COP_ALLOMORPH_GO')
  r['evidence_ids']=list(dict.fromkeys(r['primary_evidence_ids']+r['supporting_evidence_ids']))
  r['meaning']='예/아니오로 대답할 질문' if 'POLAR' in r['id'] else '누구·무엇·어디 등의 구체적인 답을 구하는 질문'
  r['generation_operation']='recompose_bound_predicate_question_ending'
 spec['observations']=[
  {'id':'OBS_Q_COP_NO','title':'계사+-노 기록','meaning':'D02의 계사+-노 용례를 보존. 기본 -고 후보가 다른 형태를 전역 금지한다는 뜻이 아님.','evidence_ids':['EV_Q_VARIANT'],'related_rule_ids':['SEM_Q_C_WH'],'status':'recorded_variant_not_executable_in_this_slice'},
  {'id':'OBS_Q_OTHER_FUNCTION','title':'명령·반어·감탄 질문','meaning':'질문 모양이라도 직접 정보 요청과 다름. 해당 해석을 분석 단계에서 구별.','evidence_ids':['EV_Q_FUNCTION_BOUNDARY'],'related_rule_ids':['SEM_Q_V_POLAR','SEM_Q_V_WH'],'status':'outside_current_function_scope'},
  {'id':'OBS_Q_SI','title':'-시- 설명 차이','meaning':'D04 8쪽 표와11쪽 설명 차이. 주체높임 없는 이번 범위와 분리.','evidence_ids':['EV_Q_SI_EXCEPTION'],'related_rule_ids':['SEM_Q_C_POLAR','SEM_Q_C_WH'],'status':'unresolved_source_difference'},
  {'id':'OBS_Q_REGION','title':'지역별 다른 질문 체계','meaning':'서부 -나, 울진·라/로 등의 체계를 무조건 합치지 않음. 지역 입력을 일괄 필수화하지 않음.','evidence_ids':['EV_Q_REGIONAL_VARIANT','EV_Q_RA_NONONE'],'related_rule_ids':['SEM_Q_V_WH','SEM_Q_C_POLAR','SEM_Q_C_WH'],'status':'followup_usage_refinement'},
  {'id':'OBS_Q_EXISTS','title':'있다·없다의 다른 결합 설명','meaning':'있나라는 직접 용례는 유지. -가 설명의 세부 조건은 별도 확인하며 대안 전체를 불허하지 않음.','evidence_ids':['EV_Q_EXISTENCE','EV_Q_EXISTENCE_NA'],'related_rule_ids':['SEM_Q_V_POLAR','SEM_Q_V_WH'],'status':'alternative_condition_unresolved'},
  {'id':'OBS_Q_SELF','title':'자문·하게체 ㄴ가/ㄴ고','meaning':'표면형 일부가 같다고 해라체 종결로 합치지 않음.','evidence_ids':['EV_Q_SELF_QUESTION'],'related_rule_ids':['SEM_Q_C_POLAR','SEM_Q_C_WH'],'status':'different_construction_outside_slice'}]
 spec['generation_policy']={'scope':'question_ending_only','lexeme_replacement':False,'preserve_prefinal_morphemes':True,
  'morphology':'analyst-supplied lemma/stem/nominal/prefinals/final-ending; fused syllables recompose the whole bound predicate',
  'missing_morphology':'knowledge candidate may be retrieved but handoff is needs_analysis',
  'uncertain_meaning':'do not randomly choose between different question meanings'}
 obs={o['id']:o for o in spec['observations']}
 obs['OBS_Q_COP_NO']['evidence_ids']+=['EV_Q_COP_NO_WIKI','EV_Q_ULJIN']
 obs['OBS_Q_REGION']['evidence_ids']+=['EV_Q_RA_WIKI','EV_Q_ULJIN']
 obs['OBS_Q_SELF']['evidence_ids']+=['EV_Q_HAGE','EV_Q_GO_KKO']
 obs['OBS_Q_EXISTS']['applies_to_lemmas']=['있다','없다']
 spec['observations'] += [
  {'id':'OBS_Q_PAST_SURFACE','title':'과거 계사 조합의 확인 수준','meaning':'일반 조건에 따라 입력의 계사·었 계열을 유지하는 시험. 모음 명사 뒤와 계사+었+노의 완성 예문은 읽은 범위에서 직접 확인하지 못함. 이랐- 같은 다른 형태는 이번에 선택하지 않음.','evidence_ids':['EV_COP_PREFINAL_RULE','EV_COP_PAST','EV_Q_HOST'],'related_rule_ids':['SEM_Q_C_PAST_POLAR','SEM_Q_C_PAST_WH'],'status':'general_rule_application_requires_generation_validation'},
  {'id':'OBS_Q_JE','title':'지/제의 다른 질문 용법','meaning':'별도 질문 체계로 후속 정제. 지/제를 모두 확인 질문이라고 확정하지 않음.','evidence_ids':['EV_Q_JE_JI'],'related_rule_ids':['SEM_Q_V_POLAR','SEM_Q_V_WH'],'status':'followup_usage_refinement'},
  {'id':'OBS_Q_DEO','title':'회상 질문의 다른 실현','meaning':'다/도와 더+나/노는 해당 문맥을 따로 확인할 후속 대상. 관찰만으로 두 체계가 모순이라고 단정하지 않음.','evidence_ids':['EV_Q_DEO_DADO','EV_COP_PREFINAL_RULE'],'related_rule_ids':['SEM_Q_C_PAST_POLAR','SEM_Q_C_PAST_WH'],'status':'outside_current_prefinal_scope'}]
 spec['question_interpretation']='D02는 의문사 여부로 설명한다. 조회에는 D04의 다의성 설명을 반영하여 실제 요구하는 답을 사용한다. 기능 분석은 연구자가 공급하며 문자열 유무와 동일시하지 않는다.'
 # Explicit condition-value evidence is the source of truth in this version.
 for v in spec['condition_basis'].values():v['evidence_ids']=[]
 spec['condition_evidence']=[
  {'feature':k,'allowed':vals,'evidence_ids':ids} for k,vals,ids in [
   ('question_kind',['polar'],['EV_Q_FUNCTION_BODY','EV_Q_HOST','EV_Q_AMBIG']),('question_kind',['wh'],['EV_Q_FUNCTION_BODY','EV_Q_HOST','EV_Q_AMBIG']),
   ('predicate_class',['adjective','verb'],['EV_Q_TAM','EV_Q_V_EXAMPLES']),('predicate_class',['copula'],['EV_COP_HOST','EV_Q_HOST']),
   ('prefinal_type',['eoss','none'],['EV_Q_TAM','EV_Q_HOST']),('prefinal_type',['none'],['EV_Q_TAM','EV_COP_PREFINAL_RULE','EV_Q_HOST']),
   ('prefinal_type',['eoss'],['EV_COP_PREFINAL_RULE','EV_Q_HOST'])]]
 inherited={n['id']:n for n in [json.loads(l) for l in (BASE/'graph/nodes.jsonl').read_text('utf8').splitlines()]}
 graph=previous.compile_graph(spec,inherited);nodes={n['id']:n for n in graph['nodes']}
 # A condition's evidence depends on its value, not only its feature name.
 for n in list(nodes.values()):
  if n['type']!='Condition':continue
  p=n['properties'];key=p['feature'];values=p['allowed']
  ev=next(x['evidence_ids'] for x in spec['condition_evidence'] if x['feature']==key and x['allowed']==values)
  graph['edges']=[e for e in graph['edges'] if not(e['source']==n['id'] and e['relation']=='SUPPORTED_BY')]
  for eid in ev:graph['edges'].append({'id':'E_'+previous.stable([n['id'],'SUPPORTED_BY',eid]),'source':n['id'],'relation':'SUPPORTED_BY','target':eid})
  p['evidence_role']='condition_interpretation; complete combination is justified at usage level'
 for r in spec['rules']:
  nodes[r['id']]['properties'].update({k:r[k] for k in ('primary_evidence_ids','supporting_evidence_ids','realization_basis','meaning','generation_operation')})
  for edge in graph['edges']:
   if edge['source']==r['id'] and edge['relation']=='SUPPORTED_BY':edge['evidence_role']='primary' if edge['target'] in r['primary_evidence_ids'] else 'supporting'
 for o in spec['observations']:
  graph['nodes'].append({'id':o['id'],'type':'UsageObservation','properties':{k:v for k,v in o.items() if k!='id'}})
  for rid in o['related_rule_ids']:
   graph['edges'].append({'id':'E_'+previous.stable([rid,'HAS_CONTEXT_NOTE',o['id']]),'source':rid,'relation':'HAS_CONTEXT_NOTE','target':o['id']})
  for eid in o['evidence_ids']:
   graph['edges'].append({'id':'E_'+previous.stable([o['id'],'SUPPORTED_BY',eid]),'source':o['id'],'relation':'SUPPORTED_BY','target':eid})
 graph['generation_policy']=spec['generation_policy']
 graph['edges'].append({'id':'E_'+previous.stable(['EV_Q_VARIANT','CONTRASTS_WITH','EV_Q_COP_NO_WIKI']),'source':'EV_Q_VARIANT','relation':'CONTRASTS_WITH','target':'EV_Q_COP_NO_WIKI','interpretation':'builder flags different assertions; does not adjudicate modern usage'})
 dump(HERE/'private/spec.json',spec);dump(HERE/'private/graph.json',graph)
 dump(HERE/'private/change_log.json',[
  {'before':'6용법의 근거 역할이 구별되지 않음','after':'본문 조건·용례와 재인용 보조 근거 분리','why':'특히 계사+었+노에 판정 예문을 직접 근거로 붙였던 연결 수정'},
  {'before':'지원 범위가 각 용법 조건에 반복','after':'가족의 지원 범위와 실제 질문 기능/서술어/선어말 조건 분리','why':'현재 미지원과 문법적 금지를 구별'},
  {'before':'기본6분기 밖 기록은 설명문에만 있음','after':'9개 관찰 노드로 해당 용법·근거와 연결','why':'참고로 검색되되 생성 어미 후보로 섞이지 않음'},
  {'before':'수정 구간의 형태소 정보가 없어도 일반 지시 전달','after':'조회 결과와 조합 준비 상태 구별; 형태소/보존 정보 부족 시 구체적으로 반환','why':'실제 작업 위치·어간·선어말·종결형을 명시하기 위해'}])
 print('built',VERSION,len(graph['nodes']),len(graph['edges']))
 return spec,graph
if __name__=='__main__':build()
