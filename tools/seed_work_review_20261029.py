"""Register this turn's concrete proposals; preserve existing decisions on rerun."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from research_management.work import WorkStore

def main():
    store=WorkStore(ROOT)
    proposals=[
      dict(id='dashboard-20261029',version=1,title='진행·검토·결정 화면 연결',
        before='실험 결과 조회만 가능. 진행 상황과 승인 기록을 한곳에서 확인하기 어려움.',
        after='2초마다 실제 작업 기록 갱신. 완료 수·경과 시간·갱신 지연 표시. 같은 반복 단위의 측정이 3회 이상 쌓이면 남은 시간 범위 표시. 수정안별 채팅/대시보드 결정과 적용 이력 보존.',
        reason='사용자가 실시간 진행 상태와 혼합 승인 방식을 요청함.',
        scope='기존 로컬 대시보드·관리 기록·테스트·작업 절차. KG 내용, 생성 규칙, Qwen 실험 실행은 포함하지 않음.',
        verification='승인 버전 변경 시 재승인, 일괄 저장 원자성, 오래된 화면의 결정 거부, ETA 근거·갱신 지연, 로컬 API 접근 검사.',
        evidence=['2026-10-29 채팅: “이것도 빠르게 작업 범위를 제시해서 구현해줘.”'],lead='현재 작업으로 구현. 자동으로 연구 변경을 적용하는 기능은 없음.'),
      dict(id='retrieval-condition-20261029',version=1,title='카드 순위: 글자 일치를 문법 조건과 분리',
        before='condition이 coda_condition 속성 이름에도 일치하여 목적격 조사 카드가 조건문 관련 점수를 얻음. 필요한 종결·연결 카드가 48개 안에서 밀려나는 사례가 있음.',
        after='허용한 문법 기능 필드의 값만 비교한다. 어절·구성별로 후보와 탈락 이유를 기록한다. 48개 한도는 첫 비교에서는 유지하고, 후보 누락이 남으면 별도 한도 실험안을 제시한다.',
        reason='실제 과거 선별 결과 50개를 재현해 잘못된 점수 경로를 확인함. “카드가 있다”와 “이 문장에 적용 가능하다”는 다름.',
        scope='src/kg_runtime/cards.py의 후보 관련성 계산과 선별 감사 기록. KG 원문·모델·활용 코드는 이 수정안에서 바꾸지 않음.',
        verification='동결된 분석으로 50개 전체 선별 전후 비교. coda_condition만으로 조건문 점수가 생기지 않는지 검사. 필요한 후보 포함 여부는 문장별로 별도 검토. 이후 생성 효과 실험은 별도 승인.',
        evidence=['DEV030: 목적격 GS_PART_ACC_01이 conditional 점수를 받음.','LONG004: 명령·금지에 관련된 종결 카드가 공급 목록에서 빠짐.','원본: full_review_20261029/private/selection_diagnostics.json'],
        reviewers={'Codex':'기존 진단에서는 후보와 조건 범위를 구별해 확인하도록 제안함. 이 변경안 자체는 아직 재검토하지 않음.','Claude':'기존 진단에서는 제공 카드의 누락과 적용 가능성 문제를 지적함. 이 변경안 자체는 아직 재검토하지 않음.'},
        lead='재현 가능한 코드 결함을 먼저 고치는 제안. 자연스러움 향상은 아직 검증하지 않음.'),
      dict(id='card-plan-20261029',version=1,title='선택한 카드·적용 조건·수정 지시를 일치시키기',
        before='선택 ID는 -를 카드인데 지시는 열쇠을이거나, 회상 카드 ID에 의지 표현 지시를 붙임. 조건에 적힌 어미 계열이 입력 조건인지 목표 표현인지 불명확한 항목도 있음.',
        after='말단 카드에서 입력 적용 조건과 목표 표현 정보를 구분한다. 선택한 카드 ID, 수정할 원문 구간, 보존할 특징, 목표 어미를 한 계획으로 연결하고 서로 어긋나는 계획을 별도로 표시한다.',
        reason='카드 ID가 존재하고 검색되었다는 검사만으로는 규칙의 올바른 적용을 확인할 수 없음.',
        scope='관련 말단 카드의 조건 표현과 계획 검증 명세를 먼저 작성. 원문헌에 없는 조건을 확정하지 않음. 일괄 KG 수정 전 대상 카드별 변경표를 다시 제시.',
        verification='50개 전체에서 카드·지시·결과 불일치 목록을 대조. 합성 검사 입력으로 서로 다른 규칙을 혼용한 계획이 탐지되는지 확인.',
        evidence=['DEV012: -를 카드 인용과 열쇠을 지시가 불일치.','원본: full_review_20261029/private/casebook.json 및 입력별 final_plan.json'],
        lead='규칙마다 별도 Python 함수를 만드는 제안이 아님. 공통 검사와 간결한 카드 데이터로 구분한다.'),
      dict(id='realization-20261029',version=1,title='활용형을 붙이는 과정과 수정 구간 점검',
        before='사+었+지 → 사었지, 되ㄴ가 같은 활용 오류가 발생함. 여러 어절 표현을 가진 카드에도 한 어절 출력만 허용하는 제약이 있음.',
        after='Qwen에는 분석 형태소와 원문 표면형을 함께 주고, 바꿀 어미와 유지할 어간·시제를 명시한다. 수정 구간은 실제 원문 범위로 고정하되 여러 어절 결과를 허용하는 계약을 설계한다. 고립 자모·겹치는 편집·빈 수정과 원문 유지 상태를 구분해 검사한다.',
        reason='활용 지식 부족과 구현 제약 충돌이 함께 관측됨. 프롬프트 추가만으로 해결된다고 가정하지 않음.',
        scope='우선 활용·편집 계약 변경안과 재현 테스트 작성. 자동 재시도·전체 재생성·학습은 포함하지 않음. 기록된 길이 제한/반복 출력 문제는 이 항목과 별도 원인 확인 필요.',
        verification='샀어의 재결합, 공백을 포함하는 목표 표현, 위치 겹침과 원문 보존 검사. 한 요소씩 바꾸는 원인 확인 실험안을 마련하고 50개 전체 회귀 비교.',
        evidence=['DEV002 Single 지시 자체에 사었지가 있음. Multi는 샀지.','DEV013 Multi: 되ㄴ가.','완성 출력 4개에 결합되지 않은 자모, 4건은 한 어절 제약으로 출력 실패.'],
        lead='문법적으로 잘못된 결합과 지역화자가 판단할 어감을 별도로 다룬다.'),
      dict(id='ji-je-20261029',version=1,title='-지·-제: 용법 존재와 실제 선택 조건 구별',
        before='서술과 확인 질문 카드가 이미 모두 있음. DEV002에서 중립적인 샀어를 샀지로 바꾸는 것이 적절한지는 별도 문제임.',
        after='기존 서술·확인 질문 카드를 보존한다. 사용자 예문 “그거 니 책이제?”를 확인 질문 항목에 사용자 제공 용례로 연결하는 변경안을 작성한다. 서술형이라는 이유만으로 모든 -어를 -지/-제로 바꾸는 조건은 허용하지 않도록 검토한다.',
        reason='문헌은 서술 사용과 확인 질문 사용을 모두 제시한다. 특정 용법이 존재한다는 근거만으로 문장 간 자유 교체를 정당화할 수 없음.',
        scope='GS_ENDRULE_JI_ASSERT / GS_ENDRULE_JI_CONFIRM의 조건 설명·사용자 용례 연결 변경표. 현재 사용자 피드백은 문헌 근거와 구별. 지역·시대·상황 모델 전면 확장은 하지 않음.',
        verification='경북방언 종결어미 연구 PDF 200쪽과 210–211쪽 근거 유지. 새 사용자 예문 출처 확인. DEV002의 중립 진술에서 목표 어미 선택을 따로 검토.',
        evidence=['경북방언_종결어미_연구.pdf: PDF 200쪽 서술/답변, 210–211쪽 확인 질문.','사용자 제공: 그거 니 책이제?'],
        human_question='DEV002처럼 별도 상황 설명이 없는 “샀어”를 “샀지/샀제”로 바꾸면, 의미·말하는 태도가 바뀌었다고 느끼는지? 선호 문장과 허용 가능한 문장은 구별해서 알려주세요.',
        lead='-제를 의문 전용으로 바꾸자는 제안은 하지 않는다. 문헌의 두 용법을 남기고 선택 조건을 보완한다.')
    ]
    existing={p['id'] for p in store.state()['proposals']}
    for p in proposals:
        if p['id'] not in existing:store.proposal(p)
    dashboard=next(p for p in store.state()['proposals'] if p['id']=='dashboard-20261029')
    if dashboard['state']=='pending':
        store.decide({'items':[dict(id=dashboard['id'],version=1,revision=0,action='approved',comment='대시보드 구현 범위에 대한 사용자 명시 요청')],
            'reference':'현재 채팅 2026-10-29 사용자 요청 2번','quote':'실시간 진행률·예상 남은 시간과 승인 기록을 연결하는 대시보드 기능 … 이것도 빠르게 작업 범위를 제시해서 구현해줘.'},channel='chat')
    state=store.state()
    if not any(t['id']=='dashboard-build-20261029' for t in state['tasks']):
        store.task(dict(id='dashboard-build-20261029',title='진행·승인 화면 구현',actor='총괄 Codex',stage='구현 완료 후 통합 검증',status='running',message='10개 신규 기능 테스트 통과. 기존 관리 기능과 화면을 추가 확인 중. 기록 시작 전 구현 시간은 경과 시간에 포함하지 않음.'))
    print('Registered proposals and explicit dashboard authorization; no KG changes.')

if __name__=='__main__':main()
