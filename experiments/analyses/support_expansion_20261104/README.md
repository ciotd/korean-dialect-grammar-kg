# 미지원 46곳 진단과 첫 지원 확장

2026-11-04. 이전 50건의 62개 종결 위치 중 `out_of_slice`였던 **46곳 전부**를 원문·기존 카드·분석·조회 기록과 대조했다. 이 46곳은 46문장이 아니다.

## 결과를 읽는 순서

1. [쉬운 결과 보고서](private/report.html): 주원인, 실제 수정, 50문장의 이전/이번/승인 참조 비교.
2. [검토 의견 처리](reviewer_resolution.md): 수용·부분 수용·정정.
3. [46곳 진단 원본](private/audit46.json), [수치](private/summary.json), [검증](private/validation.json).

## 작업과 산출물

| 작업 | 파일 | 범위 |
|---|---|---|
| 전체 46곳 대조 | `audit.py`, `finalize_audit.py`, `private/audit46.json` | 초기 진단 생성기는 확정 진단을 덮어쓸 수 있으므로 재실행 전 별도 출력 경로를 사용할 것 |
| 원문 확인 | `private/source_evidence.json`, `source_search.json`, `source_hashes.json` | 7개 PDF 해시, 전체 검색, 관련 쪽의 본문·일부 표 대조. 7종 전체 의미 재정독과 다름 |
| KG 확장 | `build_graph.py` | 기존 r4의 9용법 보존 + 긍정 현재 명사 서술/공손 어요 질문 2용법 |
| 분석·조회 연결 | `runtime.py` | 실제 EF 값·일반/의존명사 구분·unknown 처리. 문장별 답안 매칭 없음 |
| 생성 | `run.py` | 기존 실행기 재사용. Qwen이 전체 문장 작성. 조합기 결과 미전달·미대체 |
| 회귀 검사 | `test_runtime.py` | 범위·근거·미확정·계사 결합·기존 그래프 보존 17검사 |
| 같은 분석 재조회 | `replay.py` | 이전 62개 Qwen 응답 재사용. 새 모델 호출 없이 준비14→19 |
| 추가 전달 진단 | `handoff_probe.py` | 실제 KG 지시가 있는 17입력·19위치 고정. 기존 전달 vs 원형 보존 안내, 각17 생성 |
| 결과 관리 | `report.py` | 실제 실행 원본에서 통계·HTML 생성, 기존 관리 시스템 등록 |

## 실행 버전

- r5: 검토 전 초안. 과거·부정 계사를 포함하려던 안. **모델 실행에 쓰지 않음**.
- r6: 2용법만 남긴 첫 개발 버전. 개발 14건 실행 후 reviewer 보완.
- r7: 미확정·근거 역할·결합 안내 보완. `knowledge/authored/semantic_grammar_20261104_r7/private/graph.json`.
- 이번 실험은 Neo4j를 바꾸지 않고 버전 고정 JSON의 실제 관계를 조회한다. Neo4j의 내용이 r7로 바뀌었다고 해석하면 안 된다.

## 재현

저장소 루트에서 현재 프로젝트 Python 환경으로 실행한다. `test.py`의 접속 정보를 로컬에서 사용한다. 키를 문서·출력·Git에 넣지 않는다.

```powershell
python experiments/analyses/support_expansion_20261104/test_runtime.py
python experiments/analyses/support_expansion_20261104/replay.py
# 아래는 새 모델 호출이 발생한다.
python experiments/analyses/support_expansion_20261104/run.py dev
python experiments/analyses/support_expansion_20261104/run.py full50
python experiments/analyses/support_expansion_20261104/handoff_probe.py
python experiments/analyses/support_expansion_20261104/report.py
```

이미 실행에 사용한 그래프·실험 폴더는 수정하지 않는다. 코드나 KG를 변경할 때 새 버전·새 Run ID를 만든다. r7 작성 코드를 재사용해 다음 그래프를 만들 때는 OUT과 version부터 변경한다. `private/latest_*.json`은 최신 실행 위치를 가리키는 색인이며 실행 원본이 아니다.

## 해석 제한

- `ready`는 조건을 충족해 생성에 전달할 수 있다는 뜻이다. 자연스러움 인증이 아니다.
- old out46 → out29라는 수치만으로 17곳 개선이라고 하지 않는다. 12곳은 `no_matching_usage`가 먼저 표시되도록 바뀐 것이며, 준비 증가 5곳과 다르다.
- 9곳의 공유 형태 가능성을 모든 원문 유지의 정당화로 확대하지 않는다. 어휘·화용·억양·다른 문장 성분은 별도 문제이다.
- 문헌의 미관찰은 금지 규칙이 아니다. D02의 높임 명령 관찰과 위키의 세예 등을 단순 통합하지 않았다.
- 최종 50건은 회귀셋이다. 새 독립 평가 성능을 주장하지 않는다. 참조 문장은 보고서 비교에만 사용한다.
- 전달 진단은 설명·중복 필드 제거를 함께 바꾼 비교다. 효과가 있더라도 어느 한 문구만의 인과 효과로 주장하지 않는다.

## 다음 순서

생성 실패의 전달 방식 비교 결과를 먼저 해석한다. 이어서 남은 질문·제의, 요청·금지, 약속·의도 등의 지식을 원문 조건으로 정제한다. 각 묶음은 조건 노드·관계·근거·정상/반례/미확정 검사·개발 예문·최종 Qwen 기록이 갖춰질 때 완료로 표시한다. 근거 부족이나 충돌은 실행하지 않은 후보로 보존한다. 전체 12모듈 정제가 끝났다고 보고하지 않는다.

## 추가 비교의 최종 상태
- `realization_probe.py`: r8 결합형/설명만 바꾼 비교. 원문 보존 계약 위반 증가, 미채택.
- `typed_probe.py`, `prefix_probe.py`: 수정 단위·원문 보존 부분 전달 비교. 위반5/9가 남아 미채택.
- `prompt_contract_probe.py`: 같은 prefix 패킷에서 시스템 두 문장만 변경, 조건별2반복. 두 반복 모두 계약충족4/9로 해결되지 않음.
- 이 모든 수치는 선택된 두 용법9위치의 원문 보존 계약이며 자연스러움 점수가 아니다. 같은요청에서도LONG001출력변동이관찰됨.
- 현재 기본실행기는 r7. r8/r9는 실험자료만 보존하며 Neo4j적재없음. 모델의지시불이행은실제원시응답까지확인했으나내부원인은미확인. 실제서버실행명령을사용자에게요청함.
- 고정비교 config의 data_check.records=50은 부모전체데이터점검값이고 실제입력은 input_count=17이다. 과거설정은수정하지않고이해석을추가한다.
