import { test } from 'node:test';
import assert from 'node:assert/strict';
import { loadPrefs, savePrefs } from '../src/prefs.js';

let stored=null;
globalThis.localStorage={getItem:()=>stored,setItem:(_key,value)=>{stored=value;}};
test('old workout preferences survive adding character selection',()=>{
  stored=JSON.stringify({v:2,mode:'time',targets:{distance:2000,time:1200},repeats:4,rest:120,week:6,session:2});
  const cfg=loadPrefs(8);
  assert.equal(cfg.character,'june');assert.equal(cfg.targets.time,1200);
  cfg.character='ada';savePrefs(cfg);
  assert.deepEqual(loadPrefs(8),cfg);
});
test('unknown characters and malformed storage use the default',()=>{
  stored=JSON.stringify({character:'mira'});assert.equal(loadPrefs(8).character,'june');
  stored='{broken';assert.equal(loadPrefs(8).character,'june');
});
test('unavailable storage does not prevent a workout',()=>{
  const original=globalThis.localStorage;
  globalThis.localStorage={getItem:()=>{throw Error('blocked');},setItem:()=>{throw Error('quota');}};
  assert.equal(loadPrefs(8).character,'june');assert.doesNotThrow(()=>savePrefs(loadPrefs(8)));
  globalThis.localStorage=original;
});
