// Rebuild Ada's local sculpt from the retained original-image reconstructions.
import {execFileSync} from 'node:child_process';
import {homedir} from 'node:os';
const python=`${homedir()}/.local/share/rower-tools/TripoSR/.venv/bin/python`;
const geometry=(file,...args)=>execFileSync(python,[`scripts/${file}`,...args],{stdio:'inherit'});
const blender=(file,...args)=>execFileSync('blender',['-b','--factory-startup','--python-exit-code','1','--python',`scripts/${file}`,...(args.length?['--',...args]:[])],{stdio:'inherit'});
// Retained compact inputs make this independent of inference caches.
blender('ada-refine-body.py');
geometry('ada-refine-hands.py');
geometry('ada-refine-head.py');
blender('ada-retopologize-head.py');
geometry('ada-assemble.py');
geometry('ada-colour-surface.py');
blender('ada-save-sculpt.py');
