"""Bind the reconstructed June study to a rowing rig and bake the real stroke.

blender -b --python scripts/rig-reconstructed-june.py
Writes review assets only, so a failed deformation cannot replace the game mesh.
"""
import bpy
import json
import sys
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'validation/reconstruction/rigged'
OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'scripts'))
from anatomy import make_body,frame,smooth
C=Matrix(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)))
B=Matrix(((0,0,-1,0),(0,1,0,0),(1,0,0,0),(0,0,0,1)))
R=C@B@C.inverted()
samples=json.loads((ROOT/'validation/reconstruction/stroke-samples.json').read_text())
old_samples=json.loads((ROOT/'art/characters/stroke-samples.json').read_text())

def v(x,y,z):return Vector((x,y,z))
def boat(p):return B@p
hip=boat(v(0,.017,-.017)); neck=boat(v(0,.31,-.02))
target_hip=v(0,.415,0);target_neck=target_hip+v(0,.55,0)
source={};target={};lengths={};anchors={}
source['pelvis']=C@frame(hip,hip+v(0,.12,0))
source['torso']=C@frame(hip+v(0,.05,0),neck)
source['head']=C@frame(neck,neck+v(0,.17,0))
target['pelvis']=C@frame(target_hip,target_hip+v(0,.12,0))
target['torso']=C@frame(target_hip+v(0,.10,0),target_neck)
target['head']=C@frame(target_neck,target_neck+v(0,.30,0))
for sign,k in [(1,'L'),(-1,'R')]:
    h=boat(v(sign*.055,.017,-.017));knee=boat(v(sign*.067,-.235,.008));ankle=boat(v(sign*.077,-.442,-.03))
    shoulder=boat(v(sign*.09,.268,-.021));elbow=boat(v(sign*.148,.137,.018));wrist=boat(v(sign*.192,-.014,.011))
    dh=target_hip+v(0,0,sign*.105); ds=target_hip+v(0,.50,sign*.185)
    dk=dh+(knee-h).normalized()*.45; da=dk+(ankle-knee).normalized()*.44
    de=ds+(elbow-shoulder).normalized()*.30;dw=de+(wrist-elbow).normalized()*.30
    leg_hinge=(knee-h).cross(ankle-knee).normalized()
    arm_hinge=-(elbow-shoulder).cross(wrist-elbow).normalized()
    for name,a,b,ta,tb,hinge,old_length in [
        ('thigh',h,knee,dh,dk,leg_hinge,.45),('shin',knee,ankle,dk,da,leg_hinge,.44),
        ('upperArm',shoulder,elbow,ds,de,arm_hinge,.34),('forearm',elbow,wrist,de,dw,arm_hinge,.34),
    ]:
        bone=name+k
        source[bone]=C@frame(a,b,hinge);target[bone]=C@frame(ta,tb,hinge)
        lengths[bone]=((b-a).length,(tb-ta).length,old_length)
    source['foot'+k]=C@frame(ankle,ankle+v(-.1,0,0))
    target['foot'+k]=C@frame(da,da+v(-.1,0,0))
    x,y,z,w=samples[0]['bones']['grip'+k]['q']
    q=Quaternion((w,x,y,z))
    grip=q.to_matrix().to_4x4();grip.translation=dw-q@v(sign*.045,.045,0)
    target['grip'+k]=C@grip
    anchors[k]={'wrist':wrist,'forearmLength':(wrist-elbow).length}

_,_,_,_,old_mats,_=make_body(ROOT,C,old_samples,'june')

# Source-to-rest maps retain the new radial forms while fitting limb lengths.
body_map=C@Matrix.Translation(target_hip)@Matrix.Diagonal((1.8,.55/(neck.y-hip.y),1.8,1))@Matrix.Translation(-hip)@C.inverted()
maps={b:body_map for b in ('pelvis','torso','head')}
for bone,(sl,tl,ol) in lengths.items():
    maps[bone]=target[bone]@Matrix.Diagonal((1.8,tl/sl,1.8,1))@source[bone].inverted()
for k in ('L','R'):
    maps['foot'+k]=target['foot'+k]@Matrix.Diagonal((1.8,1.8,1.8,1))@source['foot'+k].inverted()

bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'validation/reconstruction/trellis-assembled/mesh.glb'))
parts=[o for o in bpy.context.scene.objects if o.type=='MESH']
print('Imported parts:',[o.name for o in parts],flush=True)
# Solve weights on a closed proxy of this character's own anatomy.
proxy_parts=[]
for obj in parts:
    obj.data.transform(R)
    if obj.name.startswith(('Head','Iris','Eye whites')):continue
    copy=obj.copy();copy.data=obj.data.copy();bpy.context.collection.objects.link(copy);proxy_parts.append(copy)
