import { buildChunk } from './course.js';
import { packChunk, chunkTransfers } from './course-chunks.js';

self.onmessage = ({ data: index }) => {
  const parts = packChunk(buildChunk(index));
  self.postMessage({ index, parts }, chunkTransfers(parts));
};
