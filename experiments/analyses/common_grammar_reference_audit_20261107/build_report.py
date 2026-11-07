"""Read-only reference-framework audit. Judgments are authored, counts are computed.

No model calls, KG writes, or implementation claims. External PDF stays private.
Run Archify finalize separately after this builder.
"""
from pathlib import Path
import collections, datetime, hashlib, html, json, shutil, sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
DESIGN = ROOT/'knowledge/authored/kg_v3_evidence_20261019_r2/inputs/design.json'
REF = HERE/'private/20261107_reference/nikk_grammar_2014.pdf'
REF_URL = 'https://www.korean.go.kr/front/reportData/reportDataView.do?mn_id=207&report_seq=763&searchOrder=date'
BOOK_URL = 'https://korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=313542'
DICT_URL = 'https://krdict.korean.go.kr/m/eng/searchResultView?ParaWordNo=17884&mainSearchWord=%EC%83%88&nation=eng&nationCode=6'
sys.path.insert(0,str(HERE.parent/'common_grammar_walkthrough_20261107'))
from examples import EXAMPLES
from toc_crosswalk import crosswalk

def load(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v): Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def e(v): return html.escape(str(v),quote=True)

# Locators refer to the 2014 development report, not the later published book.
# These are taxonomy correspondences, not assertions of full semantic support.
CHAPTER_REF = {
 1:('서술어·활용·단어 형성',[43,44]), 2:('서술어 종류·수식 구성',[43,45]),
 3:('체언·명사구',[42,43,44]), 4:('조사·문장 성분',[43,44]),
 5:('어미·복문·종결 표현',[43,45]), 6:('문장 구성·문장 성분·복문',[44,45]),
 7:('보조용언·상 표현',[43,45]), 8:('시간·상·법 표현',[45]),
 9:('부정 표현',[45]), 10:('사동·피동 표현',[45,46]),
 11:('높임 표현',[45]), 12:('종결 표현·발화 기능',[45,46]),
 13:('인용절 내포문',[45]), 14:('어휘·품사·담화와의 접점',[43,44,46]),
 15:('음운·이형태·활용과의 접점',[41,42,43]),
 16:('문법 단위와 분석 시스템의 접점',[42,44]),
}

# Audit author's reverse crosswalk: gaps in explicit design responsibility.
# Not a count of all grammatical rules missing from Korean or executable KG.
GAPS = [
 ('R01','일반 관형사의 구별','세부 명세 부족','우선',
  'G_NUMERAL_ROLE G_NP_HEAD G_CLAUSE_COMPONENT G_ADJ_ADNOMINAL', [43,201,202],
  '수관형사는 다루지만 성상·지시 관형사를 함께 분류하고, 관형사와 형용사의 관형형을 가르는 독립 명세는 찾지 못했다. 명사구 수식 관계라는 큰 틀은 이미 있다.',
  '새 가방 / 새로운 가방 / 세 가방',
  '‘새’와 ‘새로운’은 둘 다 가방을 꾸미지만 만들어지는 방식이 다르다. 숫자를 꾸미는 경우만으로 관형사 전체를 다뤘다고 볼 수 없다.'),
 ('R02','일반 부사의 종류와 수식 범위','세부 명세 부족','우선',
  'G_ADJ_ADVERB G_PRON_DEICTIC G_LEX_ONOMATOPOEIA G_NEG_SHORT G_CLAUSE_SCOPE', [43,203,204],
  '부사화·지시·상징·부정의 일부는 있으나 문장 전체와 특정 성분을 꾸미는 부사의 차이, 부사의 겹침을 한 체계로 정리한 계약은 없다. 부사 자체가 전혀 없다는 뜻은 아니다.',
  '아마 빨리 끝날 거야.',
  '‘아마’는 추측, ‘빨리’는 끝나는 방식에 관계한다. 같은 부사라는 이유로 같은 위치나 범위로 처리하면 안 된다.'),
 ('R03','의존명사의 일반 체계','세부 명세 부족','우선',
  'G_BOUND_NOUN_GEOT G_NUMERAL_COUNTER G_CLAUSE_NOMINAL', [42,43,143],
  '것 구성과 수량 단위에 집중되어 있다. 수·줄·바·데 등으로 범위를 넓히는 목록과 결합 제약을 공통 계약에서 확인하지 못했다. 명사절과 의존명사구를 구별하겠다는 상위 설계는 존재한다.',
  '갈 수 있어. / 갈 줄 알아. / 갈 곳이 있어.',
  '비슷한 모양이라도 능력·방법을 앎·장소라는 서로 다른 내용을 보존해야 한다.'),
 ('R04','동사 이외의 단어 형성','세부 명세 부족','다음',
  'G_VERB_COMPOUND G_VERB_DERIVED G_ADJ_ADVERB G_LEX_PROTECTED G_LEX_SENSE', [44,149,150],
  '동사의 합성·파생과 일부 부사화는 있으나 명사·형용사 등 전체 품사의 접두·접미·합성 관계를 다루는 공통 구조가 명시되지 않았다. 긴 단어를 보호하는 기능은 단어 형성 분석 전체와 다르다.',
  '풋사과 / 헛웃음 / 높이',
  '단어를 통째로 보존하는 일과 안에서 뜻이 어떻게 만들어지는지 구분하는 일은 별개다.'),
 ('R05','품사 판정과 품사 통용의 기준','세부 명세 부족','우선',
  'G_PRED_KIND G_LEX_SENSE G_TAG_MAPPING G_ANALYSIS_ALTERNATIVES', [42,43,44],
  '품사 태그 대응과 분석 후보를 보존하는 설계는 있다. 그러나 품사별 판정 기준, 동음어·다의어·품사 통용을 어떤 근거로 나눌지의 공통 문헌 대조표는 없다.',
  '다른 사람 / 생각이 다르다.',
  '겉모양이나 분석기의 이름표만으로 모든 문맥의 문법적 지위를 확정하면 안 된다. 여기서 특정 분석 이론 하나를 정답으로 강제하지 않는다.'),
 ('R06','문장 구조의 까다로운 하위 유형','세부 명세 부족','우선',
  'G_CLAUSE_COMPONENT G_CLAUSE_EMBED G_VERB_ARGFRAME G_PARTICLE_SUBJECT G_PARTICLE_OBJECT', [44,45,189,190],
  '문장 성분과 내포 관계는 설계되어 있다. 이중주어·이중목적어·서술절처럼 분석이 갈리는 구성의 별도 처리 기준은 확인하지 못했다. 특히 내포절 열거에는 서술절이 명시되지 않는다.',
  '코끼리는 코가 길다.',
  '주제, 주어, 서술 관계를 어떤 방식으로 표현할지 정하고 다른 분석 가능성도 남겨야 한다. 문장 성분이라는 항목 하나만으로 해결된 것은 아니다.'),
 ('R07','비과거·시간 기준의 체계','세부 명세 부족','우선',
  'G_TAM_SLOTS G_TAM_PAST G_TAM_PROSPECTIVE G_TAM_ADNOMINAL G_LEX_DATE G_TIME_REFERENCE', [45],
  '과거·전망·관형절 시간·상대날짜 항목은 있으나 비과거 해석과 발화시·사건시·기준시의 결속을 공통으로 다룰 구체 계약은 부족하다. 시간을 전혀 다루지 않는 것은 아니다.',
  '내일 떠나. / 지금 떠나.',
  '문장 끝 모양이 같아도 가리키는 시간이 다를 수 있다. 어미 하나만 지키는 검사로 시간 의미 보존을 다 보장할 수 없다.'),
 ('R08','일반 진술·명령·청유의 균형','분할 균형 재검토','우선',
  'G_MOOD_FUNCTION G_END_FINAL G_Q_POLAR G_Q_WH G_NEG_PROHIBITIVE G_GE_HA_ORDER G_GE_HA_PROPOSAL', [45,46],
  '의문 관련 항목은 세밀하지만 일반 진술·명령·청유는 큰 항목이나 특정 구성에 흩어져 있다. 모두 누락됐다고 할 수는 없으나 문장 유형 간 세분화 수준이 다르다.',
  '문을 닫아. / 문을 닫자. / 문을 닫았어.',
  '시키기·함께 하자고 하기·사실 알리기를 같은 상세 수준에서 확인할 대조표가 필요하다.'),
 ('R09','문장을 넘는 담화 결속','독립 체계 없음','범위 결정',
  'G_PRON_DEICTIC G_PRON_REFLEXIVE G_CLAUSE_ELLIPSIS G_LEX_INTERJECTION', [46,221,229],
  '지시·재귀·생략의 일부는 있지만 여러 문장 사이 대용·화제 이어짐·담화 표지·일관성을 맡는 공통 구조는 없다. 단문 입력만 주장한다면 일부는 범위 밖으로 명시할 수 있다.',
  '민수가 상자를 옮겼다. 그는 그것을 열었다.',
  '‘그’와 ‘그것’이 앞 문장의 무엇인지 이어져야 한다. 재귀대명사 자기의 선행사 설계만으로 전체 담화를 담당하지 못한다.'),
 ('R10','대화 참여자와 차례 사이의 기능','독립 체계 없음','범위 결정',
  'G_MOOD_FUNCTION G_HON_ADDRESSEE G_REGISTER_VARIATION G_LEX_INTERJECTION', [90,228,229,230],
  '말높임·발화 기능의 특징은 있으나 화자 교대, 요청에 대한 응답, 참여자 관계를 문장 밖에서 공급하는 공통 대화 계약은 없다. 연구가 문맥 없는 단문 변환이면 처리 불가를 명시해야 한다.',
  '가: 지금 나가도 될까요? / 나: 네.',
  '짧은 ‘네’가 무엇에 동의하는지는 앞 차례와 연결된다. 예/아니오 표면만으로 전체 기능을 판정할 수 없다.'),
 ('R11','음운 체계와 개별 음운 과정','포괄 체계 없음','현재 범위 밖 가능',
  'G_REALIZATION_CONTEXT G_REALIZATION_ALLOMORPH G_REALIZATION_CONTRACTION G_REALIZATION_PROSODY', [41,42,96,97],
  '결합 환경·이형태·축약·텍스트 운율 한계는 있지만 자음·모음 체계와 음운 과정 전반을 개별 명세한 틀은 아니다. 텍스트 방언 생성에 모두 필요한 것은 아니며 음성 생성까지 지원한다고 주장할 수 없다.',
  '표기는 같아도 실제 발음의 조건은 따로 확인한다.',
  '문법책의 모든 음성학 내용을 KG에 넣자는 결론은 아니다. 이번 연구에 필요한 표기·활용과 음성 연구 범위를 구분하자는 뜻이다.'),
]

