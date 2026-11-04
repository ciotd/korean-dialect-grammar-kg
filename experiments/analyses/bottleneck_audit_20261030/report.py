"""Readable all-50 bottleneck audit, grounded in immutable saved traces."""
import collections,hashlib,html,json
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2];P=BASE/'private'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
E=lambda x:html.escape(str(x if x is not None else '출력 없음'))
T={'analysis':'입력 분석','protocol':'응답·편집 계약','knowledge':'변환 지식 보완','retrieval':'조회·전달','selection':'후보 선택·조건','composition':'활용·교체 범위','validation':'검사 오판','lexical':'어휘·구문 실행 범위','working':'작동한 부분 보존'}
ST={'applied_somewhere':'선택·일부 반영','selected':'선택했으나 미반영/실패','delivered_not_selected':'전달했으나 미선택','retrieved_not_delivered':'조회 후 전달에서 빠짐','not_retrieved':'조회 기록에 없음','analysis_stopped':'분석에서 중단'}
ERR={'stale_request':'요청 번호 복사 불일치','CallError:200':'응답 길이 제한','invalid_analysis_function':'분석 기능 이름 불일치','binding_not_ending':'요(JX)와 어미 편집 계약 불일치'}
OUT={'applied':'반영','needs_review':'보류','kept':'유지','unchanged':'변경 없음','planned':'계획','apply':'적용 제안','keep':'유지 제안'}
def support(f):
 k=f['key']
 if k=='promise_bare':return '직접 약속 -께 카드 미확인. 다른 기능의 -께와 구별 필요.'
 if k=='muk':return '관련 활용 관찰. 먹다→묵다의 직접 대응 규칙은 아님.'
 if k=='negcop':return '음운 관찰. 아니야→아이다의 직접 생성 규칙은 아님.'
 if k=='retro':return '더니→더니만/디만 계열. 봤는데에 직접 적용 가능한지는 미확인.'
 if k=='rai':return '관련 어미 목록. 마레이의 금지·당부 구성 전체는 추가 확인.'
 if k in ('put','small'):return '명시적 어휘 대응 있음. 현재 어휘 보존·편집 계약과 별도 연결 필요.'
 if k in ('formal_q','formal_decl','kkaye','iso','da','ra'):return '형태 목록/관련 규칙 있음. 입력별 기능·높임·결합 가능성은 별도 확인.'
 if k in ('quote','intent'):return '연결 성분 대응 있음. 인용+하다/관형 구성 전체와 동일하지 않음.'
 return '관련 대응 지식 있음. 아래 실제 적용 결과와 입력 조건을 함께 확인.'
