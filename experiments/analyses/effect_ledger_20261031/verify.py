"""Recount historical results, validate source-only bundles and reject unsafe probes."""
import copy
import json
from pathlib import Path
from prepare import B,R,A,load,digest,save,proposal_packet

def main():
    root=R/json.loads((B/'private/latest.json').read_text(encoding='utf8'))['preparation']
    hashes=json.loads((root/'source_hashes.json').read_text(encoding='utf8'))
    assert all(digest(R/p)==v for p,v in hashes.items())
    inspected={}; checked=0
    for name in ('card_delivery_20261030','card_content_experiment_20261030','scoped_repair_20261030','register_connective_20261030'):
        summary=load(A/name/'private/summary.json',hashes)
        if name=='register_connective_20261030': runs=summary['runs']
        else:runs=load(A/name/'private/active_run.json',hashes)['runs']
        for arm,run in runs.items():
            rows=load(R/'experiments/runs'/run/'private/results.json',hashes)
            counts={'changed':0,'unchanged':0,'no_output':0}
            for row in rows:
                text=row.get('output_text')
                if text is None or text=='':counts['no_output']+=1
                elif text==row['input_text']:counts['unchanged']+=1
                else:counts['changed']+=1
            expected=(summary['counts'][arm+'_new'] if name=='register_connective_20261030'
                      else summary['conditions'][('new_'+arm) if name=='scoped_repair_20261030' else arm])
            assert all(counts[k]==expected[k] for k in counts),(run,counts,expected)
            inspected[run]={'records':len(rows),**counts};checked+=len(rows)
    cases=load(root/'cases.json',{})
    assert len(cases)==50 and len({c['id'] for c in cases})==50
    for c in cases:
        packet=json.loads((root/'model_inputs'/c['id']/'source_packet.json').read_text(encoding='utf8'))
        original=R/'experiments/batches/20261030T085346443103Z/private/shared'/c['id']/'reference_packet.json'
        assert packet==json.loads(original.read_text(encoding='utf8'))
        # Exact original packet equality, not naive text search: input may equal a valid reference.
        draft=json.loads((root/'selection_review'/f"{c['id']}.json").read_text(encoding='utf8'))
        assert draft['status']=='pending' and draft['targets']==[]
    packet=json.loads((root/'model_inputs/DEV026/source_packet.json').read_text(encoding='utf8'))
    morph=json.loads((root/'model_inputs/DEV026/morphology.json').read_text(encoding='utf8'))
    target={'word_id':'W5','card_id':'GS_END_DECL_YE_01','form_index':0,'morph_index':2}
    before=copy.deepcopy(packet);ok=proposal_packet(packet,morph,[target])
    assert packet==before and ok['packet']==packet and ok['runnable'] is False
    no_change=proposal_packet(packet,morph,[],{'reviewed_by':'synthetic_test_only','basis':'no_change_fixture'})
    assert no_change['status']=='reviewed_no_change_recorded' and no_change['worker_policy']=='skip_and_record_unchanged_zero_calls'
    invalid=[[],[{**target,'after':'완성 정답 금지'}],[{**target,'card_id':'NONEXISTENT'}],
             [{**target,'form_index':999}],[{**target,'form_index':True}],
             [{**target,'morph_index':0}],[{**target,'morph_index':999}],
             [{**target,'word_id':'W999'}],[target,target]]
    for value in invalid:
        try:proposal_packet(packet,morph,value)
        except ValueError:pass
        else:raise AssertionError(('should_reject',value))
    # A real existing but NOT delivered card must also fail a selection-only intervention.
    packet2=json.loads((root/'model_inputs/DEV002/source_packet.json').read_text(encoding='utf8'))
    morph2=json.loads((root/'model_inputs/DEV002/morphology.json').read_text(encoding='utf8'))
    try:proposal_packet(packet2,morph2,[dict(target,card_id='GS_END_DECL_HRA_09')])
    except ValueError:pass
    else:raise AssertionError('missing delivered card was inserted')
    # Confirm the failed cases did not mutate the reusable base.
    assert packet==before
    assert not list((root/'model_inputs').glob('*/saved_multi_decision.json'))
    assert len(list((root/'archive_only').glob('*/saved_multi_decision.json')))==50
    html=(B/'private/report.html').read_text(encoding='utf8')
    assert html.count('<details class="case">')==50
    assert all(digest(R/p)==v for p,v in hashes.items())
    save(root/'verified_source_hashes.json',hashes)
    result={'historical_runs_recounted':len(inspected),'historical_result_records_recounted':checked,
            'recount_matches_original_summaries':True,'counts_by_run':inspected,
            'source_only_packets_exact':50,'pending_selection_drafts':50,
            'binding_fixture_success':1,'reviewed_no_change_fixture_success':1,'invalid_binding_cases_rejected':len(invalid)+1,
            'old_free_text_decisions_separated_from_runtime_inputs':True,
            'base_packet_unmodified':True,'report_cases':50,'original_hashes_unchanged':len(hashes),
            'new_model_calls':0,'new_KG_queries':0,'linguistic_accuracy_measured':False,
            'new_live_diagnostic_runner_implemented':False}
    save(root/'verification.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='counts_by_run'},ensure_ascii=False))

if __name__=='__main__':main()
