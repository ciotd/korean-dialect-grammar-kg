from pathlib import Path
import importlib.util,sys
R=Path.cwd();H=R/'experiments/analyses/generation_scope_20261104'
s=importlib.util.spec_from_file_location('exchange',R/'experiments/analyses/full_review_20261029/review_exchange.py');x=importlib.util.module_from_spec(s);s.loader.exec_module(x)
stage=sys.argv[1]
for who in ('codex','claude'):
 d=H/'private/reviewers'/stage/who;d.mkdir(parents=True,exist_ok=True)
 role='동일 지식·요청 차이·실험 통제·중단 기준·집계 재현성' if who=='codex' else '생성 정책의 충돌·문법 및 의미 보존·반말 평서의 제안과 근거 구별'
 scope=f'{H}/PLAN.md, experiment.py, test_experiment.py, plain_statement_notes.md'
 if stage=='results':scope+=f', {H}/report.py, reviewer_resolution.md, private/review_outputs.json, private/latest_regression.json 및 latest_development.json이 연결하는 이번 요청·응답·집계, private/comparison.json, private/v1_comparison.json. 50회귀+12개발 전체 출력을 먼저 review_outputs.json에서 대조하고 의심 부분의 실제 요청·응답을 확인하세요. 회귀v1은 모호한 지시가 남은 초안, v2는 범위를 명확하게 했고 새 개발은 v2만 실행했습니다. 자연스러움은 인간평가 아님을 명시하고, 명백한 의미/시제/높임/문법 변화와 지역 적합성 미확인을 구분하세요. 전체 입력 ID별 짧은 판정도 남기고, 오류 수를 독립 성능평가로 주장하지 마세요. 코덱스는 통제·집계 중심, 클로드는 표현·뜻 중심입니다'
 prompt=f'''사용자가 ② 비교 조건 확정과 ③ 생성 비교를 함께 실행하도록 승인했고 기존 두 검토자 역할을 유지합니다. 이번 검토는 {stage}입니다. {scope}만 읽으세요. 역할: {role}. 문제 위치 → 실제 근거 → 수정안을 한국어로 적고 확정 관찰과 가설을 구분하세요. 새 Qwen 호출, 운영 코드/KG 변경, 다른 검토자 의견 읽기 금지. 인증정보/test.py/환경변수/원본 PDF 읽기 금지. 출력은 {d/'review.md'} 한 파일에만 작성하세요. 기존50은 회귀셋, 신규12도 개발셋이며 변경률을 방언 품질로 간주하지 마세요. 중대한 실행 전 차단 사유가 있으면 맨 위에 명시하세요. 이전 문구 비교를 반복하지 않고 빈 지식 강제복사/지정 위치 밖 생성 허용을 비교합니다. 단계④ 전체 분석 재실행이나 규칙 추가는 이번 범위가 아닙니다. END_SCOPE_{stage.upper()}_{who.upper()}_20261104 로 끝내세요.'''
 (d/'prompt.txt').write_text(prompt,'utf8');x.dump(d/'receipt.json',x.cli(['terminal','send','--terminal',x.HANDLES[who],'--text',prompt,'--enter','--wait-submit','5']));print(who,'sent',stage,flush=True)
