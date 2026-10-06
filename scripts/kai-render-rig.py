"""Repeatable front/profile and grip renders from the evaluated Blender rig."""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'validation/characters/kai'
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
tag=args[0] if args else 'review'
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'art/characters/candidates/kai/kai.blend'))
scene=bpy.context.scene;arm=bpy.data.objects['kai_rig']
C=Matrix(((1,0,0),(0,0,-1),(0,1,0)))
scene.world.use_nodes=True
bg=scene.world.node_tree.nodes.get('Background');bg.inputs['Color'].default_value=(.70,.69,.65,1);bg.inputs['Strength'].default_value=.8
for loc,power in [((-3,4,5),450),((2,-3,3),250)]:
 d=bpy.data.lights.new('Review light','AREA');d.energy=power;d.size=4
 o=bpy.data.objects.new('Review light',d);scene.collection.objects.link(o);o.location=C@Vector(loc)
 o.rotation_euler=(C@Vector((0,.8,0))-o.location).to_track_quat('-Z','Y').to_euler()
d=bpy.data.cameras.new('Review');cam=bpy.data.objects.new('Review',d);scene.collection.objects.link(cam);scene.camera=cam;d.type='ORTHO'
mat=bpy.data.materials.new('Handle');mat.diffuse_color=(.25,.17,.08,1)
mat.use_nodes=True;mat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.25,.17,.08,1)
handles=[]
for k in ('L','R'):
 bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=.020,depth=.30)
 o=bpy.context.object;o.data.materials.append(mat);handles.append(o)
scene.render.engine='CYCLES';scene.cycles.samples=16
scene.render.resolution_x=550;scene.render.resolution_y=650;scene.render.resolution_percentage=100
scene.view_settings.view_transform='Standard'
folder=OUT/tag;folder.mkdir(exist_ok=True)
for phase in [0,.5,1,1.4,1.7] if len(args)<2 else [float(args[1])]:
 scene.frame_set(1+round(phase*120))
 for k,o in zip(('L','R'),handles):
  b=arm.pose.bones['grip'+k];o.matrix_world=b.matrix.copy();o.location+=b.matrix.to_3x3()@Vector((0,0,.05))
 hip=C.inverted()@arm.pose.bones['pelvis'].head
 for label,offset,scale in [('front',(-3,0,.08),1.30),('side',(0,0,3),1.30),('rear',(3,0,.08),1.30),('waist',(0,.04,3),.65),('feet',(-.5,.1,.6),.60),('grip',(-.10,.15,.5),.33),('thumb',(.35,-.1,.20),.28)]:
  focus=Vector((hip.x,.86,0)) if label in ('front','side','rear') else C.inverted()@arm.pose.bones['gripL'].head
  if label=='waist':focus=Vector((hip.x,.50,0))
  if label=='feet':focus=C.inverted()@arm.pose.bones['footL'].head
  if label=='thumb':offset=C.inverted()@arm.pose.bones['handL'].matrix.to_3x3()@Vector(offset)
  cam.location=C@(focus+Vector(offset));cam.rotation_euler=(C@focus-cam.location).to_track_quat('-Z','Y').to_euler();d.ortho_scale=scale
  scene.render.filepath=str(folder/f'{phase:.2f}-{label}.png');bpy.ops.render.render(write_still=True)
