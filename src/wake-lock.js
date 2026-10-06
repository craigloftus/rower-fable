// Keep the screen awake for the whole session, including rests. Browser/OS
// denial is a real failure: report it rather than simulating a successful lock.
export function createScreenWakeLock({
  navigator: nav = globalThis.navigator,
  document: doc = globalThis.document,
  window: win = globalThis.window,
  onChange = () => {},
} = {}) {
  let wanted = false;
  let sentinel = null;
  let pending = null;
  let generation = 0;
  let recoveryUsed = false;
  let pageHidden = false;
  let state = 'idle';
  let error = null;
  let attempts = 0;
  let releases = 0;
  const events = [];
  const visible = () => !pageHidden && doc.visibilityState === 'visible';
  const snapshot = () => ({ state, wanted, held: !!sentinel && !sentinel.released,
    secure: win.isSecureContext, supported: !!nav.wakeLock, attempts, releases, error,
    events: events.slice() });

  function report(next, detail = null) {
    state = next;
    error = detail;
    events.push({ at: Date.now(), state, error });
    if (events.length > 30) events.shift();
    onChange(snapshot());
  }

  async function release(lock) {
    try { await lock.release(); }
    catch (err) { report(state, `${err.name}: ${err.message}`); }
  }

  function suspend() {
    generation++;
    pending = null;
    const old = sentinel;
    sentinel = null;
    if (old) void release(old);
    report(wanted ? 'suspended' : 'idle');
  }

  async function acquire() {
    if (!wanted || !visible() || sentinel) return;
    if (pending) return pending.promise;
    if (!win.isSecureContext) {
      report('insecure', 'Open the HTTPS version to keep the screen awake.');
      return;
    }
    if (!nav.wakeLock) {
      report('unsupported', 'This browser cannot keep the screen awake. Use a current browser.');
      return;
    }
    const request = { generation, promise: null };
    pending = request;
    attempts++;
    report('requesting');
    request.promise = (async () => {
      try {
        const lock = await nav.wakeLock.request('screen');
        if (!wanted || !visible() || request.generation !== generation) {
          await release(lock);
          return;
        }
        if (lock.released) {
          report('error', 'The device released the screen lock. Check power-saving settings, then retry.');
          return;
        }
        sentinel = lock;
        lock.addEventListener('release', () => {
          releases++;
          if (sentinel !== lock) return;
          sentinel = null;
          if (!wanted || !visible()) {
            report(wanted ? 'suspended' : 'idle');
            return;
          }
          report('error', 'Screen may sleep. Check power-saving settings, then retry.');
          // One automatic recovery per start/return/retry; never spin against an
          // OS that keeps revoking the lock (for example in battery saver).
          if (!recoveryUsed) {
            recoveryUsed = true;
            void acquire();
          }
        }, { once: true });
        report('active');
      } catch (err) {
        if (request.generation === generation && wanted && visible()) {
          report('error', `${err.name}: ${err.message}`);
        }
      } finally {
        if (pending === request) pending = null;
      }
    })();
    return request.promise;
  }

  function retry() {
    recoveryUsed = false;
    return acquire();
  }
  function start() {
    wanted = true;
    if (!visible()) { report('suspended'); return; }
    return retry();
  }
  function stop() {
    wanted = false;
    suspend();
  }
  function onVisibility() {
    if (!visible()) suspend();
    else if (wanted) void retry();
  }
  function onPageHide() { pageHidden = true; suspend(); }
  function onPageShow() { pageHidden = false; onVisibility(); }
  doc.addEventListener('visibilitychange', onVisibility);
  win.addEventListener('pagehide', onPageHide);
  win.addEventListener('pageshow', onPageShow);

  return { start, stop, retry, get status() { return snapshot(); } };
}
