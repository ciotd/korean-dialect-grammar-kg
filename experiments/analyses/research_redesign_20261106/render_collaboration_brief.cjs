const fs=require('fs'),path=require('path'),{pathToFileURL}=require('url');
const {chromium}=require('C:/Users/ciot28/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async()=>{
 const root=path.resolve(__dirname,'../../..');
 const input=path.join(root,'output/pdf/research_collaboration_brief_20261107.html');
 const output=input.replace('.html','.pdf');
 const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
 try{
  const page=await browser.newPage();await page.goto(pathToFileURL(input).href);await page.evaluate(()=>document.fonts.ready);
  await page.emulateMedia({media:'print'});
  const layout=await page.evaluate(()=>[...document.querySelectorAll('.page')].map((s,i)=>{
   const c=s.querySelector('.content').getBoundingClientRect(),f=s.querySelector('.source').getBoundingClientRect();
   return{page:i+1,contentBottom:c.bottom-s.getBoundingClientRect().top,sourceTop:f.top-s.getBoundingClientRect().top,gap:f.top-c.bottom,overflow:c.bottom>f.top-8};
  }));
  const checks=path.join(root,'tmp/pdfs/collaboration_brief_20261107');fs.mkdirSync(checks,{recursive:true});
  fs.writeFileSync(path.join(checks,'layout.json'),JSON.stringify(layout,null,2));
  if(layout.some(x=>x.overflow))throw new Error('Content collides with source/footer: '+JSON.stringify(layout.filter(x=>x.overflow)));
  await page.pdf({path:output,format:'A4',preferCSSPageSize:true,printBackground:true,displayHeaderFooter:false});
  console.log(JSON.stringify({output,bytes:fs.statSync(output).size,layout}));
 }finally{await browser.close();}
})();
