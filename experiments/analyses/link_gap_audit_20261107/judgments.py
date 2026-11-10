"""Human-readable audit judgments, explicitly separate from measured evidence.

Labels concern the current integrated entry point, not every historical experiment.
No row authorizes a KG mutation or certifies language quality.
"""
PROFILES = {}
def group(key, category, ids, implemented, missing, evidence, history=None):
    for id in ids.split():
        assert id not in PROFILES,id
        PROFILES[id] = dict(profile=key,category=category,implemented=implemented,missing=missing,evidence=evidence,history=history)

group('unknown','공통 처리 구현', 'G_FEATURE_UNKNOWN',
 '조건값을 참·거짓·미확정으로 나누고, 미확정이면 후보 적용을 보류하는 코드가 있다.',
 '현재 구현이 판정하는 것은 저장된 입력 특징이다. 원문 근거의 불확실성과 지역 프로필까지 자동 판정하는 전체 설계는 아니다. G_* 연결을 조회하지 않고 공통 함수로 처리한다.', ['query'])
group('alignment','공통 처리 구현','G_TOKEN_ALIGNMENT',
 'Kiwi 조각의 원문 글자 위치, 단위별 범위, 전달 직전 원문 일치 검사를 실제로 수행한다.',
 '최종 생성 문장까지 이어지는 원문–분석–출력의 완전한 대응 그래프는 없다. 이 책임은 용법마다 복제하지 않고 공통 처리에 있다.', ['morphology','observe','packet'])
group('tags','공통 처리 구현','G_TAG_MAPPING',
 'raw tag와 base_tag를 함께 보존하고, 서술어 종류의 관찰값과 모델 판단값을 구별한다.',
 '학교 품사·기능·온톨로지 사이의 완전한 다대다 어댑터는 없다. 불규칙 표지는 raw tag 안에 남지만 별도 inflection_flag는 없다.', ['morphology','observe','bind'])
group('predicate','용법에 한정 구현','G_PRED_KIND G_ADJ_STATE G_NEG_COPULA',
 '동사·형용사·계사·부정계사를 관찰하고 Qwen 판단으로 결속하며, 실제 용법의 조건에 사용한다.',
 '뜻 ID에 따른 동음이의어 분리와 학교 문법 분류까지 구현한 것은 아니다. 특징값을 사용하지만 이 공통 항목 ID와 연결하지 않았다.', ['observe','analysis','bind','query'])
group('honorific','용법에 한정 구현','G_HON_SUBJECT',
 '시/시었 형태와 Qwen의 주체높임 판단을 별도로 다루고 용법 조건에서 검사한다.',
 '누구를 높이는지 지시대상과 결속하고 출력에서 동일 대우를 검사하는 전체 절차는 없다.', ['observe','analysis','bind','query'])
group('stem','분석·지시 일부만 구현','G_VERB_STEM G_VERB_DERIVED',
 '형태 조각에서 어간을 얻고 파생 접미사가 있으면 앞부분을 합쳐 어간을 만든다.',
 '어휘 뜻 사전, 어간 변이의 동일 의미 판정, 허용된 생산 파생 규칙은 없다. 어간 관찰을 설계 전체의 구현으로 볼 수 없다.', ['observe','morphology'])
group('units','분석·지시 일부만 구현','G_UNIT_ONTOLOGY G_NP_HEAD',
 '원문 어절과 명사·조사·서술어·연결어미·보조구성 단위를 만들고 ID와 범위를 준다.',
 '명사 단위는 어절 안의 명사 조각을 묶는 방식이다. 여러 어절에 걸친 명사구의 핵·경계나 전체 구문 계층을 만드는 것은 아니다.', ['morphology','observe'])
group('roles','분석·지시 일부만 구현','G_VERB_ARGFRAME G_CASE_ROLE G_CLAUSE_COMPONENT G_VOICE_FRAME',
 'Qwen에게 행위자·대상·수혜자·사동주 등의 관계를 묻고 대상 ID·종류를 검사한다.',
 '동사 뜻별 논항 사전과 변환 전후 의미역 비교는 없다. 관계가 올바른 의미를 가졌는지는 타입 검사로 증명되지 않는다.', ['analysis','bind','generation','diagnostic'])
