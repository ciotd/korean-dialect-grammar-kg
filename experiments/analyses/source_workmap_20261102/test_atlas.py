"""Coverage/lineage safeguards, not tests of linguistic truth."""
import unittest
import build_atlas as b

class AtlasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.a=b.read(b.HERE/'private/atlas.json')
        cls.nodes=b.jsonl(b.BASE/'graph/nodes.jsonl')
        cls.items={r['legacy_id']:r for r in cls.a['legacy_items']}
        cls.sections={s['id']:s for s in cls.a['sections']}
        cls.packs={p['id']:p for p in cls.a['work_packages']}

    def test_every_legacy_design_id_exactly_once(self):
        expected={n['id'] for n in self.nodes if n['type'] in b.DESIGN_TYPES}
        self.assertEqual(expected,set(self.items))
        self.assertEqual(len(expected),len(self.a['legacy_items']))

    def test_all_pdf_pages_covered_without_invented_pages(self):
        expected={(s['id'],p) for s in self.a['sources'] for p in range(1,s['pages']+1)}
        actual={(p['doc'],p['pdf_page']) for p in self.a['pages']}
        self.assertEqual(expected,actual)
        self.assertEqual(len(expected),len(self.a['pages']))
        self.assertTrue(all(p['section_ids'] for p in self.a['pages']))

    def test_both_mapping_directions_agree(self):
        actual={(x['section_id'],x['legacy_id']) for x in self.a['candidate_links']}
        expected=set()
        for sid,s in self.sections.items():
            for i,r in self.items.items():
                if any(q['doc']==s['doc'] and s['pdf_start']<=q['pdf_page']<=s['pdf_end'] for q in r['references']):expected.add((sid,i))
            self.assertEqual(set(s['legacy_candidates']),{i for a,i in actual if a==sid})
        self.assertEqual(actual,expected)
        self.assertEqual(len(actual),len(self.a['candidate_links']))

    def test_structural_match_cannot_be_semantic_approval(self):
        self.assertTrue(all(x['semantic_support']=='unverified' for x in self.a['candidate_links']))
        self.assertTrue(all(r['semantic_validation_this_stage']=='not_performed' for r in self.items.values()))
        self.assertEqual(0,self.a['stats']['semantic_items_completed_this_stage'])

    def test_no_runtime_claim_from_property(self):
        self.assertTrue(all(r['runtime_validation']=='not_tested_this_stage' for r in self.items.values()))
        self.assertTrue(all(r['condition_edge_validation']=='not_certified_by_this_map' for r in self.items.values()))

    def test_source_first_assignment_is_not_derived_from_kg_coverage(self):
        # Conclusion and Q&A have no legacy page refs, but still get grammar review work.
        for doc,start in [('D02',225),('D03',27)]:
            s=next(s for s in self.sections.values() if s['doc']==doc and s['pdf_start']==start)
            self.assertFalse(s['legacy_candidates'])
            self.assertIn('F03',s['work_packages'])

    def test_routing_across_modules_and_prefix_collision(self):
        self.assertIn('F19',self.items['GS_HAM_NEG_AN']['work_packages'])
        self.assertEqual(12,self.items['GS_HAM_NEG_AN']['legacy_module'])
        self.assertIn('F21',self.items['GS_HAM_AUX_SERVICE']['work_packages'])
        self.assertIn('F11',self.items['GS_HAM_LOC']['work_packages'])
        self.assertIn('F16',self.items['GS_HAM_QUOTE']['work_packages'])
        self.assertNotIn('F03',self.items['GS_HAM_QUOTE']['work_packages'])
        self.assertIn('F03',self.items['GS_HAM_Q']['work_packages'])
        for n in self.nodes:
            if n['id'].startswith('GS_HAM_LOCATIVE'):self.assertIn('F09',self.items[n['id']]['work_packages'])

    def test_work_packages_are_complete_and_acyclic(self):
        for r in self.items.values():
            self.assertTrue(r['work_packages'])
            self.assertLessEqual(set(r['work_packages']),set(self.packs))
        def visit(i,chain):
            self.assertNotIn(i,chain)
            for d in self.packs[i]['depends']:visit(d,chain+[i])
        for i,p in self.packs.items():
            for k in ('analysis','query','delivery','exit','split'):self.assertTrue(p[k])
            visit(i,[])

    def test_source_assignment_stable_under_reordering_and_new_sections_detected(self):
        assignments=b.read(b.HERE/'source_assignments.json')
        ss=b.read(b.HERE/'private/reviewer_work/claude/source_sections.json')['sections']
        forward={b.section_key(s):b.section_assignment(s,assignments) for s in ss}
        reverse={b.section_key(s):b.section_assignment(s,assignments) for s in reversed(ss)}
        self.assertEqual(forward,reverse)
        self.assertEqual('unassigned_needs_review',b.section_assignment({'doc':'D01','section':'NEW'},assignments)['content_role'])

    def test_low_priority_is_not_non_grammar(self):
        s=next(s for s in self.sections.values() if s['doc']=='D02' and s['pdf_start']==183)
        self.assertEqual('grammar_or_lexical_description',s['content_role'])
        self.assertEqual('low',s['refinement_priority'])

    def test_common_contract_title_routing_and_context_separation(self):
        for i,f in [('G_END_CAUSE','F13'),('G_END_SEQUENCE','F14'),('G_GE_DEGREE','F17'),('G_BOUND_NOUN_GEOT','F02')]:
            self.assertIn(f,self.items[i]['work_packages'])
        for r in self.items.values():
            if r['legacy_id'].startswith('GS_END_'):
                self.assertNotIn('F08',r['work_packages'])
                self.assertIn('F08',r['context_links'])
        self.assertFalse(any(r['routing_basis']=='module_based_candidate_not_semantic_mapping' for r in self.items.values()))

    def test_source_family_and_reading_depth_retained(self):
        wiki=[s['family'] for s in self.a['sources'] if s['id'] in ('D03','D04','D05','D06')]
        self.assertEqual(1,len(set(wiki)))
        self.assertTrue(any(s['read_scope'] in ('head','table','toc') for s in self.sections.values()))
        self.assertFalse(any(s['pdf_visual_checked_this_stage'] for s in self.sections.values()))

    def test_all_references_valid_and_inputs_unchanged(self):
        self.assertFalse(self.a['stats']['invalid_references'])
        self.assertTrue(all(s['pdf_matches_original'] and s['cache_matches_extraction'] for s in self.a['sources']))
        for p,h in b.read(b.HERE/'private/input_hashes.json').items():self.assertEqual(h,b.sha(b.ROOT/p))

    def test_claims_without_atom_not_silently_lost(self):
        self.assertEqual({n['id'] for n in self.nodes if n['type']=='Claim'}, {c['claim_id'] for c in self.a['existing_claims']})
        self.assertEqual(4,sum(not c['source_atom_ids'] for c in self.a['existing_claims']))

    def test_gap_candidates_are_not_confirmed_missing_claims(self):
        for g in self.a['source_gap_candidates']:
            self.assertEqual('search_other_pages_and_read_body_before_declaring_missing',g['status'])
            self.assertTrue(g['work_packages'])
            self.assertFalse(any(self.items[i]['type']=='SourceAtom' for i in self.sections[g['section_id']]['legacy_candidates']))

    def test_first_slice_contract_ids_exist_and_scope_is_explicit(self):
        x=b.read(b.HERE/'next_work.json')
        self.assertEqual('planned_not_executed',x['status'])
        self.assertTrue(x['first_slice']['outside_slice_not_ungrammatical'])
        for c in x['first_slice']['required_contracts']+[x['other_required_fragment_example']]:
            for i in c['legacy_concepts']:self.assertIn(i,self.items)
            for k in ('unknown','acceptance','basis','supplier'):self.assertTrue(c[k])

if __name__=='__main__':unittest.main()
