"""Adversarial tests verify that validation catches real graph/export defects."""
import json,shutil,tempfile,unittest
from pathlib import Path
from validate_evidence_kg import validate
import os

ROOT=Path(os.environ['KG_TEST_ROOT'])
class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'kg';shutil.copytree(ROOT,self.root)
    def tearDown(self):self.tmp.cleanup()
    def mutate(self,filename,fn):
        p=self.root/'graph'/filename;data=[json.loads(l) for l in p.read_text(encoding='utf-8').splitlines()];fn(data)
        p.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in data),encoding='utf-8')
    def test_baseline_passes(self):self.assertTrue(validate(self.root)['passed'])
    def test_dangling_endpoint_rejected(self):
        self.mutate('edges.jsonl',lambda d:d[0].update(target='MISSING_NODE'))
        self.assertIn('reference_integrity',validate(self.root)['errors'])
    def test_changed_original_rejected(self):
        def change(d):next(n for n in d if n['id']=='G_PRED_KIND')['properties']['original_spec']['title']='changed'
        self.mutate('nodes.jsonl',change)
        self.assertIn('all_original_atoms_losslessly_preserved',validate(self.root)['errors'])
    def test_unsupported_source_quote_rejected(self):
        def change(d):next(n for n in d if n['type']=='Claim')['properties']['source_statement']='fabricated source text'
        self.mutate('nodes.jsonl',change)
        self.assertIn('claim_quote_equals_linked_span',validate(self.root)['errors'])
    def test_csv_data_loss_rejected(self):
        p=self.root/'neo4j/nodes_Claim.csv';p.write_text('id,title,node_type,properties_json\n',encoding='utf-8')
        self.assertIn('csv_nodes_lossless_roundtrip',validate(self.root)['errors'])
    def test_invalid_edge_type_rejected(self):
        self.mutate('edges.jsonl',lambda d:d[0].update(relation='unsupported_relation'))
        self.assertIn('relationship_domain_range',validate(self.root)['errors'])

if __name__=='__main__':unittest.main()
