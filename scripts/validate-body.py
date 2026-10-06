"""Check the actual deformed arm and leg surfaces, not just rig capsules.
Run with blender --background --python scripts/validate-body.py.
"""
import bpy
import json
import math
import sys
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]

def intersects(a,b):
    # Triangle SAT, including in-plane axes for coplanar triangles.
    ea=[a[(i+1)%3]-a[i] for i in range(3)]
    eb=[b[(i+1)%3]-b[i] for i in range(3)]
    na=ea[0].cross(ea[1]);nb=eb[0].cross(eb[1])
    axes=[na,nb]+[x.cross(y) for x in ea for y in eb]+[na.cross(x) for x in ea]+[nb.cross(x) for x in eb]
    for axis in axes:
        if axis.length_squared<1e-18:continue
        axis.normalize();pa=[v.dot(axis) for v in a];pb=[v.dot(axis) for v in b]
        if max(pa)<min(pb)-1e-7 or max(pb)<min(pa)-1e-7:return False
    return True

report=[]
final_june='--final-june' in sys.argv
native_june='--native-june' in sys.argv
for ident in (['june'] if final_june or native_june else ['mira','kai','june','sol','ada']):
    asset=ROOT/'validation/reconstruction/fresh-rig/june.blend' if native_june else ROOT/'art/characters/reference/june-final-rig.blend' if final_june else ROOT/'art/characters'/(ident+'.blend')
    bpy.ops.wm.open_mainfile(filepath=str(asset))
    obj=bpy.data.objects[ident]
    volume_skin=obj.get('skinning')=='dualQuaternion'
    names={g.index:g.name.removeprefix('shorts_') for g in obj.vertex_groups}
    labels=[]
    chest_labels=[]
    if native_june:
        layout=json.loads((ROOT/'validation/reconstruction/fresh-rig/layout.json').read_text())
        C=Matrix(((1,0,0),(0,0,-1),(0,1,0)))
        B=Matrix(((0,0,-1),(0,1,0),(1,0,0)))
    for v in obj.data.vertices:
        arm=sum(g.weight for g in v.groups if names[g.group].startswith(('upperArm','forearm','hand','mitt') if volume_skin else ('upperArm','forearm')))
        leg=sum(g.weight for g in v.groups if names[g.group].startswith(('thigh','shin')))
        if native_june:
            source=B.inverted()@((C.inverted()@v.co-Vector(layout['hipRest']))/layout['scale'])+Vector(layout['hipSource'])
            # Regions come from the sculpt, independently of weights. A bad
            # weight assignment must not make an intersecting limb disappear
            # from the test. Exclude only the connected shoulder/hip seams.
            arm_edge=.085+max(0,.170-source.y)*.36
            labels.append('arm' if abs(source.x)>arm_edge and -.11<source.y<.20 else 'leg' if abs(source.x)<.135 and -.44<source.y<-.065 else '')
            chest_labels.append(abs(source.x)<.077 and .075<source.y<.31)
        else:
            labels.append('arm' if arm>.65 else 'leg' if leg>.65 else '')
            chest_labels.append(False)
    collisions=[];chest_collisions=[];candidates=0
    for sample in range(161):
        frame=1+sample*1.5
        bpy.context.scene.frame_set(math.floor(frame),subframe=frame%1)
        evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh=evaluated.to_mesh();mesh.calc_loop_triangles()
        points=[v.co.copy() for v in mesh.vertices]
        arms=[];legs=[];chest=[]
        for tri in mesh.loop_triangles:
            ids=list(tri.vertices)
            if all(labels[i]=='arm' for i in ids):arms.append(ids)
            elif all(labels[i]=='leg' for i in ids):legs.append(ids)
            if all(chest_labels[i] for i in ids):chest.append(ids)
        at=BVHTree.FromPolygons(points,arms,all_triangles=True)
        lt=BVHTree.FromPolygons(points,legs,all_triangles=True)
        for ai,li in at.overlap(lt):
            candidates+=1
            if intersects([points[i] for i in arms[ai]],[points[i] for i in legs[li]]):
                collisions.append({'frame':frame,'arm':ai,'leg':li})
        if chest:
            ct=BVHTree.FromPolygons(points,chest,all_triangles=True)
            for ai,ci in at.overlap(ct):
                if intersects([points[i] for i in arms[ai]],[points[i] for i in chest[ci]]):
                    chest_collisions.append({'frame':frame,'arm':ai,'chest':ci})
        evaluated.to_mesh_clear()
    report.append({'id':ident,'poses':161,'armLegTriangleIntersections':len(collisions),'armChestTriangleIntersections':len(chest_collisions),
        'candidates':candidates,'firstCollisions':collisions[:5],'firstChestCollisions':chest_collisions[:5]})
    print('BODY_CHECK',report[-1],flush=True)
report_path=ROOT/('validation/reconstruction/fresh-rig/body-report.json' if native_june else 'validation/reconstruction/june-final/body-report.json' if final_june else 'validation/body-report.json')
report_path.write_text(json.dumps(report,indent=2)+'\n')
assert all(r['armLegTriangleIntersections']==0 for r in report), 'Deformed arm/leg surfaces intersect; see body-report.json'
assert all(r['armChestTriangleIntersections']==0 for r in report), 'Deformed arms/hands intersect the chest; see body-report.json'