group('modifier','분석·지시 일부만 구현','G_ADJ_ADNOMINAL G_END_ADNOMINAL G_CLAUSE_RELATIVE',
 '관형형어미를 단위로 만들고 modifier_head 관계를 받을 수 있다.',
 '관형절 내부 논항의 빈자리·시간 해석·수식 관계 보존을 끝까지 검사하는 구현은 없다. 전용 방언 변환 정제도 보류되어 있다.', ['observe','analysis','bind','gaps'])
group('nominal-clause','분석·지시 일부만 구현','G_END_NOMINAL G_CLAUSE_NOMINAL',
 '명사형어미 ETN을 관찰하고 연결 단위로 만들 수 있다.',
 '명사절의 안쪽·바깥쪽 구조, 의존명사와의 구별, 명사화 범위 포트는 없다. ETN을 인식한다는 것만으로 명사절 처리를 구현한 것은 아니다.', ['observe','gaps'])
group('speech-functions','분석·지시 일부만 구현','G_ADJ_AFFECT G_Q_RHETORICAL G_Q_INTENTION',
 '감탄·발화 의도·확인 등 일부 특징을 모델에게 묻고 생성 시 기능 보존을 지시한다.',
 '형용사 정서, 수사의문 내부 질문 변수, 종결 게의 세부 의도를 각각 결속하는 전용 구성은 없다.', ['analysis','generation'])
group('existence','분석·지시 일부만 구현','G_ADJ_EXISTENCE G_MAIN_BECOME',
 '서술어 종류와 본용언/보조구성의 관찰 및 보조기능 판단을 받는다.',
 '있다의 존재·소유와 되다의 지정·성립 등 뜻별 결합 클래스를 만드는 전용 절차는 없다.', ['observe','analysis'])
group('focus','용법에 한정 구현','G_PARTICLE_FOCUS',
 '강조 이야, 제외 밖에, 끝점 까지의 좁은 조건 후보가 별도로 존재한다.',
 '만·도·마저·조차 전체와 작용 범위 검증은 없다. 개별 후보의 동작을 공통 설계 전체로 확대하면 안 된다.', ['refined','query'])
group('case-semantics','분석·지시 일부만 구현','G_PARTICLE_INSTRUMENT G_PARTICLE_OBJECT G_PARTICLE_SUBJECT G_PARTICLE_TOPIC',
 '조사 단위와 붙는 명사를 만들고 주제·대상·방향 등 일부 기능값을 받을 수 있다.',
 '도구/자격, 주격/보격 등을 완전히 구별하거나 대응 형태를 선택하는 전용 용법은 없다. 목적격 생략·대체는 조건 근거 부족으로 명시적으로 보류됐다.', ['observe','analysis','gaps'])
group('connective-deferred','분석·지시 일부만 구현','G_END_CONCESSION',
 '양보·대조라는 분석값은 받을 수 있다.',
 '도/지만 계열 변환 후보는 의미 보존·표 대응의 문제로 보류되어 현재 56개에는 없다.', ['analysis','build'])
group('sequence','용법에 한정 구현','G_END_SEQUENCE G_CLAUSE_LINK',
 '선후·중단·조건·이유 등의 좁은 용법과 앞뒤 서술어 관계 요구가 있다.',
 '사건 동일성·시간 순서·공유 논항을 포함한 완전한 절 관계 그래프는 아니다.', ['refined','analysis','bind','query'])
group('ending-slots','분석·지시 일부만 구현','G_END_SLOT G_TAM_SLOTS',
 '선어말어미 종류와 시→었 같은 순서를 관찰하고 조건에 쓴다.',
 '선택된 목표 어간과 모든 어미의 결합 적합성을 검사하는 활용 계획기는 현재 경로에 없다. 원문 관찰과 목표 실현 검증을 구분해야 한다.', ['observe','query','generation'])
group('ellipsis','분석·지시 일부만 구현','G_CLAUSE_ELLIPSIS',
 '생략된 참여자를 만들지 말라는 지시와 null 허용이 있다.',
 '생략 유형을 구조화하고 불완전 문장별 정책을 수행하는 전용 분석기는 없다.', ['analysis'])
