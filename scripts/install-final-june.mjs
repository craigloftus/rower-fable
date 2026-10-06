import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { copyFileSync, readFileSync } from 'node:fs';

const source='validation/reconstruction/fresh-rig';
const hashes=JSON.parse(readFileSync(`${source}/validated-build.json`));
for(const file of ['june.glb','june.blend','june.png']) {
  const hash=createHash('sha256').update(readFileSync(`${source}/${file}`)).digest('hex');
  assert.equal(hash,hashes[file],'Run june:build to validate the current export before installing it.');
}
for(const extension of ['glb','png'])copyFileSync(`${source}/june.${extension}`,`public/characters/june.${extension}`);
copyFileSync(`${source}/june.blend`,'art/characters/june.blend');
console.log('Installed the validated June mesh, portrait and editable rig.');
