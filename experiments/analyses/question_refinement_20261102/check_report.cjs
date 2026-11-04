// Offline interactions only; no browser rendering or external requests.
const fs=require('fs'),vm=require('vm'),path=require('path'),assert=require('assert');
const here=__dirname,h=fs.readFileSync(path.join(here,'private/report.html'),'utf8'),payload=h.match(/<script type="application\/json" id="data">([\s\S]*?)<\/script>/)[1];
function element(){return {value:'',textContent:'',innerHTML:'',hidden:false,children:[],handlers:{},attrs:{},dataset:{},appendChild(x){this.children.push(x)},addEventListener(k,f){this.handlers[k]=f},setAttribute(k,v){this.attrs[k]=v}}}
const elems=Object.fromEntries([...h.matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],element()]));elems.data.textContent=payload;
const buttons=['answer','example','evidence'].map(v=>Object.assign(element(),{dataset:{view:v}}));
const context=vm.createContext({document:{getElementById(id){assert(elems[id],id);return elems[id]},createElement:element,querySelectorAll(s){assert.equal(s,'nav button');return buttons}}});
const scripts=[...h.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)];vm.runInContext(scripts.at(-1)[1],context);
const data=JSON.parse(payload);let count=0;assert.equal(elems.caseSelect.children.length,data.cases.length);
for(const c of data.cases){elems.caseSelect.value=c.id;elems.caseSelect.handlers.change();assert(elems.worked.innerHTML.includes(c.analysis.text));assert(elems.technical.textContent.includes(c.packet.graph_version));count++}
for(const b of buttons){b.handlers.click();assert.equal(b.attrs['aria-selected'],'true');assert.equal(elems[b.dataset.view].hidden,false);count++}
assert(!h.includes('@DATA@'));assert(!/<script[^>]+src=/.test(h));assert(elems.rules.innerHTML.includes('SEM_Q_')===false);count++;
const result={passed:true,interaction_cases:count,scope:'offline JS with DOM stubs, not browser visual inspection'};fs.writeFileSync(path.join(here,'private/report_check.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
