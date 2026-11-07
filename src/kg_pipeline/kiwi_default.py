"""Kiwi surface analysis, fresh Qwen scope, and explicit uncertain coverage.

No dialect answers or per-sentence replacements are defined here. The baseline
policy keeps the former downstream prompts and shared adapter for paired tests.
"""
import copy
from .io import save
from .validation import validate_schema
from .validation import ValidationError
from .morphology_control import anchors, kiwi_rows, frozen_clauses, prepare
from .multi_agent import obj, arr, string, word_anchors, PROMPTS

SCOPE_PROMPT = '''한국어 문장의 절 범위만 분석한다. 형태소는 주어진 Kiwi 관찰을 참고하되 정답으로 가정하지 않는다. 방언 번역이나 품사 수정은 하지 않는다.
모든 원문 어절을 덮는 주절을 문장마다 만들고 필요한 종속절/관형절을 그 안의 자식 절로 둔다. 같은 층위의 절 범위를 겹치지 않는다. 본용언+보조용언(해 보다, 해 주다, 하지 말다 등)은 같은 절 안에 둔다. 절을 어절마다 쪼개지 않는다. id는 중복 없이, 부모 없는 주절 parent_id는 null로 쓴다. start_word/end_word는 제공된 원문 어절 ID다.
predicate_words에는 문맥에서 서술 역할을 하는 어절 ID를 모두 적는다. 이 목록은 누락 점검용 추정이며 새 형태소를 만들 권한이 아니다. 모호한 범위는 uncertainties에 남긴다. JSON만 반환한다.'''

MEANING_ADDITION = '''
추가 판단 순서: 각 구성(construction)의 전체 뜻을 먼저 읽고 본용언/보조용언의 역할을 연결한다. relation_candidates는 형태·위치상 가능한 연결일 뿐 정답이 아니다. 의미상 맞으면 main_predicate와 auxiliary_predicate를 각각 기록하고 불명확하면 관계를 비운 채 analysis_issues로 알린다. 본용언과 보조용언을 서로 바꾸거나 construction 자신을 가리키지 않는다.
speech_act의 prohibition은 상대가 어떤 행동을 하지 않도록 금지하는 말, request는 어떤 행동을 하도록 부탁하는 말이다. 공손한 금지도 prohibition이다. 부정 평서와 금지, 시도/경험을 말하는 평서와 행동 요청도 구별한다. auxiliary_kind=none은 보조 구성이 없다는 판단이지 모른다는 뜻이 아니다. 현재 목록으로 분류되지 않는 보조용언은 other, 판단할 수 없으면 null로 둔다. 결합 전체의 기능과 각 부분의 기능은 다를 수 있다.
형태가 미확정(null)이면 임의로 없음/현재로 채우지 않는다. 관찰값에 대한 수정은 근거 구절을 가진 제안이며, 과거 형태와 시간 의미, 높임의 대상은 별개로 판단한다. missing_coverage는 확인이 필요한 범위이지 새 용언이 확정됐다는 뜻이 아니다.'''

WRITER_ADDITION = '''
추가 보존 원칙: 저/제의 겸양을 나/내로 바꾸지 않는다. 겸양 낱말의 삭제나 교체로 사회적 관계를 바꾸지 않는다. 주체 높임, 듣는 사람 높임, 화자 자신을 낮추는 표현은 서로 다른 정보다. 소유 조사 생략 지식이 있어도 명사·대명사 자체의 교체를 허가하는 것은 아니다.
source_form_literal=false이면 형태소 기본형은 원문 글자에 그대로 나타나지 않는다. 복원된 형태소를 글자처럼 잘라내거나 일반 명사에만 해당하는 변환을 축약 대명사에 확대하지 않는다. 나의→내/너의→네 예시는 저의→내를 뜻하지 않는다. 해당 입력에 맞지 않는 후보는 not_used로 남긴다.
분석에서 과거가 미확정이어도 원문에 과거가 있으면 유지한다. 누락 경고가 있는 구절도 최종 문장에서 빠뜨리지 않는다. 금지의 '하지 않도록 함', 요청의 '해 달라는 뜻', 보조용언의 시도/혜택/진행 의미를 유지한다. 이 보존 지시는 방언 정답을 제공하는 것이 아니다.'''

def scope_contract(text):
    ids=[w['id'] for w in word_anchors(text)]
    return obj({'clauses':arr(obj({'id':string(),'parent_id':string(nullable=True),
        'start_word':string(ids),'end_word':string(ids)}),minItems=1),
        'predicate_words':arr(string(ids)), 'uncertainties':arr(string())})

def initial_structure(client,text,kiwi,out,seed=20261107):
    words=anchors(text);raw=kiwi_rows(text,words,kiwi)
    save(out/'morphology_rows.json',raw)
    schema=scope_contract(text);save(out/'scope.schema.json',schema)
    response=client.call('kiwi_scope',SCOPE_PROMPT,{'text':text,'words':word_anchors(text),
        'morphology_words':words,'morphology':raw},schema,out/'scope',4096,seed)
    validate_schema(response,schema)
    clauses=frozen_clauses(text,response)
    validate_scope(text,clauses)
    save(out/'anchor_alignment.json',[{'morphology_word_id':w['uid'],
        'scope_word_ids':[s['id'] for s in word_anchors(text) if s['span'][0]<=w['start']<w['end']<=s['span'][1]],
        'span':[w['start'],w['end']]} for w in words])
    result=prepare(text,words,raw,clauses,'kiwi')
    result['scope_response']=response
    result['morphology_words']=words
    result['morphology_rows']=raw
    save(out/'common_structure.json',result)
    return result

