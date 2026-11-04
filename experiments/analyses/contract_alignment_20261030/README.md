# 문장 분석·수정 작업 연결 보완

이번 작업은 이전 답변을 수정된 프로그램으로 다시 처리한 것입니다. **새 Qwen 호출과 KG 조회는 0회이며, KG·카드 내용은 변경하지 않았습니다.**

[쉬운 비교 보고서](http://127.0.0.1:8767/reports/contract-alignment-20261030/report.html) · [입력별 원본 대조](private/cases.json) · [검증 결과](private/verification.json)

## 실제 결과

| 확인 조건 | Single: 변경 / 유지 / 확인 불가 | Multi: 변경 / 유지 / 확인 불가 |
|---|---:|---:|
| 이전 실제 출력 | 30 / 15 / 5 | 31 / 14 / 5 |
| 수정 작업 연결 보완 | 32 / 14 / 4 | 31 / 14 / 5 |
| 분석 보정도 추가 | 32 / 14 / 4 | 31 / 14 / 5 |

각 행·방식의 분모는 50입니다. 변경은 자연스러움 또는 정확도 지표가 아닙니다.

- LONG004 Single: 마세요→말끼를 보류. 원문의 금지 요청을 의지 표현으로 바꾸는 오류를 막았지만 오아도 등 다른 문제는 남았습니다.
- NEW004 Single: 시작+하를 동사로 인식해 시작했나가 적용됨. 공손함을 잃으므로 품질 개선으로 판단하지 않습니다.
- QUAL017 Single: EF+요/JX 처리로 전체 실패를 해소. Multi는 당시 worker 응답이 없어 복구를 주장하지 않습니다.
- 25개 입력에서 분석값 변경. 말높임 19개, 질문 기능 1개 보정. 부정 6개·진행 11개 값은 미확인으로 분리. 변경 개수는 오류율이 아닙니다.
- 분석 보정을 추가해도 문자열 변화는 0건. 조회·카드·Qwen 선택을 고정한 검증이므로 새 분석의 검색·선택 효과를 측정한 것이 아닙니다.

## 구현

| 파일 | 역할 |
|---|---|
| `src/kg_runtime/analysis_alignment.py` | 원문에 드러난 말높임·단순 의문사 질문 보정, 불확실 기능 및 분석 충돌 보존 |
| `src/kg_runtime/cards.py`, `card_pipeline.py` | 기능 목록과 요청 형식 일치; 실제 ID·설명 길이에 맞는 요청별 형식 |
| `src/kg_runtime/edit_contract.py` | 파생동사 판정, 기능 대조, 편집별 오류 격리, 보정 출처 기록 |
| `src/kg_runtime/scoped_operations.py`, `card_operations.json` | 기존 카드의 지정 범위 안에서 EF+요/JX 허용. 명사요·EC+요는 미지원 |
| `src/kg_runtime/card_experiment.py` | 보정 분석을 조회에 연결; 요청별 ID·길이 규칙을 서버 요청과 로컬 응답 검사에 적용 |
| `src/kg_pipeline/validation.py` | 문자열 최대 길이 검사 지원 |
| `tests/test_contract_alignment.py` 외 관련 테스트 | 반례·경계·독립 편집·요청별 형식 검사 |

분석 원문은 `analysis_call/parsed.json`에 남고 새 실행에서는 `aligned_analysis.json`, `analysis_alignment.json`을 별도로 저장합니다. 모델이 내놓은 값과 프로그램이 바꾼 값을 구분합니다. 미확인 기능은 조건 검사에서도 `analysis_unverified`이며, 거짓 또는 검증된 사실로 승격하지 않습니다.

독립 검토 `/root/card_runtime_review`가 정상 중이다 충돌, 명사 말/단순 고의 오인, 미확인→불일치 오인, 출처 오표기를 지적했습니다. 네 항목을 수정하고 반례 테스트를 추가했습니다. 이어 지적한 응답 길이의 로컬 검사 누락도 수정했습니다. 새 서버 호출에서 출력 제한이 실제 효율을 개선하는지는 미확인입니다.

## 재현 및 보존

기준 실행은 `20261030T062819598143Z_scoped_cards_{single,multi}_regression`입니다. 조회된 카드·모델의 선택·활용 제안을 고정합니다. 원래 맞는 요청/계획 ID만 새 계약 해시에 연결하며, 원래 잘못된 ID 3건과 길이 종료 3건은 복구하지 않습니다. 승인 표현은 재처리 계산이 끝난 후 표시용으로만 결합합니다.

- `replay.py`: 기존 100기록을 두 조건으로 재검증. 새 모델/DB 클라이언트를 만들지 않음.
- `report.py`: 실제 결과로 50문장 검색·비교 화면 생성.
- `verify.py --http`: 원본 587파일 해시, 코드 스냅샷, 조립 결과 182개, 50개 HTML 항목과 제한된 HTTP 경로 검사.
- `private/protocol.json`, `input_hashes.json`, `code_hashes.json`, `code_snapshot/`: 비교 조건·출처·실행 코드.
- `private/before/`: 이번 변경 직전 보존 코드. `baseline_run_snapshot/`은 별도로 이전 실험 코드에서 복사한 보충 자료.
- `private/first_replay_snapshot/`: 최초 완주한 재처리 결과. 최종 코드로 반복한 결과와 출력 동일.
- `private/test_results.json`: 관련 테스트 153개 통과. 이전 검사 실패도 별도 기록 보존.
- `private/reviewer.json`: 독립 검토 지적과 반영 내용. 방언 정확성 인증이 아님.

재실행 시 이 폴더의 산출물을 먼저 다른 고유 분석 폴더로 보존하십시오. 이전 실제 실험 폴더를 수정하지 않습니다. 로컬 Python에 `local/python`, `src`를 연결하는 실행 파일 자체 설정을 사용합니다.

## 다음 결정

높임을 잃는 선택, 연결어미의 기능 변경, 활용 조합 오류를 분리해 수정할 필요가 있습니다. 맞지 않는 후보를 막는 것뿐 아니라 대체 후보가 실제로 존재하고 전달되는지도 확인해야 합니다. 그 범위를 확정한 뒤 새 Qwen 실험을 진행합니다. 어휘·구문 변환 범위 확대는 별도 변경으로 기록합니다.
