"""Measure actual shoe geometry against the fixed foot stretcher."""
from pathlib import Path
import json
import bpy
from mathutils import Matrix,Vector

ROOT=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'art/characters/reference/june-final-rig.blend'))
obj=bpy.data.objects['june']
C=Matrix(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)))
normal=Vector((.14,.10,0)).normalized();centre=Vector((-.551,.245,0))
reference=None;maximum_drift=0;report=[]
for frame in [1,31,61,91,121,151,181,211,241]:
    bpy.context.scene.frame_set(frame)
    evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
    ids=sorted({i for poly in mesh.polygons if 'Shoe soles' in mesh.materials[poly.material_index].name for i in poly.vertices})
    points=[C.inverted()@mesh.vertices[i].co for i in ids]
    if reference is None:reference=points
    maximum_drift=max(maximum_drift,max((p-q).length for p,q in zip(points,reference)))
    for side in [-1,1]:
        sole=[p for p in points if p.z*side>0]
        gap=min((p-centre).dot(normal)-.0125 for p in sole)
        assert 0<gap<.002,f'Sole must meet the stretcher without penetration: {side}, {gap}'
        assert max(abs(p.z) for p in sole)<.18,'The sole overhangs the stretcher'
        if frame==1:report.append({'side':side,'minimumSoleClearance':gap,'maximumLateralExtent':max(abs(p.z) for p in sole)})
    evaluated.to_mesh_clear()
assert maximum_drift<1e-5,f'Sole geometry moves during the stroke: {maximum_drift}'
result={'poses':9,'maximumSoleDrift':maximum_drift,'feet':report}
(ROOT/'validation/reconstruction/june-final/fit-report.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
