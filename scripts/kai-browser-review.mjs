import {chromium} from 'playwright';
import {writeFile} from 'node:fs/promises';
const browser=await chromium.launch({headless:true,channel:'chromium'});
const reports=[];
try {
 const context=await browser.newContext({viewport:{width:914,height:412},deviceScaleFactor:2.625});
 const page=await context.newPage();page.on('pageerror',e=>console.error(e.message));
 for(const asset of ['kai','june','candidate']) {
  await page.goto(`http://127.0.0.1:5194/rower-fable/validation/characters/kai/?asset=${asset}`);
  await page.waitForFunction(()=>window.review?.ready);
  reports.push(await page.evaluate(()=>window.review.benchmark()));
  for(const phase of asset==='candidate'?[0,.5,1,1.4,1.7]:[0]) {
   await page.evaluate(t=>{window.review.pose(t);window.review.setView('quarter');},phase);
   await page.screenshot({path:`validation/characters/kai/browser-${asset}-${phase}.png`});
  }
 }
 await writeFile('validation/characters/kai/performance.json',JSON.stringify(reports,null,2)+'\n');
 console.log(reports);
} finally {await browser.close();}
