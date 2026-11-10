"""Build a short human-facing summary from actual tests, offline audit and reviewer records."""
import collections
import hashlib
import html
import json
import re
import shutil
import sys
from pathlib import Path
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[2];sys.path[:0]=[str(PROJECT/'src'),str(PROJECT/'local/python')]
from kg_pipeline.io import read,save
from kg_runtime import edit_contract as ec
from research_management.work import WorkStore

CHANGES=[
 ('찾은 설명과 다르게 바꿈','카드·목표 형태·원문의 어느 형태소를 바꾸는지 연결하고 대조한다.'),
 ('글자를 잘못 붙임','선택한 받침을 합치고, 일부 잘못된 활용은 원래 형태소와 Kiwi로 다시 조합한다. 바꾼 내역을 남긴다.'),
 ('띄어쓰기가 있으면 실패','한 단어가 여러 단어로 바뀌는 표현을 허용한다. 선택한 문법 설명에 맞는지도 확인한다.'),
 ('동사·과거 표시가 달라짐','원래 형태소를 남긴 조합과 비교하고, 다르면 재분석한다. 의심되는 수정은 보류한다.'),
 ('참고 설명을 수정 명령으로 사용','관찰·분류·금지 정보를 구분한다. 해결되지 않은 중요한 조건도 표시한다.'),
 ('여러 단어를 묶다가 뜻을 잃음','각 수정이 가리키는 원문 위치를 지정한다. 기존 단어를 보존하는 조합을 확인할 수 없으면 그 묶음을 보류한다.'),
 ('샀어를 무조건 샀지로 바꿈','DEV002 제한을 지킨다. 다른 문장의 -지/-제는 응답·확인 등 별도 근거를 요구한다.'),
 ('한 수정 때문에 전체가 실패','문제가 있는 수정과 독립된 수정을 구분한다. 함께 처리해야 하는 묶음도 기록한다.'),
 ('옛 요청이나 다른 결과를 잘못 연결','원문·분석·카드·계획의 버전을 대조한다. 서로 다르면 적용하지 않는다.'),
 ('유지·실패·보류를 혼동','출력 없음, 원문 유지, 일부 반영, 수정 보류를 나눠 기록한다. 불필요한 생성 호출도 생략한다.')]

DISPOSITIONS={
 'codex':[
 ('I01','일부 해결','-지/-제 문맥 근거, 문장 유형·서술어 종류·조사 기능·중요한 미해결 조건을 검사. 모든 문헌 조건의 해석표가 완성된 것은 아님.'),
 ('I02','범위 제한해 해결','다어절은 원문 각 단어의 지정된 수정으로 조합 가능한 경우만 적용. 일반적인 절 구조 분석은 아직 부족함.'),
 ('I03','일부 해결','원래 어휘·선어말어미 보존을 Kiwi로 대조. 어미 내부의 의향·높임 의미 전체를 증명하지는 못함.'),
 ('I04','해결','카드마다 원문 어절과 형태소 위치를 지정. 조사 기능을 대조. 한 단어 내부의 복잡한 복수 조합은 보류.'),
 ('I05','일부 해결','명시적 대안 표기와 Kiwi의 축약 조합을 활용. 다른 정상 표면형을 문자열 불일치만으로 차단하지 않음. 특수 표기는 별도 목록.'),
 ('I06','해결','DEV002의 해당 구간을 포함하는 큰 편집에도 제한 적용.'),
 ('I07','일부 해결','이미 유지된 상태도 의존 조건 충족으로 취급. 모델이 의존성을 빠뜨렸는지는 완전히 검증하지 못함.'),
 ('I08','해결','과거 실행 실패·변환 가능한 기록·새 검사 결과를 분리. 추정한 목표와 새 모델 출력을 구분.')],
 'claude':[
 ('I1','일부 해결','단순 평서와 응답을 분리하고 실제 입력 인용을 요구. 문맥 판단 자체는 모델 추론임.'),
 ('I2','해법 수정해 일부 해결','문자열에 과거 표시가 없다는 이유만으로 오답 판정하지 않음. 원래 형태소·재분석을 대조. 화계 순서표는 임의로 만들지 않음.'),
 ('I3','일부 해결','차단 역할을 데이터로 옮기고 주요 미해결 avoid를 검사. 전체 KG의 모든 차단 관계 실행은 미완성.'),
 ('I4','해법 수정해 해결','태그 패턴 몇 개를 참으로 인증하는 대신, 명시된 원문 수정 범위와 보존 조합을 대조한다.'),
 ('I5','해결','원래 실패 21건을 별도 유지. 계획 없는 15건은 재검사 불가로 표시. 감사의 재조립 값을 새 실험으로 세지 않음.'),
 ('I6','일부 해결','일반 축약은 Kiwi 조합·재분석으로 비교. 음장/영형태/음운식 같은 특수 표기는 근거 없이 문자열로 바꾸지 않음.'),
 ('I7','일부 채택','조합 성공을 방언 정답으로 인증하지 않음. 원문 보존 검사·보정 로그 추가. 모든 문자 보정을 무조건 보류하는 제안은 미채택.'),
 ('I8','해결','호출 생략과 모델/프로그램의 보류를 기록. Multi 생성기는 계획을 실현하며 새 카드를 고르지 않는다는 점을 유지.')]
}

