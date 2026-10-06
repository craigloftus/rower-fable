import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';

function run(command,args) {
  const result=spawnSync(command,args,{stdio:'inherit'});
  if(result.status!==0)process.exit(result.status??1);
}
const blender=(name,...args)=>run('blender',['--background','--factory-startup','--python-exit-code','1','--python',`scripts/${name}.py`,...args]);
const node=name=>run('node',[`scripts/${name}.mjs`]);

// The approved sculpt is an input, never regenerated or reshaped by rigging.
node('sample-june-native');
blender('bind-june-native');
node('fit-june-seating');
blender('bind-june-native');
node('validate-native-june');
node('validate-june-grip');
blender('check-native-june');
blender('validate-body','--','--native-june');
blender('render-final-june');
const root='validation/reconstruction/fresh-rig';
const hashes=Object.fromEntries(['june.glb','june.blend','june.png'].map(file=>
  [file,createHash('sha256').update(readFileSync(`${root}/${file}`)).digest('hex')]));
writeFileSync(`${root}/validated-build.json`,JSON.stringify(hashes,null,2)+'\n');
