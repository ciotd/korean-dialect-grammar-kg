"""Freeze the diagnostic subset and prompt before any follow-up model call."""
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from kg_pipeline.integrated import ANALYSIS_PROMPT
from kg_pipeline.io import save
HERE=Path(__file__).resolve().parent

GUIDANCE='''
다음은 반환값의 공통 정의다. 특정 문장의 정답을 뜻하지 않는다.
speech_act: statement는 사실·상태 서술, information_question은 답을 묻기, prohibition은 행동하지 말라는 금지, suggestion은 화자를 포함해 함께 하자는 제안, request는 상대에게 해 달라는 부탁, command는 상대에게 하는 명령, promise는 화자 자신의 행동 약속이다. -지 말다의 명령·요청형은 금지로 구별하고 단순 부정 서술과 섞지 않는다. -자/-ㅂ시다 등은 문맥에서 공동행동 제안인지 판단한다.
addressee_level은 입력 종결의 말높임이다. plain은 반말(-아/-어/-자 등), polite는 해요체(-아요/-어요/-세요 등), formal은 합쇼체와 같은 격식 높임(-ㅂ니다/-십시오 등)이다. 공손한 뜻이라는 이유만으로 모두 formal로 판단하지 않는다. 주체높임과 별개다.
auxiliary_kind: progressive는 진행(-고 있다/계시다), resultative는 완료·결과, benefactive는 남을 위해 하는 행동, attempt는 시도다. 부정·금지의 보조용언은 기존 선택지 other를 쓴다. 보조 기능이 없으면 none, 판단 불가면 null이다. 모든 VX를 progressive로 보지 않는다.
semantic_function은 그 단위가 맡는 뜻을 판단한다. 조사에서는 동반/비교/받는 대상 등을, 연결어미에서는 이유/시간 순서/조건/목적 등을 구별한다. 의문사·재귀 대명사, 의지·추측 용법에도 해당 의미를 쓸 수 있다. 무관한 의미값을 채우지 않고 null로 둔다. 어미가 같다는 이유만으로 항상 같은 뜻으로 정하지 않는다.
관계 방향: 서술어에서 참여 명사를 가리킬 때 agent/patient/recipient/causer/causee를 쓴다. 명사나 조사에서 서술어를 가리키면 head_predicate다. agent의 대상으로 서술어를 넣지 않는다. 본/보조 관계는 서로 다른 실제 서술어 단위를 지정한다. 같은 절이라도 각 단위의 시제·화행을 강제로 복사하지 않는다.
'''

def main():
    ids=['IG009','IG011','IG015','IG016','IG018','IG019','IG021','IG025','IG028','IG005','IG007','IG013','IG027','IG001','IG006','IG010','IG014','IG017']
    rows=[json.loads(l) for l in (HERE/'private/development_inputs.jsonl').read_text(encoding='utf8').splitlines() if l.strip()]
    rows=[r for r in rows if r['id'] in ids]
    target=HERE/'private/analysis_repair_inputs.jsonl'
    assert not target.exists(),'Repair subset is immutable once prepared'
    target.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf8')
    prompt=HERE/'private/analysis_prompt_repair.txt'
    prompt.write_text(ANALYSIS_PROMPT+'\n'+GUIDANCE,encoding='utf8')
    save(HERE/'private/analysis_repair_checks.json',{'purpose':'exposed diagnostic; never sent to model','checks':[
        {'id':'IG009','kind':'predicate','text':'가자','feature':'speech_act','expected':['suggestion']},
        {'id':'IG011','kind':'predicate','text':'해봐','feature':'addressee_level','expected':['plain']},
        {'id':'IG015','kind':'construction','text':'열지 마세요','feature':'speech_act','expected':['prohibition']},
        {'id':'IG015','kind':'construction','text':'열지 마세요','feature':'auxiliary_kind','expected':['other']},
        {'id':'IG016','kind':'construction','text':'앉지 마','feature':'speech_act','expected':['prohibition']},
        {'id':'IG018','kind':'predicate','text':'갑시다','feature':'speech_act','expected':['suggestion']},
        {'id':'IG019','kind':'predicate','text':'전화해','feature':'addressee_level','expected':['plain']},
        {'id':'IG021','kind':'connector','text':'와서','feature':'semantic_function','expected':['sequence']},
        {'id':'IG028','kind':'particle','text':'아이에게','feature':'semantic_function','expected':['recipient']}
    ]})
    save(HERE/'private/analysis_repair_manifest.json',{'ids':[r['id'] for r in rows],
        'inputs_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
        'prompt_sha256':hashlib.sha256(prompt.read_bytes()).hexdigest(),
        'baseline':'20261106T051728566435Z_integrated_grammar_development','max_calls':36,
        'changes':'analysis definition guidance only; reference replay is not used in model run'})
    print('Frozen',len(rows),'development inputs and prompt; no model calls')

if __name__=='__main__':main()
