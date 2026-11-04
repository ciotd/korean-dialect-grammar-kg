// Offline data/JavaScript checks only. Does not open a browser or validate rendering.
const fs=require('fs'),vm=require('vm'),path=require('path'),assert=require('assert');
const here=__dirname,html=fs.readFileSync(path.join(here,'private/report.html'),'utf8');
const payload=html.match(/<script type="application\/json" id="data">([\s\S]*?)<\/script>/)[1];
const scripts=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)];
function element(){return {value:'',textContent:'',innerHTML:'',children:[],handlers:{},attrs:{},dataset:{},classList:{toggle(){}},appendChild(x){this.children.push(x)},addEventListener(k,f){this.handlers[k]=f},setAttribute(k,v){this.attrs[k]=v}}}
const elements=Object.fromEntries([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],element()]));elements.data.textContent=payload;
const buttons=['answer','packages','sources','review'].map(v=>Object.assign(element(),{dataset:{view:v}}));
const document={getElementById(id){if(!elements[id])throw Error('Missing DOM ID '+id);return elements[id]},createElement:element,querySelectorAll(sel){assert.equal(sel,'nav button');return buttons}};
const context=vm.createContext({document});vm.runInContext(scripts.at(-1)[1],context);
const data=JSON.parse(payload);assert.equal(data.sections.length,102);assert.equal(data.items.length,911);assert.equal(elements.docFilter.children.length,7);
let cases=0;
for(const s of data.sources){elements.docFilter.value=s.id;vm.runInContext('sections()',context);assert(elements.sectionCount.textContent.startsWith(data.sections.filter(x=>x.doc===s.id).length+'개'));cases++}
elements.docFilter.value='';elements.sourceSearch.value='없는검색어ZZZZ';vm.runInContext('sections()',context);assert(elements.sectionCount.textContent.startsWith('0개'));cases++;
elements.packageSearch.value='묻는 말';vm.runInContext('packages()',context);assert(elements.packageList.innerHTML.includes('묻는 말의 어미'));cases++;
for(const button of buttons){button.handlers.click();assert.equal(button.attrs['aria-selected'],'true');cases++}
assert(elements.resolution.innerHTML.includes('인용을 질문'));assert(elements.gapList.innerHTML.length>0);cases++;
assert(!/@(?:DATA|ITEMS|PAGES|PACKS|SECTIONS|TESTS)@/.test(html));assert(!/<script[^>]+src=/.test(html));cases++;
const result={passed:true,interaction_cases:cases,scope:'offline JavaScript DOM stubs and embedded data; not browser rendering',sections:data.sections.length,legacy_items:data.items.length};
fs.writeFileSync(path.join(here,'private/report_check.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
