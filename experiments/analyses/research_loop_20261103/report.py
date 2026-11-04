"""Recompute report metrics from raw results; never mutate experimental records."""
import collections,html,json
from pathlib import Path
from pipeline import HERE,ROOT,bridge
from kg_pipeline.io import read,save,sha,load_jsonl
E=lambda x:html.escape(str(x))
RUNS=[('첫 전달 비교','20261103T072412784953Z_research_loop_dev'),('부품 전달 1차','20261103T072835388759Z_research_loop_composition_replay'),('부품 전달 코드 수정','20261103T073040472661Z_research_loop_composition_replay'),('기존 50건 진단','20261103T073106231833Z_research_loop_full50')]
WARN={'outside_target_changed':'지정 위치 밖 변경','selected_ending_not_at_target_end':'선택 어미가 끝에 없음','nominal_changed':'명사 누락·변경','prefinal_observation_changed_or_kiwi_uncertain':'선어말 변화 의심(분석기 불확실성 포함)','integrated_copula_composition_mismatch':'계사 결합 불일치','target_expanded_beyond_one_word':'대상 어절 밖으로 확장','lexical_stem_not_observed_or_kiwi_uncertain':'어간 변화 의심(분석기 불확실성 포함)'}
def category(t):
 if t['status']=='projection_unsupported':return '형태 연결 미지원'
 if t['status'].endswith('_failed'):return '실행 오류'
 if t.get('scope_failures'):return '현재 KG 지원 범위 밖'
 if t.get('readiness')=='ready_for_generation_trial':return '생성까지 연결'
 if t.get('segmentation_state')=='unresolved':return '복문 분석 미지원'
 return '분석값 미확정'
