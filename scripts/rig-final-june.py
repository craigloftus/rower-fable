"""Bind the final faceted June mesh to a rowing rig and bake the real stroke.

blender -b --python scripts/rig-final-june.py
Writes review assets only, so a failed deformation cannot replace the game mesh.
"""
import bpy
import json
import sys
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'validation/reconstruction/rigged'
OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'scripts'))
from anatomy import make_body,frame,smooth
from june_pattern import singlet
from june_fit import cut_limb,connect_limbs
C=Matrix(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)))
B=Matrix(((0,0,-1,0),(0,1,0,0),(1,0,0,0),(0,0,0,1)))
R=C@B@C.inverted()
samples=json.loads((ROOT/'validation/reconstruction/stroke-samples.json').read_text())
profile=json.loads((ROOT/'validation/reconstruction/rig-profile.json').read_text())
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
    h=boat(v(sign*.055,.017,-.017));knee=boat(v(sign*.076,-.216,-.008));ankle=boat(v(sign*.102,-.442,-.03))
    # Put the humeral pivot on the same mapped shoulder as the trunk. The
    # earlier pivot added a 3 cm vertical / 2 cm lateral jump between their maps.
    shoulder=boat(v(sign*(.185/1.8),.017+.50/.55*(.31-.017),-.017))
    elbow=boat(v(sign*.123,.140,-.021));wrist=boat(v(sign*.198,-.014,.011))
    dh=target_hip+v(0,0,sign*.105); ds=target_hip+v(0,.50,sign*.185)
    dk=dh+(knee-h).normalized()*profile['thigh']; da=dk+(ankle-knee).normalized()*profile['shin']
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
    foot_direction=v(-.13,0,sign*.038)
    source['foot'+k]=C@frame(ankle,ankle+foot_direction,v(0,1,0).cross(foot_direction))
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
maps['head']=target['head']@Matrix.Diagonal((1.8,1.8,1.8,1))@source['head'].inverted()
for bone,(sl,tl,ol) in lengths.items():
    maps[bone]=target[bone]@Matrix.Diagonal((1.8,tl/sl,1.8,1))@source[bone].inverted()
for k in ('L','R'):
    maps['foot'+k]=target['foot'+k]@Matrix.Diagonal((1.8,1.8,1.8,1))@source['foot'+k].inverted()

bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'validation/reconstruction/june-final/mesh.glb'))
parts=[o for o in bpy.context.scene.objects if o.type=='MESH']
# The rowing garment has dedicated hip loops. The standing reconstruction's
# shorts are replaced by this fitted garment when the character is seated.
for obj in list(parts):
    if obj.name=='Charcoal shorts':parts.remove(obj);bpy.data.objects.remove(obj,do_unlink=True)
print('Imported parts:',[(o.name,[a.name for a in o.data.color_attributes]) for o in parts],flush=True)
# Bind the continuous sculpt before transferring weights to material splits.
for obj in parts:obj.data.transform(R)
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.ply_import(filepath=str(ROOT/'validation/reconstruction/june-final/faceted-surface.ply'),forward_axis='Y',up_axis='Z')
proxy=bpy.context.object;proxy.data.transform(C@B)
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
print('Continuous heat guide:',len(dv),'proxy vertices',flush=True)
normal_maps={bone:matrix.to_3x3().inverted().transposed() for bone,matrix in maps.items()}

def rowing_shape(p):
    """Ease the chest and lumbar curve into the seated singlet profile."""
    q=p.copy()
    chest=np.exp(-((p.y-.211)/.060)**4)*smooth(.020,.060,-p.x)
    q.x+=max(0,-p.x-.020)*.34*chest
    lumbar=np.exp(-((p.y-.093)/.072)**4)*smooth(.005,.035,p.x)
    q.x+=.014*lumbar
    return q

