# 조합기 연결 · 보조용언/절 연결 · 평서/높임 첫 묶음

## 실제 결과
- 최종 run: 20261103T085736340654Z_research_loop_expanded50. 원문50, 종결위치62, 새 Qwen 분석62회. Qwen 생성API0회, 승인한 Kiwi 조합기가 생성 담당.
- 14문장 일부변환, 15위치 조합, 조합실패0. 나머지47위치:지원밖41 / 분석보완5 / 보조범주미확정1. 자연스러움 점수 아님.
- 별도 구조점검12건의 최종run:20261103T085702848303Z_research_loop_expanded_diagnostic. 9변환,2지원밖,1분석보완. 기존50을 대체하지 않음.
- KG r2:136노드267관계, 질문6+평서3용법. 부모100/214 값 보존. 공통척추+12모듈 유지. Neo4j 실DB 새 적재 없음.
- 최종 구현검사 test_scope11 + test_expanded7. 집계검사4. 앞단계 기존 pipeline11/composer10도 통과. 번역정확도 평가와 구별.
- 실험7회3342파일 해시 대조 통과. 단계마다 새분석/코드/프롬프트 변경이 있으므로 단일요인 인과효과 주장금지.

## 읽기
private/report.html: 쉬운 설명, 50건 검색/비교, 보류원인, 검토자 링크.
private/results50.csv: 원문/연결직후/최종출력.
private/run_comparison.json, validation.json: 실제집계/해시검증.
private/reviewers: 기존 Orca Codex(gpt-6-astra), Claude(claude-opus-5-5)의 지시/응답/수정확인.

## 변경 파일
- src/kg_runtime/realization.py: 원형태소의 말단EF만 변경. 불규칙-I/-R 보존, 계사검사, 해예표면후조건.
- experiments/analyses/research_loop_20261103/run.py: 기존실행기 확장, 새Qwen분석/조회/조합/최종문장/원본로그/자동등록.
- experiments/analyses/condition_bridge_20261103/bridge.py: projection/construction 주입.
- scope_runtime.py: 의문사owner·보조연결을 실제Kiwi ID에 결속. 의미는모델추론,코드는참조/형태검사. 확인한 보조체인의EP시 근거수집.
- expanded_runtime.py: 실제조건관계로 두construction조회; source_final/prefinal_sequence관찰값과VX의모델추론 구별.
- build_graph.py: 정확한문헌인용/쪽/PDF해시 검증, 재사용용법3개 연결. 최종 semantic_grammar_20261103_r2 생성.

## 재실행 (프로젝트 루트)
python -X utf8 experiments/analyses/research_loop_20261103/run.py expanded_diagnostic
python -X utf8 experiments/analyses/research_loop_20261103/run.py expanded50
python -X utf8 -m unittest discover -s experiments/analyses/grammar_expansion_20261103 -p test_scope.py
python -X utf8 -m unittest discover -s experiments/analyses/grammar_expansion_20261103 -p test_expanded.py
기존 test.py 인증설정과 local/python 의존성 사용. 실행마다 고유RunID. 비공개 원문/인증을 커밋하지 않는다.

## 검토 반영과 남은 한계
Codex I01 내부명사/복수EC우회, I02 의문사단순위치판정, I03 VX출처/연결된높임, I04 other선어말과대허용은 반례수정 확인. Claude 지적의 근거쪽혼용/아요어요중복/높임근거누락/축약거짓경고 반영.
I05 개별 Condition→SUPPORTED_BY는 미완료. 규칙단위 근거는 연결됨. 개별조건에서 문헌해석과 실험상범위 이유를 더 분리해야 함.
모든VX·복합보조체인·절·화행 지원 아님. 의문사owner 자체를 모델이 잘못 판단할 수 있음. 출력의 Kiwi재분석 경고2건을 오류율로 사용하지 않음.
config.comparison 일부설명은 이전paired실험에서물려받음. 실제이번 arms/realizer/paired_generation=false를 기준으로 해석한다. Qwen generation_calls=0.
브라우저시각검사는 미수행. HTML50행/링크/JS문법검사와 PDF2쪽화면검사로 구별기록.

## 다음 순서와 종료 기준
1. 분석보완5+범주미확정1 위치를 실제답변/관찰형태로 대조:지식부족·의미미확정·참조오류 구분, 코드수정은반례검사통과.
2. 새조건별 출처와 실험범위 이유 분리:각조건의근거또는구현선택추적가능.
3. 다음 지식묶음(명사계사·비높임평서·약속 등)은 사용자와 우선순위확정 후 문헌정제→검토→진단→50회귀. 지원밖을비문/모델실패로세지않음.