GAPS += [
 ('R12','정보 구조·분열문','세부 체계 없음','우선',
  'G_PARTICLE_TOPIC G_PARTICLE_FOCUS', [],
  '원목차 4.1.2.2와 4.10은 정보 구조를 명시한다. 현재는 은/는과 초점 보조사 일부만 있고, 구정보·신정보·분열문의 별도 구조는 없다. 분열문 전용 계약은 확인하지 못했다.',
  '민수가 상자를 옮겼어. / 상자를 옮긴 사람은 민수야.',
  '사건 참여자가 같아도 무엇을 새 정보로 강조하는지는 달라질 수 있다. 표면 단어 보존만으로 충분한지 확인해야 한다.'),
 ('R13','어휘상과 문법상의 결합','세부 명세 부족','우선',
  'G_TAM_ASPECT G_AUX_PROGRESS G_AUX_STATE G_LEX_SENSE', [],
  '원목차 4.6.6–4.6.7의 어휘상과 문법상 관계를 전담하는 계약은 없다. 진행·완료 보조구성은 있지만 사건 자체의 성격과의 결합 제약은 구체화되지 않았다.',
  '걷고 있다. / 의자에 앉아 있다.',
  '앞은 진행 중인 행동, 뒤는 앉은 결과 상태로 읽을 수 있다. 단순히 있다라는 글자나 상 이름 하나로 묶지 않아야 한다.'),
 ('R14','선택·메아리 의문·자문','세부 명세 부족','우선',
  'G_Q_POLAR G_Q_WH G_Q_RHETORICAL G_MOOD_FUNCTION', [],
  '원목차 4.4.2.3–4.4.2.5에는 별도 하위 유형이 있다. 현재는 판정·설명·수사적 기능에 집중되어 있고 선택지 집합, 되묻기, 혼잣말 질문의 전용 구별은 없다.',
  '차로 갈까, 걸어갈까? / 가: 내일 떠나. 나: 내일?',
  '예/아니오를 묻는지, 어느 선택지인지, 들은 내용을 되묻는지를 구별해야 한다. 새 틀을 몇 개로 나눌지는 본문 대조 후 결정한다.'),
 ('R15','이중 부정·부정극어·부정 질문','세부 명세 부족','우선',
  'G_NEG_SCOPE G_NEG_SHORT G_NEG_LONG G_Q_POLAR G_LEX_INTERJECTION', [],
  '원목차 4.9.2.4와 4.9.3.1–4.9.3.3의 세부 범주다. 부정 범위라는 상위 항목은 있지만 이중 부정의 해석, 부정극어의 허용 환경, 부정 질문과 답의 연결 조건은 충분히 명시되지 않았다.',
  '가지 않은 것은 아니야. / 아무도 오지 않았어.',
  '부정 표지가 있다는 사실만으로 문장의 긍정·부정 내용과 범위가 정해지지 않는다. 반드시 조건과 문맥을 함께 확인한다.'),
 ('R16','어순과 정보·역할 보존','세부 명세 부족','우선',
  'G_CLAUSE_COMPONENT G_VERB_ARGFRAME G_PARTICLE_TOPIC G_PARTICLE_FOCUS', [],
  '원목차 4.1.3의 어순을 전담하는 계약은 없다. 논항·성분 관계 보존은 명시했지만 이동에 따른 허용 조건과 정보 구조 효과는 별도 정의되지 않았다.',
  '민수가 영희를 도왔다. / 영희를 민수가 도왔다.',
  '누가 누구를 돕는지는 같게 유지하면서도 강조·문맥 적합성은 달라질 수 있다. 자유로운 재배치를 항상 같은 의미로 승인하면 안 된다.'),
]

