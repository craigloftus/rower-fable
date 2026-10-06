"""Rejected voxel-remesh experiment; retained to document the evaluated route.

The generated shell collapsed into thin fragments. Do not use this output
for the character. A valid continuous surface must precede texture baking.

blender -b --python scripts/retopologize-reconstruction.py -- SOURCE.glb OUT.glb
"""
import bpy
import sys
from pathlib import Path
source_path,output_path=map(Path,sys.argv[sys.argv.index('--')+1:])
output_path.parent.mkdir(exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(source_path.resolve()))
objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in objects:o.select_set(True)
bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join()
source=bpy.context.object;source.name='Reconstructed source'
# Bake only albedo, without carrying lights or specular highlights into the map.
for material in source.data.materials:
    nodes=material.node_tree.nodes;links=material.node_tree.links
    bsdf=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
    emission=nodes.new('ShaderNodeEmission')
    base=bsdf.inputs['Base Color']
    if base.is_linked:links.new(base.links[0].from_socket,emission.inputs['Color'])
    else:emission.inputs['Color'].default_value=base.default_value
    output=next(n for n in nodes if n.type=='OUTPUT_MATERIAL')
    links.new(emission.outputs[0],output.inputs['Surface'])
target=source.copy();target.data=source.data.copy();bpy.context.collection.objects.link(target)
target.name='June continuous sculpt'
bpy.ops.object.select_all(action='DESELECT');target.select_set(True);bpy.context.view_layer.objects.active=target
import bmesh
bm=bmesh.new();bm.from_mesh(target.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bm.to_mesh(target.data);bm.free();target.data.validate()
target.data.remesh_voxel_size=.002
bpy.ops.object.voxel_remesh()
print('Closed surface:',len(target.data.polygons),'quads',flush=True)
decimate=target.modifiers.new('Preserve sculpt planes','DECIMATE')
decimate.ratio=min(1,100000/(2*len(target.data.polygons)))
bpy.ops.object.modifier_apply(modifier=decimate.name)
target.data.validate()
for p in target.data.polygons:p.use_smooth=True
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=1.15192,island_margin=.002)
bpy.ops.object.mode_set(mode='OBJECT')
image=bpy.data.images.new('June albedo',width=2048,height=2048,alpha=False)
mat=bpy.data.materials.new('June sculpt albedo');mat.use_nodes=True
nodes=mat.node_tree.nodes;texture=nodes.new('ShaderNodeTexImage');texture.image=image;nodes.active=texture
bsdf=nodes.get('Principled BSDF');bsdf.inputs['Roughness'].default_value=.9
target.data.materials.clear();target.data.materials.append(mat)
for poly in target.data.polygons:poly.material_index=0
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=1
scene.render.bake.use_selected_to_active=True;scene.render.bake.cage_extrusion=.015;scene.render.bake.max_ray_distance=.03;scene.render.bake.margin=8
source.select_set(True);target.select_set(True);bpy.context.view_layer.objects.active=target
bpy.ops.object.bake(type='EMIT',use_selected_to_active=True,cage_extrusion=.015,max_ray_distance=.03,margin=8)
mat.node_tree.links.new(texture.outputs['Color'],bsdf.inputs['Base Color'])
image.pack()
source.select_set(False)
bpy.ops.export_scene.gltf(filepath=str(output_path.resolve()),export_format='GLB',use_selection=True,export_animations=False)
source.hide_render=True;source.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(output_path.with_suffix('.blend').resolve()))
print('Baked continuous sculpt:',output_path,flush=True)