group('clause-keys','분석·지시 일부만 구현','G_CLAUSE_EMBED G_CLAUSE_HEAD G_QUOTE_BOUNDARY',
 'Qwen이 절 ID와 주절/내포/인용 구별을 반환하며 일부 관계에 동일 절 검사를 한다.',
 'parent_id·지배 관계·인용 소유자·재귀 절 그래프는 분석 계약에 없다. 절 이름표를 전체 구문 분석으로 말하면 안 된다.', ['analysis','bind'])
group('scope','분석·지시 일부만 구현','G_CLAUSE_SCOPE',
 'negation_target 관계와 절 ID를 받을 수 있고 범위 보존을 지시한다.',
 '부정·의문·초점 연산자의 범위 그래프를 생성 전후 비교하지 않는다.', ['analysis','bind','diagnostic'])
group('adnominal-time','분석·지시 일부만 구현','G_TAM_ADNOMINAL',
 '관형형 위치와 주변 시제 형태를 관찰할 수 있다.',
 '관형절 시제·회상 해석 및 출력 보존 검사 전용 경로는 없다.', ['observe','gaps'])
group('aspect','용법에 한정 구현','G_TAM_ASPECT',
 '완료 보조용언 후보와 일부 진행·희망·시도 등 보조구성 보존 후보가 있다.',
 '어휘상과 문법상, 사건 완료성의 전체 구별은 없다. 결과상 resultative는 보존 후보의 허용값에서 빠져 있다.', ['refined','analysis'])
group('modality','용법에 한정 구현','G_TAM_MODALITY',
 '겠의 추측/의지 기능을 조건으로 겄 후보를 제시한다.',
 '미래·의도·추측·당위의 모든 표현 및 문맥적 범위를 구현한 것은 아니다.', ['refined','analysis','query'])
group('aux-benefactive','용법에 한정 구현','G_AUX_BENEFACTIVE',
 '수혜 보조용언 요청 후보와 일반 보조구성 보존 후보가 있다. 본용언과 보조용언 관계를 검사한다.',
 '이 공통 ID를 legacy_ids에 넣지 않았다. 수혜자·객체높임 보존 검증까지 완성된 것은 아니며 실제 분석 실패도 남아 있다.', ['lead','refined','bind','query'])
group('aux-preserve','용법에 한정 구현','G_AUX_DESIRE G_AUX_OBLIGATION G_AUX_PROGRESS G_AUX_TRIAL',
 '공통 보조용언 보존 후보가 해당 기능값을 받아 구성을 유지하라고 전달한다.',
 '새 방언 변환이 아니라 보존 지시다. 경험주·점진 변화·당위 세부 뜻 등 전체 계약이 구현된 것은 아니다.', ['refined','query','generation'])
group('aux-state-gap','분석·지시 일부만 구현','G_AUX_STATE',
 '분석 계약에는 결과 상태 resultative 값이 있다.',
 'INT_AUX_PRESERVE_COMMON의 제목은 상태를 포함하지만 실제 허용값에는 resultative가 없다. 연결만 추가해도 이 조건 불일치는 고쳐지지 않는다.', ['analysis','refined','query'])
group('aux-role','분석·지시 일부만 구현','G_AUX_ROLE',
 'VX 관찰을 바탕으로 보조구성을 만들고 모델의 기능과 본/보조 관계를 결속한다.',
 '어휘화된 구성과 본용언의 뜻을 사전으로 구별하지 않는다. VX가 관찰되지 않으면 보조구성 후보 자체가 만들어지지 않을 수 있다.', ['observe','analysis','bind'])
group('causative','용법에 한정 구현','G_CAUS_DERIVE G_REALIZATION_ALLOWLIST G_REALIZATION_CONTRACTION',
 '깨우·돋구·낮추의 명령형 축약 후보처럼 한정된 어간 목록과 형태 지시가 있다.',
 '사동 어휘 사전, 결락/미관찰 구별, 일반 축약 검증이 아니다. 최종 결합은 Qwen이 하며 코드 조합기는 현재 최종 생성 경로에 쓰지 않는다.', ['refined','generation'],history='composer')
group('passive','분석·지시 일부만 구현','G_PASS_ANALYTIC',
 '모델의 voice 값과 피동 보존 후보는 있다.',
 '어 지다의 상태 변화와 피동을 논항 프레임으로 구별하는 전용 구현은 없다. 분석적 피동 변환은 근거 부족으로 보류돼 있다.', ['analysis','refined','gaps'])
