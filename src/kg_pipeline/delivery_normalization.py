"""Exact, versioned delivery edits; no grammar eligibility changes.

    Original strings remain in the immutable graph and external audit. Never
    remove an entire '조건 보완' suffix: it can contain genuine constraints.
"""
import copy

VERSION='delivery_normalization_20261110_v1'
# Only statements contradicted by the current stored conditions / adapter.
# This table is data cleaning, not rule-specific generation Python code.
EXACT_REPLACEMENTS={
    'INT_END_PROMISE_KKE':{
        'Kiwi는 ㄹ게를 EF "ᆯ게"(받침 낱자 U+11AF)로 출력(실측) → 호환 자모 "ㄹ게"는 절대 일치 안 함.':'',
    },
    'INT_AUX_PRESERVE_COMMON':{
        'benefactive 포함으로 REQUEST_DO(보류)와 충돌 없음.':'',
    },
    'INT_CONN_SEQ_AGA':{
        'semantic_function cause는 기본 enum reason과 중복 값.':'',
    },
    'INT_END_HORT_POLITE_IPSIDEO':{'source_form 조건 없음.':''},
    'INT_END_PROHIB_MAISO':{'construction에 lemma·어미 조건이 없어 높임 금지 판정만으로 걸림.':''},
    'INT_CONN_QUOTE_KKO':{
        'Kiwi는 "간다고"를 EC ᆫ다고(받침 낱자)로 분석(실측) → "다고"만으로는 ㄴ다고/는다고를 놓침.':'',
    },
}
LIMIT_REPLACEMENTS={
    '이번 직접 정보 질문 체계의 후보이며 모든 경상도 용법을 망라하지 않음.':'실제 답을 묻는 주절 직접 질문의 후보 어미이며, 경상 방언 의문형 전부는 아니다.',
    '완성형은 조합 결과이며 원문 인용과 구별':None,
}

def normalize_delivery(payload):
    out=copy.deepcopy(payload)
    edits=EXACT_REPLACEMENTS.get(out.get('rule_id'),{})
    def clean(value,limits=False):
        if isinstance(value,list):
            return [v for x in value if (v:=clean(x,limits)) is not None]
        if isinstance(value,str):
            if limits and value in LIMIT_REPLACEMENTS:return LIMIT_REPLACEMENTS[value]
            for old,new in edits.items():value=value.replace(old,new)
            return value.strip()
        return value
    # Keep unknown structures / other keys exactly, including genuine caveats.
    if 'limitations' in out:out['limitations']=clean(out['limitations'],True)
    return out
