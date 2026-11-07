"""Render real run comparisons; never synthesize outputs or quality scores."""
import argparse,html,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from kg_pipeline.multi_agent import PROMPTS,review_context
E=lambda x:html.escape(str(x if x is not None else '기록 없음'))
def read(p,default=None):return json.loads(p.read_text(encoding='utf8')) if p.exists() else default
def table(head,rows):return '<div class="scroll"><table><tr>'+''.join('<th>'+E(x)+'</th>' for x in head)+'</tr>'+''.join('<tr>'+''.join('<td>'+str(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</table></div>'
def build(args):
 runs=[(label,Path(path).resolve()) for label,path in (s.split('=',1) for s in args.run)]
 data=[(label,path,read(path/'metrics.json',{}),read(path/'private/results.json',[])) for label,path in runs]
 inputs=[json.loads(x) for x in (runs[0][1]/'private/inputs.jsonl').read_text(encoding='utf8').splitlines() if x.strip()]
 metrics=[]
 for label,path,m,rows in data:
  metrics.append([E(label),len(rows),m.get('final_available_records',m.get('valid_output_records',0)),E(m.get('failure_stages',{})),m.get('api_attempts'),m.get('reported_usage',{}).get('total_tokens'),m.get('wall_seconds'),sum(bool(r.get('repaired')) for r in rows)])
 rows=[];details=[]
 for row in inputs:
  cells=[E(row['id']),E(row['text'])]
  detail=[]
  for label,path,met,results in data:
   r=next((x for x in results if x['id']==row['id']),{});rd=path/'private/records'/row['id']
   output=r.get('output_text');draft=r.get('draft_text') or read(rd/'writer/parsed.json',{}).get('output_text')
   cells.append(E(output) if output is not None else '<b>최종 출력 없음</b>'+('<br>보존 초안: '+E(draft) if draft else ''))
   selected=read(rd/'selected_knowledge.json',None)
   if selected is None:selected=read(rd/'generation_packet.json',{}).get('verified_scope_knowledge')
   detail.append('<h3>'+E(label)+'</h3><p>전달 후보: '+E(len(selected) if selected is not None else None)+'개 · 실제 처리 단계: '+E(r.get('current_pipeline_stage',r.get('stage',r.get('status'))))+' · 출력 수정 호출: '+E(r.get('repaired','해당 경로에 별도 검토 없음'))+'</p>')
   if selected:
    detail.append(table(['원문 위치','전달된 안내','표현 후보','기록된 규칙 번호'],[[E(a.get('source_text')),E(a.get('instruction')),E([f.get('form') if isinstance(f,dict) else f for f in a.get('forms',[])]),E(a.get('rule_id'))] for a in selected]))
   bound=read(rd/'bound_analysis.json',[])
   if bound:
    hints=review_context(bound)
    detail.append(table(['원문 구절','보존할 내용 — 분석 모델의 판단','분석에 이의가 남았나'],[[E(h['원문 구절']),'<br>'.join(E(k)+': '+E(v) for k,v in h['보존 정보(분석 추정)'].items()),E(h['분석 불확실'])] for h in hints]))
   rev=read(rd/'review_validation.json',{})
   if rev:
    detail.append('<p>검토 인용 형식 상태: '+E(rev.get('state'))+' — 지적 내용의 정답 인증이 아닙니다.</p>')
    detail.append(table(['원인으로 지목한 단계','수정 대상','문제','수정 방향'],[[E(i.get('stage')),E(i.get('repair_target','이전에는 구분하지 않음')),E(i.get('problem')),E(i.get('suggestion'))] for i in rev.get('issues',[])]))
   detail.append('<p class="small">실행 원본: '+E(path.name)+'</p>')
  rows.append(cells);details.append('<details><summary>'+E(row['id'])+' 처리 과정 보기</summary>'+''.join(detail)+'</details>')
 analysis=HERE/'RESULTS.md'
 paragraphs=''.join('<p>'+E(x).replace('\n','<br>')+'</p>' for x in analysis.read_text(encoding='utf8').split('\n\n')) if analysis.exists() else '<p>결과 해석 작성 전</p>'
 prompts=''.join('<details><summary>'+E(k)+' — 실제 지시문 전체</summary><pre>'+E(v)+'</pre></details>' for k,v in PROMPTS.items())
 page='<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>분석과 KG 연결, 검토와 수정 연결</title><style>body{font-family:Malgun Gothic,Arial;max-width:1150px;margin:30px auto;padding:20px;background:#f4f7fb;color:#183047;line-height:1.85}section,details{background:white;padding:22px;margin:18px 0;border:1px solid #d9e2ef;border-radius:12px}h1{font-size:30px}h2{font-size:23px}table{width:100%;border-collapse:collapse;font-size:14px}td,th{padding:12px;border:1px solid #d9e2ef;text-align:left;vertical-align:top}th{background:#eaf1fa}.scroll{overflow:auto}.flow{padding:20px;background:#eaf4ff;border-radius:10px;font-size:19px}.warning{padding:15px;border-left:5px solid #d39427;background:#fff4db}.small{font-size:12px;color:#627489}summary{cursor:pointer;font-weight:bold}pre{white-space:pre-wrap;font:inherit;overflow-wrap:anywhere}a{color:#1264a2}</style><h1>정보가 끊긴 두 곳을 고쳤습니다</h1><p>첫째는 분석값을 KG 조건에 연결하는 곳입니다. 둘째는 검토에서 발견한 문제를 작성자에게 다시 보내는 곳입니다. 연결을 고쳤다는 것과 방언이 자연스러워졌다는 것은 따로 확인합니다.</p><div class="flow">원문 → 구조 분석 → 뜻·관계 분석 → KG 조회 → 문장 작성 → 검토 → 필요한 경우 한 번 수정</div><section><h2>1. 무엇을 바꿨나?</h2><p>품사와 필드의 뜻을 설명하고, 서로 맞지 않는 분석은 구조 담당자에게 한 번만 재확인합니다. 잘못된 수정 제안 하나 때문에 문장 전체를 중단하지 않습니다. 검토자는 원인 단계와 실제로 수정할 대상을 따로 적습니다. 출력에서 높임이 사라졌다면 원인이 분석에 있어도 작성자에게 복구를 요청할 수 있습니다.</p><p>검토에는 원문·초안·간단한 보존 정보·실제 사용 지식만 전달합니다. 원시 품사표를 다시 설명하게 하지 않습니다. 단, 검토자의 지적도 틀릴 수 있으므로 실제 인용과 오류 유형을 확인하고, 단순히 방언화가 부족하다는 이유로 수정하지 않습니다.</p><p>KG의 문법 조건과 원래 버전은 바꾸지 않았습니다. 최종 문장은 Qwen이 씁니다. 코드가 정답 문장을 대신 넣지 않습니다.</p></section><section><h2>2. 결과와 판단</h2>'+paragraphs+'</section><section><h2>3. 실제 실행 수치</h2><p class="warning">최종 처리 수·후보 수·검토 형식 통과는 자연스러움 정확도가 아닙니다. 실패한 호출 비용도 포함합니다. 같은 개발6문장을 재사용했으며 독립 평가가 아닙니다. Kiwi 기존 경로를 포함했다면 생성 지시·호출 구조도 다르므로 Kiwi 하나의 효과라고 해석할 수 없습니다.</p>'+table(['방식','시도 문장','최종 처리','실패 단계','모델 호출','총 토큰','경과 초','출력 수정 호출 문장'],metrics)+'</section><section><h2>4. 같은 문장의 결과 비교</h2>'+table(['ID','표준어']+[label for label,_ in runs],rows)+'</section><section><h2>5. 필요한 지식은 실제로 전달됐나?</h2><p>문장을 열면 분석 판단, 전달 지식, 검토 지적을 볼 수 있습니다. 정보가 없어서 못 바꾼 경우와 정보가 있었는데 전달·작성에서 끊긴 경우를 구분하기 위한 기록입니다.</p>'+''.join(details)+'</section><section><h2>6. 두 검토자와 역할별 실제 지시문</h2><p>Claude는 언어 해석·정보 손실을, Codex는 코드 연결·비교 조건·기록을 검토했습니다. 두 의견이 같다는 이유만으로 사실이나 품질을 확정하지 않았습니다.</p><p><a href="claude_review.md">Claude 원인 검토</a> · <a href="codex_review.md">Codex 원인 검토</a> · <a href="claude_implementation_review.md">Claude 구현 검토</a> · <a href="codex_implementation_review.md">Codex 구현 검토</a></p>'+prompts+'</section></html>'
 if args.probe:
  probe=Path(args.probe).resolve();records=read(probe/'private/results.json',[])
  block='<section><h2>7. 검토를 실제로 전달하니 고쳐졌나?</h2><p>분석·KG·초안·기존 검토를 고정하고 작성자만 한 번씩 호출했습니다. 04는 정상 필터라면 제외될 거짓 지적을 일부러 전달한 반례 점검입니다. 전체 번역 성능 비교가 아닙니다.</p>'+table(['사례','기존 초안','재검토 후 모델 출력','모델이 밝힌 처리 이유'],[[E(r['id']),E(r.get('draft_text')),E(r.get('output_text')),'<br>'.join(E(x.get('decision'))+': '+E(x.get('reason')) for x in r.get('feedback_decisions',[]))] for r in records])+'</section>'
  page=page.replace('</html>',block+'</html>')
 page=page.replace('<h1>정보가 끊긴 두 곳을 고쳤습니다</h1>','<h1>연결을 보완했지만, 분석과 생성의 오류는 남았습니다</h1>')
 page=page.replace('</section></html>','</section><section><h2>8. 검토 결론과 다음 선택</h2><p>두 검토자 모두 반복 프롬프트 수정과 50건 확대를 멈추는 데 동의했습니다. 리드는 Kiwi가 형태를 분석하고 Qwen이 뜻을 판단하고 최종 문장을 쓰는 방향을 권고합니다. 아직 기본 실행 경로를 바꾸지는 않았습니다.</p><p>다음에는 의미 분석·문장 작성 조건을 같게 두고 형태 분석만 바꿔 확인합니다. 형태가 맞아도 조건이 미확정으로 남는 사례와, 목표 방언 표현을 전달해도 지키지 않는 사례를 따로 봅니다. 연결과 보존이 확인되면 50건 회귀로 이어갑니다. 개선이 없으면 같은 프롬프트를 반복하지 않고 모델 역할·목표형 지식의 기여를 분리합니다.</p><p>최종 코드 검사 66건 통과는 프로그램 검사 결과이며 언어 정확도가 아닙니다. 최신 전달 보완은 전체6건 재실험이 아닌 3사례 진단까지입니다.</p><p><a href="claude_outcome_review.md">Claude 최종 검토 원문</a> · <a href="codex_outcome_review.md">Codex 최종 검토 원문</a> · <a href="../DECISIONS.md">채택·정정한 의견</a> · <a href="../README.md">실행 기록 안내</a></p></section></html>')
 out=HERE/'private/report.html';out.write_text(page,encoding='utf8')
 (HERE/'prompts.md').write_text('# 이번 실행 역할별 지시문\n\n'+'\n\n'.join('## '+k+'\n\n'+v for k,v in PROMPTS.items()),encoding='utf8')
 (HERE/'report_latest.json').write_text(json.dumps({'report':str(out.relative_to(ROOT)),'runs':[str(p.relative_to(ROOT)) for _,p in runs]},ensure_ascii=False,indent=2),encoding='utf8')
 print(out)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run',action='append',required=True);p.add_argument('--probe');build(p.parse_args())
