"""Freeze KG inputs, inventory every ID, and exercise the existing reader offline.

No model calls, KG changes, semantic certification, or publication.
Every invocation creates a new private analysis directory.
"""
from pathlib import Path
import collections, datetime, hashlib, html, itertools, json, math, shutil, sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'local/python')]
from kg_pipeline.integrated import IntegratedReader

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p, x):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
def lines(p, rows):
    p.write_text(''.join(json.dumps(x, ensure_ascii=False)+'\n' for x in rows), encoding='utf8')
def read_lines(p): return [json.loads(l) for l in p.read_text(encoding='utf-8-sig').splitlines() if l]

stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
OUT = HERE/'private'/stamp
OUT.mkdir(parents=True, exist_ok=False)
paths = {
    'original_nodes': 'knowledge/authored/kg_v3_evidence_20261019_r2/graph/nodes.jsonl',
    'original_edges': 'knowledge/authored/kg_v3_evidence_20261019_r2/graph/edges.jsonl',
    'candidate': 'knowledge/authored/semantic_grammar_20261106_integrated_r2/private/graph.json',
    'reader': 'src/kg_pipeline/integrated.py',
    'runner': 'tools/run_integrated_grammar.py',
    'schema': 'knowledge/authored/kg_v3_evidence_20261019_r2/schema/schema.json',
    'layers': 'knowledge/authored/kg_v3_evidence_20261019_r2/schema/layers.json',
    'builder': str(Path(__file__).relative_to(ROOT)).replace('\\', '/'),
}
sources = {}
for key, rel in paths.items():
    src = ROOT/rel; dst = OUT/'snapshot'/rel
    dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, dst)
    assert sha(src) == sha(dst)
    sources[key] = {'path': rel, 'sha256': sha(src), 'bytes': src.stat().st_size}
old = {'nodes': read_lines(OUT/'snapshot'/paths['original_nodes']), 'edges': read_lines(OUT/'snapshot'/paths['original_edges'])}
new = json.loads((OUT/'snapshot'/paths['candidate']).read_text(encoding='utf8'))
reader = IntegratedReader(new)
assert sha(ROOT/paths['reader']) == sources['reader']['sha256']
N = {n['id']: n for n in new['nodes']}
node_ledger, edge_ledger, stats = [], [], {}

def obligation(t):
    if t in ('SourceDocument','SourceSpan','Evidence'): return 'source_identity_location_and_interpretation'
    if t in ('SemanticRule','ApplicabilityBranch','Condition','FeatureValue','Realization','ProcessingScope','GrammarConstruction'): return 'condition_contract_and_sentence_pipeline'
    if t == 'SourceAtom': return 'source_content_refinement_and_search_reachability'
    if t in ('AnalysisConcept','Construction','GrammarFeature','AggregateInterface','TechnicalResponsibility'): return 'design_intent_to_actual_implementation_mapping'
    return 'role_specific_structure_and_content_review'

