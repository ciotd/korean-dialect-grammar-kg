"""Versioned semantic graph compiler and clause-bound retrieval. No model calls.

Rule bodies are data. ALL edges form conjunctions; ANY_BRANCH forms alternatives.
Missing/ambiguous values yield unresolved candidates, never silent acceptance.
"""
import collections, hashlib, json

def stable(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:20]

def compile_graph(spec, inherited):
    nodes={};edges=[]
    def node(key,kind,**p):
        value={'id':key,'type':kind,'properties':p}
        if key in nodes and nodes[key]!=value:raise ValueError('conflicting_node:'+key)
        nodes[key]=value;return key
    def edge(a,rel,b):
        value={'id':'E_'+stable([a,rel,b]),'source':a,'relation':rel,'target':b}
        if value not in edges:edges.append(value)
    def old(key):
        if key not in inherited:raise ValueError('unknown_inherited_id:'+key)
        n=inherited[key]
        node(key,n['type'],title=n['title'],origin='inherited_identity_only')
    old('COMMON_SPINE')
    for key,n in inherited.items():
        if n['type']=='Module':old(key);edge('COMMON_SPINE','HAS_MODULE',key)
    family=node(spec['construction']['id'],'GrammarConstruction',**spec['construction']['properties'])
    edge(family,'IN_MODULE','M05')
    for evid,e in spec['evidence'].items():node(evid,'Evidence',**e)
    policy=node('SCOPE_'+stable(spec['support_scope']),'ProcessingScope',allowed=spec['support_scope'],basis='implementation_scope_not_linguistic_prohibition')
    edge(family,'SUPPORTED_IN',policy)
    for r in spec['rules']:
        rid=r['id'];node(rid,'SemanticRule',title=r['title'],summary=r['summary'],preserve=r['preserve'],target=r['target'],limits=r['limits'],status='source_interpreted_candidate')
        edge(family,'HAS_USAGE',rid)
        for mod in r['modules']:old(mod);edge(rid,'IN_MODULE',mod)
        for cid in r['concept_ids']:old(cid);edge(cid,'DESCRIBES_USAGE',rid)
        for aid in r['legacy_atom_ids']:old(aid);edge(rid,'REFINES',aid)
        for i,branch in enumerate(r['any_branches']):
            bid=node(rid+'/branch/'+str(i),'ApplicabilityBranch',scope='same_clause')
            edge(rid,'ANY_BRANCH',bid)
            for key,allowed in branch.items():
                basis=spec['condition_basis'][key]
                cid=node('COND_'+stable([key,sorted(allowed)]),'Condition',feature=key,allowed=sorted(allowed),operator='in',basis=basis['kind'])
                edge(bid,'ALL',cid)
                for eid in basis.get('evidence_ids',[]):edge(cid,'SUPPORTED_BY',eid)
                for value in allowed:
                    fid=node('FEATURE_'+stable([key,value]),'FeatureValue',feature=key,value=value)
                    edge(cid,'ACCEPTS',fid)
                    for concept in spec['feature_concepts'].get(key,[]):old(concept);edge(fid,'DEFINED_BY',concept)
        for form in r['forms']:
            fid=node('FORM_'+stable(form),'Realization',**form);edge(rid,'REALIZES',fid)
        for evid in r['evidence_ids']:
            e=spec['evidence'][evid];node(evid,'Evidence',**e);edge(rid,'SUPPORTED_BY',evid)
    for evid in ['EV_Q_VARIANT']:
        node(evid,'Evidence',**spec['evidence'][evid]);edge(family,'HAS_RECORDED_VARIANT',evid)
    # Preserve schema navigation without using module membership as eligibility.
    for e in edges:
        if e['source'] not in nodes or e['target'] not in nodes:raise ValueError('dangling_edge')
    return {'version':spec['version'],'feature_schema':spec['feature_schema'],'nodes':list(nodes.values()),'edges':edges}