bpy.ops.object.select_all(action='DESELECT')
for obj in proxy_parts:obj.select_set(True)
bpy.context.view_layer.objects.active=proxy_parts[0];bpy.ops.object.join()
proxy=bpy.context.object;proxy.name='Anatomical heat-weight proxy'
import bmesh
bm=bmesh.new();bm.from_mesh(proxy.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bm.to_mesh(proxy.data);bm.free();proxy.data.validate()
proxy.data.remesh_voxel_size=.006
bpy.ops.object.voxel_remesh()
weight_data=bpy.data.armatures.new('Source anatomy');weight_arm=bpy.data.objects.new('Source anatomy',weight_data);bpy.context.collection.objects.link(weight_arm)
bpy.context.view_layer.objects.active=weight_arm;weight_arm.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for name,m in source.items():
    bone=weight_data.edit_bones.new(name);bone.head=(0,0,0);bone.tail=(0,.1,0);bone.matrix=m
    bone.length=lengths[name][0] if name in lengths else {'pelvis':.05,'torso':.243,'head':.17}.get(name,.10)
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='DESELECT');proxy.select_set(True);weight_arm.select_set(True)
bpy.context.view_layer.objects.active=weight_arm
bpy.ops.object.parent_set(type='ARMATURE_AUTO')
proxy.data.calc_loop_triangles()
dv=[vert.co.copy() for vert in proxy.data.vertices]
triangles=[tuple(t.vertices) for t in proxy.data.loop_triangles]
groups={g.index:g.name for g in proxy.vertex_groups}
dw=[{groups[g.group]:g.weight for g in vert.groups} for vert in proxy.data.vertices]
surface=BVHTree.FromPolygons(dv,triangles,all_triangles=True)
print('Heat weights:',len(dv),'proxy vertices',flush=True)
for obj in parts:
    for name in target:obj.vertex_groups.new(name=name)
    # Remove the relaxed generated hands; use the established closed grip mesh.
    import bmesh
    bm=bmesh.new();bm.from_mesh(obj.data)
    remove=[]
    for vert in bm.verts:
        p=C.inverted()@vert.co;k='L' if p.z>0 else 'R'
        local=source['forearm'+k].inverted()@vert.co
        if abs(p.z)>.16 and local.y>anchors[k]['forearmLength']-.004:remove.append(vert)
    bmesh.ops.delete(bm,geom=remove,context='VERTS');bm.to_mesh(obj.data);bm.free()
    is_head=obj.name.startswith(('Head','Iris','Eye whites'))
    for vert in obj.data.vertices:
        p=vert.co.copy();bp=C.inverted()@p
        if is_head:
            head_weight=smooth(.302,.329,bp.y)
            ws={'head':head_weight,'torso':1-head_weight}
        elif bp.y<-.421:
            k='L' if bp.z>0 else 'R';foot_weight=1-smooth(-.445,-.421,bp.y)
            ws={'foot'+k:foot_weight,'shin'+k:1-foot_weight}
        else:
            hit,_,index,_=surface.find_nearest(p)
            ids=triangles[index]
            bary=barycentric_transform(hit,*(dv[i] for i in ids),v(1,0,0),v(0,1,0),v(0,0,1))
            ws={}
            for i,weight in zip(ids,bary):
                for bone,w in dw[i].items():ws[bone]=ws.get(bone,0)+max(0,weight)*w
        if not is_head and bp.y>=-.421:
            k='L' if bp.z>0 else 'R'
            lateral=abs(bp.z)
            boundary=.095-max(0,bp.y-.225)*.5
            arm=smooth(boundary-.015,boundary+.02,lateral)*smooth(-.065,-.025,bp.y)*(1-smooth(.285,.31,bp.y))
            leg=1-smooth(-.065,.035,bp.y)
            head_weight=smooth(.302,.329,bp.y)
            for bone in list(ws):
                if bone.startswith(('upperArm','forearm')):ws[bone]*=arm
                elif bone.startswith(('thigh','shin','foot')):ws[bone]*=leg
                elif bone=='head':ws[bone]*=head_weight
                else:ws[bone]*=(1-arm)*(1-leg)
            # A torso point cannot follow the neighbouring relaxed wrist.
            ws['torso']=ws.get('torso',0)+(1-arm)*(1-leg)*(1-head_weight)*smooth(.03,.10,bp.y)
        pad=(1-smooth(-.02,.035,bp.y))*smooth(.01,.04,bp.x)*(1-smooth(.065,.095,abs(bp.z)))*smooth(-.09,-.06,bp.y)
        if pad and not is_head:
            ws={b:w*(1-pad) for b,w in ws.items()};ws['pelvis']=ws.get('pelvis',0)+pad
        ws=dict(sorted(((b,w) for b,w in ws.items() if w>1e-5),key=lambda item:item[1],reverse=True)[:4])
        total=sum(ws.values());ws={b:w/total for b,w in ws.items()}
        point=sum((w*(maps[b]@p) for b,w in ws.items()),Vector())
        if pad>.95:point.z=max(.3179,point.z)
        vert.co=point
        for bone,w in ws.items():obj.vertex_groups[bone].add([vert.index],w,'REPLACE')
    print('Bound',obj.name,len(obj.data.vertices),'vertices',flush=True)

