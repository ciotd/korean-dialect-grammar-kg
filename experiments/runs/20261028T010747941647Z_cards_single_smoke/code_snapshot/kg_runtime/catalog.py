"""Searchable research knowledge is distinct from executable transformations.

The original graph remains immutable. All node/edge IDs are retained; this is
a projection joined to live Neo4j results by ID, not a replacement database.
"""
from collections import Counter
from kg_pipeline.io import load_jsonl, read, save, sha

PROJECTION = 'kg_runtime_20261025'
DATASET = 'kg_v3_evidence_20261019_r2'
CONCEPT_TYPES = ('AnalysisConcept', 'GrammarFeature', 'Construction')

def build_search_projection(project):
    old = project/'knowledge/authored/kg_runtime_20261024'
    source = project/'knowledge/authored'/DATASET/'graph'
    out = project/'knowledge/authored'/PROJECTION
    if out.exists():
        raise ValueError('projection_already_exists')
    previous = read(old/'runtime.json')
    originals = load_jsonl(source/'nodes.jsonl')
    edges = load_jsonl(source/'edges.jsonl')
    executable = {r['id'] for r in previous['rules']}
    nodes, provenance, changes = [], {}, []
    for n in originals:
        p = n['properties']; s = p.get('original_spec', {})
        s = s if isinstance(s, dict) else {}
        # Preserve linguistic conditions separately from deployment/release gates.
        fields = {k:s[k] for k in ('unit','input','match','block','action','output','preserve',
                  'documentary_condition_before_normalization') if k in s}
        attrs = {k:p[k] for k in ('module','original_kind') if k in p}
        if n['type'] in CONCEPT_TYPES or n['type']=='SourceAtom':
            attrs.update(fields)
            attrs['searchable'] = True
            attrs['executable'] = n['id'] in executable
        nodes.append({'id':n['id'],'type':n['type'],'title':n['title'],'properties':attrs})
        refs = s.get('source_refs',s.get('_refs',[]))
        provenance[n['id']] = {'source_refs':refs,'source_profile':s.get('profile'),
            'time_scope':s.get('time_scope'),'evidence_tier':s.get('evidence_tier'),
            'epistemic_status':p.get('epistemic_status'),'semantic_review_status':p.get('semantic_review_status'),
            'source_span_ids':[e['target'] for e in edges if e['source']==n['id'] and e['relation']=='cites_source_span']}
        removed = sorted(set(s)-set(fields))
        changes.append({'id':n['id'],'kept_spec_fields':sorted(fields),'moved_out_of_execution_fields':removed,
                        'original_node_reference':DATASET+':'+n['id']})
    save(out/'runtime.json',{'dataset':DATASET,'projection':PROJECTION,'rules':previous['rules'],
         'nodes':nodes,'edges':previous['edges']})
    save(out/'provenance.json',provenance)
    save(out/'field_changes.json',changes)
    stats = {'nodes':len(nodes),'edges':len(edges),'modules':sum(n['type']=='Module' for n in nodes),
        'searchable_atoms':sum(n['type']=='SourceAtom' for n in nodes),'searchable_concepts':sum(n['type'] in CONCEPT_TYPES for n in nodes),
        'executable_rule_count':len(executable),'node_types':dict(Counter(n['type'] for n in nodes)),
        'original_graph_modified':False,'all_original_ids_preserved':True,
        'source_hashes':{f:sha((source/f).read_bytes()) for f in ('nodes.jsonl','edges.jsonl')},
        'previous_projection_sha256':sha((old/'runtime.json').read_bytes()),
        'policy':{'search':'No activation/profile/executable filter; exact-ID lookup covers every concept and atom.',
          'application':'Existing 17 explicit operators plus morphology and Qwen sentence-function selection.',
          'metadata':'Full original properties remain in the source graph. Provenance is a separate ID join.',
          'conditions':'Original match/block retained as declarative knowledge, not blindly executed as deployment gates.'}}
    save(out/'statistics.json',stats)
    return stats

def route_concepts(morph):
    """POS/ending routes specify search scope, not a syntactic truth assertion."""
    from .rules import seed_concepts
    ids = set(seed_concepts(morph))
    tagmap={'VV':'G_VERB_INFLECTION','VA':'G_ADJ_STATE','VCP':'G_ADJ_EXISTENCE',
            'VCN':'G_NEG_COPULA','NNG':'G_NP_HEAD','NNP':'G_NOUN_PROPER','NP':'G_PRON_PERSON',
            'NR':'G_NUMERAL_ROLE','JKS':'G_PARTICLE_SUBJECT','JKC':'G_PARTICLE_SUBJECT',
            'JKO':'G_PARTICLE_OBJECT','JKB':'G_CASE_ROLE','JKG':'G_PARTICLE_STACK',
            'JKV':'G_PARTICLE_VOCATIVE','JX':'G_PARTICLE_FOCUS','JC':'G_PARTICLE_COORD',
            'ETM':'G_CLAUSE_RELATIVE','ETN':'G_CLAUSE_NOMINAL','EP':'G_TAM_SLOTS',
            'VX':'G_AUX_ROLE','IC':'G_LEX_INTERJECTION'}
    for w in morph['words']:
        for form,tag in w['morphs']:
            tag=tag.split('-')[0]
            if tag in tagmap:ids.add(tagmap[tag])
            if tag=='EP' and form=='시':ids.add('G_HON_SUBJECT')
            if tag=='MAG' and form in ('안','못'):ids.add('G_NEG_SHORT')
            if tag=='EC' and form in ('다고','ᆫ다고','는다고','라고','자고'):ids.add('G_QUOTE_INDIRECT')
    return sorted(ids)