group('unsupported','분석·지시 일부만 구현','G_ANALYSIS_UNSUPPORTED',
 '조회 거절·미확정·전달 누락을 기록하고 생성 결과를 사람 검토 필요로 남긴다.',
 '모든 필수 문법 구성이 지원됐는지 검사하는 지원 목록이 없으므로 전체 지원 완료 여부를 판정하지 못한다.', ['query','packet','runner'])
group('invariant','분석·지시 일부만 구현','G_INVARIANT_AUDIT',
 '출력의 과거 표지 수 감소와 미전달 규칙 ID 선언을 경고한다.',
 '지시대상·논항·부정 범위·시제·인용·높임의 구조 비교는 없다. 과거 표지 개수 일치도 의미 보존을 보장하지 않는다.', ['diagnostic'])
group('wh-current-gap','현재 전용 구현 없음','G_Q_SCOPE G_Q_WH_BIND',
 '현재는 절 ID와 질문 종류라는 더 거친 정보만 받는다.',
 '의문사 출현 절과 의미 범위 절을 분리한 WhBinding·허가 경로가 현재 계약에 없다. 이전 실험의 제한적 검사 코드는 존재하지만 현재 실행기에서 호출하지 않는다.', ['analysis','runner'],history='wh-old')
group('deferred-constructions','현재 전용 구현 없음','G_GE_CAUSATIVE_HA G_GE_HA_ORDER G_GE_HA_PROMISE G_GE_HA_PROPOSAL G_GE_DEGREE G_GE_LIMIT G_TAM_PROSPECTIVE G_BOUND_NOUN_GEOT',
 '문헌 항목 검색과 일반 생성 지시는 가능하다.',
 '사동/명령/약속/제안 구별, 정도·한계와 목적 구별, ㄹ 것+계사 관계가 부족해 전용 후보를 보류하거나 목적 한정으로 좁혔다. 문헌 검색 가능성을 실행 구현으로 세지 않는다.', ['build','gaps','legacy'])
group('source-gaps','현재 전용 구현 없음','G_LEX_DATE G_NUMERAL_ROLE G_NUMERAL_COUNTER',
 '문헌 목록에는 관련 자료가 남아 있다.',
 '날짜·수사 표의 셀 대응과 기능 근거를 확정하지 못해 후보 정제를 보류했다. 날짜 오프셋 계산이나 분류사별 선택 코드는 현재 경로에 없다.', ['gaps','runner'])
group('realization-not-active','현재 전용 구현 없음','G_VERB_INFLECTION G_VERB_ALLOMORPH G_REALIZATION_ALLOMORPH G_REALIZATION_CONTEXT G_REALIZATION_PARTICLE',
 '원문 형태는 관찰하지만 목표 형태의 조합은 Qwen에게 맡긴다.',
 '현재 실행기에는 목표 활용 부류·끝소리·조사 재결합 검사 호출이 없다. 과거 Kiwi 조합기와 제한된 어미 결합 도구는 현재 최종 생성의 증거가 아니다.', ['observe','runner','generation'],history='composer')
group('not-implemented','현재 전용 구현 없음','G_VERB_COMPOUND G_ADJ_ADVERB G_NOUN_PROPER G_PARTICLE_STACK G_PARTICLE_VOCATIVE G_END_COMPOSITE G_Q_GUESS_CHALLENGE G_Q_INDEFINITE G_HON_OBJECT G_CLAUSE_COORD G_QUOTE_DIRECT G_AUX_CONCESSIVE_ACK G_AUX_REPETITIVE G_LEX_INTERJECTION G_LEX_ONOMATOPOEIA G_LEX_PROTECTED G_LEX_RETRIEVE G_LEX_SELECTION G_LEX_SENSE G_REALIZATION_ORTHO G_REALIZATION_PROSODY G_ANALYSIS_ALTERNATIVES',
 '관련 문헌이 문자열 검색에 잡히거나 Qwen이 자체 지식으로 처리할 수는 있다.',
 '현재 분석 계약·조회·생성 후 검사에서 이 설계의 전용 입력/출력 구조와 실행 절차를 확인하지 못했다. 전역 보존 지시나 단순 관련 문자열은 구현 증거로 세지 않았다. 자료에서 보류 이유가 확인되지 않는 항목의 개발자 의도는 미확정이다.', ['analysis','legacy','runner'])
