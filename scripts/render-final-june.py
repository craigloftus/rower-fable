"""Render the character picker portrait from the actual exported rowing mesh."""
from pathlib import Path
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'validation/reconstruction/fresh-rig'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'june.blend'))
scene=bpy.context.scene;scene.frame_set(1)
arm=bpy.data.objects['june'].parent
focus=arm.pose.bones['head'].head+Vector((0,0,.15))
scene.world.use_nodes=True
world=scene.world.node_tree.nodes.get('Background')
world.inputs['Color'].default_value=(.72,.70,.63,1)
world.inputs['Strength'].default_value=.8
for location,power,size in [((-3, -4, 6),450,4),((2,2,4),250,3)]:
    data=bpy.data.lights.new('Portrait light','AREA');data.energy=power;data.shape='DISK';data.size=size
    light=bpy.data.objects.new('Portrait light',data);scene.collection.objects.link(light)
    light.location=location;light.rotation_euler=(focus-light.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('June portrait');camera=bpy.data.objects.new('June portrait',data)
scene.collection.objects.link(camera);scene.camera=camera
camera.location=focus+Vector((-.9,.40,.12))
camera.rotation_euler=(focus-camera.location).to_track_quat('-Z','Y').to_euler()
data.type='ORTHO';data.ortho_scale=.46
scene.render.engine='CYCLES';scene.cycles.samples=32
scene.render.resolution_x=512;scene.render.resolution_y=512;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='Standard'
scene.render.filepath=str(OUT/'june.png')
bpy.ops.render.render(write_still=True)
