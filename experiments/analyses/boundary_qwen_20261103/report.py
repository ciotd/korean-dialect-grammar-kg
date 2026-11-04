"""Summarize actual Qwen outputs and per-boundary graph traces without quality scores."""
from pathlib import Path
import json,html,collections,sys
H=Path(__file__).resolve().parent;R=H.parents[2];sys.path.insert(0,str(R/'src'))
from research_management.core import Registry
def read(p):return json.loads(p.read_text('utf8'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n','utf8')
def e(x):return html.escape(str(x))
def table(head,rows):return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+e(x)+'</th>' for x in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+e(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def main():
 final=Path(read(H/'private/latest_full50.json')['directory']);reg=Registry(R)
 dirs=sorted((R/'experiments/runs').glob('*_boundary_qwen_*'));runs=[];checks=[]
 for p in dirs:
  if not (p/'metrics.json').exists():continue
  reg.register(p.name);v=reg.verify(p.name);post=read(p/'postflight.json');assert v['status']=='passed' and all(post[k] for k in ('graph_unchanged','code_unchanged','inputs_unchanged'))
  runs.append({'run_id':p.name,'metrics':read(p/'metrics.json')});checks.append(v)
 rows=read(final/'private/results.json');metrics=read(final/'metrics.json');basepath=R/'experiments/runs/20261103T094439414985Z_condition_checked_replay50';baseline=read(basepath/'private/results.json');bm={x['id']:x for x in baseline}
 assert [(x['id'],x['input_text']) for x in rows]==[(x['id'],x['input_text']) for x in baseline]
 targetrows=[];diff=[];records_with_actions=0;all_outputs_qwen=True;issues=collections.Counter();changed_without_actions=[];unchanged_with_actions=[]
 for row in rows:
  folder=final/'private/records'/row['id'];packet=read(folder/'generation_packet.json');actions=packet['actions'];records_with_actions+=bool(actions)
  request=read(folder/'generation_call/request.json')
  assert json.loads(request['messages'][-1]['content'])==packet
  responsefile=folder/'generation_call/parsed.json';response=read(responsefile) if responsefile.exists() else None
  all_outputs_qwen &= response is None and row['output_text'] is None or response is not None and row['output_text']==response['output_text']
  assert all('expected_surface' not in a and 'composer_comparison' not in a for a in actions)
  if not actions and row['output_text'] is not None and row['output_text']!=row['input_text']:changed_without_actions.append(row['id'])
  if actions and row['output_text']==row['input_text']:unchanged_with_actions.append(row['id'])
  for t in row['targets']:
   td=folder/'targets'/t['target_id'];tr=read(td/'trace.json') if (td/'trace.json').exists() else None
   a=read(td/'analysis.json') if (td/'analysis.json').exists() else None
   issues.update(t.get('needs_analysis',[]));piece=next((x for x in row.get('checks',{}).get('pieces',[]) if x['target_id']==t['target_id']),None)
   comp=read(td/'composer_comparison.json') if (td/'composer_comparison.json').exists() else None
   if comp and piece and comp.get('piece')!=piece['replacement']:diff.append({'id':row['id'],'target_id':t['target_id'],'input':row['input_text'][slice(*t['span'])],'qwen':piece['replacement'],'composer_comparison':comp.get('piece'),'warnings':piece['warnings']})
   targetrows.append({'id':row['id'],'target_id':t['target_id'],'text':row['input_text'][slice(*t['span'])],'result':t,'boundaries':a.get('scope_links',{}).get('edges',[]) if a else [],'trace_path':str(td/'trace.json'),'composer_comparison':comp,'qwen_piece':piece})
 assert all_outputs_qwen
 summary={'run_id':final.name,'metrics':metrics,'records_with_kg_actions':records_with_actions,'generation_calls_without_actions':metrics['generation_calls']-records_with_actions,'all_final_outputs_equal_qwen_raw':all_outputs_qwen,'composer_completed_forms_not_in_model_payload':True,'changed_without_actions':changed_without_actions,'unchanged_with_actions':unchanged_with_actions,'analysis_issues':dict(issues),'composer_differences':diff,'verified_files':sum(v['checked_files'] for v in checks),'quality':'not_scored; source/meaning/naturalness need separate evaluation'}
 save(H/'private/summary.json',summary);save(H/'private/all_targets.json',targetrows);save(H/'private/validation.json',checks)
 findings=[]
 for ids,meaning,next_step in [
  (['LONG001'],'어간 오-를 전달했으나 Qwen이 와를 노만으로 바꿔 동사를 빠뜨림. 누락은 생성 단계에서 확인됨.','같은 분석·KG를 고정하고 어간 보존 지시 및 Qwen 재검사를 비교'),
  (['ADVCE006A','ADVCE006B'],'었과 past를 전달했으나 설명했어요를 설명해예로 생성. 과거형 보존 지시를 따르지 않음.','같은 정보로 전달 형식만 비교하고 다른 과거형 개발 문장에서도 검사'),
  (['QUAL003'],'같아요를 같어예로 생성. 문헌의 해체+예 결합 설명과 대조할 후보. 자동 경고만으로 모든 지역의 비문이라 단정하지 않음.','결합 설명의 충분성을 검토하고 생성 지시 문제와 구별'),
  (['ADVCE005B','QUAL020'],'도와예·들었어예에 어간 경고 발생. Kiwi의 방언 분석 차이일 수 있어 경고만으로 번역 오류를 판정할 수 없음.','원형·선어말 보존을 대조하여 검사기의 오경고 여부 확인')]:
  for ident in ids:
   row=next(x for x in rows if x['id']==ident);packet=read(final/'private/records'/ident/'generation_packet.json')
   findings.append({'id':ident,'input':row['input_text'],'output':row['output_text'],'actual_delivered_actions':packet['actions'],'finding':meaning,'next_check':next_step,'author':'lead_analysis_of_saved_requests_and_outputs','not_independent_quality_score':True})
 save(H/'private/representative_findings.json',findings)
 status={'ready_for_generation_trial':'KG 정보 전달 가능','out_of_slice':'현재 KG 지원 밖','needs_analysis':'분석 확인 필요','not_delivered':'분석·조회 오류'}
 rel={'auxiliary':'보조용언 연결','linked':'이어짐·부사절','nominal':'명사화·안긴절','adnominal':'명사 꾸밈','quoted':'인용','unknown':'미확정'}
 doc='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>KG 정보를 받은 Qwen의 최종 문장 생성</title><style>body{font:17px/1.65 system-ui,"Malgun Gothic",sans-serif;max-width:1280px;margin:auto;padding:24px;background:#f4f7fa;color:#203047}h1{font-size:30px}h2{font-size:23px}section{padding:24px;background:white;border:1px solid #dbe2eb;border-radius:12px;margin:20px 0}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:11px;border:1px solid #dbe2eb;text-align:left;vertical-align:top}th{background:#eaf1fa}.flow{display:flex;gap:8px;flex-wrap:wrap}.flow span{background:#e7f0fc;padding:12px;border-radius:8px}.note{background:#fff3d5;padding:15px;border-radius:8px}.big{font-size:23px;font-weight:bold}a,summary{color:#1e5ca4}summary{cursor:pointer;padding:8px}input,select{font:inherit;padding:8px;margin:6px}nav a{margin-right:14px}footer{font-size:13px;color:#536174}</style><h1>KG 정보를 받은 Qwen의 최종 문장 생성</h1><p>2026-11-03 · 기존 50문장 · 원본 출력과 실패 기록 보존</p><nav><a href="#result">결과</a><a href="#how">어떻게 연결했나</a><a href="#all">50문장</a><a href="#errors">남은 문제</a><a href="#next">다음 순서</a></nav>'''
 doc+='<section id="result"><h2>최종 문장은 Qwen이 썼습니다</h2><div class="flow"><span>표준어</span>→<span>Kiwi 위치 + Qwen 의미·연결</span>→<span>KG 조건 조회</span>→<span>핵심 정보 전달</span>→<span>Qwen 전체 문장 생성</span></div><p>조합기는 옆에서 비교용 어절을 만들 뿐입니다. 그 완성형을 Qwen에 주거나 최종 출력을 대신 쓰지 않았습니다. 모든 최종 출력이 저장된 Qwen 응답과 같은지 확인했습니다.</p>'+table(['확인 항목','실제 결과'],[['Qwen 분석 호출',metrics['analysis_calls']],['Qwen 전체 문장 생성 호출',metrics['generation_calls']],['KG 적용 정보가 전달된 입력',f'{records_with_actions}/50'],['KG 적용 정보 없이 생성한 입력',metrics['generation_calls']-records_with_actions],['원문과 달라진 출력',f"{metrics['changed_records']}/50"],['Qwen 출력이 보존된 입력',metrics['valid_output_records']],['실행 시간',str(metrics['wall_seconds'])+'초'],['서버 보고 총 토큰',metrics['reported_usage']['total_tokens']]])+'<p class="note">문장이 바뀌었다고 자연스러운 것은 아닙니다. KG 적용 정보가 없는 경우에는 원문을 유지하도록 Qwen에 지시했습니다. 일부 종결형만 지원하는 현재 KG로 문장 전체의 어휘·말투까지 바꾸는 실험은 아닙니다.</p></section>'
 doc+='<section id="how"><h2>이번에 고친 부분</h2>'+table(['이전 문제','수정','검사'],[['한 어절 안 연결을 하나로 기록','모든 EC·ETM·ETN에 형태소 순번 ID 부여','선정해가지고의 두 EC, 높아지는의 EC와 ETM 분리'],['어절 번호와 형태소 번호 혼용','답변 칸마다 허용 ID를 지정','실제 개발 실패11건의 원인 재현·차단'],['보조용언 관계를 다른 이름으로 우회','관계와 연결 대상이 함께 맞는 응답 형식','nominal→인접 VX 우회 차단, 원거리 명시 사슬 유지·인접 VX 건너뛰기 차단'],['질문 소속을 중복 판단하며 충돌','의문사 소속 용언을 한 번 답하고 연결 사슬과 대조','판정 질문의 불필요한 scope 충돌 제거'],['생성 실패·검사 오류가 결과를 가림','원본 Qwen 응답 먼저 보존, 검사는 별도 경고','검사 예외가 나도 출력 보존'],['KG 결합 설명 누락','실제 형태·조건·결합형·구조 설명 전달','완성형 정답·조합기 답 미전달']])+'<p>KG r4의 규칙과 허용값은 바꾸지 않았습니다. 같은 공통 문법 구조를 사용하고 조회·전달·생성 경로를 수정했습니다. Neo4j 실DB 재적재는 하지 않았습니다.</p><details><summary>KG에서 Qwen으로 전달한 항목</summary><p>바꿀 위치와 원문 어절, 실제 형태소, 어간·선어말·종결어미, 규칙 ID와 뜻, 선택된 결합형, 조건별 관찰값, 보존할 내용, KG 결합 설명과 구조 근거. 긴 KG 전체나 Claude 정답 문장은 전달하지 않습니다.</p></details></section>'
 doc+='<section><h2>개발 중 실패도 남겼습니다</h2>'+table(['실행 ID','입력','분석 호출','생성 호출','바뀐 문장','분석·조회 실패','시간(초)'],[[x['run_id'],x['metrics']['records'],x['metrics']['analysis_calls'],x['metrics']['generation_calls'],x['metrics']['changed_records'],x['metrics']['target_status_counts'].get('analysis_or_query_failed',0),x['metrics']['wall_seconds']] for x in runs])+'<p>개발12건은 이번에 별도로 만든 검사 예문입니다. 같은12건을 수정 후 다시 실행했고, 각 실행을 덮어쓰지 않았습니다. 개발 변경은 오류 원인을 확인하기 위한 것이며 성능 점수로 발표하지 않습니다. 기존50건은 회귀 검사셋입니다.</p></section>'
 # Worked example uses an actual multiple-boundary record when available.
 for id in ('QUAL003','QUAL020','LONG002'):
  row=next(x for x in rows if x['id']==id);folder=final/'private/records'/id;packet=read(folder/'generation_packet.json');trs=[t for t in targetrows if t['id']==id]
  w=[]
  for t in trs:
   target=read(folder/'targets'/t['target_id']/'target.json');m=target['morph'];lookup={f"{word['uid']}:M{i}":form for word in m['words'] for i,(form,tag) in enumerate(word['morphs'])}
   for edge in t['boundaries']:w.append([edge['boundary_id'],lookup.get(edge['source_host'],edge['source_host']),rel.get(edge['relation'],edge['relation']),lookup.get(edge['head_id'],edge['head_id'])])
  doc+='<section><h2>실제 추적: '+id+'</h2><p><b>입력:</b> '+e(row['input_text'])+'</p>'+table(['경계 ID','연결 시작','Qwen이 답한 관계','연결 대상'],w)+'<p><b>Qwen에 전달한 규칙:</b> '+e(', '.join(a['rule_id'] for a in packet['actions']) or '없음 — 아래 위치별 결과에서 이유 확인')+'</p><p><b>최종 Qwen 출력:</b> '+e(row['output_text'])+'</p><p>이 관계 표는 모델의 답입니다. 참조·형식 검사를 통과했어도 의미 분석의 정답 인증은 아닙니다.</p></section>'
 doc+='<section id="all"><h2>50문장 전체 비교</h2><input id="search" placeholder="ID 또는 문장 검색"><select id="filter"><option value="">전체</option><option value="changed">원문과 다름</option><option value="same">원문 유지</option><option value="warning">자동 경고 있음</option></select><span id="count"></span><div class="scroll"><table id="cases"><thead><tr><th>ID</th><th>표준어 원문</th><th>직전 조합기 출력</th><th>이번 Qwen 최종 출력</th></tr></thead><tbody>'
 for row in rows:
  st='same' if row.get('output_text')==row['input_text'] else 'changed';warnings=row.get('checks',{}).get('warnings',[])
  details=[]
  for t in row['targets']:details.append([row['input_text'][slice(*t['span'])],status.get(t.get('readiness'),t.get('status')),', '.join(t.get('rules',[])) or '없음',', '.join(t.get('needs_analysis',[])) or t.get('error','없음')])
  doc+='<tr data-state="'+st+'" data-warning="'+('yes' if warnings else 'no')+'"><td>'+e(row['id'])+'</td><td>'+e(row['input_text'])+'</td><td>'+e(bm[row['id']]['output_text'])+'</td><td><b>'+e(row.get('output_text'))+'</b><details><summary>조회·전달·경고 확인</summary>'+table(['대상','준비 상태','규칙','미확정·오류'],details)+'<p>생성 후 자동 경고: '+e(', '.join(warnings) or '없음 — 자연스러움 합격이라는 뜻은 아님')+'</p></details></td></tr>'
 doc+='</tbody></table></div><p>직전 실행과 분석 형식·생성 주체가 함께 달라졌습니다. 이 비교를 Qwen 대 조합기의 통제된 우열 비교로 해석할 수 없습니다.</p></section>'
 doc+='<section id="errors"><h2>어디가 아직 문제인가</h2>'+table(['위치 상태','수'],[[status.get(k,k),v] for k,v in metrics['readiness_counts'].items()])+table(['자동 경고 — 정답 판정 아님','문장 수'],list(metrics['warning_counts'].items()))+'<details open><summary>Qwen과 보조 조합기의 어절이 다른 사례</summary>'+table(['입력 ID','원문 어절','Qwen','보조 조합기','경고'],[[x['id'],x['input'],x['qwen'],x['composer_comparison'],', '.join(x['warnings'])] for x in diff])+'</details><p>보조 조합기의 답이 유일한 정답이라는 뜻은 아닙니다. 실제 전달 정보가 같아도 생성이 달라지는 위치를 찾는 자료입니다.</p><p>개발 사례에서 확인한 의미 판단 한계: “누가 왔는지 알아?”를 바깥 의문사 질문으로 잘못 분류할 수 있고, “주무시다”의 어휘적 높임은 -시- 형태 검사만으로 확인되지 않습니다. 현재 unknown 경계는 보수적으로 보류하며, 목표와 무관하다고 자동 간주하여 제거하지 않았습니다.</p></section>'
 doc+='<section><h2>실제 요청과 출력에서 확인한 문제</h2>'+table(['ID','Qwen 출력','문제 위치와 근거','다음 확인'],[[x['id'],x['output'],x['finding'],x['next_check']] for x in findings])+'<p><a href="representative_findings.json">실제 전달 항목과 판단 근거</a> · 이 표는 생성 단계의 구체적 위반과 검사기의 의심 경고를 구분합니다. 전체 오류를 확정했다는 뜻은 아닙니다.</p></section>'
 doc+='<section id="next"><h2>다음 작업과 종료 기준</h2>'+table(['순서','작업','종료 기준'],[['1','이번50건에서 분석이 틀린 곳과, 맞는 정보를 받고도 생성이 어긋난 곳을 분리','원문·Qwen 분석·조회 규칙·실제 생성 요청·출력이 한 줄로 대조됨'],['2','생성 문제는 같은 분석과 KG 정보를 고정해 전달 방식만 비교','정답 문장을 넣지 않고도 형태 보존이 나아지는지 확인'],['3','분석 문제는 의문사 소속·어휘 높임 등을 별도 개발 사례로 점검','오류와 정상 대조 사례를 모두 처리하고 불명확한 것은 기록'],['이후','명사+이다 평서·높임 등 다음 KG 범위를 합의해 확대','문헌 근거·조건 조회·Qwen 생성까지 연결']])+'<p>이번에 실제로 완료한 범위는 개별 경계 표현, Qwen 최종 생성 연결, 개발 검증, 기존50 실행입니다. 문법 전체 정제와 자연스러움 검증은 완료하지 않았습니다.</p></section><section><h2>검토와 재현 자료</h2><p>코드 검사17건 통과. 기존 Orca Codex와 Claude가 코드와 개발 결과를 독립 검토했습니다. 이번 최종50건 출력의 독립 평가까지 수행한 것은 아닙니다. 결과 파일·코드·KG·요청·응답을 고유 실행 ID로 보존했습니다.</p><ul>'
 for who in ('codex','claude'):
  for fn in ('review.md','confirmation.md','final_confirmation.md'):
   if (H/'private/reviewers'/who/fn).exists():doc+='<li><a href="reviewers/'+who+'/'+fn+'">'+who+' '+('검토' if fn=='review.md' else '수정 확인')+'</a></li>'
 doc+='</ul><p><a href="summary.json">집계 원본</a> · <a href="all_targets.json">위치별 추적 원본</a> · <a href="validation.json">파일 검증</a></p></section><footer>Run ID: '+final.name+'<br>검증 파일 '+str(summary['verified_files'])+'개 · 원본 해시 불일치0 · 자연스러움 미평가</footer><script>function filterRows(){let q=document.getElementById("search").value.toLowerCase(),f=document.getElementById("filter").value,n=0;document.querySelectorAll("#cases>tbody>tr").forEach(r=>{let ok=r.textContent.toLowerCase().includes(q)&&(!f||(f==="warning"?r.dataset.warning==="yes":r.dataset.state===f));r.hidden=!ok;if(ok)n++});document.getElementById("count").textContent=n+" / 50"}document.getElementById("search").addEventListener("input",filterRows);document.getElementById("filter").addEventListener("change",filterRows);filterRows();</script></html>'
 (H/'private/report.html').write_text(doc,'utf8');navp=R/'experiments/management/report_navigation.json';nav=read(navp);url=(H/'private/report.html').as_uri();nav=[x for x in nav if x.get('url')!=url];nav.append({'title':'35 · 개별 경계 분석과 Qwen 최종 생성50','url':url,'summary':f"Qwen 최종 생성 {metrics['generation_calls']}회. KG정보 전달 {records_with_actions}/50. 원문·직전조합기·Qwen출력 비교와 단계별 진단."});save(navp,nav)
 print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
