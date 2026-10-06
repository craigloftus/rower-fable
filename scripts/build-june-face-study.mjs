// Build and validate a face candidate in an isolated copy of the native pipeline.
import {cpSync,copyFileSync,mkdirSync,symlinkSync,existsSync,writeFileSync} from 'node:fs';
import {resolve,join} from 'node:path';
import {spawnSync} from 'node:child_process';

const candidate=resolve(process.argv[2]);
const build=join(candidate,'native-build');
mkdirSync(build,{recursive:true});
cpSync('scripts',join(build,'scripts'),{recursive:true});
cpSync('src',join(build,'src'),{recursive:true});
copyFileSync('package.json',join(build,'package.json'));
if(!existsSync(join(build,'node_modules')))symlinkSync(resolve('node_modules'),join(build,'node_modules'),'dir');
const sculpt=join(build,'validation/reconstruction/june-final');
mkdirSync(sculpt,{recursive:true});
copyFileSync(join(candidate,'mesh.glb'),join(sculpt,'mesh.glb'));
copyFileSync('validation/reconstruction/june-final/faceted-surface.ply',join(sculpt,'faceted-surface.ply'));
const result=spawnSync(process.execPath,['scripts/build-final-june.mjs'],{
  cwd:build,stdio:'inherit',env:{...process.env,PATH:`/opt/homebrew/bin:${process.env.PATH}`},
});
if(result.status!==0)process.exit(result.status??1);
cpSync(join(build,'validation/reconstruction/fresh-rig'),join(candidate,'rig'),{recursive:true});
writeFileSync(join(candidate,'build-source.json'),JSON.stringify({
  sculpt:'mesh.glb',pipeline:'scripts/build-final-june.mjs',
  guide:'validation/reconstruction/june-final/faceted-surface.ply',
  note:'The source guide is unchanged because this candidate only changes rigid head geometry.',
},null,2)+'\n');
