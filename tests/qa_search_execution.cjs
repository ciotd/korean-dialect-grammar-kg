const {chromium}=require('C:/Users/ciot28/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path');
const out=path.resolve(__dirname,'../experiments/validation/runtime_20261025/private');fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 const context=await browser.newContext({viewport:{width:1440,height:1000}}),page=await context.newPage(),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8766/reports/search-execution/report.html');
 await page.waitForFunction(()=>document.querySelectorAll('#summary .card').length===4);
 if(await page.locator('#kg-list tbody tr').count()!==721)throw Error('all_721_not_visible');
 if(await page.locator('#case-id option').count()!==50)throw Error('regression_count');
 await page.screenshot({path:out+'/report_desktop.png'});
 await page.locator('#kg-module').selectOption('M04');if(await page.locator('#kg-list tbody tr').count()!==101)throw Error('particle_count');
 await page.locator('#kg-list button').first().click();if(!(await page.locator('#kg-detail').textContent()).includes('미연결'))throw Error('search_execution_distinction');
 await page.locator('#case-condition').selectOption('multi');await page.locator('#case-id').selectOption('LONG003');
 if(!(await page.locator('#case-detail').textContent()).includes('들어가야'))throw Error('failed_actual_output_missing');
 await page.locator('#case-id').selectOption('DEV012');if(await page.locator('.network svg').count()!==1)throw Error('actual_graph_missing');
 await page.locator('#cases').scrollIntoViewIfNeeded();await page.screenshot({path:out+'/actual_case.png'});
 await page.locator('#case-group').selectOption('evaluation');if(await page.locator('#case-id option').count()!==12)throw Error('unseen_count');
 await page.locator('#case-group').selectOption('diagnostic');if(await page.locator('#case-id option').count()!==50)throw Error('diagnostic_count');
 await page.setViewportSize({width:390,height:844});await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:out+'/report_mobile.png'});
 const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
 await page.goto('http://127.0.0.1:8766/reports/search-execution/review.html');await page.waitForFunction(()=>document.querySelectorAll('#review-case option').length===62);
 if(await page.locator('#review-content article').count()!==2)throw Error('blind_pair_missing');
 if(!(await page.locator('#progress').textContent()).includes('평가 0 /'))throw Error('scores_not_initially_null');
 await page.locator('#review-content article').first().locator('select').first().selectOption('4');
 if(!(await page.locator('#progress').textContent()).includes('평가 1 /'))throw Error('human_input_not_saved');
 await page.reload();await page.waitForFunction(()=>document.querySelector('#progress').textContent.includes('평가 1 /'));
 await page.evaluate(()=>localStorage.clear()); // Isolated QA browser only; no experimental scores submitted.
 await page.goto('http://127.0.0.1:8766/');await page.waitForFunction(()=>document.querySelectorAll('#run-rows tr').length>=18);
 await page.locator('[data-tab="comparison"]').click();
 await page.locator('#left-run').selectOption('20261025T085653301020Z_runtime_single_regression');await page.locator('#right-run').selectOption('20261025T085653584686Z_runtime_multi_regression');await page.locator('#compare').click();
 await page.waitForFunction(()=>document.querySelector('#compare-result').textContent.includes('같은 입력 기준'));
 const info=await (await page.request.get('http://127.0.0.1:8766/api/info')).json(),links=[];
 for(const x of info.reports){const r=await page.request.get(x.url);links.push({url:x.url,status:r.status()});}
 const blocked=(await page.request.get('http://127.0.0.1:8766/reports/search-execution/blind_review_key.json')).status();
 const result={all_source_atoms:721,particle_atoms:101,regression_cases:50,evaluation_cases:12,diagnostic_cases:50,blind_pairs:62,
  actual_graph:true,actual_failure_comparison:true,human_form_persistence:true,qa_scores_not_submitted:true,mobile_overflow:overflow,browser_errors:errors,links,blinding_key_http_status:blocked};
 fs.writeFileSync(out+'/browser_qa.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 await browser.close();if(overflow||errors.length||links.some(x=>x.status!==200)||blocked!==404)process.exitCode=1;
})().catch(e=>{console.error(e);process.exit(1);});
