"""Build immutable model-facing content; original graph and v2 remain unchanged."""
import argparse,copy,json,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from kg_pipeline.io import read,save,dumps,sha

SPEC=ROOT/'knowledge/specs/card_rewrite_20261030.json'
META={'target_profile','profile','profile_id','source_profile','scope_profile','mapping_status','source_system',
      'source_region','period','sample_scope','year','activation_state','runtime_active','source_membership'}

def separate(value,path='when'):
    removed={}
    if isinstance(value,dict):
        out={}
        for k,v in value.items():
            at=path+'.'+k
            if k in META:removed[at]=v
            else:
                out[k],extra=separate(v,at);removed.update(extra)
        return out,removed
    if isinstance(value,list):
        out=[]
        for i,v in enumerate(value):
            nv,extra=separate(v,path+f'[{i}]');out.append(nv);removed.update(extra)
        return out,removed
    return value,removed

def concrete_when(cid):
    common={'input_politeness':'polite','target_level':'haeye','scope':'문장 끝 종결'}
    extra={
        'GS_END_DECL_YE_02':{'source_endings':['-네요'],'mood_form':'declarative','preserved_function':'기존 -네의 감탄·발견 기능'},
        'GS_END_DECL_YE_04':{'source_endings':['-이에요','-예요'],'predicate_kind':'copula','mood_form':'declarative','tense':'present','polarity':'positive'},
        'GS_ENDRULE_YO_COMPOSE':{'source_component':'비격식 종결 구성의 마지막 공손 표지 요','base_ending':'원문에 있는 종결 구성 전체를 보존'},
        'GS_END_DECL_YE_01':{'source_endings':['-아요','-어요','-였어요'],'mood_form':'declarative','base_ending':'요 앞의 활용은 유지'},
        'GS_END_DECL_YE_08':{'source_endings':['-(으)ㄹ게요'],'source_function':'원문에 명시된 화자의 약속·의지','intention_holder':'speaker'},
        'GS_END_Q_YE_05':{'source_endings':['-지요?','-죠?'],'mood_form':'interrogative','source_function':'기존 확인 질문'},
        'GS_END_DECL_YE_06':{'source_endings':['-지요','-죠'],'mood_form':'declarative','source_function':'기존 확인·동의 진술'},
        'GS_END_DECL_YE_07':{'source_endings':['-거든요'],'mood_form':'declarative','source_function':'설명 종결; 조건 연결어미 제외'}
    }
    return dict(common,**extra[cid]) if cid in extra else None

def build(output,cache):
    spec=read(SPEC);source=ROOT/'knowledge/authored'/spec['parent'];old=read(source/'cards.json');provenance=read(source/'provenance.json')
    references=ROOT/'data/derived_private/gyeongsang_reference50_20261030_v1'
    approval=read(references/'manifest.json');assert approval['references_sha256']==sha((references/'references.jsonl').read_bytes())
    source_pages={};new=copy.deepcopy(old);new['version']=spec['version'];side={};counts=Counter();changes=[]
    for card in new['cards']:
        before=copy.deepcopy(card);cleaned,removed=separate(card['when']);card['when']=cleaned
        counts.update(p.split('.')[-1] for p in removed)
        evidence=[];draft=spec['cards'].get(card['id'])
        if draft:
            for b in draft['basis']:
                if b['doc'] not in source_pages:source_pages[b['doc']]={p['page']:p['text'] for p in read(cache/(b['doc']+'.json'))}
                text=''.join(source_pages[b['doc']][b['page']].split());needle=''.join(b['anchor'].split())
                assert needle in text,(card['id'],b)
                evidence.append(dict(b,page_text_sha256=sha(source_pages[b['doc']][b['page']].encode())))
            condition=concrete_when(card['id'])
            if condition is not None:card['when']=condition
            card['rewrite']={k:copy.deepcopy(draft[k]) for k in ['source','target_form_index','operation','preserve','exclude']}
            card['rewrite']['selection_policy']=spec['policy']
        assert all(card[k]==before[k] for k in ['id','module','kind','title','forms','avoid'])
        side[card['id']]={'parent_version':spec['parent'],'parent_card_sha256':sha(dumps(before).encode()),
            'original_when':before['when'],'moved_metadata':removed,
            'original_provenance':provenance[card['id']],
            'rewrite_evidence':evidence,'approved_example_ids':draft['approved_examples'] if draft else [],
            'claim_type':'documented_forms_plus_user_approved_cases_plus_authored_generalization' if draft else 'metadata_separation_only',
            'condition_replacement':bool(draft and concrete_when(card['id']) is not None),
            'source_interpretation':'Original documentary facts retained; concrete source-to-target scope is authored guidance, not automatic linguistic proof.'}
        if card!=before:changes.append({'id':card['id'],'title':card['title'],'metadata_fields':list(removed),
            'direction_added':bool(draft),'when_replaced':side[card['id']]['condition_replacement'],
            'before_sha256':sha(dumps(before).encode()),'after_sha256':sha(dumps(card).encode())})
    assert {c['id'] for c in new['cards']}=={c['id'] for c in old['cards']}
    assert set(spec['cards'])<={c['id'] for c in new['cards']}
    statistics={'cards':len(new['cards']),'changed_cards':len(changes),'directional_cards':len(spec['cards']),
        'source_conditions_rewritten':sum(c['when_replaced'] for c in changes),'metadata_fields_moved':dict(counts),
        'forms_and_indices_unchanged':True,'graph_unchanged':True,'all_ids_preserved':True,
        'ranking_policy':'v2 selection then same-ID content projection','automatic_condition_engine_added':False,
        'new_model_calls':0,'model_payload_chars_before':sum(len(dumps(c)) for c in old['cards']),
        'model_payload_chars_after':sum(len(dumps(c)) for c in new['cards'])}
    manifest={'version':spec['version'],'parent':spec['parent'],'source_dataset':old['source_dataset'],
        'parent_cards_sha256':sha((source/'cards.json').read_bytes()),'spec_sha256':sha(SPEC.read_bytes()),
        'builder_sha256':sha(Path(__file__).read_bytes()),'cards_content_sha256':sha(dumps(new).encode()),'provenance_content_sha256':sha(dumps(side).encode()),'reference_sha256':approval['references_sha256'],
        'source_pages':{d:sha((cache/(d+'.json')).read_bytes()) for d in source_pages},
        'method':'Codex-authored generalizations grounded in documents and user-approved examples; deterministic build; no Qwen runtime card generation'}
    for name,value in [('cards.json',new),('provenance.json',side),('changes.json',changes),('statistics.json',statistics),('manifest.json',manifest)]:
        p=output/name
        if p.exists():assert read(p)==value,'immutable_version_changed:'+str(p)
        else:save(p,value)
    print(dumps(statistics))
    return new

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--source-cache',type=Path,required=True);a=p.parse_args();build(a.output,a.source_cache)
