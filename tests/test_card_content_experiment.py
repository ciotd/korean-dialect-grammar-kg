import copy,importlib.util,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'local/python'),str(ROOT/'src')]
from kg_runtime import card_pipeline as cp
spec=importlib.util.spec_from_file_location('content_experiment',ROOT/'experiments/analyses/card_content_experiment_20261030/run.py')
run=importlib.util.module_from_spec(spec);spec.loader.exec_module(run)

class ProjectionTests(unittest.TestCase):
    def test_only_cards_and_derived_context_change(self):
        morph={'text':'가요','words':[{'uid':'W1','start':0,'end':2,'surface':'가요','morphs':[['가','VV'],['어요','EF']]}]}
        cards=[{'id':'A','forms':['-요','-예'],'when':{'target_profile':'required'},'title':'a','kind':'realization_inventory','module':1,'avoid':[]}]
        analysis={'units':[]}
        packet={'input':'가요','words':morph['words'],'grammar':analysis,'cards':cards,'contract_context':cp.context(morph,cards,analysis,'T')}
        before=copy.deepcopy(packet)
        class Content:
            def project_cards(self,cards):
                changed=copy.deepcopy(cards);changed[0]['when']={'input_politeness':'polite'}
                return changed,{'selected_ids':['A']}
        result,audit=run.projected_packet(packet,morph,'T',Content())
        self.assertEqual(packet,before)
        self.assertEqual(audit['selected_ids'],['A'])
        self.assertNotEqual(result['contract_context']['request_id'],packet['contract_context']['request_id'])
        self.assertEqual(result['cards'][0]['forms'],cards[0]['forms'])

    def test_selection_reordering_is_rejected(self):
        class Content:
            def project_cards(self,cards):return list(reversed(cards)),{}
        morph={'text':'가요','words':[]};analysis={'units':[]}
        cards=[{'id':'A'},{'id':'B'}]
        packet={'input':'가요','grammar':analysis,'cards':cards,'contract_context':cp.context(morph,cards,analysis,'T')}
        with self.assertRaises(AssertionError):run.projected_packet(packet,morph,'T',Content())

if __name__=='__main__':unittest.main()