for version, g in [('original', old), ('candidate', new)]:
    node_ids = [n['id'] for n in g['nodes']]; edge_ids = [e['id'] for e in g['edges']]
    ids = set(node_ids); degrees = collections.Counter()
    for e in g['edges']: degrees.update((e['source'], e['target']))
    duplicate_nodes = [i for i,c in collections.Counter(node_ids).items() if c>1]
    duplicate_edges = [i for i,c in collections.Counter(edge_ids).items() if c>1]
    dangling = [e['id'] for e in g['edges'] if e['source'] not in ids or e['target'] not in ids]
    for n in g['nodes']:
        p=n.get('properties', {})
        node_ledger.append({'version':version,'id':n['id'],'type':n['type'],
            'title':n.get('title',p.get('title',n['id'])), 'degree':degrees[n['id']],
            'structure': 'id_present_unique' if n['id'] not in duplicate_nodes else 'duplicate_id',
            'isolated':degrees[n['id']]==0, 'review_obligation':obligation(n['type']),
            'stored_runtime_active':p.get('runtime_active'),
            'stored_semantic_review_status':p.get('semantic_review_status'),
            'semantic_review_this_audit':'not_performed', 'sentence_pipeline_this_audit':'not_performed',
            'properties_present':sorted(p)})
    for e in g['edges']:
        edge_ledger.append({'version':version,'id':e['id'],'source':e['source'],'relation':e['relation'],
            'target':e['target'],'structure':'dangling' if e['id'] in dangling else 'duplicate_id' if e['id'] in duplicate_edges else 'id_unique_endpoints_present',
            'meaning_review_this_audit':'not_performed','runtime_traversal_this_audit':'not_measured'})
    stats[version]={'nodes':len(node_ids),'edges':len(edge_ids),'node_types':dict(collections.Counter(n['type'] for n in g['nodes'])),
        'edge_types':dict(collections.Counter(e['relation'] for e in g['edges'])),
        'duplicate_node_ids':duplicate_nodes,'duplicate_edge_ids':duplicate_edges,'dangling_edge_ids':dangling,
        'isolated_node_ids':sorted(ids-set(degrees))}

old_by_id={n['id']:n for n in old['nodes']}; new_edges={e['id']:e for e in new['edges']}
preservation={'missing_old_nodes':[i for i in old_by_id if i not in N],
 'changed_old_nodes':[i for i,n in old_by_id.items() if i in N and n!=N[i]],
 'missing_old_edges':[e['id'] for e in old['edges'] if e['id'] not in new_edges],
 'changed_old_edges':[e['id'] for e in old['edges'] if e['id'] in new_edges and e!=new_edges[e['id']]]}
lines(OUT/'node_ledger.jsonl',node_ledger);lines(OUT/'edge_ledger.jsonl',edge_ledger)

def flatten(obj, prefix=''):
    for k,v in obj.items():
        p=prefix+'.'+k if prefix else k
        yield p,v
        if isinstance(v,dict):yield from flatten(v,p)

dictionary=[]
for t in sorted({n['type'] for n in new['nodes']}):
    group=[n for n in new['nodes'] if n['type']==t]; fields={}
    for n in group:
        for key,value in flatten(n):
            row=fields.setdefault(key,{'path':key,'present':0,'null':0,'types':set(),'example_node':n['id'],'example':value})
            row['present']+=1;row['null']+=value is None;row['types'].add(type(value).__name__)
    dictionary.append({'node_type':t,'count':len(group),'fields':[{**r,'types':sorted(r['types'])} for r in fields.values()]})
dump(OUT/'property_dictionary.json',dictionary)

