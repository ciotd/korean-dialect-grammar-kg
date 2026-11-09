"""Exhaustive structural inventory, with frozen-record observations. No model calls."""
from pathlib import Path
from collections import Counter,defaultdict,deque
import csv,hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from kg_pipeline.integrated import IntegratedReader
from kg_pipeline.separated_graph import restore,digest
from kg_pipeline.multi_agent import meaning_contract
from kg_pipeline.kiwi_default import focused_contract
def read(p):return json.loads((ROOT/p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,x):
 p=BASE/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
def csvout(name,rows):
 p=BASE/'private'/name
 with p.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader()
  for row in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in row.items()})
ptr=read('knowledge/authored/semantic_grammar_20261107_separated_r1/latest.json')
g=read(ptr['graph']);archive=read(ptr['audit']);manifest=read(ptr['manifest'])
frozen={p:sha(ROOT/p) for p in [ptr['graph'],ptr['audit'],ptr['manifest'],'src/kg_pipeline/integrated.py','src/kg_pipeline/multi_agent.py','src/kg_pipeline/kiwi_default.py']}
nodes={n['id']:n for n in g['nodes']};edges=g['edges'];out=defaultdict(list);incoming=defaultdict(list);adj=defaultdict(set)
for e in edges:
 out[e['source']].append(e);incoming[e['target']].append(e);adj[e['source']].add(e['target']);adj[e['target']].add(e['source'])
def links(i,r):return [e for e in out[i] if e['relation']==r]
duplicates=lambda xs:[{'value':k,'count':v} for k,v in Counter(xs).items() if v>1]
issues=[]
def issue(kind,target,detail):issues.append({'kind':kind,'target':target,'detail':detail})
for x in duplicates(n['id'] for n in g['nodes']):issue('duplicate_node_id',x['value'],x['count'])
for x in duplicates(e['id'] for e in edges):issue('duplicate_edge_id',x['value'],x['count'])
dangling=[e['id'] for e in edges if e['source'] not in nodes or e['target'] not in nodes]
triples=defaultdict(list)
for e in edges:triples[(e['source'],e['relation'],e['target'])].append(e['id'])
dup_triples=[{'source':k[0],'relation':k[1],'target':k[2],'ids':v} for k,v in triples.items() if len(v)>1]
components=[];seen=set()
for i in nodes:
 if i in seen:continue
 todo=[i];component=[];seen.add(i)
 while todo:
  p=todo.pop();component.append(p)
  for j in adj[p]:
   if j in nodes and j not in seen:seen.add(j);todo.append(j)
 components.append(sorted(component))
components.sort(key=len,reverse=True)
isolated=[i for i in nodes if not adj[i]]
node_rows=[{'id':i,'type':n['type'],'title':n.get('title',n.get('properties',{}).get('title','')),'incoming':len(incoming[i]),'outgoing':len(out[i]),'isolated':not bool(adj[i]),'property_keys':list(n.get('properties',{})),'structure_checked':True,'meaning_verified_this_audit':False} for i,n in nodes.items()]
edge_rows=[{'id':e['id'],'source':e['source'],'relation':e['relation'],'target':e['target'],'source_type':nodes.get(e['source'],{}).get('type'),'target_type':nodes.get(e['target'],{}).get('type'),'endpoints_exist':e['source'] in nodes and e['target'] in nodes,'parallel_same_triple':len(triples[(e['source'],e['relation'],e['target'])])>1,'semantic_relation_verified':False} for e in edges]
expected={'ANY_BRANCH':('SemanticRule','ApplicabilityBranch'),'ALL':('ApplicabilityBranch','Condition'),'ACCEPTS':('Condition','FeatureValue'),'HAS_USAGE':('GrammarConstruction','SemanticRule'),'REALIZES':('SemanticRule','Realization'),'SUPPORTED_IN':('GrammarConstruction','ProcessingScope')}
type_errors=[e for e in edge_rows if e['relation'] in expected and (e['source_type'],e['target_type'])!=expected[e['relation']]]
restored=restore(g,archive);rn={n['id']:n for n in restored['nodes']};re_out=defaultdict(list)
for e in restored['edges']:re_out[e['source']].append(e)
restore_pass=digest(restored)==archive['source_canonical_sha256']
original_dir=ROOT/'knowledge/authored/kg_v3_evidence_20261019_r2/graph'
original={k:[json.loads(s) for s in (original_dir/(k+'.jsonl')).read_text(encoding='utf-8-sig').splitlines() if s.strip()] for k in ['nodes','edges']}
def census(graph):
 ids={n['id'] for n in graph['nodes']};degree=Counter(x for e in graph['edges'] for x in (e['source'],e['target']))
 return {'nodes':len(graph['nodes']),'edges':len(graph['edges']),'duplicate_node_ids':duplicates(n['id'] for n in graph['nodes']),'duplicate_edge_ids':duplicates(e['id'] for e in graph['edges']),'dangling':[e['id'] for e in graph['edges'] if e['source'] not in ids or e['target'] not in ids],'isolated':sorted(i for i in ids if degree[i]==0),'meaning_verified':False}