DIVISIONS = [
 ('D01','문법 현상과 프로그램 기능의 혼합','확인된 분류 성격 차이',
  'G_TAG_MAPPING G_TOKEN_ALIGNMENT G_LEX_RETRIEVE G_INVARIANT_AUDIT G_ANALYSIS_UNSUPPORTED',
  '태그 맞추기·글자 위치 기록·검색·결과 검사는 프로그램 설계다. 문법 규칙 수와 같은 단위로 세면 136의 의미가 흐려진다.',
  '삭제보다 문법 내용 / 처리 기능을 분리해 설명하는 것이 우선이다.'),
 ('D02','하위 항목과 묶음 창구를 함께 계수','확인된 집계 중첩',
  'G_CASE G_COP G_HON G_LEMMA G_MOOD G_MORPH_REALIZATION G_NUMERAL G_SCOPE G_TAM G_TIME_REFERENCE G_WH',
  '11개는 여러 항목을 연결하는 AggregateInterface다. 예를 들어 G_TAM을 별도의 시제 규칙 하나로 더 세면 실제 책임 수와 문법 현상 수를 혼동한다.',
  '125개 개별 설계 항목과 11개 묶음 창구를 따로 보고한다. 125개도 모두 같은 종류의 언어 규칙은 아니다.'),
 ('D03','과거·완료·중복 과거를 한 항목에 둠','분해 수준 검토',
  'G_TAM_PAST G_TAM_ASPECT',
  '시간 위치와 사건 상태가 한 계약에 함께 있다. 원래 계약은 중복 과거를 함부로 줄이지 말라고 명시하므로 이미 잘못 동일시했다고 판정할 수 없다.',
  '상위 항목을 유지하더라도 과거 / 완료 해석 / 중복 과거의 조건·대조 예문은 따로 확인한다.'),
 ('D04','진행과 점진 변화의 묶음','분해 수준 검토',
  'G_AUX_PROGRESS G_TAM_ASPECT',
  '제목에는 진행이라고 되어 있지만 match와 output은 진행/점진 변화의 구별을 요구한다. 제목 하나만 읽으면 세부 의미를 놓친다.',
  '바로 오류로 처리하지 않고 상위 이름과 하위 기능을 일치시키는 방안을 검토한다.'),
 ('D05','호격과 높임 요의 묶음','표준어·지역 용법 경계 재검토',
  'G_PARTICLE_VOCATIVE G_HON_ADDRESSEE',
  '호격을 표시하는 기능과 청자 대우를 나타내는 기능을 한 제목에 넣었다. 원래 block은 서로 다른 요 출현을 합치지 못하게 한다. 방언 자료의 호칭 뒤 요를 표준어 호격 범주로 일반화해서는 안 된다.',
  '표준어 기준과 해당 지역 자료를 각각 확인하고, 호칭 자리와 높임 기능을 별도 속성으로 설명한다. 이번에 원문 D07·D05를 재검증하지 않았다.'),
 ('D06','관형형·관형절 항목의 겹침','중복 오류로 확정하지 않음',
  'G_ADJ_ADNOMINAL G_END_ADNOMINAL G_CLAUSE_RELATIVE',
  '형용사의 활용, 어미 형태, 절과 명사의 관계라는 서로 다른 층이다. 기준 자료도 품사·어미와 문장 성분을 구별한다.',
  '지우기보다 각 항목이 판정하는 것과 넘겨주는 것을 명시한다.'),
 ('D07','있다·없다·계사 항목','합병 오류로 확정하지 않음',
  'G_ADJ_EXISTENCE G_PRED_KIND G_NEG_COPULA',
  '제목은 여러 부류를 묶지만 실제 block에는 계사와 존재사를 같다고 보지 말라는 요구가 있다. 서술격 조사/계사 등 학설 차이도 문법 오류와 구별해야 한다.',
  '같은 부류로 판정했다고 오해하지 않게 이름·품사·기능의 구별을 보여 준다.'),
 ('D08','표준어 공통 기준과 방언 대응의 혼합','설계 층위 재검토',
  'G_PARTICLE_OBJECT G_REGISTER_MAP G_QUOTE_CONTRACTION G_REALIZATION_ORTHO',
  '목적격과 로 변이, 지역 화계 대응, 카다·쿠다 축약 등은 공통 분석과 목표 방언 실현이 맞닿는 항목이다. 136개를 순수 표준어 문법서 규칙이라고 부를 수 없는 직접적인 사례다.',
  '공통 문법 현상 / 지역별 대응 지식 / 실행 정책을 구분하되 원래 ID는 당장 바꾸지 않는다.'),
]

