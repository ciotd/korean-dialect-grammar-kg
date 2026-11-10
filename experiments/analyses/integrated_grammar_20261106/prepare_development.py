"""Freeze broad development inputs before seeing any new Qwen outputs."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
CASES=[
 ('동사·과거','어제 운동장에서 한참 뛰었어.'),
 ('동사·현재','나는 주말마다 공원에서 달려.'),
 ('형용사','오늘은 바람이 꽤 차가워.'),
 ('계사·과거','그 사람은 예전에 우리 이웃이었어.'),
 ('계사·질문','저 건물은 도서관이야?'),
 ('명사·2인칭','너는 어느 버스를 타?'),
 ('명사·지시','거기에 내 우산이 있어.'),
 ('명사·수사','오늘은 손님이 셋 왔어.'),
 ('조사·동반','누나랑 같이 시장에 가자.'),
 ('조사·비교','나는 떡보다 국수가 좋아.'),
 ('조사·유사','동생처럼 천천히 해봐.'),
 ('조사·수혜','이 상자는 친구한테 줘.'),
 ('요청·보조용언','창문 좀 닫아 주세요.'),
 ('요청·본용언','물 한 잔 주세요.'),
 ('금지·높임','위험하니까 그 문을 열지 마세요.'),
 ('금지·반말','그 의자에 앉지 마.'),
 ('약속','내가 먼저 가서 기다릴게.'),
 ('청유·높임','잠깐 여기서 쉬었다 갑시다.'),
 ('절 연결·조건','시간이 나면 전화해.'),
 ('절 연결·이유','비가 오니까 안에서 기다려.'),
 ('절 연결·순서','집에 와서 손을 씻었어.'),
 ('절 연결·의도','나는 옷을 사려고 시장에 왔어.'),
 ('부정','나는 그 사람을 만나지 않았어.'),
 ('불가능','다리가 아파서 오래 못 걸어.'),
 ('보조·완료','남은 물을 마셔 버렸어.'),
 ('본용언·대조','낡은 신발을 버렸어.'),
 ('보조·진행·높임','할아버지께서 신문을 읽고 계세요.'),
 ('사동','아이에게 약을 먹였어.'),
 ('피동','바람에 문이 닫혔어.'),
 ('관형절·과거','어제 산 옷을 오늘 입었어.'),
]

if __name__=='__main__':
    dest=ROOT/'private/development_inputs.jsonl'
    rows=[{'id':f'IG{i:03}','text':text,'development_focus':focus,'role':'exposed_development_not_final_evaluation'} for i,(focus,text) in enumerate(CASES,1)]
    dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists():
        assert [json.loads(x) for x in dest.read_text(encoding='utf8').splitlines()]==rows,'Never overwrite changed development inputs'
    else:dest.write_text('\n'.join(json.dumps(r,ensure_ascii=False) for r in rows)+'\n',encoding='utf8')
    (ROOT/'private/smoke_inputs.jsonl').write_text('\n'.join(json.dumps(rows[i],ensure_ascii=False) for i in [8,12])+'\n',encoding='utf8')
    print('Frozen development:',len(rows),'Smoke subset: 2. No expected output sentences.')
