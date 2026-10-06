"""Comparable neutral-light head views of a standing June sculpt GLB."""
import bpy
import sys
from pathlib import Path
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:]
source, output = Path(args[0]), Path(args[1])
output.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(source.resolve()))
scene = bpy.context.scene
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.72, .68, .60, 1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .6
target = Vector((0, -.008, .398))
for location, power, size in [((-.28, -.4, .64), 1.5, .20), ((.28, -.18, .45), .45, .18), ((.15, .25, .60), 1, .18)]:
    data = bpy.data.lights.new('Studio softbox', 'AREA')
    data.energy, data.size = power, size
    light = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(light)
    light.location = location
    light.rotation_euler = (target - light.location).to_track_quat('-Z', 'Y').to_euler()
data = bpy.data.cameras.new('Face study')
camera = bpy.data.objects.new('Face study', data)
scene.collection.objects.link(camera)
scene.camera = camera
data.type, data.ortho_scale = 'ORTHO', .235
scene.render.engine = 'CYCLES'
scene.cycles.samples = 32
scene.render.resolution_x, scene.render.resolution_y = 768, 896
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = 'Standard'
scene.render.image_settings.file_format = 'PNG'
for name, offset in [('front', (0, -.5, .005)), ('profile', (.5, 0, .005)), ('three-quarter', (.35, -.42, .005))]:
    focus = target + Vector((0, .025 if name == 'profile' else 0, 0))
    camera.location = focus + Vector(offset)
    camera.rotation_euler = (focus-camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str((output / (name + '.png')).resolve())
    bpy.ops.render.render(write_still=True)
