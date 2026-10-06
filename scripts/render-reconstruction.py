"""Inspect a reconstruction's colour and geometry from four directions.

blender -b --python scripts/render-reconstruction.py -- path/to/mesh.glb
"""
import bpy
import math
import sys
from pathlib import Path
from mathutils import Vector

path = Path(sys.argv[sys.argv.index('--')+1]).resolve()
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(path))
objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
# TripoSR writes Z-up coordinates into a raw GLB; Blender converts those mesh
# coordinates as though they were Y-up. Rotate the imported result back upright.
for obj in objects:
    obj.rotation_euler.x = -math.pi/2
bpy.context.view_layer.update()
points = [obj.matrix_world@v.co for obj in objects for v in obj.data.vertices]
low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
target = (low+high)*.5
height = high.z-low.z
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 24
scene.render.resolution_x = 720
scene.render.resolution_y = 900
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = 'Standard'
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.75, .7, .62, 1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .8
for location, power in [((3, -4, 5), 300), ((-3, 2, 3), 150)]:
    data = bpy.data.lights.new('Softbox', 'AREA')
    data.energy = power
    data.size = 4
    light = bpy.data.objects.new('Softbox', data)
    scene.collection.objects.link(light)
    light.location = location
    light.rotation_euler = (target-light.location).to_track_quat('-Z', 'Y').to_euler()
data = bpy.data.cameras.new('Study')
camera = bpy.data.objects.new('Study', data)
scene.collection.objects.link(camera)
scene.camera = camera
data.type = 'ORTHO'
data.ortho_scale = height*1.12
clay = bpy.data.materials.new('Clay')
clay.diffuse_color = (.5, .45, .38, 1)
clay.use_nodes = True
clay.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = clay.diffuse_color
clay.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .8
for mode in ('colour', 'clay'):
    if mode == 'clay':
        for obj in objects:
            obj.data.materials.clear()
            obj.data.materials.append(clay)
            for face in obj.data.polygons:
                face.material_index = 0
    for angle in (0, 90, 180, 270):
        a = math.radians(angle)
        camera.location = target+Vector((3*math.cos(a), 3*math.sin(a), .05))
        camera.rotation_euler = (target-camera.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = str(path.parent/f'{mode}-{angle}.png')
        bpy.ops.render.render(write_still=True)
print('RECONSTRUCTION BOUNDS', list(low), list(high))
