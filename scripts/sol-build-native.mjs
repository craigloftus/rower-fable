// Candidate only. A failed acceptance check must stop the build.
import {execFileSync} from 'node:child_process';
const node=file=>execFileSync(process.execPath,[`scripts/${file}`],{stdio:'inherit'});
const blender=file=>execFileSync('blender',['--background','--factory-startup','--python-exit-code','1','--python',`scripts/${file}`],{stdio:'inherit'});
node('sol-sample-native.mjs');
blender('sol-bind-native.py');
node('sol-fit-seating.mjs');
blender('sol-bind-native.py');
node('sol-validate-native.mjs');
blender('sol-check-parity.py');
blender('sol-validate-body.py');
node('sol-validate-grip.mjs');
