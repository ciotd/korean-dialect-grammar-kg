import unittest
from composer import compose
from pipeline import *
from kg_runtime.morphology import Morphology
class ComposerTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.k=Morphology().kiwi
 def action(self,parts,ending='나',nominal=None,integrated=False):return {'source_morphs':parts,'nominal':nominal,'forms':[{'selected_combining_form':ending,'includes_copula':integrated}]}
 def test_vowel_allomorph(self):self.assertEqual(compose(self.k,self.action([['보','VV'],['었','EP'],['어','EF']]))[0],'봤나')
 def test_irregular_tag(self):self.assertEqual(compose(self.k,self.action([['춥','VA-I'],['었','EP'],['어','EF']]))[0],'추웠나')
 def test_consonant_ending(self):self.assertEqual(compose(self.k,self.action([['차갑','VA-I'],['어','EF']]))[0],'차갑나')
 def test_l_final(self):self.assertEqual(compose(self.k,self.action([['알','VV'],['어','EF']]))[0],'아나')
 def test_integrated_copula(self):self.assertEqual(compose(self.k,self.action([],ending='이가',nominal='학생',integrated=True))[0],'학생이가')
 def test_past_copula(self):self.assertEqual(compose(self.k,self.action([['의사','NNG'],['이','VCP'],['었','EP'],['어','EF']],ending='노'))[0],'의사였노')
 def test_no_final_rejected(self):
  with self.assertRaises(ValueError):compose(self.k,self.action([['보','VV']]))
 def test_multiple_forms_rejected(self):
  a=self.action([['보','VV'],['어','EF']]);a['forms']*=2
  with self.assertRaises(ValueError):compose(self.k,a)
if __name__=='__main__':unittest.main(verbosity=2)
