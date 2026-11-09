// Local artifact QA only. Launches an isolated, hidden headless Chrome.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawn} from 'node:child_process';
import {pathToFileURL} from 'node:url';
const dir=path.resolve('experiments/analyses/full50_error_design_20261109/private');
const profile=fs.mkdtempSync(path.join(os.tmpdir(),'kg50-cdp-'));
const child=spawn('C:/Program Files/Google/Chrome/Application/chrome.exe',[
 '--headless','--disable-gpu','--no-first-run','--no-default-browser-check',
 '--allow-file-access-from-files','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],
 {windowsHide:true,stdio:'ignore'});
const delay=ms=>new Promise(r=>setTimeout(r,ms));
let ws;
try {
 for(let i=0;i<100&&!fs.existsSync(path.join(profile,'DevToolsActivePort'));i++)await delay(100);
 const port=fs.readFileSync(path.join(profile,'DevToolsActivePort'),'utf8').split('\n')[0];
 const tabs=await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
 ws=new WebSocket(tabs.find(t=>t.type==='page'&&t.url==='about:blank').webSocketDebuggerUrl);
 await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject;});
 let id=0;const pending=new Map();const errors=[];
 ws.onmessage=e=>{const v=JSON.parse(e.data);if(v.id&&pending.has(v.id)){const p=pending.get(v.id);pending.delete(v.id);clearTimeout(p.timer);v.error?p.reject(v.error):p.resolve(v.result);}
   if(v.method==='Runtime.exceptionThrown')errors.push(v.params.exceptionDetails.text);};
 const call=(method,params={})=>new Promise((resolve,reject)=>{const n=++id;pending.set(n,{resolve,reject,timer:setTimeout(()=>reject(new Error(method+' timeout')),15000)});ws.send(JSON.stringify({id:n,method,params}));});
 const evaluate=expression=>call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
 await call('Page.enable');await call('Runtime.enable');
 await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1100,deviceScaleFactor:1,mobile:false});
 console.log('nav', await call('Page.navigate',{url:'http://127.0.0.1:8879/#case-DEV002'}));await delay(5000); console.log('document',JSON.stringify(await evaluate("({url:location.href,title:document.title,ready:document.readyState,length:document.body?.innerHTML.length,text:document.body?.innerText.slice(0,200),target:!!document.getElementById('results')})")));
 const checks={};
 for(const section of ['results','case-DEV002']){
   await evaluate(`document.querySelector('#${section}').open=true;document.querySelector('#${section}').scrollIntoView();`);await delay(500);
   checks[section]=(await evaluate(`({scrollY,elementAtTop:document.elementFromPoint(100,150)?.textContent?.slice(0,100),overflow:document.documentElement.scrollWidth>innerWidth})`)).result.value;
   console.log(section,JSON.stringify(checks[section])); const shot=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false,fromSurface:true});
   fs.writeFileSync(path.join(dir,'checked-'+section+'.png'),Buffer.from(shot.data,'base64'));
 }
 checks.search=(await evaluate(`document.querySelector('#search').value='DEV002';document.querySelector('#search').dispatchEvent(new Event('input'));({visible:[...document.querySelectorAll('#overview tr')].filter(x=>!x.hidden).length,total:document.querySelectorAll('#overview tr').length})`)).result.value;
 checks.errors=errors; if(checks.search.total!==50||checks.search.visible!==1||errors.length||checks.results.overflow||checks['case-DEV002'].overflow)throw new Error('Report interaction/overflow check failed'); fs.writeFileSync(path.join(dir,'browser_qa.json'),JSON.stringify(checks,null,2));console.log(JSON.stringify(checks));
 await call('Browser.close').catch(()=>{});
} finally {if(ws)ws.close();child.kill();}
