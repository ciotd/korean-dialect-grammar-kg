"""Read-only code/record audit. No Qwen call, graph mutation, or source rewrite."""
from pathlib import Path
import ast, collections, copy, datetime, hashlib, html, json, shutil, sys
from judgments import PROFILES, PROPOSED

ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from kg_pipeline.integrated import IntegratedReader, retrieve_packet, analysis_contract
GRAPH='knowledge/authored/semantic_grammar_20261106_integrated_r2/private/graph.json'
REFINED='knowledge/authored/semantic_grammar_20261106_integrated_r2/private/refined_knowledge.json'
DESIGN='knowledge/authored/kg_v3_evidence_20261019_r2/inputs/design.json'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canon(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def esc(v):return html.escape(str(v),quote=True)
def title(n):return n.get('title') or n['properties'].get('title',n['id'])

EVIDENCE={
 'morphology':('src/kg_runtime/morphology.py','analyze'),
 'observe':('src/kg_pipeline/integrated.py','observe_units'),
 'analysis':('src/kg_pipeline/integrated.py','analysis_contract'),
 'bind':('src/kg_pipeline/integrated.py','bind_analysis'),
 'query':('src/kg_pipeline/integrated.py','query'),
 'packet':('src/kg_pipeline/integrated.py','retrieve_packet'),
 'legacy':('src/kg_pipeline/integrated.py','legacy_search'),
 'generation':('src/kg_pipeline/integrated.py','GENERATION_PROMPT'),
 'diagnostic':('tools/run_integrated_grammar.py','observational_warnings'),
 'runner':('tools/run_integrated_grammar.py','execute'),
 'build':('experiments/analyses/integrated_grammar_20261106/build_graph.py','DEFER'),
 'lead':('experiments/analyses/integrated_grammar_20261106/prepare_lead_candidates.py','common'),
 'refined':(REFINED,None),
 'gaps':(GRAPH,None),
 'composer':('src/kg_runtime/realization.py','compose'),
 'wh-old':('experiments/analyses/semantic_kg_rebuild_20261102/semantic_graph.py','scope_clause_id'),
 'compile':('src/kg_pipeline/integrated.py','compile_overlay'),
 'support-build':('experiments/analyses/support_expansion_20261104/build_graph.py',None),
 'past-build':('experiments/analyses/overnight_20261105/build_past_graph.py',None),
}

def line_reference(path,needle):
    text=(ROOT/path).read_text(encoding='utf-8-sig');lines=text.splitlines()
    if needle:
        if path.endswith('.py'):
            tree=ast.parse(text)
            for node in ast.walk(tree):
                if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and node.name==needle:return {'path':path,'start':node.lineno,'end':node.end_lineno}
        found=next((i+1 for i,s in enumerate(lines) if needle in s),1)
    else:found=1
    return {'path':path,'start':found,'end':found}

def main():
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');out=HERE/'private'/stamp;out.mkdir(parents=True)
    paths=sorted(set([GRAPH,REFINED,DESIGN]+[p for p,_ in EVIDENCE.values()]+['experiments/analyses/integrated_grammar_20261106/private/claude/knowledge_candidates.json','tools/run_integrated_grammar.py','docs/research/CURRENT_RESEARCH_PLAN.md']))
    hashes={p:sha(ROOT/p) for p in paths}
    for p in paths:
        dst=out/'snapshot'/p;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/p,dst)
    evidence={k:line_reference(*v) for k,v in EVIDENCE.items()}
    g=read(ROOT/GRAPH);nodes={n['id']:n for n in g['nodes']};common={n['id'] for n in g['nodes'] if n['properties'].get('role')=='grammar'};rules={n['id'] for n in g['nodes'] if n['type']=='SemanticRule'}
    direct=[e for e in g['edges'] if (e['source'] in common and e['target'] in rules) or(e['source'] in rules and e['target'] in common)]
    touched={e[k] for e in direct for k in ('source','target')};uc=common-touched;ur=rules-touched
    assert len(uc)==107 and len(ur)==27 and len(direct)==55
    assert uc==set(PROFILES),(uc-set(PROFILES),set(PROFILES)-uc)
    assert ur==set(PROPOSED),(ur-set(PROPOSED),set(PROPOSED)-ur)
    refined={r['id']:r for r in read(ROOT/REFINED)['rules']};outgoing=collections.defaultdict(list)
    for e in g['edges']:outgoing[e['source']].append(e)
    current=IntegratedReader(g)
    # Diagnostic only: remove documentation links in a separate in-memory copy.
    stripped={**g,'edges':[e for e in g['edges'] if e['id'] not in {d['id'] for d in direct}]}
    alternate=IntegratedReader(stripped)
    assert set(current.rules)==set(alternate.rules)
    test_rows=[]
    for rid in sorted(ur):
        for branch in current.rules[rid]['branches']:
            f={k:vals[0] for k,vals in branch['conditions'].items()}
            rels={role:['SYNTHETIC_TARGET_'+role] for role in nodes[rid]['properties'].get('required_relations',[])}
            unit={'id':'SYNTHETIC','kind':f['unit_kind'],'text':'合成条件','span':[0,4],'morphs':[],'observed':{},'relations':rels}
            q=current.query(unit,f);qa=alternate.query(unit,f)
            eligible=rid in {x['rule_id'] for x in q['eligible']}
            assert eligible and q==qa,rid
            test_rows.append({'rule_id':rid,'branch':branch['id'],'eligible':eligible,'features':f,'relations':'synthetic presence only; not validated natural-language relations','comparison_equal':q==qa})
    # Test the title-versus-condition discrepancy without generating a sentence.
    rid='INT_AUX_PRESERVE_COMMON';b=current.rules[rid]['branches'][0];bf={k:vs[0] for k,vs in b['conditions'].items()}
    unit={'id':'SYNTHETIC','kind':'construction','text':'조건검사','span':[0,4],'morphs':[],'observed':{},'relations':{'main_predicate':['P'],'auxiliary_predicate':['A']}}
    state_probe=[]
    for value in ['progressive','resultative']:
        f={**bf,'auxiliary_kind':value};q=current.query(unit,f);hit=next(x for key in ['eligible','unresolved','rejected'] for x in q[key] if x['rule_id']==rid)
        state_probe.append({'auxiliary_kind':value,'state':hit['state'],'checks':hit['branches'][0]['checks']})
    save(out/'logical_probes.json',{'unlinked_rule_branch_cases':test_rows,'state_preservation_discrepancy':state_probe,'limits':'Checks stored code conditions only. No natural sentence, model call, binding validation or linguistic certification.'})
    records=[];replays=[];saved_hashes={};per_rule={rid:[] for rid in ur};feature_witness={};delivered_witness_all={};near_misses={}
    for run in sorted((ROOT/'experiments/runs').glob('*integrated_grammar*')):
        cfg=read(run/'config.json');local_records=0
        for rd in sorted((run/'private/records').iterdir()):
            if not (rd/'result.json').exists():continue
            res=read(rd/'result.json');record={'run':run.name,'id':res['id'],'text':res.get('input_text'),'output':res.get('output_text'),'status':res.get('status'),'graph_sha256':cfg['graph_sha256']};local_records+=1
            records.append(record)
            files={}
            for name in ['input.json','result.json','generation_packet.json','bound_analysis.json','retrieval.json','units.json','morphology.json']:
                p=rd/name
                if p.exists():
                    saved_hashes[p.relative_to(ROOT).as_posix()]=sha(p);files[name]=read(p)
            packet=files.get('generation_packet.json',{});traces=files.get('retrieval.json',[])
            for delivered in packet.get('verified_scope_knowledge',[]):
                delivered_witness_all[delivered['rule_id']]={**record,'rule_id':delivered['rule_id'],'unit_id':delivered['unit_id'],'source_text':delivered['source_text']}
            for rid in ur:
                trace=[{'unit_id':t['unit_id'],**hit} for t in traces for key in ['eligible','unresolved','rejected'] for hit in t.get(key,[]) if hit['rule_id']==rid]
                for hit in trace:
                    if hit['state']=='eligible':continue
                    for branch in hit['branches']:
                        anchors=[c for c in branch['checks'] if c['feature'] in ['source_form','source_final','lemma','prefinal_type']]
                        if not anchors or not all(c['state']=='true' for c in anchors):continue
                        bad=[c for c in branch['checks'] if c['state']!='true'];score=len(bad)+len(hit.get('missing_relations',[]))
                        if rid not in near_misses or score<=near_misses[rid]['score']:
                            near_misses[rid]={**record,'unit_id':hit['unit_id'],'state':hit['state'],'failed_or_unknown':bad,'missing_relations':hit.get('missing_relations',[]),'score':score}
                delivered=[a for a in packet.get('verified_scope_knowledge',[]) if a['rule_id']==rid]
                if trace or delivered or rid in res.get('used_rule_ids',[]):
                    per_rule[rid].append({**record,'delivered':bool(delivered),'declared_used':rid in res.get('used_rule_ids',[]),'eligible':any(x['state']=='eligible' for x in trace),'unresolved':any(x['state']=='unresolved' for x in trace),'evaluated_units':len(trace),'delivered_targets':[{'unit_id':x['unit_id'],'text':x['source_text'],'conditions':x['conditions'],'relations':x['relations']} for x in delivered]})
            if 'bound_analysis.json' in files:
                bound=files['bound_analysis.json'];p1,t1=retrieve_packet(current,record['text'],bound,cfg.get('knowledge_character_budget',24000));p2,t2=retrieve_packet(alternate,record['text'],bound,cfg.get('knowledge_character_budget',24000))
                eq=p1==p2 and t1==t2 and analysis_contract(current,bound)==analysis_contract(alternate,bound)
                assert eq,(run.name,rd.name)
                replays.append({'run':run.name,'id':rd.name,'unit_count':len(bound),'packet_hash':canon(p1),'without_documentation_links_packet_hash':canon(p2),'trace_hash':canon(t1),'all_equal':eq,'current_reader_on_frozen_analysis':True,'historical_graph_sha256':cfg['graph_sha256']})
                for u in bound:
                    for k,v in u.get('features',{}).items():
                        if v is not None:feature_witness.setdefault((k,str(v)),{'run':run.name,'id':rd.name,'text':record['text'],'unit_id':u['id'],'feature':k,'value':v,'origin':u.get('feature_origin',{}).get(k)})
                    for k,vs in u.get('relations',{}).items():
                        if vs:feature_witness.setdefault(('relation',k),{'run':run.name,'id':rd.name,'text':record['text'],'unit_id':u['id'],'relation':k,'targets':vs})
                    feature_witness.setdefault(('kind',u['kind']),{'run':run.name,'id':rd.name,'text':record['text'],'unit_id':u['id'],'kind':u['kind'],'span':u['span'],'observed':u['observed']})
        print(json.dumps({'read_run':run.name,'records':local_records,'replay_total':len(replays)},ensure_ascii=False),flush=True)
    save(out/'historical_record_index.json',records);save(out/'replay.json',replays);save(out/'feature_witnesses.json',list(feature_witness.values()));save(out/'rule_trace_evidence.json',per_rule);save(out/'delivered_rule_witnesses.json',delivered_witness_all)
    rrows=[]
    for rid in sorted(ur):
        if rid in refined:
            ids=refined[rid]['legacy_ids'];types=[nodes[id]['type'] for id in ids]
            assert all(x=='SourceAtom' for x in types)
            origin='문헌 항목에만 연결' if ids else '연결 목록이 빈 채 추가'
            why='구축 코드가 legacy_ids에 적힌 문헌 항목만 REFINES로 연결했고 공통 설계 ID는 포함되지 않았다.' if ids else '후보 정의의 legacy_ids가 빈 배열이다. 구축 코드는 빈 목록을 허용하므로 조건·형태·근거만 생성하고 대응 연결을 만들지 않았다.'
            evidence_keys=['compile','refined']+(['lead'] if rid.startswith('INT_LEAD_') else [])
        else:
            ids=[];origin='이전 실행 KG에서 승계'
            why='이전 확장 빌더가 용법과 근거/문헌 항목/연구 후보를 연결했지만 G_* 공통 설계 연결은 만들지 않았다. 통합 단계는 이 상태를 그대로 가져왔다.'
            evidence_keys=['compile','past-build' if rid=='SEM_EXT_COP_PAST_HAEYE' else 'support-build']
        rows=per_rule[rid];deliver=[r for r in rows if r['delivered']];example=next((r for r in reversed(deliver) if r['output'] is not None),deliver[-1] if deliver else None)
        counts={run.name:{k:sum(bool(x[k]) for x in rows if x['run']==run.name) for k in ['eligible','delivered','declared_used','unresolved']} for run in sorted((ROOT/'experiments/runs').glob('*integrated_grammar*'))}
        note='관련 책임의 후보 대응이다. 연결 추가가 해당 설계 전체 구현이나 품질 검증을 뜻하지 않는다.'
        if rid.startswith('INT_NOM_WH'):note+=' 의문사 어휘 치환은 의문사 범위 결속의 구현이 아니므로 완전한 정제 관계로 연결해서는 안 된다.'
        if rid=='INT_AUX_PRESERVE_COMMON':note+=' 제목의 상태와 달리 resultative는 조건에서 제외되어 있다. G_AUX_STATE를 현재 지원으로 연결하면 잘못된 표시가 된다.'
        if rid=='INT_PART_GEN_ZERO':note+=' 136개에는 이 용법에 정확히 대응하는 독립 소유격 항목이 없어 넓은 격/명사구 항목만 후보로 제시한다.'
        rrows.append({'id':rid,'title':title(nodes[rid]),'origin':origin,'why':why,'legacy_ids':ids,'implementation':'현재 조회·전달 경로 존재; 저장된 분기 조건의 합성 검사 통과','branches':current.rules[rid]['branches'],'required_relations':nodes[rid]['properties'].get('required_relations',[]),'historical_counts_by_run':counts,'historical_any_delivery':bool(deliver),'historical_delivery_records':len(deliver),'example':example,'near_miss':near_misses.get(rid) if not deliver else None,'proposed_related_common':PROPOSED[rid],'proposal_limit':note,'evidence':evidence_keys})
    crows=[]
    for cid in sorted(uc,key=lambda id:(nodes[id]['properties']['module'],id)):
        p=copy.deepcopy(PROFILES[cid]);n=nodes[cid];s=n['properties']['original_spec']
        matched=[rid for rid,ids in PROPOSED.items() if cid in ids]
        # Witnesses demonstrate only the named feature/relationship, never the whole design.
        witness_keys={
          'predicate':[('predicate_class','adjective'),('predicate_class','negative_copula')], 'honorific':[('subject_honorific','present')],
          'alignment':[('kind','connector')], 'tags':[('kind','predicate')], 'stem':[('kind','predicate')], 'units':[('kind','nominal')],
          'roles':[('relation','agent'),('relation','patient')], 'modifier':[('relation','modifier_head')],
          'speech-functions':[('speech_act','exclamation'),('semantic_function','intention')], 'case-semantics':[('semantic_function','topic'),('semantic_function','object')],
          'clause-keys':[('clause_role','embedded'),('clause_role','quoted')], 'scope':[('relation','negation_target')],
          'ending-slots':[('prefinal_sequence','eoss')], 'aux-role':[('relation','main_predicate'),('relation','auxiliary_predicate')],
          'aux-state-gap':[('auxiliary_kind','resultative')], 'passive':[('voice','passive')],
        }.get(p['profile'],[])
        witnesses=[feature_witness[k] for k in witness_keys if k in feature_witness]
        narrow=NARROW_RULES.get(p['profile'],[])
        crows.append({'id':cid,'title':title(n),'module':n['properties']['module'],'type':n['type'],**p,'actual_spec_match':s.get('match'),'actual_spec_output':s.get('output'),'related_unlinked_rules_proposal':matched,'witnesses':witnesses,'narrow_rule_ids':narrow,'narrow_rule_witnesses':[delivered_witness_all[rid] for rid in narrow if rid in delivered_witness_all],'witness_limit':'Only this stored value or relation was observed. It does not establish the full G_* contract.'})
    stats={'unlinked_common':len(uc),'unlinked_rules':len(ur),'common_categories':dict(collections.Counter(r['category'] for r in crows)),
      'unlinked_rule_origins':dict(collections.Counter(r['origin'] for r in rrows)),
      'unlinked_rules_with_historical_delivery':sum(r['historical_any_delivery'] for r in rrows),
      'unlinked_rules_without_historical_delivery':sum(not r['historical_any_delivery'] for r in rrows),
      'historical_result_records':len(records),'replayed_frozen_analyses':len(replays),'replayed_units':sum(r['unit_count'] for r in replays),
      'documentation_edges_removed_in_memory_only':len(direct),'changed_packets_or_traces':sum(not r['all_equal'] for r in replays),
      'synthetic_branch_probes':len(test_rows),'all_unlinked_rules_logically_reachable':len({r['rule_id'] for r in test_rows}),
      'unique_refines_targets_by_type':dict(collections.Counter(nodes[id]['type'] for id in {e['target'] for e in g['edges'] if e['relation']=='REFINES'})),
      'new_model_calls':0,'persistent_kg_or_runtime_changes':False}
    design=read(ROOT/DESIGN);book={'source_limit':design['root']['common_grammar_source_limit'],'design_scope':design['roles']['grammar']['design_scope'],'atomic_definition':design['root']['atomic_definition'],'historical_intent_limit':'No documentary evidence that a complete standard grammar book was compared and intentionally rejected. Additional rationale is an engineering interpretation, not a historical fact.'}
    save(out/'audit.json',{'stats':stats,'common':crows,'rules':rrows,'code_evidence':evidence,'standard_grammar_origin':book,'findings':{'state_probe':state_probe},'classification_is_auditor_judgment':True})
    save(out/'manifest.json',{'analysis_id':stamp,'question':'Why are 107 common concepts and 27 current usages not directly linked? Which contracts are implemented, partial, absent or historical only?','scope':'Current integrated entry point, graph builders, and four archived integrated runs. No source-text semantic recertification.','before_checkpoint':read(ROOT/'local/version_history/latest.json')['commit'],'input_hashes':hashes,'historical_record_hashes':saved_hashes,'future_decision':'Review correspondence and missing functionality before any KG/code edit.','stop_criterion':'All 107/27 IDs accounted for, reasons and code/record limits explicit, immutable inputs checked.'})
    assert all(sha(ROOT/p)==h for p,h in hashes.items())
    assert all(sha(ROOT/p)==h for p,h in saved_hashes.items())
    render(out,stats,crows,rrows,evidence,book)
    print(json.dumps({'directory':str(out),'stats':stats},ensure_ascii=False),flush=True)

