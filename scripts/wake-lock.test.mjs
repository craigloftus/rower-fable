import test from 'node:test';
import assert from 'node:assert/strict';
import { createScreenWakeLock } from '../src/wake-lock.js';

function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
function lock() {
  const result = new EventTarget();
  result.released = false;
  result.release = async () => {
    result.released = true;
    result.dispatchEvent(new Event('release'));
  };
  return result;
}
function fixture() {
  const document = new EventTarget();
  document.visibilityState = 'visible';
  const window = new EventTarget();
  window.isSecureContext = true;
  const requests = [];
  const navigator = { wakeLock: { request(type) {
    assert.equal(type, 'screen');
    const result = deferred();
    requests.push(result);
    return result.promise;
  } } };
  const controller = createScreenWakeLock({ document, window, navigator });
  const visibility = (value) => {
    document.visibilityState = value;
    document.dispatchEvent(new Event('visibilitychange'));
  };
  return { controller, requests, document, window, navigator, visibility };
}
const flush = () => new Promise((resolve) => setImmediate(resolve));

test('requests immediately at Begin and stays held without touch/BLE activity through rest', async () => {
  const { controller, requests } = fixture();
  const ready = controller.start();
  assert.equal(requests.length, 1);
  const held = lock();
  requests[0].resolve(held);
  await ready;
  assert.equal(controller.status.state, 'active');
  await flush();
  assert.equal(controller.status.held, true);
  controller.stop();
  assert.equal(held.released, true);
  assert.equal(controller.status.state, 'idle');
});

test('coalesces requests and releases an acquisition that completes after session end', async () => {
  const { controller, requests } = fixture();
  const ready = controller.start();
  void controller.retry();
  assert.equal(requests.length, 1);
  controller.stop();
  const old = lock();
  requests[0].resolve(old);
  await ready;
  assert.equal(old.released, true);
  assert.equal(controller.status.held, false);
  assert.equal(controller.status.state, 'idle');
});

test('old request completion cannot replace a new session lock', async () => {
  const { controller, requests } = fixture();
  const first = controller.start();
  controller.stop();
  const second = controller.start();
  const current = lock();
  requests[1].resolve(current);
  await second;
  const stale = lock();
  requests[0].resolve(stale);
  await first;
  assert.equal(stale.released, true);
  assert.equal(current.released, false);
  assert.equal(controller.status.held, true);
});

test('visibility transitions release and reacquire, including pending acquisition races', async () => {
  const { controller, requests, visibility } = fixture();
  const first = controller.start();
  visibility('hidden');
  assert.equal(controller.status.state, 'suspended');
  visibility('visible');
  const current = lock();
  requests[1].resolve(current);
  await flush();
  const stale = lock();
  requests[0].resolve(stale);
  await first;
  assert.equal(stale.released, true);
  assert.equal(controller.status.held, true);
  visibility('hidden');
  assert.equal(current.released, true);
  visibility('visible');
  assert.equal(requests.length, 3);
});

test('delayed release from an old sentinel cannot clear a newly acquired lock', async () => {
  const { controller, requests, visibility } = fixture();
  const old = lock();
  old.release = async () => {};
  const ready = controller.start();
  requests[0].resolve(old);
  await ready;
  visibility('hidden');
  visibility('visible');
  requests[1].resolve(lock());
  await flush();
  old.dispatchEvent(new Event('release'));
  assert.equal(controller.status.held, true);
  assert.equal(requests.length, 2);
});

test('recovers once from unexpected release, then exposes failure without retry loop', async () => {
  const { controller, requests } = fixture();
  const ready = controller.start();
  const first = lock();
  requests[0].resolve(first);
  await ready;
  await first.release();
  assert.equal(requests.length, 2);
  const second = lock();
  requests[1].resolve(second);
  await flush();
  await second.release();
  assert.equal(requests.length, 2);
  assert.equal(controller.status.state, 'error');
  assert.equal(controller.status.held, false);
  const retry = controller.retry();
  requests[2].resolve(lock());
  await retry;
  assert.equal(controller.status.held, true);
});

test('a rejected request reports the reason and a user retry can recover', async () => {
  const { controller, requests } = fixture();
  const ready = controller.start();
  requests[0].reject(new DOMException('Battery saver enabled', 'NotAllowedError'));
  await ready;
  assert.equal(controller.status.state, 'error');
  assert.match(controller.status.error, /NotAllowedError: Battery saver enabled/);
  const retry = controller.retry();
  requests[1].resolve(lock());
  await retry;
  assert.equal(controller.status.state, 'active');
});

test('insecure origins and missing API are visible failures', async () => {
  const insecure = fixture();
  insecure.window.isSecureContext = false;
  await insecure.controller.start();
  assert.equal(insecure.controller.status.state, 'insecure');
  assert.equal(insecure.requests.length, 0);
  const unsupported = fixture();
  delete unsupported.navigator.wakeLock;
  await unsupported.controller.start();
  assert.equal(unsupported.controller.status.state, 'unsupported');
  assert.equal(unsupported.requests.length, 0);
});

test('page cache navigation releases and restores active sessions only', async () => {
  const { controller, requests, window } = fixture();
  const ready = controller.start();
  const first = lock();
  requests[0].resolve(first);
  await ready;
  window.dispatchEvent(new Event('pagehide'));
  assert.equal(first.released, true);
  window.dispatchEvent(new Event('pageshow'));
  assert.equal(requests.length, 2);
  requests[1].resolve(lock());
  await flush();
  assert.equal(controller.status.held, true);
  controller.stop();
  window.dispatchEvent(new Event('pageshow'));
  assert.equal(requests.length, 2);
});

test('a session started while hidden acquires only when visible', async () => {
  const { controller, requests, visibility } = fixture();
  visibility('hidden');
  await controller.start();
  assert.equal(requests.length, 0);
  assert.equal(controller.status.state, 'suspended');
  visibility('visible');
  assert.equal(requests.length, 1);
  requests[0].resolve(lock());
  await flush();
  assert.equal(controller.status.held, true);
});

test('an already released result is never reported as keeping the screen awake', async () => {
  const { controller, requests } = fixture();
  const ready = controller.start();
  const result = lock();
  result.released = true;
  requests[0].resolve(result);
  await ready;
  assert.equal(controller.status.state, 'error');
  assert.equal(controller.status.held, false);
});

test('a stale rejection cannot overwrite the next session state', async () => {
  const { controller, requests } = fixture();
  const first = controller.start();
  controller.stop();
  const second = controller.start();
  requests[1].resolve(lock());
  await second;
  requests[0].reject(new DOMException('Old document was hidden', 'NotAllowedError'));
  await first;
  assert.equal(controller.status.state, 'active');
  assert.equal(controller.status.error, null);
});
