"""Compare actual paired rerun with the historical run; no model calls or gold accuracy claims."""
import collections
import hashlib
import html
import json
import re
import sys
from pathlib import Path
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[2];sys.path.insert(0,str(PROJECT/'src'))
from kg_pipeline.io import read,save,load_jsonl
from research_management.core import Registry
BATCH='20261030T020345468863Z'
OLD='20261028T011829489985Z'
LABELS={'unchanged':'원문 유지','generated_requires_human_review':'변경 출력','partial':'일부 반영·일부 보류','needs_review':'수정 보류·원문 유지',
        'planning_failed':'수정 계획 실패','generation_failed':'생성 실패','analysis_failed':'분석 실패','retrieval_failed':'KG 조회 실패'}
REASONS={
 'CallError:200':'설명이 반복되어 6,000토큰 한도에서 응답 중단', 'invalid_analysis_function':'분석 결과에 허용 목록 밖 문법 기능명이 있음', 'stale_request':'Qwen이 요청 식별값을 다르게 반환', 'stale_worker_plan':'생성 응답의 계획 식별값 불일치',
 'invalid_binding_source':'카드가 가리킨 원문 형태소 위치 오류','binding_not_ending':'어미가 아닌 곳을 어미 수정 위치로 지정',
 'binding_not_particle':'조사가 아닌 곳을 조사 수정 위치로 지정','invalid_target_index':'카드에 없는 목표형 번호 선택',
 'unretrieved_rule_reference':'전달하지 않은 카드 선택','invalid_edit_anchor':'원문 어절 ID 오류','overlap':'같은 원문 범위를 겹쳐 수정',
 'worker_plan_mismatch':'생성기가 계획의 편집 목록과 다르게 응답','cross_boundary_edit':'문장 경계를 가로지르는 수정',
 'source_suffix_composition_disagreement':'원래 어휘·선어말어미와 생성형 분석이 다름',
 'target_realization_unverified':'선택한 형태와 생성형의 대응 미확인',
 'function_evidence_insufficient':'어미의 문맥 기능 근거 부족', 'function_not_supported':'분석한 문법 기능과 카드 조건 불일치',
 'user_restricted_conversion':'사용자가 제외한 변환', 'reference_or_restriction_not_rewrite':'참고·금지 자료를 수정 명령으로 선택',
 'unresolved_card_condition':'카드에 미해결 조건이 있음','whole_word_not_suffix':'완성 단어를 어미처럼 사용',
 'predicate_kind_disagreement':'동사·형용사·계사 구분과 카드 조건 불일치','particle_function_disagreement':'조사 기능 불일치',
 'particle_edit_changes_other_material':'지정한 조사 이외의 내용까지 변경','missing_target_binding':'수정 목표 연결 누락',
 'compound_edit_composition_unverified':'복합 수정의 조합을 확인하지 못함','multiword_boundary_unproven':'다어절 수정의 보존 범위 미확인',
 'multiword_composition_unverified':'다어절 생성형이 원문 보존 조합과 다름','bound_form_needs_composition':'중간 형태를 완성 표현으로 사용',
 'card_form_unparsable':'문헌의 특수 표기를 직접 활용형으로 읽을 수 없음','unlicensed_word_expansion':'근거 없이 단어를 추가',
 'dependency_group_not_applied':'함께 처리할 다른 수정이 보류됨','protected_punctuation_changed':'문장부호 변경',
 'empty_realization':'빈 생성형','new_unjoined_jamo':'떨어진 자모','particle_span_unavailable':'조사 위치 확인 불가'}

def status_counts(rows):return dict(collections.Counter(r['status'] for r in rows))
def summary(rows):
    valid=[r for r in rows if isinstance(r.get('output_text'),str)]
    return {'records':len(rows),'with_output':len(valid),'without_output':len(rows)-len(valid),
        'changed_text':sum(r['output_text']!=r['input_text'] for r in valid),
        'unchanged_text':sum(r['output_text']==r['input_text'] for r in valid),
        'statuses':status_counts(rows),'accuracy':None,'naturalness':None}

