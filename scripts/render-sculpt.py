"""Repeatable studio views of June's actual mesh, without portrait cropping.
Run: blender --background art/characters/june.blend --python scripts/render-sculpt.py
"""
import bpy
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'validation/sculpt'
scene=bpy.context.scene
arm=bpy.data.objects['june_rig']
# A neutral head makes silhouette comparisons independent of the rowing lean.
scene.frame_set(1)
arm.animation_data_clear()
for bone in arm.pose.bones:
    bone.matrix_basis.identity()
bpy.context.view_layer.update()
for side,sign in [('L',1),('R',-1)]:
    hand=arm.pose.bones['grip'+side]
    wrist=arm.pose.bones['forearm'+side].matrix @ Vector((0,.34,0))
    matrix=hand.matrix.copy()
    matrix.translation=wrist-matrix.to_3x3() @ Vector((sign*.045,.045,0))
    hand.matrix=matrix
bpy.context.view_layer.update()
scene.render.resolution_x=768
scene.render.resolution_y=896
scene.cycles.samples=48
scene.world.node_tree.nodes.get('Background').inputs['Color'].default_value=(.78,.72,.62,1)
scene.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.65
head=arm.matrix_world @ arm.pose.bones['head'].head
camera=scene.camera
for name,offset,look,scale in [
    ('portrait',(-.9,-.45,.075),(0,0,.17),.48),
    ('front',(-1,0,.015),(0,0,.17),.48),
    ('profile',(-.12,-1,.03),(0,0,.17),.48),
    ('bust',(-1,-.55,.18),(0,0,-.02),.90),
]:
    target=head+Vector(look)
    camera.location=target+Vector(offset)
    camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.ortho_scale=scale
    scene.render.filepath=str(OUT/(name+'.png'))
    bpy.ops.render.render(write_still=True)
