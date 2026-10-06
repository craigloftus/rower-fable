from pathlib import Path
import bpy,json
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'validation/characters/shared-cast'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'validation/reconstruction/fresh-rig/june.blend'))
layout=json.loads((ROOT/'validation/reconstruction/fresh-rig/layout.json').read_text())
C=Matrix(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)));B=Matrix(((0,0,-1,0),(0,1,0,0),(1,0,0,0),(0,0,0,1)))
placement=C@Matrix.Translation(Vector(layout['hipRest']))@Matrix.Scale(layout['scale'],4)@Matrix.Translation(-(B@Vector(layout['hipSource'])))@B
inv=placement.inverted();report={'layout':{k:layout[k] for k in ['scale','hipRest','hipSource']},'objects':[]}
for o in bpy.context.scene.objects:
 if o.type!='MESH':continue
 p=[inv@(o.matrix_world@v.co) for v in o.data.vertices]
 import numpy as np
 source=np.array(p);np.savez_compressed(OUT/'june-source-points.npz',positions=source)
 eyeids={v for f in o.data.polygons if 'Eye ivory' in o.data.materials[f.material_index].name for v in f.vertices}
 lipids={v for f in o.data.polygons if ' lip' in o.data.materials[f.material_index].name for v in f.vertices}
 report['lipBounds']=[[float(source[list(lipids),k].min()) for k in range(3)],[float(source[list(lipids),k].max()) for k in range(3)]]
 report['eyeBounds']=[[float(source[list(eyeids),k].min()) for k in range(3)],[float(source[list(eyeids),k].max()) for k in range(3)]]
 report['headBounds']=[source[source[:,1]>.345].min(axis=0).tolist(),source[source[:,1]>.345].max(axis=0).tolist()]
 from mathutils.bvhtree import BVHTree
 bvh=BVHTree.FromPolygons([v.co for v in o.data.vertices],[list(f.vertices) for f in o.data.polygons],all_triangles=True)
 report['frontRays']={}
 for y in [.08,.10,.12,.14,.16,.18,.20,.22,.24,.26,.28]:
  row={}
  for x in [0,.02,.04,.06,.08]:
   hit,normal,index,distance=bvh.ray_cast(placement@Vector((x,y,1)),(placement.to_3x3()@Vector((0,0,-1))).normalized())
   if hit is not None:row[str(x)]=float((inv@hit).z)
  report['frontRays'][str(y)]=row
 report['chestSections']={str(y):{str(x):float(source[(abs(source[:,1]-y)<.009)&(abs(abs(source[:,0])-x)<.01),2].max()) for x in [.0,.03,.055,.075] if np.any((abs(source[:,1]-y)<.009)&(abs(abs(source[:,0])-x)<.01))} for y in [.14,.17,.20,.23,.26,.28]}
 report['objects'].append({'name':o.name,'vertices':len(p),'polygons':len(o.data.polygons),'bounds':[[min(v[i] for v in p) for i in range(3)],[max(v[i] for v in p) for i in range(3)]],'materials':[{'name':m.name,'color':list(m.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value)} for m in o.data.materials],'matrix':list(map(list,o.matrix_world))})
arm=bpy.data.objects['june_rig'];report['bones']=[b.name for b in arm.data.bones];report['action']=arm.animation_data.action.name
(OUT/'june-inspection.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
