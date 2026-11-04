// Offline script/data QA. This is not browser rendering or visual QA.
const fs=require('fs'),vm=require('vm'),path=require('path');
const file=path.join(__dirname,'private','report.html');
const html=fs.readFileSync(file,'utf8');
const data=html.match(/<script id="payload" type="application\/json">([\s\S]*?)<\/script>/)[1];
const scripts=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)];
const elements={payload:{textContent:data}};
function element(){return {value:'',textContent:'',innerHTML:'',children:[],append(x){this.children.push(x)},addEventListener(){}}}
const document={getElementById(id){return elements[id]??=element()},createElement(){return element()}};
const context=vm.createContext({document});
vm.runInContext(scripts.at(-1)[1],context);
const d=JSON.parse(data);
for(const c of d.cases){elements.case.value=c.id;vm.runInContext('draw()',context);if(!elements.example.innerHTML.includes(c.analysis.text))throw Error('Missing example '+c.id);JSON.parse(elements.packet.textContent)}
const result={checks:'offline JavaScript execution with DOM stubs; no visual browser review',case_count:d.cases.length,selector_options:elements.case.children.length,passed:true};
fs.writeFileSync(path.join(__dirname,'private','report_check.json'),JSON.stringify(result,null,2));
console.log(JSON.stringify(result));
