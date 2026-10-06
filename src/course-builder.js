import { unpackChunk } from './course-chunks.js';

export function createCourseBuilder() {
  const worker = new Worker(new URL('./course-worker.js', import.meta.url), { type: 'module' });
  const pending = new Map();
  let failure = null;
  worker.onmessage = ({ data }) => {
    pending.get(data.index).resolve(unpackChunk(data.parts));
    pending.delete(data.index);
  };
  worker.onerror = event => {
    failure = new Error(event.message);
    worker.terminate();
    for (const request of pending.values()) request.reject(failure);
    pending.clear();
  };
  return index => new Promise((resolve, reject) => {
    if (failure) { reject(failure); return; }
    pending.set(index, { resolve, reject });
    worker.postMessage(index);
  });
}
