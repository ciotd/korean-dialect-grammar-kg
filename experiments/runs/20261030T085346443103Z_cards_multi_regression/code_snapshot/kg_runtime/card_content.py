"""Explicit, same-ID content projection after the unchanged v2 ranking."""
import re
from pathlib import Path
from kg_pipeline.io import read,dumps,sha
from .cards import VERSION

class CardContent:
    def __init__(self,project,version):
        if not re.fullmatch(r'kg_cards_[A-Za-z0-9_]+',version):raise ValueError('invalid_card_content_version')
        self.project=Path(project);self.version=version
        self.folder=self.project/'knowledge/authored'/version
        base_path=self.project/'knowledge/authored'/VERSION/'cards.json';base=read(base_path)
        data=read(self.folder/'cards.json')
        if data['version']!=version or data['source_dataset']!=base['source_dataset']:raise ValueError('content_dataset_mismatch')
        self.by={c['id']:c for c in data['cards']};self.base={c['id']:c for c in base['cards']}
        if len(self.by)!=len(data['cards']) or self.by.keys()!=self.base.keys():raise ValueError('content_ids_mismatch')
        for cid,c in self.by.items():
            if any(c[k]!=self.base[cid][k] for k in ('id','module','kind','title','forms','avoid')):raise ValueError('content_structure_changed:'+cid)
            directive=c.get('rewrite',{});ix=directive.get('target_form_index')
            if ix is not None and (type(ix)!=int or not 0<=ix<len(c['forms'])):raise ValueError('content_target_index_invalid')
        if version!=VERSION:
            manifest=read(self.folder/'manifest.json')
            if manifest.get('cards_content_sha256')!=sha(dumps(data).encode()):raise ValueError('content_hash_mismatch')
            if manifest.get('provenance_content_sha256')!=sha(dumps(read(self.folder/'provenance.json')).encode()):raise ValueError('content_provenance_mismatch')
            if manifest['parent']!=VERSION or manifest['parent_cards_sha256']!=sha(base_path.read_bytes()):raise ValueError('content_parent_mismatch')

    def project_cards(self,selected):
        ids=[c['id'] for c in selected]
        if len(ids)!=len(set(ids)):raise ValueError('duplicate_selected_card')
        for c in selected:
            if c!=self.base.get(c['id']):raise ValueError('projection_requires_original_ranked_cards')
        cards=[self.by[cid] for cid in ids]
        return cards,{'selection_version':VERSION,'generation_version':self.version,'selected_ids':ids,
            'same_ids_and_order':True,'before_sha256':sha(dumps(selected).encode()),'after_sha256':sha(dumps(cards).encode())}