# Expected values below describe the stored logical contract, not linguistic truth.
# Synthetic relation targets exercise query presence checks only, not bind_analysis.
specs=[]; cases=[]
for rid,r in reader.rules.items():
    required=r['node']['properties'].get('required_relations',[])
    for b in r['branches']:
        cond=b['conditions']; keys=list(cond)
        specs.append({'rule_id':rid,'branch_id':b['id'],'conditions':cond,'required_relations':required,
            'syntactic_positive_combinations':math.prod(len(v) for v in cond.values()),
            'path_edge_ids':b['path_edge_ids'], 'natural_sentence_ids':[],
            'sentence_status':'not_generated','linguistic_feasibility':'not_reviewed'})
        all_features=[dict(zip(keys,values)) for values in itertools.product(*(cond[k] for k in keys))]
        base=all_features[0]
        variants=[('all_allowed_values',f,None,None) for f in all_features]
        for k in keys:
            other=next((v for v in sorted(reader.values[k]) if v not in cond[k]),'__OUTSIDE_DECLARED_VALUES__')
            variants.extend([('one_false',{**base,k:other},k,None),('one_unknown',{**base,k:None},k,None)])
        variants += [('missing_relation',base,None,role) for role in required]
        for mode,features,changed,missing_role in variants:
            relations={role:['SYNTHETIC_TARGET_'+role] for role in required if role!=missing_role}
            unit={'id':'CONTRACT_UNIT','kind':features['unit_kind'],'relations':relations}
            tr=reader.query(unit,features)
            target=next((x for category in ('eligible','unresolved','rejected') for x in tr[category] if x['rule_id']==rid),None)
            if target is None:
                expected='not_dispatched_for_unit_kind'
                passed=not any(features['unit_kind'] in z['conditions']['unit_kind'] for z in r['branches'])
                observed=expected
            else:
                branch_expected=[]
                for z in r['branches']:
                    unknown=any(features.get(k) is None or features.get(k)=='unknown' for k in z['conditions'])
                    false=any(features.get(k) is not None and features.get(k)!='unknown' and features.get(k) not in vs for k,vs in z['conditions'].items())
                    branch_expected.append('false' if false else 'unknown' if unknown else 'true')
                expected='eligible' if 'true' in branch_expected else 'unresolved' if 'unknown' in branch_expected else 'condition_mismatch'
                if expected=='eligible' and missing_role:expected='unresolved'
                observed=target['state'];passed=expected==observed and branch_expected==[z['state'] for z in target['branches']]
            cases.append({'case_id':f'LOGIC_{len(cases)+1:05d}','rule_id':rid,'target_branch_id':b['id'],
                'mode':mode,'features':features,'changed_feature':changed,'missing_relation':missing_role,
                'synthetic_relation_targets':True,'expected_contract_state':expected,'observed_state':observed,
                'matches_contract':passed,'other_eligible_rule_ids':[x['rule_id'] for x in tr['eligible'] if x['rule_id']!=rid],
                'target_branch_states':[] if target is None else [{'id':z['id'],'state':z['state']} for z in target['branches']]})
lines(OUT/'branch_specifications.jsonl',specs);lines(OUT/'reader_contract_cases.jsonl',cases)

summary={'analysis_id':stamp,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'baseline_checkpoint':'21315e436862d94ee54c147ccd5bf187c2ab6dca','sources':sources,
    'counts':stats,'original_preservation':preservation,
    'ledger_rows':{'nodes':len(node_ledger),'edges':len(edge_ledger)},
    'rules':len(reader.rules),'branches':len(specs),'syntactic_positive_combinations':sum(s['syntactic_positive_combinations'] for s in specs),
    'effective_condition_slots':sum(len(s['conditions']) for s in specs),
    'reader_contract_cases':len(cases),'reader_contract_matches':sum(c['matches_contract'] for c in cases),
    'reader_contract_modes':dict(collections.Counter(c['mode'] for c in cases)),
    'routing_cases_not_branch_evaluation':sum(c['observed_state']=='not_dispatched_for_unit_kind' for c in cases),
    'new_natural_sentences':0,'new_model_calls':0,'new_source_semantic_reviews':0,
    'scope':'all IDs inventoried; structure and stored reader contract checked; no semantic or sentence generation certification'}
dump(OUT/'summary.json',summary)

E=html.escape
def display(v):
    if v is None:return '미기록 / null'
    if isinstance(v,bool):return 'true' if v else 'false'
    if isinstance(v,list):return ' · '.join(display(x) for x in v) if v else '빈 목록'
    if isinstance(v,dict):return ' / '.join(str(k)+': '+display(x) for k,x in v.items())
    return str(v)
