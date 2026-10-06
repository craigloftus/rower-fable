// Candidate only. A failed acceptance check must stop the build.
import {execFileSync} from 'node:child_process';
const node=file=>execFileSync(process.execPath,[`scripts/${file}`],{stdio:'inherit'});
const blender=file=>execFileSync('blender',['--background','--factory-startup','--python-exit-code','1','--python',`scripts/${file}`],{stdio:'inherit'});
node('ada-sample-native.mjs');
blender('ada-bind-native.py');
node('ada-fit-seating.mjs');
blender('ada-bind-native.py');
node('ada-validate-native.mjs');
blender('ada-check-parity.py');
blender('ada-validate-body.py');
node('ada-validate-grip.mjs');