lineage={'original_evidence_graph':census(original),'restored_integrated_graph':census(restored),'original_jsonl_hashes_match_integrated_header':{k:sha(original_dir/(k+'.jsonl'))==restored.get('whole_sha256',{}).get(k) for k in ['nodes','edges']}}
reader=IntegratedReader(g)
packages=read('experiments/analyses/integrated_grammar_20261106/coverage_r2.json')['packages']
run=ROOT/'experiments/runs/20261109T030211818725Z_kiwi_default_regression'
observed_fields={'unit_kind','source_form','lemma','source_final','prefinal_type','prefinal_sequence','past_form','nominal_end','nominal_kind','morph_tag','ending_tag','root_tag'}
observed={i:{'considered':set(),'eligible':set(),'delivered':set(),'reported_used':set(),'form_compatible':set(),'unresolved':[],'false_features':Counter()} for i in reader.rules}
payload_notes=[];notes_regex=re.compile(r'D0[1-7]\s*p\d+|리드 판단|원문 확인 필요|실측|Kiwi로 결합')
for d in sorted((run/'private/records').iterdir()):
 rec=d.name.removesuffix('_kiwi_focused')
 if (d/'retrieval.json').exists():
  for unit in json.loads((d/'retrieval.json').read_text(encoding='utf8')):
   for state in ['eligible','unresolved','rejected']:
    for h in unit[state]:
     o=observed[h['rule_id']];o['considered'].add(rec)
     if state=='eligible':o['eligible'].add(rec)
     if state=='unresolved':o['unresolved'].append({'record':rec,'unit':unit['unit_id'],'missing_relations':h.get('missing_relations',[]),'unknown_features':sorted({c['feature'] for b in h['branches'] for c in b['checks'] if c['state']=='unknown'})})
     for b in h['branches']:
      o['false_features'].update(c['feature'] for c in b['checks'] if c['state']=='false')
      morphology_checks=[c for c in b['checks'] if c['feature'] in observed_fields]
      if morphology_checks and all(c['state']=='true' for c in morphology_checks):o['form_compatible'].add(rec)
 if (d/'selected_knowledge.json').exists():
  selected=json.loads((d/'selected_knowledge.json').read_text(encoding='utf8'));actionmap={a['action_id']:a['rule_id'] for a in selected}
  for a in selected:
   observed[a['rule_id']]['delivered'].add(rec)
   for key in a:
    text=json.dumps(a.get(key,''),ensure_ascii=False)
    if notes_regex.search(text):payload_notes.append({'record':rec,'rule_id':a['rule_id'],'field':key,'text':text})
  if (d/'writer/parsed.json').exists():
   parsed=json.loads((d/'writer/parsed.json').read_text(encoding='utf8'))
   for a in parsed.get('used_action_ids',[]):
    if a in actionmap:observed[actionmap[a]]['reported_used'].add(rec)