def render(out,stats,crows,rrows,evidence,book):
    previous=ROOT/'experiments/analyses/common_grammar_walkthrough_20261107/private/20261107T033934996218Z/guide.html'
    def common_link(id):return '#'+id if id in PROFILES else previous.as_uri()+'#'+id
    def narrow_html(r):
        if not r.get('narrow_rule_ids'):return ''
        s='<h4>일부 책임을 맡는 실제 후보 ID</h4><p>'+esc(', '.join(r['narrow_rule_ids']))+'</p>'
        for w in r.get('narrow_rule_witnesses',[]):s+='<div class="obs"><b>'+esc(w['rule_id'])+'</b><p>'+esc(w['text'])+' → '+esc(w['output'])+'</p><small>'+esc(w['run']+' / '+w['id'])+'</small><p>전달 기록이며, 이 공통 계약 전체의 의미 검증은 아니다.</p></div>'
        if not r.get('narrow_rule_witnesses'):s+='<p>위 후보의 전달 사례는 확인한 네 실행에서 찾지 못했다. 조건·전달 코드의 존재와 실제 도달을 구분한다.</p>'
        return s
    def refs(keys):
        return ''.join(f'<li><code>{esc(evidence[k]["path"])}</code> {evidence[k]["start"]}–{evidence[k]["end"]}행</li>' for k in dict.fromkeys(keys))
    def example(r):
        x=r['example']
        if not x:
            s='<p class="warn">과거 4개 통합 실행 기록에서 전달 사례를 찾지 못했다. 조건 조회 코드가 없다는 뜻은 아니다. 분석 오류·시험 입력 부족·조건/관계 불충족을 추가로 나눠야 한다.</p>'
            near=r.get('near_miss')
            if near:
                s+=f'<p><b>원문 형태는 맞았지만 다른 조건에서 배제된 실제 사례:</b> {esc(near.get("text"))}<br>{esc(near["run"])} / {esc(near["id"])} / {esc(near["unit_id"])}</p><ul>'
                labels={'semantic_function':'문맥 기능','addressee_level':'말높임','speech_act':'발화 기능','question_kind':'질문 종류','ending_tag':'어미 종류'}
                vals={'location':'장소','interrogative':'정보 의문','subject':'주어','endpoint':'끝점','limitation':'범위 제한','plain':'반말','polite':'공손한 말','formal':'격식 높임','prohibition':'금지','statement':'진술','information_question':'정보 질문','confirmation':'확인','polar':'판정 질문','EF':'종결어미','EC':'연결어미'}
                for c in near['failed_or_unknown']:
                    v='미확정' if c['value'] is None else vals.get(c['value'],c['value']);allowed=' 또는 '.join(vals.get(v,v) for v in c['allowed'])
                    s+=f'<li>{esc(labels.get(c["feature"],c["feature"]))}: 저장 분석은 {esc(v)}, 용법은 {esc(allowed)}를 요구</li>'
                s+='</ul><p>배제됐다는 사실만으로 오류라고 판정하지 않는다. 실제로 다른 기능의 문장이거나 분석값·용법 조건의 구별 방식이 맞지 않을 수 있다.</p>'
            return s
        return f'<div class="obs"><b>당시 실제 전달 사례</b><p>{esc(x["text"])} → {esc(x["output"])}</p><small>{esc(x["run"])} / {esc(x["id"])} · Qwen 사용 선언 {"있음" if x["declared_used"] else "없음"}</small><p>이 실행은 당시 코드·KG의 기록이며 현재 품질 검증으로 합산하지 않는다.</p></div>'
    common_html=''.join(f'''<details class="item common" data-category="{esc(r['category'])}" id="{r['id']}"><summary><span class="badge">{esc(r['category'])}</span> {esc(r['title'])}<small>{r['id']}</small></summary><p><b>현재 실제로 하는 일:</b> {esc(r['implemented'])}</p><p><b>아직 하지 못하는 일 / 연결 부재 해석:</b> {esc(r['missing'])}</p><p><b>처음 설계가 요구한 것:</b> {esc(' / '.join(r['actual_spec_match'] or []))}</p><p><b>설계상 출력:</b> {esc(r['actual_spec_output'])}</p><p><b>관련 용법 후보:</b> {', '.join(f'<a href="#{id}">{id}</a>' for id in r['related_unlinked_rules_proposal']) or '별도 대응이 없거나 공통 처리 책임임'}</p><p>위 대응은 이번 해석이며 실제 KG에는 추가하지 않았다.</p>{('<div class="warn">과거 별도 구현: '+esc(evidence[r['history']]['path'])+' — 현재 실행기에서 사용하지 않음.</div>') if r['history'] else ''}<h4>저장 기록에서 찾은 부분 증거</h4>{''.join('<p>'+esc(w['run']+' / '+w['id']+' / '+w['unit_id'])+'<br>'+esc(w['text'])+'<br>'+esc(str({k:v for k,v in w.items() if k not in ['run','id','unit_id','text']}))+'</p>' for w in r['witnesses']) or '<p>이 행에 직접 제시할 특징·관계의 실측 증거는 없음. 코드 존재와 실측 도달을 구분한다.</p>'}<p class="muted">이름표나 관계 하나의 존재는 공통 계약 전체의 구현·정확성 증거가 아니다.</p><ul>{refs(r['evidence']+([r['history']] if r['history'] else []))}</ul></details>''' for r in crows)
    # Insert each narrow-rule witness block at its own card, not by repeated generic text matching.
    import re
    for r in crows:
        marker=f'id="{r["id"]}"'
        pattern='('+re.escape(marker)+r'.*?)(<h4>저장 기록에서 찾은 부분 증거</h4>)'
        common_html=re.sub(pattern,lambda m:m.group(1)+narrow_html(r)+m.group(2),common_html,count=1,flags=re.S)
    rules_html=''.join(f'''<details class="item rule" id="{r['id']}"><summary><span class="badge">{esc(r['origin'])}</span> {esc(r['title'])}<small>{r['id']}</small></summary><p><b>연결이 없는 직접 원인:</b> {esc(r['why'])}</p><p><b>기능 구현:</b> {esc(r['implementation'])}</p><p><b>기존 연결 대상:</b> {esc(', '.join(r['legacy_ids']) or '이 legacy_ids 목록 없음; 승계 항목은 별도 빌더 참고')}</p>{example(r)}<p><b>검토할 공통 책임:</b> {', '.join(f'<a href="{common_link(id)}">{id}</a>' for id in r['proposed_related_common'])}</p><p class="warn">{esc(r['proposal_limit'])}</p><table><tr><th>당시 실행</th><th>조건 충족 기록</th><th>전달 기록</th><th>사용 선언 기록</th></tr>{''.join(f'<tr><td>{esc(run)}</td><td>{v["eligible"]}</td><td>{v["delivered"]}</td><td>{v["declared_used"]}</td></tr>' for run,v in r['historical_counts_by_run'].items())}</table><p>분모는 각 실행에 포함된 입력 기록이다. 용법별 전용 시험의 성공률이 아니다.</p><ul>{refs(r['evidence'])}</ul></details>''' for r in rrows)
    category_table=''.join(f'<tr><th>{esc(k)}</th><td>{v}</td></tr>' for k,v in stats['common_categories'].items())
    body=f'''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>연결 공백 107개·27개 원인 감사</title><style>{CSS}</style><header><p>수정 전 설명 · 코드와 과거 실행을 읽은 감사</p><h1>선이 없다는 것과<br>기능이 없다는 것은 다릅니다</h1><p>공통 107개와 용법 27개를 모두 확인했습니다. 아래 분류는 현재 실행 경로의 계약 범위를 대조한 감사 판단이며 품질 점수가 아닙니다.</p></header><main><section><h2>먼저 결론</h2><p><b>27개 용법은 모두 현재 코드가 조건을 읽고 전달할 수 있습니다.</b> 직접 연결이 없는 이유는 연결 목록 작성·이전 판본 승계 방식에서 확인됩니다. 하지만 공통 107개에는 공통 처리, 좁은 용법 구현, 분석값만 있는 부분 구현, 현재 전용 구현 부재, 묶음 창구 설계가 섞여 있습니다.</p><p><a href="overview.html">Archify 그림으로 전체 결론 보기 ↗</a></p><table><tr><th>공통 107개 판정</th><th>개수</th></tr>{category_table}</table><p class="warn">‘용법에 한정 구현’과 ‘분석·지시 일부만 구현’은 공통 설계 전체의 구현 완료가 아닙니다. ‘현재 전용 구현 없음’도 Qwen이 해당 문장을 전혀 처리할 수 없다는 뜻은 아닙니다.</p></section><section><h2>왜 표준어 문법책을 그대로 가져오지 않았나?</h2><p><b>확인된 역사적 이유는 당시 별도 공통 한국어 문법책 전체가 제공되지 않았다는 것입니다.</b> 책을 읽은 뒤 통째로 가져오는 방법을 의도적으로 배제했다는 증거는 찾지 못했습니다.</p><blockquote>{esc(book['source_limit'])}</blockquote><p>실제로는 방언 자료가 보여 주는 구별을 출발점으로 분석·보존 책임을 설계했습니다. 왜 그런 분해가 필요한가에 대한 일반적 설명과, 당시 그렇게 선택한 이유는 분리해야 합니다.</p><table><tr><th>문헌의 설명</th><th>프로그램에서 추가로 정할 것</th></tr><tr><td>주체높임을 나타낸다</td><td>어느 주체인지, ‘시’가 실제로 분리됐는지, 모호하면 어떻게 할지</td></tr><tr><td>조건 연결어미를 쓴다</td><td>앞뒤 절 ID, 조건 기능값, 적용·비적용 조건</td></tr><tr><td>과거를 보존한다</td><td>입력 과거 형태, 후보 선택, 출력에서의 보존 검사</td></tr></table><p>이 추가 설계가 필요하다는 사실은 최초 136개 목록이 충분했다는 증명이 아닙니다. 표준어 문법 원전과의 체계적인 대조가 부족한 출발점은 연구 한계로 남습니다. 이후 원전의 분류·정의·예외와 항목별로 대조해야 하며, 책 목차를 전부 새 실행 규칙으로 복사할 필요는 없습니다.</p></section><section><h2>연결이 누락된 정확한 생성 경로</h2><table><tr><th>27개 용법의 부재 원인</th><th>개수</th><th>실제 코드 동작</th></tr>{''.join(f'<tr><td>{esc(k)}</td><td>{v}</td><td>{esc("legacy_ids에 문헌 항목만 존재" if k=="문헌 항목에만 연결" else "legacy_ids가 빈 배열" if k=="연결 목록이 빈 채 추가" else "이전 확장 그래프의 연결을 그대로 복사")}</td></tr>' for k,v in stats['unlinked_rule_origins'].items())}</table><p>구축기는 목록에 있는 ID의 존재만 검사하고 연결을 만듭니다. 공통 설계 대응이 적어도 하나 있어야 한다는 검사는 없습니다. 따라서 이를 ‘컴퓨터가 연결을 잃어버렸다’고 보기보다, 대응을 일관되게 기록하지 않은 구축 계약의 공백이라고 보는 것이 정확합니다.</p><p>누가 어떤 의도로 목록을 비웠는지는 개별 결정 기록이 없는 경우 확정하지 않았습니다.</p></section><section><h2>선을 추가하면 출력이 바로 좋아질까?</h2><p>실제 KG 파일은 그대로 두고, 메모리 사본에서 공통↔용법 연결 55개만 빼서 비교했습니다. 저장된 분석 <b>{stats['replayed_frozen_analyses']}건·{stats['replayed_units']}단위</b>에 대해 현재 조회 코드의 후보·추적·전달 패킷과 분석 계약이 모두 같았습니다.</p><p>현재 조회기는 그 선을 실행 조건으로 읽지 않습니다. 연결은 추적·설명에 중요하지만, 연결 추가만으로 분석 오류·관계 누락·시제 손실이 고쳐지지는 않습니다. Qwen은 새로 호출하지 않았으므로 새 생성 출력 비교는 아닙니다.</p></section><section><h2>연결만 고치면 안 되는 구체 사례</h2><p><b>‘상태 보존’이라는 이름과 실제 조건이 다릅니다.</b> INT_AUX_PRESERVE_COMMON의 제목에는 진행·희망·상태·당위·봉사·시행이 나오지만 허용값은 5종이며 결과 상태 resultative가 빠져 있습니다. 다른 조건을 고정한 논리 검사에서 progressive는 통과, resultative는 거절됐습니다.</p><p>이것은 저장된 제목과 조건의 불일치입니다. resultative를 추가하는 것이 언어학적으로 옳은지는 별도 검토해야 합니다. 지금 G_AUX_STATE 연결만 넣고 상태 처리를 구현했다고 표시하면 잘못입니다.</p><p><b>의문사 범위는 과거 코드와 현재 경로를 구별해야 합니다.</b> 이전 실험에는 출현 절·범위 절을 검사하는 제한적 코드가 있지만, 현재 분석 계약에는 그 필드가 없습니다. 과거 코드가 존재한다는 이유로 현재 G_Q_SCOPE가 구현됐다고 판정하지 않았습니다.</p></section><section><h2>107개 공통 항목별 판정</h2><p>각 항목을 펼치면 현재 처리·남은 계약·코드 위치·부분 실행 증거가 나옵니다.</p><div class="tools"><input id="q" placeholder="항목명·ID·키워드 검색" aria-label="검색"><select id="category" aria-label="분류"><option value="">전체 분류</option>{''.join(f'<option>{esc(k)}</option>' for k in stats['common_categories'])}</select></div><p id="count"></p><div id="common">{common_html}</div></section><section><h2>27개 용법별 원인과 실제 전달 기록</h2><p>모두 조건·전달 구현이 존재합니다. 이 중 {stats['unlinked_rules_with_historical_delivery']}개 ID는 과거 통합 실행에서 전달 기록이 있고, {stats['unlinked_rules_without_historical_delivery']}개 ID는 찾지 못했습니다. 네 실행의 판본과 반복을 합쳐 품질·지원률로 계산하지 않습니다.</p><div id="rules">{rules_html}</div></section><section><h2>수정 전 권고 순서</h2><ol><li>현재 구현된 책임과 공통 설계의 대응표를 먼저 검토합니다. ‘전체 구현’과 ‘일부만 대응’을 구별합니다.</li><li>출처·검토 기록을 실행 그래프 밖으로 분리한다는 현행 방침에 맞춰, 대응표도 별도 추적 기록으로 둘지 결정합니다. 실행에 쓰지 않는 선을 무조건 KG에 늘릴 필요는 없습니다.</li><li>상태 조건 불일치·의문사 범위·뜻별 어휘 처리 같은 기능 공백은 각각 근거와 반례를 정한 뒤 별도 구현 대상으로 다룹니다.</li><li>그 뒤 조건별 자연어 예문을 전체 파이프라인에 넣고 실제 도달과 사람 판정을 기록합니다.</li></ol><p>이번에는 조사와 설명만 수행했습니다. KG·실행 코드·기존 출력의 수정, 새 모델 호출은 없습니다. 새 분류는 감사자의 판단이며 독립 언어학 검토를 받았다는 뜻은 아닙니다.</p><p class="muted">분석 ID {out.name} · <a href="audit.json">전체 근거 대장</a> · <a href="manifest.json">입력·실행 해시</a> · <a href="replay.json">메모리 비교 기록</a></p></section></main><script>
function filter(){{let q=document.querySelector('#q').value.toLowerCase(),c=document.querySelector('#category').value,n=0;document.querySelectorAll('#common .item').forEach(x=>{{x.hidden=!(x.textContent.toLowerCase().includes(q)&&(!c||x.dataset.category===c));if(!x.hidden)n++}});document.querySelector('#count').textContent=n+' / 107개 표시';}}document.querySelector('#q').oninput=filter;document.querySelector('#category').onchange=filter;filter();
function reveal(){{let x=document.getElementById(decodeURIComponent(location.hash.slice(1)));if(x){{document.querySelector('#q').value='';document.querySelector('#category').value='';filter();x.open=true;x.scrollIntoView();}}}}window.onhashchange=reveal;reveal();
</script></html>'''
    (out/'report.html').write_text(body,encoding='utf-8')

