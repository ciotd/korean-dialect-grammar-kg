// Offline functional checks, not browser rendering or actual disk download.
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');
const h=fs.readFileSync(path.join(__dirname,'private/review.html'),'utf8');
const payload=h.match(/<script type="application\/json" id="data">([\s\S]*?)<\/script>/)[1];
const script=[...h.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].at(-1)[1];
const data=JSON.parse(payload),store=new Map();
function boot(broken=false){const elements={};const downloads=[];let blob;
 function el(){let inner='';return {value:'',textContent:'',hidden:false,handlers:{},children:[],get innerHTML(){return inner},set innerHTML(s){inner=s;scan(s)},addEventListener(k,f){this.handlers[k]=f},appendChild(x){this.children.push(x)},click(){if(this.download)downloads.push(this.download)},remove(){}}}
 function scan(s){for(const m of s.matchAll(/\bid="([^"]+)"/g))elements[m[1]]=el()}
 scan(h);elements.data.textContent=payload;elements.filter.value='all';
 const ctx=vm.createContext({document:{getElementById(id){assert(elements[id],id);return elements[id]},createElement:el,body:el()},localStorage:{getItem(k){if(broken)throw Error('blocked');return store.get(k)},setItem(k,v){if(broken)throw Error('blocked');store.set(k,v)}},Blob:class{constructor(a){blob=a.join('')}},URL:{createObjectURL(){return 'blob:test'},revokeObjectURL(){}},setTimeout:f=>f(),confirm:()=>true});
 vm.runInContext(script,ctx);return {elements,ctx,downloads,get blob(){return blob}}}
let n=0;const a=boot();assert.equal(data.rows.length,16);assert.equal(new Set(data.rows.map(r=>r.input)).size,15);assert.equal(data.rows.flatMap(r=>r.candidates).length,16);assert.equal(a.elements.progress.textContent,'검토 0 / 16개');n++;
assert(!a.elements['Q16-naturalness']);assert(a.elements['Q13A-naturalness']&&a.elements['Q13B-naturalness']);n++;
for(const c of data.rows.flatMap(r=>r.candidates)){
 for(const [field,value] of [['naturalness','uncertain'],['meaning','context']]){a.elements[c.id+'-'+field].value=value;a.elements[c.id+'-'+field].handlers.change()}
 n++;
}
assert.equal(a.elements.progress.textContent,'검토 16 / 16개');a.elements.filter.value='pending';a.elements.filter.handlers.change();assert(data.rows.every(r=>a.elements['row-'+r.id].hidden));n++;
const b=boot();assert.equal(b.elements.progress.textContent,'검토 16 / 16개');n++;
b.elements['Q01-comment'].value='<script>alert(1)</script>';b.elements['Q01-comment'].handlers.input();vm.runInContext('draw()',b.ctx);assert(b.elements.cases.innerHTML.includes('&lt;script&gt;alert(1)&lt;/script&gt;'));n++;
b.elements.download.handlers.click();const exported=JSON.parse(b.blob);assert.equal(Object.keys(exported.answers).length,16);assert.equal(exported.answers.Q01.comment,'<script>alert(1)</script>');assert.equal(b.downloads.length,1);n++;
for(const bad of [
 {...exported,review_set_hash:'wrong'},
 {...exported,answers:{Q16:{naturalness:'natural',meaning:'preserved',alternative:'',comment:''}}},
 {...exported,answers:{Q01:{naturalness:'approved',meaning:'preserved',alternative:'',comment:''}}}
]){b.ctx.bad=bad;assert.throws(()=>vm.runInContext('validateRecord(bad)',b.ctx));n++}
const c=boot(true);assert(c.elements.saveStatus.textContent.includes('읽지 못'));c.elements.download.handlers.click();assert.equal(c.downloads.length,1);n++;
assert(!h.includes('@@DATA@@'));assert(!/<script[^>]+src=/.test(h));assert(!/fetch\(/.test(script));n++;
const result={passed:true,checks:n,scope:'offline form, draft restoration, export request, invalid import rejection, escaping; not browser visual QA or real download',model_calls:0};
fs.writeFileSync(path.join(__dirname,'private/ui_check.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
