"""Background review renders and mesh inventory for a Sol candidate."""
import bpy, json, sys, math
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
args=sys.argv[sys.argv.index('--')+1:]
path=ROOT/args[0]; out=ROOT/args[1]; out.mkdir(parents=True,exist_ok=True)
if path.suffix=='.blend':
    bpy.ops.wm.open_mainfile(filepath=str(path))
else:
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(path))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.hide_render]
for arm in [o for o in bpy.context.scene.objects if o.type=='ARMATURE']:
    arm.data.pose_position='REST' if '--rest' in args else 'POSE'
bpy.context.view_layer.update()
points=[o.matrix_world@v.co for o in objects for v in o.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.vertices]
if '--head' in args:points=[p for p in points if p.z>.33]
if '--hand' in args:points=[p for p in points if p.x>.185 and p.z<.005 and p.z>-.14]
low=Vector([min(p[i] for p in points) for i in range(3)])
high=Vector([max(p[i] for p in points) for i in range(3)])
target=(low+high)/2; height=high.z-low.z
report={'source':str(path.relative_to(ROOT)), 'bounds':[list(low),list(high)], 'objects':[]}
for o in objects:
    o.data.calc_loop_triangles()
    report['objects'].append({'name':o.name,'vertices':len(o.data.vertices),'triangles':len(o.data.loop_triangles),
        'materials':[m.name for m in o.data.materials]})
(out/'inventory.json').write_text(json.dumps(report,indent=2)+'\n')
scene=bpy.context.scene; scene.render.engine='CYCLES'; scene.cycles.samples=16
scene.render.resolution_x=650; scene.render.resolution_y=900; scene.render.resolution_percentage=100
scene.view_settings.view_transform='Standard'
scene.world.use_nodes=True
bg=scene.world.node_tree.nodes['Background']; bg.inputs['Color'].default_value=(.7,.69,.66,1);bg.inputs['Strength'].default_value=.7
for o in list(scene.objects):
    if o.type in ('LIGHT','CAMERA'):bpy.data.objects.remove(o,do_unlink=True)
for loc,power in [((3,-4,5),350),((-3,2,3),180)]:
    data=bpy.data.lights.new('Review softbox','AREA');data.energy=power;data.size=4
    o=bpy.data.objects.new('Review softbox',data);scene.collection.objects.link(o);o.location=target+Vector(loc)
    o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('Review');camera=bpy.data.objects.new('Review',data);scene.collection.objects.link(camera)
scene.camera=camera;data.type='ORTHO';data.ortho_scale=height*1.12
clay=bpy.data.materials.new('Neutral clay');clay.diffuse_color=(.47,.43,.37,1);clay.use_nodes=True
clay.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=clay.diffuse_color
offset=float(args[args.index('--angle')+1]) if '--angle' in args else 0
for mode in ('colour','clay'):
    if mode=='clay':
        for obj in objects:
            obj.data.materials.clear();obj.data.materials.append(clay)
            for face in obj.data.polygons:face.material_index=0
    for name,angle in [('front',0),('profile',90),('rear',180),('three-quarter',35),('reference-angle',-35)]:
        a=math.radians(angle+offset)
        width=abs(math.cos(a))*(high.x-low.x)+abs(math.sin(a))*(high.y-low.y)
        data.ortho_scale=max(height,width/(650/900))*1.12
        camera.location=target+Vector((3*math.sin(a),-3*math.cos(a),.015))
        camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(out/f'{mode}-{name}.png');bpy.ops.render.render(write_still=True)
