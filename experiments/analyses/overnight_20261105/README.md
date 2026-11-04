# 11월5일 연구 미팅·논문 인계

완료: 오류 피드백12호출, r7/r10 개발16 비교48호출, 기존50 비교162호출, 쉬운30 지식·형식 비교120호출. 합계342호출·473,541토큰. 사람 자연스러움 평가는 미실시.

- [미팅 보고서](private/report.html) / [브라우저](http://127.0.0.1:8767/reports/overnight-20261105/report.html)
- [논문 제안 방법·실험 인계](private/paper_handoff.md)
- [최초 승인 계획](PLAN.md)
- [① 피드백](STAGE1.md), [② 과거 계사](STAGE2.md), [③ 분석 진단](STAGE3.md), [④ 기존50](STAGE4.md), [⑤ 남은 범위](STAGE5.md), [⑥ 쉬운30](STAGE6.md)
- [파일럿 사전 계획](PILOT_PLAN.md)

## 판단

r10은 조건 조회·전달 범위를4위치 늘렸지만 생성은2위치에서 실패했다. 쉬운 단문에서도 과거형 손실이 나왔다. r7운영/r10실험후보를 유지하며 동일 프롬프트 반복을 멈췄다. 전역 unknown 차단 완화는 미채택. 7종 전체 지식 정제·미지원 전면 확장·독립 논문 평가가 끝났다고 주장하지 않는다.

모든 최종 문장은 Qwen 원시 출력이다. 코드가 정답으로 대체하지 않았다. 테스트/자동 경고/출력 변화는 방언 정확도 지표가 아니다. 참조 문장과 기대 완성형은 새 생성 요청에 넣지 않았다.

## 구현

- build_past_graph.py: 기존 r7 보존, r10 후보 조건·실현·근거 생성.
- candidate_runtime.py / paired_kg.py: 같은 분석으로 두 그래프 조회·생성 비교.
- analysis_diagnostic.py:62목표와 형태 분석 후보를 읽기 전용으로 추적.
- easy_pilot.py:같은 분석·지식의 정보 유무/직렬화 비교. 기대형 제외·정보 역복원 검사.
- src/kg_pipeline/io.py:문자열은 그대로 전송하고 dict는 기존 JSON 직렬화 유지. 모의 전송·기존30테스트로 확인.
- report_builder.py:실행 원본으로 표·전체 출력 보고서 생성.
- src/research_management/server.py:보고서6파일만 허용하는 로컬 경로 추가. 기존8767서버 갱신.

## 검증·재현

사용 Python:
C:\Users\ciot28\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -X utf8

후보 runtime이 local/python을 포함한 기존 의존 경로를 사용한다. 다른 Python 환경에서는 pypdfium2 등의 의존성이 없어 검사가 실패할 수 있다. 새 설치는 수행하지 않았다.

실행 원본4개와 중단0호출 run을 별도 보존. private/latest_*.json의 경로에서 입력·분석·조회·요청·원시 응답·코드/KG 사본·해시 확인. 각 완료 run의 실행 중 코드/KG 불변 검사 통과. 통제 비교는 결정론적 출력을 보장하지 않으며 단회 결과의 일반 성능을 주장하지 않는다.

실행기는 승인된08시KST 마감을 코드에 포함한다. 이후 새 실행은 새 Run ID와 새 승인 범위·마감을 기록해야 한다. 보존 원본을 덮어써 재사용하지 않는다. 오프라인 재집계·보고서는 report_builder.py와 검사 도구로 재현한다.

로컬 Git 복구 체크포인트를 단계 전후 생성했다. 원격 push는 이번 작업에서 하지 않았다. private실행 원본은 로컬 별도 보존되고 PDF·인증정보는 커밋하지 않았다.
