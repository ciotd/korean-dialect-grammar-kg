"""Separate candidate runtime; reuse existing analysis and reader unchanged."""
from pathlib import Path
import importlib.util
R=Path(__file__).resolve().parents[3]
s=importlib.util.spec_from_file_location('overnight_support_parent',R/'experiments/analyses/support_expansion_20261104/runtime.py');parent=importlib.util.module_from_spec(s);s.loader.exec_module(parent)
ROOT=R;bridge=parent.bridge;base=parent.base
GRAPH=R/'knowledge/authored/semantic_grammar_20261105_r10/private/graph.json'
PROMPT=parent.PROMPT;GENERATION_PROMPT=parent.GENERATION_PROMPT;GENERATION_SCHEMA=parent.GENERATION_SCHEMA
schema_and_payload=parent.schema_and_payload;analyze_response=parent.analyze_response;preservation_check=parent.preservation_check

def generation_payload(a,tr,morph):
 compact,enhanced=parent.generation_payload(a,tr,morph)
 if tr['retrieval']['construction_id']=='SEM_CX_EXT_COP_PAST':
  act=enhanced['actions'][0]
  if not act['target'].endswith('요'):raise ValueError('source_surface_not_yo')
  act['expected_surface']=act['target'][:-1]+'예';act['expected_surface_basis']='compositional_candidate_diagnostic_not_gold'
 return compact,enhanced
