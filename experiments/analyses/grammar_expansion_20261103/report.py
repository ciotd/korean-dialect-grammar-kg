"""Build the consolidated report from immutable run artifacts."""
import json,html,collections,csv,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'src'))
from research_management.core import Registry

def read(p):return json.loads(p.read_text('utf8'))
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n','utf8')
def e(x):return html.escape(str(x))
def table(head,rows):return '<table><thead><tr>'+''.join('<th>'+e(x)+'</th>' for x in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table>'
IDS=['20261103T083454291199Z_research_loop_composer50','20261103T084100993596Z_research_loop_scoped50','20261103T084710388022Z_research_loop_expanded_diagnostic','20261103T084849689062Z_research_loop_expanded50','20261103T085447920775Z_research_loop_expanded_diagnostic','20261103T085702848303Z_research_loop_expanded_diagnostic','20261103T085736340654Z_research_loop_expanded50']
NAMES=['① 조합기 연결','② 절·보조용언 첫 연결','구조 점검 12건 · KG r1','③ 평서 확장 · KG r1','검토 수정 · KG r2 / 12건','최종 코드 · 12건','최종 코드 · 기존 50건']
def main():
 reg=Registry(ROOT);runs=[];ver=[]
 for id in IDS:
  p=ROOT/'experiments/runs'/id;reg.register(id);v=reg.verify(id);post=read(p/'postflight.json')
  assert v['status']=='passed' and all(post[k] for k in ('graph_unchanged','loaded_graph_matches_snapshot','code_unchanged','inputs_unchanged'))
  runs.append({'id':id,'config':read(p/'config.json'),'metrics':read(p/'metrics.json'),'results':read(p/'private/results.json')});ver.append({**v,'postflight':post})
 final=runs[-1];rows=final['results'];base={r['id']:r for r in runs[0]['results']};targets=[t for r in rows for t in r['targets']]
 for run in [runs[1],runs[3],final]:assert [(r['id'],r['input_text']) for r in run['results']]==[(r['id'],r['input_text']) for r in runs[0]['results']]
 issues=collections.Counter(x for t in targets for x in t.get('needs_analysis',[]));errors=collections.Counter(t.get('error') for t in targets if t.get('error'))
 warnings=collections.Counter(w for t in targets for gr in t.get('generation',{}).values() for w in gr.get('checks',{}).get('warnings',[]))
 save(HERE/'private/run_comparison.json',runs);save(HERE/'private/validation.json',ver)
 summary={'run_id':final['id'],'metrics':final['metrics'],'needs_analysis':dict(issues),'errors_or_unknown':dict(errors),'surface_warnings':dict(warnings),'verified_files':sum(v['checked_files'] for v in ver),'quality':'human_evaluation_not_performed'};save(HERE/'private/final_summary.json',summary)
 with (HERE/'private/results50.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['ID','표준어 원문','조합기 연결 직후','최종 결과','변환 위치 수','실행 상태'])
  for r in rows:w.writerow([r['id'],r['input_text'],base[r['id']]['output_text'],r['output_text'],r['generated_targets'],r['status']])
 stat=table(['실행','입력','Qwen 분석','바뀐 문장','바뀐 위치','시간(초)','총 토큰'],[[e(n),x['metrics']['records'],x['metrics']['analysis_calls'],x['metrics']['changed_records'],x['metrics']['actual_generated_outputs'],x['metrics']['wall_seconds'],x['metrics']['reported_usage']['total_tokens']] for n,x in zip(NAMES,runs)])
 labels={'statement':'평서','information_question':'정보 질문','request':'요청·명령','exclamation':'감탄','confirmation':'확인','plain':'비높임','polite':'상대 높임','present':'현재','past':'과거','future':'미래'}
 reasons={'boundary_coverage_mismatch':'모델이 경계 일부를 빠뜨리거나 중복함','adnominal_structure_mismatch':'관형절 판단과 실제 형태가 안 맞음','clause_connection_mismatch':'연결 관계 판단과 실제 형태가 안 맞음','question_scope_unresolved':'질문의 범위를 확정하지 못함','question_owner_not_target_or_unknown':'의문사가 대상 서술어 소속인지 확인하지 못함','question_scope_kind_conflict':'질문 종류와 범위 판단이 충돌','auxiliary_class_unresolved':'보조용언의 성격을 확정하지 못함','auxiliary_structure_mismatch':'보조용언 연결과 실제 형태가 안 맞음','nonadjacent_auxiliary_unresolved':'보조용언 사이의 연결을 확인하지 못함','boundary_relation_unresolved':'경계의 연결 대상이 미확정','internal_clause_alignment_unresolved':'붙여 쓴 내부 구성을 아직 구별하지 못함'}
 body=[]
 for r in rows:
  detail=[]
  for t in r['targets']:
   i,j=t['span'];f=t.get('features',{});meaning=' / '.join(labels.get(f.get(k),str(f.get(k))) for k in ('speech_act','addressee_level','tense')) if f else '분석 미확정'
   why='; '.join(reasons.get(x,x) for x in t.get('needs_analysis',[])) or reasons.get(t.get('error'),t.get('error')) or ('지원 범위 밖' if t.get('readiness')=='out_of_slice' else '조건 일치')
   detail.append([e(r['input_text'][i:j]),e(meaning),e(', '.join(t.get('rules',[])) or '선택 없음'),e(why)])
  state='변환' if r['generated_targets'] else '유지'
  body.append('<tr data-state="'+state+'"><td>'+e(r['id'])+'</td><td>'+e(r['input_text'])+'</td><td>'+e(base[r['id']]['output_text'])+'</td><td><b>'+e(r['output_text'])+'</b><details><summary>이 문장이 바뀌거나 멈춘 이유</summary>'+table(['대상','모델 판단','조회 규칙','조합 / 보류'],detail)+'</details></td></tr>')
 cases='<table id="cases"><thead><tr><th>ID</th><th>원문</th><th>조합기 연결 직후</th><th>최종 결과</th></tr></thead><tbody>'+''.join(body)+'</tbody></table>'
 g=read(ROOT/'knowledge/authored/semantic_grammar_20261103_r2/private/graph.json');ns={n['id']:n for n in g['nodes']};rr=[]
 for n in g['nodes']:
  if n['type']=='SemanticRule' and n['id'].startswith('SEM_DECL_'):
   ev=[ns[x['target']]['properties'] for x in g['edges'] if x['source']==n['id'] and x['relation']=='SUPPORTED_BY'];rr.append([e(n['properties']['title']),e(n['id']),e(', '.join(sorted({x['document_id']+' PDF '+str(x['pdf_page']) for x in ev})))])
 doc='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>조합기 연결과 평서·높임 첫 확장</title><style>
body{font:17px/1.65 system-ui,"Malgun Gothic",sans-serif;background:#f5f7fb;color:#202b3d;max-width:1250px;margin:auto;padding:26px}h1{font-size:30px}h2{font-size:23px}section{background:white;padding:24px;border:1px solid #d9e1eb;border-radius:12px;margin:18px 0}table{width:100%;border-collapse:collapse;font-size:14px;margin:16px 0}th,td{border:1px solid #dbe2ec;padding:10px;text-align:left;vertical-align:top}th{background:#edf3fc}summary{cursor:pointer;color:#2156a6;padding:8px}a{color:#164c9e}.big{font-size:22px;font-weight:700}.flow{display:flex;gap:9px;flex-wrap:wrap}.flow span{padding:12px;background:#edf3fc;border-radius:8px}.note{background:#fff5d8;padding:12px;border-radius:8px}input,select{font:inherit;padding:9px;margin:5px}details table{font-size:12px}.scroll{overflow-x:auto}.metric{display:inline-block;background:#e8f3ed;padding:14px;margin:5px;border-radius:8px}nav a{margin-right:16px}footer{font-size:13px;color:#536477}#cases td{min-width:100px}code{word-break:break-all}</style><h1>조합기 연결과 평서·높임 첫 확장</h1><p>2026-11-03 · 실제 Qwen 분석과 최종 출력 확인 · 기존 50문장·과거 결과 보존</p><nav><a href="#answer">핵심 결과</a><a href="#all">50문장 비교</a><a href="#knowledge">추가 지식</a><a href="#next">남은 일</a></nav>'''
 doc+='<section id="answer"><h2>무엇을 끝냈나</h2><p class="big">Qwen이 분석하고, KG 조건으로 어미를 고르고, 조합기가 최종 문장까지 만듭니다.</p><div class="flow"><span>표준어 입력</span>→<span>Kiwi 위치 + Qwen 의미 판단</span>→<span>KG 조건 관계 조회</span>→<span>활용 조합</span>→<span>최종 문장</span></div><p>모델에 전달할 자료만 준비하고 끝난 작업이 아닙니다. 이번 실험은 승인한 <b>Qwen 분석 + 조합기 생성</b> 방식입니다. Qwen의 생성 API 호출은 0회입니다.</p>'
 for text in [str(final['metrics']['changed_records'])+' / 50 문장 일부 변환',str(final['metrics']['actual_generated_outputs'])+' / 62 위치 조합','62회 새 Qwen 분석']:doc+='<div class="metric">'+text+'</div>'
 doc+='<p class="note">변환 수는 정확도나 자연스러움 점수가 아닙니다. 문장 전체의 어휘·문맥을 자연스럽게 다시 쓰는 기능까지 완성하지 않았습니다. 이번 출력에 사람 평가는 아직 없습니다.</p></section><section><h2>실험을 나눠 확인한 이유</h2>'+stat+'<p>12건은 별도 개발용 구조 점검입니다. 기존 50건은 회귀 검사이며, 독립 최종 평가셋이 아닙니다. 단계별로 새 Qwen 분석을 실행했고 코드·KG·프롬프트 변경도 있으므로 수치 차이를 한 수정의 인과 효과라고 단정하지 않습니다.</p></section>'
 ex=next(r for r in rows if r['id']=='ADVCE006A')
 doc+='<section><h2>실제로 연결된 예</h2><p><b>'+e(ex['input_text'])+'</b> → <b>'+e(ex['output_text'])+'</b></p><div class="flow"><span>설명 + 하 + 었 + 어요</span>→<span>평서·높임 / 실제 었 / 종결 어요</span>→<span>해예 평서 구성</span>→<span>조건 관계를 따라 어예 선택</span>→<span>설명했어예</span></div><p>HAS_USAGE → ANY_BRANCH → ALL → ACCEPTS 및 REALIZES 관계를 실제 조회합니다. 문법 모듈에 연결된 카드 전체를 전달하지 않습니다. Claude 정답 문장을 모델 요청이나 변환 표에 넣지 않았습니다.</p></section>'
 doc+='<section id="knowledge"><h2>추가한 지식과 범위</h2>'+table(['구성','실제 규칙 ID','문헌 근거'],rr)+'<p>아요/어요는 Kiwi에서 같은 형태로 정규화되므로 한 용법입니다. 원래 6개 질문 용법에 새 평서·상대높임 용법 3개를 추가했습니다. 선어말 조건은 <b>없음·었·시·시+었</b>입니다. 명사계사·부정계사·약속·명령·확인·회상형은 이번 묶음에서 제외했습니다.</p><p>원래 질문 KG의 100노드·214관계는 값까지 보존됐습니다. 최종 KG는 <b>136노드·267관계</b>이며 공통척추와 12모듈을 유지합니다. 12모듈 전체 정제가 끝난 것은 아닙니다. 이번 실행은 버전별 JSON 그래프이고 Neo4j 실DB를 새로 적재하지 않았습니다.</p><details><summary>원문 확인 범위와 검토자 의견</summary><p>리드: D02 PDF201–206·57·214·29 및 D05 PDF25–27 추출 본문 확인, D02 PDF203·205 화면 대조. 원본 PDF 해시와 정확한 인용 위치 저장. 7종 전체 정독을 다시 완료했다는 뜻은 아닙니다.</p><p>지역·시기는 출처로 보존하며 필수 사용자 입력으로 제한하지 않습니다. 원문에서 관찰된 구성과 실제 입력에 조합한 새 완성형은 구별합니다.</p><ul>'
 for label,path in [('Codex 설계','codex/design_review.md'),('Codex 구현 반례','codex/implementation_review.md'),('Codex 수정 확인','codex/final_confirmation.md'),('Claude 원문 검토','claude/source_review.md'),('Claude 후속 논의','claude/followup.md'),('Claude 출력·근거 검토','claude/final_review.md')]:doc+='<li><a href="reviewers/'+path+'">'+label+'</a></li>'
 doc+='</ul><p>Codex는 기존 반례 네 가지의 수정과 18개 검사를 확인했습니다. 다만 <b>새 조건 각각의 직접 출처 관계는 미완료</b>입니다. 규칙 단위의 근거 연결과 이 한계를 구분합니다.</p></details></section>'
 doc+='<section id="all"><h2>50문장 전체 비교</h2><p>원문 유지도 숨기지 않습니다. 각 행에서 판단·조회·보류 이유를 펼칠 수 있습니다.</p><input id="search" placeholder="ID 또는 문장 검색"><select id="filter"><option value="">전체</option><option>변환</option><option>유지</option></select><span id="count"></span><div class="scroll">'+cases+'</div><p><a href="results50.csv">50문장 CSV</a> · <a href="run_comparison.json">실험 비교 원본</a> · <a href="validation.json">파일 검증</a></p></section>'
 doc+='<section id="next"><h2>남은 문제와 다음 작업</h2>'+table(['문제','다음 작업','종료 기준'],[['명사계사·약속·명령 등이 미지원','다음 지식 묶음을 원문에서 정제해 조건·실현형 연결','양성/음성 사례와 실제 조회·출력 확인'],['Qwen의 절 소속·보조용언 판단 오류/미확정','보류 위치를 원문·분석 답변과 대조','잘못된 귀속 차단과 올바른 귀속 조회를 함께 확인'],['개별 조건의 직접 출처 연결 미완료','문헌 조건과 실험상 범위 조건을 분리하여 연결','조건마다 근거 또는 구현 선택 이유 추적 가능'],['자연스러움 미평가','지원 범위가 충분해진 뒤 사용자 평가','사람이 뜻·높임·자연스러움을 판정']])+'<p>실제 보류 사유는 중복 집계가 가능합니다.</p>'+table(['사유','대상 수'],[[e(reasons.get(k,k)),v] for k,v in issues.items()])+table(['분석 미확정/오류','수'],[[e(reasons.get(k,k)),v] for k,v in errors.items()])+'<details><summary>자동 표면 경고 — 오류율이 아님</summary>'+table(['경고','수'],[[e(k),v] for k,v in warnings.items()])+'</details><p>복잡한 문장 하나를 고치는 전용 정답 규칙은 추가하지 않았습니다. 다음 지식 범위를 늘리는 결정은 사용자와 합의하고, 일반 코드 수정과 합의한 검사는 계속 수행합니다.</p></section>'
 doc+='<footer>최종 Run ID: '+final['id']+'<br>검증 파일 '+str(summary['verified_files'])+'개, 해시 불일치 0. 파일 일치는 언어학적 정확성 인증이 아닙니다.</footer><script>function filterRows(){let q=document.querySelector("#search").value.toLowerCase(),f=document.querySelector("#filter").value,n=0;document.querySelectorAll("#cases>tbody>tr").forEach(r=>{let show=(!f||r.dataset.state===f)&&r.textContent.toLowerCase().includes(q);r.hidden=!show;if(show)n++});document.querySelector("#count").textContent=n+" / 50건"}document.querySelector("#search").addEventListener("input",filterRows);document.querySelector("#filter").addEventListener("change",filterRows);filterRows();</script></html>'
 (HERE/'private/report.html').write_text(doc,'utf8')
 navp=ROOT/'experiments/management/report_navigation.json';nav=read(navp);url=(HERE/'private/report.html').as_uri();nav=[x for x in nav if x.get('url')!=url];nav.append({'title':'33 · 조합기 연결과 평서·높임 첫 확장','url':url,'summary':'Qwen 분석→조건 KG→활용 조합→최종 출력. 50건 중14문장·15위치 변환. 원본·검토·보류 원인과 남은 작업.'});save(navp,nav)
 print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':main()