CSS='''*{box-sizing:border-box}body{margin:0;background:#f2f6f7;color:#173449;font:17px/1.75 "Malgun Gothic",sans-serif}header{padding:36px max(24px,calc((100vw - 1160px)/2));background:#173449;color:white}h1{font-size:34px;line-height:1.4}h2{font-size:25px}main{max-width:1220px;margin:auto;padding:20px}section{background:white;padding:26px;margin:20px 0;border-radius:14px;border:1px solid #d6e2e7}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:12px;text-align:left;border-bottom:1px solid #d6e2e7;overflow-wrap:anywhere}th{background:#f0f5f6}.item{border:1px solid #cfdee4;border-radius:9px;padding:16px;margin:10px 0;overflow-wrap:anywhere;scroll-margin-top:15px}summary{cursor:pointer;font-weight:bold}summary small{display:block;color:#637c8a;font-size:12px;font-weight:normal}.badge{display:inline-block;background:#e4f1f2;color:#08616c;font-size:12px;border-radius:12px;padding:2px 8px;margin-right:10px}.muted,small{color:#607786}.warn{padding:15px;background:#fff3d9;border-radius:8px}.obs{padding:16px;background:#edf6f2;border-radius:8px}blockquote{border-left:4px solid #25808c;margin:18px 0;padding:15px;background:#edf6f8}.tools{display:flex;gap:10px;flex-wrap:wrap}input,select{font:inherit;padding:10px;border:1px solid #a9c0ca;border-radius:8px}input{flex:1;min-width:230px}code{font-size:12px}a{color:#086d86}.item[hidden]{display:none}@media(max-width:600px){body{font-size:16px}h1{font-size:28px}main{padding:10px}section{padding:17px}table{font-size:12px}th,td{padding:7px}.tools>*{width:100%}}'''

NARROW_RULES={
 'predicate':['INT_LEAD_DECL_PRESENT_DA','SEM_SUP_COP_PRESENT','SEM_EXT_COP_PAST_HAEYE'],
 'honorific':['SEM_SUP_POLITE_Q_EO'],
 'focus':['INT_PART_FOCUS_SA','INT_PART_EXCEPT_BAKKI','INT_PART_UNTIL_KKEOJI'],
 'sequence':['INT_CONN_SEQ_AGA','INT_CONN_INTERRUPT_DA','INT_CONN_COND_MO'],
 'aspect':['INT_AUX_BEORIDA_PPIDA','INT_AUX_PRESERVE_COMMON'],
 'modality':['INT_TAM_GET_GEOT'],
 'aux-benefactive':['INT_LEAD_REQUEST_JU_AUX','INT_AUX_PRESERVE_COMMON'],
 'aux-preserve':['INT_AUX_PRESERVE_COMMON'],
 'aux-state-gap':['INT_AUX_PRESERVE_COMMON'],
 'causative':['INT_CAUS_CONTRACT_AARA'],
 'passive':['INT_PASS_PRESERVE'],
}

if __name__=='__main__':main()