def validate_scope(text,clauses):
    words=word_anchors(text);index={c['id']:c for c in clauses}
    for c in clauses:
        if not c['id'].strip():raise ValidationError('empty_clause_id')
        sentences={w['sentence'] for w in words if c['span'][0]<=w['span'][0]<w['span'][1]<=c['span'][1]}
        if len(sentences)!=1:raise ValidationError('clause_crosses_sentence')
    def ancestor(a,b):
        parent=b.get('parent_id')
        while parent is not None:
            if parent==a['id']:return True
            parent=index[parent].get('parent_id')
        return False
    for i,a in enumerate(clauses):
        for b in clauses[i+1:]:
            if max(a['span'][0],b['span'][0])<min(a['span'][1],b['span'][1]) and not (ancestor(a,b) or ancestor(b,a)):
                raise ValidationError('overlapping_nonancestor_clauses')

def enhance_structure(text,prepared):
    result=copy.deepcopy(prepared);units=result['units'];missing=[]
    # A recognized temporal/honorific EP is not proof that an unrecognized EP
    # carries no past. Preserve already observed past, otherwise leave it open.
    known={'았','었','였','시','으시','겠','더','더라','리','으리','오','옵','사옵'}
    for u in units:
        unresolved=[f for f,t in u['morphs'] if t=='EP' and f not in known]
        if unresolved:
            for k in ('prefinal_type','prefinal_sequence'):u['observed'][k]=None
            if not any(f in ('았','었','였') and t=='EP' for f,t in u['morphs']):u['observed']['past_form']=None
            u['morphology_uncertainties']=[{'forms':unresolved,'reason':'uninterpreted_prefinal_not_absent'}]
        # Applies to all literal-source conditions, not an ID-specific rule.
        form=u['observed'].get('source_form')
        u['source_form_literal']=bool(form and form not in ('none','') and form in u['text'])
    byword={r['word_id']:r['morphs'] for r in result.get('morphology_rows',{}).get('words',[])}
    ledger=[]
    for w in result.get('morphology_words',[]):
        morphs=byword.get(w['uid'],[])
        for ix,m in enumerate(morphs):
            if m['tag'] in ('VV','VA','VX','VCP','VCN','XSV','XSA'):
                matches=[u['id'] for u in units if u['kind']=='predicate' and u['word_id']==w['uid'] and u.get('predicate_token_index')==ix]
                kind='root'
            elif m['tag'] in ('EC','ETM','ETN'):
                matches=[u['id'] for u in units if u['kind']=='connector' and u['word_id']==w['uid'] and u.get('token_index')==ix]
                kind='connector'
            else:continue
            ledger.append({'word_id':w['uid'],'morph_index':ix,'form':m['form'],'tag':m['tag'],'unit_ids':matches,
                'status':'represented' if matches else 'unrepresented_observation'})
            if not matches:missing.append({'text':w['surface'],'span':[w['start'],w['end']],
                'basis':'observed_'+kind+'_without_unit','morph_index':ix})
    for wid in result.get('scope_response',{}).get('predicate_words',[]):
        w=next((w for w in word_anchors(text) if w['id']==wid),None)
        if w and not any(u['kind']=='predicate' and w['span'][0]<=u['span'][0]<u['span'][1]<=w['span'][1] for u in units):
            missing.append({'text':w['text'],'span':w['span'],'basis':'qwen_scope_suspects_unrepresented_predicate'})
    result['missing_coverage']=missing
    result['coverage_ledger']=ledger
    result['uncertainties']=result.get('scope_response',{}).get('uncertainties',[])
    return result

def relation_candidates(units):
    rows=[]
    for u in units:
        if u['kind']!='construction':continue
        possible=[v for v in units if v['kind']=='predicate' and v['word_id'] in u['related_word_ids'] and v['clause_key']==u['clause_key']]
        rows.append({'unit_id':u['id'],'text':u['text'],
            'main_predicate':[v['id'] for v in possible if v['observed'].get('root_tag') in ('VV','VA','VCP','VCN','XSV','XSA')],
            'auxiliary_predicate':[v['id'] for v in possible if v['observed'].get('root_tag')=='VX']})
    return rows

def humble_hints(units):
    seen=set();hints=[]
    for u in units:
        if any(f in ('저','저희') and t=='NP' for f,t in u['morphs']):
            key=tuple(u['span'])
            if key not in seen:
                hints.append({'원문 구절':u['text'],'span':u['span'],
                    '보존 정보':'저/제/저희의 화자 겸양 가능성을 원문 문맥으로 확인하고 보존. 나/내로 낮추지 않는다.','근거':'관찰된 저 또는 저희/NP. 품사만으로 인칭을 확정하지 않음'})
                seen.add(key)
    return hints

def prompts():
    return {**PROMPTS,'meaning':PROMPTS['meaning']+MEANING_ADDITION,
        'writer':PROMPTS['writer']+WRITER_ADDITION}
