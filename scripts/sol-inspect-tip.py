"""Locate the source vertices behind the visible left-hand tip in its review view."""
from pathlib import Path
import bpy,json
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'validation/characters/sol'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'art/characters/candidates/sol/sol.blend'))
scene=bpy.context.scene;scene.frame_set(1);arm=bpy.data.objects['sol_rig'];obj=bpy.data.objects['sol']
C=Matrix(((1,0,0),(0,0,-1),(0,1,0)));B=Matrix(((0,0,-1),(0,1,0),(1,0,0)))
layout=json.loads((OUT/'layout.json').read_text());focus=arm.pose.bones['gripL'].head
loc=focus+arm.pose.bones['handL'].matrix.to_3x3()@Vector((.35,-.1,.20))
rotation=(focus-loc).to_track_quat('-Z','Y').to_matrix().transposed()
eval=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());rows=[]
for i,v in enumerate(eval.data.vertices):
 q=rotation@(v.co-focus);pixel=Vector(((q.x/(.28*550/650)+.5)*550,(.5-q.y/.28)*650))
 distance=(pixel-Vector((475,289))).length
 if distance<12:
  rest=obj.data.vertices[i]
  source=B.inverted()@((C.inverted()@rest.co-Vector(layout['hipRest']))/layout['scale'])+Vector(layout['hipSource'])
  rows.append({'pixel':list(pixel),'distance':distance,'depth':q.z,'source':list(source),'weights':{obj.vertex_groups[g.group].name:g.weight for g in rest.groups}})
rows.sort(key=lambda r:r['distance']);(OUT/'tip-inspection.json').write_text(json.dumps(rows[:20],indent=2)+'\n');print(rows[:4])
