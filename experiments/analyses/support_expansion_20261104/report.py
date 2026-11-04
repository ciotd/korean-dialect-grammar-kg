"""Report measured support, actual outputs, and traceable limits separately."""
from pathlib import Path
import json,html,collections,sys,os
H=Path(__file__).resolve().parent;R=H.parents[2];sys.path.insert(0,str(R/'src'))
from kg_pipeline.io import read,save,sha
from research_management.core import Registry
from research_management.work import WorkStore
BASE=R/'experiments/runs/20261103T111250623634Z_boundary_qwen_full50'
def e(x):return html.escape(str(x))
def href(p):return Path(os.path.relpath(p,H/'private')).as_posix()
def table(head,rows):
 return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+e(x)+'</th>' for x in head)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+e(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def link(p,label):return '<a href="'+e(href(p))+'">'+e(label)+'</a>'
def probe(index):
 if not (H/'private'/index).exists():return None
 paths={a:Path(p) for a,p in read(H/'private'/index).items()};results={a:read(p/'private/results.json') for a,p in paths.items()};metrics={a:read(p/'metrics.json') for a,p in paths.items()};records=[];affected=0;field_differences=collections.Counter();surface_checks={'control':[],'surface':[]}
 for left,right in zip(results['control'],results['surface']):
  assert left['id']==right['id'] and left['input_text']==right['input_text']
  packets={}
  for a,r in [('control',left),('surface',right)]:
   d=paths[a]/'private/records'/r['id'];packets[a]=read(d/'generation_packet.json');req=read(d/'generation_call/request.json');raw=read(d/'generation_call/parsed.json')
   assert json.loads(req['messages'][-1]['content'])==packets[a] and raw['output_text']==r['output_text']
   internal=read(d/'actions_internal.json')
   for action in internal:
    if action['rule_id'] not in ('SEM_DECL_HAEYE_EO','SEM_SUP_POLITE_Q_EO'):continue
    assert action['target'].endswith('요')
    piece=next((x['replacement'] for x in r.get('checks',{}).get('pieces',[]) if x['target_id']==action['target_id']),None)
    surface_checks[a].append({'id':r['id'],'target_id':action['target_id'],'source':action['target'],'actual':piece,'contract_match':piece==action['target'][:-1]+'예'})
  for a,b in zip(packets['control']['actions'],packets['surface']['actions']):
   assert all(a[k]==b[k] for k in ('target_id','target','span','rule_id','preserve'))
   changed={k for k in set(a)|set(b) if a.get(k)!=b.get(k)};field_differences.update(changed);affected+=bool(changed)
  records.append({'id':left['id'],'input':left['input_text'],'control':left['output_text'],'variant':right['output_text'],'different':left['output_text']!=right['output_text']})
 same_prompt=(paths['control']/'generation_prompt.txt').read_bytes()==(paths['surface']/'generation_prompt.txt').read_bytes()
 reg=Registry(R);validation=[]
 for d in paths.values():reg.register(d.name);v=reg.verify(d.name);assert v['status']=='passed';validation.append(v)
 return {'run_ids':{a:p.name for a,p in paths.items()},'metrics':metrics,'same_system_prompt':same_prompt,'fixed_input_records':len(records),'fixed_positions':sum(r['supported_targets'] for r in results['control']),'changed_packet_positions':affected,'changed_action_fields':dict(field_differences),'different_outputs':sum(r['different'] for r in records),'records':records,'validation':validation,'surface_contract_checks':surface_checks,'surface_contract_counts':{a:{'matched':sum(x['contract_match'] for x in v),'total':len(v)} for a,v in surface_checks.items()},'same_quality_checks':'frozen source actions including same surface-preservation postcondition; no composer rerun'}
def main():
 final=Path(read(H/'private/latest_full50.json')['directory']);rows=read(final/'private/results.json');m=read(final/'metrics.json');old=read(BASE/'private/results.json');bm={x['id']:x for x in old};om=read(BASE/'metrics.json')
 assert [(x['id'],x['input_text']) for x in rows]==[(x['id'],x['input_text']) for x in old]
 refs={r['id']:r for r in map(json.loads,(R/'data/derived_private/gyeongsang_reference50_20261030_v1/references.jsonl').read_text('utf8').splitlines())}
 audit=read(H/'private/audit46.json');sm=read(H/'private/audit_summary.json');replay=read(H/'private/replay_summary_r7.json');graph=read(final/'private/graph.json');g={n['id']:n for n in graph['nodes']}
 checks=[];reg=Registry(R)
 for d in sorted((R/'experiments/runs').glob('*_support_expansion_*')):
  if not (d/'metrics.json').exists():continue
  reg.register(d.name);check=reg.verify(d.name);assert check['status']=='passed',check
  post=read(d/'postflight.json');assert all(post[k] for k in ('graph_unchanged','code_unchanged','inputs_unchanged'));checks.append(check)
 actual=[];pieces=[];with_actions=0;unchanged_with_actions=[];no_action_changes=[]
 for r in rows:
  d=final/'private/records'/r['id'];p=read(d/'generation_packet.json');q=read(d/'generation_call/request.json');response=read(d/'generation_call/parsed.json')
  assert json.loads(q['messages'][-1]['content'])==p and response['output_text']==r['output_text']
  assert all(not any(k in a for k in ('expected_surface','copula_surface_candidates','composer_comparison')) for a in p['actions'])
  with_actions+=bool(p['actions'])
  if p['actions'] and r['output_text']==r['input_text']:unchanged_with_actions.append(r['id'])
  if not p['actions'] and r['output_text']!=r['input_text']:no_action_changes.append(r['id'])
  for t in r['targets']:
   action=next((a for a in p['actions'] if a['target_id']==t['target_id']),None)
   piece=next((x for x in r['checks']['pieces'] if x['target_id']==t['target_id']),None)
   record={'id':r['id'],'target_id':t['target_id'],'source':r['input_text'][slice(*t['span'])],'readiness':t['readiness'],'rules':t.get('rules',[]),'features':t.get('features'),'needs':t.get('needs_analysis',[]),'action':action,'qwen_piece':piece}
   actual.append(record)
   if piece:pieces.append(record)
 summary={'run_id':final.name,'metrics':m,'baseline_run':BASE.name,'baseline_metrics':om,'records_with_actions':with_actions,'unchanged_with_actions':unchanged_with_actions,'changed_without_actions':no_action_changes,'replay_same_analysis':replay,'audit46':sm,'all_outputs_equal_qwen_response':True,'generation_packets_equal_requests':True,'completed_composer_forms_not_sent':True,'input_texts_unchanged':True,'quality_accuracy':'not_scored','verification_files':sum(v['checked_files'] for v in checks)}
 probes={'handoff':probe('latest_handoff.json'),'realization':probe('latest_realization.json'),'typed':probe('latest_typed.json'),'prefix':probe('latest_prefix.json'),'prompt_r1':probe('latest_prompt_contract_r1.json'),'prompt_r2':probe('latest_prompt_contract_r2.json')};summary['additional_probes']=probes
 save(H/'private/summary.json',summary);save(H/'private/all_targets_latest.json',actual);save(H/'private/validation.json',checks)
 warning_labels={'documented_surface_structure_mismatch':'결합 후 형태 재확인','lexical_stem_not_observed_or_kiwi_uncertain':'어휘 보존 재확인','prefinal_observation_changed_or_kiwi_uncertain':'시제·높임 형태 재확인','selected_ending_not_at_target_end':'선택 어미 반영 재확인','outside_supported_spans_changed':'허용 위치 밖 변경','copula_composition_requires_review':'명사+계사 결합 재확인'}
 h='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>미지원 46곳 점검과 첫 확장 결과</title><style>
 body{font:16px/1.75 system-ui,"Malgun Gothic",sans-serif;color:#203047;background:#f3f6fa;margin:0}main{max-width:1150px;margin:auto;padding:28px 20px}h1{font-size:30px;line-height:1.4}h2{font-size:23px;margin-top:40px}h3{font-size:18px}p{max-width:950px}.lead,.box,details{background:white;border:1px solid #dbe3ee;border-radius:12px;padding:18px;margin:12px 0}.lead{border-left:6px solid #2764ad}.muted{color:#58677b;font-size:14px}.flow{display:flex;gap:8px;flex-wrap:wrap;align-items:center}.flow b{padding:12px;background:#e5edf9;border-radius:8px}.scroll{overflow:auto}table{width:100%;border-collapse:collapse;background:white}th,td{padding:12px;text-align:left;vertical-align:top;border-bottom:1px solid #dce3ed}th{background:#eaf0f7;white-space:nowrap}details summary{cursor:pointer;font-weight:650}a{color:#165fa7}input,select{font:inherit;padding:8px;max-width:100%;margin:6px}nav{display:flex;gap:16px;flex-wrap:wrap}.bar{height:16px;background:#4381bc;border-radius:4px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f7f9fc;padding:12px;font-size:13px}.pill{display:inline-block;background:#eff3f8;border-radius:6px;padding:2px 8px;margin:2px;font-size:13px}.warn{border-left:5px solid #bf7223}td{min-width:90px}.cases td:first-child{min-width:90px;width:100px}footer{padding:30px 0;color:#64748b}</style><main>
 <p class="muted">2026-11-04 · 기존 결과 보존 · 최종 작성자 Qwen · 회귀 실험</p><h1>미지원 46곳을 나누어 확인하고,<br>근거가 준비된 5곳을 먼저 연결했습니다.</h1>
 <nav><a href="#answer">핵심 결과</a><a href="#audit">46곳 원인</a><a href="#changes">실제 수정</a><a href="#outputs">50문장 결과</a><a href="#next">남은 작업</a><a href="#evidence">검증 근거</a></nav>
 <section class="lead" id="answer"><b>이번에 확인한 점</b><p>‘KG 지원 밖’은 한 종류의 문제가 아니었습니다. 연결만 빠진 곳도 있고, 문헌의 조건을 더 읽어야 하는 곳도 있습니다. 표준어와 방언에서 같은 형태를 쓸 수 있는 곳까지 모두 실패로 세면 진단이 잘못됩니다.</p>
 <p>기존 모델 분석을 그대로 두고 다시 조회했을 때, 전달 준비가 된 위치가 <b>14 → 19곳</b>으로 늘었습니다. 이 5곳은 실제 연결 보완 효과입니다. 하지만 이것은 번역 정확도가 아닙니다.</p></section>'''
 h+=table(['비교 항목','직전 50건','이번 50건'],[
 ('입력 / 종결 위치','50 / 62',f"{m['records']} / {m['target_count']}"),('KG 지시를 전달한 위치',om['readiness_counts'].get('ready_for_generation_trial',0),m['readiness_counts'].get('ready_for_generation_trial',0)),('일부라도 글자가 바뀐 문장',om['changed_records'],m['changed_records']),('최종 출력 확보',om['valid_output_records'],m['valid_output_records']),('모델 호출',om['api_attempts'],m['api_attempts']),('총 소요 시간(초)',om['wall_seconds'],m['wall_seconds']),('전체 토큰',om['reported_usage']['total_tokens'],m['reported_usage']['total_tokens']),('자연스러움 점수','새 평가 없음','새 평가 없음')])
 h+='<p class="muted">50건 재실험은 모델이 분석부터 새로 수행했습니다. 같은 입력·모델명·온도·시드를 사용했지만 결과가 완전히 결정적이라는 보장은 없습니다. ‘같은 분석 재조회’와 구분해서 읽어주세요. 여러 부분을 보완했으므로 위 전체 차이를 KG만의 효과로 보지 않습니다.</p>'
 h+='<h2 id="audit">1. 미지원 46곳은 왜 막혔나?</h2><p>한 문장에 종결 위치가 여러 개 있어 50문장에서 62곳을 검사합니다. 직전의 62곳 중 준비 14곳, 추가 분석 필요 2곳을 제외한 <b>46곳 전체</b>를 대조했습니다. 아래는 첫 조치를 정하기 위한 주원인 분류이며, 별도로 10곳에는 분석 문제도 겹칩니다.</p>'
 h+=table(['주원인','위치 수','뜻'],[(k,v,{'표준어와 공유하는 형태 가능':'같은 어미를 쓰는 것이 곧 오류는 아님','근거 있는 구성의 실행 연결 누락':'이번에 조건 관계를 추가한 5곳','기존 관련 지식의 조건 정제 필요':'자료는 관련되지만 적용 조건을 더 정리해야 함','문헌별 관찰 범위 차이':'지역·자료마다 달라 보편 규칙으로 합치면 안 됨','결합·변이 추가 정제 필요':'어미 결합·뜻·높임을 더 구별해야 함','형태 분석·투영 충돌':'분석기가 본 형태와 실제 용법의 충돌','같은 기능·높임의 대응 미확보':'관련 자료는 있으나 같은 조건의 형태는 미확보'}[k]) for k,v in sm['primary_cause_counts'].items()])
 h+='<details><summary>46곳 전체의 원인과 다음 조치 보기</summary>'+table(['ID / 위치','원래 부분','문법군','주원인','다음 조치','겹친 분석 문제'],[(x['id']+' / '+x['target_id'],x['target'],x['group_label'],x['primary_cause'],x['next_check'],x.get('analysis_issue') or '—') for x in audit])+'</details>'
 h+='<h2 id="changes">2. 무엇을 실제로 고쳤나?</h2><div class="flow"><b>Kiwi로 형태·위치 확인</b>→<b>Qwen으로 뜻·절 관계 판단</b>→<b>KG 조건 관계 조회</b>→<b>맞는 결합 정보 전달</b>→<b>Qwen이 문장 전체 작성</b></div>'
 h+=table(['수정','실제 예 / 효과','이번에 하지 않은 일'],[
 ('긍정 현재 명사 서술 연결','예요·에요 + 일반명사 + 평서 + 공손 조건 → 라예 결합 정보','과거·부정·거예요 같은 의존명사까지 확대하지 않음'),
 ('공손한 어요 질문 연결','어요·아요 + 정보 질문 + 용언 → 어예 결합 정보','나요·ㄹ까요·명령까지 확대하지 않음'),
 ('모르는 값 처리','명사 종류를 판단하지 못하면 미확정으로 보존','모르는 것을 허용 또는 금지로 확정하지 않음'),
 ('근거 종류 분리','직접 용례 / 원문 해석 / 구현 범위 결정을 구별','검토자 합의를 문헌 사실로 바꾸지 않음'),
 ('계사 조합 설명','이+라예 결합과 관찰되지 않은 -시- 추가 금지를 전달','완성된 정답이나 조합기 출력을 Qwen에 주지 않음')])
 h+='<details><summary>실제 그래프 연결 한 가지: 현재 명사 서술</summary><div class="flow"><b>관찰값: 예요·일반명사</b>→<b>ACCEPTS: 조건값 연결</b>→<b>ALL: 같은 절의 조건 모두 대조</b>→<b>SEM_SUP_COP_PRESENT</b>→<b>REALIZES: 라예</b></div><p>문헌 D02 PDF 199의 ‘왕이라예’ 용례와 설명을 연결했습니다. 친구·선생님·동료라는 정답 문장을 저장한 규칙은 아닙니다. 조회는 조건 노드와 실제 관계를 사용하며, 규칙마다 별도 Python 함수를 만든 방식도 아닙니다.</p></details>'
 h+='<h3>두 검토자 의견은 어떻게 반영했나?</h3>'+table(['검토','발견','처리'],[
 ('Codex','미확정 값이 불일치로 처리됨 / 조건의 해석 근거가 빈 배열처럼 보임','값 처리와 출처 전달을 수정하고 반례 검사 추가'),('Claude','직접 근거와 보조 자료 혼합 / 계사 조합·높임 설명 모호','근거 역할 분리, 결합 설명 보완, 후보와 문헌 사실 구분'),('리드의 재확인','옛 중간 지시문이 실제 Qwen에 전달됐다는 검토자의 추정','최종 요청을 확인해 반박·정정. 실패 원인으로 집계하지 않음'),('두 검토자 후속 확인','r7 수정 범위에서 추가 실행 차단 문제 없음','독립 읽기 검토 완료. 새 출력의 자연스러움 인증은 아님')])
 h+='<p>'+link(H/'private/reviewers/codex/followup_review.md','Codex 후속 검토')+' · '+link(H/'private/reviewers/claude/followup_review.md','Claude 후속 검토')+' · '+link(H/'reviewer_resolution.md','수용·보류·정정 기록')+'</p>'
 h+='<h2>추가 진단: 정보를 받았는데 왜 잘못 활용했나?</h2><p>먼저 분석·선택을 고정한 17문장을 비교했습니다. 이는 새 데이터셋이 아니라, 이번 50개 중 실제 KG 지시를 받은 문장 전부입니다. 적용 위치는 19곳입니다.</p>'
 h+='<div class="box warn"><b>추가 비교의 결론: 새 대안을 운영 경로에 채택하지 않았습니다.</b><p>r7의 새 지식 5곳 연결은 유지합니다. 그러나 r8/r9의 생성 대안은 일부 출력이 악화되거나 오류가 남아 비교용으로만 보존했습니다. 실제 요청·원시 응답을 두 검토자가 대조했고, 정보 누락이나 후처리 훼손으로 설명되지 않는 지시 불이행을 확인했습니다. 같은 요청도 일부 출력이 달라져 단회 차이를 확정적 효과로 보지 않습니다.</p></div><details><summary>실패한 대안까지 포함한 비교 과정 자세히 보기</summary>'
 for key,title in [('handoff','① 전달을 짧게 하고 원래 활용을 보존하라고 안내'),('realization','② KG의 결합형·결합 설명만 정정'),('typed','③ 수정 단위를 구분한 지시로 전달'),('prefix','④ 보존할 원문 부분까지 명시')]:
  pr=probes[key]
  if not pr:continue
  a=pr['metrics']['control'];b=pr['metrics']['surface'];h+='<h3>'+title+'</h3>'+table(['항목','기존 방식','비교 방식'],[('생성 호출',a['generation_calls'],b['generation_calls']),('전체 토큰',a['reported_usage']['total_tokens'],b['reported_usage']['total_tokens']),('호출별 경과시간 합(초)',round(a['record_seconds_sum'],2),round(b['record_seconds_sum'],2)),('최종 출력 확보',a['valid_output_records'],b['valid_output_records'])])
  h+='<p>같은 시스템 프롬프트: '+('예' if pr['same_system_prompt'] else '아니요')+' · 전달 정보가 바뀐 적용 위치: '+str(pr['changed_packet_positions'])+' / 19 · 최종 출력이 달라진 문장: '+str(pr['different_outputs'])+' / 17. 시간은 병렬 처리 중 각 호출 시간을 더한 값이며 독립 속도 벤치마크가 아닙니다.</p>'
  h+='<p><b>원래 활용형 보존 검사(자연스러움 점수 아님): '+str(pr['surface_contract_counts']['control']['matched'])+'/9 → '+str(pr['surface_contract_counts']['surface']['matched'])+'/9.</b> 아/어요 계열의 지정된 9위치에서 ‘요 앞부분 유지+예’라는 동일 지시를 따랐는지만 확인했습니다.</p>'
  if key=='handoff':h+='<p>설명 축약과 보존 안내만으로는 설명해예·같어예가 해소되지 않았습니다. 따라서 긴 JSON만이 원인이라는 설명은 부족합니다.</p>'
  elif key=='realization':h+='<p>적용 조건과 연결은 그대로 두고, 기존 평서 1규칙과 새 질문 1규칙의 실현 정보를 바꿨습니다. 그러나 실제로는 설명했예·맛있예처럼 출력돼 나빠졌습니다. 이 버전은 그대로 채택하지 않았습니다. ‘예’가 전체 어미의 대체값으로 읽히는 전달 형식이 남아 있었기 때문일 가능성을 다음 비교로 확인했습니다.</p>'
  elif key=='typed':h+='<p>②의 문법 의미는 유지하되, ‘마지막 요만 예로 바꾸고 앞부분은 보존’이라는 수정 단위를 별도 필드로 전달했습니다. 이 유형에 한해 어간부터 재조합하도록 읽힐 수 있는 중복 필드를 제거했습니다. 코드가 완성형을 작성해 전달한 것은 아닙니다. 두 조건 모두 이전과 같은 원문 보존 검사 기준으로 대조했고 보조 조합기는 재실행하지 않았습니다. 시스템 안내도 함께 바뀌므로 필드 하나만의 효과라고 주장하지 않습니다.</p>'
  else:h+='<p>같은 지시·조건에서 원문에서 떼어낸 ‘설명했어’ 같은 보존 부분만 추가했습니다. 방언 완성 답안은 전달하지 않았습니다. 그런데도 설명했예·같예 등의 위반이 남았습니다. 따라서 더 많은 카드를 추가하기 전에 현재 생성 설정이 기본 수정 지시를 얼마나 따르는지 별도 진단해야 합니다. 모델 자체의 능력 부족인지, 방언 생성이라는 작업 지시와의 충돌인지는 아직 구분하지 못했습니다.</p>'
  h+='<details><summary>고정 17문장의 두 출력 비교</summary>'+table(['ID','입력','기존 방식','비교 방식'],[(r['id'],r['input'],r['control'],r['variant']) for r in pr['records']])+'</details>'
 h+='<h3>⑤ 시스템 지시 두 문장만 수정하고 각 조건을 2회 반복</h3><p>원문 보존 지시와 ‘축약을 판단하라’는 공통 지시의 충돌 가능성을 추가 확인했습니다. 동일한 패킷을 유지한 채 공통 지시 두 문장만 수정했습니다. 두 반복 모두 9위치 중 4곳만 동일 형태 보존 검사를 만족해, 이 수정만으로도 해결되지 않았습니다.</p>'
 h+=table(['반복','기존 지시: 보존 검사','수정 지시: 보존 검사','분모'],[(key,str(probes[key]['surface_contract_counts']['control']['matched']),str(probes[key]['surface_contract_counts']['surface']['matched']),'9위치') for key in ('prompt_r1','prompt_r2') if probes[key]])
 h+='</details><p>'+link(H/'private/reviewers/codex/results_review.md','실제 요청·원시 응답 검토')+' · '+link(H/'private/reviewers/claude/results_review.md','출력·문법 해석 검토')+'</p>'
 h+='<h2 id="outputs">3. 실제 Qwen 출력 50개</h2><p>이전 출력·이번 출력·사용자가 승인한 참조 표현을 나란히 보여줍니다. 참조 표현은 아래 비교 화면에만 사용했으며 모델 요청에는 넣지 않았습니다. 자동 경고는 재확인 표시이고, 경고가 없다고 자연스러움이 보장되지는 않습니다.</p><input id="search" placeholder="ID 또는 문장 검색"><select id="filter"><option value="all">모두</option><option value="warn">자동 경고 있음</option><option value="same">원문 유지</option><option value="changed">일부 변경</option><option value="new">새 규칙 전달</option></select><span id="count"></span><div id="cases">'
 for r in rows:
  targets=[x for x in actual if x['id']==r['id']];new=any(any(z.startswith('SEM_SUP_') for z in x['rules']) for x in targets);warn=bool(r['checks']['warnings']);same=r['output_text']==r['input_text'];tag=' '.join(['warn' if warn else '', 'same' if same else 'changed','new' if new else ''])
  h+='<details class="case cases" data-tags="'+tag+'" data-search="'+e(r['id']+' '+r['input_text'])+'"><summary>'+e(r['id'])+' · '+e(r['input_text'])+(' <span class="pill">새 규칙</span>' if new else '')+(' <span class="pill">확인 필요</span>' if warn else '')+'</summary>'
  h+=table(['구분','문장'],[('원문',r['input_text']),('직전 Qwen',bm[r['id']]['output_text']),('이번 Qwen',r['output_text']),('승인 참조',refs[r['id']]['reference'])])
  h+=table(['위치','원래 부분','상태','선택 규칙','Qwen이 만든 부분'],[(x['target_id'],x['source'],{'ready_for_generation_trial':'정보 전달','out_of_slice':'현재 실행 범위 밖','no_matching_usage':'맞는 조건 조합 없음','needs_analysis':'분석 확인 필요'}.get(x['readiness'],x['readiness']),', '.join(x['rules']) or '—',(x['qwen_piece'] or {}).get('replacement','—')) for x in targets])
  if warn:h+='<p class="warn">'+e(' / '.join(warning_labels.get(w,w) for w in r['checks']['warnings']))+'</p>'
  for x in targets:
   if x['action']:
    a=x['action'];h+='<details><summary>'+e(x['target_id'])+'에 전달한 핵심 설명</summary>'+table(['항목','값'],[('어간',a['stem']),('보존할 선어말',', '.join(a['prefinals']) or '없음'),('바꿀 어미',a['source_final']),('결합 설명',' / '.join(a['composition']))])+link(final/'private/records'/r['id']/'targets'/x['target_id']/'trace.json','실제 조회 원본')+'</details>'
  h+=link(final/'private/records'/r['id']/'generation_packet.json','실제 모델 전달 원본')+'</details>'
 h+='</div><h2 id="next">4. 남은 작업과 끝나는 기준</h2>'
 h+=table(['순서','해야 할 일','완료 기준','예상과 다르면'],[
 ('이번 묶음 완료','46곳 진단 → 첫 2구성 확장 → 검토·검사 → 50건 실행','46곳 각각 원인·근거·조치 기록, 입력별 원본과 출력 확보','미확보는 보류 상태로 남김. 전체 지원 완료로 부르지 않음'),
 ('추가 진단 완료','같은 17입력에서 설명 축약 / 실현 정보 / 수정 단위 / 원문 보존 부분을 순서대로 비교','각 조건별 원문·실제 요청·출력·비용 보존','네 대안 모두 운영 채택을 보류. 현재r7유지'),
 ('다음 1','현재 서버 실행 명령으로 모델·템플릿·옵션을 확인하고 기본 편집/방언 지시 비교 설계','실제 설정을 기록하고, 같은 입력 반복에서 어느 조건이 실패하는지 분리','서버 문제로 단정하지 않음. 실행 명령은 사용자에게 요청 중. 이 단계에서는 전체 KG를 다시 바꾸지 않음'),
 ('다음 2','나요·ㄹ까요, 요청·금지, 약속 등 남은 문법군을 근거별 정제','각 문법군에 적용 조건·근거·반례·새 개발 예문과 실제 조회 경로 확보','자료가 충돌하면 후보로 남기고 필요한 판단만 사용자에게 요청'),
 ('다음 3','확장된 규칙을 연결하고 같은 50건 재실험','기존 지원이 깨지지 않고 실제 전달·최종 출력까지 추적 가능','새 오류는 첫 실패 단계별로 분리하여 수정'),
 ('그 이후','현대 경상도 표현의 사용자 평가와 별도 새 평가셋','뜻·높임·자연스러움 확인, 회귀셋과 독립셋 구별','현 자료만으로 자연스러움이 부족하면 지식 범위·모델 역할을 다시 판단')])
 h+='<p>지금 요청한 것은 새로운 연구 방향 승인이 아니라 <b>Qwen 서버를 켤 때 쓴 실행 명령어</b>입니다. 실제 모델·옵션을 확인하는 데 필요합니다. 서버 오류가 확인됐다는 뜻은 아닙니다. 문헌이 충돌하는 표현의 확정이나 최종 생성 주체 변경이 필요해지면 별도로 구체적인 선택지를 드립니다.</p>'
 h+='<h2 id="evidence">5. 검증과 자료 범위</h2>'
 h+=table(['항목','확인 결과'],[('자동 코드 검사','신규 17 + 기존 조회 39 + 기존 분석 17 + 수정단위 5 = 78개 통과'),('동일 분석 재조회','새 Qwen 호출 0회, 이전 14곳 유지 + 새 5곳'),('새 그래프',f"{len(graph['nodes'])}노드 / {len(graph['edges'])}관계 / 11실행 용법(기존9+신규2)"),('기존 지식 보존','r4 노드 내용·관계 보존 검사 통과'),('원문 접근','7개 PDF 해시 확인. 이번에는 관련 쪽 본문 대조와 2개 표 이미지 확인. 7종 전체 재정독은 아님'),('실행 무결성',f"{summary['verification_files']}개 파일 해시 확인. 입력·코드·KG 실행 중 불변"),('최종 작성자','50개 모두 저장된 Qwen 응답과 동일. 조합기 결과로 대체하지 않음'),('Neo4j','이번 버전은 실제 관계가 든 JSON 스냅샷을 조회. 실행 중 DB 적재·변경 없음'),('분모와 해석','50개 입력 / 62개 종결 위치. 미지원 감소·글자 변화는 정확도 점수가 아님')])
 h+='<details><summary>문헌별 직접 인용과 해석 구분</summary>'+table(['근거 ID','문헌 PDF 쪽','짧은 원문','해석'],[(n['id'],n['properties']['document_id']+' / '+str(n['properties']['pdf_page']),n['properties']['quote'],n['properties'].get('builder_paraphrase','')) for n in graph['nodes'] if n['id'].startswith('EV_SUP_')])+'</details>'
 h+='<p>'+link(final/'metrics.json','실험 수치 원본')+' · '+link(final/'config.json','실행 설정')+' · '+link(H/'private/summary.json','집계 원본')+' · '+link(H/'private/replay_summary_r7.json','동일 분석 재조회')+' · '+link(H/'README.md','재현 방법')+'</p><footer>Run ID: '+e(final.name)+'<br>문장 변경과 문헌 인용이 포함되어 로컬 private 폴더에 보관합니다.</footer></main><script>function filter(){let q=document.querySelector("#search").value.toLowerCase(),f=document.querySelector("#filter").value,n=0;document.querySelectorAll(".case").forEach(x=>{let yes=x.dataset.search.toLowerCase().includes(q)&&(f==="all"||x.dataset.tags.split(" ").includes(f));x.hidden=!yes;if(yes)n++});document.querySelector("#count").textContent=n+" / 50";}document.querySelector("#search").addEventListener("input",filter);document.querySelector("#filter").addEventListener("change",filter);filter();</script></html>'
 (H/'private/report.html').write_text(h,'utf8')
 nav=read(R/'experiments/management/report_navigation.json');url=(H/'private/report.html').as_uri();nav=[x for x in nav if x['url']!=url];nav.append({'title':'36 · 미지원46곳 진단과 근거 기반 첫 확장','url':url,'summary':f"46곳 원인 분리. 같은 분석 지원14→19. 새 50건 Qwen 생성 {m['changed_records']}문장 일부 변경. 품질 점수 아님."});save(R/'experiments/management/report_navigation.json',nav)
 store=WorkStore(R)
 if not any(t['id']=='support_expansion_20261104' and t['status'] in ('completed','failed') for t in store.state()['tasks']):
  store.task({'id':'support_expansion_20261104','title':'미지원46곳 점검과 첫 확장','actor':'리드 + 기존 Orca 두 검토자','stage':'결과·원본·검토 정리','status':'completed','done':50,'total':50,'unit':'입력','message':'46곳 진단·근거 확장·Qwen50 완료. 생성 오류와 남은 문법군 별도 기록'})
 print(json.dumps({k:v for k,v in summary.items() if k not in ('additional_probes','audit46','baseline_metrics')},ensure_ascii=False))
if __name__=='__main__':main()
