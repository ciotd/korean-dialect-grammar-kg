"""Small offline review view generated from real records and reviewer text."""
import json,html,hashlib,re
from pathlib import Path
H=Path(__file__).resolve().parent;P=H/'private';R=H.parents[2]
esc=lambda s:html.escape(str(s if s is not None else ''))
read=lambda p:json.loads(p.read_text(encoding='utf8'))
rows=read(P/'index.json');counts=read(P/'counts.json')
latest=read(R/'experiments/analyses/selection_probe_20261102/private/latest.json')
statuses={'unchanged':'원문 유지','needs_review':'보류·확인 필요','partial':'일부만 반영','generated_requires_human_review':'변경됨·품질 미평가','generation_failed':'응답 처리 실패','review_not_eligible':'비교용 선택 미확보','preworker_blocked':'생성 전 차단','no_planned_edit':'적용 계획 없음','planned':'적용 예정','applied':'반영됨','apply':'적용 지시','skip':'건너뜀'}
def label(s):return statuses.get(s,s or '없음')
def plan_status(z,key):
 rid=next((v for v in latest['run_ids'] if v.endswith('_'+z['arm']+'_r'+str(z['repeat']))),None)
 f=R/'experiments/runs'/rid/'private/records'/key/'final_plan.json' if rid else None
 return read(f)['status'] if f and f.exists() else None
flags={'no_reviewed_selection':'비교용 선택 미확보','model_abstained':'모델이 보류','program_blocked_apply':'검사가 적용 차단','program_repaired':'코드가 표현 보정','call_failed':'호출·응답 처리 실패'}
def table(head,rs):return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+esc(x)+'</th>' for x in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+x+'</td>' for x in r)+'</tr>' for r in rs)+'</tbody></table></div>'
def inline(s):
 s=esc(s);s=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',s);s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
 return re.sub(r'\[([^\]]+)\]\((https://[^\s)]+)\)',r'<a href="\2" target="_blank" rel="noopener">\1</a>',s)
def readable_md(text):
 lines=text.splitlines();out=[];i=0
 while i<len(lines):
  s=lines[i].strip()
  if not s:i+=1;continue
  if s.startswith('|') and i+1<len(lines) and re.fullmatch(r'[|:\-\s]+',lines[i+1]):
   head=[c.strip() for c in s.strip('|').split('|')];rs=[];i+=2
   while i<len(lines) and lines[i].strip().startswith('|'):
    rs.append([inline(c.strip()) for c in lines[i].strip().strip('|').split('|')]);i+=1
   out.append(table(head,rs));continue
  if s.startswith('#'):
   n=min(4,len(s)-len(s.lstrip('#'))+1);out.append(f'<h{n}>'+inline(s.lstrip('#').strip())+f'</h{n}>')
  elif s.startswith('- '):out.append('<p>• '+inline(s[2:])+'</p>')
  else:out.append('<p>'+inline(s)+'</p>')
  i+=1
 return ''.join(out)
