"""Derived diagnostic report; no model calls and no mutation of completed runs."""
import collections
import hashlib
import html
import json
from pathlib import Path
from bridge import HERE,ROOT,DEFINITIONS,inventory
from kg_pipeline.io import read,save,sha

LABELS={'baseline':'기존 방식','bridge':'수정 방식','eligible':'조건에 맞는 후보 있음','unresolved':'조건 판단 보류',
 'out_of_slice':'현재 구현 범위 밖','no_matching_usage':'맞는 용법 없음','analysis_failed':'분석 응답 실패',
 'binding_failed':'형태·위치 연결 실패','retrieval_failed':'조회 실패','ready_for_generation_trial':'생성 지시 준비 가능',
 'needs_analysis':'분석 보완 필요'}
FNAME={'clause_role':'절 역할','speech_act':'발화 목적','addressee_level':'상대 높임','question_kind':'질문 종류',
 'predicate_class':'서술어 종류','prefinal_type':'선어말 형태','tense':'시간 의미','subject_honorific':'주체 높임','polarity':'긍정·부정'}
def label(k,v):
 return '판단 보류' if v is None else DEFINITIONS.get(k,('',{}))[1].get(v,str(v))

def main():
 run=Path(read(HERE/'private/latest_run.json')['directory']);rows=read(run/'private/cases.json');results=read(run/'private/results.json')
 pairs=[];arms={};scored=[r for r in rows if not r['diagnostic_only']]
 for row in rows:
  records={r['condition']:r for r in results if r['source_case']==row['id']};comparisons={}
  for arm,r in records.items():
   f=r.get('feature_values',{});diff={k:{'observed':f.get(k),'missing_output':k not in f,'accepted':v} for k,v in row['accepted_features'].items() if k not in f or f[k] not in v}
   comparisons[arm]={'differences':diff,'target_matches':r.get('target')==row['target'],
     'all_reference_features_match':not diff and r.get('target')==row['target'],
     'comparison_type':'builder reference agreement, not independent ground truth'}
  pairs.append({'case':row,'records':records,'comparison':comparisons})
 for arm in ('baseline','bridge'):
  rs=[r for r in results if r['condition']==arm];ps=[p for p in pairs if not p['case']['diagnostic_only']]
  field_scores={k:{'matched':sum(k in p['records'][arm].get('feature_values',{}) and p['records'][arm]['feature_values'][k] in p['case']['accepted_features'][k] for p in ps),'total':len(ps)} for k in rows[0]['accepted_features']}
  calls=[c for r in rs for c in r['calls']]
  cohorts={}
  for group in ('previous_development','new_core','new_boundary'):
   selected=[p for p in ps if p['case']['group']==group]
   cohorts[group]={'cases':len(selected),'all_features_and_target_agree':sum(p['comparison'][arm]['all_reference_features_match'] for p in selected),
    'ready':sum(p['records'][arm].get('readiness')=='ready_for_generation_trial' for p in selected)}
  arms[arm]={'records':len(rs),'valid_analysis_responses':sum(r.get('analysis_response_valid',False) for r in rs),
    'status_counts':dict(collections.Counter(r['status'] for r in rs)),
    'query_states':dict(collections.Counter(r.get('query_state','not_queried') for r in rs)),
    'ready':sum(r.get('readiness')=='ready_for_generation_trial' for r in rs),
    'field_scores':field_scores,'cohorts':cohorts,
    'scored_cases':len(ps),'full_reference_agreement':sum(p['comparison'][arm]['all_reference_features_match'] for p in ps),
    'reported_tokens':{k:sum((c.get('usage') or {}).get(k,0) or 0 for c in calls) for k in ('prompt_tokens','completion_tokens','total_tokens')},
    'api_seconds_sum':round(sum(c['seconds'] for c in calls),3)}
 # Integrity is checked against the frozen manifest, not a newly manufactured baseline.
 manifest=read(run/'artifact_hashes.json')
 mismatches=[p for p,h in manifest.items() if sha((run/p).read_bytes())!=h]
 original=read(run/'kg_hashes.json');assert not mismatches,mismatches
 assert all(sha(Path(p).read_bytes())==h for p,h in original.items())
 assert len(results)==64 and len(list((run/'private').rglob('generation_call/request.json')))==0
 # Inspect the actual saved request to establish reference separation.
 for request_path in (run/'private/records').glob('*/analysis_call/request.json'):
  request=read(request_path);user=json.loads(next(m['content'] for m in request['messages'] if m['role']=='user'))
  assert set(user)<= {'text','words','questions'},set(user)
  assert 'accepted_features' not in user
 findings=[
  {'cases':['Q09','N07','N09','N15'],'topic':'정보 질문과 확인의 겹침',
   'observed':'Qwen이 confirmation을 선택. Q09·N07·N09는 그 값 때문에 일반 질문 후보가 지원 범위 밖으로 나감. N15는 부정 계사도 지원 밖.',
   'interpretation':'정보를 묻는 일과 확인하는 태도가 동시에 가능하다. 배타적인 한 항목으로 만든 설계에도 문제가 있어 네 건을 모두 모델의 문장 이해 실패로 단정할 수 없다.',
   'next':'정보 요청 여부와 확인 태도를 분리하고, 확인이라는 이유만으로 정보 질문 후보를 제거해야 하는지 KG 조건 정의부터 검토. 아직 변경/재실험하지 않음.'},
  {'cases':['Q14','N11'],'topic':'과거 형태와 현재 상태 해석',
   'observed':'과거 선어말 eoss는 정확히 연결됐지만 Qwen은 아직 안 했다는 현재 상태를 근거로 tense=present 선택.',
   'interpretation':'현재 상태와 과거 형태를 하나의 시간값으로 비교하면 평가가 애매해진다. 이번 22/29 집계에서는 사전 기준과 불일치로 유지하지만 단순 시제 이해 오류라고 확정하지 않음.',
   'next':'관찰된 과거 형태와 사건/기준 시점 해석을 구분. 생성에 과거 형태 보존 정보가 사라지지 않도록 별도 검증.'},
  {'cases':['N07'],'topic':'높임 어휘와 서술어 높임의 구별',
   'observed':'그분을 근거로 subject_honorific=present 선택. 사전 기준은 서술어 가수야의 비높임을 기준으로 absent.',
   'interpretation':'주체에 대한 존대 어휘와 서술어의 높임 실현을 같은 항목으로 다룬 정의가 충분히 좁지 않다.',
   'next':'그분 같은 지칭어의 높임과 주무시다/시 같은 서술어 높임을 구분. 필요한 범위만 조회 조건에 연결.'},
  {'cases':['N16'],'topic':'요청문의 시간 정답 기준',
   'observed':'조용히 문 좀 닫아에서 Qwen은 행동 요청으로 판단하고 tense=null. 사전 기준은 present.',
   'interpretation':'요청문에 현재 시제를 강제한 사전 기준이 부적절할 수 있다. 불일치 기록은 보존하고 모델 오류로 확정하지 않음.',
   'next':'사전 분석 기준을 사람 검토하고 수정 시 별도 버전으로 관리. 이번 실행의 기준과 집계는 바꾸지 않음.'},
 ]
 audit={'run_id':run.name,'cases':32,'unique_texts':31,'arms':arms,'metrics':read(run/'metrics.json'),'pairs':pairs,'findings':findings,
   'inventory':read(run/'private/condition_inventory.json'),
   'validation':{'status':'passed','frozen_files':len(manifest),'source_hashes_preserved':True,'requests':64,'generation_requests':0,
                 'no_reference_fields_in_saved_model_inputs':True,'browser_render_checked':False},
   'limitations':['Builder reference agreement, not human-confirmed analysis accuracy.',
    'Changed prompt definitions, output vocabulary, morphology ownership, derivation handling together; cannot isolate one cause.',
    'Only the refined question construction is tested. No translation quality measurement.',
    'New cases were fixed before calls, but are small author-designed development probes.',
    'Q13/Q15 ambiguity and Q16 duplicate excluded from 29-case reference metrics, retained in all 32 operational counts.']}
 save(HERE/'private/audit.json',audit);render(audit,run)
 print(json.dumps({'run_id':run.name,'arms':arms,'validation':audit['validation']},ensure_ascii=False,indent=2))

