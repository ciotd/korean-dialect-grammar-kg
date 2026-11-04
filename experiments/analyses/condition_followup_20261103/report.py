"""A readable report computed from frozen run records, never from guessed counts."""
from pathlib import Path
import json,html,collections,sys
H=Path(__file__).resolve().parent;R=H.parents[2]
sys.path.insert(0,str(R/'src'))
from research_management.core import Registry
from research_management.work import WorkStore
BASE='20261103T085736340654Z_research_loop_expanded50'
SMOKE='20261103T093319695026Z_research_loop_followup_diagnostic'
MODEL='20261103T093451123726Z_research_loop_followup50'
FINAL=json.loads((H/'private/latest_checked.json').read_text('utf8'))['run_id']
def read(p):return json.loads(p.read_text('utf8'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n','utf8')
def esc(x):return html.escape(str(x))
def table(head,rows):return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+esc(x)+'</th>' for x in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'
WHY={'auxiliary_structure_mismatch':'보조용언 연결과 형태 분석이 충돌','boundary_relation_unresolved':'절 연결을 확정하지 못함','adnominal_structure_mismatch':'관형절 관계와 형태 분석이 충돌','clause_connection_mismatch':'이어진 절 관계와 형태 분석이 충돌','auxiliary_class_unresolved':'보조용언의 동사·형용사 성격 미확정','question_scope_unresolved':'의문사 범위 미확정','question_owner_not_target_or_unknown':'의문사의 소속 절 미확정','internal_clause_alignment_unresolved':'한 어절 안 여러 구성의 분리가 미완성','multiple_boundaries_in_word_unresolved':'한 어절 안 여러 경계를 아직 따로 연결하지 못함','tense':'시간 의미 미확정','subject_honorific':'주체높임 판단 미확정'}
STATUS={'out_of_slice':'현재 지원 범위 밖','ready_for_generation_trial':'조건 통과 → 조합','needs_analysis':'분석 확인 필요','not_retrieved':'조회 전 중단'}
def main():
 runs={id:R/'experiments/runs'/id for id in (BASE,SMOKE,MODEL,FINAL)};reg=Registry(R);verification=[]
 for id,p in runs.items():
  reg.register(id);v=reg.verify(id);post=read(p/'postflight.json')
  assert v['status']=='passed' and all(post[k] for k in ('graph_unchanged','loaded_graph_matches_snapshot','code_unchanged','inputs_unchanged'))
  verification.append(dict(v,postflight=post))
 old=read(runs[BASE]/'private/results.json');new=read(runs[FINAL]/'private/results.json');metrics={id:read(p/'metrics.json') for id,p in runs.items()}
 assert [(x['id'],x['input_text']) for x in old]==[(x['id'],x['input_text']) for x in new]
 om={x['id']:x for x in old};nm={x['id']:x for x in new};cases=read(H/'private/six_cases.json');six=[];details=[];axes=collections.Counter();issues=collections.Counter()
 for row in new:
  for t in row['targets']:
   td=runs[FINAL]/'private/records'/row['id']/'targets'/t['target_id'];tr=read(td/'trace.json') if (td/'trace.json').exists() else {}
   errors=tr.get('diagnosis_axes',{}).get('structural_issues',[]);issues.update(t.get('needs_analysis',[]))
   states=tr.get('diagnosis_axes',{}).get('construction_states',{});alloutside=bool(states) and all(x=='out_of_slice' for x in states.values())
   axes[('范围外' if alloutside else '范围内或待定')+(' + 分析问题' if errors else ' + 无结构警告')]+=1
   d={'id':row['id'],'target_id':t['target_id'],'target_text':row['input_text'][slice(*t['span'])],'result':t,'construction_states':states,'analysis_issues':errors,'trace_path':str(td/'trace.json')};details.append(d)
 for c in cases:
  row=nm[c['id']];d=next(d for d in details if d['id']==c['id'] and d['target_id']==c['target_id']);td=runs[FINAL]/'private/records'/c['id']/'targets'/c['target_id']
  raw=read(td/'analysis_call/parsed.json') if (td/'analysis_call/parsed.json').exists() else read(td/'analysis_reused.json')['parsed'] if (td/'analysis_reused.json').exists() else None
  six.append({'id':c['id'],'target_id':c['target_id'],'surface':d['target_text'],'before':c['result'],'after':d,'new_model_answer':raw,'old_model_answer':c['raw']})
 deltas=[{'id':x['id'],'input':x['input_text'],'before':om[x['id']]['output_text'],'after':x['output_text']} for x in new if om[x['id']]['output_text']!=x['output_text']]
 preserved=[x['id'] for x in old if x.get('generated_targets') and nm[x['id']]['output_text']==x['output_text']]
 summary={'baseline':BASE,'final':FINAL,'metrics':metrics,'six_case_diagnosis':six,'output_differences':deltas,'old_generated_sentences_preserved':preserved,'analysis_issues_including_unknown_features':dict(issues),'verified_files':sum(x['checked_files'] for x in verification),'quality':'not_evaluated','new_grammar_rules':0}
 save(H/'private/summary.json',summary);save(H/'private/validation.json',verification);save(H/'private/all_targets.json',details)
 g=read(runs[FINAL]/'private/graph.json');ns={n['id']:n for n in g['nodes']};maps=[{'feature':n['properties']['feature'],'allowed':n['properties']['allowed'],'evidence_ids':n['properties'].get('evidence_ids',[]),'kind':n['properties']['basis']} for n in g['nodes'] if n['id'].startswith('COND_DECL_')]
 metricrows=[]
 for label,id in [('직전 50건',BASE),('이번 새 Qwen 답변',MODEL),('검사 누락 보완 후 같은 답변 재사용',FINAL)]:
  m=metrics[id];metricrows.append([label,m['records'],m['analysis_calls'],m['changed_records'],m['actual_generated_outputs'],m['generation_failures'],m['wall_seconds'],m['reported_usage']['total_tokens']])
 sixrows=[]
 explanations={('ADVCE002A','W4'):'계세요를 계+이다로 나눈 형태 분석 문제는 남아 있음. 현재 -세요 생성도 미지원.',('DEV021','W3'):'보조용언 성격을 모르더라도, 알려진 요청 기능으로 미지원 여부를 조회. 과거에는 조회 전 중단.',('LONG002','W7'):'사 온의 안쪽 연결과 온 사과의 관형 관계를 구별하는지 확인.',('LONG002','W13'):'보기에는의 명사화 관계 확인. 회상 종결 -더라는 여전히 미지원.',('NEW007','W7'):'있을 테니까의 관형 관계와 보조용언 관계를 구별. 명령형 생성은 미지원.',('QUAL002','W15'):'배움의의 명사화와 뒤 명사를 꾸미는 역할을 구별. 거예요 계사 생성은 미지원.'}
 for x in six:
  a=x['after'];t=a['result'];sixrows.append([x['id']+' / '+x['surface'],STATUS.get(x['before'].get('readiness','not_retrieved'),x['before'].get('readiness')),STATUS.get(t.get('readiness','not_retrieved'),t.get('readiness')),', '.join(WHY.get(i,i) for i in a['analysis_issues']) or '구조 경고 없음 — 의미 정답 인증은 아님',explanations[(x['id'],x['target_id'])]])
 provenance=[]
 for x in maps:
  sources=[ns[i]['properties']['document_id']+' PDF '+str(ns[i]['properties']['pdf_page']) for i in x['evidence_ids']]
  provenance.append([{'source_final':'입력 종결어미','speech_act':'문장의 기능','prefinal_sequence':'선어말 지원 범위'}[x['feature']],', '.join(x['allowed']),'; '.join(dict.fromkeys(sources)) or '문헌의 닫힌 허용목록 아님',{'implementation_scope':'이번 실험의 선택','source_interpretation_with_analyzer_mapping':'문헌 용례 + 분석기 형태 대응','source_classification_with_label_interpretation':'문헌 분류 + 모델 답변 항목의 대응'}[x['kind']]])
 doc='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>분석 6곳 보완과 50문장 재확인</title><style>body{font:17px/1.65 system-ui,"Malgun Gothic",sans-serif;background:#f4f6fa;color:#253046;max-width:1240px;margin:auto;padding:24px}section{background:white;border:1px solid #dce3ed;border-radius:12px;padding:24px;margin:20px 0}h1{font-size:30px}h2{font-size:23px}table{width:100%;border-collapse:collapse;font-size:14px}th,td{padding:11px;border:1px solid #dce3ed;text-align:left;vertical-align:top}th{background:#eef3fa}.scroll{overflow:auto}.note{background:#fff4d9;padding:13px;border-radius:8px}.flow{display:flex;gap:8px;flex-wrap:wrap}.flow span{background:#eaf1fb;padding:12px;border-radius:8px}summary{cursor:pointer;color:#205da4}a{color:#205da4}nav a{margin-right:18px}input{font:inherit;padding:9px;width:min(80%,500px)}.big{font-size:23px;font-weight:bold}footer{font-size:13px;color:#5d6c7f}details{margin-top:10px}button{padding:8px}</style><h1>분석 6곳 보완과 50문장 재확인</h1><p>2026-11-03 · 실제 실행 기록을 기준으로 정리</p><nav><a href="#answer">결론</a><a href="#six">6곳 확인</a><a href="#kg">KG 근거</a><a href="#all">50문장</a><a href="#next">다음 작업</a></nav>'''
 m=metrics[FINAL]
 doc+='<section id="answer"><h2>이번에 한 일</h2><p class="big">Qwen에게 절 연결을 더 구체적으로 묻고, 멈춘 이유를 두 갈래로 나눴습니다.</p><div class="flow"><span>Kiwi: 실제 형태와 위치</span>→<span>Qwen: 각 경계의 뜻·연결</span>→<span>KG: 조건 일치 여부</span>→<span>조합기: 최종 문장</span></div><p><b>문법을 아직 지원하지 않는 것</b>과 <b>분석이 불확실한 것</b>을 구별합니다. 둘은 한 문장에서 함께 발생할 수 있습니다. 문헌을 인용한 조건과 우리가 정한 실험 범위도 따로 연결했습니다.</p>'+table(['실행','입력','Qwen 분석','바뀐 문장','조합 위치','조합 실패','초','총 토큰'],metricrows)+'<p class="note">새 Qwen 답변에서는 15문장·16위치가 변환됐습니다. 검토에서 검사 누락 2곳을 발견해 보완한 뒤, 같은 답변으로 다시 처리한 최종 결과는 13문장·14위치입니다. 두 출력이 틀렸다고 확정한 것은 아니며, 복수 경계 연결을 충분히 확인하지 못해 보류했습니다. 변환된 문장 수는 자연스러움 점수가 아닙니다. 이번에는 Qwen이 분석하고 조합기가 생성했습니다. Qwen 생성 API 호출은 0회입니다. 새 문법 규칙도 0개입니다.</p><p>직전 출력과 달라진 문장: '+str(len(deltas))+'개. 직전 일부 변환된 14문장 중 최종 검사 후 출력이 그대로 유지된 문장: '+str(len(preserved))+'개.</p>'+table(['ID','직전 출력','이번 출력'],[[x['id'],x['before'],x['after']] for x in deltas])+'</section>'
 doc+='<section id="six"><h2>막혔던 6곳은 같은 문제가 아니었습니다</h2><p>6곳은 <b>5개 입력 문장 안의 6개 위치</b>입니다. 기존 문법으로 추가 변환을 기대할 수 있었던 것은 LONG002의 봤어 한 곳이었습니다. 나머지는 분석을 고쳐도 현재 문법 지원 밖입니다.</p>'+table(['입력 / 위치','직전 표시','이번 표시','이번 분석 경고','해석'],sixrows)+'<p>원래 기록은 보존했습니다. 주세요는 과거에 조회한 것처럼 다시 쓰지 않고, 이번 실행에서 실제 조회한 결과를 별도로 남겼습니다.</p><details><summary>질문을 어떻게 바꿨나</summary><p>이전에는 모든 위치에 같은 관계 목록을 주었습니다. 이번에는 관찰된 형태에 맞춰 후보를 나눕니다. 관형사형 어미에는 관형 관계, 명사형 어미에는 명사화 관계를 묻고, 연결어미에는 연결·보조용언·인용 등을 묻습니다. 모르면 unknown을 답할 수 있습니다.</p><p>의도한 질문은 사→온의 내부 연결과 온→사과의 관형 관계를 구별하는 것입니다. 실제 Qwen은 사→온을 보조용언이 아닌 일반 연결(linked)로 답했습니다. 기존의 잘못된 관형 분류는 사라졌지만 의미 관계까지 정확해졌다고 인증할 수 없습니다. 이 예문 정답을 모델 요청에 넣은 것이 아니라, 모든 문장에 같은 경계 질문 형식을 적용했습니다. Kiwi가 형태를 잘못 나누면 이 방식만으로 해결할 수 없습니다.</p><p>검사에서 손으로 연결을 고친 경우와 Qwen이 새로 답한 경우는 별도 기록입니다. 테스트용 정답을 실제 처리에 주입하지 않았습니다.</p></details></section>'
 doc+='<section id="kg"><h2>KG에서 무엇이 달라졌나</h2><p>새 방언 지식을 늘린 작업은 아닙니다. 기존 평서 조건 6개의 <b>근거와 작성 이유</b>를 드러냈습니다. 실제 허용값·규칙·실현형은 이전과 같습니다.</p>'+table(['조건','현재 값','문헌 위치','이 값의 성격'],provenance)+'<p>인용 표기: D02 PDF75는 각주70의 사전 재인용이며, PDF203의 아/어요 빈도 행은 표48입니다. 네요·거든요 입력 목록은 표47입니다.</p><p>KG: '+str(len(g['nodes']))+'개 노드 / '+str(len(g['edges']))+'개 관계. 문헌 분류와 우리가 붙인 분석 라벨의 연결은 ‘원문 해석’, 선어말 4종만 지원하는 결정은 ‘구현 범위’로 구분했습니다. D02 PDF201의 서술법 높임 설명도 정확한 인용 위치와 함께 연결했습니다.</p><details><summary>실제 관계 이름과 출처</summary><p>Condition → INTERPRETS_SOURCE → Evidence: 원문을 현재 분석 조건으로 해석한 연결.<br>Condition → DEFINED_BY_DECISION → ImplementationDecision: 구현 선택 이유.<br>Rule → PRESERVATION_SUPPORTED_BY → Evidence: 높임 보존의 보조 근거.</p><p>새 Qwen 실행은 KG r3를 사용했습니다. 검토 후 근거 역할과 인용 범위를 보완한 r4는 같은 62개 답변으로 조회 결과가 유지됨을 확인했습니다. 새 해석 관계는 조회의 허용값을 바꾸지 않으며, 실행 trace의 condition_provenance에서 별도로 확인할 수 있습니다. JSON 그래프를 사용한 실험이며 Neo4j 실DB를 새로 적재한 것은 아닙니다.</p></details></section>'
 doc+='<section id="all"><h2>50문장 전체 결과</h2><p>입력 원문과 이전 결과는 바꾸지 않았습니다. 검색하면 해당 문장만 볼 수 있습니다.</p><input id="search" placeholder="ID 또는 문장 검색"><span id="count"></span><div class="scroll"><table id="cases"><thead><tr><th>ID</th><th>표준어 입력</th><th>직전 출력</th><th>이번 출력 / 이유</th></tr></thead><tbody>'
 for row in new:
  ts=[x for x in details if x['id']==row['id']];trs=[]
  for t in ts:
   result=t['result'];trs.append([t['target_text'],STATUS.get(result.get('readiness','not_retrieved'),result.get('readiness')),', '.join(WHY.get(x,x) for x in result.get('needs_analysis',[])) or '없음',', '.join(result.get('rules',[])) or '선택 없음'])
  doc+='<tr><td>'+esc(row['id'])+'</td><td>'+esc(row['input_text'])+'</td><td>'+esc(om[row['id']]['output_text'])+'</td><td><b>'+esc(row['output_text'])+'</b><details><summary>위치별 결과</summary>'+table(['위치','처리','분석 경고','조회 규칙'],trs)+'</details></td></tr>'
 doc+='</tbody></table></div></section><section id="next"><h2>남은 문제와 다음 순서</h2>'+table(['순서','할 일','끝났다고 판단할 기준'],[['1','한 어절 안 경계를 각각 묻도록 분석 계약을 보완. 선정해가지고·높아지는의 누락을 해결하고, 사→온 관계도 점검. 계세요 형태 충돌은 별도 확인.','누락된 연결이 드러나고, 잘못된 연결을 막으며, 지원하는 종결형으로 연결되는지 확인'],['2','명사+이다 평서·높임 묶음부터 다음 지원 범위를 합의하고 원문 정제','문헌 근거 → 조건 조회 → 조합 결과가 새 예문에서도 연결'],['3','일반 평서·약속·명령을 묶음별로 확대','묶음마다 지원·미지원과 오류를 분리하여 기존50 + 별도 개발 사례 검사'],['4','지원 범위가 늘어난 뒤 자연스러움 평가','사용자가 실제 출력의 뜻·높임·말투를 확인']])+'<p>이번 단계에서는 2–3의 새 문법을 추가하지 않았습니다. 현재 결과만으로 현대 경상도 표현이 자연스럽다고 결론낼 수 없습니다. 우선 연결 누락을 표현할 수 있게 고치는 것이 다음 순서이며, 미지원 문법을 늘리는 것과 분리하겠습니다.</p></section><section><h2>검토와 검증 기록</h2><p>새 구현 검사12건과 기존 검사29건을 통과했습니다. 구조진단12건, 기존50건을 새 Qwen 호출로 실행했습니다. 그 뒤 검사 누락을 수정하고 저장된62개 답변을 재사용했습니다. 마지막 재검사는 모델 호출0회이며, 같은 응답·같은 문법 조건에서 검사 변경만 확인했습니다. 과거 결과와 새 실행의 파일 해시를 확인했습니다.</p><ul>'
 for who,label in [('codex','Codex: 구조·코드'),('claude','Claude: 문헌·해석')]:
  for fn,name in [('review.md','계획 검토'),('implementation_review.md','구현 검토'),('confirmation.md','수정 확인')]:
   if (H/'private/reviewers'/who/fn).exists():doc+='<li><a href="reviewers/'+who+'/'+fn+'">'+label+' / '+name+'</a></li>'
 doc+='</ul><p>Codex가 발견한 복수 경계 검사 누락과 Claude가 발견한 출처 역할 혼동을 수정하고, 각각 반영 확인을 받았습니다. Claude의 EC→nominal 일괄 금지 제안은 품사와 절 기능이 다른 층위이므로 채택하지 않았고, 검토자도 철회했습니다.</p><p><a href="reviewer_resolution.json">의견별 처리</a> · <a href="summary.json">계산 원본</a> · <a href="all_targets.json">62위치 처리 기록</a> · <a href="validation.json">파일 검증 결과</a></p><p>기존 50건은 오류 분석에 사용한 회귀 검사셋입니다. 독립 평가셋이 아닙니다. 직전 실행과 이번 Qwen 실행은 새 답변이므로 단일 변경의 인과 효과를 단정하지 않습니다. 마지막 검사 보완 전후만 같은62개 답변을 고정했습니다. 모델 서버의 내부 버전은 노출되지 않았습니다.</p></section><footer>최종 Run ID: '+FINAL+'<br>파일 검증 '+str(summary['verified_files'])+'개 · 해시 불일치 0</footer><script>function filter(){let q=document.getElementById("search").value.toLowerCase(),n=0;document.querySelectorAll("#cases>tbody>tr").forEach(r=>{r.hidden=!r.textContent.toLowerCase().includes(q);if(!r.hidden)n++});document.getElementById("count").textContent=" "+n+" / 50"}document.getElementById("search").addEventListener("input",filter);filter();</script></html>'
 (H/'private/report.html').write_text(doc,'utf8')
 navp=R/'experiments/management/report_navigation.json';nav=read(navp);url=(H/'private/report.html').as_uri();nav=[x for x in nav if x.get('url')!=url];nav.append({'title':'34 · 분석6곳 보완·조건 근거·50문장 재확인','url':url,'summary':f"기존 문법 범위 유지. 50건 중{m['changed_records']}문장 일부변환. 분석문제와 미지원 구별, 조건6개 근거·구현결정 분리."});save(navp,nav)
 print(json.dumps({'metrics':m,'differences':deltas,'old_generated_preserved':len(preserved),'analysis_issues_including_unknown_features':dict(issues),'verified_files':summary['verified_files']},ensure_ascii=False))
if __name__=='__main__':main()
