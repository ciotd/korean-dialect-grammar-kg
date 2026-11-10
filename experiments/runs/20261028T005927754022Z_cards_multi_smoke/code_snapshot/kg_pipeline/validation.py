"""Validate the exact contract keywords used here, plus span/reference/edit integrity.
Not a general-purpose JSON Schema validator. Unsupported schema keywords fail closed.
"""
import re
class ValidationError(ValueError):pass
def validate_schema(value,schema,path='$'):
    allowed={'type','properties','required','additionalProperties','items','enum','minimum','minLength','anyOf'}
    if set(schema)-allowed:raise ValidationError('unsupported_schema_keyword:'+str(set(schema)-allowed))
    if 'anyOf' in schema:
        for choice in schema['anyOf']:
            try:validate_schema(value,choice,path);return
            except ValidationError:pass
        raise ValidationError(path+':no_union_variant_matches')
    types=schema.get('type');types=types if isinstance(types,list) else [types]
    kinds={'object':lambda x:isinstance(x,dict),'array':lambda x:isinstance(x,list),'string':lambda x:isinstance(x,str),
           'integer':lambda x:type(x) is int,'boolean':lambda x:type(x) is bool,'null':lambda x:x is None}
    if not any(kinds[t](value) for t in types):raise ValidationError(path+':type')
    if 'enum' in schema and value not in schema['enum']:raise ValidationError(path+':enum')
    if 'minimum' in schema and value<schema['minimum']:raise ValidationError(path+':minimum')
    if 'minLength' in schema and isinstance(value,str) and len(value)<schema['minLength']:raise ValidationError(path+':minLength')
    if isinstance(value,dict):
        if set(schema.get('required',[]))-set(value):raise ValidationError(path+':missing_fields')
        props=schema.get('properties',{})
        if schema.get('additionalProperties') is False and set(value)-set(props):raise ValidationError(path+':extra_fields')
        for k,v in value.items():validate_schema(v,props[k],path+'.'+k)
    if isinstance(value,list):
        for i,v in enumerate(value):validate_schema(v,schema['items'],path+f'[{i}]')
def locate(text,anchor):
    surface=anchor['surface'];starts=[m.start() for m in re.finditer('(?='+re.escape(surface)+')',text)]
    i=anchor['occurrence']-1
    if i<0 or i>=len(starts):raise ValidationError('anchor_not_in_input:'+surface)
    return [starts[i],starts[i]+len(surface)]
def validate_analysis(a,text,input_id,schema):
    validate_schema(a,schema)
    if a['input_id']!=input_id:raise ValidationError('wrong_input_id')
    ids=[c['cid'] for c in a['clauses']]+[u['uid'] for u in a['units']]
    if len(set(ids))!=len(ids):raise ValidationError('duplicate_local_id')
    if not a['clauses'] or not a['units']:raise ValidationError('empty_analysis')
    clauses={c['cid']:c for c in a['clauses']};spans={};warnings=[]
    for c in a['clauses']:
        spans[c['cid']]=locate(text,c['anchor']);parent=c['parent_cid'];seen={c['cid']}
        while parent is not None:
            if parent not in clauses:raise ValidationError('dangling_parent')
            if parent in seen:raise ValidationError('clause_cycle')
            seen.add(parent);parent=clauses[parent]['parent_cid']
    for u in a['units']:
        if u['cid'] not in clauses:raise ValidationError('dangling_clause')
        spans[u['uid']]=locate(text,u['anchor']);cs,ce=spans[u['cid']];s,e=spans[u['uid']]
        if not(cs<=s<e<=ce):raise ValidationError('unit_outside_clause:'+u['uid'])
        wh=u['features'].get('wh_scope_cid')
        if wh and wh not in clauses:raise ValidationError('dangling_wh_scope')
    for q in a['uncertainties']:
        if q['target_id'] not in ids:raise ValidationError('dangling_uncertainty')
    # Uncovered content is a diagnostic, not silently interpreted as a correct complete analysis.
    covered=set(i for c in a['clauses'] for i in range(*spans[c['cid']]))
    uncovered=[i for i,ch in enumerate(text) if ch.isalnum() and i not in covered]
    if uncovered:warnings.append({'type':'clause_coverage_gap','positions':uncovered})
    return {'spans':spans,'warnings':warnings,'linguistic_correctness':'not_verified'}
def validate_generation(g,text,input_id,analysis,packet,checks,schema):
    validate_schema(g,schema)
    if g['input_id']!=input_id:raise ValidationError('wrong_input_id')
    units={u['uid']:u for u in analysis['units']};evidence={e['evidence_id']:e for e in packet['evidence']};changes=[];seen=set()
    for e in g['edits']:
        uid=e['target_uid']
        if uid in seen or uid not in units:raise ValidationError('duplicate_or_missing_edit_unit')
        seen.add(uid)
        if e['before']!=units[uid]['anchor']['surface']:raise ValidationError('edit_before_mismatch')
        if e['before']==e['after']:raise ValidationError('no_op_edit')
        if not e['evidence_ids']:raise ValidationError('edit_without_evidence')
        for k in e['evidence_ids']:
            if k not in evidence or evidence[k]['target_uid']!=uid or evidence[k]['role']!='realization_reference':raise ValidationError('invalid_edit_evidence')
        s,t=checks['spans'][uid];changes.append((s,t,e['after']))
    changes.sort()
    if any(a[1]>b[0] for a,b in zip(changes,changes[1:])):raise ValidationError('overlapping_edits')
    reconstructed=text
    for s,t,replacement in reversed(changes):reconstructed=reconstructed[:s]+replacement+reconstructed[t:]
    if reconstructed!=g['output_text']:raise ValidationError('untracked_output_change')
    return {'structure_passed':True,'changed':text!=g['output_text'],'edit_count':len(changes),'meaning_naturalness':'requires_human_review'}