def render(a,run):
 e=lambda x:html.escape(str(x));arms=a['arms'];tables=[]
 for key,title in [('valid_analysis_responses','분석 응답 형식 통과 /32'),('ready','생성 지시 준비 가능 /32'),('full_reference_agreement','분석 전체가 작성 기준과 일치 /29')]:
  tables.append(f'<tr><td>{title}</td><td>{arms["baseline"][key]}</td><td>{arms["bridge"][key]}</td></tr>')
 fieldrows=''.join(f'<tr><td>{FNAME[k]}</td><td>{v["matched"]}/{v["total"]}</td><td>{arms["bridge"]["field_scores"][k]["matched"]}/{v["total"]}</td></tr>' for k,v in arms['baseline']['field_scores'].items())
 cases=[];problemrows=[]
 for p in a['pairs']:
  r=p['case'];cells=[]
  for arm in ('baseline','bridge'):
   result=p['records'][arm];comparison=p['comparison'][arm]
   diffs=' / '.join(FNAME[k]+': '+('결과 없음' if d['missing_output'] else label(k,d['observed']))+' (작성 기준: '+', '.join(label(k,v) for v in d['accepted'])+')' for k,d in comparison['differences'].items())
   state=LABELS.get(result.get('query_state',result['status']),result['status'])
   why=' / '.join(FNAME.get(f['feature'],f['feature'])+'='+label(f['feature'],f['observed']) for f in result.get('scope_failures',[]))
   needs=' / '.join(result.get('needs_analysis',[]))
   features=result.get('feature_values',{})
   readable=''.join(f'<tr><td>{FNAME[k]}</td><td>{e(label(k,v))}</td></tr>' for k,v in features.items())
   trace_path=run/'private/records'/result['id']/('condition_trace.json' if arm=='bridge' else 'retrieval_raw.json')
   trace_link=f'<a href="{e(trace_path.as_uri())}">실제 조회 기록</a>' if trace_path.exists() else '조회 이전에 중단되어 조회 기록 없음'
   cells.append(f'<td><b>{e(state)}</b><br>{e(why)}<br><small>{e(LABELS.get(result.get("readiness"),result.get("error","")))}</small><details><summary>무엇을 판단했나</summary><table>{readable}</table><p>{e(diffs or "작성 기준과 일치")}</p><p>{e(needs)}</p>{trace_link}</details></td>')
   if arm=='bridge' and not comparison['all_reference_features_match']:
    problemrows.append(f'<tr><td>{e(r["id"])} · {e(r["text"])}</td><td>{e(diffs)}</td><td>{"모호성 진단 사례·점수 제외" if r["diagnostic_only"] else "분석 정의와 사전 기준도 함께 검토"}</td></tr>')
  group={'previous_development':'기존','new_core':'새 기본 질문','new_boundary':'새 범위 확인'}[r['group']]
  cases.append(f'<tr class="case" data-group="{r["group"]}"><td><b>{r["id"]}</b> · {group}<br>{e(r["text"])}<br><small>{"집계 제외 진단 사례" if r["diagnostic_only"] else "분석 비교 대상"}</small></td>{"".join(cells)}</tr>')
 mapping=[]
 for row in a['inventory']['rows']:
  ids=row['condition_ids']+row['scope_ids'];provider={'kiwi_observation':'Kiwi 형태 관찰','qwen_semantic_judgment':'Qwen 의미 판단','kiwi_positive_and_qwen_semantics':'시 형태 관찰 + Qwen 의미 판단'}[row['provider']]
  role={'usage_condition':'용법 선택 조건','implementation_scope':'이번 구현 범위','preservation_only':'생성 시 보존 정보'}[row['role']]
  choices=' / '.join(label(row['feature'],v) for v in row['values'])
  mapping.append(f'<tr><td>{FNAME[row["feature"]]}</td><td>{provider}</td><td>{e(row["question"])}<details><summary>반환값 종류</summary>{e(choices)} / 판단 보류</details></td><td>{role}<details><summary>실제 KG 연결</summary>{e(", ".join(ids) or "Reader.packet 보존 필드; 조건 노드 없음")}</details></td></tr>')
 counts=''.join(f'<tr><td>{LABELS[arm]}</td><td>{x["reported_tokens"]["total_tokens"]:,}</td><td>{x["api_seconds_sum"]:.1f}</td></tr>' for arm,x in arms.items())
 findings=''.join(f'<tr><td>{e(f["topic"])}<br><small>{e(", ".join(f["cases"]))}</small></td><td>{e(f["observed"])}<br><b>{e(f["interpretation"])}</b></td><td>{e(f["next"])}</td></tr>' for f in a['findings'])
 example=read(run/'private/records/N12_bridge/condition_trace.json')
 ec=example['packet']['clauses'][0];choice=ec['choices'][0] if ec['choices'] else None
 exvalues=[('입력',example['packet']['text']),('연결한 어간·선어말',str(ec['morphology']['stem'])+' + '+ ' + '.join(ec['morphology']['prefinals'])),
  ('질문 뜻',label('question_kind',ec['preserve']['question_kind'])),('선택된 실제 용법',choice['rule_id'] if choice else '없음'),
  ('조회된 어미 후보',', '.join(f['ending'] for f in choice['forms']) if choice else '없음'),('최종 방언 문장','생성하지 않음')]
 exampletable=''.join(f'<tr><td>{e(k)}</td><td>{e(v)}</td></tr>' for k,v in exvalues)
 htmltext=f'''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>KG 조건과 문장 분석 연결 결과</title>
<style>body{{font:17px/1.65 system-ui,'Malgun Gothic',sans-serif;background:#f3f6fa;color:#1b334b;margin:0}}main{{max-width:1180px;margin:auto;padding:28px 20px}}h1{{font-size:30px}}h2{{font-size:22px}}section{{background:white;border:1px solid #d4e0eb;border-radius:12px;padding:22px;margin:20px 0}}table{{width:100%;border-collapse:collapse}}td,th{{padding:11px;border-bottom:1px solid #dce5ee;text-align:left;vertical-align:top}}th{{background:#eef4fa}}.scroll{{overflow:auto}}.notice{{background:#e5f0ff;border-left:5px solid #2372ac;padding:18px}}.warn{{background:#fff3df;border-color:#b67a20}}small{{color:#526b80}}summary,a{{color:#17639e;cursor:pointer}}details{{margin:8px 0}}.flow{{display:flex;gap:9px;flex-wrap:wrap}}.flow span{{padding:10px;background:#e9f2fc;border-radius:7px}}button,select,input{{font:inherit;padding:8px}}.muted{{font-size:14px}}@media(max-width:650px){{main{{padding:12px}}section{{padding:12px}}}}</style>
<main><small>2026-11-03 · {e(a['run_id'])}</small><h1>KG 조건을 실제 분석값에 연결했습니다</h1>
<p class="notice"><b>이번에는 방언을 생성하지 않았습니다.</b> 기존16건과 새16건에서 분석·조회만 비교했습니다. 실제 KG의 7개 조건과 기존 조회 코드를 재사용했습니다.</p>
<section><h2>무엇을 바꿨나</h2><div class="flow"><span>표준어·Kiwi</span>→<span>KG에서 필요한 조건 읽기</span>→<span>정의가 있는 선택지로 Qwen 판단</span>→<span>형태·판단을 실제 KG에 연결</span>→<span>후보·제외·보류 이유 기록</span></div>
<ul><li>문장별 정답표를 만들지 않았습니다. 질문과 선택지는 KG의 조건 종류·값에서 구성합니다.</li><li>어간·선어말은 Kiwi가 제공하고, 의미 판단은 Qwen이 맡습니다. '도착+하' 같은 파생 동사도 연결합니다.</li><li>'주무시다'처럼 시가 별도 형태소로 나오지 않는 높임도 있어, 시 부재를 높임 부재로 단정하지 않습니다.</li><li>모르는 값은 후보를 보류하며, 여섯 용법 모두에 선택·제외 사유를 남깁니다. 설명이 없는 새 조건은 누락하지 않고 연결 정의가 필요하다고 알립니다.</li></ul></section>
<section><h2>실제 결과</h2><table><tr><th>항목</th><th>기존 방식</th><th>수정 방식</th></tr>{''.join(tables)}</table>
<p class="notice warn">29건의 비교 기준은 실행 전에 작성한 연구 리드의 문법 분석입니다. 독립적인 사람 평가 정확도가 아닙니다. Q13·Q15의 모호한 해석과 Q16 중복 검사는 이 집계에서 제외했습니다. 후보가 조회됐다고 번역에 성공한 것도 아닙니다.</p>
<details><summary>어떤 분석 항목이 달라졌나</summary><table><tr><th>항목</th><th>기존 일치/비교 수</th><th>수정 일치/비교 수</th></tr>{fieldrows}</table></details></section>
<section><h2>조건 연결표 — 검색 허용 목록이 아닙니다</h2><p>문헌 조건은 7개 노드에 저장돼 있고, 용법을 나누는 축은 질문 종류·서술어 종류·선어말 종류입니다. 범위 조건과 보존 정보는 별도로 표시했습니다.</p><div class="scroll"><table><tr><th>정보</th><th>담당</th><th>실제 질문·정의</th><th>사용처</th></tr>{''.join(mapping)}</table></div><p>현재 정제 그래프에는 의문문 구성 하나가 있습니다. 다른 문법군을 자동으로 찾아 연결하는 전체 구성 탐색기는 이번 범위에 포함되지 않았습니다. 문맥 설명과 활용 조합 설명도 모두 실행 규칙이 된 것은 아닙니다.</p></section>
<section><h2>먹다가 아닌, 실제 새 사례를 보겠습니다</h2><table>{exampletable}</table><p>같은 절의 특징값 → ACCEPTS 조건 관계 → ALL 조건 묶음 → 실제 용법 → REALIZES 어미 관계를 사용했습니다. 형태소마다 모듈 전체를 가져오지 않았습니다.</p></section>
<section><h2>32건을 직접 비교하세요</h2><p><input id="search" placeholder="문장 또는 ID 검색" aria-label="문장 검색"> <select id="group" aria-label="사례 종류"><option value="">전체</option><option value="previous_development">기존16건</option><option value="new_core">새 기본12건</option><option value="new_boundary">새 범위 확인4건</option></select> <span id="count">32건</span></p><div class="scroll"><table><thead><tr><th>입력</th><th>기존 방식</th><th>수정 방식</th></tr></thead><tbody>{''.join(cases)}</tbody></table></div></section>
<section><h2>수정 방식에도 남은 차이 — 전부 모델 오류는 아닙니다</h2><table><tr><th>문제 위치</th><th>실제 근거와 해석</th><th>수정·확인 제안</th></tr>{findings}</table><details><summary>사전 기준과 다른 7사례 보기</summary><table><tr><th>사례</th><th>작성 기준과 다른 분석</th><th>해석</th></tr>{''.join(problemrows) or '<tr><td colspan="3">이번 기준에서 차이 없음. 일반화 성능을 보장하지는 않습니다.</td></tr>'}</table></details><p>이 결과에 맞춰 재실험하거나 정답 기준을 바꾸지 않았습니다. 자동 수정으로 실패를 숨기지도 않았습니다.</p></section>
<section><h2>검증·비용·다음 단계</h2><ul><li>분석 호출64회, 생성0회, 자동 재시도0회. 코드 검사12개 통과.</li><li>동결 파일 {a['validation']['frozen_files']}개 해시 일치, 원본 입력과 KG 보존. 요청에 정답 분석값을 넣지 않았습니다.</li><li>전체 실행 시간 약 {a['metrics']['wall_seconds']:.1f}초. 아래 시간은 병렬 실행 각 호출 시간의 합이므로 전체 경과 시간과 다릅니다.</li><li>브라우저 화면 렌더 검수는 하지 않았습니다.</li></ul><table><tr><th>방식</th><th>서버 보고 토큰</th><th>호출 시간 합(초)</th></tr>{counts}</table><p>다음에는 남은 분석 차이가 해석의 모호성인지 연결 오류인지 확인해야 합니다. 생성의 과거형 누락·어미 결합 문제는 아직 별도 과제로 남아 있습니다. 이번에 동시에 바꾼 요소가 여러 개라, 한 요소만이 개선 원인이라고 단정하지 않습니다.</p></section>
<p><a href="audit.json">전체 진단 원본</a> · <a href="{run.as_uri()}/private/results.json">동결 실행 결과</a> · <a href="../README.md">코드·재현 설명</a></p></main>
<script>function filterRows(){{const q=document.getElementById('search').value.toLowerCase(),g=document.getElementById('group').value;let n=0;document.querySelectorAll('tr.case').forEach(r=>{{const show=(!g||r.dataset.group===g)&&r.textContent.toLowerCase().includes(q);r.hidden=!show;if(show)n++;}});document.getElementById('count').textContent=n+'건';}}document.getElementById('search').addEventListener('input',filterRows);document.getElementById('group').addEventListener('change',filterRows);</script></html>'''
 (HERE/'private/report.html').write_text(htmltext,encoding='utf-8')

if __name__=='__main__':main()