def table(headers,rows):return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+E(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+E(display(v))+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'
def detail(title,body):return '<details><summary>'+E(title)+'</summary>'+body+'</details>'
content=[]
content.append('''<h1>현재 KG를 이해하고 전수 검사를 시작하기</h1><p class="lead">먼저 우리가 무엇을 설계했고, 무엇을 지식으로 저장했으며, 무엇이 실제로 실행되는지 구분합니다. 이 설명과 대장은 2026년 11월 7일 저장 파일을 동결해 만들었습니다.</p><p>목표는 표준어 문장의 뜻·시제·부정·높임을 유지하면서 근거에 맞는 자연스러운 방언 문장을 생성하는 것입니다. KG는 필요한 지식을 고르는 방법이며, 최종 문장 작성자는 Qwen입니다.</p><nav><a href="#foundation">① 표준어 분석 틀</a><a href="#storage">② 지식과 속성</a><a href="#actual">③ 실제 요청 용법</a><a href="#audit">④ 전수 검사</a><a href="#freeze">⑤ 실험 동결</a><a href="#appendix">전체 목록</a></nav>''')
content.append('''<h2 id="foundation">1. 최초 문법 틀은 완성된 분석기가 아니라 공통 분석 설계입니다</h2><p>공통 척추는 문법 정보를 찾기 위한 설계 탐색 뷰입니다. 실제 루트의 설명에도 ‘언어학적 루트 또는 실행 엔진이 아니다’라고 적혀 있습니다. 이 틀은 표준어와 방언을 비교할 때 어간·절·시제·높임 등을 같은 항목으로 다루려는 설계입니다. 외부의 표준어 문법 전체를 이미 검증해 수록했다고 말할 수는 없습니다.</p><p>공통 문법 항목은 분석 개념 48개, 구성 54개, 특징 23개, 집계 인터페이스 11개로 총 136개입니다. 기술 책임 54개와 방언 문헌 항목 721개는 별도입니다. 같은 항목이 여러 분야에 연결될 수 있으므로 분야별 합계를 고유 항목 수로 쓰면 안 됩니다.</p>''')
content.append(table(['분야','무엇을 구별하려는가'],[(n['title'],n['properties']['original_spec']['functions']) for n in old['nodes'] if n['type']=='Module']))
stem=N['G_VERB_STEM']['properties']['original_spec']
content.append('<h3>실제 설계 한 개를 읽어보기: 표제어와 활용 어간의 연결</h3><p>예를 들어 문장에 나타난 활용형이 어떤 기본 단어의 어간인지 연결하려는 항목입니다. 아래 내용은 실제 G_VERB_STEM에 저장된 값입니다. recover_stem이라는 이름이 적혀 있어도 그 이름의 동작이 자동 실행된다는 뜻은 아닙니다.</p>')
labels={'input':'무엇을 받는가','action':'어떤 처리를 하도록 설계했는가','match':'무엇을 확인해야 하는가','block':'어떤 처리를 금지하는가','output':'무엇을 만들도록 설계했는가','preserve':'무엇을 보존해야 하는가','on_unknown':'판단할 수 없으면 어떻게 하는가','status':'실제 저장된 상태','runtime_active':'이 설계 항목의 실행 활성 표지','scope_profile':'주장할 수 있는 범위'}
content.append(table(['읽는 질문','실제 값'],[(label,stem.get(k)) for k,label in labels.items()]))
content.append('''<p>이 항목의 상태는 design_blueprint이고 runtime_active는 false입니다. 현재 코드에 관련 분석 기능이 있을 수는 있지만, 그 사실과 이 설계 노드가 실행 경로에 연결됐다는 것은 별도입니다. 코드 위치·검사·실제 실행을 대응시켜야 합니다.</p><h2 id="storage">2. 한 KG 안에 서로 다른 종류의 정보가 들어 있습니다</h2><p>원본 1,625노드·6,167관계에는 문헌 내용, 출처 위치, 공통 문법 설계, 관리 정보가 함께 있습니다. 최신 통합 후보는 이 원본을 포함하고 실행 조건을 추가한 2,320노드·7,476관계입니다. ‘노드 수’는 ‘변환 규칙 수’가 아닙니다.</p>''')
content.append(table(['정보의 종류','실제 보관 내용','읽을 때의 주의'],[
 ('문헌 항목 SourceAtom 721개','문헌에서 다룬 내용과 원래 명세, 출처 연결','검색됐다고 적용 가능한 규칙이 되는 것은 아님'),
 ('문헌 위치 SourceSpan 655개·문헌 SourceDocument 7개','문헌·쪽·발췌와 위치','발췌 존재와 그 해석의 타당성은 별도'),
 ('공통 문법 설계 136개','입력·처리·조건·금지·보존·미확정 처리','설계 완료와 실행 구현은 별도'),
 ('실행 용법 SemanticRule 56개','입력 단위, 조건 분기, 필요한 관계, 표현, 근거, 한계','조건 적합은 독립 품질 인증이 아님'),
 ('문장별 분석 기록','원문 위치, 형태소, 특징값, 절·단위 관계','영구 KG와 다른 실행 기록')]))
content.append('''<div class="flow"><span>문헌과 원문 위치</span><b>→</b><span>해석한 용법</span><b>→</b><span>적용 조건과 표현</span><b>↕</b><span>입력 문장 분석값</span><b>→</b><span>전달할 지식</span><b>→</b><span>Qwen의 최종 문장</span></div><p>원본 설계의 연결은 상호참조일 수 있고, 실행 후보의 연결은 실제 조건을 읽는 경로일 수 있습니다. 연결선이 있다는 이유만으로 두 항목을 차례로 실행하거나 의미를 상속하지 않습니다.</p>''')
rid='INT_LEAD_REQUEST_JU_AUX';rp=N[rid]['properties'];sp=next(s for s in specs if s['rule_id']==rid)
content.append('<h2 id="actual">3. 부탁 표현 한 개로 실제 연결을 읽습니다</h2><p>“창문 좀 닫아 주세요.”를 생각해 보세요. 앞 행동인 닫다와 보조 주다의 연결, 부탁이라는 기능, 높임을 함께 확인해야 합니다. 아래는 이 용법의 실제 저장 조건이며 이 예문의 분석·생성이 지금 성공했다는 보고는 아닙니다.</p>')
translations={'lemma':'어간·기본형','source_form':'입력 형태','speech_act':'문장 기능','addressee_level':'듣는 사람에 대한 높임','auxiliary_kind':'보조용언의 기능','unit_kind':'조회 대상 단위'}
content.append(table(['확인하는 항목','허용된 값'],[(translations.get(k,k)+' ('+k+')',v) for k,v in sp['conditions'].items()]))
content.append(table(['지식의 내용','실제 저장 값'],[('용법 이름',rp['title']),('필요한 입력 관계',rp['required_relations']),('지시와 해석',rp['instruction']),('보존',rp['preserve']),('상태',rp['status']),('한계',rp['limitations'])]))
content.append('''<p>코드는 같은 입력 단위에서 조건을 모두 확인합니다. 하나라도 맞지 않으면 그 분기는 거부하며, 불일치는 없지만 필요한 값이 없으면 미확정입니다. 여러 분기 중 하나가 맞으면 용법 후보가 될 수 있습니다. 필요한 본용언·보조용언 관계가 없으면 조건이 맞아도 미확정으로 남습니다.</p><p>이 용법의 후보는 주이소이지만 원문의 주세요 유지도 가능한 선택지로 기록돼 있습니다. 두 표현을 높임의 완전한 일대일 치환이라고 저장한 것은 아닙니다. 예문에서 주이소가 나왔는지만 채점하면 이 의도를 검사하지 못합니다.</p><p>실행 순서는 Kiwi 관찰→코드의 단위 구성→Qwen의 기능·관계 판단→코드의 연결 검사와 KG 조회→전달 내용 구성→Qwen 전체 문장 생성입니다. Qwen 분석이 틀리면 올바른 규칙도 조회되지 않을 수 있습니다. 분석값을 직접 주입한 조회 검사는 이 앞단을 검사하지 않습니다.</p>''')
content.append('<h2 id="audit">4. 지금 실제로 검사한 것과 다음에 검사할 것</h2>')
content.append(table(['항목','이번 결과','아직 하지 않은 것'],[
 ('원본과 후보의 전 항목 대장',f'노드 {len(node_ledger):,}행·관계 {len(edge_ledger):,}행. 버전 간 중복은 별도 행','의미 타당성 전수 판정'),
 ('ID·끝점 무결성',display({k:{z:v[z] for z in ['duplicate_node_ids','duplicate_edge_ids','dangling_edge_ids','isolated_node_ids']} for k,v in stats.items()}),'고립 항목의 의미상 필요 여부 판단'),
 ('실행 분기 명세',f'{len(reader.rules)}용법·{len(specs)}분기·합성 양성 조합 {summary["syntactic_positive_combinations"]}개','각 조합이 자연어로 가능한지 검토'),
 ('실제 조회 코드의 계약 검사',f'{len(cases)}건 중 {summary["reader_contract_matches"]}건 저장 논리와 일치','문헌 해석의 옳음·Kiwi/Qwen·자연스러움'),
 ('새 문장 생성과 전체 실행','0건·새 모델 호출 0회','모든 목표에 예문 연결 및 단계별 실행')]))
content.append('''<p>이 검사는 전수 검증의 출발점입니다. 각 노드와 관계가 대장에 있다는 것을 ‘전부 검증 완료’로 표현하지 않습니다. 직접 특징값을 넣은 합성 검사는 문법적으로 자연스러운 문장 수가 아닙니다. 관계 대상도 조회기의 존재 검사를 위한 합성 값이므로 문장 관계 해석을 검증하지 않습니다.</p><p>다음 예문 작업은 각 용법의 적용·비적용·모호 사례를 만들고, 아직 연결되지 않은 문헌·설계 항목도 누락 없이 추적합니다. 모든 자연어 예문은 실제 전체 파이프라인에 넣고, 첫 실패 위치와 이후 미수행 단계를 남깁니다. 실행 경로가 없는 항목은 문장을 늘려도 저절로 실행되지 않으므로 연결 공백 자체를 수정 대상으로 기록합니다.</p><p>문헌·출처·관리 연결은 문장을 통해 확인할 수 있는 역할과 별도 구조·원문 검사가 필요한 역할을 나눕니다. 그래프를 순회했다는 사실, 분석에서 도달했다는 사실, 올바른 출력에 기여했다는 사실을 각각 기록합니다. 어떤 항목도 이유 없이 검사 범위에서 빼지 않습니다.</p>''')
content.append('''<h2 id="freeze">5. 검증 중 수정과 비교 실험 중 수정은 다르게 관리합니다</h2><p>지금은 시스템이 의도대로 만들어졌는지 확인하는 검증·개발 단계입니다. 오류를 찾으면 근거와 함께 새 KG/코드 버전으로 수정하고 동일한 예문을 다시 실행할 수 있습니다. 최초 실패와 수정 전 결과는 보존합니다.</p><p>동료와 방법의 효과를 비교하는 실험에 들어갈 때는 KG·조회·전달·분석·모델 설정·입력·평가법을 동결합니다. 비교하려는 요인만 조건별로 다르게 고정합니다. 조회 방식을 비교하는 실험이라면 조회 방식 두 개가 각 조건 안에서 고정돼 있어야 한다는 뜻입니다.</p><p>실험 중 결함이 드러나면 실행 원본을 그대로 닫고 영향을 기록합니다. 방법 간 비교를 바꿀 결함이면 새 버전으로 영향을 받는 비교 조건을 다시 맞춰 실행합니다. 수정 전 A와 수정 후 B를 같은 실험의 결과로 합치지 않습니다. 코드/KG/요청 해시, 데이터 ID, 평가 기준, 실패와 재시도 규칙이 일치하는지 실행 전 확인합니다.</p><p>동료는 이 준비 기간에 현재 연구의 가정과 파이프라인을 검토하고 연구 질문·가설·조작할 요인·고정 요인·예상 결과·반례를 작성할 수 있습니다. 현재 검증을 기다리며 손을 놓을 필요는 없지만, 바뀌는 기반 위에서 비교 결과를 논문 결론으로 쌓지는 않습니다.</p>''')
content.append('<h2 id="appendix">6. 전체 목록과 실제 속성 사전</h2><p>아래 목록은 저장 파일에서 자동 집계했습니다. 속성이 존재하는지와 그 내용이 맞는지는 별도입니다. 설계 명세는 원래 항목의 original_spec 안에 보존돼 있습니다.</p>')
common=[n for n in old['nodes'] if n['type'] in ('AnalysisConcept','Construction','GrammarFeature','AggregateInterface')]
content.append(detail('공통 문법 설계 136개 전체 목록',table(['ID','이름','종류','설계상 실행 활성'],[(n['id'],n.get('title'),n['type'],n['properties'].get('runtime_active')) for n in common])))
content.append(detail('56용법과 57조건 분기 전체 목록',table(['용법 / 분기','실제 조건','필요한 입력 관계','합성 양성 조합'],[(s['branch_id'],s['conditions'],s['required_relations'],s['syntactic_positive_combinations']) for s in specs])))
for group in dictionary:
    rows=[(f['path'],str(f['present'])+'/'+str(group['count']),f['types'],f['example_node'],display(f['example'])[:650]) for f in group['fields'] if not isinstance(f['example'],dict)]
    content.append(detail(group['node_type']+' · '+str(group['count'])+'개 · 실제 속성',table(['저장 위치','존재 개수','자료형','실제 예시 ID','예시 값 (긴 값은 앞부분)'],rows)))
content.append('<h2>원본과 검사 기록</h2><p>정확한 전체 값은 동결 사본과 속성 사전에 보존돼 있습니다. 아래 원본은 사람이 읽는 설명의 근거이며 설명을 대신하지 않습니다.</p><ul>'+''.join('<li><a href="'+p+'">'+label+'</a></li>' for p,label in [('summary.json','집계와 입력 해시'),('node_ledger.jsonl','모든 노드의 검사 대장'),('edge_ledger.jsonl','모든 관계의 검사 대장'),('property_dictionary.json','실제 속성 전수 사전'),('branch_specifications.jsonl','분기별 조건과 남은 문장 작업'),('reader_contract_cases.jsonl','조회 계약 검사 입력과 결과')])+'</ul>')
style='''body{font:17px/1.75 "Malgun Gothic",sans-serif;color:#193041;background:#f4f6f8;margin:0}main{max-width:1100px;margin:auto;padding:28px 24px 80px;background:white}h1{font-size:30px}h2{margin-top:44px;font-size:24px}h3{font-size:20px}.lead{font-size:20px}nav,.flow{display:flex;gap:12px;flex-wrap:wrap}nav{padding:16px 0}a{color:#075d99}p{max-width:95ch}.flow{align-items:center;padding:20px 0}.flow span{background:#e9f1f6;padding:12px}.scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;margin:15px 0;font-size:15px}th,td{text-align:left;vertical-align:top;padding:10px;border-bottom:1px solid #d5dfe8;overflow-wrap:anywhere}th{background:#edf2f6}details{margin:15px 0}summary{cursor:pointer;font-weight:bold;padding:10px 0}td:first-child{min-width:130px}@media(max-width:600px){main{padding:16px}h1{font-size:26px}table{min-width:560px}}'''
(OUT/'guide.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>KG 실제 구조와 전수 검사 시작</title><style>'+style+'</style><main>'+''.join(content)+'</main></html>',encoding='utf8')
for key,rel in paths.items():assert sha(ROOT/rel)==sources[key]['sha256'], 'Source changed during audit: '+rel
dump(HERE/'private/latest.json',{'analysis_id':stamp,'directory':str(OUT),'guide':str(OUT/'guide.html')})
print(json.dumps({'directory':str(OUT),'summary':{k:summary[k] for k in ['ledger_rows','rules','branches','syntactic_positive_combinations','reader_contract_cases','reader_contract_matches','routing_cases_not_branch_evaluation','new_model_calls']},'isolated':stats['candidate']['isolated_node_ids'],'preservation':preservation},ensure_ascii=False))
