"""Compact data-driven grammar cards, joined to unchanged Neo4j IDs.

This projection is a model-readable grammar, not 721 certified string rules.
The 17 legacy Python operators are deliberately absent from the execution path.
"""
import re
from collections import Counter, defaultdict
from kg_pipeline.io import load_jsonl, read, save, sha, dumps
from .catalog import DATASET, CONCEPT_TYPES, route_concepts
from .graph import QUERY

VERSION = 'kg_cards_20261028_v1'
# Deployment metadata is moved to the provenance sidecar, not interpreted as grammar.
META_KEYS = {'profile', 'profile_id', 'mapping_status', 'source_profile', 'scope_profile',
    'activation_state', 'runtime_active', 'source_membership'}
META_BLOCKS = {'required_condition_unknown', 'profile_not_selected', 'source_conflict_unresolved',
    'semantic_preservation_failed', 'target_register_level_unknown_or_incompatible',
    'no_approved_source_to_target_register_mapping'}

def grammar_only(value):
    if isinstance(value, dict):
        return {k: grammar_only(v) for k,v in value.items() if k not in META_KEYS}
    if isinstance(value, list):
        return [grammar_only(v) for v in value if not isinstance(v,str) or v not in META_BLOCKS]
    return value

def build_cards(project):
    source=project/'knowledge/authored'/DATASET/'graph'
    nodes=load_jsonl(source/'nodes.jsonl'); edges=load_jsonl(source/'edges.jsonl')
    membership={e['source']:e['target'] for e in edges if e['relation']=='in_module'}
    cards=[]; provenance={}
    for n in nodes:
        if n['type']!='SourceAtom':continue
        p=n['properties']; s=p.get('original_spec',{}); output=s.get('output',{})
        forms=output.get('forms',[]) if isinstance(output,dict) else []
        conditions=grammar_only(s.get('documentary_condition_before_normalization',s.get('match',{})))
        constraints=grammar_only(s.get('block',[]))
        # Keep both original linguistic interpretations if the normalization added distinctions.
        normalized=grammar_only(s.get('match',{}))
        if normalized and normalized!=conditions: conditions={'documentary':conditions,'normalized':normalized}
        c={'id':n['id'],'module':membership.get(n['id']),'kind':p.get('original_kind'),
           'title':n['title'],'when':conditions,'forms':forms,'avoid':constraints}
        cards.append(c)
        provenance[n['id']]={'source_refs':s.get('source_refs',s.get('_refs',[])),
            'original_node_sha256':sha(dumps(n).encode()),'original_spec':s,
            'interpretation_status':p.get('epistemic_status'),'review_status':p.get('semantic_review_status')}
    concepts=[{'id':n['id'],'title':n['title'],'module':membership.get(n['id'])} for n in nodes if n['type'] in CONCEPT_TYPES]
    result={'version':VERSION,'source_dataset':DATASET,'cards':cards,'concepts':concepts,
        'modules':[{'id':n['id'],'title':n['title']} for n in nodes if n['type']=='Module']}
    out=project/'knowledge/authored'/VERSION
    if out.exists():
        if read(out/'cards.json')!=result:raise ValueError('immutable_card_version_changed')
        return result
    save(out/'cards.json',result);save(out/'provenance.json',provenance)
    save(out/'statistics.json',{'card_count':len(cards),'kinds':dict(Counter(c['kind'] for c in cards)),
        'with_forms':sum(bool(c['forms']) for c in cards),'concept_count':len(concepts),'modules':len(result['modules']),
        'card_bytes':len(dumps(cards).encode()),'original_atom_bytes':len(dumps([n for n in nodes if n['type']=='SourceAtom']).encode()),
        'per_rule_python_operators':0,'all_cards_retrievable':True,'neo4j_original_unchanged':True,
        'source_hashes':{f:sha((source/f).read_bytes()) for f in ('nodes.jsonl','edges.jsonl')}})
    return result

FUNCTION_TERMS={
 'declarative':['declarative','assert','서술','평서'], 'polar_question':['interrogative','polar','판정','의문'],
 'wh_question':['interrogative','wh_question','설명 의문'], 'request':['imperative','명령','요청'],
 'propositive':['hortative','propositive','청유'], 'prohibition':['prohibition','금지','말다'],
 'conditional':['conditional','condition','조건'], 'causal':['causal','cause','원인','이유'],
 'quotation':['quotation','quote','인용'], 'intention':['intention','promise','의도','약속'],
 'conjecture':['conjecture','추측','추정'], 'retrospective':['retrospective','회상','더+'],
 'negation':['negation','negative','부정'], 'relative':['adnominal','relative','관형'],
 'progressive':['progressive','진행','보조'], 'contrast':['contrast','대조','양보'],
 'particle':['particle','case','조사'], 'other':[]}

def select_cards(cards,analysis,morph,limit=48):
    """Generic rank + per-function diversity. No rule-ID allowlist or gold answers."""
    active={f for u in analysis['units'] for f in u['functions']}
    sourceforms={x[0] for w in morph['words'] for x in w['morphs'] if len(x[0])>1}
    scores=[]
    for c in cards:
        text=dumps([c['title'],c['when']]).lower()
        fs={f:sum(3 for term in FUNCTION_TERMS[f] if term.lower() in text) for f in active}
        score=sum(fs.values())+sum(2 for x in sourceforms if x in c['title'])
        if c['kind']=='design_rule':score+=2
        if not c['forms']:score-=4
        scores.append((score,c['id'],fs,c))
    scores.sort(key=lambda x:(-x[0],x[1])); selected={}
    # Prevent a common function from crowding out intention/negation in a long input.
    for f in sorted(active):
        group=sorted((x for x in scores if x[2].get(f,0)>0),key=lambda x:(-x[2][f],-x[0],x[1]))
        for x in group[:3]:selected[x[1]]=x[3]
    for x in scores:
        if len(selected)>=limit:break
        selected.setdefault(x[1],x[3])
    # Deterministic cap; diverse first, then rank.
    chosen=list(selected.values())[:limit]
    return chosen,[{'id':i,'score':s,'selected':i in {c['id'] for c in chosen},'function_scores':fs} for s,i,fs,c in scores]

class CardGraph:
    def __init__(self,project,neo):
        self.data=build_cards(project);self.neo=neo
        self.by={c['id']:c for c in self.data['cards']};self.concepts={c['id']:c for c in self.data['concepts']}
        self.edges={e['id'] for e in load_jsonl(project/'knowledge/authored'/DATASET/'graph/edges.jsonl')}
    def retrieve(self,morph,analysis):
        requested={c for u in analysis['units'] for c in u['concept_ids']}
        if not requested<=self.concepts.keys():raise ValueError('unknown_concept_id')
        concepts=sorted((requested|set(route_concepts(morph))) & self.concepts.keys())
        modules=sorted({self.concepts[c]['module'] for c in concepts if self.concepts[c]['module']})
        params={'dataset':DATASET,'concepts':concepts,'modules':modules}
        rows=self.neo.query(QUERY,params)
        if any(r['rule_id'] not in self.by or not set(r['edge_ids'])<=self.edges for r in rows):raise ValueError('live_graph_snapshot_mismatch')
        cards=[self.by[i] for i in sorted({r['rule_id'] for r in rows})]
        chosen,rank=select_cards(cards,analysis,morph)
        return {'query':QUERY,'query_parameters':params,'paths':rows,'concept_ids':concepts,
            'retrieved_ids':[c['id'] for c in cards],'cards':chosen,'ranking':rank,
            'selection':'function diversity + linguistic term rank; top48; no execution-ID allowlist'}
