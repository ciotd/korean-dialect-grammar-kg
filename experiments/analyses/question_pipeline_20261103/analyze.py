"""Read-only result audit and counterfactual retrieval. Never calls a model."""
import collections,copy,datetime,html,json
from adapter import HERE,ROOT,RuntimeReader,adapt,projected
from kg_pipeline.io import read,save,sha

def main():
 out=Path(read(HERE/'private/latest_run.json')['directory']);results=read(out/'private/results.json');source={r['id']:r for r in read(out/'private/manual_source.json')}
 graph=read(out/'private/graph.json');morphs=read(out/'private/kiwi_inputs.json');metrics=read(out/'metrics.json')
 review=read(ROOT/'experiments/analyses/question_human_review_20261102/private/review_set.json');refs={r['id']:[c['text'] for c in r['candidates']] for r in review['rows']}
 receipt=read(Path(read(ROOT/'experiments/analyses/question_human_review_20261102/private/latest_receipt.json')['receipt']))
 accepted_ids={r['id'] for r in receipt['rows'] if r['accepted_by_this_reviewer_in_given_context']}
 pairs=[];replays=[]
 for qid,s in source.items():
  pair={r['condition']:r for r in results if r['source_case']==qid};mr=pair['model'];manual=pair['manual'];folder=out/'private/records'/mr['id'];parsed=folder/'analysis_call/parsed.json'
  reasons=[]
  if parsed.exists():
   raw=read(parsed);q=read(folder/'retrieval_raw.json') if (folder/'retrieval_raw.json').exists() else None
   if q:reasons.extend('范围:'+x['feature']+'='+str(x['observed']) for c in q['clauses'] for x in c['scope_failures'])
   reasons.extend(mr.get('needs_analysis',[]))
   count={}
   for name in ('as_returned','speech_act_only','speech_act_and_prefinal'):
    changed=copy.deepcopy(raw)
    if name!='as_returned':changed['features']['speech_act']=s['analysis']['clauses'][0]['features']['speech_act']
    if name=='speech_act_and_prefinal':
     w=next(w for w in morphs[qid]['words'] if w['uid']==raw['target_word_id']);changed['features']['prefinal_type']=projected(w)[2]
    a=adapt(changed,morphs[qid]);p=RuntimeReader(graph,morphs[qid]).packet(a)
    count[name]={'ready':any(c['readiness']=='ready_for_generation_trial' for c in p['clauses']),'readiness':[c['readiness'] for c in p['clauses']],
     'rule_ids':[x['rule_id'] for c in p['clauses'] for x in c['choices']],'query_only_no_generation':True}
   replays.append({'id':qid,'scope':'diagnostic intervention, not corrected automatic result','results':count})
  else:raw=None;meta=read(folder/'analysis_call/meta.json');reasons.append('分析输出截断' if meta.get('finish_reason')=='length' else mr.get('error','analysis failed'))
  outtext=manual['output_text'];agreement=outtext in refs[qid] if outtext is not None else None
  pairs.append({'id':qid,'input':s['analysis']['text'],'manual':manual,'model':mr,'model_raw_analysis':raw,'model_block_reasons':reasons,
   'previous_user_accepted_candidates':refs[qid] if qid in accepted_ids or qid=='Q13' else [],'manual_exact_reference_agreement':agreement,
   'analysis_feature_differences':{k:{'manual':('negative' if qid=='Q15' and k=='polarity' else v),'model':raw['features'].get(k)} for k,v in s['analysis']['clauses'][0]['features'].items() if raw and raw['features'].get(k)!=('negative' if qid=='Q15' and k=='polarity' else v)}})
 findings=[
 {'id':'analysis_function','stage':'분석','cases':[p['id'] for p in pairs if p['model_raw_analysis'] and p['model_raw_analysis']['features']['speech_act']=='request'],
  'observation':'완료된 분석 응답15개 모두 speech_act=request. 이유 설명에서는 정보 질문으로 설명한 사례도 있음. 이 값 때문에15개가 현재 직접정보질문 범위 밖으로 조회됨.',
  'inference':'질문을 information request라는 일반 의미의 request로 인코딩했을 가능성. 이번 프롬프트는 information_question/request의 대조 정의가 충분하지 않음. 모든 경우가 무조건 같은 언어학 오류라고 단정하지 않음.',
  'next_test':'발화 기능을 한국어 정의와 함께 묻고 코드가 고정 enum에 매핑하는 분석 전용 비교. 원본 모델 결과와 비교하며 KG 범위는 그대로 유지.'},
 {'id':'analysis_prefinal','stage':'분석','cases':['Q04','Q09','Q10','Q13','Q14'],
  'observation':'Kiwi가 었/EP를 제공했지만 Qwen은 prefinal_type=none으로 출력. 시간 의미 tense=past와 형태 존재 여부를 따로 기록한 결과가 어긋남.',
  'inference':'관찰 가능한 형태까지 Qwen에 재판정시켜 이미 확보된 정보를 버리는 구조적 약점.',
  'next_test':'해당 어절의 선어말·어간·위치는 Kiwi에서 공급하고 Qwen은 문법 기능 해석을 담당. 불일치 기록은 유지.'},
 {'id':'analysis_truncated','stage':'분석','cases':['Q12'],'observation':'HTTP200이나 completion_tokens=2048, finish_reason=length. 정상 JSON 분석으로 사용하지 않음.','inference':'요청된 분석 출력 길이 한도에 도달. 모델의 올바른 문장 이해 여부와 별개.','next_test':'긴 reason 대신 짧은 근거 필드로 분석 출력 계약을 줄여 별도 확인. 이번 실패를 재시도로 지우지 않음.'},
 {'id':'generation_past','stage':'생성','cases':['Q04'],'observation':'올바른 수작업 분석과 었/EP·과거 보존 지시를 전달했지만 어제 뭐 먹노? 출력. 모델 설명도 었을 축약했다는 근거 없는 설명을 함.','inference':'조회 정보 부재가 아니라 전달받은 과거 형태 보존을 이행하지 못한 사례. 전달 형식과 모델 조합 능력 중 어느 것이 원인인지는 미확정.','next_test':'동일 지식으로 기존 지시와 명시적 조합 순서 지시를 비교하는 생성 전용 시험.'},
 {'id':'generation_copula','stage':'생성','cases':['Q06','Q08'],'observation':'Q06 선택 결합형 가를 누락해 의사? 출력. Q08 선택 결합형 고 대신 의사이고? 출력.','inference':'명사+선택 결합형의 조합 지시 미준수. 의사이고를 모든 문맥에서 비문이라고 판정한 것은 아님.','next_test':'모음/받침 명사의 결합 대상을 한 가지 지시로 명시한 전달 대조. 완성 정답 문장을 주지 않음.'},
 {'id':'output_check_gap','stage':'검사','cases':['Q04','Q08'],'observation':'현재 표면 검사에서 두 오류는 경고되지 않았음. Q06의 어미 누락만 경고.','inference':'경고0을 성공으로 셀 수 없음. 접미 문자열 검사만으로 시제와 계사 조합을 충분히 확인하지 못함.','next_test':'보존 형태와 계사 결합을 별도 진단에 추가하되 잘못된 출력 원문을 숨기거나 자동 정답으로 고치지 않음.'}]
 focus=[r for r in replays if r['id'] not in ('Q13','Q15','Q16')]
 allcalls=[c for r in results for c in r['calls']]+metrics['smoke_calls']
 summary={'run_id':out.name,'cases':16,'condition_records':32,'model_analysis_complete':sum(p['model_raw_analysis'] is not None for p in pairs),
  'manual_generation_calls':sum((out/'private/records'/r['id']/'generation_call/meta.json').exists() for r in results if r['condition']=='manual'),
  'model_generation_calls':sum((out/'private/records'/r['id']/'generation_call/meta.json').exists() for r in results if r['condition']=='model'),
  'actual_nonempty_model_outputs':sum(bool(r['output_text']) for r in results),
  'manual_exact_reference_agreement':sum(p['manual_exact_reference_agreement'] is True for p in pairs),'manual_reference_comparable_outputs':sum(p['manual_exact_reference_agreement'] is not None for p in pairs),
  'replay_focus_completed_analyses':len(focus),'replay_ready_counts':{k:sum(r['results'][k]['ready'] for r in focus) for k in ('as_returned','speech_act_only','speech_act_and_prefinal')},
  'all_api_attempts':len(allcalls),'main_api_attempts':metrics['api_attempts'],'smoke_api_attempts':len(metrics['smoke_calls']),
  'all_reported_tokens':{k:sum((c.get('usage') or {}).get(k,0) or 0 for c in allcalls) for k in ('prompt_tokens','completion_tokens','total_tokens')},
  'main_reported_tokens':metrics['reported_usage'],'elapsed_seconds':metrics['wall_seconds'],
  'legacy_metric_caveat':'Frozen metrics.valid_output_records=31 counts needs_review records with no output. This audit uses actual_nonempty_model_outputs=13. Do not use31 as generated or successful translations.',
  'counterfactual_caveat':'Replay changes fields in saved analyses and only re-queries KG; it does not show improved Qwen generation. Q13/Q15/Q16 are excluded from the12-case focus; Q12 had no completed analysis.',
  'quality_caveat':'10 exact matches are agreement with this user-reviewed development reference, not unseen accuracy. Manual analysis is a supplied interpretation; text-only ambiguity remains.',
  'preparation_issues':['Missing jsonschema dependency caught before any chat call; reused existing validate_schema instead. No package installation.']}
 save(HERE/'private/audit.json',{'summary':summary,'findings':findings,'pairs':pairs,'counterfactual_retrieval':replays})
 render(summary,pairs,findings,out)
 print(json.dumps(summary,ensure_ascii=False,indent=2))

