import bpy,sys
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from reference_head import build_head
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
verts,faces,colors=build_head()
C=Matrix(((1,0,0),(0,0,-1),(0,1,0)))
data=bpy.data.meshes.new('Reference planes');data.from_pydata([C@v for v in verts],[],faces);data.update()
obj=bpy.data.objects.new('June study',data);bpy.context.collection.objects.link(obj)
palette={'skin':'edb58e','cheek':'e99e7c','lipUpper':'b96e51','lipLower':'d48765','hairDark':'794122','white':'f6e6cd','iris':'5b422c','pupil':'211e17','hair':'9e4f28','earInner':'d18b63'}
names=list(palette)
for name,h in palette.items():
 c=[int(h[i:i+2],16)/255 for i in (0,2,4)];c=[v/12.92 if v<.04045 else ((v+.055)/1.055)**2.4 for v in c]
 mat=bpy.data.materials.new(name);mat.diffuse_color=(*c,1);mat.use_nodes=True
 node=mat.node_tree.nodes.get('Principled BSDF');node.inputs['Base Color'].default_value=(*c,1);node.inputs['Roughness'].default_value=.85
 data.materials.append(mat)
for p,c in zip(data.polygons,colors):
 p.material_index=names.index(c);p.use_smooth=c in ('white','iris','pupil')
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32
scene.render.resolution_x=800;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.world.color=(.5,.5,.5);scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.80,.73,.62,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.65
scene.view_settings.view_transform='Standard'
for p,energy,size in [((-2,-3,4),160,3),((1,3,2),80,2)]:
 ld=bpy.data.lights.new('Softbox','AREA');ld.energy=energy;ld.shape='DISK';ld.size=size
 light=bpy.data.objects.new('Softbox',ld);scene.collection.objects.link(light);light.location=p;light.rotation_euler=(Vector((0,0,.16))-light.location).to_track_quat('-Z','Y').to_euler()
cd=bpy.data.cameras.new('Study camera');cam=bpy.data.objects.new('Study camera',cd);scene.collection.objects.link(cam);scene.camera=cam;cd.type='ORTHO';cd.ortho_scale=.40
for name,offset in [('front',(-1,0,0)),('three-quarter',(-1,-.55,0)),('profile',(0,-1,0))]:
 target=Vector((0,0,.17));cam.location=target+Vector(offset);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
 scene.render.filepath=str(ROOT/'validation/reconstruction'/('planes-'+name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/characters/reference/june-planes.blend'))
print('PLANE STUDY',len(verts),'vertices',len(faces),'faces')
