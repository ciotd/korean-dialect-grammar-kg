"""Human-readable paired report and request-level control audit; no model calls."""
import collections,html,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from kg_pipeline.io import read,save,sha,dumps
E=lambda x:html.escape(str(x if x is not None else '미확정'))
def table(head,rows):return '<div class="scroll"><table><tr>'+''.join('<th>'+E(x)+'</th>' for x in head)+'</tr>'+''.join('<tr>'+''.join('<td>'+str(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</table></div>'
def maybe(path,default):return read(path) if path.exists() else default
def build():
 run=ROOT/read(HERE/'latest.json')['run'];results=read(run/'private/results.json');m=read(run/'metrics.json');cfg=read(run/'config.json')
 index={(r['id'],r['backend']):r for r in results};ids=list(dict.fromkeys(r['id'] for r in results))
 audit={'run':run.name,'checks':{},'pairs':[]};requests=collections.defaultdict(list)
 for p in (run/'private/records').rglob('request.json'):
  r=read(p);requests[p.parent.name].append(r)
 for role in ('meaning','writer','reviewer'):
  rr=requests[role];settings=[{k:r.get(k) for k in ('model','temperature','top_p','seed','max_tokens','chat_template_kwargs')} for r in rr]
  audit['checks'][role]={'calls':len(rr),'one_system_prompt':len({r['messages'][0]['content'] for r in rr})==1,
    'one_sampling_config':len({dumps(x) for x in settings})==1,'system_prompt_sha256':sha(rr[0]['messages'][0]['content'].encode()) if rr else None,
    'no_backend_label':all('"backend"' not in r['messages'][1]['content'] for r in rr)}
 audit['checks']['no_repair_calls']=not requests['revision'] and not requests['structure_revision']
 audit['checks']['postflight']=read(run/'postflight.json')
 rows=[];details=[]
 kinds={'predicate':'용언','nominal':'명사류','particle':'조사','connector':'절 연결 어미','construction':'보조용언 구성'}
 labels={'lemma':'기본형','source_final':'끝 어미','past_form':'과거 표지','tense':'시간 의미','addressee_level':'상대 높임','subject_honorific':'주체 높임','speech_act':'문장 기능'}
 values={'plain':'반말','polite':'존댓말','formal':'격식 존댓말','past':'과거','future':'미래','statement':'평서','request':'요청','prohibition':'금지','promise':'약속','information_question':'정보 질문'}
 def show_feature(k,v):
  if k in ('past_form','subject_honorific'):return '있음' if v=='present' else '없음' if v=='absent' else str(v)
  if k=='tense' and v=='present':return '현재'
  return values.get(v,str(v))
 for identifier in ids:
  pair=[index.get((identifier,b),{}) for b in ('qwen','kiwi')];source=next(r['input_text'] for r in pair if r)
  rows.append([E(identifier),E(source)]+[E(r.get('output_text','실패 또는 미시도')) for r in pair])
  paths={b:run/'private/records'/(identifier+'_'+b) for b in ('qwen','kiwi')};record={'id':identifier}
  for name in ('meaning','writer','reviewer'):
   req=[maybe(paths[b]/name/'request.json',None) for b in paths]
   record[name+'_request_identical']=req[0] is not None and req[0]==req[1]
   resp=[maybe(paths[b]/name/'parsed.json',None) for b in paths]
   record[name+'_response_identical']=resp[0] is not None and resp[0]==resp[1]
  audit['pairs'].append(record)
  blocks=['<h3>'+E(source)+'</h3>']
  morphs={b:maybe(paths[b]/'morphology_rows.json',{'words':[]}) for b in paths}
  wordrows=maybe(paths['qwen']/'common_anchors.json',maybe(paths['kiwi']/'common_anchors.json',[]))
  tokenmap={b:{x['word_id']:' + '.join(t['form']+'/'+t['tag'] for t in x['morphs']) for x in raw['words']} for b,raw in morphs.items()}
  blocks.append(table(['원문 어절','Qwen이 나눈 형태','Kiwi가 나눈 형태'],[[E(w['surface']),E(tokenmap['qwen'].get(w['uid'])),E(tokenmap['kiwi'].get(w['uid']))] for w in wordrows]))
  for b in paths:
   rd=paths[b];r=index.get((identifier,b),{});units=maybe(rd/'bound_analysis.json',[]);actions=maybe(rd/'selected_knowledge.json',[])
   blocks.append('<h3>'+E(b.upper())+' 이후 처리</h3>')
   blocks.append(table(['원문 위치','어떤 단위인가','분석된 형태·의미','남은 이의'],[[E(u['text']),E(kinds[u['kind']]),E(' / '.join(labels[k]+': '+show_feature(k,u['features'][k]) for k in labels if u['features'].get(k) is not None)),E(u.get('analysis_issues',[])+u.get('structural_objections',[]))] for u in units]))
   blocks.append('<p>생성 모델에 전달한 규칙: '+str(len(actions))+'개. 이 수치는 정확도가 아닙니다.</p>')
   blocks.append(table(['적용 위치','전달 지시','실제 KG ID'],[[E(a.get('source_text')),E(a.get('instruction')),E(a['rule_id'])] for a in actions]))
   omissions=collections.Counter(x['reason'] for x in r.get('delivery_omissions',[]))
   blocks.append('<p>보류 기록: '+E(dict(omissions))+'</p><p><strong>Qwen 실제 출력:</strong> '+E(r.get('output_text'))+'</p>')
   issues=r.get('review',{}).get('issues',[])
   blocks.append(table(['검토 모델이 한 말 — 틀릴 수도 있음','제안'],[[E(x['problem']),E(x['suggestion'])] for x in issues]))
  details.append('<details><summary>'+E(identifier)+' — 형태부터 출력까지 보기</summary>'+''.join(blocks)+'</details>')
 save(HERE/'private/control_audit.json',audit)
 metrics=[]
 for b,v in m['by_backend'].items():
  mm=[read(p) for d in (run/'private/records').glob('*_'+b) for p in d.rglob('meta.json')]
  morph=[x for x in mm if x['stage']=='controlled_morphology'];down=[x for x in mm if x['stage']!='controlled_morphology']
  metrics.append([E(b.upper()),str(v['complete'])+'/'+str(v['records']),v['api_attempts'],v['reported_usage']['total_tokens'],round(v['record_seconds'],1),sum((x.get('usage') or {}).get('total_tokens',0) for x in morph),sum((x.get('usage') or {}).get('total_tokens',0) for x in down)])
 notes=HERE/'RESULTS.md';explanation=''.join('<p>'+E(p).replace('\n','<br>')+'</p>' for p in notes.read_text(encoding='utf8').split('\n\n')) if notes.exists() else '<p>결과 검토 중입니다. 아래 출력은 실제 기록입니다.</p>'
 css='body{font-family:Malgun Gothic,Arial;background:#f4f7fb;color:#17334a;max-width:1180px;margin:30px auto;padding:20px;line-height:1.85}section,details{background:white;padding:22px;border:1px solid #d7e1ed;border-radius:12px;margin:16px 0}h1{font-size:30px}h2{font-size:23px}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border:1px solid #d7e1ed;padding:12px;vertical-align:top;text-align:left}th{background:#e8f0fa}.scroll{overflow:auto}.flow{padding:20px;background:#e3f1ff;border-radius:12px;font-size:18px}.note{padding:15px;background:#fff4d8}summary{cursor:pointer;font-weight:bold}a{color:#1764a4}'
 page='<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>형태 분석만 바꾼 비교</title><style>'+css+'</style><h1>형태 분석만 바꾸면 결과도 달라질까?</h1><p>2026년 11월 7일 · 같은 개발 6문장을 Qwen과 Kiwi 두 방식으로 처리했습니다. 형태를 나누는 담당자만 다르고, 그 뒤의 의미 분석·KG 조회·문장 작성·검토 지시는 같습니다.</p><div class="flow">같은 원문·절 구획 → <strong>Qwen 형태 분석 또는 Kiwi 형태 분석</strong> → 같은 단위 정리 → 같은 Qwen 의미 분석 → 같은 KG 조회 → 같은 Qwen 작성 → 같은 검토(재작성 없음)</div><section><h2>1. 결론과 다음 행동</h2>'+explanation+'</section><section><h2>2. 무엇을 같게 두었나?</h2>'+table(['고정','뜻'],[[E('원문·절 구획·KG'),E('이전 최초 Qwen 구획을 양쪽에 재사용했습니다. 정답 구획이라는 뜻은 아닙니다.')],[E('의미·작성·검토 지시와 모델 설정'),E('분석 결과나 전달 규칙은 달라질 수 있지만 이를 처리하는 방법은 같습니다.')],[E('자동 재분석·재작성 모두 0회'),E('잘못된 검토가 작성 결과를 다시 바꾸는 영향을 이번 비교에서 제외했습니다.')],[E('형태소 표기와 공통 연결 코드'),E('같은 형태소를 주면 같은 후속 요청이 나오는지 코드로 검사했습니다. 현재 KG 표기와의 호환성도 결과에 포함됩니다.')]])+'<p class="note">분석값 자체를 똑같이 만든 실험이 아닙니다. 분석기가 다르게 분석하면 이후 판단도 달라질 수 있습니다. 이전 전체 경로 비교와 달리 이번 두 방식끼리는 같은 후속 코드를 사용합니다.</p></section><section><h2>3. 실제 비용과 완료 여부</h2>'+table(['형태 분석','완료/시도','Qwen 호출','전체 토큰','경로 시간(초)','형태 호출 토큰','이후 호출 토큰'],metrics)+'<p>Kiwi 초기화 '+E(round(cfg.get('kiwi_initialization_seconds',0),2))+'초는 위 경로 시간 밖의 공통 준비 기록입니다. 완료는 자연스러운 문장이라는 뜻이 아닙니다. 독립 사람 평가·정답 정확도는 계산하지 않았습니다.</p></section><section><h2>4. 같은 문장의 실제 출력</h2>'+table(['ID','원문','Qwen 형태 분석 후 출력','Kiwi 형태 분석 후 출력'],rows)+'</section><section><h2>5. 왜 달라졌는지 직접 확인</h2><p>VV=동사, VA=형용사, VX=보조용언, EP=과거·높임 등 선어말 어미, EF=종결어미, ETM=관형형 어미입니다. 아래 검토 모델의 말은 검증된 사실이 아닙니다.</p>'+''.join(details)+'</section><section><h2>6. 검토와 재현 기록</h2><p><a href="claude_outcome_review.md">Claude 결과 검토</a> · <a href="codex_outcome_review.md">Codex 결과 검토</a> · <a href="../DECISIONS.md">의견 반영과 정정</a> · <a href="../prompts.md">실제 지시문</a> · <a href="../README.md">실행·검사 기록</a></p><p>실행: '+E(run.name)+'</p></section></html>'
 (HERE/'private/report.html').write_text(page,encoding='utf8')
 (HERE/'prompts.md').write_text('# 비교에서 실제 사용한 지시문\n\n'+'\n\n'.join('## '+name+'\n\n'+(run/'prompts'/f'{name}.txt').read_text(encoding='utf8') for name in ('morphology','meaning','writer','reviewer')),encoding='utf8')
 print(dumps({'report':str(HERE/'private/report.html'),'control_audit':audit}))
if __name__=='__main__':build()
