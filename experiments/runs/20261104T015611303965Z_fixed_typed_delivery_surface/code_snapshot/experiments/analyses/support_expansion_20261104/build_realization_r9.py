"""Expose the r8 edit unit as typed data; no change to applicability or forms."""
from pathlib import Path
import sys,copy
H=Path(__file__).resolve().parent;R=H.parents[2];sys.path.insert(0,str(R/'src'))
from kg_pipeline.io import read,save,sha
def main():
 src=R/'knowledge/authored/semantic_grammar_20261104_r8/private/graph.json';g=read(src);changes=[]
 for n in g['nodes']:
  p=n['properties']
  if n['type']=='Realization' and p.get('operation')=='replace_final_yo_with_ye_preserve_inflected_prefix':
   p['surface_edit']={'kind':'replace_surface_suffix','source_suffix':'요','replacement_suffix':'예','preserve':'all_characters_before_source_suffix'};changes.append(n['id'])
 assert len(changes)==2
 g['version']='semantic_grammar_20261104_r9';out=R/'knowledge/authored/semantic_grammar_20261104_r9/private';save(out/'graph.json',g);save(out/'change_ledger.json',{'parent_sha256':sha(src.read_bytes()),'changed_nodes':changes,'change':'expose existing r8 operation as typed surface_edit','conditions_changed':False,'forms_changed':False,'edges_changed':False,'new_linguistic_facts':False,'neo4j_imported':False});print('r9 typed edit nodes:',changes)
if __name__=='__main__':main()