# Same real contract functions, with structural placeholder units only; not natural-language tests.
kinds=['predicate','nominal','particle','connector','construction']
units=[{'id':'AUDIT_'+k,'kind':k,'clause_key':'AUDIT_C1','word_id':'AUDIT_W1','related_word_ids':['AUDIT_W1'],'morphs':[],'text':'구조 검사 자리표시','span':[0,10],'observed':{}} for k in kinds]
schema=focused_contract(meaning_contract(reader,units),reader,units)
contract={v['properties']['unit_id']['enum'][0].removeprefix('AUDIT_'):v['properties']['features']['properties'] for v in schema['properties']['units']['items']['anyOf']}
header_diffs=[{'feature':k,'header_values':g.get('feature_schema',{}).get(k),'condition_values_missing_from_header':sorted(set(v)-set(g.get('feature_schema',{}).get(k,[])))} for k,v in reader.values.items() if k not in g.get('feature_schema',{}) or set(v)-set(g['feature_schema'][k])]
semantic_enums={k:v.get('semantic_function',{}).get('enum') for k,v in contract.items()}
rule_rows=[];branch_rows=[];feature_rows=[];memo_rows=[];provenance_rows=[]
for rid,r in reader.rules.items():
 p=r['node']['properties'];family=r['family']
 direct=[e['target'] for e in links(rid,'IN_MODULE')]
 familymodules=[e['target'] for e in links(family,'IN_MODULE')]
 refined=[e['target'] for e in links(rid,'REFINES')]
 refinedmodules=sorted({e['target'] for i in refined for e in out[i] if e['relation'] in ['in_module','IN_MODULE']})
 group_ids=[x['id'] for x in packages if rid in x['new_rule_ids']]
 forms=[nodes[e['target']]['properties'] for e in links(rid,'REALIZES')]
 direct_evidence=[e for e in re_out[rid] if e['relation']=='SUPPORTED_BY']
 # Precise direct documentary support only; contextual evidence is not silently promoted.
 evidence_ids=[e['target'] for e in direct_evidence];docs=sorted({rn[i]['properties'].get('document_id','') for i in evidence_ids})
 prov={'rule_id':rid,'direct_supported_by_ids':evidence_ids,'documents':docs,'original_property_evidence_fields':{k:v for k,v in rn[rid]['properties'].items() if k in ['primary_evidence_ids','supporting_evidence_ids','source_refs','evidence_ids']},'pdf_meaning_checked':False}
 provenance_rows.append(prov)
 if not direct:issue('no_direct_module_edge',rid,{'family_modules':familymodules,'refined_modules':refinedmodules})
 if len(forms)!=1:issue('realization_cardinality',rid,len(forms))
 if not direct_evidence:issue('no_direct_supported_by',rid,prov)
 for key,val in p.items():
  if isinstance(val,(str,list,dict)):
   text=json.dumps(val,ensure_ascii=False)
   if notes_regex.search(text):memo_rows.append({'rule_id':rid,'field':key,'text':text,'status':'pattern_candidate_not_automatic_error'})
 obs=observed[rid]
 rule_rows.append({'rule_id':rid,'title':p.get('title',''),'rule_type':p.get('rule_type','conversion'),'family':family,'direct_modules':direct,'family_modules':familymodules,'refinement_modules':refinedmodules,'additional44_package_membership':group_ids,'condition_branch_ids':[b['id'] for b in r['branches']],'required_relations':p.get('required_relations',[]),'forms':forms,'instruction':p.get('instruction',p.get('meaning',p.get('summary',''))),'preserve':p.get('preserve',[]),'limitations':p.get('limitations',p.get('limits',[])),'evidence_ids':evidence_ids,'record_counts':{k:len(obs[k]) for k in ['considered','eligible','delivered','reported_used','form_compatible']},'eligible_record_ids':sorted(obs['eligible']),'form_compatible_record_ids':sorted(obs['form_compatible']),'unresolved':obs['unresolved'],'mismatched_feature_occurrences':dict(obs['false_features']),'source_meaning_verified':False,'next_example_tests':['적용','비적용','미확정','다른 규칙과 결합']})
 rule_rows[-1].update(stored_limits=p.get('limits'),stored_limitations=p.get('limitations'),payload_limitations=p.get('limitations',''),normalized_limitations_is_not_actual_payload=True)
 for b in r['branches']:
  raw_conditions=[nodes[e['target']] for e in links(b['id'],'ALL')]
  checks=[]
  for c in raw_conditions:
   cp=c['properties'];accept=[nodes[e['target']]['properties'] for e in links(c['id'],'ACCEPTS')]
   mismatch=[v for v in accept if v['feature']!=cp['feature']]
   if mismatch:issue('feature_name_mismatch',c['id'],mismatch)
   checks.append({'id':c['id'],'feature':cp['feature'],'allowed':cp['allowed'],'operator':cp['operator'],'value_edges_match':set(v['value'] for v in accept)==set(cp['allowed']),'feature_names_match':not mismatch})
  branch_rows.append({'rule_id':rid,'branch_id':b['id'],'effective_conditions':b['conditions'],'direct_conditions':checks,'scope_inherited':len(links(family,'SUPPORTED_IN'))>0,'path_edge_ids':b['path_edge_ids'],'nonempty':all(b['conditions'].values()),'meaning_and_natural_input_test':'not_performed','example_test_plan':{'positive':'모든 조건을 만족하는 서로 다른 어휘 문장','negative':'핵심 조건 하나를 바꾼 최소대립 문장','unknown':'입력만으로 필수 조건을 확정할 수 없는 문장'}})
  for kind in b['conditions']['unit_kind']:
   for key,values in b['conditions'].items():
    declared=contract.get(kind,{}).get(key)
    origin='morph_observation' if key in observed_fields else 'meaning_question' if declared is not None else 'not_in_contract'
    absent=[] if origin=='morph_observation' else [v for v in values if declared is None or v not in declared.get('enum',[])]
    feature_rows.append({'rule_id':rid,'branch_id':b['id'],'unit_kind':kind,'feature':key,'allowed':values,'supplier':origin,'values_not_in_question':absent})
    if absent:issue('condition_not_representable_in_meaning_contract',rid,{'branch':b['id'],'feature':key,'values':absent})
