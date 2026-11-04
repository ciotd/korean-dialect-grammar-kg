# 2026-11-04 서버 실행 명령 확인

사용자가 전달한 명령을 확인했다. 현재 프로세스나 로컬 모델 파일을 직접 열어본 것은 아니다.

| 확인 항목 | 판단 |
|---|---|
| model 경로·served-model-name | 기존 API 반환 이름/경로와 일치. 실제 가중치 버전 인증은 아님 |
| reasoning-parser qwen3 | 공식 Qwen3.8 vLLM recipe에도 쓰임. 모델 버전 번호3.8과 parser이름qwen3이 다르다는 이유로 오류 아님 |
| enable_thinking=False | 공식3.8 non-thinking 요청 예시와 일치. 기존 A/B/C81응답 reasoning비어있음 |
| max-model-len32768 | 기존 A/B/C 입력최대1594, 전체81응답finish_reason=stop. 해당 글자 누락을 길이초과로 볼 근거 없음 |
| host127.0.0.1:18501 | 내부서버와 외부gateway주소는 다를수있음. 연결오류의 근거로보지않음 |
| max-num-seqs128·메모리0.8·TP1 | 실행명령만으로 글자누락원인을알수없음. 임의변경안함 |
| 별도 chat-template | 제공명령에는없음. 모델폴더의실제기본템플릿과vLLM버전은미확인 |
| 요청temperature0 | 현재 코드가명시. 공식3.8 non-thinking권장은0.7 등. 추천과다름이오류는아니므로단독비교 |

공식 근거(2026-11-04 열람):
- https://huggingface.co/Qwen/Qwen3.8-27B : non-thinking, sampling 권장. Qwen3 일반문서를3.8에무조건적용하지않음.
- https://recipes.vllm.ai/Qwen/Qwen3.8-27B : qwen3 parser예시.
- https://docs.vllm.ai/en/stable/features/reasoning_outputs/ : parser와thinking 제어 역할.

다음 진단은 TEMPERATURE_PLAN.md. 서버재시작/KG수정없음. 공식권장묶음전체가아니라temperature한값만비교함. 운영기본값을바꿨다는뜻아님.

실제 서버정보가 더 필요하면 inspect_qwen_server.py를 서버의 동일Python환경에서 실행한다. 모델을 로드하거나 파일을 바꾸지 않고 버전·선택된설정·파일해시만 출력한다. 비밀번호/키/환경변수는 읽지 않는다. 출력값만으로 가중치전체동일성까지 인증하지않는다.
