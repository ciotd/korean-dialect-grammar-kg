"""Compile a graph realization's edit unit into a Qwen instruction, never output text."""
import copy
def compile_action(graph,action):
 forms=[e['target'] for e in graph['edges'] if e['source']==action['rule_id'] and e['relation']=='REALIZES'];ns={n['id']:n for n in graph['nodes']}
 typed=[ns[f]['properties'] for f in forms if ns[f]['properties'].get('surface_edit')]
 if not typed:return copy.deepcopy(action)
 if len(forms)!=1 or len(typed)!=1:raise ValueError('ambiguous_edit_unit')
 p=typed[0];edit=p['surface_edit']
 if edit['kind']!='replace_surface_suffix' or not edit['source_suffix'] or not action['target'].endswith(edit['source_suffix']):raise ValueError('surface_edit_source_mismatch')
 if edit['replacement_suffix']!=p['form'].lstrip('-'):raise ValueError('edit_form_disagreement')
 # The base target is the original input, not a computed dialect answer.
 out={k:copy.deepcopy(action[k]) for k in ('target_id','target','span','rule_id','meaning','preserve','structure_evidence') if k in action}
 out['surface_edit']=copy.deepcopy(edit);out['edit_unit']=p['unit'];return out

PROMPT_SUFFIX='''
actions에서 다음 두 수정 단위를 구별해서 사용한다.
surface_edit가 있는 action: target에 적힌 원래 어절의 맨 끝 source_suffix만 replacement_suffix로 바꾼다. 앞부분 전체를 그대로 유지한다. 어간부터 새로 활용하거나 전체 종결어미를 교체하는 작업이 아니다.
surface_edit가 없는 action: 기존 forms와 composition에 따라 조합한다.
모든 action을 반영한 문장 전체를 네가 output_text에 작성한다. 중간 코드나 설명을 출력하지 않는다.
'''