def main():
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out=HERE/'private'/stamp;out.mkdir(parents=True)
    initial_hash=sha(DESIGN);d=load(DESIGN)
    atoms=[x for x in d['atoms'] if x['id'].startswith('G_')]
    assert len(atoms)==136 and len({x['id'] for x in atoms})==136
    chapters={x['number']:x['title'] for x in d['roles']['grammar']['chapters']}
    modules={int(x['number']):x['name'] for x in d['root']['module_catalog']}
    ids={x['id'] for x in atoms}
    for row in GAPS:
        assert set(row[4].split()) <= ids
    for row in DIVISIONS:
        assert set(row[3].split()) <= ids
    rows=[]
    engineering={'G_TAG_MAPPING','G_TOKEN_ALIGNMENT','G_LEX_RETRIEVE','G_INVARIANT_AUDIT','G_ANALYSIS_UNSUPPORTED','G_FEATURE_UNKNOWN','G_ANALYSIS_ALTERNATIVES'}
    wiki={'D03','D04','D05','D06'}
    for a in atoms:
        refs=a.get('source_refs',[]);srcs={x['document_id'] for x in refs}
        category='문법 현상·처리 계약'
        if a['kind']=='AggregateInterface': category='묶음 창구'
        elif a['id'] in engineering: category='프로그램 설계 중심'
        else: category='문법 현상·처리 계약'
        gs=[x[0] for x in GAPS if a['id'] in x[4].split()]
        ds=[x[0] for x in DIVISIONS if a['id'] in x[3].split()]
        topic,pages=CHAPTER_REF[a['chapter']]
        if category in ('묶음 창구','프로그램 설계 중심'):
            correspondence='직접적인 문법 규칙 대응 대상 아님'
            assessment='관련 문법을 연결·처리하는 설계다. 이 항목 자체를 문법책의 규칙 하나와 1:1 대조하지 않는다.'
        else:
            correspondence='주제 대응 확인 · 정의/조건 인증 아님'
            assessment='기준 자료에서 관련 영역을 확인했다. 이 설계의 입력·조건·예외 전체가 문헌에서 검증되었다는 뜻은 아니다.'
        r={'id':a['id'],'title':a['title'],'kind':a['kind'],'category':category,
           'old_chapter':a['chapter'],'old_title':chapters[a['chapter']],'old_path':a['path'],
           'module':a['_module'],'module_title':modules[a['_module']],'display_path':a['_display_path'],
           'reference_topic':topic,'reference_pdf_pages':pages,'correspondence':correspondence,'assessment':assessment,
           'existing_match':a.get('match',[]),'existing_output':a.get('output'),
           'source_refs':refs,'source_class':'문헌 연결 없음' if not srcs else ('위키 계통만' if srcs<=wiki else '논문 포함'),
           'reference_book_locator_in_original':False,'gaps':gs,'division_reviews':ds,'example':EXAMPLES.get(a['id'])}
        r['source_class']='문헌 연결 없음' if not srcs else r['source_class']
        rows.append(r)
    counts={'total':len(rows),'atomic':sum(a['kind']!='AggregateInterface' for a in atoms),
            'interfaces':sum(a['kind']=='AggregateInterface' for a in atoms),
            'with_document_refs':sum(bool(a.get('source_refs')) for a in atoms),
            'without_document_refs':sum(not a.get('source_refs') for a in atoms),
            'wiki_only':sum(r['source_class']=='위키 계통만' for r in rows),
            'kinds':dict(collections.Counter(a['kind'] for a in atoms)),
            'categories':dict(collections.Counter(r['category'] for r in rows)),
            'reverse_review_groups':len(GAPS),'division_review_groups':len(DIVISIONS)}
    transitions=[{'chapter':n,'title':title,'targets':[{'module':m,'title':modules[m],'count':c} for m,c in sorted(collections.Counter(a['_module'] for a in atoms if a['chapter']==n).items())]} for n,title in chapters.items()]
    assert sum(t['count'] for x in transitions for t in x['targets'])==136
    toc=crosswalk(load(REF.parent/'original_toc.json'),ids)
    counts['original_toc_numbered_entries']=len(toc)
    counts['original_toc_leaf_entries']=sum(x['leaf'] for x in toc)
    counts['original_toc_leaf_statuses']=dict(collections.Counter(x['status'] for x in toc if x['leaf']))
    save(out/'toc_crosswalk.json',toc)
    save(out/'audit.json',{'counts':counts,'rows':rows,'gaps':GAPS,'division_reviews':DIVISIONS,'chapter_transitions':transitions})
    shutil.copy2(DESIGN,out/'design.snapshot.json')
    save(out/'manifest.json',{'run_id':stamp+'_common_grammar_reference_audit','created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
       'purpose':'136개 공통 설계의 기준 문헌 대응·공백·분할·출처 감사. KG를 수정할지 판단하기 위한 진단.',
       'reviewer':'현재 Codex 대화의 AI 감사자 1명. 사람 또는 독립 검토자 검증 없음.',
       'design_path':str(DESIGN),'design_sha256':initial_hash,'reference_pdf':str(REF),'reference_pdf_sha256':sha(REF),
       'reference_url':REF_URL,'reference_year':2014,'reference_read_scope':{'taxonomy_pdf_pages':[40,41,42,43,44,45,46,47],
       'selected_body_pdf_pages':[89,90,91,96,97,143,149,150,189,201,202,203,204,221,228,229,230],
       'scope_note':'전체 PDF를 추출했으나 전권 정독·136개 의미 조건 전수 검증은 하지 않음. 분류표와 선택 본문 대조.'},
       'provenance':'초기 사용자 대화 2026-10-13에서 한국어 문법 총론1 목차 참고 지시·원목차·범위 결정을 확인. 당시 응답의 2025개정판 안내는 현재 서지 페이지와 일치. 최초 목차→136 대응표는 당시 기록에 없으며 이번에 새로 대조함.',
       'original_toc_path':str(REF.parent/'original_toc.json'),'original_toc_sha256':sha(REF.parent/'original_toc.json'),
       'history_evidence':str(REF.parent/'original_toc_history.json'),'history_evidence_sha256':sha(REF.parent/'original_toc_history.json'),
       'mutations':{'kg':False,'runtime':False,'new_model_calls':0},'criteria':'상위 항목 존재 / 세부 책임 명시 / 근거 위치 / 구현 상태를 분리. 주제 유사성을 문헌 지지로 간주하지 않음.',
       'completion':'136/136 개별 행, 역방향 공백 16개 검토 묶음, 분할 8개 검토 묶음. 언어학적 완전성·정확도 인증 아님.'})
    write_html(out,rows,counts,transitions,d,toc)
    write_archify(out,counts)
    assert sha(DESIGN)==initial_hash
    save(out/'checks.json',{'unique_rows':len(ids),'all_136_mapped':len(rows)==136,'all_review_ids_exist':True,'chapter_counts_sum':136,'design_unchanged':True,'model_calls':0,'kg_changes_by_this_audit':0})
    print(json.dumps({'output':str(out),'counts':counts},ensure_ascii=False))

def anchors(ids): return ' · '.join(f'<a href="#{x}">{x}</a>' for x in ids.split())
def reflink(pages):
    return '<a href="../20261107_reference/nikk_grammar_2014.pdf#page='+str(pages[0])+'">2014 보고서 PDF '+','.join(map(str,pages))+'쪽</a>'

