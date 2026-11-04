"""Characterization tests: passing reproduces an old behavior, not a fixed system."""
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[2]
SNAPSHOT=ROOT/'private/code_snapshot'
sys.path.insert(0,str(SNAPSHOT))
from kg_runtime.card_pipeline import bind_plan,realize_plan,assemble

def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
BOOK={c['id']:c for c in read(PROJECT/'experiments/analyses/full_review_20261029/private/casebook.json')['cases']}
def inputs(key,arm='single'):
    a=BOOK[key]['arms'][arm];p=PROJECT/a['source_record_dir']
    return a,read(p/'morphology.json'),read(p/'reference_packet.json')['cards']

class ReproduceCurrentBehavior(unittest.TestCase):
    def test_gap_bad_contraction_is_accepted(self):
        a,m,c=inputs('DEV002');p=bind_plan(a['draft'],m,c)
        self.assertIn('사었지',assemble(m['text'],p))
    def test_gap_card_form_disagreement_is_accepted(self):
        a,m,c=inputs('DEV012');p=bind_plan(a['draft'],m,c)
        self.assertEqual(next(x for x in c if x['id']=='GS_PART_ACC_03')['forms'],['-를'])
        self.assertTrue(any(e['after']=='열쇠을' and e['rule_ids']==['GS_PART_ACC_03'] for e in p['edits']))
    def test_gap_detached_jamo_is_accepted(self):
        a,m,c=inputs('DEV013','multi');plan=bind_plan(a['draft'],m,c,realize=False)
        final=realize_plan(plan,a['worker_response'],m,c)
        self.assertIn('되ㄴ가',assemble(m['text'],final))
    def test_gap_invented_realization_instruction_survives(self):
        a,m,c=inputs('DEV019');p=bind_plan(a['draft'],m,c)
        self.assertTrue(any(e['after']=='미끄러우아가' for e in p['edits']))
    def test_actual_multiword_worker_response_is_rejected(self):
        a,m,c=inputs('QUAL020','multi');plan=bind_plan(a['draft'],m,c,realize=False)
        self.assertEqual(a['error'],'after_not_single_word')
        with self.assertRaisesRegex(ValueError,'after_not_single_word'):realize_plan(plan,a['worker_response'],m,c)
    def test_gap_surface_keep_still_appears_in_edits(self):
        a,m,c=inputs('DEV002');v=copy.deepcopy(a['draft']);v['edits'][0]['after']='샀어'
        p=bind_plan(v,m,c);self.assertEqual(len(p['edits']),1);self.assertEqual(assemble(m['text'],p),m['text'])
    def test_empty_plan_already_allowed(self):
        _,m,c=inputs('DEV002');p=bind_plan({'edits':[],'reason':'유지'},m,c)
        self.assertEqual(assemble(m['text'],p),m['text'])
    def test_existing_unknown_card_guard(self):
        a,m,c=inputs('DEV002');v=copy.deepcopy(a['draft']);v['edits'][0]['rule_ids']=['TEST_NONEXISTENT_ID']
        with self.assertRaisesRegex(ValueError,'unretrieved_rule_reference'):bind_plan(v,m,c)
    def test_existing_duplicate_word_guard(self):
        a,m,c=inputs('DEV002');v=copy.deepcopy(a['draft']);v['edits'].append(copy.deepcopy(v['edits'][0]))
        with self.assertRaisesRegex(ValueError,'invalid_edit_anchor'):bind_plan(v,m,c)
    def test_existing_source_position_guard(self):
        a,m,c=inputs('DEV002');m=copy.deepcopy(m)
        next(w for w in m['words'] if w['uid']=='W5')['start']=0
        with self.assertRaisesRegex(ValueError,'invalid_source_span'):bind_plan(a['draft'],m,c)
    def test_existing_output_outside_edit_is_preserved(self):
        a,m,c=inputs('DEV002');v=copy.deepcopy(a['draft']);v['edits'][0]['after']='샀다'
        self.assertEqual(assemble(m['text'],bind_plan(v,m,c)),'집에 가는 길에 빵을 샀다.')
    def test_all50_source_references_and_card_definitions_are_real(self):
        mapped=read(ROOT/'private/all50_mapping.json')
        self.assertEqual(len(mapped['rows']),50)
        self.assertEqual(sum(len(x['arms']) for x in mapped['rows']),100)
        self.assertTrue(all(not a['selected_id_missing_from_packet'] for r in mapped['rows'] for a in r['arms'].values()))
    def test_unique_ids_arms_and_original_inputs(self):
        rows=read(ROOT/'private/all50_mapping.json')['rows']
        expected=[json.loads(line) for line in (PROJECT/'data/derived_private/standard_inputs_50_20261023_v1/inputs.jsonl').read_text(encoding='utf-8-sig').splitlines() if line.strip()]
        self.assertEqual(len({r['id'] for r in rows}),50)
        self.assertEqual({r['id']:r['input'] for r in rows},{r['id']:r['text'] for r in expected})
        for row in rows:self.assertEqual(set(row['arms']),{'single','multi'})
    def test_evidence_files_match_frozen_hashes(self):
        for path,digest in read(ROOT/'private/evidence_manifest.json').items():
            with self.subTest(path=path):self.assertEqual(hashlib.sha256((PROJECT/path).read_bytes()).hexdigest(),digest)
    def test_runtime_snapshot_integrity_and_import(self):
        import kg_runtime.card_pipeline as module
        self.assertEqual(Path(module.__file__).resolve(),(SNAPSHOT/'kg_runtime/card_pipeline.py').resolve())
        for path,digest in read(SNAPSHOT/'manifest.json').items():
            with self.subTest(path=path):self.assertEqual(hashlib.sha256((SNAPSHOT/path).read_bytes()).hexdigest(),digest)

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(ReproduceCurrentBehavior)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    out={'purpose':'기존 동작 재현. 오류 수정 또는 방언 정확도 시험이 아님.','code_source':'private/code_snapshot','tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'new_qwen_calls':0}
    (ROOT/'private/reproduction_results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    sys.exit(not result.wasSuccessful())