group('aggregate','묶음 창구 설계만 존재','G_CASE G_COP G_HON G_LEMMA G_MOOD G_MORPH_REALIZATION G_NUMERAL G_SCOPE G_TAM G_TIME_REFERENCE G_WH',
 '일부 하위 책임은 별도 함수·특징·용법으로 처리된다.',
 '선택한 하위 계약 ID와 결속 인스턴스를 받는 공통 디스패처는 없다. 이 11개는 원래 개별 변환 규칙이 아니라 묶음 창구이므로 1:1 용법 연결 누락으로 세는 것도 부정확하다.', ['analysis','runner'])

# Suggested conceptual correspondence only. Never automatically materialize edges.
PROPOSED = {
 'INT_AUX_PRESERVE_COMMON':['G_AUX_ROLE','G_AUX_PROGRESS','G_AUX_DESIRE','G_AUX_OBLIGATION','G_AUX_BENEFACTIVE','G_AUX_TRIAL'],
 'INT_CAUS_CONTRACT_AARA':['G_CAUS_DERIVE','G_REALIZATION_CONTRACTION','G_REALIZATION_ALLOWLIST'],
 'INT_CONN_GEOLLANG':['G_END_CONDITIONAL'],
 'INT_CONN_INTENT_LLAKKO':['G_CLAUSE_LINK','G_TAM_MODALITY'],
 'INT_CONN_INTERRUPT_DA':['G_END_SEQUENCE'],
 'INT_END_HORT_POLITE_IPSIDEO':['G_MOOD_FUNCTION','G_END_FINAL','G_HON_ADDRESSEE'],
 'INT_END_Q_CONFIRM_JE':['G_Q_POLAR','G_END_FINAL'],
 'INT_LEAD_DECL_PAST_DA':['G_TAM_PAST','G_END_FINAL'],
 'INT_LEAD_DECL_PRESENT_DA':['G_PRED_KIND','G_ADJ_STATE','G_END_FINAL'],
 'INT_LEAD_PROHIB_PLAIN':['G_NEG_PROHIBITIVE'],
 'INT_LEAD_REQUEST_JU_AUX':['G_AUX_BENEFACTIVE','G_HON_ADDRESSEE'],
 'INT_LEAD_REQUEST_JU_MAIN':['G_VERB_ARGFRAME','G_MOOD_FUNCTION','G_HON_ADDRESSEE'],
 'INT_NOM_LOC_YEO':['G_PRON_DEICTIC'],
 'INT_NOM_WH_EODE_A':['G_Q_WH_BIND'], 'INT_NOM_WH_MEO':['G_Q_WH_BIND'], 'INT_NOM_WH_NU':['G_Q_WH_BIND'],
 'INT_PART_EXCEPT_BAKKI':['G_PARTICLE_FOCUS','G_NEG_SCOPE'],
 'INT_PART_FOCUS_SA':['G_PARTICLE_FOCUS'],
 'INT_PART_GEN_ZERO':['G_CASE_ROLE','G_NP_HEAD'],
 'INT_PART_MEASURE_MANCHI':['G_PARTICLE_COMPARE'],
 'INT_PART_SIMILAR_MAENCHIRO':['G_PARTICLE_COMPARE'],
 'INT_PART_UNTIL_KKEOJI':['G_PARTICLE_FOCUS'],
 'INT_Q_CONFIRM_ANIGA':['G_Q_POLAR','G_NEG_LONG'],
 'INT_TAM_GET_GEOT':['G_TAM_MODALITY'],
 'SEM_EXT_COP_PAST_HAEYE':['G_TAM_PAST','G_NEG_COPULA','G_REGISTER_MAP'],
 'SEM_SUP_COP_PRESENT':['G_PRED_KIND','G_REGISTER_MAP','G_END_FINAL'],
 'SEM_SUP_POLITE_Q_EO':['G_MOOD_FUNCTION','G_HON_ADDRESSEE','G_END_FINAL'],
}