def main():
    data=(BASE/'private/tests_final.txt').read_bytes();log=data.decode('utf-16' if data.startswith(b'\xff\xfe') else 'utf-8-sig')
    n=int(re.search(r'Ran (\d+) tests',log)[1]);assert re.search(r'\nOK\s*$',log),log[-1000:]
    old=PROJECT/'experiments/analyses/change_spec_20261030/private'
    evidence=read(old/'evidence_manifest.json');changed=[p for p,h in evidence.items() if hashlib.sha256((PROJECT/p).read_bytes()).hexdigest()!=h];assert not changed
    cards=read(PROJECT/'knowledge/authored/kg_cards_20261028_v2/cards.json')['cards']
    inventory={'cards':len(cards),'roles':dict(collections.Counter(ec.role(c) for c in cards)),
        'unparsed_forms':[{'card_id':c['id'],'form':f} for c in cards for f in c['forms'] if not ec.variants(f)]}
    save(BASE/'private/card_inventory.json',inventory)
    replay=read(BASE/'private/replay.json');rows=replay['rows'];assert len(rows)==50 and len({r['id'] for r in rows})==50
    assert all(set(r['arms'])=={'single','multi'} for r in rows)
    sources=read(BASE/'private/before_hashes.json');files=[p for p,h in sources.items() if hashlib.sha256((PROJECT/p).read_bytes()).hexdigest()!=h]
    files+=['src/kg_runtime/edit_contract.py','src/kg_runtime/suffix_composition.py','src/kg_runtime/card_interpretation.json',
            'src/research_management/core.py','src/research_management/web/app.js','src/research_management/web/index.html',
            'tests/test_edit_contract.py','tests/test_card_integration_v2.py','tests/test_kg_cards.py']
    hashes={}
    for rel in sorted(set(files)):
        p=PROJECT/rel;dest=BASE/'private/final_code'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest);hashes[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
    save(BASE/'private/code_hashes.json',hashes)
    result={'local_tests_passed':n,'new_qwen_calls':0,'historical_inputs':50,'historical_records':100,'historical_failures_preserved':21,
        'unusable_legacy_plans':15,'original_evidence_files_unchanged':len(evidence),'files':list(hashes),'reviewer_findings':{k:len(v) for k,v in DISPOSITIONS.items()},
        'review_scope':'Intermediate implementation independently reviewed; revisions locally tested, not reapproved by reviewers',
        'linguistic_accuracy':None,'naturalness':None,'current_status':'code_and_offline_checks_complete; new Qwen experiment pending approval'}
    save(BASE/'private/result.json',result);save(BASE/'private/reviewer_dispositions.json',DISPOSITIONS)
    esc=lambda x:html.escape(str(x))
    page='<h1>이번에 무엇을 고쳤나</h1><p class="lead">잘못된 수정을 그대로 내보내던 부분을 고쳤습니다.<br><strong>새 방언 생성 실험은 아직 하지 않았습니다.</strong></p>'
    page+='<div class="steps"><span>문장 읽기</span> → <span>문법 설명 찾기</span> → <strong>어디를 어떻게 바꿀지 확인</strong> → <strong>글자 조합·원문 보존 확인</strong> → <span>반영 또는 보류</span></div>'
    page+='<h2>실제로 바뀐 것</h2><table><tr><th>기존 문제</th><th>이번 수정</th></tr>'+''.join('<tr><td>'+esc(a)+'</td><td>'+esc(b)+'</td></tr>' for a,b in CHANGES)+'</table>'
    page+=f'<h2>확인한 결과</h2><ul><li>프로그램 검사 <strong>{n}개 통과</strong>. 방언 정답률을 뜻하지 않습니다.</li><li>기존 50문장·100개 결과를 다시 확인했습니다. Qwen을 새로 호출하지 않았습니다.</li><li>과거 실패 21개는 실패 기록으로 보존했습니다. 그중 15개는 수정 계획이 없어 새 검사도 할 수 없었습니다.</li><li>원본 근거 파일 {len(evidence)}개는 그대로입니다.</li><li>Codex 8개·Claude 8개 지적을 검토해 반영했습니다. 두 검토자는 수정 중간 코드를 보았으며, 최종 수정본은 로컬 검사로 확인했습니다.</li></ul>'
    page+='<h2>아직 해결됐다고 말할 수 없는 것</h2><ul><li>Qwen이 문장의 뜻과 문법을 처음부터 제대로 읽는지.</li><li>어떤 어미가 그 상황에서 자연스러운지, 높임과 의향이 완전히 유지되는지.</li><li>문법 설명에 없는 조건과 모든 예외. 모든 KG 지식이 실행 가능한 규칙이 된 것은 아닙니다.</li><li>새 검사가 정상 표현까지 너무 많이 보류하는지. 실제 재실험으로 확인해야 합니다.</li></ul>'
    page+='<h2>다음에는 무엇을 하나</h2><p><strong>권장: 같은 50문장을 Single·Multi로 다시 생성</strong>하고, 예전 오류가 줄었는지와 보류가 과도한지 비교합니다. 이 새 모델 실행은 사용자 승인 후 진행합니다.</p>'
    page+='<details><summary>예문별로 확인하기 — 기존 결과를 새 검사에 넣은 기록</summary><p>아래 재조립 값은 새 Qwen 번역이 아닙니다. 옛 기록에 없는 목표 형태를 일부 추정했으므로 성능 비교에 사용할 수 없습니다.</p>'
    for r in rows:
        page+='<details><summary>'+esc(r['id']+' · '+r['input'])+'</summary>'
        for arm,a in r['arms'].items():
            page+='<h3>'+esc(arm)+'</h3><p>기존 출력: '+esc(a['old_output'] if a['old_output'] is not None else '출력 실패')+'</p>'
            page+='<p>원래 오류: '+esc(a['old_error'] or '기록 없음')+'</p>'
            for e in a.get('plan',{}).get('edits',[]):
                page+='<p><b>'+esc(e['before'])+'</b> → 제안 '+esc(e['proposed_after'])+' / 검사 뒤 형태 '+esc(e['after'])+' / '+esc({'applied':'반영 후보','needs_review':'보류','kept':'유지','unchanged':'변경 없음'}.get(e['outcome'],e['outcome']))+'</p>'
            if a['adaptation_gaps']:page+='<p>옛 기록에 목표나 적용 위치가 명확히 없어 판단이 제한됩니다.</p>'
        page+='</details>'
    page+='</details><details><summary>두 검토자의 지적을 어떻게 처리했나</summary>'
    for who,items in DISPOSITIONS.items():
        page+='<h3>'+who+'</h3><table><tr><th>번호</th><th>처리</th><th>내용</th></tr>'+''.join('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in item)+'</tr>' for item in items)+'</table>'
    page+='</details>'
    css='body{font:18px/1.8 system-ui,sans-serif;color:#182e45;background:#f5f7fb;margin:0}main{max-width:1000px;margin:auto;padding:32px}h1{font-size:32px}h2{margin-top:36px}p,li{max-width:880px}.lead,.steps{padding:20px;background:#e6efff;border-radius:12px}.steps{font-size:16px}table{width:100%;border-collapse:collapse;background:white;font-size:16px}td,th{padding:13px;text-align:left;border-bottom:1px solid #dbe3ef;vertical-align:top}th{background:#e7edf5}details{background:white;padding:18px;margin-top:20px;border:1px solid #dbe3ef;border-radius:10px}summary{cursor:pointer;font-weight:bold}details p{overflow-wrap:anywhere}@media(max-width:600px){main{padding:14px}td,th{padding:7px}}'
    (BASE/'report.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>문장 수정 오류 보완 결과</title><style>'+css+'</style><main>'+page+'</main></html>',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