class GraphReader:
    def __init__(self, graph):
        self.graph=graph;self.nodes={n['id']:n for n in graph['nodes']}
        self.out=collections.defaultdict(list);self.inc=collections.defaultdict(list)
        for e in graph['edges']:self.out[e['source']].append(e);self.inc[e['target']].append(e)
        self.conditions=[n for n in graph['nodes'] if n['type']=='Condition']
        self.feature_index={(n['properties']['feature'],n['properties']['value']):n['id'] for n in graph['nodes'] if n['type']=='FeatureValue'}
        self.graph_hash=stable(graph)
        self.policies=[n for n in graph['nodes'] if n['type']=='ProcessingScope']
    def validate(self,analysis):
        text=analysis['text'];seen=set()
        for c in analysis['clauses']:
            a,b=c['span'];t,u=c['target_span']
            if not(0<=a<=t<u<=b<=len(text)):raise ValueError('invalid_clause_or_target_span')
            if c['target_text']!=text[t:u]:raise ValueError('target_text_mismatch')
            for oid in [c['id'],c['predicate']['id'],c['ending_slot']['id']]:
                if oid in seen:raise ValueError('duplicate_instance_id')
                seen.add(oid)
            p=c['predicate'];slot=c['ending_slot']
            if p['clause_id']!=c['id'] or p['span']!=c['target_span'] or p['surface']!=c['target_text']:raise ValueError('predicate_binding_mismatch')
            if slot['predicate_id']!=p['id'] or slot['clause_id']!=c['id']:raise ValueError('ending_binding_mismatch')
            for k,v in c['features'].items():
                if k not in self.graph['feature_schema']:raise ValueError('unknown_feature:'+k)
                vals=v if isinstance(v,list) else [v]
                if any(x is not None and (not isinstance(x,str) or x not in self.graph['feature_schema'][k]) for x in vals):raise ValueError('invalid_feature_value:'+k)
                binding=c['feature_bindings'].get(k)
                if not binding or binding['clause_id']!=c['id'] or not binding.get('origin'):raise ValueError('feature_binding_mismatch:'+k)
                if k in ('predicate_class','prefinal_type','subject_honorific') and binding.get('predicate_id')!=p['id']:raise ValueError('feature_predicate_mismatch:'+k)
            if c['features'].get('question_kind')=='wh':
                w=c.get('question_variable')
                if not w or w['scope_clause_id']!=c['id'] or w['clause_id']!=c['id'] or w['role']!='asked_information':raise ValueError('question_scope_mismatch')
                x,y=w['span']
                if not(a<=x<y<=b) or text[x:y]!=w['surface']:raise ValueError('question_span_mismatch')
    def links(self,key,rel):return [e for e in self.out[key] if e['relation']==rel]
    def query(self, analysis):
        self.validate(analysis)
        text=analysis['text'];results=[];ids=set()
        for clause in analysis['clauses']:
            if clause['id'] in ids:raise ValueError('duplicate_clause_id')
            ids.add(clause['id'])
            a,b=clause['span'];t,u=clause['target_span']
            if not (0<=a<=t<u<=b<=len(text)):raise ValueError('invalid_clause_or_target_span')
            if clause.get('target_text')!=text[t:u]:raise ValueError('target_text_mismatch')
            features=clause['features'];states={};condition_trace={};accepted={}
            for key,value in features.items():
                if not isinstance(value,str):continue
                fid=self.feature_index.get((key,value))
                if fid:
                    for e in self.inc[fid]:
                        if e['relation']=='ACCEPTS':accepted[e['source']]=(fid,e['id'])
            # Feature-value edges are the actual lookup entry; each distinct
            # condition is evaluated once per clause, not once per morpheme.
            for n in self.conditions:
                p=n['properties'];v=features.get(p['feature'])
                if v is None or isinstance(v,list):state='unknown'
                elif not isinstance(v,str):raise ValueError('feature_value_must_be_string_or_unknown')
                else:state='true' if n['id'] in accepted else 'false'
                states[n['id']]=state
                fid=self.feature_index.get((p['feature'],v)) if isinstance(v,str) else None
                condition_trace[n['id']]={'feature':p['feature'],'observed':v,'allowed':p['allowed'],'state':state,'feature_node':fid,'entry_edge_id':accepted.get(n['id'],(None,None))[1]}
            by_rule=collections.defaultdict(list)
            for bid,n in self.nodes.items():
                if n['type']!='ApplicabilityBranch':continue
                checks=self.links(bid,'ALL');ss=[states[e['target']] for e in checks]
                state='false' if 'false' in ss else 'unknown' if 'unknown' in ss else 'true'
                owner=[e for e in self.inc[bid] if e['relation']=='ANY_BRANCH']
                if len(owner)!=1 or not checks:raise ValueError('invalid_branch')
                by_rule[owner[0]['source']].append({'branch':bid,'state':state,'conditions':[condition_trace[e['target']] for e in checks],'edge_ids':[owner[0]['id']]+[e['id'] for e in checks]})
            policy_failures=[];policy_missing=[]
            for policy in self.policies:
                for key,vals in policy['properties']['allowed'].items():
                    v=features.get(key)
                    if v is None or isinstance(v,list):policy_missing.append(key)
                    elif v not in vals:policy_failures.append({'feature':key,'observed':v,'supported':vals})
            eligible=[];unresolved=[];rejected=[];outside=[]
            for rid,branches in by_rule.items():
                true=[b for b in branches if b['state']=='true'];unknown=[b for b in branches if b['state']=='unknown']
                state='eligible' if true else 'unresolved' if unknown else 'not_matching_usage'
                if policy_failures:state='out_of_slice'
                elif policy_missing and state=='eligible':state='unresolved'
                chosen=true or unknown or branches
                item={'rule_id':rid,'state':state,'branches':chosen,'realization_edges':self.links(rid,'REALIZES'),'evidence_edges':self.links(rid,'SUPPORTED_BY')}
                {'eligible':eligible,'unresolved':unresolved,'not_matching_usage':rejected,'out_of_slice':outside}[state].append(item)
            results.append({'clause_id':clause['id'],'target_span':clause['target_span'],'target_text':clause['target_text'],'eligible':eligible,'unresolved':unresolved,'not_matching_usage':rejected,'out_of_slice':outside,'scope_failures':policy_failures,'scope_unknown':policy_missing,'analysis_conflicts':[k for k,v in features.items() if isinstance(v,list)]})
        return {'graph_version':self.graph['version'],'graph_hash':self.graph_hash,'analysis_hash':stable(analysis),'analysis_origin':analysis['origin'],'clauses':results}
    def packet(self,analysis,retrieval):
        if retrieval.get('analysis_hash')!=stable(analysis):raise ValueError('stale_analysis_result')
        if retrieval.get('graph_hash')!=self.graph_hash:raise ValueError('stale_graph_result')
        self.validate(analysis)
        clauses=[]
        by={c['id']:c for c in analysis['clauses']}
        for result in retrieval['clauses']:
            c=by[result['clause_id']];choices=[]
            for item in result['eligible']:
                r=self.nodes[item['rule_id']]['properties']
                evidence=[{'id':e['target'],**{k:self.nodes[e['target']]['properties'][k] for k in ['builder_paraphrase','evidence_kind','source_scope']}} for e in item['evidence_edges']]
                choices.append({'rule_id':item['rule_id'],'meaning':r['summary'],'forms':[self.nodes[e['target']]['properties'] for e in item['realization_edges']],'why':[x for b in item['branches'] for x in b['conditions']],'preserve':r['preserve'],'evidence_ids':[e['target'] for e in item['evidence_edges']],'evidence_summary':evidence,'limits':r['limits']})
            clauses.append({'clause_id':c['id'],'predicate_id':c['predicate']['id'],'ending_slot':c['ending_slot'],'target_span':c['target_span'],'target_text':c['target_text'],'analysis':c['features'],'morphology':c.get('morphology'),'choices':choices,'scope_failures':result['scope_failures'],'scope_unknown':result['scope_unknown'],'needs_analysis':[{'rule_id':i['rule_id'],'missing_features':sorted({x['feature'] for b in i['branches'] for x in b['conditions'] if x['state']=='unknown'})} for i in result['unresolved']]})
        return {'graph_version':self.graph['version'],'text':analysis['text'],'instruction':'같은 절의 조건을 만족한 choices만 해당 서술어의 종결 구성에 적용한다. 어간·시제·논항·높임·질문의 뜻은 유지한다. 완성형을 단순 문자열 덧붙이기로 만들지 말고 활용을 조합한다. choices가 없거나 해석이 미확정이면 확인할 사항을 반환한다.','clauses':clauses}
