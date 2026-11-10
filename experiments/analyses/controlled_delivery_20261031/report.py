"""A short human-facing report; offline replay and new model runs never conflated."""
import html,json,sys,collections
from pathlib import Path
B=Path(__file__).resolve().parent;R=B.parents[2];P=B/'private';sys.path[:0]=[str(R/'local/python'),str(R/'src')]
from kg_pipeline.io import read,save
E=lambda x:html.escape(str(x if x is not None else '결과 없음'))
def table(headers,rows):return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+E(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+E(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'

def main():
 summary=read(P/'replay_summary.json');cases=read(P/'replay_cases.json');tests=read(P/'tests.json')
 checks=[json.loads(l) for l in (P/'preflight_history.jsonl').read_text('utf8').splitlines()]
 actual=None;metrics={};actual_cases={};active=read(P/'active_run.json') if (P/'active_run.json').exists() else None
 if active and (R/'experiments/batches'/active['batch']/'resources.json').exists():
  actual=read(R/'experiments/batches'/active['batch']/'resources.json')
  for key,run in active['runs'].items():
   rows=read(R/'experiments/runs'/run/'private/results.json');actual_cases[key]={r['id']:r for r in rows}
   metrics[key]={'changed':sum(r['output_text'] is not None and r['output_text']!=r['input_text'] for r in rows),'unchanged':sum(r['output_text']==r['input_text'] for r in rows),'no_output':sum(r['output_text'] is None for r in rows),
    'calls':sum(len(r['calls']) for r in rows),'tokens':sum((c.get('usage') or {}).get('total_tokens',0) for r in rows for c in r['calls'])}
 save(P/'report_summary.json',{'offline':summary,'actual_model_results':metrics if actual else None,'actual_resources':actual,'preflight_latest':checks[-1],'tests':tests['tests']})
 h='<header><p class="eyebrow">판단 기준 통일 → 설명과 조합 도움을 나눠 비교</p><h1>'+('세 조건의 실제 실험 결과' if actual else '판단 기준은 고쳤습니다.<br>새 실험은 서버 복구를 기다립니다.')+'</h1></header>'
 h+='<nav><a href="#answer">이번에 한 일</a><a href="#replay">실제로 달라진 판단</a><a href="#experiment">비교 실험</a><a href="#cases">50문장 확인</a><a href="/work">진행 기록</a></nav>'
 h+='<section id="answer"><h2>무엇을 고쳤나</h2>'+table(['문제','이번 변경'],[
  ['추천할 때는 허용하고, 적용할 때는 같은 이유로 금지','두 단계가 같은 문법 기능 판단표를 사용하도록 통일'],
  ['금지와 일반 명령을 한꺼번에 처리할 위험','말/VX가 있는 원문의 종결어미만 바꾸고, 앞의 지와 말이 없어지지 않도록 확인'],
  ['설계 기록의 required 같은 표시를 문법 조건으로 오해','이 표시는 구체 조건값이 아니라는 설명을 제공하는 비교 조건 준비'],
  ['형태 설명을 그대로 붙여 시작했ㅂ니껴 같은 결과 생성','원문 형태소와 어미를 합친 후보를 보여주는 별도 비교 조건 준비']])
 h+='<p>KG와 카드 721개의 내용, 표준어 50문장, 과거 실험 결과는 바꾸지 않았습니다. 이번에는 <b>조건을 판단하고 모델에 전달하는 코드</b>를 고쳤습니다.</p>'
 h+=f'<p>프로그램 검사 <b>{tests["tests"]}개 통과</b>. 여기에는 실제 네트워크 호출을 대신한 모의 응답으로 Single/Multi × 세 조건의 연결을 확인한 검사도 포함합니다. 모의 검사는 Qwen 성능 실험이 아닙니다.</p></section>'
 h+='<section id="replay"><h2>이전 100개 처리 기록으로 먼저 확인</h2><p>Qwen에게 다시 물어본 결과가 아닙니다. <b>이전 Qwen의 카드 선택·표현을 그대로 두고</b> 수정한 검사만 적용했습니다.</p>'
 h+=table(['방식','재검증 가능한 출력','최종 문장이 달라진 입력'],[[a.title(),summary['arms'][a]['replayed_outputs'],', '.join(summary['arms'][a]['output_changes']) or '없음'] for a in ('single','multi')])
 h+=table(['사례','이전 판단','수정 후 판단','해석'],[
  ['LONG004 / 마세요 → 말이소','명령과 금지의 기준 충돌로 보류','기준 충돌이 해소되어 저장된 제안을 반영','말이소가 자연스럽다는 인증은 아님. 승인 표현 마이소와의 차이는 남음'],
  ['DEV020 / 마 → 마','기능 불일치로 보류','원문 유지로 정리','문장 자체는 동일'],
  ['LONG004 Multi / 나가지·마세요','기능 기준 충돌 등의 이유로 보류','지 구성의 별도 변경까지 함께 검토하도록 보류','금지 의미가 유지되는지 불분명한 조합을 새로 허용하지 않음']])
 h+='<p><b>결론:</b> 잘못된 보류 하나를 해결한 근거는 생겼습니다. 그러나 이 수정 하나만으로 전체 번역이 좋아진다고 볼 수는 없습니다. 이전에 응답이 없던 2건과 카드 형태 번호가 잘못된 1건은 성공으로 바꾸지 않았습니다.</p></section>'
 h+='<section id="experiment"><h2>다음 비교는 한 가지씩 바꿉니다</h2>'+table(['조건','달라지는 부분','확인하려는 것'],[
  ['기준','공통 판단 기준 수정만 적용','지금의 기준 결과'],['설명만 보강','카드별 공손함·기능 대조 결과를 읽기 쉽게 추가','후보를 반말로 오해하거나 설계용 표시를 잘못 읽는 문제가 줄어드는가'],
  ['조합 도움만 추가','원문 형태소와 조합기가 만든 후보 제공','어미를 실제 단어로 합치는 오류가 줄어드는가']])
 h+='<p>세 조건 모두 <b>같은 50문장·분석·조회 결과·카드 목록·검사·모델 설정</b>을 사용합니다. Single/Multi 각각 수행하므로 총 300개 처리 결과를 비교합니다. 설명과 조합 도움을 동시에 넣지 않습니다. 조합 후보를 정답으로 강제하지 않습니다.</p>'
 if actual:
  h+=table(['조건·방식','원문과 다름','원문 유지','출력 없음','호출','토큰'],[[k,*[v[f] for f in ('changed','unchanged','no_output','calls','tokens')]] for k,v in metrics.items()])
  h+='<p>변경 수는 자연스러움 점수가 아닙니다. 조건별 사례와 실패 원인을 함께 확인해야 합니다.</p>'
 else:
  h+=f'<p class="notice"><b>실제 비교 실험은 아직 실행하지 못했습니다.</b><br>기존 설정의 모델 목록 요청: HTTP {E(checks[-1].get("http_status",checks[-1].get("error_type")))}. 서버에 연결 요청은 갔지만 사용 가능한 모델을 확인할 수 없었습니다. 새 Qwen 생성 호출은 0회입니다.</p>'
  h+='<p><b>지금 필요한 것:</b> Qwen 배포가 정상인지 확인해 주세요. 주소가 바뀌었다면 기존 test.py 설정을 갱신한 뒤 알려주시면 됩니다. 모델이 확인되면 준비된 동일 조건 비교를 실행할 수 있습니다.</p>'
 h+='</section><section id="cases"><h2>50문장 전체 기록</h2><p>“재검증”은 저장 응답에 새 검사를 적용한 결과입니다. 새 모델 결과가 없으면 그 자리를 채워 넣지 않습니다.</p><label>검색 <input id="search" placeholder="번호 또는 문장"></label> <span id="count"></span>'
 for row in cases:
  h+='<details class="case"><summary>'+E(row['id'])+' · '+E(row['input'])+'</summary>'
  h+=table(['방식','이전 실제 Qwen 출력','검사만 바꾼 재검증'],[[a.title(),v['old_output'],v['replay']['output']] for a,v in row['arms'].items()])
  changes=[[a.title(),e['before'],e['after'],e['old_outcome'],e['new_outcome']] for a,v in row['arms'].items() for e in v['edit_changes']]
  if changes:h+=table(['방식','원문 부분','기존 제안','이전 처리','재검증 처리'],[[{'needs_review':'보류','applied':'반영','unchanged':'변경 없음'}.get(str(x),x) for x in r] for r in changes])
  if actual:h+=table(['새 실험 조건','실제 출력'],[[k,v[row['id']]['output_text']] for k,v in actual_cases.items()])
  h+='</details>'
 h+='</section><section><h2>정정과 검토 범위</h2><p>지난 보고서에서 DEV012의 실패를 형태소 위치 오류라고 설명했으나, 정확한 원인은 <b>형태가 하나뿐인 카드에서 form_index=1, 즉 두 번째 형태를 고른 것</b>입니다. 해당 카드의 실제 허용 번호는 0입니다. 과거 원본을 바꾸지 않고 여기서 정정합니다.</p><p>기존 Codex Reviewer가 공통 판정과 세 조건의 분리를 읽기 전용으로 검토했습니다. 미지원 조건이 남은 경우를 잘못 차단하는 분기 지적을 수정하고 반례 검사를 추가했습니다. Claude 추가 검토나 새 출력의 사람 평가를 수행한 것으로 표시하지 않습니다.</p><p>구현·재현 명세: experiments/analyses/controlled_delivery_20261031/README.md</p></section>'
 (P/'report.html').write_text('<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>판정 기준 통일·전달 조건 분리 검증</title><link rel="stylesheet" href="report.css"><script defer src="report.js"></script></head><body><main>'+h+'</main></body></html>',encoding='utf8')
 (P/'report.css').write_bytes((R/'experiments/analyses/register_connective_20261030/private/report.css').read_bytes())
 (P/'report.js').write_text("const q=document.getElementById('search'),rows=[...document.querySelectorAll('.case')];function filter(){let n=0;for(const r of rows){r.hidden=!r.textContent.toLowerCase().includes(q.value.toLowerCase());if(!r.hidden)n++;}document.getElementById('count').textContent=n+' / 50문장';}q.addEventListener('input',filter);filter();",encoding='utf8')
 print('Report: '+str(P/'report.html')+'; actual Qwen results: '+str(bool(actual)))
if __name__=='__main__':main()
