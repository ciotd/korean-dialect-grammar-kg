"""Build an immutable candidate overlay from reviewed source interpretations."""
import collections
import copy
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from kg_pipeline.integrated import compile_overlay,IntegratedReader,analysis_contract
from kg_pipeline.io import read,save,sha
HERE=Path(__file__).resolve().parent
OUT=ROOT/'knowledge/authored/semantic_grammar_20261106_integrated/private'
norm=lambda s:s.replace('ᆯ','ㄹ').replace('ᆫ','ㄴ').replace('ᆷ','ㅁ').replace('ᆸ','ㅂ')
ALIASES={'cause':'reason','comparison_standard':'comparison','restriction':'limitation','indirect_quote':'quotation','question':'information_question'}
DEFER={
 'INT_CONN_CONCESS_DO':'더라도→어도의 가정 의미 보존이 문헌에서 확인되지 않아 범용 변환을 보류한다.',
 'INT_CONN_CONTRAST_JIMANEUN':'표 행 대응이 불명확하고 대조→양보 변화 가능성이 있어 PDF 표 재검토가 필요하다.',
 'INT_END_HORT_PLAIN_JEI':'조심스러움·즉시성 조건은 이번 분석 범위에 없다. source_form만 추가해 일반 청유 전체에 적용하지 않는다.',
 'INT_TAM_FUT_KKIDA':'관형형 ㄹ+것+계사의 연결을 이 후보의 필수 관계로 아직 표현하지 못한다.',
 'INT_COP_RA':'계사 과거 후보와 겹치며 동형 실현·높임·시제별 분기를 추가 검토해야 한다.',
 'INT_END_Q_SI_NOUN_GA':'기존 시 선어말 조건의 계사 질문과 중복. 별도 실행 규칙으로 더하지 않고 기존 경로의 시험 대상으로 둔다.',
}