relations=defaultdict(Counter)
for e in edge_rows:relations[e['relation']][(e['source_type'],e['target_type'])]+=1
rel_rows=[{'relation':r,'count':sum(c.values()),'type_pairs':[{'source_type':a,'target_type':b,'count':n} for (a,b),n in c.items()],'role':'runtime_condition_or_payload' if r in ['HAS_USAGE','SUPPORTED_IN','ANY_BRANCH','ALL','ACCEPTS','REALIZES'] else 'classification_or_reference_not_condition_gate'} for r,c in relations.items()]
noeligible=[r['rule_id'] for r in rule_rows if not r['record_counts']['eligible']]
# Structural equivalence candidates; condition sharing and parallel links need semantic review, not deletion.
signatures=defaultdict(list)
for r in rule_rows:
 sig=json.dumps([b['effective_conditions'] for b in branch_rows if b['rule_id']==r['rule_id']],sort_keys=True,ensure_ascii=False)
 signatures[sig].append(r['rule_id'])
same_conditions=[v for v in signatures.values() if len(v)>1]
summary={'scope':'전체 목록·구조 검사. 자연어 예문·Qwen 신규 실행 및 PDF 의미 검증 아님','graph':{'version':g['version'],'nodes':len(g['nodes']),'edges':len(edges),'node_types':dict(Counter(n['type'] for n in g['nodes']))},'lineage':lineage,'checks':{'duplicate_node_ids':duplicates(n['id'] for n in g['nodes']),'duplicate_edge_ids':duplicates(e['id'] for e in edges),'dangling_edges':dangling,'duplicate_relation_triples':len(dup_triples),'isolated_nodes':isolated,'weak_components':len(components),'component_sizes':[len(c) for c in components],'runtime_relation_type_errors':len(type_errors),'reader_compiles_all_rules':len(reader.rules),'branches':len(branch_rows),'restore_canonical_equal':restore_pass,'restored_nodes':len(restored['nodes']),'restored_edges':len(restored['edges']),'graph_file_matches_manifest':sha(ROOT/ptr['graph'])==manifest['graph_sha256']},'issue_counts':dict(Counter(i['kind'] for i in issues)),'same_effective_condition_groups':same_conditions,'mixed_note_pattern_rules':len({r['rule_id'] for r in memo_rows}),'mixed_note_pattern_delivered_rules':len({r['rule_id'] for r in payload_notes}),'no_eligible_observation_rules':noeligible,'frozen_hashes':frozen,'new_qwen_calls':0,'all_nodes_meaning_verified':False,'all_pdf_evidence_verified':False}
probe_ptr=read('experiments/analyses/semantic_reachability_20261107/latest.json')
probes=read(str(Path(probe_ptr['directory'])/'natural_probes.json'))
example_plan=[{'rule_id':b['rule_id'],'branch_id':b['branch_id'],'conditions':b['effective_conditions'],'existing_rule_level_probe_candidates':[{'case_id':p['case_id'],'text':p['text'],'target':p['target']} for p in probes if p['rule_id']==b['rule_id']],'probe_branch_binding_verified':False,'next_tests':b['example_test_plan'],'new_model_test_performed':False} for b in branch_rows]
save('private/example_test_plan.json',example_plan)
special_fields=[]
for r in rule_rows:
 p=nodes[r['rule_id']]['properties']
 for k in ['limits','target','generation_operation']:
  if k in p:special_fields.append({'rule_id':r['rule_id'],'node_id':r['rule_id'],'field':k,'value':p[k],'directly_selected_by_payload':False,'semantic_loss_confirmed':False})
 for e in links(r['rule_id'],'REALIZES'):
  fp=nodes[e['target']]['properties']
  for k in ['unit','surface_postcondition','operation']:
   if k in fp:special_fields.append({'rule_id':r['rule_id'],'node_id':e['target'],'field':k,'value':fp[k],'directly_selected_by_payload':False,'semantic_loss_confirmed':False})
