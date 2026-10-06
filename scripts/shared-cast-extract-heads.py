"""Save compact approved donor heads; later builds need no candidate bodies."""
from pathlib import Path
import bpy,bmesh,json,hashlib
ROOT=Path(__file__).resolve().parents[1];MASTER=ROOT/'art/characters/shared-cast';OUT=ROOT/'validation/characters/shared-cast'
cuts={c['id']:c['headCut'] for c in json.loads((MASTER/'cast.json').read_text())['characters'] if c['id']!='june'}
MASTER.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
provenance={}
for character in ['kai','sol','ada']:
 cut=cuts[character]
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 source=ROOT/f'art/characters/candidates/{character}/standing.glb'
 bpy.ops.import_scene.gltf(filepath=str(source))
 parts=[];eyes=[];mouth=[]
 for o in list(bpy.context.scene.objects):
  if o.type!='MESH':continue
  # GLTF imports use Blender Z up; source height is unchanged.
  if max(v.co.z for v in o.data.vertices)<cut:bpy.data.objects.remove(o,do_unlink=True);continue
  if min(v.co.z for v in o.data.vertices)<cut:
   bm=bmesh.new();bm.from_mesh(o.data)
   bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-8,plane_co=(0,0,cut),plane_no=(0,0,-1),clear_outer=True,clear_inner=False)
   bm.to_mesh(o.data);bm.free();o.data.update()
  parts.append(o)
  name=o.data.materials[0].name.split('.')[0]
  o.data.materials[0].name=f'{character} · {name}'
  if 'Eye ivory' in name:eyes.extend([list(v.co) for v in o.data.vertices])
  if name in ('Mouth','Lips'):mouth.extend([list(v.co) for v in o.data.vertices])
 bpy.ops.object.select_all(action='DESELECT')
 for o in parts:o.select_set(True)
 bpy.context.view_layer.objects.active=parts[0]
 bpy.ops.export_scene.gltf(filepath=str(MASTER/f'{character}-head.glb'),export_format='GLB',use_selection=True,export_animations=False,export_extras=True)
 provenance[character]={'source':str(source.relative_to(ROOT)),'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'headSha256':hashlib.sha256((MASTER/f'{character}-head.glb').read_bytes()).hexdigest(),'cutSourceHeight':cut,'eyeBounds':[[min(p[k] for p in eyes) for k in range(3)],[max(p[k] for p in eyes) for k in range(3)]],'lipBounds':[[min(p[k] for p in mouth) for k in range(3)],[max(p[k] for p in mouth) for k in range(3)]]}
( MASTER/'head-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
