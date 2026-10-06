import {execFileSync} from 'node:child_process';

// Reuse the approved June body/rig and retained head-only sources.
// Review before installing; this command never replaces app assets.
execFileSync('blender',[
  '--background','--factory-startup','--python-exit-code','1',
  '--python','scripts/shared-cast-build.py',
],{stdio:'inherit'});
execFileSync(process.execPath,['scripts/shared-cast-validate.mjs'],{stdio:'inherit'});