def shape_normal(p):
    columns=[]
    for i in range(3):
        delta=Vector();delta[i]=.00002
        columns.append((rowing_shape(p+delta)-rowing_shape(p-delta))/.00004)
    return C.to_3x3()@Matrix(columns).transposed().inverted().transposed()@C.to_3x3().inverted()

for obj in parts:
    for name in target:obj.vertex_groups.new(name=name)
    # Remove the relaxed generated hands; use the established closed grip mesh.
    import bmesh
    bm=bmesh.new();bm.from_mesh(obj.data)
    if obj.name=='Skin':
        for sign,k in [(1,'L'),(-1,'R')]:
            forearm=source['forearm'+k]
            cut_limb(bm,lambda p:sign*(C.inverted()@p).z>.14,
                     forearm@v(0,anchors[k]['forearmLength']-.003,0),forearm.to_3x3()@v(0,1,0))
            cut_limb(bm,lambda p: .015<sign*(C.inverted()@p).z<.14 and (C.inverted()@p).y<-.045,
                     C@v(0,-.110,0),C.to_3x3()@v(0,1,0))
    bm.to_mesh(obj.data);bm.free()
    saved_normals=[n.vector.copy() for n in obj.data.corner_normals]
    vertex_normal_maps=[]
    for vert in obj.data.vertices:
        p=vert.co.copy();bp=C.inverted()@p
        if bp.y>.30:
            head_weight=smooth(.302,.329,bp.y)
            ws={'head':head_weight,'torso':1-head_weight}
        elif bp.y<-.421:
            k='L' if bp.z>0 else 'R';foot_weight=1-smooth(-.445,-.421,bp.y)
            ws={'foot'+k:foot_weight,'shin'+k:1-foot_weight}
        elif bp.y<-.070 and abs(bp.z)<.135:
            k='L' if bp.z>0 else 'R'
            shin=1-smooth(-.242,-.192,bp.y)
            ws={'thigh'+k:1-shin,'shin'+k:shin}
        elif abs(bp.z)>.17:
            k='L' if bp.z>0 else 'R'
            ws={'forearm'+k:1}
        elif .025<bp.y<.205 and abs(bp.z)<.074+.042*max(0,min(1,(.14-bp.y)/.075)):
            torso=smooth(.020,.160,bp.y)
            ws={'pelvis':1-torso,'torso':torso}
        else:
            hit,_,index,_=surface.find_nearest(p)
            ids=triangles[index]
            bary=barycentric_transform(hit,*(dv[i] for i in ids),v(1,0,0),v(0,1,0),v(0,0,1))
            ws={}
            for i,weight in zip(ids,bary):
                for bone,w in dw[i].items():ws[bone]=ws.get(bone,0)+max(0,weight)*w
        # Use a continuous hinge blend through the elbow. Heat weights near
        # the torso can pull its outer surface into a point during recovery.
        elbow_blend=smooth(.082,.108,abs(bp.z))*smooth(.065,.105,bp.y)*(1-smooth(.185,.225,bp.y))
        if elbow_blend:
            k='L' if bp.z>0 else 'R';forearm=1-smooth(.108,.176,bp.y)
            ws={bone:w*(1-elbow_blend) for bone,w in ws.items()}
            ws['upperArm'+k]=ws.get('upperArm'+k,0)+elbow_blend*(1-forearm)
            ws['forearm'+k]=ws.get('forearm'+k,0)+elbow_blend*forearm
        # Weight the clavicle and deltoid by anatomy, independently of the
        # painted armhole. Both skin and fabric share this broad transition.
        if .17<bp.y<.302:
            k='L' if bp.z>0 else 'R'
            upper=smooth(.058,.110,abs(bp.z))*(1-smooth(.282,.302,bp.y))
            chest=smooth(.005,.040,-bp.x)*(1-smooth(.245,.270,bp.y))
            upper*=1-chest
            blend=smooth(.17,.205,bp.y)
            ws={bone:w*(1-blend) for bone,w in ws.items()}
            ws['torso']=ws.get('torso',0)+blend*(1-upper)
            ws['upperArm'+k]=ws.get('upperArm'+k,0)+blend*upper
        # Keep the lower singlet on the trunk without forcing the shoulder
        # weights to jump at a clothing boundary.
        if .025<bp.y<.205:
            garment=float(singlet(np.array([[bp.z,bp.y,-bp.x]]))[0])
            trunk=1-smooth(-.0005,.009,garment)
            trunk*=1-smooth(.17,.205,bp.y)
            if trunk:
                torso=smooth(.020,.160,bp.y)
                ws={bone:w*(1-trunk) for bone,w in ws.items()}
                ws['torso']=ws.get('torso',0)+trunk*torso
                ws['pelvis']=ws.get('pelvis',0)+trunk*(1-torso)
        ws=dict(sorted(((b,w) for b,w in ws.items() if w>1e-5),key=lambda item:item[1],reverse=True)[:4])
        total=sum(ws.values())
        assert total>1e-6, f'Unbound anatomical point {obj.name}: {list(bp)}'
        ws={b:w/total for b,w in ws.items()}
        shaped=C@rowing_shape(bp)
        point=sum((w*(maps[b]@shaped) for b,w in ws.items()),Vector())
        vert.co=point
        vertex_normal_maps.append(sum((normal_maps[b]*w for b,w in ws.items()),Matrix(((0,0,0),(0,0,0),(0,0,0))))@shape_normal(bp))
        for bone,w in ws.items():obj.vertex_groups[bone].add([vert.index],w,'REPLACE')
    obj.data.update()
    obj.data.normals_split_custom_set([(vertex_normal_maps[loop.vertex_index]@saved_normals[loop.index]).normalized() for loop in obj.data.loops])
    print('Bound',obj.name,len(obj.data.vertices),'vertices',flush=True)

