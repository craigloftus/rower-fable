import {execFileSync} from 'node:child_process';

execFileSync(process.execPath,['scripts/shared-cast-validate.mjs'],{stdio:'inherit'});
execFileSync('blender',[
  '--background','--factory-startup','--python-exit-code','1',
  '--python','scripts/validate-body.py','--','--shared-cast',
],{stdio:'inherit'});