def main():
    registry=Registry(PROJECT);runs={};compared=[];verifications={};matched=None
    for arm in ('single','multi'):
        newdir=PROJECT/'experiments/runs'/f'{BATCH}_cards_{arm}_regression'
        olddir=PROJECT/'experiments/runs'/f'{OLD}_cards_{arm}_regression'
        assert (newdir/'artifact_hashes.json').exists(),'Run not finalized'
        new=read(newdir/'private/results.json');old=read(olddir/'private/results.json');before={r['id']:r for r in old}
        assert len(new)==50 and len({r['id'] for r in new})==50
        matching={r['id'] for r in new if r['input_text']==before[r['id']]['input_text']}
        assert len(matching)==49 and set(before)-matching=={'ADVCE008A'}
        matched=matching if matched is None else matched;assert matching==matched
        registry.register(newdir.name);v=registry.verify(newdir.name);verifications[arm]=v;assert v['status']=='passed',v
        errors=collections.Counter();issues=collections.Counter();repairs=[];holds=collections.Counter();call_errors=[];profile_rows=set();applied_checks=collections.Counter()
        for r in new:
            folder=newdir/'private/records'/r['id'];plan=read(folder/'final_plan.json') if (folder/'final_plan.json').exists() else None
            if r.get('error'):errors[r['error']]+=1
            for meta_path in folder.glob('*_call/meta.json'):
                meta=read(meta_path)
                if meta.get('status')=='failed':call_errors.append({'id':r['id'],'stage':meta_path.parent.name,'error':meta.get('error'),'finish_reason':meta.get('finish_reason')})
            if plan:
                original_plan=read(folder/'transformation_plan.json') if (folder/'transformation_plan.json').exists() else plan
                original_actions={e['edit_id']:e['action'] for e in original_plan['edits']}
                for e in plan['edits']:
                    issues.update(i['code'] for i in e['issues'])
                    if e['outcome']=='needs_review':
                        model=(original_actions.get(e['edit_id']) if r.get('generation_call_skipped') else e['action'])=='needs_review';program=bool(e['issues'])
                        holds['model_and_program' if model and program else 'model_only' if model else 'program_only' if program else 'other']+=1
                        explanation=e['instruction']+' '+e['reason']
                        if any(x in explanation for x in ('target_profile','지역 프로필','지역/시기')):profile_rows.add(r['id'])
                    if e['outcome']=='applied':
                        applied_checks.update(c.get('result','other') for c in e.get('condition_checks',[]) if c.get('field','').startswith('when.'))
                    repairs.extend({'id':r['id'],'edit_id':e['edit_id'],'outcome':e['outcome'],**fix} for fix in e.get('repairs',[]))
            compared.append({'id':r['id'],'arm':arm,'same_input':r['id'] in matching,'input':r['input_text'],
                'before_input':before[r['id']]['input_text'],'before_output':before[r['id']].get('output_text'),'before_status':before[r['id']]['status'],
                'output':r.get('output_text'),'status':r['status'],'error':r.get('error'),'plan':plan,
                'result_path':str((folder/'result.json').relative_to(PROJECT))})
        runs[arm]={'run_id':newdir.name,'old_run_id':olddir.name,'all50':summary(new),
            'matched49_before':summary([r for r in old if r['id'] in matching]),
            'matched49_after':summary([r for r in new if r['id'] in matching]),
            'metrics':read(newdir/'metrics.json'),'errors':dict(errors),'held_reasons':dict(issues),'repairs':repairs,
            'config':read(newdir/'config.json'),'postflight':read(newdir/'postflight.json'), 'hold_origins':dict(holds),'profile_mentioned_in_held_ids':sorted(profile_rows),'applied_condition_states':dict(applied_checks),'call_errors':call_errors}
        assert all(runs[arm]['postflight'].values()),runs[arm]['postflight']
    shared=PROJECT/'experiments/batches'/BATCH/'private/shared'
    identical=[]
    for p in shared.iterdir():
        for filename in ['morphology.json','analysis_call/parsed.json','reference_packet.json']:
            if not (p/filename).exists():continue
            blobs=[(p/filename).read_bytes()]+[(PROJECT/'experiments/runs'/runs[a]['run_id']/'private/records'/p.name/filename).read_bytes() for a in runs]
            identical.append(all(blob==blobs[0] for blob in blobs))
    assert identical and all(identical)
    resources=read(PROJECT/'experiments/batches'/BATCH/'resources.json')
    result={'batch_id':BATCH,'runs':runs,'resources':resources,'matching_inputs':49,'changed_input':'ADVCE008A',
        'shared_file_checks':len(identical),'all_shared_files_identical':True,'artifact_verifications':verifications,
        'limits':['No native gold scores; output change is not quality.','Validation, prompts and input version changed; not a single-factor causal experiment.',
                  'Only 49 unchanged inputs directly paired with historical run.','Remote serving load/hardware may differ; latency is observational.']}
    save(BASE/'private/comparison.json',result);save(BASE/'private/cases.json',compared)
    save(BASE/'private/comparison_hashes.json',{str(p.relative_to(PROJECT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [BASE/'private/comparison.json',BASE/'private/cases.json']})
    esc=lambda s:html.escape(str(s if s is not None else '출력 없음'))
    page='<h1>50문장 재실험 결과</h1><p class="lead">새 Qwen 출력과 이전 출력을 비교합니다. 표의 숫자는 실행 결과이며, 방언 정답률이 아닙니다.</p>'
    page+='<p class="warn"><strong>판단: 재실험은 끝났지만, 자연스러운 방언 생성 문제는 아직 해결되지 않았습니다.</strong> 잘못된 수정을 일부 막았으나, 문장 구조가 깨지는 출력도 여전히 통과했습니다.</p>'
    page+='<div class="flow">문장 50개 → 공통 분석·KG 조회 → Single 50개 / Multi 50개 → 검사·반영</div>'
    page+='<h2>이번 50개 결과</h2><table><tr><th>방식</th><th>전체 또는 일부 변경</th><th>원문 유지·보류</th><th>출력 실패</th></tr>'
    for arm,r in runs.items():
        s=r['all50'];page+=f'<tr><td>{arm.title()}</td><td>{s["changed_text"]}</td><td>{s["unchanged_text"]}</td><td>{s["without_output"]}</td></tr>'
    page+='</table><p>검사가 수정 일부를 막아서 원문이 유지될 수 있습니다. 실패·보류가 줄어도 자연스러운 방언이 늘었다고 단정하지 않습니다.</p>'
    page+='<details><summary>이전 실험과 비교 — 같은 원문 49개</summary><table><tr><th>방식</th><th>이전 출력 실패</th><th>이번 출력 실패</th><th>이전 변경 출력</th><th>이번 변경 출력</th></tr>'
    for arm,r in runs.items():
        a,b=r['matched49_before'],r['matched49_after'];page+=f'<tr><td>{arm.title()}</td><td>{a["without_output"]}</td><td>{b["without_output"]}</td><td>{a["changed_text"]}</td><td>{b["changed_text"]}</td></tr>'
    page+='</table><p>ADVCE008A는 사용자가 원문을 수정했으므로 위 비교에서 제외했습니다. 새 검사는 이전보다 다르므로 이것은 같은 기준의 정확도 비교가 아닙니다.</p></details>'
    page+='<details><summary>실패·보류 집계 자세히 보기</summary><h2>어디에서 막혔나</h2>'
    for arm,r in runs.items():
        page+='<h3>'+arm.title()+'</h3><ul>'
        for error,n in sorted(r['errors'].items(),key=lambda x:-x[1])[:7]:page+='<li>'+esc(REASONS.get(error,error))+f' — {n}개 문장</li>'
        for reason,n in sorted(r['held_reasons'].items(),key=lambda x:-x[1])[:6]:page+='<li>'+esc(REASONS.get(reason,reason))+f' — {n}개 수정 지적</li>'
        page+='</ul>'
    page+='<h2>보류는 누가 결정했나</h2><p>아래는 문장 수가 아니라 수정할 부분의 개수입니다. 한 문장에 여러 수정이 있을 수 있습니다.</p><table><tr><th>방식</th><th>모델이 스스로 보류</th><th>프로그램이 보류</th><th>둘 다 보류</th></tr>'
    for arm,r in runs.items():
        h=r['hold_origins'];page+=f'<tr><td>{arm.title()}</td><td>{h.get("model_only",0)}</td><td>{h.get("program_only",0)}</td><td>{h.get("model_and_program",0)}</td></tr>'
    page+='</table>'
    page+='</details>'
    findings=read(BASE/'private/root_findings.json')
    page+='<h2>실제로 발견한 문제와 다음 수정</h2><p>아래는 연구 리드의 로그 대조 결과입니다. 새로운 두 Reviewer의 재검토나 사람의 점수는 아닙니다. 설명을 펼치면 원인과 수정 방향을 볼 수 있습니다.</p>'
    for f in findings['findings']:
        page+='<details><summary>'+esc(f['title'])+'</summary><p><strong>'+esc(f['case']+' / '+f['arm']+' / '+f['stage'])+'</strong></p><p>'+esc(f['observation'])+'</p><p><strong>확인 범위:</strong> '+esc(f['cause_status'])+'</p><p><strong>다음 수정안:</strong> '+esc(f['proposal'])+'</p></details>'
    page+='<h2>다음 작업 순서</h2><ol><li>이번 실험에 필요한 문법 조건과, 나중에 쓸 지역·시기 설정을 분리합니다.</li><li>반말/높임말, 질문 종류, 관형·인용 관계, 회상 표현을 문장 분석과 카드 조건에 맞춰 연결합니다.</li><li>활용형 조합과 응답 형식 오류를 고친 뒤, 단계 하나만 바꾸는 확인 실험을 합니다.</li><li>확인된 수정으로 같은 50개를 다시 비교합니다.</li></ol><p>위 수정과 추가 Qwen 호출은 아직 수행하지 않았습니다. 이번 결과를 보고 범위를 합의한 다음 진행합니다.</p>'
    page+='<h2>시간과 호출</h2><p>실제 모델 요청 '+str(resources['physical_api_attempts'])+'회 · 총 토큰 '+str(resources['physical_total_tokens'])+' · 분석부터 저장까지 '+str(round(resources['wall_seconds']/60,1))+'분. 준비·서버 기동 시간은 제외했습니다.</p>'
    page+='<table><tr><th>방식</th><th>모델 호출</th><th>총 토큰</th><th>입력당 처리 시간 중앙값</th></tr>'
    for arm,r in runs.items():
        m=r['metrics'];page+=f'<tr><td>{arm.title()}</td><td>{m["api_attempts"]}</td><td>{m["reported_usage"]["total_tokens"]:,}</td><td>{m["median_record_seconds"]}초</td></tr>'
    page+='</table><p>각 방식의 토큰·호출 수는 공통 분석 비용을 각각 포함하므로 두 행을 합하면 중복됩니다. 입력당 시간은 공통 분석·조회 시간에 해당 방식의 계획·생성 처리 시간을 더한 값이며, 보류로 생성 호출을 건너뛴 입력도 포함합니다. 따라서 빠른 시간이 더 좋은 번역을 뜻하지 않습니다. 원화 비용과 GPU 사용량은 측정하지 않았습니다.</p>'
    page+='<p>두 방식의 문장 분석과 조회 자료가 같은지 '+str(len(identical))+'개 파일 비교로 확인했습니다. 입력·코드·KG 보존 검사와 실행 파일 검증도 통과했습니다.</p>'
    page+='<h2>원문과 실제 출력 50개</h2><p>각 문장을 펼치면 이전 출력과 이번 출력이 함께 나옵니다.</p>'
    by=collections.defaultdict(dict)
    for row in compared:by[row['id']][row['arm']]=row
    order=[r['id'] for r in load_jsonl(PROJECT/'data/derived_private/standard_inputs_50_20261029_v2/inputs.jsonl')]
    for key in order:
        data=by[key];page+='<details><summary>'+esc(key+' · '+data['single']['input'])+'</summary>'
        if not data['single']['same_input']:page+='<p class="warn">이전 원문과 달라 직접 성능 비교하지 않습니다. 이전 원문: '+esc(data['single']['before_input'])+'</p>'
        for arm,row in data.items():
            page+='<h3>'+arm.title()+'</h3><p>이전: '+esc(row['before_output'])+'</p><p class="output">이번: '+esc(row['output'])+'</p><p>'+esc(LABELS.get(row['status'],row['status']))+'</p>'
            if row['error']:page+='<p>이유: '+esc(REASONS.get(row['error'],row['error']))+'</p>'
            if row['plan']:
                page+='<details><summary>수정 또는 보류 이유</summary><table><tr><th>원문 부분</th><th>모델 제안</th><th>처리</th><th>이유</th></tr>'
                for e in row['plan']['edits']:
                    reasons=' / '.join(REASONS.get(i['code'],i['code']) for i in e['issues']) or e['reason']
                    page+='<tr><td>'+esc(e['before'])+'</td><td>'+esc(e['proposed_after'])+'</td><td>'+esc({'applied':'반영','needs_review':'보류','kept':'유지','unchanged':'변경 없음'}.get(e['outcome'],e['outcome']))+'</td><td>'+esc(reasons)+'</td></tr>'
                page+='</table></details>'
        page+='</details>'
    css='body{font:18px/1.8 system-ui,sans-serif;background:#f5f7fa;color:#183047;margin:0}main{max-width:1100px;margin:auto;padding:30px}h1{font-size:32px}h2{margin-top:32px}.lead,.flow{padding:18px;background:#e6effe;border-radius:10px}table{border-collapse:collapse;width:100%;background:white;font-size:16px}td,th{padding:12px;border-bottom:1px solid #d7e0ec;vertical-align:top;text-align:left}th{background:#e8eef6}details{padding:18px;background:white;border:1px solid #d7e0ec;border-radius:10px;margin:14px 0}summary{font-weight:bold;cursor:pointer}.output{padding:14px;background:#f1f6fd}.warn{color:#815200}p,td{overflow-wrap:anywhere}@media(max-width:600px){main{padding:12px}td,th{padding:6px}}'
    (BASE/'private/report.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>50문장 실제 재실험</title><link rel="stylesheet" href="report.css"><main>'+page+'</main></html>',encoding='utf-8')
    (BASE/'private/report.css').write_text(css,encoding='utf-8')
    print(json.dumps({a:{'all50':r['all50'],'errors':r['errors'],'held_reasons':r['held_reasons']} for a,r in runs.items()},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
