"""Data-defined exact surface-tail operations; no sentence-specific replacements."""
import hashlib,json
from pathlib import Path

CONFIG=json.loads(Path(__file__).with_name('card_operations.json').read_text(encoding='utf-8'))
def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
CONFIG_HASH=digest(CONFIG)

def inside_explicit_quote(text,start):
    """Conservative literal quote boundary check; not a full syntactic quotation parser."""
    pairs={'“':'”','‘':'’','"':'"',"'":"'"};stack=[]
    for char in text[:start]:
        if stack and char==stack[-1]:stack.pop()
        elif char in pairs:stack.append(pairs[char])
    return bool(stack)

def scoped_binding(card,binding,word,text=None):
    spec=CONFIG['operations'].get(card['id'])
    # v2 cards did not declare the v3 partial-ending operation; preserve their behavior.
    if spec is None or 'rewrite' not in card:return None
    info={'card_id':card['id'],'word_id':word['uid'],'operation':spec['kind'],'config_hash':CONFIG_HASH,
          'candidates':[],'status':'scope_unavailable','exact':True}
    def fail(reason):return dict(info,reason=reason)
    if digest(card)!=spec['card_sha256']:return fail('card_content_contract_mismatch')
    if text is None:return fail('source_context_unavailable')
    if inside_explicit_quote(text,word['start']):return fail('explicit_quotation_out_of_scope')
    if spec['kind']!='replace_surface_tail':return fail('unknown_scope_operation')
    if binding['form_index']!=spec['target_form_index'] or card['forms'][binding['form_index']]!=spec['target_form']:
        return fail('unsupported_scope_target')
    if binding['component']!=spec['source_component']:return fail('unsupported_scope_component')
    parts=word.get('morphs',[]);idx=binding['morph_index']
    terminal_yo=bool(parts) and idx==len(parts)-1 and parts[idx]==['요','JX'] and idx>0 and parts[idx-1][1].split('-')[0]=='EF'
    if not parts or idx!=len(parts)-1 or (parts[idx][1].split('-')[0]!=spec['source_tag'] and not terminal_yo):return fail('unsupported_scope_source_tag')
    if not {p[1].split('-')[0] for p in parts}&set(spec['required_predicate_tags']):return fail('scope_requires_predicate')
    surface=word['surface'];tail=spec['source_tail']
    if not tail or not surface.endswith(tail) or not parts[idx][0].endswith(tail):return fail('source_tail_not_literal')
    if any(surface.endswith(x) for x in spec['excluded_source_suffixes']):return fail('excluded_source_ending')
    if spec['allowed_source_suffixes'] and not any(surface.endswith(x) for x in spec['allowed_source_suffixes']):return fail('source_ending_out_of_scope')
    candidate=surface[:-len(tail)]+spec['target_tail']
    return dict(info,status='scope_ready',candidates=[candidate],source_surface=surface,
        source_tail=tail,target_tail=spec['target_tail'],preserved_prefix=surface[:-len(tail)],
        origin='deterministic_execution_of_card_operation_not_Qwen_realization')

def scoped_edit_checks(edit,morph,cards,realize):
    by={c['id']:c for c in cards};words={w['uid']:w for w in morph['words']};checks=[];issues=[]
    for b in edit['bindings']:
        info=scoped_binding(by[b['card_id']],b,words[b['source_word_id']],morph['text'])
        if info is None:continue
        checks.append(info)
        if info['status']!='scope_ready':issues.append({'code':'scoped_operation_source_unavailable','basis':info['reason']})
    if checks and not issues:
        projection=edit.get('suffix_projection',{})
        if not projection.get('exact_scoped') or len(projection.get('candidates',[]))!=1:
            issues.append({'code':'scoped_operation_composition_unavailable','basis':'mixed_or_ambiguous_bindings'})
        elif realize and edit['after']!=projection['candidates'][0]:
            issues.append({'code':'scoped_operation_preservation_violation','basis':'exact_card_scope'})
    return issues,checks

def realize_scoped(edit):
    """Execute only a unique exact operation. Caller retains proposed_after and repair audit."""
    projection=edit.get('suffix_projection',{})
    if not projection.get('exact_scoped') or len(projection.get('candidates',[]))!=1:return
    expected=projection['candidates'][0]
    edit['surface_origin']='deterministic_card_scope_composition'
    if edit['after']!=expected:
        edit['repairs'].append({'kind':'scoped_surface_tail','before':edit['after'],'after':expected,
            'basis':'only registered source tail replaced; all preceding source text preserved',
            'operations':projection.get('scope_operations',[]),'config_hash':CONFIG_HASH})
        edit['after']=expected
