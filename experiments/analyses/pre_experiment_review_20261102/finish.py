"""Validate audit artifacts and register the proposed next scope, without executing it."""
import json,sys,hashlib,re
from pathlib import Path
from html.parser import HTMLParser
H=Path(__file__).resolve().parent;R=H.parents[2];P=H/'private'
sys.path.insert(0,str(R/'src'))
from research_management.work import WorkStore
read=lambda p:json.loads(p.read_text(encoding='utf8'))
rows=read(P/'index.json');assert len(rows)==len({r['id'] for r in rows})==50
reviewers={}
for who in ('codex','claude'):
 t=(P/'dispatch'/who/'response.md').read_text(encoding='utf8')
 assert f'END_PRE_EXPERIMENT_{who.upper()}_20261102' in t
 present=[r['id'] for r in rows if re.search(r'\|\s*'+re.escape(r['id'])+r'\s*\|',t)]
 assert len(present)==50,(who,len(present))
 reviewers[who]={'complete_marker':True,'table_ids':len(present)}
class Inspect(HTMLParser):
 def __init__(self):super().__init__();self.ids=set();self.cases=0
 def handle_starttag(self,tag,attrs):
  d=dict(attrs)
  if d.get('id'):assert d['id'] not in self.ids;self.ids.add(d['id'])
  if tag=='article' and d.get('class')=='case':self.cases+=1
v=Inspect();v.feed((P/'review.html').read_text(encoding='utf8'));assert v.cases==50
assert all(hashlib.sha256((R/k).read_bytes()).hexdigest()==h for k,h in read(P/'source_hashes.json').items())
counts=read(P/'verified_findings.json')['counts']
assert counts['status_mismatches']==49 and counts['preblocked_edits_sent_as_apply']==18
check={'reviewers':reviewers,'unique_inputs':50,'records':sum(len(read(P/r['case_file'])['records']) for r in rows),'html_case_sections':v.cases,'original_source_hashes_unchanged':True,'new_generation_calls':0,'validation_note':'HTML structure and source consistency checked; no browser screenshot QA or linguistic accuracy certification.'}
(P/'validation.json').write_text(json.dumps(check,ensure_ascii=False,indent=2),encoding='utf8')
ws=WorkStore(R)
proposal=dict(id='review-followup-20261102',version=1,title='연결 오류 수정 후 하이소체 설명 비교',
 before='카드 누락·보류/적용 전달 모순·요약 상태 불일치가 있고 Qwen이 하이소체를 반말로 해석한 기록이 있음.',
 after='연결·기록 오류를 고치고 50건 전체 재검사. 같은 카드와 위치에서 하이소체 설명 한 문장 유무만 비교.',
 reason='이미 확인한 결함과 아직 미확인인 원인 가설을 분리해 재실험의 해석 가능성을 확보.',
 scope='선별 조건과 지시·기록 정합성 수정, 전체50 오프라인 검사, 호출 가능한 입력 N개 × A/B × 동일 요청3회(최대300호출). KG 척추 재구축·정답 학습 제외.',
 verification='전달 상태 모순·요약 상태 불일치 0건, 필수 기능 충돌 반례 검사, A/B 요청 차이 검사. 원시 보류·활용·의미 보존과 보정 후 결과·비용 별도 기록. 변화 수를 정확도로 사용하지 않음.',
 evidence='experiments/analyses/pre_experiment_review_20261102/README.md',
 reviewers='Codex GPT-6-Astra High 및 Claude Opus 5.5 독립 검토. 채택·보류 및 총괄 정정은 README 참조.',
 lead='확인된 연결 결함 수정이 우선. 첫 비교는 화계 설명 하나의 효과로 제한.',
 human_question='이 범위로 수정과 Qwen 비교를 진행할까요? 채팅에서 답해 주세요.')
with ws.connect() as db:exists=db.execute('SELECT 1 FROM proposals WHERE id=?',(proposal['id'],)).fetchone()
if not exists:ws.proposal(proposal)
with ws.connect() as db:task=db.execute('SELECT body FROM tasks WHERE id=?',('pre-experiment-review-20261102',)).fetchone()
if not task or json.loads(task['body'])['status'] not in ('completed','failed'):
 ws.task(dict(id='pre-experiment-review-20261102',title='실험 전 원인·설계 검토',actor='Codex 총괄',stage='전체50 대조·독립 검토·실험안 완료',status='completed',done=50,total=50,unit='문장',unit_key='stored_audit',message='분석 완료. 생성 호출 0회. 다음 수정·A/B 비교안은 채팅 승인 대기이며 실행하지 않았습니다.'))
print(json.dumps(check,ensure_ascii=False))
