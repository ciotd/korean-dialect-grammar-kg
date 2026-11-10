"""Use the two existing Orca reviewers for source-map and coverage review."""
import datetime,importlib.util,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
s=importlib.util.spec_from_file_location('exchange',ROOT/'experiments/analyses/full_review_20261029/review_exchange.py');x=importlib.util.module_from_spec(s);s.loader.exec_module(x)
COMMON='''[전체 문헌 작업지도 20261102]
사용자가 승인한 작업: 현재 방법의 타당성을 재검토하고 합리적이면 문헌7종과 기존KG의 전체 작업지도를 작성한다. 이번은 KG 수정/생성 실험이 아니라 범위·대응·누락후보·정제순서의 지도다. 전 문헌 의미검증 완료와 분류 완료를 혼동하지 않는다. 한국어로 근거있게 비판한다. 코드·KG·과거자료 수정, Qwen호출, 새에이전트 생성 금지. 당신의 새 검토 산출물만 아래 자신의 폴더에 작성할 수 있다. 외부검색은 지도작성에 필수인 경우만, 자료확장을 목표로 하지 않는다.
ROOT=G:/Work/00_projects/active/hyperscale_AI/02_research/KG
원본PDF: C:/Users/ciot28/Downloads/1 (7개 모두 접근·해시 일치 확인됨)
과거 전체추출: C:/Users/ciot28/Documents/Codex/2026-10-13/ciotd-odor-complaint-dialect-rag-kg/work/source_audit/D01.json~D07.json (page/text 배열, 474쪽; 기존추출manifest와전체해시일치)
기존KG: knowledge/authored/kg_v3_evidence_20261019_r2/graph/{nodes,edges}.jsonl; inputs/design.json; provenance/sources.json. SourceAtom721(설계규칙81/실현목록433/관찰183/분류24), 나머지공통개념·구성·기술역할190개도 별도 추적해야 한다. 721을 실행규칙721개로 보지 않는다.
첫구성 결과: experiments/analyses/semantic_kg_rebuild_20261102/README.md, knowledge/authored/semantic_foundation_20261102_r2/manifest.json. 첫구성의 성공은 전체지식 검증이 아니다.
계획: ①기준고정 ②7종의 장·절·표 단위 내용지도 ③기존721와양방향대조 ④뜻·결합조건에 따른작업묶음과 분석→조회→생성의입출력 ⑤독립후교차검토 ⑥선행관계·우선순위·종료조건. 지도완성 기준과 의미정제완료를 구분. 제목/형태/페이지일치로의미대응인증금지. 전체페이지배정만으로읽었다주장금지. 동일위키계열독립근거중복계수금지. 기존원문/그래프그대로보존.
'''
ROLE={
'claude':'''문법·문헌검토자로서 먼저 계획이 생성연구에서벗어나는지 비판하라. 이어7종의 모든장절 구조를 확인하여 source-first 내용지도를 작성하라. 읽기범위를명확히 남기고, 원문 의미정제 전체를완료했다고하지말라. 단순정규식/키워드가아닌 장절의실제내용을읽어 관련성 판단. 문헌마다 [장절명,PDF시작끝,내용설명1~2문장,문법기능,필요한입력분석,검색/생성에서쓰일정보,검토쟁점,실제로읽은범위]를 제시. 직접본문읽은페이지와 목차/표제로분류한페이지를구별하라. D02는본론의어미체계/유형/제약, D01거로의다기능, D04/D05중복, D06음운의텍스트생성관련성, D07전통/변화범위를특히보라. 다른리뷰어의견읽지말라. source_sections.json과 source_review.md를 자기폴더(private/reviewer_work/claude)에 작성할수있다. 이것은초안분석이며원본수정아님. 충분한범위를읽되context부족으로못읽은곳을명시하고빈칸을완료로꾸미지말라. 최소한모든장절을대상으로위치지도는확보. 외부자료는현재7종을대체하지않는다.''',
'codex':'''구조·조회검토자로서 계획을검토하고 실제전체721항목과 나머지190설계항목을어떻게빠짐없이대응할지설계하라. 원본graph/입력spec에서모듈,역할,문헌ref형식과분포,형태목록과실행규칙의잘못된동일시,형태/제목일치대응의위험,현재설계누락후보를확인하라. code검사로전수참조·소속을확인하되의미검증으로칭하지말라. 다음정제를실행할작업카드(근거읽을범위→분석특징→조건/관계→실현/보존→양성/음성/unknown검사)의실제2~3개예를기존ID로제시. 지도종료기준/중단기준,총괄이작성할자동매핑초안을검증할방법,우선순위제안. 자기폴더(private/reviewer_work/codex)에 structural_review.md와원하는검증JSON을저장가능. 다른검토자의견읽지말라.'''}
def send(who,phase):
 d=HERE/'private/dispatch'/phase/who;d.mkdir(parents=True,exist_ok=False)
 out=HERE/'private/reviewer_work'/who;out.mkdir(parents=True,exist_ok=True)
 marker=f'END_WORKMAP_{phase.upper()}_{who.upper()}_20261102'
 if phase=='independent':prompt=COMMON+ROLE[who]+f'\n당신의작성가능폴더:{out}'
 else:
  other='codex' if who=='claude' else 'claude'
  prompt=f'''전체 작업지도 교차검토1회. 총괄산출물 {HERE/'private/atlas.json'}, {HERE/'README.md'}, {HERE/'build_atlas.py'}와 상대결과 {HERE/'private/dispatch/independent'/other/'response.md'}를 확인. 자동배정과의미검증혼동,모든항목연결누락,다음정제가능성,문헌범위누락,과잉분류를검토. 핵심문제최대5개:위치→근거→수정안. 코드/KG/기존자료수정금지. 읽은범위와못확인한범위명시. 전체언어학검증인증금지.''' 
 prompt+='\n작업루트 '+str(ROOT)+'\n마지막줄 '+marker
 (d/'prompt.txt').write_text(prompt,encoding='utf8');x.dump(d/'start.json',{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'offset':x.LOGS[who].stat().st_size,'marker':marker})
 x.dump(d/'receipt.json',x.cli(['terminal','send','--terminal',x.HANDLES[who],'--text',prompt,'--enter','--wait-submit','5']));print(who,phase,'sent')
def collect(phase):
 for who in ('codex','claude'):
  d=HERE/'private/dispatch'/phase/who
  if not (d/'start.json').exists():continue
  start=json.loads((d/'start.json').read_text(encoding='utf8'));es=[];done=False
  for e in x.entries(who):
   if e.get('timestamp','')<start['at']:continue
   es.append(e)
   if e['role']=='assistant' and start['marker'] in e['text']:done=True;break
  x.dump(d/'messages.json',es);a=[e for e in es if e['role']=='assistant' and e['text'].strip()]
  if a:(d/'response.md').write_text('\n\n'.join(e['text'] for e in a),encoding='utf8')
  print(json.dumps({'who':who,'complete':done,'last':a[-1]['text'][-400:] if a else None},ensure_ascii=False))
if __name__=='__main__':
 if sys.argv[1]=='send':send(sys.argv[2],sys.argv[3])
 else:collect(sys.argv[2])
