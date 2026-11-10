import json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
ORCA=r'C:\Users\ciot28\AppData\Local\Programs\orca\resources\bin\orca.exe'
HANDLES={'claude':'term_56cdd7ed-5833-4d65-8dbf-691852380b96','codex':'term_57d39dd0-15d4-436b-9182-853b45cfc9a9'}
for who,handle in HANDLES.items():
    other='codex' if who=='claude' else 'claude'
    prompt=f'''설계 독립 검토 감사합니다. 서로의 {other}_design_review.md 및 experiments/analyses/qwen_multi_20261107/DECISIONS.md를 읽고, 실제 src/kg_pipeline/multi_agent.py와 tools/run_qwen_multi.py를 검토해 주세요. 기본4역할/최대5호출(계획+작성통합), --separate-plan시5역할/최대6호출. 구조이의는자동덮어쓰기아니며관련후보보류. source_form/lemma는열린값, nominal의의문성격분리, 본보조root_tag검사. 새개발6문장최대30호출연결진단예정. 효과우월성주장아님.
문제위치→실제근거→수정안. 실행전차단할오류/후속개선구분. 코드/KG수정·Qwen호출·인증/test.py/원본PDF/참조정답읽기금지. 결과를 {HERE/'private'/f'{who}_implementation_review.md'} 에만작성. 쉬운한국어500~1200단어, 본인이반대한채택항목도숨기지말것. 두검토자의동의를사실인증으로쓰지않음.'''
    p=HERE/'private'/f'{who}_implementation_prompt.txt'
    if p.exists():raise RuntimeError('Already dispatched')
    p.write_text(prompt,encoding='utf8')
    result=subprocess.run([ORCA,'terminal','send','--terminal',handle,'--text',prompt,'--enter','--wait-submit','5'],capture_output=True,text=True,encoding='utf8',timeout=45)
    (p.parent/f'{who}_implementation_receipt.json').write_text(json.dumps({'code':result.returncode,'stdout':result.stdout,'stderr':result.stderr},ensure_ascii=False),encoding='utf8')
    print(who,result.returncode,flush=True)
