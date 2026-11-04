"""Join approved references to actual requests; no model calls or KG mutations.

Text differences are navigation aids, never automatic linguistic error labels.
The research queue below is lead annotation, not executable grammar rules.
"""
from pathlib import Path
import json,hashlib,difflib,datetime
R=Path(__file__).resolve().parents[3];H=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text('utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n','utf8')
REF=R/'data/derived_private/gyeongsang_reference50_20261030_v1/references.jsonl'
GROUPS=[
 ('plain','반말 평서','DEV002 DEV005 DEV007 NEW009','평서 실현 후보와 시제 보존. 어휘 교체는 별도 지식으로 구별.'),
 ('polite_question','공손 질문·제안','DEV011 DEV013 NEW004 NEW005 ADVCE001A ADVCE001B ADVCE003A ADVCE003B','질문 종류·제안/추측·상대높임을 보존하는 후보.'),
 ('request','요청·명령·금지','DEV017 DEV019 DEV020 DEV021 DEV030 LONG002 LONG003 LONG004 NEW006 NEW007','요청/금지/명령과 높임을 구별. 어휘 한정 표현을 일반화하지 않음.'),
 ('intention','약속·의향','DEV021 DEV030 LONG001 LONG004 NEW007 ADVCE008A ADVCE008B QUAL017','약속·의향과 높임을 보존. 어휘 높임은 별도 보존.'),
 ('clause','절 연결·인용','DEV019 DEV026 DEV028 DEV029 LONG001 LONG003 NEW006 NEW012 QUAL018 QUAL020','원인·우려·인용·대조 관계를 바꾸지 않는 대응.'),
 ('nominal','계사·부정 계사','DEV004 NEW001 NEW008 NEW012 ADVCE005A QUAL002 QUAL005','명사/계사와 과거·부정·높임을 분리.'),
 ('polite_realization','공손형 실현·보존','DEV003 DEV026 LONG003 LONG004 ADVCE002B ADVCE006A ADVCE006B ADVCE010A ADVCE010B QUAL003 QUAL018 QUAL020','전달된 결합형과 실제 생성의 차이. 과거형·높임·해체 형태 보존.'),
 ('formal_choice','공손체 후보 선택','ADVCE002A ADVCE005B','참조의 격식체 선택과 현재 후보 차이. 다른 허용 표현도 가능.'),
 ('question','반말 질문','DEV012 DEV014 LONG001 LONG002','질문 조건, 어간과 과거형 보존.'),
 ('lexical','어휘·지시어 등','DEV022','먹다/묵다 등 어휘 변이. 문장 전체를 외우는 규칙을 만들지 않음.'),
]
def main():
 stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
 out=H/'private/reference_followup'/stamp;out.mkdir(parents=True)
 refs={r['id']:r for r in (json.loads(x) for x in REF.read_text('utf8').splitlines())}
 runs={a:Path(d) for a,d in read(H/'private/latest_regression.json').items()}
 rows=read(runs['A']/'private/shared_cases.json');assert len(rows)==len(refs)==50
 assert set(refs)=={r['id'] for r in rows}
 files={str(REF):sha(REF)};joined=[];past=[];policies=[]
 for row in rows:
  ref=refs[row['id']];assert ref['input']==row['text'],('reference_input_version_mismatch',row['id'])
  groups=[g[0] for g in GROUPS if row['id'] in g[2].split()];assert groups,row['id']
  differences=[{'source':row['text'][i:j],'reference':ref['reference'][k:l],'kind':tag} for tag,i,j,k,l in difflib.SequenceMatcher(None,row['text'],ref['reference'],autojunk=False).get_opcodes() if tag!='equal']
  outputs={}
  for a,d in runs.items():
   outputs[a]=[]
   for rep in (1,2):
    folder=d/'private/records'/(row['id']+'__r'+str(rep));reqpath=folder/'generation_call/request.json';respath=folder/'generation_call/response.json';storedpath=folder/'result.json'
    req=read(reqpath);packet=json.loads(req['messages'][1]['content']);raw=read(respath);actual=json.loads(raw['choices'][0]['message']['content']);stored=read(storedpath)
    assert stored['output_text']==actual['output_text']
    for p in (reqpath,respath,storedpath):files[str(p)]=sha(p)
    outputs[a].append({'repeat':rep,'text':actual['output_text'],'reason':actual['reason'],'request':str(reqpath),'response':str(respath)})
    if a=='A' and rep==1:
     policies.append(req['messages'][0]['content'])
     for action in packet['actions']:
      if action.get('preserve',{}).get('tense')=='past':
       past.append({'id':row['id'],'target_id':action['target_id'],'target':action['target'],'rule_id':action['rule_id'],'morphs':action.get('source_morphs'),'prefinals':action.get('prefinals'),'features':action.get('features'),'preserve':action['preserve'],'forms':action.get('forms'),'composition':action.get('composition'),'output':actual['output_text'],'request':str(reqpath),'response':str(respath),'automatic_error_label':None})
  joined.append({'id':row['id'],'input':row['text'],'approved_reference':ref['reference'],'reference_status':ref['status'],'groups':groups,'text_differences_not_error_labels':differences,'actions':row['packet']['actions'],'unresolved':row['packet'].get('unsupported_or_unresolved',[]),'outputs':outputs})
 assert len(set(policies))==1
 old=R/'experiments/runs/20261104T015832989809Z_fixed_source_prefix_surface/private/records/ADVCE006A'
 oldpacket=read(old/'generation_packet.json');oldresp=json.loads(read(old/'generation_call/response.json')['choices'][0]['message']['content'])
 for p in (old/'generation_packet.json',old/'generation_call/request.json',old/'generation_call/response.json'):files[str(p)]=sha(p)
 assert oldpacket['actions'][0]['preserved_source_prefix']=='설명했어'
 save(out/'cases.json',joined);save(out/'past_delivery.json',past)
 save(out/'prior_probe.json',{'request':str(old/'generation_call/request.json'),'preserve_prefix':oldpacket['actions'][0]['preserved_source_prefix'],'edit':oldpacket['actions'][0]['surface_edit'],'raw_result':oldresp,'conclusion':'Explicit prefix was already tried. This recorded output retains past but drops 어; do not claim a new prefix prompt is an untried fix.'})
 save(out/'research_queue.json',[{'local_group':g[0],'title':g[1],'ids':g[2].split(),'goal':g[3],'status':'lead_proposed_refinement_not_executable_rule','basis':'user_approved_case_references; generalization_requires_conditions_and_transfer_check'} for g in GROUPS])
 save(out/'manifest.json',{'created_utc':stamp,'model_calls':0,'kg_changes':0,'input_count':50,'requests_verified':300,'raw_outputs_verified':300,'source_files_sha256':files,'reference_delivered_to_model':False,'limitation':'All50 joined and reference read; no claim all linguistic gaps individually source-validated. Overlapping research groups are not KG node IDs.'})
 save(H/'private/latest_reference_followup.json',{'directory':str(out)})
 print(json.dumps({'directory':str(out),'inputs':len(joined),'past_actions_in_A':len(past),'requests_checked':300,'new_calls':0},ensure_ascii=False))
if __name__=='__main__':main()
