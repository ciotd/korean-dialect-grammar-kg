"""Readable report from immutable diagnostic records; no model calls."""
import html,statistics
from collections import Counter
import runner as r
H=lambda x:html.escape(str(x if x is not None else ''))
STATUS={'generated_requires_human_review':'변경됨 · 자연스러움 미평가','partial':'일부 변경 · 다른 편집은 보류','unchanged':'최종 원문 유지','needs_review':'검사에서 보류','review_not_eligible':'비교 선택 미확보 · 호출 안 함','plan_validation_failed':'선택 형식 오류 · 호출 안 함','preworker_blocked':'사전 검사 차단 · 호출 안 함','no_planned_edit':'실행할 편집 없음 · 호출 안 함','generation_failed':'생성 또는 응답 처리 실패'}
ISSUE={'source_suffix_composition_disagreement':'제안 활용형과 조합 검사가 맞지 않음','target_realization_unverified':'선택한 형태가 결과에 실현됐는지 확인하지 못함','source_connective_mismatch':'원래 연결어미와 카드의 적용 대상이 다름','function_not_supported':'지정 위치의 분석에 요구 기능이 없음','user_restricted_conversion':'사용자가 금지한 변환','prohibitive_companion_edit_unverified':'금지 표현의 연결된 편집을 확인하지 못함','target_form_unknown':'목표 형태 확인 불가','unpreserved_source_material':'보존해야 할 원문 요소 누락 의심'}
def table(headers,rows):return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+H(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def output(x):
 if x['output_text'] is not None:return H(x['output_text'])
 reason=STATUS.get(x['status'],x['status'])
 if x.get('error')=='worker_plan_mismatch':reason='정해진 편집 목록과 응답이 맞지 않아 처리 실패'
 if x.get('generation_meta',{}).get('finish_reason')=='length':reason='출력 길이 한도에 도달해 응답이 끝나지 않음'
 return '<span class="muted">생성 결과 없음 — '+H(reason)+'</span>'
def plan_view(c,arm):
 a=c['arms'][arm];lines=[]
 for e in a.get('decision',{}).get('edits',[]):
  words=' / '.join(next(w['surface'] for w in c['morphology']['words'] if w['uid']==i) for i in e['word_ids'])
  cards={x['id']:x for x in c['common']['cards']}
  for b in e['bindings']:
   fs=cards[b['card_id']]['forms'];fi=b['form_index'];form=fs[fi] if 0<=fi<len(fs) else f'잘못된 형태 번호 {fi}'
   lines.append(H(words)+' → '+H(form)+' <small>'+H(b['card_id'])+' · '+H(e['action'])+'</small>')
 return '<br>'.join(lines) or '<span class="muted">선택 없음</span>'
def main():
 latest=r.read(r.HERE/'private/latest.json');assert latest['state']=='completed'
 root=r.ROOT/latest['root'];cases=r.read(root/'prepared.json');records=r.read(root/'results.json');summary=r.read(root/'summary.json')
 source=r.ROOT/'experiments/analyses/effect_ledger_20261031/private/preparations/20261031T031655556269Z/cases.json'
 refs={x['id']:x['approved_reference'] for x in r.read(source)}
 index={(x['id'],x['arm'],x['repeat']):x for x in records}
 notespath=r.HERE/'private/interpretation.json';notes=r.read(notespath) if notespath.exists() else {}
 stats=[];arms={};issues=Counter()
 for arm in r.ARMS:
  rows=[x for x in records if x['arm']==arm];called=[x for x in rows if x['worker_calls']];valid=[x for x in called if x['output_text'] is not None]
  latency=[x['generation_meta']['seconds'] for x in called if 'generation_meta' in x]
  usage=Counter();abstain=0;blocked=0;repaired=0
  for x in rows:
   usage.update({k:v for k,v in (x.get('generation_meta',{}).get('usage') or {}).items() if isinstance(v,(int,float))})
   abstain+=any(e['raw_action']=='needs_review' for e in x.get('edit_trace',[]))
   blocked+=any(e['raw_action']=='apply' and e['outcome'] not in ('applied','unchanged') for e in x.get('edit_trace',[]))
   repaired+=any(e['repairs'] for e in x.get('edit_trace',[]))
   issues.update(set(i['code'] for i in x['issues']))
  arms[arm]={'records':len(rows),'calls':len(called),'valid_responses':len(valid),'changed':sum(x['changed'] for x in valid),'unchanged':sum(not x['changed'] for x in valid),'worker_abstention_records':abstain,'postcheck_block_records':blocked,'program_repair_records':repaired,'failures':sum(x['status']=='generation_failed' for x in rows),'usage':dict(usage),'latency_median':statistics.median(latency) if latency else None}
  a=arms[arm];stats.append([H('기존 선택' if arm=='saved' else '검토한 선택'),H(a['records']),H(a['calls']),H(a['changed']),H(a['unchanged']),H(a['worker_abstention_records']),H(a['postcheck_block_records']),H(a['failures'])])
 paired=[c for c in cases if all(c['arms'][a]['status']=='ready' for a in r.ARMS)]
 pairs=[]
 for c in paired:
  for rep in range(1,4):
   a,b=[index[c['id'],arm,rep] for arm in r.ARMS]
   pairs.append({'id':c['id'],'repeat':rep,'same_selection':c['same_selection'],'saved_changed':a['changed'],'reviewed_changed':b['changed'],'both_have_output':all(x['output_text'] is not None for x in (a,b)),'identical_output':a['output_text']==b['output_text']})
 variation={arm:[c['id'] for c in cases if len({(index[c['id'],arm,rep]['status'],index[c['id'],arm,rep]['output_text']) for rep in range(1,4)})>1] for arm in r.ARMS}
 analysis={'arms':arms,'paired_cases':len(paired),'paired_repetitions':len(pairs),'pairs':pairs,'same_selection_cases':sum(c['same_selection'] is True for c in paired),'same_selection_different_output_ids':sorted({p['id'] for p in pairs if p['same_selection'] and not p['identical_output']}),'variation_ids':variation,'issue_record_counts_deduplicated':dict(issues),'quality_accuracy':None,'all50_reviewed':True,'selection_ready_cases':sum(bool(c['reviewed_targets']) for c in cases)}
 r.save(root/'analysis.json',analysis)
 content='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>카드를 미리 골라 주면 달라질까?</title><link rel="stylesheet" href="report.css"><script src="report.js" defer></script><main>'''
 content+='<header><p class="eyebrow">KG 연구 · 2026-11-02 · 실제 Qwen 진단 실험</p><h1>카드를 미리 골라 주면<br>방언 변환이 나아질까?</h1><p>이번에는 자동 선택을 고치는 대신, 연구 리드(Codex)가 검토한 카드와 위치를 넣어 보았습니다. <strong>어디서 막히는지 찾는 실험</strong>이며, 완성된 시스템의 성적표가 아닙니다.</p><nav><a href="#answer">먼저 결론</a><a href="#method">비교 방법</a><a href="#numbers">측정값</a><a href="#cases">50문장 보기</a><a href="#next">다음 작업</a></nav></header>'
 content+='<section id="answer"><h2>이번에 알게 된 것</h2>'+''.join('<p><strong>'+H(i+1)+'. </strong>'+H(t)+'</p>' for i,t in enumerate(notes.get('findings',['실행 결과를 생성했습니다. 구체적인 언어학적 판단은 아래 원문·출력·처리 기록을 함께 보아야 합니다.'])))+'</section>'
 content+='<section id="method"><h2>같은 재료로, 두 선택 계획을 비교했습니다</h2><div class="flow"><span>같은 원문·문법 분석<br>같은 전체 카드 목록</span><b>→</b><span>① 기존 선택 계획<br>② 검토한 선택 계획</span><b>→</b><span>같은 Qwen 워커<br>같은 검사·반영 코드</span></div><p>정답 문장이나 완성된 교체 단어는 넣지 않았습니다. 검토자가 정한 것은 <strong>어느 위치에 어떤 카드의 형태를 쓸지</strong>입니다. 기존 자유 지시는 양쪽 모두 같은 설명 형식으로 다시 작성했습니다.</p>'
 content+=table(['구분','정확한 범위'],[
 ['전체 검토','50문장 모두 확인. 32문장에 검토 후보가 있고, 18문장은 카드·분석 등 미확보 사유를 남겼습니다.'],
 ['직접 비교',f'{len(paired)}문장 × 3회 = {len(pairs)}쌍을 시도했습니다. 그중 양쪽 최종 응답이 모두 남은 것은 {sum(p["both_have_output"] for p in pairs)}쌍입니다. 응답 처리 실패를 빼고 성능이 좋아졌다고 계산하지 않습니다.'],
 ['선택 자체가 같은 경우',f'{analysis["same_selection_cases"]}문장. 결과 차이가 나도 선택 개선 효과로 해석하지 않습니다. 편집 ID와 계획 해시는 서로 다르므로 요청문이 바이트 단위로 같지는 않습니다.'],
 ['무엇을 바꿨나','카드·원문 위치뿐 아니라 선택한 편집의 수, 적용/보류, 묶음·의존관계가 달라질 수 있습니다. 선택 계획 전체를 바꾼 진단입니다.'],
 ['불완전한 계획','예: LONG004는 마세요 한 곳만 검토했습니다. 나머지 어휘·어미가 그대로여도 그 위치 실험의 실패로 일괄 계산하지 않습니다.'],
 ['미전달 카드','LONG003의 공손 질문 카드는 당시 목록에 없어 추가하지 않았습니다. 다른 세 위치만 비교했습니다.'],
 ['고정한 것','기존 저장 분석·카드·프롬프트·현재 검사/자동 조합 보정. 새 문장 분석·검색·선택 모델 호출은 없습니다.'],
 ['해석 한계','검토자는 승인된 참조 문장을 알고 있습니다. 자동 선택 성능이나 새로운 문장에 대한 일반화 성능을 측정한 실험이 아닙니다.'],
 ['비교 설계에서 발견한 한계','두 방식의 편집 이름(E1/R1)과 이에 따른 계획 해시도 달라집니다. 동일한 카드 선택에서 응답 차이가 있어, 카드 선택만의 순수한 인과 효과로 주장하지 않습니다. 후속 비교에서는 편집 이름도 통일해야 합니다.']])+'</section>'
 content+='<section id="numbers"><h2>실제로 몇 번 실행했나?</h2><p><strong>'+H(summary['records'])+'개 처리 기록 · '+H(summary['actual_worker_calls'])+'회 Qwen 호출</strong> · 전체 실행 '+H(round(summary['wall_seconds']/60,1))+'분</p><p>아래 수치는 3회 반복을 합한 것입니다. <strong>변경됨 = 올바른 방언</strong>이 아닙니다. ‘원문 유지’ 안에서도 Qwen 스스로 보류한 경우와 검사에서 막힌 경우를 따로 보았습니다.</p>'
 content+=table(['선택 방식','처리 기록','실제 호출','최종 변경','최종 원문 유지','Qwen 보류 포함','검사 차단 포함','처리 실패'],stats)
 failed=[x for x in records if x['status']=='generation_failed']
 content+='<p>처리 실패 '+H(len(failed))+'회 중 출력 길이 한도 도달 '+H(sum(x.get('generation_meta',{}).get('finish_reason')=='length' for x in failed))+'회, 정해진 편집 목록과 응답의 불일치 '+H(sum(x.get('error')=='worker_plan_mismatch' for x in failed))+'회였습니다. 자동 재시도는 하지 않았습니다.</p>'
 content+='<p class="note">보류와 검사 차단은 겹칠 수 있으며, 부분 변경 문장에도 포함될 수 있습니다. 미호출은 원문 출력으로 계산하지 않습니다. 기존 기록의 status가 unchanged라도 워커가 needs_review라고 답했는지 원문 응답을 다시 집계했습니다. 오류는 같은 기록 안에서 같은 코드를 중복 계산하지 않았습니다.</p>'
 content+='<p>프로그램의 활용 보정이 들어간 기록: 기존 선택 '+H(arms['saved']['program_repair_records'])+'건, 검토 선택 '+H(arms['reviewed']['program_repair_records'])+'건. 이 경우 최종 표현을 Qwen 단독 생성 결과로 해석하면 안 됩니다.</p>'
 content+=table(['방식','입력 토큰 합','출력 토큰 합','호출 응답시간 중앙값','반복 결과가 달라진 문장'],[[H('기존 선택' if a=='saved' else '검토한 선택'),H(arms[a]['usage'].get('prompt_tokens','미제공')),H(arms[a]['usage'].get('completion_tokens','미제공')),H(round(arms[a]['latency_median'],2))+'초',H(len(variation[a]))] for a in r.ARMS])
 content+='<p class="note">비용은 이번 워커 호출만 포함합니다. 저장된 분석·검색·선택의 과거 비용은 제외했습니다. 서버가 공개하지 않은 모델 체크포인트·GPU 정보는 추정하지 않았습니다. 3회 반복은 작은 안정성 점검이며 통계적 품질 검증이 아닙니다.</p></section>'
 content+='<section id="cases"><h2>50문장 전체 결과</h2><p>먼저 첫 번째 실행을 나란히 보고, 펼치면 나머지 두 번과 실제 변경 위치를 확인할 수 있습니다. ‘Qwen 이유’는 모델이 한 설명이며, 그 내용이 사실이라는 뜻은 아닙니다.</p><input id="search" aria-label="문장 검색" placeholder="ID 또는 문장으로 검색"><span id="count">50문장</span>'
 for c in cases:
  key=c['id'];a,b=[index[key,arm,1] for arm in r.ARMS]
  content+='<article class="case" data-search="'+H(key+' '+c['input'])+'"><h3>'+H(key)+'</h3><p class="source">'+H(c['input'])+'</p><p><strong>승인한 참조:</strong> '+H(refs[key])+'</p>'
  content+=table(['기존 선택 → 생성','검토한 선택 → 생성'],[[output(a),output(b)],[H(STATUS[a['status']]),H(STATUS[b['status']])]])
  content+='<p><strong>이번에 확인한 범위:</strong> '+H(c['scope_note'])+'</p>'
  if key in notes.get('cases',{}):content+='<p class="insight"><strong>해석:</strong> '+H(notes['cases'][key])+'</p>'
  if c['missing_targets']:content+='<p class="warning">전달 목록에 없어 제외한 목표: '+H(c['missing_targets'])+'</p>'
  content+='<details><summary>선택 카드·3회 결과·실제 처리 보기</summary>'
  content+=table(['기존 선택','검토한 선택'],[[plan_view(c,'saved'),plan_view(c,'reviewed')]])
  content+=table(['반복','기존 선택 결과','검토한 선택 결과'],[[H(rep),output(index[key,'saved',rep]),output(index[key,'reviewed',rep])] for rep in range(1,4)])
  for arm in r.ARMS:
   content+='<h4>'+('기존 선택' if arm=='saved' else '검토한 선택')+' · 첫 실행의 처리 기록</h4>'
   x=index[key,arm,1];trace=x.get('edit_trace',[])
   if trace:
    content+=table(['원래 부분','Qwen 제안','최종 편집 상태','검사 이유·자동 보정'],[[H(e['before']),H(e['raw'])+'<small>'+H(e['raw_action'])+'</small>',H(e['after'])+'<small>'+H(e['outcome'])+'</small>',H('; '.join(ISSUE.get(i['code'],i['code']) for i in e['issues']))+'<small>'+H('; '.join(z['kind'] for z in e['repairs']))+'</small>'] for e in trace])
    rid=latest['run_ids'][0 if arm=='saved' else 1];path=r.ROOT/'experiments/runs'/rid/'private/records'/key/'generation_call/parsed.json'
    if path.exists():
     response=r.read(path)
     content+='<details><summary>Qwen이 보류·적용한 이유</summary>'+''.join('<p>'+H(e['edit_id'])+': '+H(e['reason'])+'</p>' for e in response['edits'])+'</details>'
   else:content+='<p>'+H(STATUS[x['status']])+' '+H(x.get('error',''))+'</p>'
  content+='</details></article>'
 content+='</section><section id="next"><h2>다음에 무엇을 고쳐야 하나?</h2>'+table(['문제','수정 제안','확인 방법'],[[H(x) for x in row] for row in notes.get('next',[])])+'<p>위 항목은 후속 수정안입니다. 이번 실행 중에는 KG·생성 코드·검사 조건을 바꾸지 않았습니다. 새 적용 전 범위를 채팅에서 확인합니다.</p></section>'
 content+='<footer><h2>검증과 기록</h2><p>실행 전 자동 검사 10개 통과. 기존 검토자가 동일 전달 자료·답안 혼입 방지·잘못된 형태 번호 보존을 확인했습니다. 검토자의 ‘실패와 원문 출력 구별’, ‘28문장 짝 비교 분모’, ‘토큰 집계 호환’ 지적을 반영했습니다.</p><p>실행 전후 입력·카드·분석·실행 코드 해시 일치: <strong>'+H(summary['source_and_runtime_unchanged'])+'</strong>. 상세 요청·응답·원시 제안·검사·최종 출력은 실행 폴더에 보존했습니다.</p><details><summary>재현 파일 위치</summary><p>'+H(root)+'</p>'+''.join('<p>'+H(x)+'</p>' for x in latest['run_ids'])+'</details><p>문장 자연스러움의 새 사람 평가는 아직 하지 않았습니다. 보고서는 변경 수를 정확도라고 부르지 않습니다.</p></footer></main></html>'
 (r.HERE/'private/report.html').write_text(content,encoding='utf-8')
 print(r.dumps({'paired_cases':len(paired),'arms':arms,'variation':variation}),flush=True)
if __name__=='__main__':main()