content='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>실험 전 확인 · 50문장</title><style>
body{font-family:system-ui,"Malgun Gothic",sans-serif;background:#f4f6f8;color:#202a38;margin:0;line-height:1.65}main{max-width:1100px;margin:auto;padding:28px}section,article{background:white;padding:22px;border-radius:12px;margin:16px 0}h1,h2,h3{line-height:1.35}small,.muted{color:#566475}table{border-collapse:collapse;width:100%;font-size:14px}td,th{border-bottom:1px solid #dde4ea;text-align:left;vertical-align:top;padding:10px;min-width:100px}th{background:#eef3f7}.scroll{overflow:auto}pre{white-space:pre-wrap;word-break:break-word;font:inherit;font-size:14px}.note{border-left:4px solid #387bc1;padding:12px;background:#eff6ff}input{padding:12px;width:90%;font:inherit;border:1px solid #a9b6c4;border-radius:8px}summary{cursor:pointer;font-weight:bold}a{color:#185c9e}.tag{display:inline-block;padding:3px 8px;background:#edf1f5;border-radius:4px;font-size:13px;margin:2px}nav{display:flex;gap:20px;flex-wrap:wrap}</style><main>
<h1>실험 전 확인: 어디가 문제이고, 무엇을 시험할까?</h1><p>2026-11-02 · 기존 50문장 × 두 선택 방식 × 세 번 = 300개 처리 기록. 실제 Qwen 호출은 219회였습니다.</p>
<nav><a href="#plan">짧은 실험안</a><a href="#review">두 검토자 의견</a><a href="#cases">50문장 확인</a></nav>
<p class="note">이번 작업에서는 새로운 Qwen 생성이나 KG·카드 수정은 하지 않았습니다. 아래 ‘미확보·보류·차단·보정’은 처리 기록이며 방언 정확도 점수가 아닙니다.</p>'''
plan=H/'README.md'
content+='''<section id="plan"><h2>먼저 이것만 읽어주세요</h2><p><b>KG가 전부 잘못됐다고 결론낼 근거는 아직 없습니다. 있는 카드를 전달하지 못하고, 전달한 뜻을 모델이 오해하고, 잘못 만든 표현을 검사에서 놓치는 문제가 함께 있습니다.</b></p>'''
content+=table(['확인한 문제','쉬운 예','다음 조치'],[
 ['카드 선별에서 누락','볼게요에 맞는 -께예 카드가 있어도 마지막 필터에서 탈락','선별 조건을 고친 뒤 전체50의 전달 변화를 확인'],
 ['프로그램 지시·기록이 엇갈림','보류해 놓고 모델에는 적용하라고 전달','적용/보류 지시와 최종 기록을 일치'],
 ['모델이 문법 기호를 오해','하이소체를 반말로 해석하며 -이소 사용을 보류','같은 카드에서 뜻 설명 한 문장만 추가해 비교'],
 ['잘못된 활용도 통과','재밌아가가 최종 문장에 반영','원시 표현·코드 보정·최종 표현을 따로 검토']])
content+='''<p><b>다음 승인 범위:</b> 연결·기록 오류 수정 → 전체50 재검사 → 하이소체 설명 유무 비교(호출 가능한 문장에 두 조건·각3회, 최대300호출). 같은 카드·위치·설정으로 비교하며 정답 문장은 전달하지 않습니다.</p><p>이 비교로 나머지 활용 오류까지 해결된다고 약속하지 않습니다. 설명을 추가해도 오해가 줄지 않으면 그 가설을 보류합니다. 이번에는 분석까지만 했으며 새 생성 호출은 0회입니다.</p><details><summary>판단 근거·정확한 실험 조건·검토 의견 반영 내역</summary>'''+readable_md(plan.read_text(encoding='utf8') if plan.exists() else '검토 결과를 종합하고 있습니다.')+'</details></section>'
content+='<section id="review"><h2>두 검토자의 의견</h2><p>독립 검토자의 원문입니다. 총괄의 채택·보류 판단은 위 실험안에 구분해 적었습니다.</p>'
for who,name in [('codex','Codex · 코드·실험 설계'),('claude','Claude · 문법·지식')]:
 f=P/'dispatch'/who/'response.md'
 content+='<details><summary>'+name+'</summary><pre>'+esc(f.read_text(encoding='utf8') if f.exists() else '아직 응답 없음')+'</pre></details>'
content+='</section><section id="cases"><h2>50문장 전체</h2><p>각 문장을 펼치면 원문·승인 참조·6개 출력과 실제 변경 과정을 볼 수 있습니다. 원시 제안이 비어 있으면 모델이 보류했거나 생성 기록이 없는 경우입니다.</p><input id="q" placeholder="문장 ID 또는 내용 검색" aria-label="문장 검색"><p id="count">50문장</p></section>'
for row in rows:
 c=read(P/row['case_file']);content+='<article class="case" data-text="'+esc(row['id']+' '+row['input'])+'"><details><summary>'+esc(row['id'])+' · '+esc(row['input'])+'</summary>'
 content+='<p><b>승인 참조:</b> '+esc(row['reference'])+'</p><p>'+''.join('<span class="tag">'+s+'</span>' for k,s in flags.items() if row[k])+'</p>'
 content+='<p class="muted">이전 검토의 범위(확정 원인 아님): '+esc(c['prior_review_scope'])+'</p>'
 content+=table(['선택','반복','최종 출력','기존 요약 상태','실제 최종 계획 상태'],[[esc('기존' if z['arm']=='saved' else '검토'),esc(z['repeat']),esc(z['output_text']) if z['output_text'] is not None else '<b>출력 없음</b>',esc(label(z['status'])),esc(label(plan_status(z,row['id'])))] for z in c['records']])
 for z in c['records']:
  traces=z.get('edit_trace',[])
  if not traces:continue
  content+='<details><summary>'+esc(('기존' if z['arm']=='saved' else '검토')+' 선택 / '+str(z['repeat'])+'회 처리')+'</summary>'
  content+=table(['원래 부분','선택 카드','Qwen의 원래 제안','반영 과정','검사·보정 기록'],[[esc(t['before']),'<br>'.join(esc(b['card_id']) for b in t['bindings']),esc(t['raw'])+'<br><small>'+esc(label(t['raw_action']))+'</small>',esc(t['after'])+'<br><small>'+esc(label(t['outcome']))+'</small>',('검사 문제 '+str(len(t['issues']))+'개 · 코드 보정 '+str(len(t.get('repairs',[])))+'회')+'<details><summary>기술 기록</summary>'+esc(', '.join(i['code'] for i in t['issues']))+'<br>'+esc(', '.join(i['kind'] for i in t.get('repairs',[])))+'</details>'] for t in traces])
  content+='</details>'
 content+='</details></article>'
content+='''<footer>원본 처리 기록과 승인 참조는 변경하지 않았습니다. 반복 기록을 독립된 새 문장으로 계산하지 않습니다.</footer></main><script>document.querySelector('#q').addEventListener('input',e=>{let n=0;document.querySelectorAll('.case').forEach(a=>{a.hidden=!a.dataset.text.toLowerCase().includes(e.target.value.toLowerCase());if(!a.hidden)n++});document.querySelector('#count').textContent=n+'문장';});</script></html>'''
(P/'review.html').write_text(content,encoding='utf8')
assert content.count('class="case"')==50
hashes=read(P/'source_hashes.json')
assert all(hashlib.sha256((R/k).read_bytes()).hexdigest()==v for k,v in hashes.items())
print(json.dumps({'html_cases':50,'source_hashes_unchanged':True,'html_bytes':(P/'review.html').stat().st_size}))