def render(s,pairs,findings,out):
 e=lambda x:html.escape(str(x));tables=[]
 for p in pairs:
  m=p['manual'];q=p['model'];why=' / '.join(p['model_block_reasons']).replace('范围:','범위:').replace('分析输出截断','분석 출력 길이 초과')
  tables.append(f"<tr><td><b>{p['id']}</b><br>{e(p['input'])}</td><td>{e(m['output_text'] or '생성하지 않음')}<br><small>{e(', '.join(m.get('readiness',[])))}</small></td><td>{e(q['output_text'] or '생성하지 않음')}<br><small>{e(why)}</small></td><td>{'기존 수용 표현과 일치' if p['manual_exact_reference_agreement'] else '다름: 아래 사례 확인' if p['manual_exact_reference_agreement'] is False else '비교 대상 아님'}<details><summary>실제 분석·조회·전달 보기</summary><pre>{e(json.dumps({'model_analysis':p['model_raw_analysis'],'feature_difference':p['analysis_feature_differences'],'manual_rule':m.get('rule_ids'),'model_rule':q.get('rule_ids'),'manual_output':m['output_text']},ensure_ascii=False,indent=2))}</pre></details></td></tr>")
 errors=''.join(f"<tr><td>{e(f['stage'])}<br>{e(', '.join(f['cases']))}</td><td>{e(f['observation'])}</td><td>{e(f['next_test'])}</td></tr>" for f in findings)
 report=f'''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>질문 KG 연결 실험 결과</title><style>
body{{margin:0;background:#f2f6fa;color:#17324b;font:17px/1.7 system-ui,'Malgun Gothic',sans-serif}}main{{max-width:1200px;margin:auto;padding:30px 24px}}h1{{font-size:29px}}h2{{font-size:23px}}section{{background:white;border:1px solid #d6e1eb;border-radius:12px;padding:24px;margin:22px 0}}.call{{padding:17px;background:#eaf3fe;border-left:5px solid #276ba6}}.warn{{background:#fff6e4;border-left-color:#b27620}}table{{width:100%;border-collapse:collapse;font-size:16px}}th,td{{padding:12px;border-bottom:1px solid #d6e1eb;vertical-align:top;text-align:left}}th{{background:#edf3fa}}small{{color:#617386}}.scroll{{overflow:auto}}pre{{font-size:13px;white-space:pre-wrap;overflow-wrap:anywhere;max-height:460px;overflow:auto}}summary{{cursor:pointer;color:#1764aa}}a{{color:#1764aa}}.flow{{display:flex;gap:12px;align-items:center;flex-wrap:wrap}}.step{{padding:12px;background:#edf3fa;border-radius:7px}}@media(max-width:650px){{main{{padding:18px 12px}}section{{padding:15px}}}}
</style><main><small>2026-11-03 · 실제 Qwen 실행 · {e(s['run_id'])}</small><h1>연결은 실행했습니다.<br>분석 단계와 생성 단계에서 각각 문제가 확인됐습니다.</h1>
<div class="call"><b>모델 분석 경로:</b> 16건 중 15건은 조회 조건에서 멈췄고 1건은 분석 출력이 잘렸습니다. 생성 호출은 0회입니다.<br><b>수작업 분석 경로:</b> 13건을 실제 생성했습니다. 10건은 사용자가 수용한 기존 표현과 같고, 3건은 전달한 조합 지시를 제대로 지키지 못했습니다.</div>
<section><h2>같은 지식으로 두 경로를 비교했습니다</h2><div class="flow"><span class="step">같은 표준어·Kiwi</span><span>→</span><span class="step">Qwen 분석 / 수작업 분석</span><span>→</span><span class="step">같은 KG 조건 조회</span><span>→</span><span class="step">같은 형식의 지시</span><span>→</span><span class="step">같은 Qwen 생성</span></div><p>사람이 확인한 방언 정답이나 대안은 모델에 주지 않았습니다. 운영 KG를 고치거나 넓은 모듈의 카드 전체를 가져오지 않았습니다. 이번 조회는 동결한 JSON 그래프의 실제 조건 간선을 사용했고, 실시간 Neo4j 조회는 아닙니다.</p><p class="warn call">이 실험은 작은 개발 사례의 원인 진단입니다. 수작업 분석에는 특정 상황의 해석이 들어 있고, 모델은 문장과 Kiwi만 봅니다. 해석 차이를 모두 모델 오류로 계산할 수는 없습니다.</p></section>
<section><h2>실제로 어디서 막혔나</h2><div class="scroll"><table><thead><tr><th>단계·사례</th><th>실제 기록</th><th>다음 확인 방법</th></tr></thead><tbody>{errors}</tbody></table></div></section>
<section><h2>저장된 분석값만 바꿔 조회를 다시 해봤습니다</h2><p>일반 질문 13건 중 정상 분석 응답을 받은 12건을 대상으로 합니다. Q12는 응답이 잘렸고, 모호성/범위 밖/중복 기술 검사인 Q13·Q15·Q16은 이 집계에서 제외합니다.</p><table><tr><th>분석값</th><th>생성 지시 준비 가능</th></tr><tr><td>모델이 원래 반환한 값</td><td>{s['replay_ready_counts']['as_returned']} / 12</td></tr><tr><td>발화 기능만 수작업 가정으로 변경</td><td>{s['replay_ready_counts']['speech_act_only']} / 12</td></tr><tr><td>추가로 선어말 종류를 Kiwi 값으로 변경</td><td>{s['replay_ready_counts']['speech_act_and_prefinal']} / 12</td></tr></table><p><b>새 Qwen 생성은 하지 않은 조회 재현 검사입니다.</b> 두 분석 필드가 준비 단계의 병목이라는 근거이며, 바꾸면 번역 12건이 성공한다는 뜻은 아닙니다.</p></section>
<section><h2>전체 16건의 실제 결과</h2><p>‘생성하지 않음’은 원문을 그대로 출력했다는 뜻이 아닙니다. 실제 생성 요청을 보내지 않았습니다. 수작업 경로의 Q13은 질문 뜻 미확정, Q15는 재촉 표현, Q16은 의도적으로 누락한 분석값 때문에 멈췄습니다.</p><div class="scroll"><table><thead><tr><th>입력</th><th>수작업 분석 → Qwen</th><th>모델 분석 → Qwen</th><th>수작업 경로 대조·상세</th></tr></thead><tbody>{''.join(tables)}</tbody></table></div></section>
<section><h2>비용·검증과 한계</h2><ul><li>본실험 호출 {s['main_api_attempts']}회: 분석16회·생성13회. 별도 연결 시험 {s['smoke_api_attempts']}회. 자동 재시도0회.</li><li>전체 토큰 {s['all_reported_tokens']['total_tokens']:,}개, 본실험 토큰 {s['main_reported_tokens']['total_tokens']:,}개. 서버가 보고한 수치입니다.</li><li>기록된 경과 시간 약 {s['elapsed_seconds']:.1f}초: 연결 시험·Kiwi·본실험 포함, 준비·코드작성 시간 제외.</li><li>연결 코드 검사9개 통과. 실제 출력은 코드가 정답으로 바꾸거나 숨기지 않았습니다.</li><li>모델 분석 실패 Q12는 통신 실패가 아니라 출력 한도2048토큰 도달입니다.</li></ul><p class="call warn">기존 공통 집계의 valid_output_records=31은 출력 없는 보류 기록까지 포함합니다. 이를 번역 출력 수로 쓰지 않습니다. 실제 생성 문장은 <b>13개</b>입니다. 원본 집계는 보존하고 이 보고서에서 분모를 바로잡았습니다.</p></section>
<section><h2>다음 작업 제안</h2><ol><li><b>분석부터 분리해서 수정:</b> 선어말·어간·위치는 Kiwi가 공급하고, Qwen의 발화 기능은 한국어로 명확히 정의해 비교합니다. KG 범위를 넓혀 오류 값을 억지로 통과시키지 않습니다.</li><li><b>생성 조합을 별도로 비교:</b> 같은 수작업 분석과 지식에서 조합 순서를 더 명시한 지시가 과거 누락·계사 결합 오류를 줄이는지 검사합니다. 지금 결과만으로 전달 형식이 원인이라고 확정하지 않습니다.</li><li>각 단계가 나아진 것을 확인한 뒤 다시 전체를 연결합니다. 새 어휘·조사 생략은 이번 비교에 섞지 않습니다.</li></ol></section>
<p><a href="audit.json">상세 진단 원본</a> · <a href="{out.as_uri()}/private/results.json">실험 출력 원본</a> · <a href="{out.as_uri()}/config.json">실행 설정</a></p></main></html>'''
 (HERE/'private/report.html').write_text(report,encoding='utf8')

from pathlib import Path
if __name__=='__main__':main()
