"""Coordinate only the two existing user-designated Orca reviewers."""
import json,sys,importlib.util,datetime
from pathlib import Path
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[2]; P=HERE/'private'
s=importlib.util.spec_from_file_location('exchange',ROOT/'experiments/analyses/full_review_20261029/review_exchange.py')
x=importlib.util.module_from_spec(s);s.loader.exec_module(x)
COMMON='''[PRE_EXPERIMENT_20261102 독립 검토]
사용자 승인 범위는 실험 전 기록 대조와 짧은 실험안 작성입니다. Qwen 호출, KG/카드/코드 변경, 새로운 에이전트 생성은 금지합니다. 다른 검토자의 결론은 읽지 마세요. 결과는 쉬운 한국어로 문제 위치→실제 근거→수정안 형식이며 확정 관찰/원인 가설을 구분합니다. 자연스럽지 않다는 평만 하지 마세요.
사용자 승인 참조는 현 연구의 비교 기준이며 문헌 사실과 별도입니다. 50개 문장 통째 암기나 정답 누출은 금지합니다. 원문 변경 수를 품질 점수로 쓰지 않습니다. 이번에 총괄이 만든 index/cases는 기존 파일의 연결본이며 prior_review_*는 예전 총괄 판단이지 사실 인증이 아닙니다. 모든 50 ID를 검토하되 원인 미확인은 미확인으로 표시하세요. JSON 전체를 무작정 출력하지 말고 표와 짧은 근거를 쓰세요.
작업 루트: G:/Work/00_projects/active/hyperscale_AI/02_research/KG
공통 자료:
- experiments/analyses/pre_experiment_review_20261102/private/index.json (전체50 ID/승인 참조/6회 결과)
- 같은 private/cases/<ID>.json (선택 계획/원시 제안/검사/보정/최종 출력)
- experiments/analyses/selection_probe_20261102/private/20261102T005306227866Z/prepared.json (분석/카드 전체/계획/실제 전달 데이터, 8MB이므로 필요한 ID만 코드로 추출)
- experiments/analyses/selection_probe_20261102/README.md 및 runner.py (최근 실제 비교)
- experiments/analyses/effect_ledger_20261031/README.md (과거 수정과 확인 범위)
- experiments/analyses/controlled_delivery_20261031/README.md (준비된 설명/조합 비교, 실제 실행 여부 확인)
- knowledge/authored/kg_cards_20261030_v3/cards.json (전체 카드)
실제 요청·응답: experiments/runs/20261102T005306227866Z_selection_probe_{saved|reviewed}_r{1|2|3}/private/records/<ID>/generation_call/
최종 산출: 핵심 문제 최대6개(근거 위치 포함), 전체50 ID별 한 줄 진단표, 가장 먼저 할 원인 확인 실험과 고정/변경/반증 기준, 이전 실험과 차이. 사실이 부족하면 필요한 증거를 적으세요. 코드·카드는 수정하지 말고 채팅으로 답하세요. 파일 읽기 실패 시 확인하지 못했다고 보고하고 자료를 요청하세요.
'''
ROLE={
'codex':'''당신은 GPT-6-Astra High 코드·실험 설계 검토자입니다. 처음에 README와 index를 실제 읽을 수 있는지 확인하세요. 실패하면 다른경로 추측/설치/환경수정 하지 말고 ACCESS_BLOCKED와 오류만 보고하세요. 읽을 수 있다면 전체50/300기록을 검토하세요. 선택 이외 변수, 편집/계획 ID, 스키마·길이·파싱, 보정이 가리는 오류, 기존해시와 코드 재현을 점검하세요. 반복실험을 또 제안할 때 이미 수행한 것과 무엇이 다른지 구체적으로 적으세요. 마지막에 END_PRE_EXPERIMENT_CODEX_20261102.''',
'claude':'''당신은 Opus 5.5 문법·지식 검토자입니다. 전체50개를 읽고 승인 참조에 필요한 재사용 문법과 실제 전달 카드/적용 위치/원시 출력 차이를 대조하세요. 후보 미확보18건은 전체 카드에 존재하지만 전달 안 됨 / 카드 내용 불충분 / 분석 또는 적용 범위 문제 / 미확인으로 구분하고 실제 ID·조건을 적으세요. 단순 형태 문자열 존재를 적용 가능의 근거로 삼지 마세요. 핵심2~3가지 문법 쟁점에 한해 외부 사전/문헌/실제용례 검색을 수행하여 직접 근거와 추론을 분리하세요. PDF 기본 Read 실패 시 기존 pypdf 경로를 사용하세요. 검색 실패를 지식 부재로 단정하지 마세요. 모델의 기억/문헌/사용자 승인 참조를 구분하세요. 어떤 재사용 지식이 없고 어떤 정보가 있는데 잘못 적용됐는지 우선순위를 권고하세요. 최신 운영 정책은 docs/workflows/REVIEWER_ROLES_20261102.md. 마지막에 END_PRE_EXPERIMENT_CLAUDE_20261102.'''}
who=sys.argv[2] if len(sys.argv)>2 else None
if sys.argv[1]=='send':
 d=P/'dispatch'/who;d.mkdir(parents=True,exist_ok=False)
 prompt=COMMON+'\n'+ROLE[who]
 (d/'prompt.txt').write_text(prompt,encoding='utf8')
 x.dump(d/'start.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'offset':x.LOGS[who].stat().st_size})
 receipt=x.cli(['terminal','send','--terminal',x.HANDLES[who],'--text',prompt,'--enter','--wait-submit','5'])
 x.dump(d/'receipt.json',receipt);print(who,'sent')
elif sys.argv[1]=='collect':
 for who in ('codex','claude'):
  d=P/'dispatch'/who
  if not d.exists():continue
  t=x.read if hasattr(x,'read') else None
  since=json.loads((d/'start.json').read_text())['at']
  es=[e for e in x.entries(who) if e.get('timestamp','')>=since]
  x.dump(d/'messages.json',es)
  answers=[e for e in es if e['role']=='assistant' and e['text'].strip()]
  if answers:
   (d/'response.md').write_text('\n\n'.join(e['text'] for e in answers),encoding='utf8')
   print(who,answers[-1]['text'][-650:])
  else: print(who,'awaiting reply')
