"""Headless views of the shared rig in rest and the exact approved cycle."""
from pathlib import Path
import bpy,sys
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1];args=sys.argv[sys.argv.index('--')+1:];character=args[0]
OUT=ROOT/'validation/characters/shared-cast'/character/'review';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/f'art/characters/shared-cast/{character}.blend'))
scene=bpy.context.scene;arm=bpy.data.objects['june_rig'];C=Matrix(((1,0,0),(0,0,-1),(0,1,0)))
scene.world.use_nodes=True;bg=scene.world.node_tree.nodes.get('Background');bg.inputs['Color'].default_value=(.70,.69,.65,1);bg.inputs['Strength'].default_value=.8
for o in list(scene.objects):
 if o.type in ('LIGHT','CAMERA'):bpy.data.objects.remove(o,do_unlink=True)
for loc,power in [((-3,4,5),450),((2,-3,3),250)]:
 d=bpy.data.lights.new('Review light','AREA');d.energy=power;d.size=4;o=bpy.data.objects.new('Review light',d);scene.collection.objects.link(o);o.location=C@Vector(loc);o.rotation_euler=(C@Vector((0,.8,0))-o.location).to_track_quat('-Z','Y').to_euler()
d=bpy.data.cameras.new('Review');cam=bpy.data.objects.new('Review',d);scene.collection.objects.link(cam);scene.camera=cam;d.type='ORTHO'
scene.render.engine='CYCLES';scene.cycles.samples=16;scene.render.resolution_x=650;scene.render.resolution_y=850;scene.render.resolution_percentage=100;scene.view_settings.view_transform='Standard'
def render(label,focus,offset,scale):
 focus=Vector(focus);cam.location=C@(focus+Vector(offset));cam.rotation_euler=(C@focus-cam.location).to_track_quat('-Z','Y').to_euler();d.ortho_scale=scale;scene.render.filepath=str(OUT/f'{label}.png');bpy.ops.render.render(write_still=True)
arm.data.pose_position='REST';bpy.context.view_layer.update()
for view,offset in [('front',(-3,0,0)),('profile',(0,0,3)),('reference-angle',(-3,0,-2)),('rear',(3,0,0))]:
 render('rest-'+view,(0,.37,0),offset,1.95)
 render('head-'+view,(-.08,1.09,0),offset,.43)
if '--quick' not in args:
 arm.data.pose_position='POSE'
 for phase in [0,1,1.4,1.7]:
  scene.frame_set(1+round(phase*120));hip=C.inverted()@arm.pose.bones['pelvis'].head
  for view,offset in [('front',(-3,0,.08)),('side',(0,0,3)),('rear',(3,0,.08)),('reference-angle',(-3,0,-2))]:render(f'{phase:.2f}-{view}',(hip.x,.78,0),offset,1.55)
  render(f'{phase:.2f}-hand',C.inverted()@arm.pose.bones['gripL'].head,(-.1,.15,.5),.33)
  render(f'{phase:.2f}-waist',(hip.x,.5,0),(0,.04,3),.65)
 arm.data.pose_position='REST'
 clay=bpy.data.materials.new('Neutral clay');clay.use_nodes=True;clay.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.47,.43,.37,1)
 for obj in scene.objects:
  if obj.type=='MESH':
   obj.data.materials.clear();obj.data.materials.append(clay)
   for face in obj.data.polygons:face.material_index=0
 for view,offset in [('front',(-3,0,0)),('profile',(0,0,3)),('reference-angle',(-3,0,-2))]:
  render('clay-head-'+view,(-.08,1.09,0),offset,.43)
  render('clay-rest-'+view,(0,.37,0),offset,1.95)
