"""Readable, offline report generated from measured records (no CDN)."""
import html
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def esc(v):return html.escape(str(v))
def text(v):
    if isinstance(v,list):return '<br>'.join(text(x) for x in v)
    if isinstance(v,dict):return '<br>'.join(esc(k)+': '+text(x) for k,x in v.items())
    return esc(v)
def table(headers,rows):return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+esc(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(x)+'</td>' for x in r)+'</tr>' for r in rows)+'</tbody></table></div>'
def main():
    s=read(HERE/'summary.json');n=read(HERE/'natural_summary.json')
    examples=read(HERE/'private/claude_examples.json');obs=read(HERE/'private/natural_observations.json')
    payloads=read(HERE/'private/delivery_comparison.json')
    statuses={'requires_meaning_and_relations':'형태 후보 있음 · 의미와 연결 판단은 아직 안 함','target_exists_no_supported_unit':'원문에 해당 표현은 있으나 지원 종류의 분석 단위 없음','target_string_missing':'확인 대상 문자열이 원문에 없음','observed_conditions_block_all':'실제 형태가 저장 조건과 다름'}
    verdicts={'ready':'Claude: 예문 후보 준비','needs_revision':'설명·조건 보완 필요','unresolved':'근거·해석 추가 확인 필요'}
    h=['<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>문법 조건 검사와 전달 보완 · 11월 10일</title><style>body{margin:0;background:#f4f6fa;color:#192b3b;font:17px/1.75 "Malgun Gothic",sans-serif}main{max-width:1100px;margin:auto;padding:32px 24px}h1{font-size:32px;line-height:1.4}h2{margin-top:42px;color:#174c69}h3{font-size:19px}p{max-width:950px}.lead,section,details{background:white;border:1px solid #dbe3ec;border-radius:14px;padding:22px;margin:16px 0}.lead{border-left:6px solid #167583}.muted{color:#52677b;font-size:15px}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:15px}th,td{padding:12px;border-bottom:1px solid #dce4ec;vertical-align:top;text-align:left;min-width:120px}th{background:#edf3f8}summary{cursor:pointer;font-weight:bold;overflow-wrap:anywhere}input{font:inherit;padding:10px;width:min(90%,700px);border:1px solid #91a5b8;border-radius:8px}a{color:#006c9e}code{font-size:13px;overflow-wrap:anywhere}.bad{border-left:5px solid #b66d23}.flow{display:flex;flex-wrap:wrap;gap:10px}.flow span{background:#e9f2f6;padding:12px;border-radius:8px} @media print{input{display:none}details{break-inside:avoid}main{padding:0}body{background:white}}</style><main>']
    h+=['<p class="muted">2026년 11월 10일 · 전체 KG 구조 검사 다음 단계</p><h1>규칙을 찾는 조건과<br>Qwen에게 건네는 내용을 점검했습니다</h1>',
        '<div class="lead"><b>결론: 전달 누락과 낡은 지시 일부는 고쳤습니다. 전체 번역이 좋아졌다는 결론은 아직 아닙니다.</b><p>실제 문장 171개를 형태 분석기에 넣어 보니, 의미를 판단하기 전부터 막히는 경우가 드러났습니다. 이제는 생성 프롬프트를 계속 바꾸기보다, 이 지점부터 구별해 고칠 수 있습니다.</p><p>이번에는 Qwen을 새로 호출하지 않았습니다. 아래의 “통과”는 프로그램 검사이며 자연스러운 방언 평가가 아닙니다.</p></div>',
        '<h2>1. 이번에 한 일과 하지 않은 일</h2>']
    h.append(table(['작업','실제 결과','해석하면 안 되는 것'],[
        ['저장 조건의 논리 재검사',f'{s["logic_passed"]}/{s["logic_cases_reused"]} 일치. 분기 평가 876개 + 단위 종류 배정 114개.','문헌 내용 자체가 모두 옳다는 뜻은 아님'],
        ['생성에 보낼 정보 검사',f'56규칙의 {s["delivery_fields_checked"]}개 검사항목 확인, 57분기 전달 표본 보존.','Qwen이 이 지시를 따랐다는 뜻은 아님'],
        ['자연어 예문 준비·형태 분석','57분기마다 적용·비적용·판단 검토 후보 = 171문장. 실제 Kiwi 실행.','Qwen 의미 분석·조회·번역을 171회 완료한 것이 아님'],
        ['KG 문법 조건','기존 조건과 관계 유지. 그래프 파일 해시 동일.','미지원 문법을 새로 확장한 것은 아님'],
        ['두 검토자','기존 Orca Claude와 Codex의 검토 수령·수정 반영.','모델 의견을 사람의 정답 인증으로 쓰지 않음']]))
    h+=['<h2>2. 무엇을 고쳤나요?</h2><p>같은 주의사항도 저장 이름이 달라 빠졌습니다. 이제 두 이름을 모두 읽습니다. 두 내용이 다르면 하나를 버리지 않고 둘 다 남깁니다. 그리고 어미를 바꿀 위치, 어간·시제를 보존하는 처리 지시를 함께 전달합니다.</p>']
    h.append(table(['이전 문제','이번 보완','남은 범위'],[
        ['limits에 저장한 제한을 읽지 않음','limitations와 함께 읽도록 수정','문구의 언어학적 타당성은 별도 검토'],
        ['실현형의 처리 방법·검사 조건 누락','실현형 종류·처리 방법·출력 조건 전달','전달은 실행·품질 보증이 아님'],
        ['상위 구성의 범위 조건은 검사하지만 조회 경로에 표시하지 않음','해당 관계 ID를 실제 경로 기록에 포함','문법 조건 판정 자체는 동일'],
        ['“ㄹ게는 절대 일치하지 않음”처럼 현재 코드와 반대인 메모','6규칙의 확인된 낡은 문장만 제거','나머지 혼합 메모와 설명·조건 충돌은 남음'],
        ['필드가 없는 규칙도 검사 통과로 집계','필드 수·실현형 개수 검사 및 삭제 반례 추가','수정 전 집계도 보존']]))
    h+=['<h2>3. 실제 문장으로 찾은 막힘</h2><p>아래는 “틀린 번역”이 아니라, 번역에 앞서 입력을 읽고 필요한 지식으로 연결할 때 발견한 문제입니다.</p>']
    h.append(table(['입력 예문','어디서 막히나','다음 해결 방향'],[
        ['사과하고 배를 샀어.','명사 “사과+하고”와 동사 “사과하다”가 겹침. 이번 Kiwi 분석에서 조사 후보를 찾지 못함.','문맥상 명사 나열인지 확인하는 분석 보완. 쉬운 다른 예문으로 덮어버리지 않고 이 반례 유지.'],
        ['철수 오거든 이것 좀 전해 줘.','“거든”을 연결어미 대신 종결어미로 읽는 경우. 연결 단위가 없어 조회 이전에 막힘.','절 연결 분석과 형태 후보의 충돌을 기록하고 재확인하는 방법 검토.'],
        ['선생님, 이제 그만 들어가시지요.','분석 결과는 시+지요. KG 조건은 시지요/으시지요를 기대.','높임 시와 종결 지요의 조합으로 같은 표현을 인식하도록 조건 연결안 검토. “지요” 전체를 무조건 허용하지 않음.'],
        ['지갑에 천 원밖에 없어.','처음 검사표가 “천 원밖에” 전체를 한 단위에서 찾으려 함.','예문 표시 범위와 실제 분석 단위 범위를 분리해 검사표 수정. KG 오류로 집계하지 않음.'],
        ['그건 제 거예요.','KG는 일반 명사만 허용하고 의존명사 “거”는 제외.','현재로서는 명확한 지원 범위 밖. 의미 미확정과 구별하고 확장 근거 확인.']]))
    h+=['<h2>4. 예문 전체를 확인하세요</h2><p>Claude의 최초 분류는 40개 준비 후보·15개 보완 필요·2개 판단 보류입니다. 준비 후보도 사람 정답이 아닙니다. 특히 아래 “판단 검토”에는 문맥 모호성과 지원 범위 질문이 함께 있어, 모두 조회 결과 unknown을 기대하면 안 됩니다.</p>',
        '<p>적용 후보 57개 중 54개는 형태 후보가 발견됐고, 2개는 대상 종류를 찾지 못했으며, 1개는 형태 조건이 달랐습니다. 54개도 의미·관계가 맞는지 아직 확인해야 합니다.</p>',
        '<label>문장·규칙 검색 <input id="search" placeholder="예: 주세요, 높임, INT_END"></label><p id="count" class="muted"></p>']
    for e in examples:
        rows=[]
        for cat,label in [('positive','적용 후보'),('negative','비적용 후보'),('unknown','판단 검토 후보')]:
            o=next(r for r in obs if r['branch_id']==e['branch_id'] and r['category']==cat)
            rows.append([label,esc(o['text'])+'<br><small>확인 부분: '+esc(o['target'])+'</small>',esc(o['reviewer_reason']),statuses[o['status']]])
        h.append('<details class="example"><summary>'+esc(e['positive']['text'])+' — '+verdicts[e['verdict']]+'</summary><p class="muted">추적 ID: <code>'+esc(e['branch_id'])+'</code></p>'+table(['종류','문장','검토자의 이유','실제 형태 관찰'],rows)+'<p><b>남은 쟁점</b><br>'+text(e['issues'])+'</p></details>')
    h+=['<h2>5. 다음 작업과 끝나는 기준</h2><div class="flow"><span>문장별 기대 판단 확정</span><span>→ 분석·조회 실제 연결</span><span>→ 전달 내용 확인</span><span>→ 같은 지식으로 생성 비교</span></div><p>우선 앞의 세 가지 실제 연결 문제와 설명·조건 충돌을 구별합니다. 분기마다 적용·비적용·미확정의 기대 판단 또는 보류 이유가 정리되면 예문 준비를 마칩니다. 그다음 검토된 사례로 실제 Qwen 분석부터 생성까지 실행하고, 처음 어긋난 단계별로 기록합니다.</p><p>지식이 제대로 도착했는데 생성만 틀리면 생성 방식 비교로 넘깁니다. 문헌 충돌이나 높임 등급 변경이 필요하면 근거와 선택지를 드리고 사용자 판단을 받습니다. 같은 프롬프트만 반복 수정하지 않습니다.</p>',
        '<h2>6. 검토와 원본 기록</h2><p><a href="../REVIEW_RESOLUTION.md">검토 의견과 반영 내역</a> · <a href="../RESULTS.md">결과와 남은 작업</a> · <a href="../PLAN.md">이번 범위</a></p><p class="muted">기존 KG와 실행 결과는 보존했습니다. 최신 모델 호출·자연스러움 평가·50문장 재실험은 이번에 수행하지 않았습니다. 이 문서는 공개 사이트가 아닌 로컬 보고서입니다.</p>',
        '<script>const q=document.querySelector("#search");function filter(){let n=0;document.querySelectorAll(".example").forEach(e=>{e.hidden=!e.textContent.toLowerCase().includes(q.value.toLowerCase());if(!e.hidden)n++});document.querySelector("#count").textContent=n+" / 57개 조건 묶음 표시"}q.addEventListener("input",filter);filter()</script></main></html>']
    (HERE/'private/report.html').write_text(''.join(h),encoding='utf-8')
    print('report: '+str(HERE/'private/report.html'))
if __name__=='__main__':main()
