"""Reviewer-directed single-variable comparison, two repetitions per arm.
Identical r9 prefix packets. Only two system-instruction sentences differ.
"""
from pathlib import Path
import importlib.util
H=Path(__file__).resolve().parent;R=H.parents[2]
s=importlib.util.spec_from_file_location('prefix_prepare',H/'prefix_probe.py');pre=importlib.util.module_from_spec(s);s.loader.exec_module(pre);p=pre.p
def prompts():
 previous=Path(p.read(H/'private/latest_prefix.json')['surface']);base=(previous/'generation_prompt.txt').read_text('utf8')
 edits=[('actions에는 조건을 확인한 위치, 실제 형태소, 보존할 선어말, 바꿀 종결어미와 KG 결합형이 있다. 활용의 축약·불규칙은 네가 판단해 자연스러운 어절로 조합한다.','actions에는 위치와 수정 단위별 지시가 있다. surface_edit가 있는 항목은 원문 글자 보존 작업이므로 활용·축약·불규칙을 새로 판단하지 않는다. surface_edit가 없는 항목에만 형태소와 KG 결합형으로 활용을 조합한다.'),('음운 축약·불규칙만 적용하고 제공된 결합형 외의 방언 어미 변이를 만들지 않는다.','음운 축약·불규칙은 surface_edit가 없는 항목에만 적용한다. surface_edit 항목은 보존 부분을 한 글자도 줄이지 않는다. 제공된 수정 범위 밖의 방언 어미 변이를 만들지 않는다.')]
 variant=base
 for a,b in edits:assert variant.count(a)==1;variant=variant.replace(a,b)
 return base,variant,previous
def main():
 baseline,variant,previous=prompts();saved={p.read(d/'generation_packet.json')['text']:p.read(d/'generation_packet.json') for d in (previous/'private/records').iterdir()}
 def packet(original):
  out=pre.convert(original);assert out==saved[original['text']];return out
 p.GRAPH_BY_ARM={'control':pre.t.G,'surface':pre.t.G};p.EXTRA_CODES=[Path(__file__),H/'prefix_probe.py',H/'typed_probe.py',H/'typed_delivery.py',H/'realization_probe.py'];p.COMPARISON='identical prefix packets; exactly two system-instruction sentences changed to restrict contraction to non-surface-edit actions; two repeats; no new analysis or selection';p.CONTROL_TRANSFORM=packet;p.lean=packet;p.validate_packet=pre.t.validate
 for repeat in (1,2):
  p.EXPERIMENT='prompt_contract_r'+str(repeat);p.INDEX='latest_prompt_contract_r'+str(repeat)+'.json';p.rt.GENERATION_PROMPT=baseline;p.SURFACE_PROMPT=variant;p.main()
if __name__=='__main__':main()
