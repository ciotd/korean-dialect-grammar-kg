"""Create a post-run interpretation report without overwriting the frozen run report."""
from pathlib import Path
from html import escape as esc
import json,re,os,argparse,hashlib

def main():
    p=argparse.ArgumentParser();p.add_argument('run',type=Path);a=p.parse_args();run=a.run.resolve()
    analysis=run.parent.parent/'analyses'/(run.name+'_diagnostics');private=analysis/'private';private.mkdir(exist_ok=True)
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    m=read(run/'metrics.json');d=read(analysis/'diagnostics.json');rows=read(run/'private/results.json')
    def rel(path):return Path(os.path.relpath(path,private)).as_posix()
    def href(path,label):return '<a href="'+esc(rel(path))+'">'+esc(label)+'</a>'
    raw=(run/'private/report.html').read_text(encoding='utf-8')
    def rewrite(match):
        value=match.group(1)
        if value.startswith(('http:','https:','#','data:')):return match.group(0)
        return 'href="'+esc(rel((run/'private'/value).resolve()))+'"'
    raw=re.sub(r'href="([^"]+)"',rewrite,raw)
    # The assessments below are explicit builder interpretations of saved examples, not gold labels.
    findings=[
      {'id':'A1','record_ids':['DEV028','DEV030','NEW007'],'finding':'기저 형태 또는 다른 조사형을 원문 구간으로 출력함','interpretation':'예: 입력에 없는 나·은 등을 anchor로 요청했다. 원문 보존 계약 위반으로 생성 전 중단했다.','scope':'자동 검사로 확인한 문자열 오류'},
      {'id':'A2','record_ids':['LONG001','LONG003','LONG004','NEW001','ADVCE008A','QUAL017'],'finding':'단위가 자신이 속한다고 한 절의 구간 바깥에 있음','interpretation':'절 연결·범위가 맞지 않는다. 어떤 절을 고쳐야 하는지는 추가 언어학적 판단이 필요하다.','scope':'자동 검사로 확인한 구조 오류'},
      {'id':'A3','record_ids':['DEV003','DEV005'],'finding':'종결 표현을 완료 보조구성과 혼동한 분석이 근거 선택에 전파됨','interpretation':'선택기는 Qwen의 completion 특징을 받아 종결 보조동사 근거를 제공했다. 생성 모델은 실제 문맥과 맞지 않는다고 보고 적용하지 않았다.','scope':'Builder의 사후 사례 검토. 독립 평가 아님'},
      {'id':'A4','record_ids':['DEV026'],'finding':'출력 검사는 통과했지만 분석 자체에는 오류가 있음','interpretation':'분석은 늦을까 봐를 상위 절로, 조금 일찍 나왔어요를 이유 절로 연결했고, 까·봐를 조사로 분류했다. 실제 변경은 조금→쪼께만 한 곳이다. 구조 검사 통과가 정확한 문법 분석을 뜻하지 않는다.','scope':'Builder의 사후 사례 검토. 원문·응답은 수정하지 않음'},
      {'id':'A5','record_ids':['QUAL020'],'finding':'인용 근거가 있어도 모델이 복합 구성 적용을 보류함','interpretation':'간접 인용 근거가 전달되었지만 생성 모델은 것 같다고의 결합이 명확하지 않다며 원문을 유지했다. 보류가 언어학적으로 반드시 옳다는 뜻은 아니다.','scope':'모델의 보류 이유 관찰'},
    ]
    (private/'qualitative_review.json').write_text(json.dumps({'reviewer':'main_builder','independent_human_review':False,'quality_scores':None,'findings':findings},ensure_ascii=False,indent=2),encoding='utf-8')
    finding_html=''.join('<tr><td>'+esc(x['id'])+'<br>'+esc(', '.join(x['record_ids']))+'</td><td><b>'+esc(x['finding'])+'</b><p>'+esc(x['interpretation'])+'</p><small>'+esc(x['scope'])+'</small></td></tr>' for x in findings)
    intro='''<section><h2>먼저 읽을 결론: 연결 구현은 완료했지만, 문법 방언화 성과는 확인하지 못했습니다.</h2><p>50개 입력을 모두 시도했습니다. <b>35개는 출력 검사까지 통과했고, 15개는 분석 검사에서 중단</b>됐습니다. 35개 가운데 34개는 원문 그대로이고, 한 개만 부사 ‘조금’을 ‘쪼께만’으로 바꿨습니다. 어미·조사 등의 문법 변환 성과가 확인된 실행은 아닙니다.</p><p class="notice">35/50은 <b>파이프라인의 구조 검사 통과 비율</b>이지 정확도가 아닙니다. 1/50도 올바른 방언 변환 성공률이 아닙니다. 정답·화자 평가가 없으므로 품질 점수는 비워 두었습니다.</p><table><tr><th>측정 항목</th><th>결과</th><th>해석</th></tr><tr><td>입력 처리</td><td>50건</td><td>실패도 포함한 전체 분모</td></tr><tr><td>분석 검사 통과</td><td>35건</td><td>원문 구간·ID·절 참조 등 형식/구조 검사</td></tr><tr><td>분석 중단</td><td>15건</td><td>원문 구간 불일치 9건, 절 구간 불일치 6건</td></tr><tr><td>변환 참고 근거를 전달한 입력</td><td>4건</td><td>적절성이 검증된 4건이라는 뜻은 아님</td></tr><tr><td>입력과 다른 최종 출력</td><td>1건</td><td>DEV026 · 부사 한 곳 변경</td></tr><tr><td>Qwen 호출</td><td>85회</td><td>분석 50회 + 생성 35회, 자동 재시도 없음</td></tr><tr><td>별도 개발 예문 호출</td><td>35회</td><td>5개 예문으로 4차 점검. 50개 평가 수치에 합치지 않음</td></tr></table><p>약 '''+f'{m["wall_seconds"]/60:.2f}'+'''분이 걸렸고, 서버가 보고한 입력 토큰은 '''+f'{m["reported_usage"]["prompt_tokens"]:,}'+''', 출력 토큰은 '''+f'{m["reported_usage"]["completion_tokens"]:,}'+'''개입니다. 비용 금액은 계산하지 않았습니다.</p></section>
<section><h2>왜 대부분의 문장이 유지되거나 중단됐나요?</h2><p><b>첫째, 모델 분석의 안정성이 부족합니다.</b> 원문에 없는 표면형을 쓰거나, 단위를 잘못된 절에 연결했습니다. 문자열 검사를 통과한 입력에서도 의미·문법 기능 해석 오류가 보입니다.</p><p><b>둘째, 현재 활성화한 문헌 참고 범위가 좁습니다.</b> 기존 설계 항목 전체를 검증된 규칙으로 승격하지 않았습니다. 직접 대조 Claim 29개 가운데 구현된 조건만 사용했고, 실제 변환 참고 근거는 3개 Claim에서만 전달됐습니다.</p><p><b>셋째, 분석 오류가 검색·선별에 전파됩니다.</b> 정확히 존재하는 Concept ID를 찾아도 입력 분석이 잘못되면 관련 없는 근거를 고를 수 있습니다. 따라서 ‘실제 ID 사용’과 ‘올바른 개념 선택’을 구별해야 합니다.</p><p>35개 입력에서 실제 Concept ID '''+str(len(d['distinct_actual_concept_ids']))+'''종을 조회했습니다. 넓은 이웃 조회는 8개 입력에서 1,501개 경로 한도에 닿았고 이를 기록했습니다. 직접 대조 Claim 경로는 이 한도로 잘라내지 않았습니다.</p></section>
<section><h2>대표 문제를 실제 기록으로 확인하기</h2><table><tr><th>대상</th><th>관찰과 해석</th></tr>'''+finding_html+'''</table><p>'''+href(private/'qualitative_review.json','사후 사례 검토 JSON')+' · '+href(analysis/'diagnostics.json','오류 분류·단계 시간·Concept 목록')+'''</p></section>
<section><h2>다음 작업의 우선순위</h2><ol><li><b>문법 분석부터 보완:</b> 원문 표면형과 기저 형태소를 구별하고, 절 관계·완료상·문장 종결을 혼동하지 않도록 별도 정답 분석과 검증 예문을 만든다.</li><li><b>지원 가능한 문법 근거를 확장:</b> 종결·의문·높임·부정·연결 구성의 문헌 조건을 더 직접 대조하고, 적용 대상·보존 조건을 명시한다. 그래프의 연결 수를 늘리는 것만으로 해결하지 않는다.</li><li><b>생성 단계의 보류 이유를 점검:</b> 근거가 있는데도 적용하지 않는 경우와, 적용하면 안 되는 경우를 사람이 구별한다.</li><li><b>그 뒤 재평가:</b> 이번 50개를 개발에 사용하면 다음 성능 평가는 새로운 미관측 입력과 지역 화자의 평가로 수행한다. KG 없는 조건도 동일 분석·모델 설정으로 비교해야 기여를 판단할 수 있다.</li></ol><p>이 제안들은 후속 작업입니다. 이번 50개 결과를 보고 파이프라인을 수정하거나 재실행하지 않았습니다.</p></section>'''
    raw=raw.replace('<main>','<main>'+intro,1)
    provenance='<section><h2>원 실행과 검토 기록의 구분</h2><p>이 문서는 원 실행 보고서를 기반으로 사후 해석을 덧붙인 별도 판본입니다. 고정 실행의 입력·출력·코드·설정을 덮어쓰지 않았습니다.</p><p>'+href(run/'private/report.html','변경하지 않은 원 실행 보고서')+' · '+href(run/'postflight.json','코드·입력·KG 불변 확인')+' · '+href(run.parent.parent/'validation/kg_pipeline_20261023/unit_tests.json','30개 단위 검사 기록')+' · '+href(run.parent.parent/'validation/kg_pipeline_20261023/smoke_history.json','별도 개발 시험 4회 이력')+'</p></section>'
    raw=raw.replace('</main>',provenance+'</main>',1)
    (private/'report.html').write_text(raw,encoding='utf-8')
    meta={'source_run_id':run.name,'source_artifact_manifest_sha256':hashlib.sha256((run/'artifact_hashes.json').read_bytes()).hexdigest(),
      'renderer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
      'report_sha256':hashlib.sha256((private/'report.html').read_bytes()).hexdigest(),'original_run_modified':False}
    (analysis/'review_manifest.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    print(str(private/'report.html'))
if __name__=='__main__':main()
