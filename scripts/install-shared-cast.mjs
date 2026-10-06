import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {copyFileSync,mkdirSync,readFileSync,writeFileSync} from 'node:fs';
import {CHARACTERS} from '../src/characters.js';
import {compressCharacter} from './compress-character.mjs';
import {validateNativeJune} from './validate-native-june.mjs';

const source='art/characters/shared-cast';
const manifest=JSON.parse(readFileSync(`${source}/manifest.json`));
assert.deepEqual(manifest.characters.map(c=>c.id).sort(),CHARACTERS.map(c=>c.id).sort());
const installed=[];
for(const character of manifest.characters) {
  const {id,file,sha256,bodyIdentityCheck,clipIdentityCheck}=character;
  assert(bodyIdentityCheck.passed&&clipIdentityCheck.passed,`${id}: shared body and clip checks must pass`);
  const raw=`${source}/${file}`;
  assert.equal(createHash('sha256').update(readFileSync(raw)).digest('hex'),sha256,`${id}: unvalidated export`);
  const output=`validation/characters/installed/${id}`;
  mkdirSync(output,{recursive:true});
  const delivery=await compressCharacter(raw,`${output}/${id}.glb`);
  await validateNativeJune(`${output}/${id}.glb`,output);
  installed.push({...character,sourceSha256:sha256,sha256:delivery.sha256,bytes:delivery.bytes});
}
// Publish the local cast only once every compressed export has passed.
for(const character of installed) {
  copyFileSync(`validation/characters/installed/${character.id}/${character.id}.glb`,`public/characters/${character.id}.glb`);
  copyFileSync(`${source}/${character.editableBlend}`,`art/characters/${character.id}.blend`);
}
writeFileSync('validation/characters/installed/manifest.json',JSON.stringify({characters:installed},null,2)+'\n');
console.log('Installed four characters using the approved shared June body and RowingCycle.');