def write_html(out,rows,c,transitions,d,toc):
    gaps=''.join(f'<article id="{id}"><span class="tag">{e(status)} · {e(priority)}</span><h3>{id}. {e(title)}</h3><p>{e(finding)}</p><div class="example"><b>설명용 예문</b><p>{e(example)}</p>{e(why)}</div><p class="small">현재 관련 항목: {anchors(ids)}<br>분류 기준: {reflink(pages) if pages else "2026-10-13 사용자가 제공한 원목차의 위 번호 항목"}. 문헌의 모든 용법을 인증한 결과가 아니다.</p></article>' for id,title,status,priority,ids,pages,finding,example,why in GAPS)
    divs=''.join(f'<article id="{id}"><span class="tag">{e(status)}</span><h3>{id}. {e(title)}</h3><p>{e(finding)}</p><p><b>수정 전 판단:</b> {e(action)}</p><p class="small">{anchors(ids)}</p></article>' for id,title,status,ids,finding,action in DIVISIONS)
    cards=[]
    for r in rows:
        ex=r['example'];extext=''
        if ex:
            if isinstance(ex,dict): extext='<b>'+e(ex['text'])+'</b><p>'+e(ex['explanation'])+'</p>'
            else: extext=' — '.join(e(x) for x in ex)
        source=' / '.join(e(x['document_id'])+' PDF '+','.join(map(str,x.get('pdf_pages',[])))+'쪽' for x in r['source_refs']) or '이 항목의 source_refs는 비어 있음'
        related=' '.join(f'<a href="#{x}">{x}</a>' for x in r['gaps']+r['division_reviews']) or '이번 주요 검토 묶음에는 없음. 검증 완료 판정이 아님.'
        cards.append(f'''<details class="item" id="{r['id']}" data-cat="{r['category']}" data-source="{r['source_class']}"><summary><span class="tag">{r['category']}</span> {e(r['title'])}<small>{r['id']} · {r['source_class']}</small></summary>
<p><b>어떤 기준과 대조했나:</b> {e(r['reference_topic'])} — {reflink(r['reference_pdf_pages'])}</p>
<p><b>판정:</b> {e(r['correspondence'])}. {e(r['assessment'])}</p>
<div class="example">{extext}<p class="small">이 예문은 이해를 위해 작성한 예시다. 모델 실행·언어적 정답 인증 결과가 아니다.</p></div>
<p><b>실제 설계에서 하겠다고 한 구별:</b> {e(' / '.join(r['existing_match']))}</p>
<p><b>기존 출처:</b> {source}. 표준어 기준서의 항목별 쪽 연결은 없음.</p>
<p><b>분류 이동:</b> 원래 {r['old_chapter']}장 {e(r['old_title'])}({r['old_path']}) → 통합 {r['module']}분야 {e(r['module_title'])}({r['display_path']})</p>
<p><b>함께 볼 문제:</b> {related}</p><p class="small">설계 원본의 상태는 design_blueprint, runtime_active=false. 후속 구현 유무는 이전 연결 공백 감사에서 별도 판정한다.</p></details>''')
    tr=''.join('<tr><td>'+e(str(x['chapter'])+'. '+x['title'])+'</td><td>'+e(' / '.join(str(t['module'])+'. '+t['title'] for t in x['targets']))+'</td><td>'+str(sum(t['count'] for t in x['targets']))+'</td></tr>' for x in transitions)
    kinds=''.join(f'<tr><td>{e(k)}</td><td>{v}</td></tr>' for k,v in c['kinds'].items())
    source_policy=e(d['root']['common_grammar_source_limit'])
    toc_html=''.join(f'<details class="toc-item" id="toc-{x["number"]}"><summary>{e(x["number"]+" "+x["title"])} <span class="tag">{e(x["status"])}</span></summary><p>{e(x["note"])}</p><p>{anchors(" ".join(x["common_ids"])) or "이 하위 항목을 전담하는 공통 계약을 확인하지 못함"}</p><p class="small">목차 제목과 기존 계약의 대응이며 책 본문의 정의·조건 검증은 아님. 이번에 작성한 대응으로 원래 작성자의 개별 차용 경로를 확정하지 않는다.</p></details>' for x in toc if x['leaf'])
    body=f'''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>136개 문법 틀 · 기준 자료 대조</title><style>{CSS}</style>
<header><div class="eyebrow">수정 전 진단 · 2026년 11월 7일</div><h1>136개면 문법을<br>충분히 담았을까요?</h1><p class="lead">현재 136개를 한국어 공통 문법의 완전한 목록으로 쓰기에는 부족합니다. 큰 문법 영역은 상당수 들어 있지만 세부 구분이 불균형하고, 프로그램 기능과 묶음 창구도 같은 개수에 섞여 있습니다.</p><p>이번에는 원래 설계 136개 전부를 공개 문법 체계와 대조했습니다. <b>KG·실행 코드를 수정하지 않았고, 새 문장을 생성하지 않았습니다.</b> 문법 조건 전부가 옳다는 인증도 아닙니다.</p><a class="button" href="overview.html">Archify 전체 그림 보기 →</a></header>
<nav><a href="#basis">기준 자료</a><a href="#toc">목차 반영</a><a href="#gaps">빠진 세부 구분</a><a href="#division">잘못 나눴나?</a><a href="#evidence">근거 상태</a><a href="#all">136개 전체</a><a href="#next">다음 판단</a></nav><main>
<section id="basis"><h2>1. 어떤 자료를 기준으로 삼았나</h2><p>이번 질문은 단어의 표준어 여부보다 <b>한국어 문법을 어떤 체계로 분류하고 설명할 것인가</b>에 가깝습니다. 따라서 맞춤법 규정만으로 비교하지 않고 국립국어원의 참조 문법 개발 자료를 기준으로 삼았습니다.</p>
<table><thead><tr><th>자료</th><th>이번 역할</th><th>확인 범위와 한계</th></tr></thead><tbody>
<tr><td>『한국어 문법 총론 1』<br>2026-10-13 사용자 제공 원목차</td><td>최초 출발점 복원·하위 범위 대조</td><td>번호 항목 224개, 최하위 171개. 당시 안내한 <a href="https://m.yes24.com/goods/detail/152957561">2025개정판 서지</a>도 확인했다. 책 본문 정독과는 구별한다.</td></tr>
<tr><td><a href="{REF_URL}">국립국어원, 2014년 표준 국어 문법 개발</a><br>유현경 외, 2014</td><td>음운·형태·통사·담화의 범주 대조</td><td>PDF40–47쪽의 분류표와 선정 본문을 읽었다. 표는 앞 단계 체계를 제시하며 본문이 이후 수정 필요를 밝힌다. 최신 완성판이나 법적 정답표가 아니다.</td></tr>
<tr><td><a href="{BOOK_URL}">국립국어원의 단행본 안내</a><br>2025-04-23 답변</td><td>후속 기준서 확인</td><td>『한국어 표준 문법』(집문당)을 안내한다. 이번에 그 책 전권을 읽었다고 주장하지 않는다. 구입·원문 확보 후 판본을 고정할 대상이다.</td></tr>
<tr><td><a href="{DICT_URL}">국립국어원 한국어기초사전 ‘새’</a></td><td>분류 차이의 실제 예</td><td>‘새’를 관형사로 제시한다. 관형형 어미 항목이 있다고 모든 관형사를 다룬 것은 아님을 보여 준다.</td></tr></tbody></table>
<p>기준 보고서 자체도 문법의 배열·용어에 여러 관점이 있음을 인정합니다(PDF40·91쪽). <b>목차가 다르다는 이유만으로 오류라고 판정하지 않았습니다.</b> 아래 공백은 원문과 설계의 대조에 따른 이번 감사자의 판단입니다.</p></section>
<section id="toc"><h2>2. 처음에는 책의 목차만 가져온 것이 맞나?</h2><p><b>맞습니다. 출발점은 『한국어 문법 총론 1권』의 목차였습니다.</b> 초기 대화 원문에서 책 이름, 목차를 참고하자는 지시, 사용자가 붙인 전체 목차를 확인했습니다.</p>
<table><thead><tr><th>2026-10-13의 실제 기록</th><th>의미</th></tr></thead><tbody><tr><td>21:10 KST · 온라인 서점에서 발견한 총론 목차를 기반으로 설계하자는 제안</td><td>처음 참고할 책 확인</td></tr><tr><td>22:30 KST · 목차 전체를 검토 대장으로 삼자는 제안을 사용자께서 수정</td><td>하위 요소·관계·중점 범위의 논의를 위한 참고 자료</td></tr><tr><td>22:39 KST · 원목차를 직접 붙여 주심</td><td>번호 항목 224개, 최하위 항목 171개 복원</td></tr><tr><td>22:39·22:47 KST · 1장 제외, 2장 상세 논의 보류, 3장부터 설명 진행</td><td>모든 장을 같은 수준으로 먼저 구축하자는 계획은 아니었음</td></tr></tbody></table>
<p><b>책의 목차를 참고한 것은 사실이지만, 목차 항목을 그대로 136개로 옮긴 것은 아닙니다.</b> 제공 목차는 언어 일반·음운·형태·통사의 4장입니다. 이후 공통 설계는 16장으로 재구성됐고, 통합 화면은 다시 12분야로 배치됐습니다. 다음 16→12 이동은 실제 ID로 확인됩니다. 책 목차→136은 이번 감사의 주제 대응이며 과거 개별 작성 경로를 확정하는 것은 아닙니다.</p>
<div class="warn"><b>이전 설명의 정정:</b> 설계 파일의 ‘전체 본문 미제공’만 확인하고 목차 차용 여부를 확답하지 못했던 설명은 불충분했습니다. 초기 대화까지 확인한 결과, 목차를 참고한 사실과 특정 책 이름을 복원했습니다. 책의 규칙·정의·예외를 그대로 전사했다는 기록은 없습니다.</div>
<details><summary>원래 설계의 직접 기록 보기</summary><p>common_grammar_source_limit: {source_policy}</p><p>index_tree_policy: {e(d['root']['atomic_definition']['index_tree_policy'])}</p></details>
<table><thead><tr><th>원래 공통 설계 16장</th><th>통합 화면 12분야</th><th>항목 수</th></tr></thead><tbody>{tr}</tbody></table>
<p>예를 들어 보조용언 13개와 사동·피동 8개는 통합 9분야로, 시제·상·양태 7개와 부정 5개는 통합 8분야로 모였습니다. 분류 이동 자체가 문법 지식 추가·구현을 뜻하지는 않습니다.</p>
<p><b>어디까지 반영됐나:</b> 형태소·단어, 품사, 논항·절, 시제·상·양태, 부정·높임 등은 공통 설계와 주제가 대응합니다. 그러나 일반 관형사, 선택·메아리 의문, 어휘상, 정보 구조·분열문 등은 전용 항목이나 세부 조건이 부족합니다. 세부 설계의 출처는 방언 자료 D01–D07로 되어 있으며 책 본문 위치는 연결되어 있지 않습니다.</p>
<p class="small">조사한 범위: 현재 design.json, 이전 HTML 추출본 root_full.json·dashboard.json, 원본 설계 사본·출처 목록, 초기 KG v3 대화의 관련 사용자 발언. 채팅 조회 도구의 크기 제한 뒤 해당 대화 파일에서 관련 발언만 선별해 복원했다. <a href="../20261107_reference/original_toc_history.json">초기 근거 기록</a></p>
<details><summary>제공 목차의 최하위 171개를 기존 설계와 대조해서 보기</summary><p>224개 번호 항목 중 하위 항목이 없는 171개를 표시합니다. 4개 장 제목은 번호 항목 수에 포함하지 않았습니다. 1장 제외·2장 보류는 당시 결정이며 영구 제외가 아닙니다. 지원률이나 정확도로 계산하지 않습니다.</p>{toc_html}</details></section>
<section id="gaps"><h2>3. 기준 자료에서 거꾸로 찾아본 공백</h2><p>136개 항목의 이름만 기준서에 끼워 맞추면 없는 영역을 놓칩니다. 그래서 기준 자료의 영역에서 출발해 기존 설계의 책임을 찾아봤습니다. 아래 <b>16개는 검토 묶음 수</b>이며 ‘빠진 문법 규칙이 정확히 16개’라는 뜻은 아닙니다.</p><div class="grid">{gaps}</div></section>
<section id="division"><h2>4. 잘못 나눈 것과 다시 나눌 필요가 있는 것은 다르다</h2><p>현행 분류는 문법책을 위한 체계와 프로그램 처리를 위한 체계가 섞여 있습니다. 확인된 집계 문제와 해석이 필요한 분할 후보를 구분했습니다. 원래 계약에 구별이 명시된 항목은 이름이 비슷하다고 중복 오류로 판정하지 않았습니다.</p><div class="grid">{divs}</div></section>
<section id="evidence"><h2>5. 출처가 있다고 모두 검증된 것은 아니다</h2><div class="stats"><div><strong>136</strong>전체 설계 항목</div><div><strong>125 + 11</strong>개별 설계 + 묶음 창구</div><div><strong>121 / 136</strong>항목 안에 문헌 연결 있음</div><div><strong>15 / 121</strong>연결이 위키 계통뿐</div></div>
<p>문헌 연결이 있는 121개는 모두 D01–D07 중 하나 이상을 가리킵니다. 이 중 15개는 D03–D06의 같은 위키 계통만 연결합니다. 이는 <b>기록된 출처의 성격</b>을 센 것이며, 맞거나 틀린 항목 수가 아닙니다. 예를 들어 수사 역할·감탄사 기능·명사 보호 등에 공통 문법 근거를 보강할 필요가 있습니다.</p>
<p>출처가 비어 있는 15개는 묶음 창구 11개와 태그 대응·문자 위치·결과 검사·미지원 처리 4개입니다. 프로그램 관리 설계에 문법책 쪽수가 없는 것 자체를 언어학 오류로 세면 안 됩니다.</p>
<p><b>공통 기준서의 항목별 위치 연결은 현재 136개 모두에서 확인되지 않았습니다.</b> 이번 표의 기준 자료 대응은 새 감사 기록이며 KG에 넣지 않았습니다. 방언 논문의 사례가 있어도 표준어 전반의 정의·예외를 입증하는지 별도 확인해야 합니다.</p>
<details><summary>136개 내부 종류별 실제 개수</summary><table><thead><tr><th>원본 종류</th><th>개수</th></tr></thead><tbody>{kinds}</tbody></table><p>Construction도 완성된 실행 규칙이라는 뜻이 아니다. 원본은 설계 상태다.</p></details></section>
<section id="all"><h2>6. 기존 136개를 하나씩 확인하기</h2><p>각 카드에 기존 역할, 기준 자료의 관련 위치, 근거 상태, 이번 재검토 사항을 연결했습니다. <b>주제 대응은 정의·조건 전체의 검증과 다릅니다.</b> 136개를 모두 확인했다는 뜻은 여기에서 빠진 행이 없다는 뜻입니다.</p>
<div class="tools"><input id="search" placeholder="이름·ID·관련 문법 검색" aria-label="항목 검색"><select id="cat" aria-label="항목 종류"><option value="">모든 종류</option><option>문법 현상·처리 계약</option><option>프로그램 설계 중심</option><option>묶음 창구</option></select><select id="source" aria-label="출처 종류"><option value="">모든 출처</option><option>논문 포함</option><option>위키 계통만</option><option>문헌 연결 없음</option></select><span id="count"></span></div>{''.join(cards)}</section>
<section id="next"><h2>7. 다음에 무엇을 결정해야 하나</h2><p>지금 필요한 것은 항목 수를 임의로 늘리는 작업이 아니라, <b>공통 문법의 기준·범위·세분화 수준을 먼저 고정하는 일</b>입니다. 현재 틀은 좁은 방언 생성 연구의 출발점으로 재사용할 수 있지만, 한국어 문법 전영역을 검증했다는 근거로 쓸 수 없습니다.</p>
<ol><li>서명·판본이 고정된 참조 문법과 이번 공개 보고서를 연결한다. 복원한 원목차와 본문을 구별해 항목별 정의·조건의 근거를 추가한다.</li><li>우선 항목 R01–R08 및 R12–R16의 정의·조건·예외를 본문에서 대조하고, 기존 항목 보완으로 충분한지 새 항목이 필요한지 결정한다. 담화·음성은 목표 범위에 따라 포함/제외를 명시한다.</li><li>사람이 검토한 기준 목록과 기존 136개 사이에 빠짐·중복·보류가 남지 않는 대응표를 고정한다. 근거가 없으면 unknown으로 남긴다.</li><li>그 다음 KG 전수 예문 검증을 설계한다. 각 지식에 대해 적용 예·비적용 예·모호한 예·결합 예를 연결한다. 기존 노드를 모두 지나간다는 것만으로 누락 문법이나 언어적 정확성을 증명하지는 못한다.</li></ol>
<p><b>종료 기준:</b> 선정 범위의 모든 기준 항목이 대응·보완 후보·범위 제외·판단 보류 중 하나에 배정되고 근거 위치가 남아야 한다. 불일치가 반복되면 예문을 더 만드는 대신 분류나 분석 계약부터 재검토한다.</p>
<p><b>검토자와 사용자:</b> 이번은 AI 감사자 1명의 근거 대조다. 독립 언어학 검토·사람 평가를 받은 결과가 아니다. 이번 읽기·정리는 별도 승인 없이 완료했으며, 실제 KG 수정이나 연구 범위 확대는 실행하지 않았다.</p>
<p><a href="../../../link_gap_audit_20261107/private/20261107T042114917700Z/report.html">앞선 107개·27개 연결 공백 감사</a> · <a href="audit.json">재현용 대응 데이터</a> · <a href="manifest.json">범위·해시·확인 한계</a></p></section></main>
<script>const cards=[...document.querySelectorAll('.item')];const q=document.querySelector('#search'),cat=document.querySelector('#cat'),src=document.querySelector('#source');function filter(){{let n=0;cards.forEach(c=>{{c.hidden=!(c.textContent.toLowerCase().includes(q.value.toLowerCase())&&(!cat.value||c.dataset.cat===cat.value)&&(!src.value||c.dataset.source===src.value));if(!c.hidden)n++}});document.querySelector('#count').textContent=n+' / 136개';}}[q,cat,src].forEach(x=>x.addEventListener('input',filter));function jump(){{let x=document.getElementById(decodeURIComponent(location.hash.slice(1)));if(x?.classList.contains('item')){{q.value=cat.value=src.value='';filter();x.open=true;x.scrollIntoView()}}}}window.addEventListener('hashchange',jump);filter();jump();</script></html>'''
    (out/'report.html').write_text(body,encoding='utf-8')

