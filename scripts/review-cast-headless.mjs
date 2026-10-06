import assert from 'node:assert/strict';
import {mkdir,readFile,writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright';

const output='validation/characters/installed';
const browser=await chromium.launch({headless:true,channel:'chromium'});
try {
  const page=await browser.newPage({viewport:{width:1000,height:900},deviceScaleFactor:2});
  const errors=[],responses=new Map(),report=[];
  page.on('pageerror',error=>errors.push(error.message));
  page.on('response',response=>{
    const match=new URL(response.url()).pathname.match(/\/characters\/(kai|june|sol|ada)\.glb$/);
    if(match) responses.set(match[1],response);
  });
  await page.goto(process.env.REVIEW_URL||'http://127.0.0.1:5194/rower-fable/');
  await page.waitForFunction(()=>window.__sim.rower.ready);
  assert.equal(await page.locator('[data-character]').count(),4);
  for(const id of ['kai','june','sol','ada']) {
    await mkdir(`${output}/${id}`,{recursive:true});
    await page.locator(`[data-character="${id}"]`).click();
    await page.waitForFunction(id=>window.__sim.rower.ready&&window.__sim.rower.character===id,id);
    const hash=data=>createHash('sha256').update(data).digest('hex');
    const sha256=hash(await responses.get(id).body());
    assert.equal(sha256,hash(await readFile(`public/characters/${id}.glb`)));
    await page.getByRole('button',{name:/^just row$/i}).click();
    await page.getByRole('button',{name:/^begin$/i}).click();
    await page.waitForTimeout(2500);
    for(const [label,time,offset] of [
      ['catch',0,[-2.2,1.1,2.1]],['drive',.5,[-2.2,1.1,2.1]],
      ['finish',1,[-2.2,1.1,2.1]],['recovery',1.4,[-2.2,1.1,2.1]],
      ['profile',1,[0,.65,2.7]],
    ]) {
      await page.evaluate(({time,offset})=>{
        const s=window.__sim;
        s.pause(time<=1?'drive':'rec',time<=1?time:time-1);s.step();
        window.dispatchEvent(new WheelEvent('wheel'));
        const direction=s.controls.target.clone().fromArray(offset)
          .applyQuaternion(s.boat.group.getWorldQuaternion(s.camera.quaternion.clone()));
        s.camera.position.copy(s.controls.target).add(direction);
        s.controls.update();s.step();
      },{time,offset});
      await page.waitForTimeout(200);
      await page.screenshot({path:`${output}/${id}/live-${label}.png`});
    }
    await page.keyboard.press('r');
    await page.reload();
    await page.waitForFunction(id=>window.__sim.rower.ready&&window.__sim.rower.character===id,id);
    report.push({id,sha256,reloadPersisted:true});
  }
  assert.deepEqual(errors,[]);
  await writeFile(`${output}/browser-report.json`,JSON.stringify({headless:true,errors,characters:report},null,2)+'\n');
  console.log(report);
} finally {await browser.close();}
