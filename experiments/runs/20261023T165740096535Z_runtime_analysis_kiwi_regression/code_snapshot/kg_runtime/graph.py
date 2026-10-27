import collections
import json
import re
from pathlib import Path
from kg_pipeline.io import load_jsonl,save,sha,dumps
from .rules import RULES,forms_for,seed_concepts

DATASET='kg_v3_evidence_20261019_r2'
QUERY='''MATCH (c:KGNode)-[cm:in_module]->(m:KGNode)<-[rm:in_module]-(r:KGNode)
WHERE c.dataset_id=$dataset AND c.id IN $concepts AND r.dataset_id=$dataset AND r.id IN $rules
RETURN c.id AS concept_id,r.id AS rule_id,[cm.id,rm.id] AS edge_ids,m.id AS via
UNION
MATCH(c:KGNode)<-[ic:interpreted_as]-(cl:KGNode)-[da:documents_atom]->(r:KGNode)
WHERE c.dataset_id=$dataset AND c.id IN $concepts AND r.dataset_id=$dataset AND r.id IN $rules
RETURN c.id AS concept_id,r.id AS rule_id,[ic.id,da.id] AS edge_ids,cl.id AS via'''

def build(project,source_texts):
    original=project/'knowledge/authored'/DATASET
    out=project/'knowledge/authored/kg_runtime_20261024'
    if out.exists():raise ValueError('runtime_projection_already_exists; create a new version instead')
    ns=load_jsonl(original/'graph/nodes.jsonl');es=load_jsonl(original/'graph/edges.jsonl');by={n['id']:n for n in ns}
    manifest=json.loads((source_texts/'manifest.json').read_text(encoding='utf-8'));source_versions=[]
    for doc in manifest:
        actual=sha(Path(doc['file']).read_bytes())
        if actual!=doc['sha256']:raise ValueError('source_PDF_changed:'+doc['id'])
        source_versions.append({'id':doc['id'],'pdf_sha256':actual,'extracted_text_sha256':sha((source_texts/(doc['id']+'.txt')).read_bytes())})
    sources=[];compiled=[];ledger=[]
    for rid,(op,condition,refs) in RULES.items():
        if rid not in by or by[rid]['type']!='SourceAtom':raise ValueError('unknown_source_atom:'+rid)
        spans=[]
        for doc,page in refs:
            text=(source_texts/(doc+'.txt')).read_text(encoding='utf-8')
            match=re.search(r'=== PDF PAGE '+str(page)+r' ===\s*(.*?)(?==== PDF PAGE|\Z)',text,re.S)
            if not match or not match.group(1).strip():raise ValueError('missing_source_page:'+doc+':'+str(page))
            span={'doc':doc,'pdf_page':page,'text_sha256':sha(match.group(1).encode()),'text':match.group(1)}
            spans.append({k:v for k,v in span.items() if k!='text'});sources.append(span)
        compiled.append({'id':rid,'operation':op,'condition':condition,'title':by[rid]['title'],
                         'source_refs':spans,'interpretation':'builder_implemented_mapping_and_surface_composition',
                         'code':'src/kg_runtime/rules.py:forms_for'})
    projected=[]
    for n in ns:
        props=n['properties'];spec=props.get('original_spec',{});spec=spec if isinstance(spec,dict) else {}
        runtime=next((r for r in compiled if r['id']==n['id']),None)
        attrs={k:v for k,v in {'module':props.get('module'),'kind':props.get('original_kind'),
               'forms':spec.get('output',{}).get('forms') if isinstance(spec.get('output'),dict) else None}.items() if v is not None}
        if runtime:attrs.update(operation=runtime['operation'],condition=runtime['condition'],implementation_status='executable_candidate')
        projected.append({'id':n['id'],'type':n['type'],'title':n['title'],'properties':attrs})
        if n['type']=='SourceAtom':
            kind=props.get('original_kind');forms=attrs.get('forms',[])
            reason='implemented_with_explicit_input_operator' if runtime else ('classification_or_observation_not_a_substitution' if kind in ('classification','observation') else 'form_inventory_needs_input_alignment_and_composition' if kind=='realization_inventory' else 'no_output_form_or_preservation_constraint' if not forms else 'operator_not_implemented; lexical/function/allomorph conditions require explicit mapping')
            ledger.append({'id':n['id'],'title':n['title'],'module':props.get('module'),'kind':kind,'status':'implemented' if runtime else 'not_executable','reason':reason,
              'documentary_conditions':spec.get('documentary_condition_before_normalization'),
              'input':spec.get('input'),'match':spec.get('match'),'block':spec.get('block'),'action':spec.get('action'),
              'source_refs':spec.get('source_refs',spec.get('_refs',[])),'forms':forms,
              'links':[{'relation':e['relation'],'target':e['target']} for e in es if e['source']==n['id'] and e['relation']!='cites_source_span'],
              'missing_implementation':None if runtime else {'input_matcher':True,'surface_composer':True,'positive_negative_tests':True}})
    edges=[{k:e[k] for k in ('id','source','relation','target')} for e in es]
    save(out/'runtime.json',{'dataset':DATASET,'rules':compiled,'nodes':projected,'edges':edges})
    save(out/'private/source_pages.json',sources);save(out/'coverage_ledger.json',ledger);save(out/'source_versions.json',source_versions)
    stats={'source_nodes':len(ns),'projected_nodes':len(projected),'source_edges':len(es),'projected_edges':len(edges),
      'modules':sum(n['type']=='Module' for n in ns),'source_atom_kinds':dict(collections.Counter(n['properties'].get('original_kind') for n in ns if n['type']=='SourceAtom')),
      'implemented_rule_ids':[x['id'] for x in compiled],'implemented_rules':len(compiled),
      'source_node_property_fields':sum(len(n['properties']) for n in ns),'projected_node_property_fields':sum(len(n['properties']) for n in projected),
      'source_graph_json_bytes':sum((original/'graph'/x).stat().st_size for x in ('nodes.jsonl','edges.jsonl')),
      'runtime_json_bytes':(out/'runtime.json').stat().st_size,'source_hashes':{x:sha((original/'graph'/x).read_bytes()) for x in ('nodes.jsonl','edges.jsonl')},
      'original_graph_modified':False,'note':'All IDs/edges preserved; only execution fields projected. Source text/profiles remain in research KG and sidecars.'}
    save(out/'statistics.json',stats);return stats

