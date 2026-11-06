import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from kg_pipeline.reference_delivery import reference_exclusion

class ReferenceDeliveryTests(unittest.TestCase):
    def node(self,title,module,condition=None):
        return {'title':title,'properties':{'module':module,'original_spec':{'documentary_condition_before_normalization':condition or {}}}}
    def unit(self,kind,lemma=''):return {'kind':kind,'observed':{'lemma':lemma}}
    def test_dialect_side_is_not_input_side(self):
        self.assertEqual(reference_exclusion(self.node('-의 → -에',4),self.unit('particle'),{'matched_anchors':['에']}),'no_input_side_anchor')
        self.assertIsNone(reference_exclusion(self.node('-의 → -에',4),self.unit('particle'),{'matched_anchors':['의']}))
    def test_nominal_source_not_predicate_ending(self):
        self.assertEqual(reference_exclusion(self.node('대명사/3인칭 : 야/가/자',12),self.unit('predicate'),{'matched_anchors':['야']}),'module_unit_mismatch')
    def test_same_module_not_enough_for_wrong_vowel(self):
        n=self.node('받침 있는 ㅔ 어간 + -어',2,{'stem_last_vowel':'ㅔ','stem_coda':'present'})
        self.assertEqual(reference_exclusion(n,self.unit('predicate','씻'),{'matched_anchors':['어']}),'documented_stem_vowel_mismatch')
    def test_unknown_source_not_certified(self):
        n=self.node('미정리 어형',12,{'stem_last_vowel':'unknown'})
        self.assertIsNone(reference_exclusion(n,self.unit('predicate','씻'),{'matched_anchors':['어형']}))
    def test_word_fragment_does_not_match_input(self):
        self.assertEqual(reference_exclusion(self.node('어린아이 → 얼라',3),self.unit('nominal'),{'matched_anchors':['아이']}),'no_input_side_anchor')
    def test_nominal_does_not_inherit_ending_anchor(self):
        unit={'kind':'nominal','observed':{'lemma':'도서관','source_form':'도서관','source_final':'야'}}
        self.assertEqual(reference_exclusion(self.node('대명사/3인칭 : 야/가/자',12),unit,{'matched_anchors':['야']}),'anchor_belongs_to_other_morpheme')

if __name__=='__main__':unittest.main()
