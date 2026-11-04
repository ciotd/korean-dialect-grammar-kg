"""Build a new, bounded semantic layer; originals remain immutable."""
import hashlib,json
from pathlib import Path
from inventory import BASE,CACHE,HERE,ROOT,dump,read,sha
from semantic_graph import compile_graph,GraphReader

VERSION='semantic_foundation_20261102_r2'

def evidence(doc,page,quote,meaning,kind='source_statement'):
    text=next(p['text'] for p in read(CACHE/(doc+'.json')) if p['page']==page)
    start=text.find(quote)
    if start<0:raise ValueError('quote_not_found:'+doc+':'+str(page))
    source=next(s for s in read(BASE/'provenance/sources.json') if s['id']==doc)
    return {'document_id':doc,'pdf_page':page,'page_system':'PDF 1-based','page_text_sha256':hashlib.sha256(text.encode()).hexdigest(),'source_pdf_sha256':source['sha256'],'start':start,'end':start+len(quote),'quote':quote,'builder_paraphrase':meaning,'evidence_kind':kind,'access':'original_pdf_hash_verified_and_selected_page_checked','source_family':source['policy']['family'],'source_scope':source['policy']['time_scope']}

def build():
    original=[json.loads(s) for s in (BASE/'graph/nodes.jsonl').read_text(encoding='utf8').splitlines()];by={n['id']:n for n in original}
    ev={
      'EV_Q_HOST':evidence('D02',145,'1.서술어에 시상관련 형태가 통합되어 있지 않을 때\n용언 서술어 의문사 없음:-나 /있음:-노\n체언 서술어 의문사 없음:-가 /있음:-고\n2.서술어에 {엇}/{더}/{겠}등의 형태가 통합되어 있을 때\n의문사 없음:-나 의문사 있음:-노','서술어의 종류와 시상 형태가 어미 계열 선택에 함께 관여한다. 이 부분은 논문 각주162가 박종갑(1999)을 재인용한 것이다.','secondary_citation_within_thesis'),
      'EV_Q_SCOPE':evidence('D02',142,'해라체 의문법 종결어미는 판정 의문문과 설명 의문문으로 구분하여 지역\n분포 및 사용 양상을 살펴볼 필요가 있다.','해라체 의문문의 유형을 나누어 기술한 문맥이다.'),
      'EV_Q_AMBIG':evidence('D04',9,'두 예문에서 보이듯, 표준어는 "뭐 먹었어?"라는 문장이 "무언가를 먹었느냐 안 먹었느냐", 혹은 "어떠한 것을 먹었으냐"의 두\n가지 의미로 해석될 수 있다. 이는 강세와 맥락으로 구별해야 하며, 표기만으로는 구별할 수 없다.','의문사 모양의 단어가 있다는 이유만으로 설명 의문으로 정하지 않는다.','wiki_usage_explanation'),
      'EV_Q_TAM':evidence('D02',145,'‘-나/노’는 ‘-가/고’와는 달리,용언과 선어말어미와의 결합이 자유롭다.','나/노는 용언 및 선어말어미와 결합한다.'),
      'EV_Q_VARIANT':evidence('D02',146,'그러나 일부 용례\n에서는 ‘-노’가 계사와 결합하여 쓰이기도 한다(97ㅁ).','기본 네 갈래로 모든 실현형을 배제할 수 없다. 계사+노의 별도 용례가 있다.'),
      'EV_COP_HOST':evidence('D02',144,'‘-가/고’는 계사와 직접 결합하여 쓰이는 특징을 보인다.','가/고의 계사 결합을 직접 기술한다.'),
      'EV_COP_ALLOMORPH':evidence('D04',10,"체언이 자음으로 끝\n났으면 '~이가', 모음으로 끝났으면 '~가'가 이어지므로 합쳐서 '~(이)가'로 표기.",'명사 말음에 따른 이가/가, 같은 쪽에서 이고/고도 설명한다.','wiki_usage_explanation'),
      'EV_COP_ALLOMORPH_GO':evidence('D04',10,"체언이 자음\n으로 끝났으면 '~이고', 모음으로 끝났으면 '~고'가 이어지므로 합쳐서 '~(이)고'로 표기.",'명사 말음에 따른 이고/고를 설명한다.','wiki_usage_explanation'),
      'EV_COP_PAST':evidence('D04',11,'사람이가? → 사람이었나?','과거 형태 뒤 나의 실제 예가 있다. 다른 계사 활용 전체까지 승인하는 근거는 아니다.','wiki_example'),
    }
    rules=[]
    cases=[('V_POLAR','용언의 예/아니오 질문','polar',['verb','adjective'],['none','past'],'-나','GS_ENDRULE_Q_POLAR_V'),('V_WH','용언의 구체적인 답을 묻는 질문','wh',['verb','adjective'],['none','past'],'-노','GS_ENDRULE_Q_WH_V'),('C_POLAR','현재 계사 구문의 예/아니오 질문','polar',['copula'],['none'],'-가','GS_ENDRULE_Q_POLAR_C'),('C_WH','현재 계사 구문의 구체적인 답을 묻는 질문','wh',['copula'],['none'],'-고','GS_ENDRULE_Q_WH_C'),('C_PAST_POLAR','과거 계사 구문의 예/아니오 질문','polar',['copula'],['past'],'-나','GS_ENDRULE_Q_TAM_C'),('C_PAST_WH','과거 계사 구문의 구체적인 답을 묻는 질문','wh',['copula'],['past'],'-노','GS_ENDRULE_Q_TAM_C')]
    for code,title,q,pred,tam,form,legacy in cases:
        concepts=['G_Q_WH' if q=='wh' else 'G_Q_POLAR','G_MOOD_FUNCTION','G_HON_ADDRESSEE','G_END_FINAL']
        if tam==['past']:concepts.append('G_TAM_PAST')
        forms={'form':form,'unit':'final_ending','composition':'해당 용언 어간과 보존한 선어말 형태 뒤에 종결어미를 실현한다.','allomorphs':[]}
        if pred==['copula']:
            if tam==['none']:
                forms['composition']='명사와 계사 구성에 실현한다. 원문 종결형을 제거한 뒤 계사 이형태를 포함해 조합하며 이를 중복해서 붙이지 않는다.'
                allomorph_evidence='EV_COP_ALLOMORPH' if q=='polar' else 'EV_COP_ALLOMORPH_GO'
                forms['allomorphs']=[{'after':'consonant_final_nominal','surface':'이'+form[1:],'evidence':allomorph_evidence},{'after':'vowel_final_nominal','surface':form[1:],'evidence':allomorph_evidence}]
            else:
                forms['composition']='계사 뒤 이미 있는 -었- 계열을 보존한 뒤 종결어미를 실현한다. 이었-/였- 대 이랐-의 방언 표면형 선택은 아직 확정하지 않았다.'
        evidence_ids=['EV_Q_HOST','EV_Q_SCOPE','EV_Q_AMBIG']
        evidence_ids+=['EV_Q_TAM'] if pred!=['copula'] else ['EV_COP_HOST',allomorph_evidence] if tam==['none'] else ['EV_COP_PAST']
        rules.append({'id':'SEM_Q_'+code,'title':title,'summary':title+'에서 '+form+'를 종결어미 후보로 제시한다.','legacy_atom_ids':[legacy],'concept_ids':concepts,'modules':['M05','M06',*(['M01','M02'] if pred!=['copula'] else ['M02']),*(['M08'] if 'past' in tam else [])],
          'any_branches':[{'clause_role':['main'],'speech_act':['information_question'],'addressee_level':['plain'],'question_kind':[q],'predicate_class':pred,'prefinal_type':['eoss' if t=='past' else t for t in tam],'subject_honorific':['absent']}],
          'forms':[forms],
          'target':'same_clause.predicate.final_ending','preserve':['lexical_meaning','argument_roles','tense','polarity','addressee_level','question_kind'],
          'evidence_ids':evidence_ids,
          'limits':['현재·과거, 주체높임 없는 직접 정보 질문으로 이번 검증 범위를 한정한 설계 선택이며 문법 전체의 금지 조건이 아니다.','반어·확인·권유 질문, 아니다 및 시/더/겠 결합은 후속 정제 대상이다.','계사+노 등 별도 용례가 있으므로 이 후보 집합을 유일한 문법 정답으로 주장하지 않는다.','현대 화자의 자연스러움은 이 문헌의 존재만으로 인증하지 않는다.']})
    spec={'version':VERSION,'scope':'question_family_first_vertical_slice_not_full_KG','knowledge_status':'source_interpreted_and_review_pending','rules':rules,'evidence':ev,'design_choices':['조건은 동일 절에 묶는다.','module은 탐색 분류이고 후보 인정 조건이 아니다.','사용 범위 메타데이터와 현재 실행 지원 범위를 분리한다.','정보질문/main/주체높임없음/현재과거 제한은 초기 구현 범위이며 원문이 주장한 모든 용법이 아니다.'],'unresolved':['아니다와 주체높임 시 결합','과거 외 더/겠','계사+노 역사 용례와 현재 사용 범위','확인 의문 -제와 순수 정보 질문의 구별','시제와 표면 선어말 형태의 차이'], 'analysis_contract':{'origin':'builder_annotation_for_query_tests; not Qwen output','clauses':'각 절마다 고유 ID/문자 범위/서술어 범위/특징을 따로 기록','question_kind':'polar=예/아니오 여부, wh=내용 요청, null=입력만으로 미확정','unknown':'미확정 후보를 별도 반환. 무작위 선택하지 않는다.'}}
    spec['construction']={'id':'SEM_CX_HAERA_INFORMATION_QUESTION','properties':{'title':'해라체 정보 질문의 종결 구성','status':'bounded_development_slice'}}
    spec['feature_schema']={'clause_role':['main','embedded','quoted'],'speech_act':['information_question','statement','request','rhetorical_question','confirmation'],'addressee_level':['plain','polite'],'question_kind':['polar','wh'],'predicate_class':['verb','adjective','copula','negative_copula'],'prefinal_type':['none','eoss','gess','deo','other'],'tense':['past','present','future'],'subject_honorific':['absent','present']}
    spec['support_scope']={'clause_role':['main'],'speech_act':['information_question'],'addressee_level':['plain'],'predicate_class':['verb','adjective','copula'],'prefinal_type':['none','eoss'],'subject_honorific':['absent']}
    spec['condition_basis']={
       'clause_role':{'kind':'implementation_scope','evidence_ids':[]},
       'speech_act':{'kind':'implementation_scope','evidence_ids':[]},
       'subject_honorific':{'kind':'implementation_scope','evidence_ids':[]},
       'addressee_level':{'kind':'research_mapping_plain_input_to_haera_target','evidence_ids':['EV_Q_SCOPE']},
       'question_kind':{'kind':'source_interpretation','evidence_ids':['EV_Q_HOST','EV_Q_AMBIG']},
       'predicate_class':{'kind':'source_interpretation','evidence_ids':['EV_Q_HOST','EV_COP_HOST']},
       'prefinal_type':{'kind':'source_interpretation','evidence_ids':['EV_Q_HOST','EV_COP_PAST']}}
    spec['feature_concepts']={'clause_role':['G_CLAUSE_SCOPE'],'speech_act':['G_MOOD_FUNCTION'],'addressee_level':['G_HON_ADDRESSEE'],'question_kind':['G_Q_SCOPE','G_Q_WH_BIND'],'predicate_class':['G_PRED_KIND'],'prefinal_type':['G_TAM_SLOTS'],'subject_honorific':['G_HON_SUBJECT']}
    spec['knowledge_status']='source_interpreted_cross_review_corrections_applied_not_generation_validated'
    graph=compile_graph(spec,by);reader=GraphReader(graph)
    data=[]
    examples=[
      ('너 지금 웃어?','웃어','verb','none','polar','SEM_Q_V_POLAR'),
      ('너 왜 웃어?','웃어','verb','none','wh','SEM_Q_V_WH'),
      ('물이 차가워?','차가워','adjective','none','polar','SEM_Q_V_POLAR'),
      ('물이 왜 차가워?','차가워','adjective','none','wh','SEM_Q_V_WH'),
      ('기차가 멈췄어?','멈췄어','verb','past','polar','SEM_Q_V_POLAR'),
      ('기차가 왜 멈췄어?','멈췄어','verb','past','wh','SEM_Q_V_WH'),
      ('방이 조용했어?','조용했어','adjective','past','polar','SEM_Q_V_POLAR'),
      ('방이 왜 조용했어?','조용했어','adjective','past','wh','SEM_Q_V_WH'),
      ('그분이 의사야?','의사야','copula','none','polar','SEM_Q_C_POLAR'),
      ('여기가 무슨 장소야?','장소야','copula','none','wh','SEM_Q_C_WH'),
      ('그 사람이 학생이야?','학생이야','copula','none','polar','SEM_Q_C_POLAR'),
      ('그게 무슨 뜻이야?','뜻이야','copula','none','wh','SEM_Q_C_WH'),
      ('그 사람이 학생이었어?','학생이었어','copula','past','polar','SEM_Q_C_PAST_POLAR'),
      ('그게 무슨 뜻이었어?','뜻이었어','copula','past','wh','SEM_Q_C_PAST_WH'),
      ('그분이 의사였어?','의사였어','copula','past','polar','SEM_Q_C_PAST_POLAR'),
      ('여기가 무슨 장소였어?','장소였어','copula','past','wh','SEM_Q_C_PAST_WH'),
      ('어디 가?','가','verb','none',None,None),
      ('뭐 샀어?','샀어','verb','past',None,None),
      ('이게 아니야?','아니야','negative_copula','none','polar',None),
      ('그분이 선생님이셔?','선생님이셔','copula','none','polar',None),
      ('문을 닫아 줘.','닫아 줘','verb','none',None,None),
      ('기차가 멈췄나요?','멈췄나요','verb','past','polar',None),
      ('내일 비가 오겠어?','오겠어','verb','conjecture','polar',None),
      ('그 사람이 학생이었대.','학생이었대','copula','past',None,None),
    ]
    for i,(text,target,pred,tam,q,expected) in enumerate(examples,1):
        features={'clause_role':'main','speech_act':'information_question','addressee_level':'plain','question_kind':q,'predicate_class':pred,'prefinal_type':'eoss' if tam=='past' else 'gess' if tam=='conjecture' else 'none','tense':'past' if tam=='past' else None,'subject_honorific':'absent'}
        if i==20:features['subject_honorific']='present'
        if i==21:features['speech_act']='request'
        if i==22:features['addressee_level']='polite'
        if i==24:features['speech_act']='statement'
        start=text.index(target)
        predicate={'id':'p1','clause_id':'c1','span':[start,start+len(target)],'surface':target,'origin':'builder_manual_annotation'}
        ending_slot={'id':'end1','predicate_id':'p1','clause_id':'c1','boundary_status':'morpheme_boundary_not_yet_resolved'}
        bindings={k:{'clause_id':'c1','predicate_id':'p1' if k in ('predicate_class','prefinal_type','subject_honorific') else None,'origin':'builder_manual_annotation'} for k in features}
        variable=None
        if q=='wh':
            word=next(w for w in ['왜','무슨'] if w in text);offset=text.index(word)
            variable={'id':'w1','clause_id':'c1','scope_clause_id':'c1','span':[offset,offset+len(word)],'surface':word,'role':'asked_information','origin':'builder_manual_annotation'}
        analysis={'text':text,'origin':'builder_manual_annotation_for_development_query_test','clauses':[{'id':'c1','span':[0,len(text)],'target_span':[start,start+len(target)],'target_text':target,'features':features,'feature_bindings':bindings,'predicate':predicate,'ending_slot':ending_slot,'question_variable':variable}]}
        result=reader.query(analysis)
        data.append({'id':f'EASYQ{i:03d}','purpose':'development_query_contract_not_heldout_translation_evaluation','analysis':analysis,'expected_eligible':[expected] if expected else [],'expected_unresolved':['SEM_Q_V_POLAR','SEM_Q_V_WH'] if i in (17,18) else [],'retrieval':result,'packet':reader.packet(analysis,result)})
    dump(HERE/'private/foundation.json',spec);dump(HERE/'private/graph.json',graph);dump(HERE/'private/easy_development.json',data)
    validation=[]
    for d in data:
        actual=sorted(i['rule_id'] for i in d['retrieval']['clauses'][0]['eligible']);unknown=sorted(i['rule_id'] for i in d['retrieval']['clauses'][0]['unresolved'])
        validation.append({'id':d['id'],'eligible_matches_expectation':actual==sorted(d['expected_eligible']),'unresolved_matches_expectation':unknown==sorted(d['expected_unresolved'])})
    for row in validation:
        if not all(v for k,v in row.items() if k!='id'):raise AssertionError(row)
    dump(HERE/'private/query_checks.json',validation)
    preserved={p:sha(ROOT/p)==h for p,h in read(HERE/'private/original_hashes.json').items()}
    if not all(preserved.values()):raise ValueError('originals_changed')
    dump(HERE/'private/preservation.json',preserved)
    print(json.dumps({'new_rules':len(rules),'nodes':len(graph['nodes']),'edges':len(graph['edges']),'development_queries':len(data),'contract_passed':len(validation),'translation_experiments':0,'originals_unchanged':all(preserved.values())},ensure_ascii=False))
if __name__=='__main__':build()
