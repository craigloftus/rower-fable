"""Bind the complete approved sculpt, including its shorts and simplified hands."""
import bpy
import json
import hashlib
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'validation/reconstruction/fresh-rig'
layout=json.loads((OUT/'layout.json').read_text())
samples=json.loads((OUT/'samples.json').read_text())
C=Matrix(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)))
B=Matrix(((0,0,-1,0),(0,1,0,0),(1,0,0,0),(0,0,0,1)))
scale=layout['scale']
placement=Matrix.Translation(Vector(layout['hipRest']))@Matrix.Scale(scale,4)@Matrix.Translation(-(B@Vector(layout['hipSource'])))@B
def smooth(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)

def bone_matrix(bone):
    x,y,z,w=bone['q'];m=Quaternion((w,x,y,z)).to_matrix().to_4x4()
    m.translation=Vector(bone['a']);return C@m

bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'validation/reconstruction/june-final/mesh.glb'))
parts=[o for o in bpy.context.scene.objects if o.type=='MESH']
for obj in parts:obj.data.transform(C@placement@C.inverted())
reference={o.name:[v.co.copy() for v in o.data.vertices] for o in parts}

bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.ply_import(filepath=str(ROOT/'validation/reconstruction/june-final/faceted-surface.ply'),forward_axis='Y',up_axis='Z')
guide=bpy.context.object;guide.data.transform(C@placement)
arm_data=bpy.data.armatures.new('June anatomy');arm=bpy.data.objects.new('june_rig',arm_data)
bpy.context.collection.objects.link(arm);bpy.context.view_layer.objects.active=arm;arm.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for name,b in layout['rest'].items():
    bone=arm_data.edit_bones.new(name);bone.head=(0,0,0);bone.tail=(0,.1,0)
    bone.matrix=bone_matrix(b);bone.length=(Vector(b['b'])-Vector(b['a'])).length
    if b['parent']:
        bone.parent=arm_data.edit_bones[b['parent']]
        bone.use_connect=(bone.head-bone.parent.tail).length<1e-5
bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='DESELECT');guide.select_set(True);arm.select_set(True)
bpy.context.view_layer.objects.active=arm
bpy.ops.object.parent_set(type='ARMATURE_AUTO')
assert all(v.groups for v in guide.data.vertices),'Heat weighting failed on the continuous sculpt'
guide.data.calc_loop_triangles()
points=[v.co.copy() for v in guide.data.vertices]
triangles=[tuple(t.vertices) for t in guide.data.loop_triangles]
names={g.index:g.name for g in guide.vertex_groups}
weights=[{names[g.group]:g.weight for g in v.groups} for v in guide.data.vertices]
surface=BVHTree.FromPolygons(points,triangles,all_triangles=True)
cache={}
for obj in parts:
    for name in layout['rest']:obj.vertex_groups.new(name=name)
    for vertex in obj.data.vertices:
        p=vertex.co;key=tuple(round(c,7) for c in p)
        if key not in cache:
            hit,_,index,_=surface.find_nearest(p);ids=triangles[index]
            bary=barycentric_transform(hit,*(points[i] for i in ids),Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
            ws={}
            for i,w in zip(ids,bary):
                for name,amount in weights[i].items():ws[name]=ws.get(name,0)+max(0,w)*amount
            source=placement.inverted()@C.inverted()@p
            # Heat diffusion crosses the narrow gap from arm to chest. Use
            # anatomical regions here so the singlet stays on the ribcage,
            # with a short shoulder transition and a local elbow crease.
            if source.y>.005 and source.y<.331:
                k='L' if source.x>0 else 'R'
                boundary=.080+max(0,.170-source.y)*.36
                shoulder=smooth(boundary-.002,boundary+.002,abs(source.x))
                if source.y>.170:
                    side=smooth(.075,.119,abs(source.x))
                    root=1-smooth(.140,.230,source.y)
                    shoulder=(side+(shoulder-side)*root)*(1-smooth(.265,.312,source.y))
                chest=smooth(.075,.150,source.y)
                original=ws
                ws={'spine':(1-shoulder)*(1-chest),'torso':(1-shoulder)*chest}
                elbow=smooth(.170,.130,source.y)
                ws['upperArm'+k]=shoulder*(1-elbow)
                forearm=(Vector(layout['rest']['hand'+k]['a'])-Vector(layout['rest']['forearm'+k]['a']))
                t=max(0,min(1,((C.inverted()@p)-Vector(layout['rest']['forearm'+k]['a'])).dot(forearm)/forearm.length_squared))
                twist=t*2
                for j,name in enumerate(('forearm','forearmTwist','forearmWrist')):
                    ws[name+k]=shoulder*elbow*max(0,1-abs(twist-j))
                blend=max(shoulder,smooth(.040,.090,source.y))
                ws={name:ws.get(name,0)*blend+original.get(name,0)*(1-blend) for name in set(ws)|set(original)}
            # The thigh must not drag the waist and singlet down when sitting.
            # Constrain heat diffusion at the pelvis; this changes weights,
            # never the sculpt or its shared material-boundary positions.
            leg_influence=1-smooth(-.020,.017,source.y)
            pelvis_weight=0
            for name in ws:
                if name.startswith(('thigh','shin')):
                    pelvis_weight+=ws[name]*(1-leg_influence)
                    ws[name]*=leg_influence
            ws['pelvis']=ws.get('pelvis',0)+pelvis_weight
            # The middle of a femur is rigid. Keep the hem and adjacent skin
            # on that segment; blend only near the hip and knee joints.
            if abs(source.x)<.14 and source.y<0:
                core=smooth(.040,.060,-source.y)*(1-smooth(.175,.200,-source.y))
                ws={name:w*(1-core) for name,w in ws.items()}
                name='thigh'+('L' if source.x>0 else 'R')
                ws[name]=ws.get(name,0)+core
            # Face details are all carried rigidly by the head. Soles and the
            # shoe roof remain one rigid shoe, including their colour splits.
            if source.y>.290:
                head=smooth(.290,.327,source.y)
                ws={name:w*(1-head) for name,w in ws.items()}
                ws['head']=ws.get('head',0)+head
            if source.y<-.445:ws={'foot'+('L' if source.x>0 else 'R'):1}
            # Pose the existing joined finger block and thumb. The wrist
            # blend stays continuous; no replacement or individual fingers.
            if abs(source.x)>.17 and source.y<.035:
                k='L' if source.x>0 else 'R'
                hand=smooth(.035,.002,source.y)
                thumb=(1-smooth(.197,.203,abs(source.x)))*smooth(.024,.041,-source.y)*smooth(.015,.023,source.z)
                mitt=smooth(.033,.050,-source.y)*(1-thumb)
                tip=smooth(.069,.083,-source.y)
                ws={name:w*(1-hand) for name,w in ws.items()}
                ws['hand'+k]=ws.get('hand'+k,0)+hand*(1-mitt-thumb)
                ws['mitt'+k]=ws.get('mitt'+k,0)+hand*mitt*(1-tip)
                ws['mittTip'+k]=hand*mitt*tip
                thumb_tip=smooth(.044,.057,-source.y)
                ws['thumb'+k]=hand*thumb*(1-thumb_tip)
                ws['thumbTip'+k]=hand*thumb*thumb_tip
            ws=dict(sorted(ws.items(),key=lambda item:item[1],reverse=True)[:4])
            total=sum(ws.values());assert total>0,'Every sculpt vertex needs a bone influence'
            cache[key]={b:w/total for b,w in ws.items() if w>1e-7}
        for name,w in cache[key].items():obj.vertex_groups[name].add([vertex.index],w,'REPLACE')
    assert all((v.co-reference[obj.name][v.index]).length==0 for v in obj.data.vertices)
    print('BOUND',obj.name,len(obj.data.vertices),flush=True)
bpy.data.objects.remove(guide,do_unlink=True)

bpy.ops.object.select_all(action='DESELECT')
for obj in parts:obj.select_set(True)
bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join()
mesh=bpy.context.object;mesh.name='june'
for material in mesh.data.materials:
    if 'Charcoal shorts' in material.name:material.name='june_shorts'
    for node in material.node_tree.nodes:
        if node.type=='VERTEX_COLOR':node.layer_name='Color'
modifier=mesh.modifiers.new('Native anatomical skin','ARMATURE');modifier.object=arm;mesh.parent=arm
modifier.use_deform_preserve_volume=True
mesh['skinning']='dualQuaternion'
mesh['source']='Approved June sculpt; one uniform scale; original simplified hands and shorts'
arm['description']='Connected native-proportion skeleton with clavicles and distributed forearm twist'

# Grip markers track the boat's handles and do not deform the source hands.
bpy.context.view_layer.objects.active=arm;arm.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for k in ('L','R'):
    b=arm_data.edit_bones.new('grip'+k);b.head=(0,0,0);b.tail=(0,0,.08);b.use_deform=False
bpy.ops.object.mode_set(mode='OBJECT')
for sample in samples:
    posed={name:bone_matrix(b) for name,b in sample['bones'].items()}
    for name,b in sample['bones'].items():
        bone=arm.pose.bones[name];bone.rotation_mode='QUATERNION'
        rest=arm_data.bones[name]
        basis=rest.matrix_local.inverted()@posed[name]
        if rest.parent:
            basis=rest.matrix_local.inverted()@rest.parent.matrix_local@posed[rest.parent.name].inverted()@posed[name]
        bone.location=basis.to_translation();bone.rotation_quaternion=basis.to_quaternion()
        bone.rotation_quaternion.normalize();bone.scale=(1,1,1)
        bone.keyframe_insert('location',frame=1+round(sample['time']*120))
        bone.keyframe_insert('rotation_quaternion',frame=1+round(sample['time']*120))
arm.animation_data.action.name='RowingCycle'
scene=bpy.context.scene;scene.render.fps=120;scene.frame_start=1;scene.frame_end=241;scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);mesh.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'june.glb'),export_format='GLB',use_selection=True,
    export_animations=True,export_frame_range=True,export_force_sampling=True,export_animation_mode='ACTIVE_ACTIONS',
    export_nla_strips_merged_animation_name='RowingCycle',export_anim_slide_to_zero=True,export_skins=True,
    export_yup=True,export_vertex_color='MATERIAL',export_all_vertex_colors=False,export_extras=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'june.blend'))
(OUT/'binding.json').write_text(json.dumps({'scale':scale,'restVertexDisplacement':0,'replacedMeshParts':[],
    'sourceSha256':hashlib.sha256((ROOT/'validation/reconstruction/june-final/mesh.glb').read_bytes()).hexdigest(),
    'sourceTriangles':sum(len(o.data.polygons) for o in [mesh]),'bones':len(arm_data.bones),'uniqueWeightSamples':len(cache)},indent=2)+'\n')