CSS='''*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:80px}body{margin:0;color:#203336;background:#f3f6f3;font:17px/1.8 "Segoe UI","Malgun Gothic",sans-serif;word-break:keep-all;overflow-wrap:anywhere}header,main,nav{max-width:1160px;margin:auto}header{padding:65px 34px 45px}h1{font-size:clamp(34px,5.2vw,64px);line-height:1.18;letter-spacing:-2px}h2{font-size:28px;line-height:1.45}h3{font-size:21px;line-height:1.5}.eyebrow{color:#3f6965;font-weight:700}.lead{font-size:22px;max-width:950px}nav{position:sticky;top:0;z-index:2;background:#e1ebe6;padding:13px 24px;display:flex;gap:18px;flex-wrap:wrap;border-radius:14px}a{color:#21665d;text-underline-offset:4px}.button{display:inline-block;background:#245c54;color:white;border-radius:12px;padding:12px 20px;text-decoration:none}main{padding:10px 24px 70px}section{margin:34px 0;padding:30px;background:white;border:1px solid #dce5df;border-radius:20px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}article{background:#f7f9f6;border:1px solid #dce5df;border-radius:14px;padding:23px;scroll-margin-top:90px}.example{padding:16px;background:#e9f2ec;border-left:4px solid #4f8c72;border-radius:6px}.warn{padding:20px;background:#fff1d8;border-left:4px solid #a77825;border-radius:6px}.tag{font-size:13px;border-radius:6px;background:#e4ece7;padding:4px 7px}.small,small{font-size:13px;color:#536561}small{display:block}table{width:100%;border-collapse:collapse;font-size:15px;table-layout:fixed}th,td{padding:12px;border-bottom:1px solid #dae3dc;text-align:left;vertical-align:top}th{background:#edf2ed}details{margin:12px 0;border:1px solid #dce5df;border-radius:12px;padding:17px}summary{cursor:pointer;font-weight:700}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.stats div{padding:17px;background:#edf4ed;border-radius:12px;font-size:14px}.stats strong{display:block;font-size:29px}.tools{display:flex;gap:10px;flex-wrap:wrap;margin:24px 0}input,select{padding:12px;font:inherit;max-width:100%;border:1px solid #b7c8bf;border-radius:8px}input{flex:1;min-width:160px}[hidden]{display:none!important}@media(max-width:760px){header{padding:32px 20px}.lead{font-size:19px}main{padding:5px 12px}section{padding:20px 16px}.grid{grid-template-columns:1fr}.stats{grid-template-columns:1fr 1fr}nav{position:static;margin:0 12px;gap:10px;font-size:14px}table{font-size:12px}th,td{padding:7px}h2{font-size:24px}.tools>*{width:100%}}'''

