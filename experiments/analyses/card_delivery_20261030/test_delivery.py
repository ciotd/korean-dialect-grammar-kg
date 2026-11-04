"""Executable tests for the intervention; never calls a model."""
import copy,importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('delivery_probe',Path(__file__).with_name('run.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class ReplacementTests(unittest.TestCase):
    def setUp(self):
        self.by={i:{'id':i,'forms':['형태'],'kind':'realization_inventory','title':i,'when':{},'avoid':[]} for i in ['a','b','c','new']}
        self.packet={'cards':[self.by[i] for i in ['a','b','c']]}
        self.raw={'retrieved_ids':list(self.by),'ranking':[{'id':i,'score':s} for i,s in [('a',0),('b',1),('c',5),('new',0)]]}
    def test_replaces_lowest_unprotected_in_place_without_mutating(self):
        original=copy.deepcopy(self.packet)
        cards,swaps=m.replace_cards(self.packet,self.raw,self.by,['new'],{'a'})
        self.assertEqual([c['id'] for c in cards],['a','new','c'])
        self.assertEqual(self.packet,original)
        self.assertEqual(swaps[0]['removed'],'b')
    def test_unretrieved_card_rejected(self):
        with self.assertRaisesRegex(ValueError,'not_retrieved'):m.replace_cards(self.packet,self.raw,self.by,['missing'],set())
    def test_already_delivered_card_rejected(self):
        with self.assertRaisesRegex(ValueError,'already_delivered'):m.replace_cards(self.packet,self.raw,self.by,['a'],set())
    def test_protected_cards_cannot_be_evicted(self):
        with self.assertRaisesRegex(ValueError,'insufficient'):m.replace_cards(self.packet,self.raw,self.by,['new'],{'a','b','c'})
    def test_promotions_deduplicated(self):
        cards,swaps=m.replace_cards(self.packet,self.raw,self.by,['new','new'],set())
        self.assertEqual(len(swaps),1);self.assertEqual(len(cards),3)

if __name__=='__main__':unittest.main()
