import { chromium } from 'playwright';
import { mkdir, writeFile } from 'node:fs/promises';
import assert from 'node:assert/strict';

const url = process.env.PROFILE_URL || 'http://127.0.0.1:5176/rower-fable/?perf=1';
const label = process.env.PROFILE_LABEL || 'headless-native';
const output = 'validation/performance';
await mkdir(output, { recursive: true });
const browser = await chromium.launch({
  headless: true, channel: 'chromium',
});
try {
  const viewport = { width: 914, height: 412 };
  const context = await browser.newContext({ viewport, screen: viewport, deviceScaleFactor: 2.625 });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => {
    if (message.type() === 'error' && message.text().includes('River scenery')) errors.push(message.text());
  });
  await page.goto(url);
  await page.getByText('Performance · local measurements', { exact: true }).click();
  await page.getByRole('button', { name: 'Choose June', exact: true }).click();
  await page.waitForFunction(() => document.querySelector('#characterStatus').textContent === 'June is ready');
  await page.getByRole('button', { name: /^just row$/i }).click();
  await page.getByText('Performance · local measurements', { exact: true }).click();
  await page.getByRole('button', { name: 'Run 60s rowing sample', exact: true }).click();
  console.log(`${label}: headless only, native DPR 2.625; warming up for 10s, sampling for 60s.`);
  await page.waitForFunction(() => document.querySelector('#perf-live').textContent.startsWith('60s sample complete'), null, { timeout: 85000 });
  await page.getByText('Report data', { exact: true }).click();
  await page.waitForFunction(() => document.querySelector('#perf-report').textContent.startsWith('{'));
  const report = JSON.parse(await page.locator('#perf-report').textContent());
  report.testEnvironment = { headless: true, viewport, deviceScaleFactor: 2.625,
    note: 'Phone-sized viewport on the desktop GPU. Not a Pixel 8 hardware/thermal test.' };
  await writeFile(`${output}/${label}.json`, JSON.stringify(report, null, 2));
  await page.getByText('Report data', { exact: true }).click();
  await page.screenshot({ path: `${output}/${label}.png` });
  assert.equal(report.capture.state, 'complete');
  assert.ok(report.samples.length >= 50);
  assert.ok(report.samples.every(sample => sample.dpr === 2.63));
  assert.deepEqual(errors, []);
  const average = key => report.samples.reduce((sum, row) => sum + row[key], 0) / report.samples.length;
  console.log(JSON.stringify({ label, samples: report.samples.length,
    fps: average('fps'), browserRaf: average('browserRafFps'), gpu:report.metadata.gpuRenderer, cpuMs: average('cpuMean'), gpuMs: average('gpuMean'),
    draws: average('calls'), frameP95: average('frameP95'), cpuMax: Math.max(...report.samples.map(row=>row.cpuMax)),
    buffer: report.samples[0].drawingBuffer, wakeLock: report.wakeLock.state, errors }, null, 2));
  const downloadEvent = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Save report', exact: true }).click();
  await (await downloadEvent).saveAs(`${output}/${label}-download.json`);
  await page.keyboard.press('r');
  await page.waitForFunction(() => document.querySelector('#wakeStatus').hidden);
  await page.setViewportSize({ width: 412, height: 914 });
  await page.getByText('Performance · local measurements', { exact: true }).click();
  await page.screenshot({ path: `${output}/${label}-portrait.png` });
  await page.goto(url.replace('?perf=1',''));
  await page.waitForFunction(() => !document.querySelector('#begin').disabled);
  assert.equal(await page.locator('#performance').count(), 0);
  const dimensions = await page.locator('#app canvas').evaluate(canvas => ({
    buffer: [canvas.width, canvas.height], css: [canvas.clientWidth,canvas.clientHeight], dpr: devicePixelRatio,
  }));
  assert.ok(Math.abs(dimensions.buffer[0] - dimensions.css[0]*dimensions.dpr) < 1);
  console.log('Verified JSON download, wake-lock release on reset, portrait layout, and native resolution without diagnostics.');
} finally {
  await browser.close();
}
