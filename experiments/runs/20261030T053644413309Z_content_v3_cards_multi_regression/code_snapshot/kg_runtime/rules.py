"""Executable operators. Conditions are explicit, source facts live in sidecars.

Every rule_id below is an existing SourceAtom ID, not an invented KG relation.
Surface composition is an implementation derivation, not a newly attested quote.
"""
RULES={
 'GS_ENDRULE_YO_COMPOSE':('polite_ye','해예체의 확인된 종결형. 의도·높임·시제는 그대로 유지.',[( 'D02',203),('D02',213),('D05',26)]),
 'GS_ENDRULE_ISO_IMP':('request_iso','상대에게 행동을 요청하는 명령일 때만. 평서·안부 인사에는 적용하지 않음.',[('D02',154),('D05',4),('D05',5)]),
 'GS_ENDRULE_Q_POLAR_V':('question_na','반말의 정보 요구 판정 의문. 용언 또는 시상 형태를 가진 서술어.',[('D02',145)]),
 'GS_ENDRULE_Q_WH_V':('question_no','반말의 실제 의문사 질문. 의문사와 이 종결부가 같은 질문에 속함.',[('D02',145)]),
 'GS_ENDRULE_Q_POLAR_C':('copula_ga','시상 선어말이 없는 체언 서술어의 판정 의문.',[('D02',144),('D02',145)]),
 'GS_ENDRULE_Q_WH_C':('copula_go','시상 선어말이 없는 체언 서술어의 설명 의문.',[('D02',144),('D02',145)]),
 'GS_ENDRULE_Q_TAM_C':('copula_tam','과거 등 시상 형태가 붙은 체언 서술어 의문은 나/노 계열.',[('D02',145)]),
 'GS_ENDRULE_NNA_O':('come_command','오다의 반말 명령. 일반 동사나 의문문에는 적용하지 않음.',[('D02',169)]),
 'GS_ENDRULE_HORT_JA':('propositive','자 청유형을 제로. 인용 자고나 자다 동사에는 적용하지 않음.',[('D02',190)]),
 'GS_ENDRULE_JI_ASSERT':('ji_je','사실 서술·응답의 종결 지를 제로. 연결 지에는 적용하지 않음.',[('D02',200)]),
 'GS_ENDRULE_JI_CONFIRM':('ji_je','확인 질문의 종결 지를 제로. 부정 지 않다에는 적용하지 않음.',[('D02',211)]),
 'GS_CONNECT_COND_03':('condition_mo','조건 연결어미 면을 모로. 관형절·명사 면은 대상 아님.',[('D04',27)]),
 'GS_CONNECT_CAUSE_01':('cause_aga','아서 계열 연결어미를 아가로. -어서는 등 뒤 결합이 있는 형태 제외.',[('D04',27)]),
 'GS_CONNECT_QUOTE_02':('quotation_kko','다고/라고/자고 간접 인용의 고를 꼬로. 자다+고나 일반 연결 고에는 적용하지 않음.',[('D04',28)]),
 'GS_HAM_ADV_MAI':('many','정도·수량 부사 많이의 마이 대응.',[('D07',26)]),
 'GS_HAM_ADV_LITTLE':('little','부사 조금만의 쪼께만 대응. 조금을 조금만으로 강화하지 않음.',[('D07',26)]),
 'GS_HAM_ADV_BARE':('barely','부사 겨우/간신히의 보도시 대응.',[('D07',26)]),
}