comment_rules=[r['rule_id'] for r in rule_rows if '조건 보완' in str(r['limitations'])]
comment_delivered=[i for i in comment_rules if observed[i]['delivered']]
sources={'source_atoms_total':sum(n['type']=='SourceAtom' for n in rn.values()),'source_atoms_with_span_links':sum(n['type']=='SourceAtom' and any(e['relation']=='cites_source_span' for e in re_out[n['id']]) for n in rn.values()),'rules_with_direct_evidence':sum(bool(p['direct_supported_by_ids']) for p in provenance_rows),'pdf_semantic_check':False}
save('private/interface_findings.json',{'feature_header_differences':header_diffs,'semantic_function_enums_by_unit':semantic_enums,'properties_not_directly_selected_by_payload':special_fields,'property_omission_counts':dict(Counter(r['field'] for r in special_fields)),'review_comment_marker_rules':comment_rules,'review_comment_marker_delivered_rules':comment_delivered,'source_links':sources})
save('private/audit.json',{'summary':summary,'nodes':node_rows,'edges':edge_rows,'relations':rel_rows,'rules':rule_rows,'branches':branch_rows,'feature_contracts':feature_rows,'issues':issues,'duplicate_triples':dup_triples,'components':components,'type_errors':type_errors,'provenance':provenance_rows,'mixed_note_candidates':memo_rows,'delivered_mixed_note_candidates':payload_notes,'work_packages':packages,'earlier_rules_without_package_mapping':[r['rule_id'] for r in rule_rows if not r['additional44_package_membership']]})
save('summary.json',summary)
for name,rows in [('nodes.csv',node_rows),('edges.csv',edge_rows),('rules.csv',rule_rows),('branches.csv',branch_rows),('feature_contracts.csv',feature_rows)]:csvout(name,rows)
assert all(sha(ROOT/p)==h for p,h in frozen.items()),'Inspected inputs changed during audit'
print(json.dumps(summary,ensure_ascii=False,indent=2))