def main():
    candidates=read(HERE/'private/claude/knowledge_candidates.json')
    adjud=read(HERE/'private/claude/adjudication.json');decisions={r['id']:r for r in adjud['rules']}
    rules=[];ledger=[]
    for original in candidates['rules']:
        r=copy.deepcopy(original);d=decisions[r['id']];change=d['proposed_changes']
        why=DEFER.get(r['id']) or (d['reason'] if d['decision']=='defer' else None)
        if why:
            ledger.append({'id':r['id'],'title':r['title'],'decision':'deferred','reason':why,'packages':r['packages'],'legacy_ids':r['legacy_ids']});continue
        for key in ('conditions','forms','unit_kind','lexical_map','forms_annotated'):
            if key in change:r[key]=copy.deepcopy(change[key])
        if change.get('instruction_rewrite'):r['instruction']=change['instruction_rewrite']
        r['forms']=[f for f in r['forms'] if f not in change.get('forms_remove',[])]
        r['legacy_ids']=[i for i in r['legacy_ids'] if i not in change.get('legacy_ids_remove',[])]
        r['source_refs']=[e for e in r['source_refs'] if e not in change.get('source_refs_remove',[])]
        variants=[r]
        if r['id']=='INT_NOM_WH_EODE':
            variants=[]
            for split in change['split_into']:
                variants.append({**copy.deepcopy(r),**{k:v for k,v in split.items() if k in ('id','conditions','forms','unit_kind')}})
        elif r['id']=='INT_CONN_PURPOSE_GURO':
            # Degree/until remains separately visible in source candidates, not silently
            # merged into the purpose-only branch with different source restrictions.
            r['conditions']={'source_form':['게','도록'],'semantic_function':['purpose']}
        elif r['id']=='INT_Q_CONFIRM_ANIGA':
            r['conditions']={'lemma':['않'],'speech_act':['information_question'],'question_kind':['confirmation'],'addressee_level':['plain']}
            r['forms']=['-다 아니가','-다이가']
        elif r['id']=='INT_CONN_QUOTE_KKO':
            r['conditions']['source_form']=['다고','ㄴ다고','는다고']
            r['forms']=['-다꼬'];r['instruction']='서술 간접인용의 다고/ㄴ다고/는다고에서 인용 기능을 유지하며 고를 꼬로 실현하는 후보. 인용 내용의 시제·높임과 뒤의 말하다/하다를 보존한다. 라고 하다 축약은 이번 규칙 밖이다.'
        for v in variants:
            v['conditions']={k:[ALIASES.get(norm(x),norm(x)) for x in vals] for k,vals in v['conditions'].items()}
            if v['unit_kind']=='predicate' and v.get('rule_type')!='preserve_only':v['conditions']['ending_tag']=['EF']
            if v['unit_kind']=='connector':v['conditions']['morph_tag']=['EC']
            if v['unit_kind']=='particle':v['conditions']['morph_tag']=['JKB','JX','JC','JKG']
            # Add constraints identified in plain language to machine-checked fields.
            if v['id']=='INT_END_RETRO_DE':v['conditions']['addressee_level']=['plain']
            if v['id']=='INT_END_Q_CONFIRM_JE':v['conditions']['addressee_level']=['plain'];v['forms']=['-제']
            if v['id']=='INT_PART_EXCEPT_BAKKI':v['conditions']['polarity']=['negative'];v['required_relations']=['nominal_host','head_predicate']
            if v['id']=='INT_CAUS_CONTRACT_AARA':v['conditions']['speech_act']=['command'];v['conditions']['voice']=['causative']
            if v['id']=='INT_AUX_GA_BODA_BAE':v['conditions']['auxiliary_kind']=['other']
            v['limitations']+=' | 조건 보완: '+d['reason']
            rules.append(v)
        ledger.append({'id':r['id'],'title':r['title'],'decision':'trial_candidate','produced_ids':[v['id'] for v in variants],
                       'reason':d['reason'],'packages':r['packages'],'legacy_ids':r['legacy_ids']})
    if (HERE/'private/lead_candidates.json').exists():
        for r in read(HERE/'private/lead_candidates.json')['rules']:
            rules.append(r);ledger.append({'id':r['id'],'title':r['title'],'decision':'trial_candidate','produced_ids':[r['id']],
                'reason':'리드가 누락된 핵심 용법을 직접 원문 대조. 표준어 입력과 문헌 실현형의 대응은 연구 해석.', 'packages':r['packages'],'legacy_ids':r['legacy_ids']})
    refined={'rules':rules,'gaps':candidates['gaps'],'interpretation_policy':'Document interpretation is distinct from attested source text. No reference50 answers were used.'}
    graph=compile_overlay(refined);reader=IntegratedReader(graph)
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'graph.json').exists():raise RuntimeError('Graph already frozen; make a new version instead of overwriting')
    save(OUT/'refined_knowledge.json',refined);save(OUT/'graph.json',graph)
    save(HERE/'private/curation_decisions.json',ledger)
    atlas=read(ROOT/'experiments/analyses/source_workmap_20261102/private/atlas.json')
    reverse=collections.defaultdict(list)
    for r in rules:
        for old in r['legacy_ids']:reverse[old].append(r['id'])
    wholeledger=[{**x,'new_rule_ids':reverse[x['legacy_id']], 'this_stage_status':'partially_refined_link' if reverse[x['legacy_id']] else 'mapped_not_semantically_completed'} for x in atlas['legacy_items']]
    save(HERE/'private/legacy_item_ledger.json',wholeledger)
    packages=[]
    for p in atlas['work_packages']:
        selected=[r for r in rules if p['id'] in r['packages']]
        packages.append({'id':p['id'],'title':p['title'],'legacy_items':len(p['legacy_ids']),
            'new_rule_ids':[r['id'] for r in selected], 'deferred_candidate_ids':[r['id'] for r in ledger if r['decision']=='deferred' and p['id'] in r['packages']],
            'status':'部分 정제·통합 시험 대상' if selected else '원본 검색 가능 / 의미 정제 미완료','whole_package_complete':False})
    save(HERE/'coverage.json',{'packages':packages,'legacy_items':len(wholeledger),'legacy_items_with_new_refinement':sum(bool(x['new_rule_ids']) for x in wholeledger)})
    stats={'source_graph':{'nodes':1625,'edges':6167},'combined_candidate':{'nodes':len(graph['nodes']),'edges':len(graph['edges'])},
        'original_source_atoms_searchable':len(reader.legacy),'existing_rules':12,'new_rules':len(rules),'all_interpreted_rules':len(reader.rules),
        'new_rule_types':dict(collections.Counter(r.get('rule_type','conversion') for r in rules)),
        'new_unit_kinds':dict(collections.Counter(r['unit_kind'] for r in rules)),'source_quote_checks':sum(len(r['source_refs']) for r in rules),
        'new_module_rule_memberships':dict(collections.Counter(str(m) for r in rules for m in r['modules'])),
        'deferred_candidates':sum(r['decision']=='deferred' for r in ledger),'graph_sha256':sha((OUT/'graph.json').read_bytes()),
        'scope_note':'Counts describe candidate data and reachability; not whole grammar completion, naturalness, or quality gains.'}
    save(HERE/'statistics.json',stats);save(OUT/'statistics.json',stats)
    print(json.dumps(stats,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