bpy.data.objects.remove(proxy,do_unlink=True)
bpy.data.objects.remove(weight_arm,do_unlink=True)

# Reuse the closed grip geometry, transformed through its documented bone frame.
with bpy.data.libraries.load(str(ROOT/'art/characters/reference/june-rowing-components.blend')) as (available,loaded):
    loaded.objects=['june']
old=loaded.objects[0];bpy.context.collection.objects.link(old)
old.modifiers.clear();old.parent=None
short_materials={i for i,m in enumerate(old.data.materials) if '_shorts' in m.name}
shorts=old.copy();shorts.data=old.data.copy();bpy.context.collection.objects.link(shorts);shorts.name='June rowing shorts'
import bmesh
bm=bmesh.new();bm.from_mesh(shorts.data)
bmesh.ops.delete(bm,geom=[face for face in bm.faces if face.material_index not in short_materials],context='FACES')
bmesh.ops.delete(bm,geom=[vert for vert in bm.verts if not vert.link_faces],context='VERTS')
# Replace the upper waistband with a strip fitted to the reconstructed singlet.
# The sitting pads become fixed constraints while the remaining shell is fitted.
cut_limb(bm,lambda p:True,C@v(0,.490,0),C.to_3x3()@v(0,1,0))
bm.to_mesh(shorts.data);bm.free()
shorts_bones=set()
group_names={g.index:g.name for g in shorts.vertex_groups}
for vertex in shorts.data.vertices:
    for group in vertex.groups:
        if group.weight>1e-6:shorts_bones.add(group_names[group.group])