def forms_for(rule_id,w,morph,analyzer):
    op=RULES[rule_id][0];s=w['surface'];e=w['ending'];tag=w['ending_tag'];tags=[x[1].split('-')[0] for x in w['morphs']]
    pred=[x[0] for x in w['morphs'] if x[1].split('-')[0] in ('VV','VA','VX','VCP','VCN','XSV','XSA')]
    ep=[x[0] for x in w['morphs'] if x[1].split('-')[0]=='EP']
    sentence=''.join(t['surface'] for t in morph['tokens'] if t['sentence']==w['sentence'])
    q='?' in sentence;cop=any(t in tags for t in ('VCP','VCN'));polite=s.endswith(('요','죠','니다','니까'))
    out=[]
    if op=='polite_ye' and tag=='EF':
        # Only source-supported families, not arbitrary suffix replacement.
        if e in ('어요','아요','네요','거든요','데요','지요') and s.endswith('요'):
            out=[s[:-1]+'예']
        elif e=='죠' and s.endswith('죠'):out=[s[:-1]+'지예']
        elif cop and not ep and e in ('예요','에요','이에요'):
            for suffix in ('이에요','예요','에요'):
                if s.endswith(suffix):
                    base=s[:-len(suffix)];has_coda=bool(base and 0xAC00<=ord(base[-1])<=0xD7A3 and (ord(base[-1])-0xAC00)%28)
                    out=[base+('이라예' if has_coda else '라예')];break
        elif e in ('세요','으세요') and s.endswith('세요'):
            # Declarative 계세요 is preserved explicitly; request candidate is separate.
            out=[s[:-2]+'세예']
        elif e in ('ᆯ래요','을래요') and s.endswith('요'):out=[s[:-1]+'예']
    elif op=='request_iso' and tag=='EF' and e in ('세요','으세요') and any(t in tags for t in ('VV','VX','XSV')) and 'VA' not in tags and not q:
        out=[s[:-2]+'이소'] if s.endswith('세요') else []
    elif op in ('question_na','question_no','copula_ga','copula_go','copula_tam') and tag=='EF' and q and not polite and e in ('어','아','니','냐','나','야'):
        if op.startswith('question') and not cop:out=[analyzer.join_ending(w,'나' if op=='question_na' else '노')]
        elif op.startswith('copula') and cop:
            if op=='copula_tam' and ep:out=[analyzer.join_ending(w,x) for x in ('나','노')]
            elif not ep and op!='copula_tam':out=[analyzer.join_ending(w,'가' if op=='copula_ga' else '고')]
    elif op=='come_command' and tag=='EF' and not q and not polite and pred and pred[-1]=='오' and not ep:
        if s=='와':out=['온나']
    elif op=='propositive' and tag=='EF' and e=='자' and not ep:out=[analyzer.join_ending(w,'제')]
    elif op=='ji_je' and tag=='EF' and e=='지' and ((rule_id.endswith('CONFIRM') and q) or (rule_id.endswith('ASSERT') and not q)):
        out=[s[:-1]+'제']
    elif op=='condition_mo' and tag=='EC' and e in ('면','으면') and s.endswith('면'):out=[s[:-1]+'모']
    elif op=='cause_aga' and tag=='EC' and e in ('어서','아서') and s.endswith('서'):out=[s[:-1]+'가']
    elif op=='quotation_kko' and tag=='EC' and e in ('다고','ᆫ다고','는다고','라고','자고') and s.endswith('고'):out=[s[:-1]+'꼬']
    elif op=='many' and s=='많이' and 'MAG' in tags:out=['마이']
    elif op=='little' and s=='조금만' and any(x[0]=='조금' and x[1] in ('MAG','NNG') for x in w['morphs']):out=['쪼께만']
    elif op=='barely' and s in ('겨우','간신히') and 'MAG' in tags:out=['보도시']
    return [x for x in dict.fromkeys(out) if x and x!=s]

def seed_concepts(morph):
    ids=set()
    for w in morph['words']:
        if w['ending_tag']=='EF':ids.update(('G_END_FINAL','G_MOOD_FUNCTION','G_HON_ADDRESSEE'))
        if w['ending_tag']=='EC':ids.add('G_CLAUSE_LINK')
        if w['ending'] in ('면','으면'):ids.add('G_END_CONDITIONAL')
        if w['ending'] in ('어서','아서'):ids.add('G_END_CAUSE')
        if any(t[1].split('-')[0]=='MAG' for t in w['morphs']) or w['surface']=='조금만':ids.add('G_LEX_SENSE')
    if '?' in morph['text']:ids.update(('G_Q_POLAR','G_Q_WH','G_Q_SCOPE'))
    return sorted(ids)
