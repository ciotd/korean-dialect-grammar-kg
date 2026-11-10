"""Create an immutable cleaned KG, external audit, backup and offline comparison.

No Qwen, credentials, external source reads, or live Neo4j mutations.
"""
import argparse
import collections
import copy
import datetime as dt
import hashlib
import html
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'local/python')]
from kg_pipeline.separated_graph import separate, restore, compact_payload, compact_reference, BOILERPLATE, canonical, digest
from kg_pipeline.integrated import IntegratedReader, retrieve_packet, analysis_contract
from kg_pipeline.io import dumps

SOURCE = ROOT/'knowledge/authored/semantic_grammar_20261106_integrated_r2/private/graph.json'
CASES = ROOT/'experiments/analyses/kg_understanding_audit_20261107/private/20261107T031711223906Z/reader_contract_cases.jsonl'
HOME = ROOT/'experiments/analyses/kg_storage_separation_20261107'


def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p, v):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def file_hash(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def check(ok, message):
    if not ok: raise AssertionError(message)


def semantic_query(query):
    q = copy.deepcopy(query)
    q['legacy_candidates'] = [compact_reference(x) for x in q['legacy_candidates']]
    return q


def semantic_payload(payload):
    p = compact_payload(payload)
    if p.get('limitations') == BOILERPLATE['limitations']: p['limitations'] = ''
    for form in p.get('forms_annotated', []): form.pop('source', None)
    return p


def verify_structural(old, new, audit):
    a, b = IntegratedReader(old), IntegratedReader(new)
    check(restore(new, audit) == old, 'Restoration mismatch')
    check(set(a.rules) == set(b.rules), 'Rule identity changed')
    for rid in a.rules:
        check(a.rules[rid]['branches'] == b.rules[rid]['branches'], 'Branch/path changed: '+rid)
        check(a.rules[rid]['family'] == b.rules[rid]['family'], 'Family changed: '+rid)
    check(a.values == b.values, 'Feature values changed')
    check([n['id'] for n in a.legacy] == [n['id'] for n in b.legacy], 'Legacy knowledge dropped')
    check(old['feature_schema'] == new['feature_schema'], 'Feature schema changed')
    # All non-documentary relationships, including unexecuted designs, survive.
    ids = set(b.nodes)
    old_edges = {e['id']: (e['source'], e['relation'], e['target']) for e in old['edges'] if e['source'] in ids and e['target'] in ids}
    new_edges = {e['id']: (e['source'], e['relation'], e['target']) for e in new['edges']}
    check(old_edges == new_edges, 'Non-documentary relationship changed')
    # Deep equality of every unaffected field, not just fields consumed by today's reader.
    permitted = collections.defaultdict(set)
    for change in audit['changes']: permitted[change['id']].add(change['path'])
    def diff(left, right, path=''):
        if isinstance(left, dict) and isinstance(right, dict):
            result=[]
            for k in left.keys() | right.keys():
                p=path+'/'+k
                result.extend([p] if k not in left or k not in right else diff(left[k],right[k],p))
            return result
        if isinstance(left, list) and isinstance(right, list) and len(left)==len(right):
            return [p for i,(x,y) in enumerate(zip(left,right)) for p in diff(x,y,path+'/'+str(i))]
        return [] if left==right else [path]
    for family in ('nodes','edges'):
        previous={x['id']:x for x in old[family]}
        for item in new[family]:
            changes=set(diff(previous[item['id']],item))
            check(changes <= permitted[item['id']], 'Unlisted field edit: '+item['id']+str(changes-permitted[item['id']]))
    return a,b,{'restores_entire_source':True,'all_retained_fields_audited':True,
                'semantic_edge_ids_endpoints_types_unchanged':True,'rule_conditions_and_paths_unchanged':True,
                'rules':len(a.rules),'branches':sum(len(r['branches']) for r in a.rules.values()),
                'legacy_items':len(a.legacy),'retained_relationships':len(new_edges)}


def replay_contracts(a,b):
    rows=[]
    for line in CASES.read_text(encoding='utf8').splitlines():
        c=json.loads(line); features=c['features']; kind=features['unit_kind']
        required=a.rules[c['rule_id']]['node']['properties'].get('required_relations',[])
        unit={'id':c['case_id'],'kind':kind,'span':[0,1],'text':'검','morphs':[],
              'relations':{k:['synthetic_target'] for k in required if k!=c.get('missing_relation')}}
        before=a.query(unit,features);after=b.query(unit,features)
        equal=semantic_query(before)==semantic_query(after)
        check(equal,'Contract replay changed: '+c['case_id'])
        rows.append({'case_id':c['case_id'],'rule_id':c['rule_id'],'mode':c['mode'],'identical':equal})
    return rows


def replay_records(a,b,out):
    rows=[];example=None;input_hashes={}
    for path in sorted((ROOT/'experiments/runs').glob('*_integrated_grammar_*/private/records/*/bound_analysis.json')):
        if not (path.parent/'input.json').is_file(): continue
        units=read(path);inp=read(path.parent/'input.json');text=inp['text']
        check(analysis_contract(a,units)==analysis_contract(b,units),'Analysis schema changed')
        old_packets=[];new_packets=[]
        for u in units:
            old=a.query(u,u['features']);new=b.query(u,u['features'])
            check(semantic_query(old)==semantic_query(new),'Query changed: '+str(path)+' '+u['id'])
            for x,y in zip(old['eligible'],new['eligible']):
                p=a.payload(u,x);q=b.payload(u,y)
                check(semantic_payload(p)==semantic_payload(q),'Linguistic payload changed: '+x['rule_id'])
                old_packets.append(p);new_packets.append(q)
                if example is None and inp['id']=='DEV012': example={'input':text,'before':p,'after':q}
        before,bt=retrieve_packet(a,text,units);after,at=retrieve_packet(b,text,units)
        before_inf,_=retrieve_packet(a,text,units,char_budget=10**9)
        after_inf,_=retrieve_packet(b,text,units,char_budget=10**9)
        check([semantic_payload(p) for p in before_inf['verified_scope_knowledge']]==[semantic_payload(p) for p in after_inf['verified_scope_knowledge']], 'Unbounded information changed')
        old_ids=[(x['unit_id'],x['rule_id']) for x in before['verified_scope_knowledge']]
        new_ids=[(x['unit_id'],x['rule_id']) for x in after['verified_scope_knowledge']]
        old_refs=[(x['unit_id'],x['source_id']) for x in before['related_unprocessed_sources']]
        new_refs=[(x['unit_id'],x['source_id']) for x in after['related_unprocessed_sources']]
        label=path.parents[3].name+'/'+inp['id']
        row={'record':label,'input_id':inp['id'],'input_text_sha256':digest(text),'units':len(units),
             'query_identical':True,'unbounded_linguistic_payload_identical':True,
             'before_action_count':len(old_ids),'after_action_count':len(new_ids),
             'before_reference_count':len(old_refs),'after_reference_count':len(new_refs),
             'fixed_budget_action_ids_same':old_ids==new_ids,'fixed_budget_reference_ids_same':old_refs==new_refs,
             'before_packet_characters':len(dumps(before)),'after_packet_characters':len(dumps(after)),
             'before_unbounded_characters':len(dumps(before_inf)),'after_unbounded_characters':len(dumps(after_inf)),
             'before_action_characters':sum(len(dumps(x)) for x in old_packets),
             'after_action_characters':sum(len(dumps(x)) for x in new_packets)}
        rows.append(row);input_hashes[str(path.relative_to(ROOT))]=file_hash(path)
        input_hashes[str((path.parent/'input.json').relative_to(ROOT))]=file_hash(path.parent/'input.json')
        save(out/'replays'/path.parents[3].name/inp['id']/'comparison.json',{'summary':row,'input':inp,'before':before,'after':after})
        if len(rows)%10==0: print(json.dumps({'replayed_records':len(rows)},ensure_ascii=False),flush=True)
    missing=[str(p.parent.relative_to(ROOT)) for p in sorted((ROOT/'experiments/runs').glob('*_integrated_grammar_*/private/records/*/input.json'))
             if not (p.parent/'bound_analysis.json').is_file()]
    return rows,example,input_hashes,missing


def report(summary, example, destination):
    esc=lambda s:html.escape(str(s))
    stats=summary['statistics'];r=summary['replay'];checks=summary['structural']
    def tr(label,x,y,note): return '<tr>'+''.join('<td>'+esc(v)+'</td>' for v in (label,x,y,note))+'</tr>'
    comparison=''.join([
        tr('현재 통합 KG의 노드',stats['before_nodes'],stats['after_nodes'],'줄어든 항목은 별도 기록 파일에서 보존'),
        tr('현재 통합 KG의 연결',stats['before_edges'],stats['after_edges'],'문법 지식끼리의 연결은 모두 유지'),
        tr('문법 규칙',checks['rules'],checks['rules'],'새 규칙 추가·삭제 없음'),
        tr('조건 분기',checks['branches'],checks['branches'],'조건값·분기 경로가 모두 동일'),
        tr('정제 전 문헌 지식 항목',checks['legacy_items'],checks['legacy_items'],'검색에서 숨기지 않음'),
        tr('출처·검토 전용 노드',stats['moved_nodes'],0,'별도 보관 파일에 같은 ID로 이동'),
        tr('실행 그래프 파일 크기(바이트)',stats['before_canonical_bytes'],stats['after_canonical_bytes'],'같은 JSON 저장 방식으로 비교; 토큰 수 아님')])
    e=''
    if example:
        p,q=example['before'],example['after']
        e='<p class="example">입력: '+esc(example['input'])+'</p><p>수정 대상: <b>'+esc(q['source_text'])+'</b>. 이 위치에 전달되는 지식은 다음과 같습니다. 새 방언 출력은 이번에 생성하지 않았습니다.</p>'
        e+='<table><tr><th>내용</th><th>정리 전</th><th>정리 후</th></tr>'
        labels={'lexical_meaning':'단어의 뜻','argument_roles':'누가 누구에게 무엇을 하는지',
                'tense':'시제(과거·현재 등)','past_form':'과거를 나타내는 형태','polarity':'긍정·부정',
                'addressee_level':'상대방에게 쓰는 말높임','question_kind':'질문의 종류',
                'subject_honorific':'주어에 대한 높임','clause_embedding':'안긴절 구조'}
        for name,key in [('사용 방법','instruction'),('보존할 내용','preserve')]:
            val=lambda v:' · '.join(labels.get(x,x) for x in v) if isinstance(v,list) else str(v)
            e+='<tr><td>'+name+'</td><td>'+esc(val(p[key]))+'</td><td>'+esc(val(q[key]))+'</td></tr>'
        e+='<tr><td>가능한 어미</td><td>'+esc(str(p['forms'][0]['form']))+'</td><td>'+esc(str(q['forms'][0]['form']))+'</td></tr>'
        e+='<tr><td>결합 방법</td><td>'+esc(p['forms'][0].get('composition',p['instruction']))+'</td><td>'+esc(q['forms'][0].get('composition',q['instruction']))+'</td></tr>'
        e+='<tr><td>출처 안내</td><td>'+str(len(p.get('sources',[])))+'개 출처의 문헌 ID·쪽수 전달</td><td>생성 모델에 보내지 않음. 별도 기록에서 규칙 ID로 확인</td></tr></table>'
    body=f'''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>KG 정리 전후 비교</title>
<style>body{{font-family:Malgun Gothic,Arial,sans-serif;max-width:1050px;margin:40px auto;padding:0 24px;background:#f5f7fa;color:#18273d;line-height:1.8}}h1{{font-size:30px}}h2{{margin-top:0;font-size:22px}}section{{background:white;border:1px solid #dce3eb;border-radius:12px;padding:26px;margin:22px 0}}table{{width:100%;border-collapse:collapse;font-size:14px}}th,td{{border:1px solid #dce3eb;padding:10px;text-align:left;vertical-align:top;overflow-wrap:anywhere}}th{{background:#edf3fa}}.lead{{font-size:20px}}.note{{color:#53627b}}.example{{background:#eaf5f3;padding:12px}}.two{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}.box{{padding:18px;background:#edf3fa;border-radius:8px}}@media(max-width:700px){{.two{{grid-template-columns:1fr}}table{{font-size:12px}}}}@media print{{body{{margin:0;background:white;font-size:11pt}}section{{break-inside:avoid;box-shadow:none}}}}</style>
<h1>문법 지식은 그대로, 출처와 작업 기록은 따로</h1><p class="lead">실제 KG 파일과 조회 코드를 정리했습니다. 같은 분석값을 넣었을 때 같은 문법 규칙을 찾는지 확인했습니다.</p>
<p class="note">2026년 11월 7일 · 구조 정리 및 기존 기록 재생 검사 · 새 Qwen 호출 0회</p>
<section><h2>1. 무엇을 바꿨나요?</h2><p>기존에는 문법 지식 옆에 문헌의 긴 발췌문, 쪽수, 검토 상태, 반복 설명이 함께 들어 있었습니다. 이제 생성에 사용할 지식과 연구자가 확인할 기록을 두 파일로 나눴습니다. 문헌과 검토 기록을 버린 것이 아닙니다.</p><div class="two"><div class="box"><b>문장을 바꾸는 데 쓰는 실행 그래프</b><br>대상 · 문법 조건 · 가능한 표현 · 보존할 의미 · 문법 관계 · 실제 제한</div><div class="box"><b>따로 열어 보는 출처·검토 기록</b><br>문헌 · 발췌문 · 쪽수 · 검토 기록 · 이전 속성<br>규칙/지식 ID와 버전으로 다시 연결</div></div><p>이전 원본 1,625개 노드·6,167개 관계와, 확장된 현재 통합본을 혼동하면 안 됩니다. 이번 정리 대상은 <b>{stats['before_nodes']:,}개 노드·{stats['before_edges']:,}개 관계의 통합본</b>입니다. 과거 파일은 덮어쓰지 않았습니다.</p></section>
<section><h2>2. 무엇이 줄었고, 무엇이 그대로인가요?</h2><table><tr><th>항목</th><th>전</th><th>후</th><th>뜻</th></tr>{comparison}</table><p>개별 속성 {stats['changed_fields']:,}곳에서 출처·관리 정보를 옮기거나 정확히 같은 설명의 중복을 제거했습니다. 모든 수정 위치는 변경 목록에 남았습니다.</p><p><b>일괄 삭제하지 않은 부분:</b> 설명 안에 적용 금지, 의미 차이, 지역별 사용 차이가 섞여 있으면 그대로 남겼습니다. 예를 들어 ‘보조용언과 일반 동사를 구별한다’는 내용은 사족이 아니라 문법 조건입니다. 판단하기 어려운 설명까지 이번에 임의로 줄이지 않았습니다.</p></section>
<section><h2>3. 실제 입력에서는 무엇이 달라지나요?</h2>{e}<p>규칙을 고르는 기준과 수정 지시는 그대로입니다. 생성 모델에 보내던 문헌 ID·쪽수와, 사용 지시를 그대로 반복하던 결합 설명을 제거했습니다. 오래된 실행 기록을 다시 열면 당시 전달 내용도 그대로 확인할 수 있습니다.</p></section>
<section><h2>4. 빠진 지식이 없는지 어떻게 확인했나요?</h2><table><tr><th>검사</th><th>결과</th><th>무엇을 확인한 것인가</th></tr>
<tr><td>원본 복원</td><td>일치</td><td>새 그래프와 별도 기록을 합치면 기존 JSON 전체가 정확히 복원됨. 원본 파일의 바이트 사본도 보관</td></tr>
<tr><td>조건·관계 검사</td><td>일치</td><td>규칙 {checks['rules']}개, 분기 {checks['branches']}개, 남긴 모든 관계의 ID·종류·연결 대상 동일</td></tr>
<tr><td>기존 조건 검사 재생</td><td>{r['contract_cases']}건 일치</td><td>적용·비적용·미확정·필요 관계 누락의 판정이 전후 동일</td></tr>
<tr><td>실제 저장 분석 재생</td><td>{r['records']}개 기록 / {r['units']}개 분석 위치 일치</td><td>분석을 새로 만들지 않고 같은 분석을 넣어 조회 결과와 문법 전달 내용 비교</td></tr>
<tr><td>제한 길이 안에서 전달</td><td>규칙 묶음 변화 {r['fixed_budget_action_changes']}건 / 참고 항목 변화 {r['fixed_budget_reference_changes']}건</td><td>같은 길이 제한이어도 설명이 짧아져 더 들어갈 수 있음. 조회 조건 변경과 구별해 기록</td></tr></table>
<p>재생 기록에는 같은 문장을 다시 실행한 기록이 포함됩니다. 고유 입력 문장 해시는 {r['unique_texts']}개입니다. 기존 입력 기록 중 {len(r['missing_analysis_records'])}개는 분석 결과가 저장되어 있지 않아 재생하지 못했습니다. 이 기록도 제외 이유와 함께 남겼습니다. 이것은 번역 정확도 평가가 아니라 <b>정리 과정에서 작동이 바뀌지 않았는지 확인한 검사</b>입니다.</p>
<p>길이 제한이 없을 때 전달문 전체의 합계: 정리 전 {r['before_unbounded_characters']:,}자 → 정리 후 {r['after_unbounded_characters']:,}자. 문자 수이며 실제 모델 토큰이나 지연시간을 측정한 값은 아닙니다.</p></section>
<section><h2>5. 완료한 일과 다음 일</h2><p><b>완료:</b> 백업, 새 KG 파일, 출처·검토 분리, 조회기 연결, 전체 복원 검사, 기존 조건 및 실제 분석 기록 재생을 마쳤습니다. 통합 실행기에서 KG 경로를 따로 지정하지 않으면 새 저장 버전을 읽습니다. 이전 버전으로 비교하려면 해당 경로를 명시하면 됩니다. 생성 모델은 출처 기록 파일을 읽지 않습니다. 필요한 경우 연구자가 ID로 따로 조회합니다.</p><p><b>이번에 하지 않은 일:</b> 문법의 옳고 그름을 새로 판정하거나 규칙 범위를 확장하지 않았고, Qwen을 다시 호출하지 않았습니다. Neo4j에 남아 있는 과거 데이터도 덮어쓰지 않았습니다. 따라서 방언 자연스러움이나 생성 속도가 개선됐다고 말할 수 없습니다.</p><p><b>다음:</b> 이 새 저장 형식을 기준으로 전체 지식의 의미·조건 검토를 이어갑니다. 출처가 필요할 때만 별도 기록을 열면 됩니다. 이후 생성 비교에서는 KG 버전과 전달 길이를 고정하여 정리 효과와 문법 수정 효과를 구분합니다. 조건·조회가 달라지는 문제가 발견되면 새 버전을 보류하고 백업 버전을 사용합니다.</p><p><b>검토 역할:</b> 이번 작업은 자동 검증과 리드의 코드 점검으로 확인했습니다. 외부 Claude·Codex 검토자에게 새 자료를 보내거나 독립 검토를 받았다고 주장하지 않습니다. 사용자에게 새 문법 판단이나 추가 승인을 요청할 항목은 없습니다.</p></section>
<p class="note">실행 식별자: {esc(summary['run_id'])} · 전체 변경 목록과 입력별 비교는 같은 분석 폴더의 비공개 기록에 보존됩니다.</p></html>'''
    destination.write_text(body,encoding='utf8')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,default=SOURCE);args=parser.parse_args()
    stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out=HOME/'private'/stamp;out.mkdir(parents=True,exist_ok=False)
    version='semantic_grammar_20261107_separated_'+stamp
    bundle=ROOT/'knowledge/authored/semantic_grammar_20261107_separated_r1/private'/stamp
    bundle.mkdir(parents=True,exist_ok=False)
    source=args.source.resolve();before_hash=file_hash(source)
    shutil.copy2(source,out/'before_graph.json')
    code_paths=['src/kg_pipeline/separated_graph.py','src/kg_pipeline/integrated.py','tools/separate_kg_storage.py','tools/inspect_separated_kg.py','tools/run_integrated_grammar.py','tests/test_separated_graph.py','tests/test_integrated_runner.py']
    for rel in code_paths:
        p=out/'code_snapshot'/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/rel,p)
    try:
        old=read(source);new,audit=separate(old,version)
        save(bundle/'graph.json',new);save(bundle/'audit.json',audit)
        a,b,structural=verify_structural(old,new,audit)
        print('Structure and exact restoration verified',flush=True)
        contracts=replay_contracts(a,b);save(out/'contract_replay.json',contracts)
        print('Contract replay complete: '+str(len(contracts)),flush=True)
        records,example,inputs,missing=replay_records(a,b,out)
        check(bool(records),'No saved analysis records found')
        save(out/'record_replay.json',records);save(out/'example.json',example)
        check(file_hash(source)==before_hash==file_hash(out/'before_graph.json'),'Source or backup changed')
        stats={'before_nodes':len(old['nodes']),'after_nodes':len(new['nodes']),
               'before_edges':len(old['edges']),'after_edges':len(new['edges']),
               'moved_nodes':len(audit['documentary_nodes']),'moved_edges':len(audit['documentary_edges']),
               'changed_fields':len(audit['changes']),'before_canonical_bytes':len(canonical(old)),
               'after_canonical_bytes':len(canonical(new)),
               'before_node_types':dict(collections.Counter(n['type'] for n in old['nodes'])),
               'after_node_types':dict(collections.Counter(n['type'] for n in new['nodes'])),
               'change_reasons':dict(collections.Counter(x['reason'] for x in audit['changes']))}
        replay={'contract_cases':len(contracts),'records':len(records),'units':sum(x['units'] for x in records),
                'missing_analysis_records':missing,
                'unique_texts':len({x['input_text_sha256'] for x in records}),
                'fixed_budget_action_changes':sum(not x['fixed_budget_action_ids_same'] for x in records),
                'fixed_budget_reference_changes':sum(not x['fixed_budget_reference_ids_same'] for x in records),
                **{key:sum(r[key] for r in records) for key in ('before_packet_characters','after_packet_characters','before_unbounded_characters','after_unbounded_characters','before_action_characters','after_action_characters')}}
        summary={'run_id':stamp,'status':'passed_structural_and_offline_replay','source':str(source.relative_to(ROOT)),
                 'source_file_sha256':before_hash,'bundle':str(bundle.relative_to(ROOT)),
                 'statistics':stats,'structural':structural,'replay':replay,'qwen_calls':0,
                 'naturalness_evaluated':False,'live_neo4j_changed':False,'independent_review':False}
        save(out/'summary.json',summary)
        manifest={**summary,'graph_sha256':file_hash(bundle/'graph.json'),'audit_sha256':file_hash(bundle/'audit.json'),
                  'code_sha256':{p:file_hash(ROOT/p) for p in code_paths},'replayed_input_sha256':inputs,
                  'backup':str((out/'before_graph.json').relative_to(ROOT)),
                  'activation':'integrated runner defaults to latest separated storage; explicit --graph preserves historical comparison'}
        save(bundle/'manifest.json',manifest)
        report(summary,example,out/'report.html')
        # Human-facing latest pointers; immutable run/bundle directories remain intact.
        save(HOME/'latest.json',{'run_id':stamp,'analysis':str(out.relative_to(ROOT)),'bundle':str(bundle.relative_to(ROOT))})
        shutil.copy2(out/'report.html',HOME/'report.html')
        save(ROOT/'knowledge/authored/semantic_grammar_20261107_separated_r1/latest.json',
             {'version':version,'graph':str((bundle/'graph.json').relative_to(ROOT)),
              'audit':str((bundle/'audit.json').relative_to(ROOT)),'manifest':str((bundle/'manifest.json').relative_to(ROOT)),
              'status':summary['status'],'translation_quality':'not_evaluated'})
        from research_management.work import WorkStore
        try:
            WorkStore(ROOT).task({'id':'kg_storage_separation_'+stamp,'title':'KG 실행 지식과 출처 기록 분리',
                'actor':'연구 리드 / 자동 검사','stage':'백업→분리→조회 재생','status':'completed',
                'done':4,'total':4,'unit':'단계','unit_key':stamp,
                'message':f'{len(records)}개 기존 기록 재생 일치. Qwen 호출 0회. 번역 품질 평가는 별도.'})
        except Exception as exc: save(out/'registration_error.json',{'type':type(exc).__name__,'message':str(exc)})
        print(json.dumps(summary,ensure_ascii=False),flush=True)
    except Exception as exc:
        save(out/'failure.json',{'error_type':type(exc).__name__,'message':str(exc),'source_sha256':before_hash})
        raise


if __name__=='__main__':main()
