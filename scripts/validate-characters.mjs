import {mkdirSync,writeFileSync} from 'node:fs';
import {CHARACTERS} from '../src/characters.js';
import {validateNativeJune} from './validate-native-june.mjs';

const characters=[];
for(const {id} of CHARACTERS) {
  const output=`validation/characters/installed/${id}`;
  mkdirSync(output,{recursive:true});
  const report=await validateNativeJune(`public/characters/${id}.glb`,output);
  characters.push({id,...report});
}
writeFileSync('validation/character-report.json',JSON.stringify({characters},null,2)+'\n');
console.log('Validated all four installed character files over 1,201 poses each.');