bpy.data.objects.remove(proxy,do_unlink=True)
bpy.data.objects.remove(weight_arm,do_unlink=True)

# Reuse the closed grip geometry, transformed through its documented bone frame.
with bpy.data.libraries.load(str(ROOT/'art/characters/june.blend')) as (available,loaded):
    loaded.objects=['june']
old=loaded.objects[0];bpy.context.collection.objects.link(old)
old.modifiers.clear();old.parent=None
for sign,k in [(1,'L'),(-1,'R')]:
    group=old.vertex_groups['grip'+k].index
    ids={vert.index for vert in old.data.vertices if any(g.group==group and g.weight>.9 for g in vert.groups)}
    hand=old.copy();hand.data=old.data.copy();bpy.context.collection.objects.link(hand);hand.name='Closed grip '+k
    bm=bmesh.new();bm.from_mesh(hand.data);bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm,geom=[vert for vert in bm.verts if vert.index not in ids],context='VERTS');bm.to_mesh(hand.data);bm.free()
    transform=target['grip'+k]@old_mats['grip'+k].inverted()
    hand.data.transform(transform)
    parts.append(hand)
bpy.data.objects.remove(old,do_unlink=True)

bpy.ops.object.select_all(action='DESELECT')
for obj in parts:obj.select_set(True)
bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join()
mesh=bpy.context.object;mesh.name='june_reconstruction'
bpy.ops.mesh.customdata_custom_splitnormals_clear()
for poly in mesh.data.polygons:poly.use_smooth=True
for material in mesh.data.materials:
    if material.name.startswith('Charcoal shorts'):material.name='june_shorts'
arm_data=bpy.data.armatures.new('Reconstructed June rig');arm=bpy.data.objects.new('june_rig',arm_data);bpy.context.collection.objects.link(arm)
bpy.context.view_layer.objects.active=arm;arm.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
root=arm_data.edit_bones.new('root');root.head=(0,0,0);root.tail=(0,.1,0)
for name,m in target.items():
    bone=arm_data.edit_bones.new(name);bone.head=(0,0,0);bone.tail=(0,.1,0);bone.matrix=m;bone.length=.1;bone.parent=root
bpy.ops.object.mode_set(mode='OBJECT')
mod=mesh.modifiers.new('Rowing deform','ARMATURE');mod.object=arm;mesh.parent=arm
for sample in samples:
    for name,b in sample['bones'].items():
        x,y,z,w=b['q'];pose=Quaternion((w,x,y,z)).to_matrix().to_4x4();pose.translation=Vector(b['a'])
        basis=target[name].inverted()@C@pose
        bone=arm.pose.bones[name];bone.rotation_mode='QUATERNION';bone.location=basis.to_translation();bone.rotation_quaternion=basis.to_quaternion()
        bone.keyframe_insert('location',frame=1+round(sample['time']*120));bone.keyframe_insert('rotation_quaternion',frame=1+round(sample['time']*120))
arm.animation_data.action.name='RowingCycle'
scene=bpy.context.scene;scene.render.fps=120;scene.frame_start=1;scene.frame_end=241;scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);mesh.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'june.glb'),export_format='GLB',use_selection=True,export_animations=True,export_frame_range=True,export_force_sampling=True,export_animation_mode='ACTIVE_ACTIONS',export_nla_strips_merged_animation_name='RowingCycle',export_anim_slide_to_zero=True,export_skins=True,export_yup=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/characters/reference/june-trellis-rig.blend'))
print('EXPORTED reconstructed rowing study',flush=True)
