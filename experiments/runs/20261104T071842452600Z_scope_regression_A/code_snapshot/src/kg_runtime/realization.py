"""General morphology composition using observed Kiwi tags and selected KG form.
No sentence-ID rules, reference outputs, or dialect vocabulary replacement.
"""
import copy

def compose(kiwi,action):
 forms=[f for f in action['forms'] if f.get('selected_combining_form')]
 if len(forms)!=1:raise ValueError('one_selected_form_required')
 form=forms[0];ending=form['selected_combining_form']
 parts=copy.deepcopy(action['source_morphs']);finals=[i for i,(f,t) in enumerate(parts) if t.split('-')[0]=='EF']
 if len(finals)!=1 or finals[0]!=len(parts)-1:raise ValueError('single_final_ending_at_end_required')
 if form['includes_copula']:
  nominal=action.get('nominal')
  if not nominal:raise ValueError('nominal_required')
  if any(t.split('-')[0]=='EP' for f,t in parts):raise ValueError('current_integrated_copula_conflicts_with_prefinal')
  copulas=[i for i,(f,t) in enumerate(parts) if t.split('-')[0]=='VCP' and f=='이']
  if len(copulas)!=1 or copulas[0]!=len(parts)-2:raise ValueError('integrated_copula_source_mismatch')
  if ''.join(f for f,t in parts[:copulas[0]])!=nominal:raise ValueError('nominal_source_mismatch')
  return nominal+ending,{'operation':'nominal_plus_selected_integrated_copula_form','nominal':nominal,'ending':ending,'lm_search':False}
 old=parts[-1];parts[-1]=[ending,'EF']
 # Keep -I/-R from the frozen analyzer. Do not strip irregularity information.
 joined=kiwi.join([tuple(x) for x in parts],lm_search=False)
 # This operation replaces one original unspaced word; preserve its spacing unit.
 surface=joined.replace(' ','')
 if action.get('expected_surface') is not None and surface!=action['expected_surface']:raise ValueError('documented_surface_postcondition_failed')
 return surface,{'operation':'kiwi_join_replace_final_only','source_final':old,'join_morphs':parts,'lm_search':False,'irregular_tags_preserved':True,'kiwi_surface':joined,'spacing_policy':'preserve_original_one_word'}
