import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('checkpoint_separation_test',ROOT/'tools/research_checkpoint.py')
checkpoint=importlib.util.module_from_spec(spec);spec.loader.exec_module(checkpoint)


class BackupTests(unittest.TestCase):
    def test_nested_bundle_is_local_only_and_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'knowledge/authored/new/private/version1';folder.mkdir(parents=True)
            for name in ('graph.json','audit.json','manifest.json','unrelated_secret.json'):
                (folder/name).write_text('{}',encoding='utf8')
            selected=checkpoint.private_kg_paths(root)
            self.assertEqual({p.name for p in selected},{'graph.json','audit.json','manifest.json'})
            self.assertTrue(all(checkpoint.denied(p.relative_to(root).as_posix()) for p in selected))


if __name__=='__main__':unittest.main()
