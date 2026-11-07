"""Send bounded review requests to the user-designated existing Orca reviewers."""
import sys,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
ORCA=r'C:\Users\ciot28\AppData\Local\Programs\orca\resources\bin\orca.exe'
HANDLES={'claude':'term_56cdd7ed-5833-4d65-8dbf-691852380b96','codex':'term_57d39dd0-15d4-436b-9182-853b45cfc9a9'}
for who in ('claude','codex'):
    prompt=f'''기존 KG Reviewer 역할로 새 작업을 독립 검토해 주세요. 사용자가 Kiwi를 제외하고 Qwen 분석·생성 모두 멀티 에이전트로 실제 구현하도록 명시 승인했습니다. 이번은 그 설계 검토입니다. 인증정보/test.py/원본PDF/사용자정답파일은 읽거나 전달하지 마세요. 코드/KG 변경과 Qwen 호출 금지. 지정된 자기 검토파일만 작성하세요.
먼저 experiments/analyses/qwen_multi_20261107/PLAN.md, 기존 experiments/analyses/research_redesign_20261106/DECISIONS.md, src/kg_pipeline/integrated.py를 읽으세요. 최신 separated KG는 출처/검토기록 밖으로 분리되어 있고 56규칙57분기. 현재 조회기와 연결 계약 재사용. 제안: 구조분석→의미분석→그래프조건조회→변환계획→전체문장작성→독립보존검토, 필요시 작성1회수정. Qwen 5역할/5~6호출. 구조에서 형태/품사/절은LLM담당, 코드가 원문 어절ID/범위만검증. 단어마다worker없음. 정답문장주입없음. KG지식부족시모델지식사용가능하나근거구별.
{'언어·지식·정보전달 관점: 구조/의미의 경계, 어디의 장소/의문 혼합 방지, 하지마의 본/보조 연결, 시제·어간·높임 보존, 5역할이 정말필요한지와 최소프롬프트를 비판 검토하세요.' if who=='claude' else '시스템·공정비교 관점: 실제조건키/ID/관계/스키마 인계, 실패와 토큰분모, 5역할/수정상한의 근거와 단일/동일호출 대조 필요를 비판 검토하세요.'}
문제위치→실제근거→수정안 형식, 쉬운 한국어로. 이전계획과달라진점, 필수수정과향후실험구별. 다른검토자파일은초안전읽지마세요. 결과를 {HERE/'private'/f'{who}_design_review.md'} 에 작성하고 완료경로알려주세요. 1000~1800단어이내.'''
    p=HERE/'private'/f'{who}_design_prompt.txt';p.parent.mkdir(exist_ok=True,parents=True)
    if p.exists():raise RuntimeError('Do not resend completed dispatch')
    p.write_text(prompt,encoding='utf8')
    proc=subprocess.run([ORCA,'terminal','send','--terminal',HANDLES[who],'--text',prompt,'--enter','--wait-submit','5'],capture_output=True,text=True,encoding='utf8',timeout=45)
    (p.parent/f'{who}_dispatch.json').write_text(json.dumps({'code':proc.returncode,'stdout':proc.stdout,'stderr':proc.stderr},ensure_ascii=False,indent=2),encoding='utf8')
    print(who,proc.returncode,flush=True)
