"""Reuse frozen graph reader; bridge model word IDs with actual Kiwi positions."""
import copy,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'local/python'),str(ROOT/'experiments/analyses/question_refinement_20261102')]
from query import Reader
from kg_pipeline.io import read
from kg_runtime.morphology import compact_morph
GRAPH=ROOT/'knowledge/authored/semantic_questions_20261102_r3/private/graph.json'

def projected(word):
 parts=word['morphs'];hosts=[(i,f,t.split('-')[0]) for i,(f,t) in enumerate(parts) if t.split('-')[0] in ('VV','VA','VCP','VCN')]
 if len(hosts)!=1:raise ValueError('unsupported_predicate_morphology')
 i,stem,tag=hosts[0];endings=[f for f,t in parts[i+1:] if t.split('-')[0]=='EF']
 if len(endings)!=1:raise ValueError('missing_or_multiple_final_endings')
 pf=[f for f,t in parts[i+1:] if t.split('-')[0]=='EP'];nominal=''.join(f for f,t in parts[:i]) if tag=='VCP' else None
 kind={'VV':'verb','VA':'adjective','VCP':'copula','VCN':'negative_copula'}[tag]
 pfkind='none' if not pf else 'eoss' if len(pf)==1 and pf[0] in ('었','았','였') else 'other'
 m={'predicate_id':'p1','lemma':stem+'다','stem':stem,'prefinals':pf,'source_final':endings[0],
  'alignment':'whole_predicate_recomposition','origin':'kiwi_token_projection'}
 if nominal:
  cp=ord(nominal[-1]);m.update(nominal=nominal,nominal_end=('consonant_final_nominal' if (cp-0xac00)%28 else 'vowel_final_nominal') if 0xac00<=cp<=0xd7a3 else None)
 m['source_alignment']={'target_span':[word['start'],word['end']],'surface':word['surface'],'checked_by':'kiwi_token_projection','status':'machine_aligned_not_human_verified',
  **{k:copy.deepcopy(m.get(k)) for k in ('lemma','stem','prefinals','source_final','nominal')}}
 return m,kind,pfkind

def adapt(raw,morph):
 words={w['uid']:w for w in morph['words']};uid=raw['target_word_id']
 if uid not in words:raise ValueError('model_target_word_not_found')
 w=words[uid];m,_,_=projected(w);features=copy.deepcopy(raw['features']);q=None
 if features['question_kind']=='wh':
  qw=words.get(raw['question_word_id'])
  if not qw:raise ValueError('model_question_word_not_found')
  q={'id':'q1','span':[qw['start'],qw['end']],'surface':qw['surface'],'role':'asked_information','clause_id':'c1','scope_clause_id':'c1'}
 span=[w['start'],w['end']]
 return {'text':morph['text'],'origin':'qwen_features_with_kiwi_positions','clauses':[{'id':'c1','span':[0,len(morph['text'])],
  'target_span':span,'target_text':w['surface'],'features':features,'feature_bindings':{k:{'clause_id':'c1','predicate_id':'p1' if k in ('predicate_class','prefinal_type','subject_honorific','tense','polarity') else None,'origin':'qwen_feature_binding'} for k in features},
  'predicate':{'id':'p1','clause_id':'c1','span':span,'surface':w['surface'],'origin':'kiwi_word_selected_by_qwen'},
  'ending_slot':{'id':'end1','clause_id':'c1','predicate_id':'p1','boundary_status':'whole_predicate_recomposition'},'question_variable':q,'morphology':m}]}

class RuntimeReader(Reader):
 def __init__(self,graph,morph):super().__init__(graph);self.morph=copy.deepcopy(morph)
 def validate(self,a):
  super().validate(a)
  if a['text']!=self.morph['text']:raise ValueError('morphology_text_mismatch')
 def morphology_status(self,c):
  needs,m=super().morphology_status(c)
  if not m or m.get('origin')!='kiwi_token_projection':return needs,m
  words=[w for w in self.morph['words'] if [w['start'],w['end']]==c['target_span'] and w['surface']==c['target_text']]
  if len(words)!=1:return needs+['kiwi_word_alignment_missing'],m
  expected,pc,pf=projected(words[0])
  if m!=expected:return needs+['kiwi_projection_mismatch'],m
  needs=[x for x in needs if x!='source_alignment_review']
  f=c['features']
  if f.get('predicate_class') is not None and f['predicate_class']!=pc:needs.append('qwen_kiwi_predicate_disagreement')
  if f.get('prefinal_type') is not None and f['prefinal_type']!=pf:needs.append('qwen_kiwi_prefinal_disagreement')
  return sorted(set(needs)),m

def compact_packet(analysis,packet,morph):
 actions=[]
 for p in packet['clauses']:
  if p['readiness']!='ready_for_generation_trial':continue
  if len(p['choices'])!=1:raise ValueError('multiple_ready_rules_require_selection')
  choice=p['choices'][0];words=[w for w in morph['words'] if [w['start'],w['end']]==p['target']['span']]
  if len(words)!=1:raise ValueError('packet_target_missing_in_kiwi')
  actions.append({'target':p['target']['surface'],'span':p['target']['span'],'source_morphs':words[0]['morphs'],
   'lemma':p['morphology']['lemma'],'stem':p['morphology']['stem'],'nominal':p['morphology'].get('nominal'),
   'rule_id':choice['rule_id'],'meaning':choice['meaning'],'forms':[{k:f[k] for k in ('ending','selected_combining_form','includes_copula')} for f in choice['forms']],
   'composition':choice['composition'],'preserve':p['preserve']})
 return {'text':analysis['text'],'actions':actions}

def check_output(text,output,payload):
 warnings=[];actions=payload['actions']
 if len(actions)!=1:return {'warnings':['unsupported_output_check_scope']}
 a=actions[0];i,j=a['span'];prefix,suffix=text[:i],text[j:]
 if not output.startswith(prefix) or (suffix and not output.endswith(suffix)):warnings.append('outside_target_changed')
 else:
  piece=output[len(prefix):len(output)-len(suffix) if suffix else len(output)]
  forms=[f['selected_combining_form'] for f in a['forms'] if f['selected_combining_form']]
  if not any(piece.endswith(f) for f in forms):warnings.append('selected_ending_not_at_target_end')
  if a.get('nominal') and not piece.startswith(a['nominal']):warnings.append('nominal_changed')
 return {'warnings':warnings,'unchanged':text==output,'scope':'surface target/suffix checks only; not semantic or naturalness validation'}
