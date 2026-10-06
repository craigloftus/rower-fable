"""Smooth reconstruction ridges locally before skinning, retaining source anatomy."""
from pathlib import Path
import bpy,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'validation/characters/ada'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.wm.ply_import(filepath=str(OUT/'faceted-surface.ply'),forward_axis='Y',up_axis='Z')
o=bpy.context.object;before=[v.co.copy() for v in o.data.vertices]
g=o.vertex_groups.new(name='Inferred_shirt_ridges')
def smooth(a,b,x):
 t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
for v in o.data.vertices:
 x,y,z=v.co
 weight=(1-smooth(.055,.105,abs(x)))*smooth(-.015,.04,y)*(1-smooth(.22,.275,y))
 g.add([v.index],weight,'REPLACE')
m=o.modifiers.new('Reduce reconstruction cloth ridges','SMOOTH');m.factor=.65;m.iterations=22;m.vertex_group=g.name
bpy.ops.object.modifier_apply(modifier=m.name)
maxmove=max((v.co-before[v.index]).length for v in o.data.vertices)
bpy.ops.wm.ply_export(filepath=str(OUT/'refined-body.ply'),export_selected_objects=True,forward_axis='Y',up_axis='Z')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/characters/candidates/ada/body-topology.blend'))
(OUT/'body-refinement.json').write_text(json.dumps({'maximumSourceDisplacement':maxmove,'method':'Local cloth surface smoothing before rigging','uniformRigPlacementRequired':True},indent=2)+'\n')
