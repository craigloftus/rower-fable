// Candidate only. A failed acceptance check must stop the build.
import {execFileSync} from 'node:child_process';
const node=file=>execFileSync(process.execPath,[`scripts/${file}`],{stdio:'inherit'});
const blender=file=>execFileSync('blender',['--background','--factory-startup','--python-exit-code','1','--python',`scripts/${file}`],{stdio:'inherit'});
node('kai-sample-native.mjs');
blender('kai-bind-native.py');
node('kai-fit-seating.mjs');
blender('kai-bind-native.py');
node('kai-validate-native.mjs');
blender('kai-check-parity.py');
blender('kai-validate-body.py');
node('kai-validate-grip.mjs');