def main():
 cases=read(P/'evidence.json');notes=read(P/'notes.json');analysis=read(P/'analysis_observations.json');solutions=read(P/'solutions.json');counts=collections.Counter()
 assert len(cases)==50 and set(notes)=={c['id'] for c in cases}
 refs={r['id']:r for r in [json.loads(x) for x in (ROOT/'data/derived_private/gyeongsang_reference50_20261030_v1/references.jsonl').read_text(encoding='utf-8').splitlines()]}
 failures=[];paths=collections.Counter();complete_matches=[];applied=0;edits=0
 for c in cases:
  assert c['input']==refs[c['id']]['input'] and c['reference']==refs[c['id']]['reference']
  counts.update(notes[c['id']]['tags'])
  for arm,v in c['arms'].items():
   if v['error']:failures.append({'id':c['id'],'arm':arm,'error':v['error']})
   if v['output']==c['reference']:complete_matches.append({'id':c['id'],'arm':arm})
   for e in v.get('plan',{}).get('edits',[]):edits+=1;applied+=e['outcome']=='applied'
   paths.update(x['stage'] for x in v['candidate_trace'].values())
 for rel,h in read(P/'input_hashes.json').items():assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==h,rel
 summary={'input_count':50,'actual_run_records':100,'new_model_calls':0,'new_KG_queries':0,'pipeline_or_card_changes':False,
  'review_topics_overlapping':dict(counts),'explicit_analysis_observations':len(analysis),'execution_failures':dict(collections.Counter(f['error'] for f in failures)),
  'candidate_path_states_not_causal_labels':dict(paths),'complete_reference_matches_not_quality_score':complete_matches,'final_plan_edits':edits,'applied_edits':applied,
  'review_status':'lead evidence audit; mechanistic subset independently reviewed; linguistic applicability not globally adjudicated',
  'limits':['Related candidate mapping reused and refined, not a completeness proof for all sources.','No new counterfactual model experiment.','Same reference expression is not the only valid output.']}
 save(P/'summary.json',summary);save(P/'verification.json',{'50_notes_complete':True,'reference_texts_unchanged':True,'all_read_input_hashes_unchanged':True,'read_files':len(read(P/'input_hashes.json')),'new_calls':0})
 h='<header><p class="eyebrow">50문장 전체 · 기존 기록 대조 · 새 모델 호출 없음</p><h1>필요한 정보는 어디서 끊겼나?</h1><p class="lead">문제는 KG 하나가 아닙니다.<br><strong>입력 분석 오류, 덜 정리된 변환 지식, 잘못된 선택, 좁은 편집 범위, 검사 오류가 함께 있습니다.</strong></p><p>승인한 Claude 표현과 최신 Single·Multi 기록 100개를 대조했습니다. 이번에는 카드나 생성 코드를 고치지 않았습니다.</p></header>'
 h+='<nav><a href="#conclusion">핵심 결론</a><a href="#fixes">어떻게 고칠까</a><a href="#cases">50문장 대조</a><a href="#limits">확인 범위</a><a href="/work">진행·승인 기록</a></nav>'
 h+='<section id="conclusion"><h2>지금 가장 중요한 세 가지</h2><ol><li><b>앞단 분석부터 틀린 경우가 있습니다.</b> 반말을 높임으로, 부정이 없는 문장을 부정으로 기록했습니다. 실제 분석 값과 대조해 '+str(len(analysis))+'개 입력에 구체적인 검토 의견을 남겼습니다. 전체 분석 오류율을 계산한 것은 아닙니다.</li><li><b>카드의 존재와 사용할 지식의 완성은 다릅니다.</b> ‘묵다’ 활용 카드가 있다고 ‘먹자→묵자’를 실행할 수 있는 것은 아닙니다.</li><li><b>목표와 편집기의 범위가 다릅니다.</b> 승인 표현은 어휘·구문도 바꾸지만 현재 지시·검사는 어휘 보존과 어미/조사 교체 중심입니다.</li></ol><p class="notice">조건 검사를 더 붙이는 것만으로 해결되지 않습니다. 틀린 변경을 막는 것과 올바른 대안을 만드는 것을 함께 설계해야 합니다.</p></section>'
 h+='<section><h2>실제 기록으로 확인한 예</h2><div class="flow"><span>입력 분석</span><b>→</b><span>KG 지식</span><b>→</b><span>조회·전달</span><b>→</b><span>선택·조합</span><b>→</b><span>검사·출력</span></div><div class="tablewrap"><table><tr><th>사례</th><th>어디서 끊겼나</th><th>해결 방향</th></tr>'
 examples=[('LONG001','반말 전체를 formal로 분석. 왜는 의문사, 와는 판정 질문으로 따로 분류.','절 안의 질문 종류·말높임을 연결해 분석부터 교정.'),('DEV022','묵 카드는 전달됐지만 내용은 무우 활용. 먹자→묵자 대응이 아님.','어휘 대응+청유 어미 보존을 별도 지식·동작으로 연결.'),('DEV002','-다 카드 조회 후 전달에서 빠짐.','종결 위치에 필요한 중립 평서 후보를 남김. 적용 정보도 보완.'),('LONG004','금지로 분석했지만 약속 카드 선택. 해당 기능 검사가 생략됨.','기능 충돌을 검사하고 금지에 맞는 대안으로 연결.'),('ADVCE002A','Qwen의 계시ㅂ니더를 프로그램이 계십니더로 조합했으나 검사에서 보류.','정당한 방언형을 잘못 막는 재분석 검사 보완.'),('QUAL017','하려고요의 요는 JX. 한 편집의 태그 불일치로 전체 출력 실패.','종결 구성과 형태소 태그 연결·독립 편집 실패 격리.')]
 for i,p,f in examples:h+='<tr><td><a href="#'+i+'">'+i+'</a></td><td>'+E(p)+'</td><td>'+E(f)+'</td></tr>'
 h+='</table></div><p>독립 검토자가 원본 응답·분석·카드·코드를 대조해 위 기계적 원인을 확인했습니다. 모든 표현의 자연스러움을 인증한 것은 아닙니다.</p></section>'
 h+='<section id="fixes"><h2>어떤 순서로 보완할까?</h2><p><b>먼저 분석·응답·편집 계약을 정리하고, 그다음 말단 지식과 선택·조합을 연결하는 순서</b>를 권합니다. 아래는 수정 제안이며 아직 적용하지 않았습니다.</p><table><tr><th>순서</th><th>할 일</th><th>끝났다고 판단할 기준</th></tr><tr><td>1</td><td>기존 50개 분석의 명백한 오류와 응답·편집 계약 불일치 교정</td><td>잘못된 기능 이름·번호 복사·태그 불일치 원인을 저장 응답으로 재현하고, 통과/거절해야 할 사례를 구별</td></tr><tr><td>2</td><td>필요한 말단 지식을 입력→조건→교체 범위→목표 형태로 연결</td><td>목록/관련 관찰/직접 변환 지식이 구별되고, 어휘·어미·구성별 동작이 맞음</td></tr><tr><td>3</td><td>위치별 후보 선택과 활용·보존 검사 연결</td><td>잘못된 선택은 대안으로 연결하고, 올바른 계십니더 같은 표현을 막지 않음</td></tr><tr><td>4</td><td>같은 50개로 변경 효과를 분리해 확인</td><td>한번에 모두 바꾸지 않고 분석만/선택만/조합만 바꾼 결과를 구별. 기존 성공 부분도 보존</td></tr></table>'
 h+='<p class="notice">이 순서는 ‘추정상 가장 효과가 크다’는 순위가 아니라, 앞단 오류가 뒤쪽 실험을 흐리지 않게 하는 작업 순서입니다. 효과 크기는 통제 확인 전에는 알 수 없습니다. 새 실험은 별도 승인 후 수행합니다.</p>'
 for s in solutions:
  h+='<details id="fix-'+s['id']+'"><summary>'+E(s['title'])+' <small>관련 검토 '+str(counts[s['id']])+'문장</small></summary><dl>'
  for key,label in [('problem','문제'),('evidence','실제 근거'),('change','무엇을 바꿀지'),('test','어떻게 확인할지'),('benefit','기대 효과와 한계'),('location','수정할 위치')]:h+='<dt>'+label+'</dt><dd>'+E(s[key])+'</dd>'
  h+='</dl></details>'
 h+='<p class="small">관련 문장 수는 총괄의 검토 주제 표시입니다. 한 문장에 여러 주제가 있어 합계가 50을 넘습니다. 원인별 실패율이나 개선 예상 건수가 아닙니다.</p></section>'
 h+='<section><h2>출력조차 없었던 경우는 따로 봅니다</h2><table><tr><th>중단 원인</th><th>실행 수</th></tr>'
 for k,n in summary['execution_failures'].items():h+='<tr><td>'+E(ERR[k])+'</td><td>'+str(n)+'</td></tr>'
 h+='</table><p>합계 10개 실행입니다. 같은 입력의 Single·Multi를 각각 셉니다. 길이 종료는 짧은 문장에서도 발생했고 설명 반복이 관찰됐습니다. 모두 긴 입력 탓으로 볼 수 없습니다.</p></section>'
 h+='<section id="cases"><h2>50문장: 문제와 해결책을 한곳에서 보기</h2><p>각 문장을 펼치면 원문·승인 표현·실제 두 출력·단절 위치·해결책을 볼 수 있습니다. <b>특정 후보를 쓰지 않았어도 같은 기능의 다른 카드로 성공할 수 있습니다.</b></p><div class="filters"><input id="search" aria-label="문장 검색" placeholder="ID 또는 문장 검색"><select id="filter" aria-label="검토 주제"><option value="all">모든 검토 주제</option>'+''.join('<option value="'+k+'">'+v+'</option>' for k,v in T.items())+'</select><span id="count"></span></div>'
 for c in cases:
  n=notes[c['id']];h+='<details class="case" id="'+c['id']+'" data-tags="'+' '.join(n['tags'])+'" data-search="'+E(c['id']+' '+c['input']+' '+c['reference'])+'"><summary><b>'+c['id']+'</b> '+E(c['input'])+'</summary><div class="labels">'+''.join('<span>'+T[t]+'</span>' for t in n['tags'])+'</div><table class="outputs"><tr><th>원문</th><td>'+E(c['input'])+'</td></tr><tr><th>승인 Claude 표현</th><td>'+E(c['reference'])+'</td></tr>'
  for a,v in c['arms'].items():h+='<tr><th>'+a.title()+'</th><td>'+E(v['output'])+(' <b>('+ERR.get(v['error'],str(v['error']))+')</b>' if v['error'] else '')+'</td></tr>'
  h+='</table><div class="diagnosis"><h3>기록에서 확인한 것</h3><p>'+E(n['finding'])+'</p>'
  if c['id'] in analysis:h+='<p><b>앞단 분석도 확인:</b> '+E(analysis[c['id']])+'</p>'
  h+='<h3>어떻게 보완할까?</h3><p>'+E(n['fix'])+'</p><p class="small"><b>확정하지 않은 부분:</b> '+E(n['limit'])+'</p></div>'
  h+='<details><summary>근거: 필요한 표현과 실제 카드 경로</summary><p>여기서는 <b>관련 후보의 이동 기록</b>과 <b>실제로 쓸 지식이 준비됐는지</b>를 구별합니다. 관련 후보는 기존 문헌 비교에서 찾은 목록이며, 원문 문헌 전체의 모든 대안을 망라했다는 뜻은 아닙니다.</p><div class="tablewrap"><table><tr><th>관련 표현</th><th>지식 준비 상태</th><th>실제 경로</th><th>문헌 연결</th></tr>'
  for f in c['families']:
   traces=[]
   for cid in f['candidate_ids']:
    t=c['arms']['single']['candidate_trace'][cid];card=t['card']
    traces.append('<b>'+E(card['title'])+'</b><br><code>'+cid+'</code><br>Single: '+ST[t['stage']]+'<br>Multi: '+ST[c['arms']['multi']['candidate_trace'][cid]['stage']])
   src='; '.join(x['doc']+' PDF '+str(x['pdf_page'])+'쪽' for x in f['source_excerpts']) or '추가 확인 필요'
   h+='<tr><td>'+E(f['label'])+'</td><td>'+E(support(f))+'</td><td>'+('<hr>'.join(traces) or '직접 후보 미확인')+'</td><td>'+E(src)+'<br><small>기존 원문 대조 기록 재사용</small></td></tr>'
  h+='</table></div></details>'
  h+='<details><summary>근거: 실제로 선택하고 반영한 부분</summary>'
  for a,v in c['arms'].items():
   h+='<h3>'+a.title()+'</h3>'
   es=v.get('plan',{}).get('edits',v.get('raw_agent',{}).get('edits',[]))
   if not es:h+='<p>'+('계획 완료 전 중단됐습니다.' if v['error'] else '편집 항목을 만들지 않고 유지했습니다.')+'</p>'
   else:
    h+='<div class="tablewrap"><table><tr><th>입력 부분</th><th>모델 제안</th><th>실제 처리</th><th>선택한 카드</th></tr>'
    for e in es:
     ids=[b['card_id'] for b in e.get('bindings',[])];before=e.get('before')
     if before is None:
      words={w['uid']:w['surface'] for w in v.get('morphology',{}).get('words',[])};before=' '.join(words.get(i,i) for i in e.get('word_ids',[]))
     outcome=e.get('outcome',e.get('action'));status=OUT.get(outcome,outcome)
     actual=(e['after'] if outcome=='applied' else '최종 출력 없음' if v['error'] else '원문 유지')
     titles={x['id']:x['title'] for x in v.get('packet',{}).get('cards',[])}
     h+='<tr><td>'+E(before)+'</td><td>'+E(e.get('proposed_after',e.get('after')))+'</td><td>'+E(status)+'<br>'+E(actual)+'</td><td>'+E('; '.join(titles.get(i,i) for i in ids))+'</td></tr>'
    h+='</table></div>'
   h+='<p class="small">원본 기록: <code>'+E(v['record'])+'</code></p>'
  h+='</details><p>관련 해결안: '+', '.join('<a href="#fix-'+t+'">'+T[t]+'</a>' for t in n['tags'])+'</p></details>'
 h+='</section><section id="limits"><h2>이번에 확인한 범위</h2><ul><li>승인 참조50개, 최신 실행100개, 최종 편집'+str(edits)+'개, 실제 분석·조회 경로·전달 카드·원래 응답·보정·검사를 대조했습니다.</li><li>새 모델 호출·카드 수정·생성 코드 수정은 0회입니다. 입력·원본 기록 해시를 확인했습니다.</li><li>원문 문헌 전체를 이번에 다시 정독하지 않았습니다. 기존 문헌 대조 근거를 재사용하고 현재 카드 내용을 확인했습니다. 문자 검색 실패를 문헌 부재로 단정하지 않습니다.</li><li>최신 실행은 앞선 분석과 조회를 재사용했습니다. 현재 자동 검색기를 새로 실행한 성능 평가가 아닙니다.</li><li>관찰된 경로 단절과 인과 효과는 다릅니다. 분석 또는 카드 선택만 바꿔 재실행한 통제 실험은 이번에 하지 않았습니다.</li><li>50개는 이미 개선에 사용한 회귀 자료입니다. 별도의 미사용 문장 평가 없이 일반 성능을 주장하지 않습니다.</li></ul><p><b>사용자가 지금 50문장을 다시 전부 채점할 필요는 없습니다.</b> 기록으로 확인되는 오류부터 보완할 수 있습니다. 걸으시소·주세예·열쇠을·빌려드릴께예 같은 대안의 실제 허용성은 추가로 필요할 때 묻겠습니다. 승인 표현과 다르다는 이유만으로 자동 오답 처리하지 않았습니다.</p></section>'
 css='''*{box-sizing:border-box}body{margin:0;background:#f5f7fa;color:#172c40;font:17px/1.8 system-ui,sans-serif}main{max-width:1140px;margin:auto;padding:32px 24px}header{padding:22px;background:#e9f0f9;border-radius:16px}h1{font-size:32px;line-height:1.4}h2{font-size:25px;margin:0 0 16px}h3{font-size:19px}.eyebrow,.small,small{font-size:14px;color:#52657a}.lead{font-size:21px}.notice{background:#fff3db;padding:16px;border-left:4px solid #cb941b}nav,.filters{display:flex;gap:16px;flex-wrap:wrap;margin:22px 0}section{margin:34px 0}a{color:#175da5}table{border-collapse:collapse;width:100%;background:white;margin:14px 0}td,th{border:1px solid #d8e0e9;text-align:left;vertical-align:top;padding:12px;overflow-wrap:anywhere}th{background:#edf2f8}table.outputs th{width:160px}.tablewrap{overflow:auto}details{background:white;border:1px solid #d8e0e9;border-radius:10px;padding:16px;margin:12px 0}summary{cursor:pointer;font-weight:650}summary small{margin-left:8px}details details{background:#fafbfd}dt{font-weight:700;margin-top:14px}dd{margin:4px 0}.labels{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}.labels span{background:#e8eff8;padding:2px 9px;border-radius:6px;font-size:13px}.diagnosis{border-left:4px solid #4384b2;padding:1px 18px;margin:16px 0}.flow{display:flex;align-items:center;gap:9px;flex-wrap:wrap}.flow span{padding:12px;background:#e4edf8;border-radius:8px}input,select{padding:10px;border:1px solid #bbc8d6;border-radius:6px;font:inherit}input{min-width:260px}code{font-size:12px;overflow-wrap:anywhere}li{margin:10px 0}hr{border:0;border-top:1px solid #dde5ed}@media(max-width:650px){main{padding:14px}h1{font-size:26px}td,th{padding:8px;font-size:14px}table.outputs th{width:95px}}'''
 js="const q=document.querySelector('#search'),f=document.querySelector('#filter'),cards=[...document.querySelectorAll('.case')];function update(){let n=0;for(const c of cards){const ok=c.dataset.search.toLowerCase().includes(q.value.toLowerCase())&&(f.value==='all'||c.dataset.tags.split(' ').includes(f.value));c.hidden=!ok;n+=ok;}document.querySelector('#count').textContent=n+' / 50 문장';}q.addEventListener('input',update);f.addEventListener('change',update);function reveal(){const c=document.getElementById(location.hash.slice(1));if(c?.classList.contains('case')){q.value='';f.value='all';update();c.open=true;}}window.addEventListener('hashchange',reveal);update();reveal();"
 (P/'report.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>50문장 정보 단절과 해결안</title><link rel="stylesheet" href="report.css"><main>'+h+'</main><script src="report.js"></script></html>',encoding='utf-8')
 (P/'report.css').write_text(css,encoding='utf-8');(P/'report.js').write_text(js,encoding='utf-8')
 print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
