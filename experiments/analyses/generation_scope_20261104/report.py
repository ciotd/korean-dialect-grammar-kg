"""Audit paired requests and render human-readable comparisons, never call a model."""
from pathlib import Path
import sys,json,collections,html,statistics,difflib
from urllib.parse import quote
from experiment import H,R,SOURCE,ARMS,SEEDS,read,save,sha,dumps,request_parts
P=H/'private'
def e(x):return html.escape(str(x))
def link(p,title):return '<a href="'+Path(p).resolve().as_uri()+'">'+e(title)+'</a>'
def table(head,rows):return '<div class="scroll"><table><tr>'+''.join('<th>'+e(x)+'</th>' for x in head)+'</tr>'+''.join('<tr>'+''.join('<td>'+str(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</table></div>'
def highlight(source,text):
 if text is None:return '[출력 실패]'
 parts=[]
 for tag,i,j,k,l in difflib.SequenceMatcher(None,source,text,autojunk=False).get_opcodes():
  if tag=='equal':parts.append(e(text[k:l]))
  else:
   if j>i:parts.append('<del title="원문에서 사라진 부분">'+e(source[i:j])+'</del>')
   if l>k:parts.append('<mark>'+e(text[k:l])+'</mark>')
 return ''.join(parts)
def summarize():
 combined={};validation=[]
 for cohort in ('regression','development'):
  latest=P/('latest_'+cohort+'.json')
  if not latest.exists():continue
  dirs={a:Path(d) for a,d in read(latest).items()};rows=read(dirs['A']/'private/shared_cases.json');arms={};requests={}
  for a,d in dirs.items():
   if not (d/'private/results.json').exists():continue
   rs=read(d/'private/results.json');arms[a]={'run_id':d.name,'metrics':read(d/'metrics.json'),'results':rs};requests[a]={}
   for rr in rs:
    record=d/'private/records'/rr['id'];req=read(record/'generation_call/request.json');r=next(x for x in rows if x['id']==rr['source_id']);prompt,payload=request_parts(r['packet'],a,version=read(d/'config.json').get('generation_policy_version','v1'))
    assert req['messages'][0]['content']==prompt and json.loads(req['messages'][1]['content'])==payload
    assert req['seed']==SEEDS[rr['repeat']-1]
    assert req['temperature']==0 and req['top_p']==1 and req['max_tokens']==2048
    assert req['model']==read(d/'config.json')['model_id'];requests[a][rr['id']]=req
    if rr['output_text'] is not None:
     raw=read(record/'generation_call/response.json');assert json.loads(raw['choices'][0]['message']['content'])['output_text']==rr['output_text']
    # Knowledge is invariant; only the scope instruction differs.
    user=json.loads(req['messages'][1]['content']);user['instruction']=r['packet']['instruction'];assert user==r['packet']
   assert all(sha((d/k).read_bytes())==v for k,v in read(d/'artifact_hashes.json').items())
  matches=[]
  for row in rows:
   comparisons={a:[r for r in x['results'] if r['source_id']==row['id']] for a,x in arms.items()}
   matches.append({'id':row['id'],'text':row['text'],'action_count':len(row['packet']['actions']),'knowledge_rules':[x['rule_id'] for x in row['packet']['actions']],'unresolved':row['packet'].get('unsupported_or_unresolved',[]),'arms':comparisons})
   for rep in (1,2):
    key=row['id']+'__r'+str(rep)
    if not all(key in requests.get(a,{}) for a in ARMS):continue
    same=('A','B') if row['packet']['actions'] else ('B','C');assert requests[same[0]][key]==requests[same[1]][key]
  groups={}
  for a,x in arms.items():
   groups[a]={}
   for name,pred in [('all',lambda r:True),('with_actions',lambda r:r['action_count']>0),('without_actions',lambda r:r['action_count']==0)]:
    rs=[r for r in x['results'] if pred(r)];suffix=[c for r in rs for c in r['diagnostic']['suffix_contracts']]
    groups[a][name]={'attempts':len(rs),'valid':sum(r['output_text'] is not None for r in rs),'changed':sum(r['diagnostic']['changed'] is True for r in rs),'unchanged':sum(r['diagnostic']['changed'] is False for r in rs),'outside_original_actions':sum(r['diagnostic']['outside_original_actions'] is True for r in rs),'suffix_match':sum(c['match'] is True for c in suffix),'suffix_mismatch':sum(c['match'] is False for c in suffix),'suffix_not_alignable':sum(c['match'] is None for c in suffix)}
  controls=[]
  for row in matches:
   a,b=('A','B') if row['action_count'] else ('B','C')
   for rep in (1,2):
    pair=[next((x for x in row['arms'].get(k,[]) if x['repeat']==rep),None) for k in (a,b)]
    if all(x and x['output_text'] is not None for x in pair):controls.append({'id':row['id'],'repeat':rep,'identical_request_arms':a+b,'same_output':pair[0]['output_text']==pair[1]['output_text']})
  repeats={a:{'valid_pairs':sum(len(rs:=row['arms'].get(a,[]))==2 and all(x['output_text'] is not None for x in rs) for row in matches),'different_outputs':sum(len(rs:=row['arms'].get(a,[]))==2 and all(x['output_text'] is not None for x in rs) and rs[0]['output_text']!=rs[1]['output_text'] for row in matches)} for a in arms}
  strata={}
  for row in matches:
   if row['action_count']:continue
   key=' + '.join(sorted({x['state'] for x in row['unresolved']})) or 'unspecified'
   group=strata.setdefault(key,{'ids':[],'changed':{a:0 for a in arms},'attempts_per_arm':0});group['ids'].append(row['id']);group['attempts_per_arm']+=2
   for a,rr in row['arms'].items():group['changed'][a]+=sum(x['output_text'] is not None and x['output_text']!=row['text'] for x in rr)
  disagreements=[{'arm':a,'id':x['id'],'model_status':x.get('model_status'),'actual_changed':x['output_text']!=x['input_text']} for a,v in arms.items() for x in v['results'] if x['output_text'] is not None and ((x.get('model_status')=='unchanged')!=(x['output_text']==x['input_text']))]
  combined[cohort]={'cases':matches,'groups':groups,'arms':arms,'no_action_strata':strata,'status_disagreements':disagreements,'repeat_variation':repeats,'identical_request_controls':{'valid_pairs':len(controls),'different_outputs':sum(not x['same_output'] for x in controls),'pairs':controls}}
  validation.append({'cohort':cohort,'rows':len(rows),'requests_verified':sum(len(x) for x in requests.values()),'knowledge_invariant':True,'paired_control_requests_equal':True,'raw_outputs_preserved':True,'artifacts_verified':True})
 save(P/'comparison.json',combined);save(P/'validation.json',validation);return combined
def render(data):
 refs={r['id']:r['reference'] for r in (json.loads(x) for x in (R/'data/derived_private/gyeongsang_reference50_20261030_v1/references.jsonl').read_text('utf8').splitlines())}
 h=['''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>생성 범위를 넓히면 달라질까?</title><style>body{font:17px/1.65 system-ui,sans-serif;background:#f4f6fa;color:#203149;margin:0}main{max-width:1200px;padding:28px 22px;margin:auto}h1{font-size:30px}h2{font-size:24px;margin-top:34px}.box,details{background:white;padding:20px;border:1px solid #d7e0ed;border-radius:10px;margin:15px 0}.scroll{overflow:auto}table{width:100%;border-collapse:collapse;font-size:15px}th,td{text-align:left;vertical-align:top;padding:11px;border-bottom:1px solid #dee5ed}th{background:#e8eef8}a{color:#1758a6}.small{font-size:14px;color:#54647b}.warn{background:#fff2d9}summary{cursor:pointer;font-weight:650}input,select,textarea,button{font:inherit;padding:8px;border:1px solid #a7b7ce;border-radius:5px}textarea{width:95%;height:65px}pre{white-space:pre-wrap;font-size:13px}.bar{background:#dce7f8;height:14px;border-radius:5px}.bar i{display:block;background:#3c76c5;height:14px;border-radius:5px}</style><main><p>② 비교 설계 · ③ 생성 실험 / 2026-11-04</p><h1>KG 수정 지시가 없는 곳에서도 Qwen이 바꾸게 하면?</h1><div class="box"><b>비교한 것:</b> 같은 문장·같은 분석·같은 KG 지식을 주고, Qwen이 수정할 수 있는 범위만 바꿨습니다.<br>기존 50문장과 새 개발 12문장을 구분합니다. 정답 번역은 생성 요청에 넣지 않았습니다.</div>''']
 front=P/'executive.json'
 if front.exists():
  f=read(front);h.append('<section class="box"><h2>핵심 결과</h2><p><b>'+e(f['conclusion'])+'</b></p><ul>'+''.join('<li>'+e(x)+'</li>' for x in f['points'])+'</ul></section>')
 h.append(table(['조건','허용한 작업'],[['A · 기존','KG가 지정한 위치만 변경. 지시가 없으면 원문 유지.'],['B · 지시 없는 문장 보완','지시가 없는 문장만 사전학습 지식으로 변환. 지시가 있는 문장은 A와 요청 동일.'],['C · 문장 전체','KG 지정 위치 밖도 변환 허용. 지시가 없는 문장은 B와 요청 동일.']]))
 h.append('<p class="box warn">문장이 많이 바뀌었다고 더 좋은 방언이 된 것은 아닙니다. KG가 지정하지 않은 표현은 모델의 자유 생성입니다. 모델 내부의 지식 출처를 관측한 것은 아니며 KG 제공 지식의 효과로 계산하지 않습니다.</p>')
 for cohort,title in [('regression','기존 50문장 · 분석/조회 고정'),('development','새 개발 12문장 · 분석 한 번 공유')]:
  if cohort not in data:continue
  d=data[cohort];h.append('<h2>'+title+'</h2><p>조건별 두 번 생성했습니다. 아래 숫자는 문장×반복 수입니다. 50문장 두 번은 독립 문장 100개가 아닙니다.</p>')
  rows=[]
  for a,x in d['arms'].items():
   g=d['groups'][a];m=x['metrics'];g0=g['without_actions'];g1=g['with_actions']
   rows.append([a,str(g['all']['valid'])+'/'+str(g['all']['attempts']),str(g0['changed'])+'/'+str(g0['attempts']),str(g1['changed'])+'/'+str(g1['attempts']),str(m['reported_usage']['total_tokens']),str(round(m['call_latency_median_seconds'],2)) if m['call_latency_median_seconds'] is not None else '—'])
  h.append(table(['조건','유효 출력','지시 없음: 변경','지시 있음: 변경','총 토큰','호출 지연 중앙값(초)'],rows))
  labels={'out_of_slice':'현재 지원 범위 밖','no_matching_usage':'조건에 맞는 용법 없음','needs_analysis':'분석값 미확정','unspecified':'상태 미기재'}
  h.append('<details><summary>왜 수정 지시가 전달되지 않았나?</summary><p>같은 입력에 여러 원인이 있으면 조합별로 묶었습니다. 지식이 없다는 뜻으로 단정하지 않습니다.</p>'+table(['미전달 상태','입력 수','A 변경','B 변경','C 변경'],[[e(' + '.join(labels.get(k,k) for k in key.split(' + '))),str(len(v['ids'])),*[str(v['changed'][a])+'/'+str(v['attempts_per_arm']) for a in ARMS]] for key,v in d['no_action_strata'].items()])+'</details>')
  h.append('<details><summary>모델의 자기 설명과 실제 출력이 다른 경우: '+str(len(d['status_disagreements']))+'응답</summary><p>“안 바꿨다”고 응답해도 실제 글자가 달라질 수 있습니다. 변경 수는 실제 원문·출력 비교로 계산했습니다.</p>'+table(['조건','기록 ID','모델 상태','실제 변경'],[[e(x['arm']),e(x['id']),e(x['model_status']),str(x['actual_changed'])] for x in d['status_disagreements']])+'</details>')
  ctl=d['identical_request_controls'];h.append('<p class="small">동일 요청 대조 '+str(ctl['valid_pairs'])+'쌍 중 출력이 달랐던 쌍: '+str(ctl['different_outputs'])+'. 요청이 같아도 출력이 달라질 수 있으므로 한 문장의 변화만으로 효과를 확정하지 않습니다. 비용은 생성 단계이며 새 개발의 공유 분석 비용은 별도입니다.</p>')
  h.append('<details><summary>기존 결합 지시를 지켰는지 — 품질 점수가 아닌 제한된 검사</summary>'+table(['조건','문자 구조 일치','불일치','문장 재구성으로 위치 검사 불가'],[[a,*[str(d['groups'][a]['all'][k]) for k in ('suffix_match','suffix_mismatch','suffix_not_alignable')]] for a in d['arms']])+'<p>아/어요계열의 해체+예 결합이 지정된 위치에서 보존됐는지 확인합니다. C의 위치 밖 변경은 허용 행동이므로 오류로 세지 않습니다. 검사 불가를 실패 0점으로 처리하지 않습니다.</p></details>')
 h.append('<h2>입력별 세 결과를 비교하세요</h2><p><del>취소선</del>은 사라진 원문, <mark>색칠</mark>은 새로 생긴 글자입니다.</p><p>승인 참조는 사람이 비교하기 위해서만 표시합니다. 생성 모델에는 전달하지 않았습니다. 아래 메모는 브라우저에 임시 저장되며 <b>저장 파일 내보내기</b>를 해야 전달할 수 있습니다. KG를 자동 수정하지 않습니다.</p><input id="search" placeholder="ID 또는 문장 검색"> <select id="group"><option value="all">모든 입력</option><option value="none">KG 지시 없는 입력</option><option value="some">KG 지시 있는 입력</option></select> <button onclick="download()">저장 파일 내보내기</button><div id="cases">')
 for cohort,d in data.items():
  for row in d['cases']:
   key=cohort+'_'+row['id'];h.append('<details class="case" data-group="'+('some' if row['action_count'] else 'none')+'"><summary>'+e(row['id']+' · '+row['text'])+'</summary><p>KG 지시 '+str(row['action_count'])+'개 · '+e(', '.join(row['knowledge_rules']) or '없음')+'</p>')
   rows=[]
   for a,rr in row['arms'].items():
    for x in rr:rows.append([a+' / '+str(x['repeat'])+'회',highlight(row['text'],x['output_text']),e(x.get('reason','')),link(R/'experiments/runs'/d['arms'][a]['run_id']/'private/records'/x['id']/'generation_call/request.json','실제 요청')])
   h.append(table(['조건','Qwen 원시 출력','모델 설명 (사실 판정 아님)','기록'],rows))
   if row['id'] in refs:h.append('<p class="small">사용자 승인 참조: '+e(refs[row['id']])+'</p>')
   h.append('<label>검토 의견 <textarea data-key="'+key+'" placeholder="자연스러움 / 뜻·시제·부정 보존 / 높임·말투 변화 등을 적어 주세요."></textarea></label></details>')
 h.append('</div><h2>다음 판단과 검토 근거</h2>')
 finding=H/'findings.md'
 h.append('<p>'+link(H/'reviewer_resolution.md','두 검토자의 의견과 반영 여부')+'</p>')
 if finding.exists():h.append('<div class="box"><pre>'+e(finding.read_text('utf8'))+'</pre></div>')
 for who in ('codex','claude'):
  for stage in ('plan','results'):
   p=P/'reviewers'/stage/who/'review.md'
   if p.exists():h.append('<details><summary>'+who+' · '+stage+' 검토</summary><pre>'+e(p.read_text('utf8'))+'</pre></details>')
 costs=[]
 for label,paths in [('수정 전 v1 회귀300',P/'v1_latest_regression.json'),('최종 v2 회귀300',P/'latest_regression.json'),('개발72',P/'latest_development.json')]:
  if paths.exists():
   ms=[read(Path(d)/'metrics.json') for d in read(paths).values() if (Path(d)/'metrics.json').exists()]
   costs.append([label,sum(x['api_attempts'] for x in ms),sum(x['reported_usage']['total_tokens'] for x in ms)])
 da=P/'latest_dev_analysis.json'
 if da.exists():
  am=read(Path(read(da)['directory'])/'metrics.json');costs.append(['새 개발 공유 분석',am['api_attempts'],am['reported_usage']['total_tokens']])
 h.append('<h2>실제 수행량 — 수정 전 실험도 포함</h2>'+table(['묶음','호출 수','총 토큰'],[[e(x[0]),str(x[1]),str(x[2])] for x in costs])+'<p>첫 회귀 결과는 검토 중 모호한 문구가 발견되어 보존했습니다. 수정된 v2와 합쳐 품질을 계산하지 않습니다. 이 기록의 호출 수는 조회용 모델 목록 요청을 제외한 chat 요청입니다.</p>')
 if (P/'v1_report.html').exists():h.append('<p>'+link(P/'v1_report.html','수정 전 v1 결과 (보존본)')+'</p>')
 h.append('<p>'+link(H/'PLAN.md','실행 전 계획과 변경 이유')+' · '+link(H/'plain_statement_notes.md','반말 평서와 근거 구분')+' · '+link(P/'validation.json','요청·원시 출력 검증')+' · '+link(P/'comparison.json','집계 원본')+'</p>')
 h.append('''</main><script>const storageKey='kg_scope_review_20261104_v1';let notes={};try{notes=JSON.parse(localStorage.getItem(storageKey)||'{}')}catch{}document.querySelectorAll('textarea').forEach(x=>{x.value=notes[x.dataset.key]||'';x.oninput=()=>{notes[x.dataset.key]=x.value;localStorage.setItem(storageKey,JSON.stringify(notes))}});function download(){const blob=new Blob([JSON.stringify({version:1,created_at:new Date().toISOString(),notes},null,2)],{type:'application/json'});let a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='generation_scope_review.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}function filter(){let q=document.getElementById('search').value.toLowerCase(),g=document.getElementById('group').value;document.querySelectorAll('.case').forEach(x=>x.hidden=!((g==='all'||x.dataset.group===g)&&x.textContent.toLowerCase().includes(q)))}document.getElementById('search').oninput=filter;document.getElementById('group').onchange=filter;</script></html>''')
 (P/'report.html').write_text(''.join(h),'utf8')
if __name__=='__main__':render(summarize());print(P/'report.html')