class GraphTool:
    def __init__(self,project,neo):
        self.neo=neo;self.project=project
        self.runtime=json.loads((project/'knowledge/authored/kg_runtime_20261024/runtime.json').read_text(encoding='utf-8'))
        self.by={n['id']:n for n in self.runtime['nodes']};self.rules={r['id']:r for r in self.runtime['rules']}
        self.edgeids={e['id'] for e in self.runtime['edges']}
    def retrieve(self,morph,analyzer,concepts=None):
        concepts=concepts if concepts is not None else seed_concepts(morph)
        if any(x not in self.by or self.by[x]['type'] not in ('AnalysisConcept','GrammarFeature','Construction') for x in concepts):raise ValueError('invalid_existing_concept')
        rows=self.neo.query(QUERY,{'dataset':DATASET,'concepts':concepts,'rules':list(self.rules)})
        if any(x not in self.edgeids for row in rows for x in row['edge_ids']):raise ValueError('query_returned_non_snapshot_edge')
        candidates=[];byrule=collections.defaultdict(list)
        for row in rows:byrule[row['rule_id']].append(row)
        for rid,paths in sorted(byrule.items()):
            rule=self.rules[rid]
            preferred={'question_na':'G_Q_POLAR','question_no':'G_Q_WH','copula_ga':'G_Q_POLAR','copula_go':'G_Q_WH',
                       'copula_tam':'G_Q_SCOPE','condition_mo':'G_END_CONDITIONAL','cause_aga':'G_END_CAUSE',
                       'quotation_kko':'G_CLAUSE_LINK','many':'G_LEX_SENSE','little':'G_LEX_SENSE','barely':'G_LEX_SENSE'}.get(rule['operation'],'G_END_FINAL')
            paths=sorted(paths,key=lambda x:(x['concept_id']!=preferred,x['concept_id']!='G_END_FINAL',x['via'].startswith('M'),x['concept_id']))
            for w in morph['words']:
                alternatives=forms_for(rid,w,morph,analyzer)
                for index,after in enumerate(alternatives):
                    candidates.append({'candidate_id':rid+':'+w['uid']+':'+str(index),'rule_id':rid,'target_uid':w['uid'],
                      'span':[w['start'],w['end']],'before':w['surface'],'after':after,'condition':rule['condition'],
                      'operation':rule['operation'],'source_refs':[{'doc':r['doc'],'page':r['pdf_page']} for r in rule['source_refs']],
                      'path':paths[0],'path_role':'retrieval_scope_only; application requires morphology and sentence_function checks',
                      'surface_origin':'implementation_composition_not_source_quote'})
        return {'concept_ids':concepts,'query':QUERY,'query_parameters':{'dataset':DATASET,'concepts':concepts,'rules':list(self.rules)},
                'paths':rows,'candidates':candidates,'kg_query_count':1}

def compact_candidates(result):
    return [{'id':c['candidate_id'],'word':c['target_uid'],'from':c['before'],'to':c['after'],
             'when':c['condition'],'source':c['source_refs']} for c in result['candidates']]

def make_plan(selected,retrieval,text):
    by={c['candidate_id']:c for c in retrieval['candidates']};edits=[]
    if len(selected)!=len(set(selected)):raise ValueError('duplicate_candidate_selection')
    for key in selected:
        if key not in by:raise ValueError('unknown_candidate:'+key)
        c=by[key]
        if text[slice(*c['span'])]!=c['before']:raise ValueError('source_binding_changed')
        edits.append(c)
    edits.sort(key=lambda e:e['span'][0])
    if any(x['span'][1]>y['span'][0] for x,y in zip(edits,edits[1:])):raise ValueError('overlapping_rule_conflict')
    cursor=0;preserved=[]
    for e in edits:
        if cursor<e['span'][0]:preserved.append([cursor,e['span'][0]])
        cursor=e['span'][1]
    if cursor<len(text):preserved.append([cursor,len(text)])
    return {'edits':edits,'apply_order':'descending_source_offset','preserved_spans':preserved,
            'conflict_policy':'one selected candidate per overlapping original range; agent resolves or omits'}

def apply_plan(text,plan):
    for e in reversed(plan['edits']):text=text[:e['span'][0]]+e['after']+text[e['span'][1]:]
    return text
