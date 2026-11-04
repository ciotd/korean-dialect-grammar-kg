from pathlib import Path
import json,collections,hashlib,sys
H=Path('experiments/analyses/support_expansion_20261104');R=Path.cwd();C=Path('C:/Users/ciot28/Documents/Codex/2026-10-13/ciotd-odor-complaint-dialect-rag-kg/work/source_audit')
def read(p):return json.loads(p.read_text('utf8'))
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n','utf8')
rows=read(H/'private/audit46.json');replay={(x['id'],x['target_id']):x for x in read(H/'private/replay62.json')}
source_specs=[('cop','D02',199,'저거 아부지는 차암 저승서는 왕이라예.','긍정 계사 공손 평서 직접 예'),('cop_alt','D04',22,'-이라예-이랐어예아이라예아이랐어예','전통형 표; 모든 현대형의 독점 규칙으로 해석하지 않음'),('polite_q','D02',57,'직접 보셨어예?','높임·과거 어예 질문 직접 예'),('polite_table','D05',26,'해예체-어/아예-어/아예-어/아예-어/아예','표에서 네 기능별 해예형; 같은위키계통'),('plain','D05',27,'해체-어/아-어/아-어/아-어/아','공통형 해체 관찰'),('request_plain','D02',217,'해체 명령법의 경우 ‘-아/어’를 제외하고는 특별한 형태를 발견하기 어렵','표준형과 공유하는 명령 관찰'),('request_polite','D02',218,'아예 가지 마세요.','공손 금지에 마세요 직접 예'),('request_gap','D02',219,'비격식체 명령법에서는 ‘예’형의 쓰임이 보이지 않는다.','이 자료의 관찰 부족. 다른지역·시기금지규칙 아님'),('promise','D02',201,'표준어 ‘-ㄹ게’에 대응되는 형태로 ‘-끼’가 쓰인다.','약속 형태; 어간·등급조건은 같은쪽 본문을 함께 읽음'),('hort','D02',189,'해라체 청유법 어미는 ‘-자’가 가장 보편적으로 쓰이고','자 유지 가능성'),('memory','D02',198,'동사와 함께 회상을 나타내는 ‘-드(더)-’와 결합하여 쓰이면서','회상 구조와 계사라 구분'),('confirm','D02',211,'‘-제’는 청자에게 사실을 확인하는 형식으로','확인 기능, 높임을 잃지 않는 별도결합 필요'),('intent','D02',89,'동사 어간과 직접 결합하며 화자가','하이소체 갈라니더 등 관련의도근거 있음. 하려고요 같은화계 직접대응 미확보')]
ev={}
for id,d,p,q,note in source_specs:
 text=read(C/f'{d}.json')[p-1]['text'];i=text.index(q);ev[id]={'document_id':d,'pdf_page':p,'quote':q,'start':i,'end':i+len(q),'page_text_sha256':hashlib.sha256(text.encode()).hexdigest(),'interpretation':note,'read_level':'selected_page_full_text_context_checked','visual_check':d=='D04' and p==22 or d=='D05' and p==26}
extra={('NEW001','W7'):'명사 존칭 님과 서술어 주체높임을 섞은 판단 의심. 관찰 선어말을 새로 만들지 않음.',('QUAL002','W15'):'된의 시간과 계사 시간 해석이 섞일 수 있음. 거/것 구성과 축약은 별도 정제.',('LONG004','W16'):'화자 약속/제안 및 수혜자 높임을 청유·주체높임과 섞은 판단 의심.',('ADVCE008A','W6'):'화자 약속/제안 및 수혜자 높임을 요청·주체높임과 섞은 판단 의심.'}
for x in rows:
 key=(x['id'],x['target_id']);r=replay[key];group=x['group']
 if key==('DEV030','W3'):group='request';x['group']='request';x['group_label']='요청·명령·금지';x['fix']='자다는 명령이며 청유자가 아님. 해체명령 근거를 대조하고 반말명령 기능 보존.'
 if group=='polite_q':x['group_label']='높임 질문·제의'
 if key in extra:x['analysis_issue']=extra[key];x['analysis_issue_type']='analysis_interpretation_review'
 if r['after']=='ready_for_generation_trial':category='근거 있는 구성의 실행 연결 누락';sources=['cop'] if group=='copula' else ['polite_q','polite_table'];action='신규 조건 관계와 실현 연결 구현, 동일 답변 재조회에서 적용 후보 확인'
 elif group=='analysis':category='형태 분석·투영 충돌';sources=[];action='계세요를 새 계사규칙으로 처리하지 않음. 분석후보 비교가 선행되어야 함'
 elif group=='plain' or group=='hort' or group=='request' and x['observed_features']['addressee_level']=='plain':category='표준어와 공유하는 형태 가능';sources=['plain'] if group=='plain' else ['hort'] if group=='hort' else ['request_plain'];action='해당 어미 유지 가능성을 평가에 반영. 어휘·음운·화용의 추가변환과 구별'
 elif group=='copula':category='결합·변이 추가 정제 필요';sources=['cop','cop_alt'];action='과거·부정·거/것을 독립조건으로 정제. 현재긍정규칙에서 자동확대하지 않음'
 elif group=='intent':category='같은 기능·높임의 대응 미확보';sources=['intent'];action='관련 의도 구문은 있지만 하려고요 직접대응 미확보. 추가문헌검색 후 별도구성 검토'
 elif group=='request':category='문헌별 관찰 범위 차이';sources=['request_polite','request_gap','polite_table'];action='대계 미관찰을 금지로 일반화하지 않음. 세예와이소의높임/결합을 별도로대조'
 else:category='기존 관련 지식의 조건 정제 필요';sources={'polite_q':['polite_q','polite_table'],'promise':['promise'],'memory':['memory'],'confirm':['confirm']}[group];action=x['fix']
 x.update(primary_cause=category,source_evidence_ids=sources,status='reviewed_for_scope_and_next_action',implementation_result=action,replay_after=r['after'],replay_rules=r['rules'],review_scope='lead checked all46 trace/features; both existing reviewers independently checked46; not gold linguistic annotation',verification='별도개발 정상/차단/미확정 검사와 동일분석 재조회; 이후 Qwen출력 대조')
 x['causes']=[category]+([x['analysis_issue_type']] if x.get('analysis_issue_type') else [])
 x['next_check']=action
 x['source_directly_proves_translation']=False
 # Explicitly distinguish selected status from all construction statuses.
 x['construction_diagnosis']={q['construction_id']:q['state'] for q in x['runtime_failures']}
assert len(rows)==46
save(H/'private/audit46.json',rows);save(H/'private/source_evidence.json',ev)
save(H/'private/audit_summary.json',{'count':46,'group_counts':dict(collections.Counter(x['group_label'] for x in rows)),'primary_cause_counts':dict(collections.Counter(x['primary_cause'] for x in rows)),'overlapping_analysis_flags':sum(bool(x['analysis_issue']) for x in rows),'historical_selected_out_of_slice_but_other_no_matching':sum(any(v=='no_matching_usage' for v in x['construction_diagnosis'].values()) for x in rows),'newly_connected_same_analysis':sum(x['replay_after']=='ready_for_generation_trial' for x in rows),'unresolved_is_not_linguistic_prohibition':True,'all7_search_not_full_reread':True})
print(json.dumps(read(H/'private/audit_summary.json'),ensure_ascii=False))
