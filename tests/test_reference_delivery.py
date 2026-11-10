import sys
import unittest
import importlib.util
import json
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from kg_pipeline.reference_delivery import reference_exclusion

class ReferenceDeliveryTests(unittest.TestCase):
    def node(self,title,module,condition=None):
        return {'title':title,'properties':{'module':module,'original_spec':{'documentary_condition_before_normalization':condition or {}}}}
    def unit(self,kind,lemma=''):return {'kind':kind,'observed':{'lemma':lemma}}
    def test_dialect_side_is_not_input_side(self):
        self.assertEqual(reference_exclusion(self.node('-의 → -에',4),self.unit('particle'),{'matched_anchors':['에']}),'dialect_side_only')
        self.assertIsNone(reference_exclusion(self.node('-의 → -에',4),self.unit('particle'),{'matched_anchors':['의']}))
    def test_nominal_source_not_predicate_ending(self):
        self.assertEqual(reference_exclusion(self.node('대명사/3인칭 : 야/가/자',12),self.unit('predicate'),{'matched_anchors':['야']}),'explicit_source_category_mismatch')
    def test_same_module_not_enough_for_wrong_vowel(self):
        n=self.node('받침 있는 ㅔ 어간 + -어',2,{'stem_last_vowel':'ㅔ','stem_coda':'present'})
        self.assertEqual(reference_exclusion(n,self.unit('predicate','씻'),{'matched_anchors':['어']}),'documented_stem_vowel_mismatch')
    def test_unknown_source_not_certified(self):
        n=self.node('미정리 어형',12,{'stem_last_vowel':'unknown'})
        self.assertIsNone(reference_exclusion(n,self.unit('predicate','씻'),{'matched_anchors':['어형']}))
    def test_source_phrase_match_is_not_reverse_direction(self):
        self.assertIsNone(reference_exclusion(self.node('내기에서 돈을 잃다 → 꼻다',10),self.unit('particle'),{'matched_anchors':['에서']}))
    def test_module_does_not_determine_application_unit(self):
        n=self.node('거로 뒤 보조사',7,{'construction_family':'GEORO','following_particle':['는','도','만']})
        n['properties']['original_spec']['unit']='construction'
        self.assertIsNone(reference_exclusion(n,self.unit('construction'),{'matched_anchors':['거로']}))
    def test_nominal_does_not_inherit_ending_anchor(self):
        unit={'kind':'nominal','observed':{'lemma':'도서관','source_form':'도서관','source_final':'야'}}
        self.assertEqual(reference_exclusion(self.node('대명사/3인칭 : 야/가/자',12),unit,{'matched_anchors':['야']}),'anchor_belongs_to_other_morpheme')
    def test_replay_preserves_failed_and_unattempted_denominator(self):
        path=Path(__file__).resolve().parents[1]/'experiments/analyses/integrated_grammar_20261106/replay_reference_delivery.py'
        spec=importlib.util.spec_from_file_location('reference_replay',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);(p/'private/records/C').mkdir(parents=True)
            (p/'private/inputs.jsonl').write_text('\n'.join(json.dumps({'id':i,'text':i}) for i in ('A','B','C')),encoding='utf8')
            (p/'private/results.json').write_text(json.dumps([{'id':'B','status':'failed'},{'id':'C','status':'generated'}]),encoding='utf8')
            (p/'private/records/C/generation_packet.json').write_text('{}',encoding='utf8')
            rows=list(module.replay_inventory(p))
            self.assertEqual([r['replay_status'] for r in rows],['missing_result','missing_packet','replayed'])
            self.assertEqual(len(rows),3)

if __name__=='__main__':unittest.main()
