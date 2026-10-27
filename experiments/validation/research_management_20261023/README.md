# 연구 관리 시스템 검증 · 2026-10-23

새 Qwen 호출 없이 기존 실행과 합성 자료로 검사했다. 기존 실험의 품질을 다시 평가한 결과가 아니다.

| 확인 항목 | 결과 | 근거 |
|---|---|---|
| 기존 파이프라인 + 관리 기능 단위·통합 검사 | 59개 통과(기존 30 + 관리 29) | [tests.json](tests.json), [실행 로그](tests.log) |
| 자동 등록 | 모의 실행 완료 후 SQLite·요약·현황 갱신 확인 | `RunnerIntegrationTests` |
| 기존 원본 보존 | 5회 실행, 총 1,067개 파일 해시 일치 | [전체 대조](original_run_integrity.json) |
| 비교 제한 | 다른 입력·미완료·원본 불일치 차단, 검사 계약 변경 시 통과 수 차이 미계산 | `ManagementTests` |
| 평가 자료 보호 | 동일 문장·공백 변형의 개발 입력 사용 차단 | `guard_dataset` 검사 |
| 로컬 HTTP 접근 | 임의 파일·잘못된 Host·토큰 없는 갱신·외부 Origin 차단 | `ServerTests` |
| 실제 브라우저 | 5회 목록, 실패 15건·변경 1건 필터, 실제 KG 조회·문서 열람 성공 | [브라우저 기록](private/browser_qa.json) |
| 기존 HTML 링크 | 8개 모두 HTTP 200 | 위 브라우저 기록 |
| 모바일 화면 | 390px 폭에서 페이지 넘침 없음, 표 내부 가로 스크롤 | [화면](private/mobile.png) |
| 합성 규모 점검 | 200회 × 50건 = 10,000개 결과 색인. 첫 동기화 8.578초, 재동기화 6.375초, 목록 조회 0.0072초 | [규모 점검](synthetic_scaling_200x50.json) |

규모 점검은 작은 합성 결과 레코드이며 모델 생성 처리량을 측정하지 않았다. 실제 큰 KG 조회 파일은 목록에 복사하지 않고 해당 문장 조회 시에만 읽는다. 서로 다른 PC의 성능을 보장하는 벤치마크가 아니다.

초기 검사에서 SQLite 연결을 닫지 않아 Windows 임시 폴더 정리에 실패했다. 연결의 commit/rollback 후 명시적으로 close하도록 수정하고 전체 검사를 통과했다. 모바일 표가 지나치게 좁아지는 문제는 표 내부 가로 스크롤로 수정하고 다시 확인했다.

재실행:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

브라우저 검사는 `tests/qa_research_dashboard_first50.cjs`에 있으며 기존 5회 실행과 두 로컬 서버(8765·8766)를 대상으로 한다. 테스트용으로 Node·Playwright·Chrome이 필요하지만 대시보드 자체에는 필요 없다. 이 환경에서는 Playwright가 이미 설치된 디렉터리를 `NODE_PATH`로 지정했다.

```powershell
node tests/qa_research_dashboard_first50.cjs
```

확정 50건 첫 실험 결과와 코드 사본은 수정하지 않았다. 파이프라인 현재 버전 0.1.4의 관리 연동은 모의 통합 검사로 확인했으며 실제 모델 50건을 재실행하지 않았다.
