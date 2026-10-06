import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { copyFileSync, readFileSync, mkdirSync } from 'node:fs';
import { compressCharacter } from './compress-character.mjs';
import { validateNativeJune } from './validate-native-june.mjs';

const source='validation/reconstruction/fresh-rig';
const hashes=JSON.parse(readFileSync(`${source}/validated-build.json`));
for(const file of ['june.glb','june.blend']) {
  const hash=createHash('sha256').update(readFileSync(`${source}/${file}`)).digest('hex');
  assert.equal(hash,hashes[file],'Run june:build to validate the current export before installing it.');
}
const output='validation/characters/installed/june';
mkdirSync(output,{recursive:true});
await compressCharacter(`${source}/june.glb`,`${output}/june.glb`);
await validateNativeJune(`${output}/june.glb`,output);
copyFileSync(`${output}/june.glb`,'public/characters/june.glb');
copyFileSync(`${source}/june.blend`,'art/characters/june.blend');
console.log('Installed the losslessly compressed June mesh and editable rig; original illustration portrait retained.');