def write_archify(out,c):
    t='''# 136개는 완성된 문법책이 아니라 연구용 설계 목록입니다 {#grammar-reference-audit}

**큰 문법 영역은 들어 있지만, 136개만으로 한국어 문법 전체를 충분히 담았다고 말할 수 없습니다.** 기존 설계를 보존한 채 범위와 근거를 먼저 고정해야 합니다.

- 개별 설계 125개와 묶음 창구 11개를 합한 수입니다.[](source:design)
- 문법 현상과 검색·검사 같은 프로그램 기능이 섞여 있습니다.[](source:design)
- 문헌 연결 121개는 지정 방언 자료를 가리킵니다. 표준어 기준서의 항목별 근거와 다릅니다.[](source:audit)
- 처음에는 한국어 문법 총론 1권의 목차를 참고했습니다. 초기 사용자 대화에서 확인했습니다.[](source:audit)

@answer scope="2026-11-07 · 설계 136개 전수 분류 대조 · 의미 조건 전수 인증 아님 · KG 수정 없음"
@meta locale=ko style=clean quality_profile=showcase
@source design title="보존한 원래 공통 설계" path=design.snapshot.json
@source audit title="항목별 대응과 감사 판정" path=audit.json
@source grammar title="국립국어원 2014년 표준 국어 문법 개발" url=REF_URL

## 무엇을 서로 구별해야 하나요? {#layers}

@architecture id=grammar-layers title="책의 분류와 연구 설계는 역할이 다릅니다"
| book | 문법 기준 자료 | external |
| design | 공통 설계 136개 | database |
| program | 실제 실행 코드 | backend |
| checks | 예문과 사람 검토 | frontend |
| book > design | 범위 대조 |
| design > program | 구현 확인 |
| program > checks | 실제 검증 |

책에 항목이 있다는 것, 설계에 이름이 있다는 것, 코드가 처리한다는 것, 문장이 옳다는 것은 각각 확인해야 합니다. 이번에는 앞의 범위 대조를 했습니다.

## 책의 목차는 어디까지 반영됐나요? {#toc}

| 확인할 것 | 이번에 확인한 상태 |
| --- | --- |
| 처음 참고한 책 | 한국어 문법 총론 1권 · 당시 2025 개정판 안내 |
| 사용자가 제공한 목차 | 번호 항목 224개 · 최하위 171개 |
| 원래 설계의 장별 분류 | 16개 장과 136개 항목이 보존됨 |
| 현재 화면의 분류 | 12개 분야로 재배치됨 |
| 책의 정의·예외를 그대로 옮겼는가 | 이를 입증하는 항목별 대응 기록 없음 |

원래 보조용언 13개와 사동·피동 8개는 한 분야로 모였습니다. 목차 재배치가 문법의 구현이나 검증을 의미하지는 않습니다.[](source:audit)

## ‘관련 항목 있음’과 ‘충분함’의 차이 {#gaps}

| 실제 예 | 기존에 있는 것 | 더 확인할 것 |
| --- | --- | --- |
| 새 가방 / 새로운 가방 | 관형형·명사구 | 관형사와 활용형의 구별 |
| 아마 빨리 끝날 거야 | 일부 부사·작용 범위 | 추측 부사와 방식 부사의 범위 |
| 갈 수 있어 / 갈 줄 알아 | 것·수량 단위 구성 | 다른 의존명사의 조건 |
| 민수가 왔다. 그는 웃었다 | 지시·재귀대명사 | 문장을 넘는 지시 관계 |

설명을 위해 만든 예문입니다. 새 모델 실행이나 정답 인증 결과가 아닙니다. 분류 기준과 해석의 자세한 범위는 상세 보고서에 있습니다.[](source:grammar)

## 비슷한 이름을 모두 합치면 안 됩니다 {#division}

@architecture id=adnominal-views title="같은 구절을 서로 다른 층에서 살핍니다"
| phrase | 예쁜 꽃 | frontend |
| predicate | 형용사의 활용 | backend |
| ending | 관형형 어미 | backend |
| relation | 꽃을 꾸미는 관계 | backend |
| phrase > predicate | 서술어 종류 |
| phrase > ending | 형태 |
| phrase > relation | 문장 구조 |

이 세 항목은 책임을 분리한 설계일 수 있습니다. 반면 검색 기능과 문법 규칙을 같은 개수로 설명하면 범위를 오해하기 쉽습니다.[](source:design)

## 다음 작업의 순서 {#next}

@workflow id=next-checks title="기준을 고정한 다음 전수 예문을 만듭니다"
| reference | 기준·범위 고정 | external |
| crosswalk | 대응·공백 검토 | backend |
| decision | 사람의 판정 | frontend |
| freeze | 검증용 판본 고정 | database |
| examples | 전수 예문 검사 | backend |
| reference > crosswalk | |
| crosswalk > decision | |
| decision > freeze | |
| freeze > examples | |

기존 노드를 모두 지나가도, 원래 빠진 문법은 검사할 수 없습니다. 대응표에서 누락·보류·범위 제외를 먼저 명시해야 합니다.

- [ ] 공통 기준서의 판본과 처리 범위를 고정한다.
- [ ] 관련 항목이 있는 것과 세부 조건이 충분한 것을 구별한다.
- [ ] 공백이 새 항목을 요구하는지 기존 항목 보완으로 되는지 판단한다.
- [ ] 적용·비적용·모호한 예를 포함해 검증한다.
'''.replace('REF_URL',REF_URL)
    (out/'candidate.archify.md').write_text(t,encoding='utf-8')

if __name__=='__main__': main()
