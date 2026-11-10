import re
from kiwipiepy import Kiwi

class Morphology:
    def __init__(self):self.kiwi=Kiwi(num_workers=1)
    def analyze(self,text):
        tokens=[{'form':t.form,'tag':t.tag,'base_tag':t.tag.split('-')[0],
                 'start':t.start,'end':t.start+t.len,'surface':text[t.start:t.start+t.len],
                 'sentence':t.sent_position} for t in self.kiwi.tokenize(text)]
        words=[]
        for i,m in enumerate(re.finditer(r'[^\s.,!?…“”"\[\]()]+',text)):
            a,b=m.span();ts=[t for t in tokens if a<=t['start']<b and t['base_tag'] not in ('SF','SP','SSO','SSC')]
            if not ts:continue
            endings=[t for t in ts if t['base_tag'] in ('EF','EC','ETM','ETN')]
            end=endings[-1] if endings else None
            words.append({'uid':f'W{i+1}','start':a,'end':b,'surface':m.group(),'sentence':ts[0]['sentence'],
                          'morphs':[[t['form'],t['tag']] for t in ts],'tokens':ts,
                          'ending':end['form'] if end else None,'ending_tag':end['base_tag'] if end else None})
        return {'origin':'Kiwi_0.23.1','text':text,'tokens':tokens,'words':words,
                'alignment_note':'Token spans may overlap or have zero length. Edits bind whole original words, not token substrings.'}
    def join_ending(self,word,ending):
        parts=list(word['morphs'])
        index=max(i for i,x in enumerate(parts) if x[1].split('-')[0] in ('EF','EC'))
        parts[index]=[ending,parts[index][1].split('-')[0]]
        return self.kiwi.join([tuple(x) for x in parts])

def compact_morph(morph):
    return [{'id':w['uid'],'text':w['surface'],'morphs':w['morphs'],'sentence':w['sentence']} for w in morph['words']]
