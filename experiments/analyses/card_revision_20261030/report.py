"""Human-readable before/after card content; no model calls."""
import html,json,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[2];sys.path.insert(0,str(ROOT/'src'))
from kg_pipeline.io import read,save,sha

def main():
    folder=ROOT/'knowledge/authored/kg_cards_20261030_v3';data=read(folder/'cards.json');stats=read(folder/'statistics.json')
    old=read(ROOT/'knowledge/authored/kg_cards_20261028_v2/cards.json');before={c['id']:c for c in old['cards']}
    provenance=read(folder/'provenance.json');E=lambda x:html.escape(str(x))
    h='<h1>카드 내용을 이렇게 고쳤습니다</h1><p class="lead">방언 표현의 목록에 <strong>어떤 원문을 어떻게 바꾸는지</strong>를 더했습니다.<br>새 버전: kg_cards_20261030_v3</p>'
    h+='<table><tr><th>전체 카드</th><th>내용 정리</th><th>변환 안내 추가</th><th>기존 내용 유지</th></tr><tr>'+''.join('<td>'+str(v)+'개</td>' for v in [721,stats['changed_cards'],stats['directional_cards'],721-stats['changed_cards']])+'</tr></table>'
    h+='<p>573개 중 563개는 출처·지역 설정 같은 관리 정보를 별도 기록으로 옮겼고, 10개에는 변환 안내도 추가했습니다. 나머지 148개는 그대로입니다. 721개 모두를 새 변환 규칙으로 검증했다는 뜻은 아닙니다.</p>'
    h+='<h2>핵심 변화</h2><table><tr><th>이전 카드가 주던 정보</th><th>새 카드가 알려주는 것</th></tr><tr><td>-네예라는 평서 표현이 있다</td><td>이미 -네요인 종결을 -네예로 바꾸고, 앞의 시제·높임은 유지</td></tr><tr><td>-라예라는 표현이 있다</td><td>긍정 현재 계사의 이에요/예요에 사용. 부정·과거·인용과 구별</td></tr><tr><td>-요와 -예가 모두 가능하다</td><td>이번 방언 생성에서는 조건이 맞는 -예를 목표로 선택. 요 앞의 활용을 지우지 않음</td></tr><tr><td>지역 설정이 required로 남아 있음</td><td>해당 정보는 출처 기록에 보존하고 생성용 조건에서 분리</td></tr></table>'
    h+='<div class="flow">기존 KG 조회·카드 선별<br>↓ 같은 카드 ID·같은 순서<br><strong>새 카드 내용으로 교체</strong><br>↓<br>기존 Qwen 지시·생성·검사</div>'
    h+='<p>표현 배열과 번호, 검색 순위 계산, 원본 KG는 유지했습니다. 새 버전은 실행할 때 명시적으로 선택합니다. 기존 기본 실행은 이전 버전으로 재현할 수 있습니다.</p>'
    h+='<h2>고친 10개 카드</h2><p>펼치면 조건·목표·유지할 내용·제외할 경우를 볼 수 있습니다. 이것은 Codex가 문헌과 승인 예문에 근거해 정리한 안내이며, Qwen이 자동으로 지킨다는 보장은 아닙니다.</p>'
    for c in data['cards']:
        if 'rewrite' not in c:continue
        d=c['rewrite'];pv=provenance[c['id']]
        h+='<details><summary>'+E(c['title'])+'</summary><table>'
        for label,value in [('원문 조건',d['source']),('변환 방법',d['operation']),('유지할 내용',' · '.join(d['preserve'])),('적용하지 않을 경우',' · '.join(d['exclude']))]:
            h+='<tr><th>'+label+'</th><td>'+E(value)+'</td></tr>'
        h+='</table><p class="small">카드 ID: '+E(c['id'])+' · 표현 목록 유지: '+E(', '.join(c['forms']))+'</p>'
        h+='<p class="small">문헌 확인: '+E(', '.join(x['doc']+' PDF '+str(x['page'])+'쪽' for x in pv['rewrite_evidence']))+'<br>승인 예문 참조: '+E(', '.join(pv['approved_example_ids']))+'</p>'
        h+='<p class="small">승인 예문은 해당 문장의 수용 근거입니다. 이를 재사용 가능한 조건으로 정리한 부분은 이번 설계 판단입니다. 이전 조건과 원본 출처는 별도 provenance 파일에 모두 남겼습니다.</p></details>'
    h+='<h2>검토자가 지적해 고친 부분</h2><table><tr><th>검토</th><th>지적과 반영</th></tr><tr><td>문법·근거 검토자</td><td>과거·부정 계사도 요→예 안내에 포함. 약속 -께예와 원인 간께예 구별. -라/-래를 무작위로 교환하지 않도록 결합 조건 보완.</td></tr><tr><td>코드 호환성 검토자</td><td>기존 선별 후 같은 ID로 치환. 표현 번호 보존. 새 내용에 맞는 요청 식별값 재생성. 방향 안내의 작성 주체를 사람으로 잘못 기록한 부분을 Codex로 정정.</td></tr></table>'
    h+='<h2>확인한 것과 아직 남은 것</h2><ul><li>카드·생성·검사 관련 자동 테스트 81개 통과.</li><li>실제 기록에서 이전 49개 입력의 카드 전달과, 앞선 전달 실험의 26개 목록을 새 내용으로 바꾸는 검사 75개 통과. 이전 분석 실패 1개는 그대로 표시.</li><li>시험용 계획 6개가 기존 검사·문장 조립을 통과했습니다. Qwen이 스스로 생성한 결과는 아닙니다.</li><li><strong>새 Qwen 호출 0회.</strong> 방언 품질이 좋아졌는지는 다음 비교 실험에서 확인해야 합니다.</li><li>한 편집의 오류가 문장 전체를 중단시키는 처리와 요의 품사 해석 차이는 이번에 고치지 않았습니다.</li></ul>'
    examples=read(BASE/'private/compatibility_cases.json');h+='<details><summary>시험용 계획 6개 보기 — 모델 실험 아님</summary><table><tr><th>입력</th><th>미리 지정한 결과</th><th>검사·조립</th></tr>'
    for e in examples:h+='<tr><td>'+E(e['input'])+'</td><td>'+E(e['proposed'])+'</td><td>'+E(e.get('output',e.get('error')) )+'</td></tr>'
    h+='</table></details><h2>다음 비교 방식</h2><p>앞선 실험에서 사용한 같은 분석과 같은 카드 ID를 두고, 이전 내용과 새 내용만 바꿔 비교합니다. 모델 지시나 오류 처리까지 동시에 고치지 않아야 카드 보완의 영향을 구분할 수 있습니다. 이번 작업은 카드 수정·통합·오프라인 검증까지 완료한 단계입니다.</p>'
    css='body{font:17px/1.8 system-ui,sans-serif;color:#173047;background:#f5f7fb;margin:0}main{max-width:1080px;margin:auto;padding:28px}h1{font-size:30px}h2{margin-top:30px}table{border-collapse:collapse;width:100%;margin:16px 0;background:white}td,th{padding:12px;border:1px solid #d8e1ed;text-align:left;vertical-align:top;overflow-wrap:anywhere}th{background:#edf2f8}.lead,.flow{background:#e9f1ff;padding:20px;border-radius:12px}.flow{text-align:center;background:#e8f5f0}details{background:white;border:1px solid #d8e1ed;border-radius:10px;padding:16px;margin:12px 0}summary{cursor:pointer;font-weight:650}.small{font-size:13px;color:#425b70}@media(max-width:650px){main{padding:12px}td,th{padding:6px;font-size:14px}}'
    (BASE/'private/report.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>카드 내용 보완</title><link rel="stylesheet" href="report.css"><main>'+h+'</main></html>',encoding='utf-8')
    (BASE/'private/report.css').write_text(css,encoding='utf-8')
    save(BASE/'private/report_sources.json',{'cards':sha((folder/'cards.json').read_bytes()),'statistics':stats,'new_qwen_calls':0})

if __name__=='__main__':main()
