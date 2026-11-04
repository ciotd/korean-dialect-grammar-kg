"""Reuse existing Orca sessions; bounded, logged independent and cross review."""
import datetime,importlib.util,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
s=importlib.util.spec_from_file_location('exchange',ROOT/'experiments/analyses/full_review_20261029/review_exchange.py');x=importlib.util.module_from_spec(s);s.loader.exec_module(x)
COMMON='''[해라체 질문 지식 정제 20261102]
승인 범위: 기존 작업지도의 첫 묶음. 원문 재해석→별도 KG 버전→수작업 분석값으로 조건 조회 검증. Qwen 호출/운영KG 수정/기존 파일 수정/새 에이전트 생성 금지. 독립 검토에서는 상대 응답을 읽지 말 것. 한국어로 문제 위치→실제 근거→수정안을 제출. 모델 동의를 사실 인증으로 쓰지 말 것.
작업루트 G:/Work/00_projects/active/hyperscale_AI/02_research/KG
계약 experiments/analyses/source_workmap_20261102/next_work.json
기존 작은 구성 knowledge/authored/semantic_foundation_20261102_r2/private/foundation.json 및 graph.json. 코드 experiments/analyses/semantic_kg_rebuild_20261102/semantic_graph.py, build_foundation.py, test_semantic_graph.py. 이 파일들은 읽기 전용.
원본PDF C:/Users/ciot28/Downloads/1
전체 추출 C:/Users/ciot28/Documents/Codex/2026-10-13/ciotd-odor-complaint-dialect-rag-kg/work/source_audit/D02.json 등(page/text배열).
읽을 범위: D02 PDF139–147, D04 PDF8–15, D03 PDF3·27–28, D05 PDF21–25. 본문/표/주석을 포함. 필요한 인접 쪽은 추가 확인하되 범위 기록.
지원 시험: 해라체 직접 정보 질문, polar/wh, 용언/긍정계사, 선어말없음/-었-, 주체높임없음. 다른 표현은 비문이 아니라 후속범위. 지역·세대 입력 일률 강제 금지. 동일 문헌의 지역별 상충체계를 조용히 합치지 말 것.
'''
ROLE={
'claude':'''문법·지식 검토. 위 범위의 본문 전체를 읽고 표/각주 포함 읽은범위와 PDF 화면 확인 여부를 구분. 기존6용법과 근거가 타당한지, 계사+노/현재계사받침/과거계사와 -시-·-더-·-겠-/의문사 문자열 vs기능/확인제/지역별라로 등과의 경계를 점검. 같은 -나/-노 형태의 다른 뜻을 합치지 말 것. 각 용법: 쉬운 의미 설명, 적용대상, 필수조건, 실현형, 보존사항, 예문과반례, 미확정, 근거PDF쪽·정확한짧은발췌. 새 지식을 기억만으로 확정하지 말 것. 필요한 외부 자료 검색은 이미 허용되었으나 이번 원문 근거와 외부 보완을 구분. 본문에서 직접확인된 것과 모델해석 구분. source_review.md 및 가능한 claims.json을 자기폴더에만 작성. 번역50정답 암기/새Qwen생성 금지.''',
'codex':'''구조·조회 검토. 원문의 의미 정제를 담을 기존semantic_graph.py를 직접 읽고 기존24개개발예문/25검사 확인. 조건이 실제graph경로로 평가되는지, 서로다른절 섞임/feature값·schema·binding 검증/unknown/지원범위vs문법조건/packet과조회일치/전체조건전수스캔 개선필요를 비판. 문장 분석값→FeatureValue/Condition→Usage→Realization/Evidence의실제경로와 전달값을 검증할 작고 의미있는 회귀검사 제안. 원본수정 금지. structural_review.md에 문제위치→근거→수정안. 추가 기능을 많이만들기보다 이번 범위의 끝까지 연결을 우선. 자체시험 필요하면 자기폴더에서 임시파일만 작성.'''}
def send(who,phase):
 d=HERE/'private/dispatch'/phase/who;d.mkdir(parents=True,exist_ok=False)
 own=HERE/'private/reviewer_work'/who;own.mkdir(parents=True,exist_ok=True)
 marker=f'END_QUESTION_{phase.upper()}_{who.upper()}_20261102'
 if phase=='independent':prompt=COMMON+ROLE[who]
 else:
  other='claude' if who=='codex' else 'codex'
  prompt=COMMON+f'''교차 검토1회. 총괄 새 산출물 {HERE}/README.md, private/spec.json, private/graph.json, query.py, private/validation.json, private/change_log.json과 상대결과 {HERE}/private/dispatch/independent/{other}/response.md를 확인. 문헌 의미·조건근거와 실제구현/검사/전달의 불일치를 찾아 핵심5개이내 제출. 실제로읽은파일/쪽/시험을 명시. 파일수정금지. 최종줄 완료표식까지 응답.'''
 prompt+=f'\n작성 가능한 폴더: {own}\n마지막줄 {marker}'
 (d/'prompt.txt').write_text(prompt,encoding='utf8');x.dump(d/'start.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'offset':x.LOGS[who].stat().st_size,'marker':marker})
 x.dump(d/'receipt.json',x.cli(['terminal','send','--terminal',x.HANDLES[who],'--text',prompt,'--enter','--wait-submit','5']));print(who,phase,'sent')
def collect(phase):
 for who in ('codex','claude'):
  d=HERE/'private/dispatch'/phase/who
  if not (d/'start.json').exists():continue
  start=json.loads((d/'start.json').read_text('utf8'));entries=[];done=False
  for e in x.entries(who):
   if e.get('timestamp','')<start['at']:continue
   entries.append(e)
   if e['role']=='assistant' and start['marker'] in e['text']:done=True;break
  x.dump(d/'messages.json',entries)
  a=[e for e in entries if e['role']=='assistant' and e['text'].strip()]
  if a:(d/'response.md').write_text('\n\n'.join(e['text'] for e in a),encoding='utf8')
  print(json.dumps({'who':who,'complete':done,'last':a[-1]['text'][-350:] if a else None},ensure_ascii=False))
if __name__=='__main__':
 if sys.argv[1]=='send':send(sys.argv[2],sys.argv[3])
 else:collect(sys.argv[2])