def link(path,label):return '<a href="'+E(Path(path).as_uri())+'">'+E(label)+'</a>'
def table(headers,rows):return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+E(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(c)+'</td>' for c in r)+'</tr>' for r in rows)+'</tbody></table></div>'
def main():
 audit={'runs':[]};runs={}
 for name,rid in RUNS:
  d=ROOT/'experiments/runs'/rid;r=read(d/'private/results.json');runs[rid]=(d,r)
  manifest=read(d/'artifact_hashes.json');bad=[p for p,h in manifest.items() if not (d/p).is_file() or sha((d/p).read_bytes())!=h]
  calls=[read(p) for p in (d/'private/records').rglob('meta.json')]
  outputs=[]
  if 'replay' in rid:
   outputs=[{'id':x['id'],'arm':'components','status':x['status'],'output':x.get('output_text') if x['status']=='generated' else None,'warnings':x.get('checks',{}).get('warnings',[])} for x in r]
  else:
   outputs=[{'id':x['id'],'target_id':t['target_id'],'arm':arm,'status':g['status'],'output':g.get('output_text'),'warnings':g.get('checks',{}).get('warnings',[])} for x in r for t in x['targets'] for arm,g in t['generation'].items()]
  armstats={}
  for arm in sorted({o['arm'] for o in outputs}):
   os=[o for o in outputs if o['arm']==arm];attempted=[o for o in os if o['status']!='no_ready_target']
   armstats[arm]={'attempts':len(attempted),'returned_outputs':sum(o['output'] is not None for o in attempted),'statuses':dict(collections.Counter(o['status'] for o in attempted)),'warning_outputs':sum(bool(o['warnings']) for o in attempted)}
  audit['runs'].append({'name':name,'run_id':rid,'inputs':len(r),'calls':len(calls),'analysis_calls':sum(c['stage']=='scoped_analysis' for c in calls),
   'generation_calls':sum(c['stage'].startswith('generation_') for c in calls),'arms':armstats,'outputs':outputs,'metrics':read(d/'metrics.json'),
   'artifact_count':len(manifest),'hash_mismatches':bad,'postflight':read(d/'postflight.json')})
 fullpath,full=runs[RUNS[-1][1]];scope=read(HERE/'private/scope.json');sm={x['id']:x for x in scope['inputs']}
 cats=collections.Counter(category(t) for r in full for t in r['targets']);audit['full50_target_categories']=dict(cats)
 original=load_jsonl(ROOT/'data/derived_private/standard_inputs_50_20261029_v2/inputs.jsonl')
 audit['full50_input_exact_match']=[(r['id'],r['input_text']) for r in full]==[(r['id'],r['text']) for r in original]
 audit['scope_runtime_policy']='manual scope tags are not used by run.py or pipeline.py'
 audit['quality']='no automated naturalness score; warning-free outputs are not correct translations'
 save(HERE/'private/audit.json',audit)
 totals={'calls':sum(a['calls'] for a in audit['runs']),'tokens':sum(a['metrics']['reported_usage']['total_tokens'] for a in audit['runs'])}
 counts=''.join('<div class="metric"><b>'+E(v)+'</b><span>'+E(k)+'</span></div>' for k,v in [('입력 전체',50),('분석한 종결 위치',62),('생성한 위치',3),('아직 다른 처리가 필요한 위치',59)])
 rows=[]
 for a in audit['runs']:
  for arm,stats in a['arms'].items():
   rows.append([E(a['name']),E({'whole':'문장 전체 출력','piece':'어절 출력·기존 지시','components':'한국어 부품 조합'}[arm]),stats['attempts'],stats['returned_outputs'],stats['warning_outputs'],E(', '.join({'generated':'후보 출력','needs_review':'모델 보류','failed':'호출/파싱 실패'}.get(k,k)+' '+str(v)+'건' for k,v in stats['statuses'].items()))])
 dev=runs[RUNS[0][1]][1];latest=runs[RUNS[2][1]][1];later={x['id']:x for x in latest}
 devrows=[]
 for r in dev:
  t=r['targets'][0];w=t.get('generation',{}).get('whole',{});n=later[r['id']]
  devrows.append([E(r['id']),E(r['input_text']),E(w.get('output_text','미생성')),E(n.get('output_text','미생성')),E(' / '.join(WARN.get(x,x) for x in n.get('checks',{}).get('warnings',[])) or ('자동 경고 없음 — 자연스러움 미확인' if n['status']=='generated' else '현재 범위 밖'))])
 fullrows=[]
 for r in full:
  targets=[]
  for t in r['targets']:
   i,j=t['span'];g=t.get('generation',{}).get('piece',{})
   failures=', '.join(x['feature']+'='+str(x['observed']) for x in t.get('scope_failures',[]))
   desc='<b>'+E(r['input_text'][i:j])+'</b> → '+E(category(t))
   more='<br>규칙: '+E(', '.join(t.get('rules',[])) or '없음')
   if failures:more+='<br>현재 범위와 다른 값: '+E(failures)
   if t.get('error'):more+='<br>코드 기록: '+E(t['error'])
   if t.get('needs_analysis'):more+='<br>추가 분석: '+E(', '.join(t['needs_analysis']))
   if g.get('checks',{}).get('warnings'):more+='<br>검사 경고: '+E(', '.join(g['checks']['warnings']))
   raw=fullpath/'private/records'/r['id']/'targets'/t['target_id']/'trace.json'
   if raw.exists():more+='<br>'+link(raw,'실제 조회 경로 원본')
   targets.append(desc+'<details><summary>왜 이렇게 됐나</summary>'+more+'</details>')
  fullrows.append('<tr data-change="'+('yes' if not r['unchanged'] else 'no')+'"><td>'+E(r['id'])+'</td><td>'+E(r['input_text'])+'</td><td>'+E(r['output_text'])+'</td><td>'+('<hr>'.join(targets) or 'Kiwi가 종결 위치를 찾지 못함')+'</td></tr>')
 issues=[['분석 연결','일반 질문이 확인/높임으로 잘못 분류됨','정의·대상 위치를 명확히 설명','준비 24→27/32. 과거 실행과 비교이며 독립 정확도 아님.'],
 ['전달 코드','과거 계사에서 명사 부품 누락','명사+계사+선어말+어미를 전달','학생이었어 → 학생이었나로 복구. 오류 버전도 보존.'],
 ['모델 조합','웃어의 어를 선어말로 착각해 거절','보존/삭제/결합순서를 한국어 필드로 구분','거절은 줄었으나 활용 오류가 남음.'],
 ['결과 집계','생성 실패도 완료·미지원으로 보일 수 있었음','하위 호출 오류와 상위 상태를 함께 기록','코드 검사 추가. 과거 집계는 원본과 재집계 구별.'],
 ['검사 누락','어휘 변경/대상 확장을 놓침','어간 관측·한 어절 범위 검사 추가','여전히 보었나/춨나 같은 활용 오류 전부 검증 못함.'],
 ['KG 범위','정제된 지식은 질문 구성 1개·용법 6개','50건 전체에서 필요한 문법군을 별도 지도화','전체 문법 KG가 완성된 상태가 아님.']]
 stage=[['1','50건 전체 요구 문법·현재 범위 대조','완료(총괄의 작업지도 초안)','20개 작업군과 연결. 전 문헌 재정제 완료 아님.'],['2','분석값을 실제 조건 관계로 연결','실험 완료, 한계 남음','32건 준비 27. 복문·보조용언 연결 미지원.'],['3','같은 분석·규칙으로 전달/조합 비교','실험·코드 오류 수정 완료, 생성 품질 미달','과거 계사 명사누락 수정. 활용 오류·원문 유지 잔존.'],['4','기존 50건 전수 진단','실행 완료','62분석+3생성. 3문장 일부 변경, 47문장 원문 유지.']]
 bars=''.join('<div class="barrow"><span>'+E(k)+'</span><div><i style="width:'+str(v/62*100)+'%"></i></div><b>'+str(v)+'</b></div>' for k,v in cats.items())
 reviewers=[]
 for who,label in [('claude','Claude — 문법·지식'),('codex','Codex — 코드·집계')]:
  d=HERE/'private/reviewers'/who
  reviewers.append('<li>'+E(label)+' · '+link(d/'response.md','독립 검토 원문')+' · '+(link(d/'results_review/response.md','결과 교차 검토 원문') if (d/'results_review/response.md').exists() else '결과 검토 진행 중')+'</li>')
 htmltext='''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>연구 루프 1–4 결과</title><style>
*{box-sizing:border-box}body{margin:0;background:#f4f6fa;color:#203047;font:16px/1.65 system-ui,'Malgun Gothic',sans-serif}main{max-width:1180px;margin:auto;padding:32px 22px 80px}h1{font-size:30px;line-height:1.35}h2{font-size:23px;margin-top:36px}h3{font-size:18px}.lead,.panel{background:white;border:1px solid #dfe6ee;border-radius:14px;padding:22px;margin:18px 0}.lead{border-left:6px solid #24677b}p{margin:10px 0}.muted{color:#607186;font-size:14px}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.metric{padding:15px;background:white;border-radius:10px;display:flex;flex-direction:column}.metric b{font-size:30px;color:#166779}.flow{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.flow span{border:1px solid #b6cbd4;padding:10px;background:#eaf4f5;border-radius:8px}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px;background:white}th,td{padding:12px;border-bottom:1px solid #dce4ed;text-align:left;vertical-align:top}th{background:#e9eff5;white-space:nowrap}td{min-width:85px}#full td:nth-child(2),#full td:nth-child(3){min-width:240px;max-width:350px}details{font-size:13px;margin:8px 0}summary{cursor:pointer;color:#146579}a{color:#086c83;overflow-wrap:anywhere}.barrow{display:grid;grid-template-columns:190px 1fr 40px;gap:14px;align-items:center;margin:12px 0}.barrow div{background:#e5edf1;height:18px}.barrow i{display:block;background:#2e7d91;height:18px}input,select{font:inherit;padding:8px;border:1px solid #bccbd9;border-radius:7px}hr{border:0;border-top:1px solid #ddd;margin:12px 0}.warn{background:#fff2d9;padding:14px;border-radius:8px}@media(max-width:700px){.metrics{grid-template-columns:1fr 1fr}.barrow{grid-template-columns:150px 1fr 30px}}
</style><main><p class="muted">2026-11-03 · 기존 결과를 지우지 않는 진단 실험 · 새로운 KG 사실 추가 없음</p><h1>어디까지 고쳤고,<br>무엇이 아직 막혀 있나</h1>
<div class="lead"><b>형태 조합 오류는 줄였습니다. 이제 남은 큰 문제는 KG의 지원 범위와 분석 범위입니다.</b><p>현재 새 KG는 질문 구성 하나만 정제되어 있습니다. 기존 50문장 전체를 처리할 문법 지식이 모두 준비된 상태가 아닙니다. 같은 분석·같은 KG에서 Qwen 대신 일반 활용 조합기를 쓰자, 확인된 활용 오류가 바뀌었습니다. 아래는 실제 고정조건 비교입니다.</p><p>전체 KG가 틀렸다고 결론낼 근거도, 전체 KG가 완성됐다고 말할 근거도 없습니다. 형태 조합을 안정화하면서 아직 정제하지 않은 문법군을 확장해야 합니다.</p></div>
'''+counts.replace('<div class="metric">','<div class="metric">')
 # Wrap metric cards before adding rest.
 htmltext=htmltext[:htmltext.index(counts)]+'<div class="metrics">'+counts+'</div>'
 latest_composer=HERE/'private/latest_composer.json'
 if latest_composer.exists():
  cdir=Path(read(latest_composer)['directory']);cr=read(cdir/'private/results.json');cm=read(cdir/'metrics.json')
  changed=[r for r in cr if r['qwen_output_text']!=r['output_text']]
  comp_table=table(['대상','Qwen 부품 조합','일반 활용 조합기'],[[E(r['source_case']),E(r['qwen_output_text']),E(r['output_text'])] for r in changed])
  section='<div class="panel"><h2>추가 승인 후: 조합기만 바꾼 비교</h2><p><b>개발27곳 + 기존50 중3곳 = 30곳</b>. 저장된 Qwen 분석과 KG 선택을 그대로 쓰고, 마지막 어절 조합만 Kiwi.join 또는 KG의 계사 결합형 직접 조합으로 바꿨습니다. 문장 ID별 예외 코드는 없습니다.</p>'+comp_table
  section+='<p><b>검토자가 확인한 변화:</b> 형태 파손4건(Q05/Q16은 같은 원문), 미변환2건, 축약 표기1건. 원문·분석·조회·전달 사본90개 일치, 결과223파일 해시 일치. 현재계사 입력 모순 검사와 다음 실행 대상 고정도 보완했고, 조합기10검사 및 저장30결과 재현을 확인했습니다.</p>'
  section+='<p>30곳 모두 후보 생성, 원문 유지0, 같은 자동검사의 경고0. 다만 <b>자연스러움 100%가 아닙니다.</b> 앞서 생성까지 도달한 위치만 비교했으므로 미지원59곳은 그대로 남습니다. Q05/Q16은 같은 원문입니다. DEV012의 두었노→뒀노는 비문 교정보다 축약 표기 차이입니다.</p>'
  section+='<p>새 Qwen 호출0·토큰0. 조합 연산 합계 '+str(round(cm['composition_seconds_sum'],3))+'초, Kiwi 초기화 '+str(round(cm['kiwi_startup_seconds'],3))+'초, 기록·검사 포함 처리 루프 '+str(round(cm['wall_seconds'],3))+'초. 이전 원격 모델 실행과 하드웨어/측정구간이 달라 속도 향상률은 계산하지 않습니다.</p>'
  section+='<details><summary>비교30곳 전체</summary>'+table(['ID','입력','기존 Qwen','조합기'],[[E(r['id']),E(r['input_text']),E(r['qwen_output_text']),E(r['output_text'])] for r in cr])+'</details>'
  section+='<p>'+link(cdir/'private/results.json','30개 실제 결과')+' · '+link(cdir/'config.json','고정 비교 설정')+' · '+link(HERE/'composer.py','일반 조합 코드')+'</p>'
  for who in ('claude','codex'):
   rp=HERE/'private/reviewers'/who/'composition_review/response.md'
   section+='<p>'+E(who)+' 조합 비교 검토: '+(link(rp,'검토 원문') if rp.exists() else '검토 진행 중')+'</p>'
  section+='</div>'
  htmltext+=section
 htmltext+='<h2>이번에 한 일</h2>'+table(['단계','작업','진행 여부','결과'],[[E(x) for x in r] for r in stage])
 htmltext+='<div class="flow"><span>원문·대상 위치</span>→<span>Qwen의 문법 판단</span>→<span>KG 조건 관계 조회</span>→<span>보존/삭제/결합 부품</span>→<span>Qwen 조합</span>→<span>원문에 반영·검사</span></div>'
 htmltext+='<h2>50문장: 어디에서 멈췄나</h2><p>문장 수가 아니라 <b>종결 위치 62곳</b>을 센 결과입니다. 한 문장에 여러 위치가 있습니다. 아래는 형태 연결 미지원 → KG 범위 밖 → 생성 → 복문 미분석 순으로 한 곳을 한 번씩 분류한 표입니다. 복문과 범위 밖이 동시에 있을 수 있으며, 상세 기록에는 둘 다 남았습니다.</p>'+bars
 htmltext+='<p class="warn">변경된 3문장도 자연스러움 합격을 뜻하지 않습니다. LONG001은 첫 질문만 바뀌었습니다. 47문장 원문 유지를 47건의 모델 번역 실패로 해석하면 안 됩니다.</p>'
 htmltext+='<h2>찾은 문제와 수정</h2>'+table(['문제 위치','확인한 문제','실제 수정','결과/남은 문제'],[[E(x) for x in r] for r in issues])
 htmltext+='<h2>같은 규칙을 줘도 조합이 달라졌습니다</h2><p>개발 32건 중 준비된 27건에 생성 요청을 했습니다. 첫 비교와 부품 전달은 프롬프트·출력 형식이 함께 바뀌므로 어느 한 요소만의 효과라고 말할 수 없습니다. 재검사 두 번은 분석·조회 결과를 그대로 재사용했습니다.</p>'+table(['실행','방식','생성 요청','실제 출력','자동 경고 동반','반환 상태'],rows)
 htmltext+='<p class="muted">자동 경고 수는 각 실행 당시 검사 기준입니다. 검사도 보완됐으므로 경고 수 감소를 품질 향상률로 쓰지 않습니다. Q16은 Q05와 같은 문장으로, 32 ID는 31개 서로 다른 원문입니다.</p>'
 htmltext+='<details><summary>개발 32건의 이전 출력과 최종 조합 출력 보기</summary>'+table(['ID','입력','전체문장 방식','최종 부품 방식','자동 검사'],devrows)+'</details>'
 htmltext+='<h2>앞선 Qwen 전수 진단: 50문장 전체 결과</h2><p>검색하거나, 바뀐 문장만 골라 볼 수 있습니다. 각 위치의 “왜 이렇게 됐나”에서 적용 규칙과 중단 이유를 확인하세요.</p><input id="search" placeholder="ID·문장·이유 검색"><select id="filter"><option value="all">전체 50건</option><option value="yes">바뀐 3건</option><option value="no">원문 유지 47건</option></select><span id="count"></span><div class="scroll"><table id="full"><thead><tr><th>ID</th><th>원문</th><th>최종 출력</th><th>위치별 처리</th></tr></thead><tbody>'+''.join(fullrows)+'</tbody></table></div>'
 htmltext+='<h2>두 검토자는 무엇을 봤나</h2><ul>'+''.join(reviewers)+'</ul><p>실제 모델: Codex GPT-6-Astra High, Claude Opus 5.5. 독립 검토 후 실제 결과를 주고 한 번 교차 검토했습니다. PDF 전체 재정독이나 사용자 자연스러움 평가를 대신하지 않습니다.</p>'
 htmltext+='<div class="panel"><h3>검토 결과를 받아 바로잡은 점</h3><ul><li>첫 어절 생성 27회는 <b>모델 보류25 + 길이 초과 실패2</b>입니다. 무출력을 모두 모델 보류로 부른 중간 설명을 정정합니다.</li><li>부품 재생의 실제 출력 한도는 <b>256토큰</b>입니다. 당시 config에는 768이 남은 기록 오류가 있었습니다. 원본 요청으로 확인했고, 다음 실행 코드는 설정과 실제 호출값을 일치시켰습니다. 과거 기록은 덮어쓰지 않았습니다.</li><li>이번 입력은 사용자 수정 <b>50건 v2</b>입니다. ADVCE008A 한 건을 사용자가 이전에 “읽고 있는 책…”으로 바꾸도록 지시했습니다. 이번 실행 중 변경한 것은 아닙니다.</li><li>84개 저장 후보를 같은 검사기로 재검사했습니다. 마지막 개발후보27 중 원문동일2·자동경고5이며, 이는 전체 언어학 오류 수가 아닙니다.</li><li>Claude는 원문 표면형이 사라졌다고 해석했지만, 요청에는 원문도 들어 있었습니다. 정확한 관찰은 <b>정규화된 부품을 조합하도록 지시한 뒤 활용 복원 오류가 생겼다</b>는 것입니다. 원문 정보 부재 하나를 확정 원인으로 삼지 않았습니다.</li><li>문자열 끝을 떼어 붙이는 방식을 모든 활용에 바로 적용하지 않습니다. 축약·불규칙·형태소 위치 겹침을 검증한 일반 조합 기능과 비교해야 합니다.</li></ul>'+link(HERE/'private/offline_validation.json','요청 설정·84후보 재검사·입력 승인 근거')+'</div>'
 htmltext+='<p>검증: 파이프라인11개·새 집계4개·기존 관리기능37개 검사 통과. HTML 필터5개 검사, 실행 산출물1898파일 해시 불일치0. 보고서 브라우저 자동 열람은 file 프로토콜 제한으로 수행하지 못했고, 문서 구조·링크·필터 코드는 별도 검사했습니다.</p>'
 htmltext+='<h2>다음 작업 제안</h2>'+table(['순서','작업','종료 기준','안 되면'],[[E(x) for x in r] for r in [
 ['1','활용 조합기 비교 — 사용자 승인 후 완료','기존30위치의 분석·KG고정,30후보·자동경고0','새 문장/새 어미까지 검증된 것은 아님'],
 ['2','평서·상대높임을 다음 문헌 정제 묶음으로 확장','근거→조건→실현형→새 문장 조회가 연결됨','근거 충돌은 사람 결정, 없는 지식을 모델 추정으로 추가하지 않음'],
 ['3','확장 후 기존50 회귀 검사와 별도 새 문장 평가','지원범위·오류·사람 자연스러움을 분리해 보고','반복 오류가 시작된 단계만 고치고 원본 실행을 보존']]])
 htmltext+='<p class="warn">1번은 사용자 추가 승인 후 실행했습니다. 조합기를 전체 파이프라인 기본값으로 연결하는 일과 새 문법군 확장은 후속 작업입니다. 이번 비교는 별도 실행 경로로 보존했습니다. “먹었노→뭇노”는 새 일반 규칙으로 넣지 않았습니다.</p>'
 htmltext+='<details><summary>실행 비용·재현 정보</summary><p>이번 4개 실행: 모델 호출 '+str(totals['calls'])+'회, 서버 보고 토큰 '+str(totals['tokens'])+'개. 새 분석 94회와 생성 111회입니다. API 시간·토큰은 실행별 metrics.json에 보존했습니다. 벽시계 시간은 동시 호출 때문에 호출별 시간 합과 다릅니다.</p>'
 for a in audit['runs']:
  d=ROOT/'experiments/runs'/a['run_id'];htmltext+='<p><b>'+E(a['name'])+'</b> '+E(a['run_id'])+'<br>'+link(d/'metrics.json','측정값')+' · '+link(d/'config.json','실행 설정')+' · '+link(d/'private/results.json','입력별 원본')+' · 해시 검사 '+str(a['artifact_count'])+'파일, 불일치 '+str(len(a['hash_mismatches']))+'</p>'
 htmltext+='<p>'+link(HERE/'private/audit.json','보고서 재집계 근거')+' · '+link(HERE/'private/scope.json','50문장 문법 작업지도')+' · '+link(HERE/'private/test_results_v2.txt','11개 코드 검사')+'</p></details><script>function filter(){let q=document.querySelector("#search").value.toLowerCase(),f=document.querySelector("#filter").value,n=0;document.querySelectorAll("#full tbody tr").forEach(r=>{let show=r.textContent.toLowerCase().includes(q)&&(f==="all"||r.dataset.change===f);r.hidden=!show;if(show)n++});document.querySelector("#count").textContent=" "+n+"건 표시"}document.querySelector("#search").addEventListener("input",filter);document.querySelector("#filter").addEventListener("change",filter);filter()</script></main></html>'
 (HERE/'private/report.html').write_text(htmltext,'utf8');print(json.dumps({'full50_categories':dict(cats),'input_exact':audit['full50_input_exact_match'],'totals':totals,'hash_mismatches':sum(len(a['hash_mismatches']) for a in audit['runs'])},ensure_ascii=False))
if __name__=='__main__':main()
