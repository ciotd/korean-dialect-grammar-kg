"""General morphology composition using observed Kiwi tags and selected KG form.
No sentence-ID rules, reference outputs, or dialect vocabulary replacement.
"""
import copy
from pipeline import apply_piece

def compose(kiwi,action):
 forms=[f for f in action['forms'] if f.get('selected_combining_form')]
 if len(forms)!=1:raise ValueError('one_selected_form_required')
 form=forms[0];ending=form['selected_combining_form']
 if form['includes_copula']:
  nominal=action.get('nominal')
  if not nominal:raise ValueError('nominal_required')
  return nominal+ending,{'operation':'nominal_plus_selected_integrated_copula_form','nominal':nominal,'ending':ending,'lm_search':False}
 parts=copy.deepcopy(action['source_morphs']);finals=[i for i,(f,t) in enumerate(parts) if t.split('-')[0]=='EF']
 if len(finals)!=1 or finals[0]!=len(parts)-1:raise ValueError('single_final_ending_at_end_required')
 old=parts[-1];parts[-1]=[ending,'EF']
 # Keep -I/-R from the frozen analyzer. Do not strip irregularity information.
 surface=kiwi.join([tuple(x) for x in parts],lm_search=False)
 return surface,{'operation':'kiwi_join_replace_final_only','source_final':old,'join_morphs':parts,'lm_search':False,'irregular_tags_preserved':True}
