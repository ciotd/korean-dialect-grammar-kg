"""Record completed specification work and separate pending implementation requests."""
import sys
from pathlib import Path
BASE=Path(__file__).resolve().parent;PROJECT=BASE.parents[2]
sys.path.insert(0,str(PROJECT/'src'))
from research_management.work import WorkStore

def main():
    store=WorkStore(PROJECT);state=store.state()
    proposals=[
        dict(id='implement-card-plan-20261030',title='다음 구현 1: 카드 조건과 수정 계획 연결',
             before='카드 ID 존재는 검사하지만, 카드 목표형과 실제 수정의 일치 및 자료 역할 구별이 부족함.',
             after='원본 카드 옆에 버전 있는 해석표를 두고, 변환·관찰·차단·반증을 구별. 여러 카드/목표형을 편집에 연결하고 코드가 원문·버전을 대조.',
             reason='DEV012에서 -를 카드로 열쇠을 수정이 통과함. 참고 관찰이 교체 명령으로 오해될 수 있음.',
             reviewers={'Codex':'복수 규칙 연결·판정 출처·스냅샷 연결을 보완하라고 지적.', 'Claude':'required 등 자리표시자를 실제 조건값으로 쓰지 말라고 지적.'}),
        dict(id='implement-realization-20261030',title='다음 구현 2: 활용 결과·편집 범위 검증',
             before='잘못된 조합은 통과하고 정상일 수 있는 공백 포함 결과는 일괄 거부함.',
             after='연속 원문 범위·구분자 보호·목표형 대응을 검사. 다어절 편집과 의존 묶음을 지원하고 부분 적용/원문 유지/실패를 구분.',
             reason='사었지·되ㄴ가가 통과하고 QUAL020의 다어절 응답이 after_not_single_word로 거부됨.',
             reviewers={'Codex':'범위 내부 문장부호, 겹침, 편집 의존성, 보존 조건을 보완하라고 지적.', 'Claude':'범위와 부분 실패 처리를 구체화하라고 지적. Kiwi를 확정 사실로 보는 제안은 총괄이 채택하지 않음.'}),
        dict(id='implement-ji-je-20261030',title='다음 구현 3: -지/-제의 용법 구별과 사용자 제한',
             before='중립 평서가 JI_ASSERT의 충분한 선택 근거처럼 사용됨. DEV002에서 샀지/샀제 변환을 사용자가 거부함.',
             after='문헌 서술 용법을 삭제하지 않고 응답·화자 확정 태도·청자 확인을 구별. DEV002 제한은 입력/구간/변환 방향을 특정한 사용자 정책으로 기록.',
             reason='문헌에는 서술과 확인 질문 용법이 모두 있음. 사용자 의견을 모든 -제의 금지나 -다/-데이 일반 규칙으로 확대할 수 없음.',
             reviewers={'Codex':'화자의 확정 태도와 청자 확인을 구별하고 사용자 제한 범위를 명시하라고 지적.', 'Claude':'현재 입력의 문맥 근거 부족을 지적. 문장부호만으로 허용하는 해법은 총괄이 채택하지 않음.'})]
    existing={p['id'] for p in state['proposals']}
    for p in proposals:
        p.update(version=1,scope='구현 및 로컬 검사까지. KG 원본 보존. 관련성 순위·48개 제한 변경, Qwen 재실험·학습은 포함하지 않음.',
            verification='REVIEW_RESOLUTION.md의 수용 기준을 실행 시험으로 구현하고 기존 15개 재현 시험과 구별. 성공·미확인·실패를 각각 보고.',
            lead='두 Reviewer가 검토한 것은 초안. 본 구현안은 총괄이 15개 지적을 대조·취합한 결과이며 검토자 재승인본은 아님.',
            evidence=['상세: experiments/analyses/change_spec_20261030/REVIEW_RESOLUTION.md','읽기 화면: experiments/analyses/change_spec_20261030/private/review.html'],
            human_question='앞서 승인한 명세·재현 시험은 완료했습니다. 이 구체화된 내용의 실제 구현까지 진행할지 결정해 주세요. 재실험 승인은 별도입니다.')
        if p['id'] not in existing:store.proposal(p)
    tasks={t['id']:t for t in state['tasks']}
    if tasks.get('lead-spec-20261030',{}).get('status') not in ('completed','failed'):
        store.task(dict(id='lead-spec-20261030',title='승인된 변경 명세·재현 시험·독립 검토',actor='총괄 Codex',
            stage='명세 보완 및 검토 취합 완료',status='completed',
            message='50개 입력/100개 기존 결과·46종 선택 카드 연결. 재현·무결성 시험 15개 통과. Codex 8건/Claude 7건 처리. KG·운영 코드 변경 없음, Qwen 호출 0회. 구체화한 다음 구현 3건은 별도 결정 대기.'))
    print('명세 단계 완료 기록 및 다음 구현 3건 결정 대기 등록. 승인/적용은 실행하지 않음.')
if __name__=='__main__':main()