for group in shorts.vertex_groups:group.name='shorts_'+group.name
for name in shorts_bones:target['shorts_'+name]=old_mats[name]
shorts.data.materials.clear()
cloth=bpy.data.materials.new('june_shorts');cloth.use_nodes=True
rgb=[57/255,58/255,51/255]
cloth.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=tuple(c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in rgb)+(1,)
cloth.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.86
shorts.data.materials.append(cloth)
for poly in shorts.data.polygons:poly.material_index=0
for attribute in list(shorts.data.color_attributes):shorts.data.color_attributes.remove(attribute)
parts.append(shorts)
for sign,k in [(1,'L'),(-1,'R')]:
    group=old.vertex_groups['grip'+k].index
    ids={vert.index for vert in old.data.vertices if any(g.group==group and g.weight>.9 for g in vert.groups)}
    hand=old.copy();hand.data=old.data.copy();bpy.context.collection.objects.link(hand);hand.name='Closed grip '+k
    bm=bmesh.new();bm.from_mesh(hand.data);bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm,geom=[vert for vert in bm.verts if vert.index not in ids],context='VERTS');bm.to_mesh(hand.data);bm.free()
    transform=target['grip'+k]@old_mats['grip'+k].inverted()
    hand.data.transform(transform)
    hand.data.materials.clear()
    grip_material=bpy.data.materials.new('June · Grip skin '+k);grip_material.use_nodes=True
    rgb=[207/255,151/255,113/255]
    base=tuple(c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4 for c in rgb)+(1,)
    grip_material.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=base
    grip_material.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.86
    hand.data.materials.append(grip_material)
    for poly in hand.data.polygons:poly.material_index=0
    for attribute in list(hand.data.color_attributes):hand.data.color_attributes.remove(attribute)
    parts.append(hand)
parts.extend(connect_limbs(parts,shorts,target,samples,C,grip_material))
bpy.data.objects.remove(old,do_unlink=True)

bpy.ops.object.select_all(action='DESELECT')
for obj in parts:obj.select_set(True)
bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join()
mesh=bpy.context.object;mesh.name='june'
for material in mesh.data.materials:
    for node in material.node_tree.nodes:
        if node.type=='VERTEX_COLOR':node.layer_name='Color'

for material in mesh.data.materials:
    if 'Charcoal shorts' in material.name:material.name='june_shorts'
arm_data=bpy.data.armatures.new('Reconstructed June rig');arm=bpy.data.objects.new('june_rig',arm_data);bpy.context.collection.objects.link(arm)
bpy.context.view_layer.objects.active=arm;arm.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
root=arm_data.edit_bones.new('root');root.head=(0,0,0);root.tail=(0,.1,0)
for name,m in target.items():
    bone=arm_data.edit_bones.new(name);bone.head=(0,0,0);bone.tail=(0,.1,0);bone.matrix=m;bone.length=.1;bone.parent=root
bpy.ops.object.mode_set(mode='OBJECT')
mod=mesh.modifiers.new('Rowing deform','ARMATURE');mod.object=arm;mesh.parent=arm
for sample in samples:
    posed_bones={**sample['bones'],**{'shorts_'+name:sample['bones'][name] for name in shorts_bones}}
    for name,b in posed_bones.items():
        x,y,z,w=b['q'];pose=Quaternion((w,x,y,z)).to_matrix().to_4x4();pose.translation=Vector(b['a'])
        basis=target[name].inverted()@C@pose
        bone=arm.pose.bones[name];bone.rotation_mode='QUATERNION';bone.location=basis.to_translation();bone.rotation_quaternion=basis.to_quaternion()
        bone.keyframe_insert('location',frame=1+round(sample['time']*120));bone.keyframe_insert('rotation_quaternion',frame=1+round(sample['time']*120))
arm.animation_data.action.name='RowingCycle'
scene=bpy.context.scene;scene.render.fps=120;scene.frame_start=1;scene.frame_end=241;scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);mesh.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'june.glb'),export_format='GLB',use_selection=True,export_animations=True,export_frame_range=True,export_force_sampling=True,export_animation_mode='ACTIVE_ACTIONS',export_nla_strips_merged_animation_name='RowingCycle',export_anim_slide_to_zero=True,export_skins=True,export_yup=True,export_vertex_color='MATERIAL',export_all_vertex_colors=False)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/characters/reference/june-final-rig.blend'))
print('EXPORTED reconstructed rowing study',flush=True)
