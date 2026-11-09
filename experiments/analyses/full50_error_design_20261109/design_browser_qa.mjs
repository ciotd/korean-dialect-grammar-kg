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
 await call('Page.navigate',{url:pathToFileURL(path.resolve('experiments/analyses/full50_error_design_20261109/report.html')).href}); await delay(1800);
 const checks=(await evaluate("({title:document.title,h2:document.querySelectorAll('h2').length,tables:document.querySelectorAll('table').length,overflow:document.documentElement.scrollWidth>innerWidth,text:document.body.innerText.length})")).result.value;
 const shot=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false,fromSurface:true});fs.writeFileSync(path.join(dir,'design-preview.png'),Buffer.from(shot.data,'base64'));
 await evaluate("document.querySelectorAll('h2')[0].scrollIntoView()");await delay(300);
 const shot2=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:false,fromSurface:true});fs.writeFileSync(path.join(dir,'design-errors.png'),Buffer.from(shot2.data,'base64'));
 checks.errors=errors;if(checks.overflow||errors.length||checks.tables<4)throw new Error('Design layout check failed');
 fs.writeFileSync(path.join(dir,'design_browser_qa.json'),JSON.stringify(checks,null,2));console.log(JSON.stringify(checks));await call('Browser.close').catch(()=>{});
} finally {if(ws)ws.close();child.kill();}
