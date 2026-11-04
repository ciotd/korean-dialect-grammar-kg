"""Bounded independent review and one cross-review in existing Orca sessions."""
import datetime, importlib.util, json, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
spec=importlib.util.spec_from_file_location('exchange',ROOT/'experiments/analyses/full_review_20261029/review_exchange.py')
x=importlib.util.module_from_spec(spec);spec.loader.exec_module(x)
COMMON='''사용자가 요청한 새 단계: 원문 의미를 이해한 재사용 문법 KG를 먼저 만들고, 이후 문장 분석→조건에 맞는 그래프 조회→Qwen 전달을 연결한다. 기존17실행함수나 기존50개 정답에 범위를 고정하지 않는다. 721개를 읽었다/검증했다고 과장하지 않는다. 이번 독립 검토는 실제 자료를 읽고 구조와 정제 단위를 정하는 작업이다.
작업루트 G:/Work/00_projects/active/hyperscale_AI/02_research/KG. 원본/실행 코드/KG 수정, Qwen 호출, 새 에이전트 생성 금지. 새 제안은 채팅 응답으로 총괄에게 전달한다. 다른 검토자 의견은 독립 검토 때 읽지 않는다. 쉬운 한국어 표: 문제 위치→실제 근거(파일/ID/페이지/짧은 인용)→수정안. 직접확인/해석/설계제안/미확인 구별.
자료: knowledge/authored/kg_v3_evidence_20261019_r2/{graph/nodes.jsonl,graph/edges.jsonl,inputs/design.json,inputs/curated_claims.json,provenance/sources.json,provenance/extraction_manifest.json,code/build_evidence_kg.py}; knowledge/authored/kg_cards_20261030_v3/cards.json; src/kg_runtime/{graph.py,cards.py,compatibility.py}.
PDF 원래 Downloads/1 폴더 없어 현재 재요청 중. 원문 전체의 과거 추출 본문은 C:/Users/ciot28/Documents/Codex/2026-10-13/ciotd-odor-complaint-dialect-rag-kg/work/source_audit/D01.json ~ D07.json (각 page/text 배열)에 존재한다. 이를 읽되 현재 PDF 원본/표 이미지 대조와 구별한다. 총괄은 추출 해시를 기존 manifest와 대조한다.
주요 기존 항목 GS_ENDRULE_Q_WH_V, GS_END_DECL_YE_08, GS_END_DECL_HRA_09, G_Q_WH, G_TAM_PAST. 이들은 예시일 뿐 범위 전체가 아니다. 12모듈·공통척추 보존을 우선하되 잘못된 것까지 보존하지 않는다.
이번 회차 최종 산출: (1) 기존 지식의 문제와 정제 기준 (2) 재사용 가능한 지식 한 단위의 실제 완성 예 (3) 소규모로 전체 경로를 증명할 첫 문법 범위 및 제외범위 (4) 전체721을 이후 정제할 순서/완료판정 (5) 쉬운 신규 개발문장과 기존50회귀자료의 역할 및 논문 KG효과를 검증할 비교설계. 무조건 합의하지 말고 반례와 한계를 적는다. 자료를 실제 확인하며 10분 내외의 한정된 검토를 수행하고 미완료 범위를 명시한다.
'''
ROLE={
'claude':'''문법·지식 검토자 Opus5.5. 문헌 문맥을 읽어 형태/의미/사용조건/결합조건/보존대상/적용결과를 분리하라. 우선 D02 PDF144~146의 나/노/가/고를 주변페이지까지, D04 의문법 관련 부분을 직접 대조하라. 가능하면 공통 체계의 동일 개념을 다른 모듈(높임/시제/계사)과 어떻게 공유할지 검토하라. 단순 의문사 문자열로 판정하지 않으며, 부정계사 아니다·과거계사·추측형 처리의 미확정 범위를 명시하라. 원문이 네 가지를 그대로 허용하는지, 어간뒤에 붙이는지 선어말어미뒤인지, 뜻에 따라 조건이 달라지는지 확인하라. 외부 문헌/사전 검색 도구 사용을 사용자 승인했다. 필요한 쟁점1~2개를 공개 검색·열람하고 URL/실제지원내용/불확실성을 남겨라. 검색 실패 시 실패 사실을 적고 기억으로 인증하지 말라. 정제 예는 최대6개이며 모두 동일 schema 초안에 맞출 필요없다. 모든7종 정독 완료라고 하지 말라.''',
'codex':'''구조·조회 검토자 GPT-6-Astra High. 실제721 SourceAtom/관계/코드를 확인해 속성에만 있는 조건과 실제 관계를 구별하라. 큰 모듈 전체후보→48장순위가 아니라 문장내 절/서술어별 feature binding→조건집합 대조→실현형과 근거로 이어지는 최소 재사용 구조를 제안하라. 문법규칙마다 Python함수 만드는 방식이 아닌 일반 조건 평가기/그래프관계 표현의 장단점, AND/OR/unknown/동일절 범위/상충규칙을 검토. 꼭 모든특징을노드화할필요는 없다. 기존개념ID와 실제연결을 보존하는 mapping, 조회누락/무관규칙제외/새동사일반화 테스트를 제안하라. 직접 소스본문 일부도 읽어 구현이 의미를 왜곡하지않는지 확인하라. 총괄이 작성할 신규 소규모 버전은 전체KG 완성주장이 아닌 검증단계이며 전수721확장 작업대장 필요. 실제그래프사용이 평면규칙조회보다 유익한지 검증가능한 비교조건도 제시하라.'''}
def send(who,phase):
 d=HERE/'private/dispatch'/phase/who;d.mkdir(parents=True,exist_ok=False)
 marker=f'END_SEMANTIC_{phase.upper()}_{who.upper()}_20261102'
 if phase=='independent': prompt=COMMON+'\n'+ROLE[who]
 else:
  other='claude' if who=='codex' else 'codex'
  prompt=f'''같은 KG 재구축의 교차검토 1회입니다. 다음 파일의 상대 의견과 총괄 구현안을 실제 확인하세요. 상대 검토: {HERE/'private/dispatch/independent'/other/'response.md'}. 총괄안: {HERE/'README.md'}. 실제신규구조: {HERE/'private/foundation.json'}. 코드: {HERE/'semantic_graph.py'}. 독립검토의 결론을 자동승계하지 마세요. 가장 중요한 문제 최대5개를 위치→근거→수정안으로, 새구조가 문헌의 의미/절범위/결합조건을 보존하고 실제 조건검색을 하는지 검토하세요. 코드/KG 수정이나 Qwen실행은 금지. 미확인범위 명시. 전체721완성으로 인증하지 마세요.'''
 prompt+='\n마지막 줄에 '+marker
 (d/'prompt.txt').write_text(prompt,encoding='utf8')
 x.dump(d/'start.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'offset':x.LOGS[who].stat().st_size,'marker':marker})
 x.dump(d/'receipt.json',x.cli(['terminal','send','--terminal',x.HANDLES[who],'--text',prompt,'--enter','--wait-submit','5']))
 print(who,phase,'sent')
def collect(phase):
 for who in ('codex','claude'):
  d=HERE/'private/dispatch'/phase/who
  if not (d/'start.json').exists():continue
  start=json.loads((d/'start.json').read_text(encoding='utf8'));es=[];done=False
  for e in x.entries(who):
   if e.get('timestamp','')<start['at']:continue
   es.append(e)
   if e['role']=='assistant' and start['marker'] in e['text']:done=True;break
  x.dump(d/'messages.json',es)
  answers=[e for e in es if e['role']=='assistant' and e['text'].strip()]
  if answers:(d/'response.md').write_text('\n\n'.join(e['text'] for e in answers),encoding='utf8')
  print(json.dumps({'who':who,'phase':phase,'complete':done,'last':answers[-1]['text'][-350:] if answers else None},ensure_ascii=False))
if __name__=='__main__':
 if sys.argv[1]=='send':send(sys.argv[2],sys.argv[3])
 else:collect(sys.argv[2])
