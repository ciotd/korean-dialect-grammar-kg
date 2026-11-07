// Export the existing report; research content remains unchanged.
const fs = require('fs');
const path = require('path');
const {pathToFileURL} = require('url');
const {chromium} = require('C:/Users/ciot28/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
(async () => {
  const root = path.resolve(__dirname, '../../..');
  const out = path.join(root, 'output/pdf/research_redesign_20261106.pdf');
  fs.mkdirSync(path.dirname(out), {recursive:true});
  const browser = await chromium.launch({headless:true, executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});
  try {
    const page = await browser.newPage();
    await page.goto(pathToFileURL(path.join(__dirname,'private/report.html')).href);
    await page.evaluate(() => {
      document.querySelectorAll('details').forEach(e => e.open=true);
      document.querySelectorAll('[hidden]').forEach(e => e.removeAttribute('hidden'));
      document.querySelectorAll('.buttons').forEach(e => e.remove());
      const p = [...document.querySelectorAll('p')].find(e=>e.textContent.includes('아래에서 현재 구조와 제안 구조를 바꿔 볼 수'));
      if(p) p.textContent='PDF에서는 현재 구조와 제안 구조를 모두 펼쳐 표시합니다. 제안 구조는 아직 실행하지 않았습니다.';
      const n=document.createElement('p');n.className='small';
      n.textContent='공유용 PDF · 2026-11-06 보고서 · 접힌 검토 의견과 두 구성도를 모두 포함합니다. 문서 안의 로컬 파일·localhost 링크는 작성자 PC 전용입니다.';
      document.querySelector('header').append(n);
    });
    await page.addStyleTag({content:`
      @page {size:A4;margin:16mm 13mm 18mm}
      html,body{background:white;font-size:10pt;line-height:1.65}
      main{max-width:none;padding:0}header{padding:0}h1{font-size:23pt}
      h2{font-size:17pt;margin:18pt 0 8pt}h3{font-size:13pt;margin:14pt 0 7pt}
      h4{font-size:11pt}h1,h2,h3,h4,summary{break-after:avoid}
      p,li{orphans:3;widows:3}p{margin:7pt 0}li{margin:5pt 0}
      .lead{font-size:12pt}.small,.tag{font-size:8.5pt}
      .section,details{padding:0;margin:12pt 0;border-radius:0}
      #decision,#plan,#reviewers{break-before:page}
      details{break-before:page}summary{font-size:14pt;margin-bottom:12pt}
      #reviewers details:first-of-type{break-before:auto}
      #overview{font-size:9pt;line-height:1.45}
      #overview h2{font-size:15pt;margin:12pt 0 6pt}
      #overview p{margin:5pt 0}#overview .section{margin:8pt 0}
      nav,.buttons{display:none!important}.table{overflow:visible;margin:9pt 0}
      table{min-width:0!important;width:100%;table-layout:fixed;font-size:8.5pt}
      th,td{padding:6pt;min-width:0!important;overflow-wrap:anywhere;word-break:normal}
      tr{break-inside:avoid}thead{display:table-header-group}
      code{font-size:8.5pt;overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere}
      .flow{display:flex;flex-wrap:nowrap;gap:6pt;break-inside:avoid}
      .node{min-width:0;padding:8pt;font-size:9pt;overflow-wrap:anywhere}
      .arrow{font-size:13pt;flex-shrink:0}.note{padding:9pt;break-inside:avoid}
      a{overflow-wrap:anywhere}.toc{columns:1}
    `});
    await page.evaluate(()=>document.fonts.ready);
    await page.pdf({path:out,format:'A4',printBackground:true,preferCSSPageSize:true,displayHeaderFooter:true,headerTemplate:'<span></span>',footerTemplate:'<div style="width:100%;font-size:8px;color:#607080;text-align:center">KG Research Plan · 2026-11-06 &nbsp; | &nbsp; <span class="pageNumber"></span> / <span class="totalPages"></span></div>'});
    console.log(JSON.stringify({output:out,bytes:fs.statSync(out).size}));
  } finally {await browser.close();}
})();
