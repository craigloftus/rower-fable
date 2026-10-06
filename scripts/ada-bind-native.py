"""Bind Ada’s measured anatomy, preserving the complete standing sculpt."""
import bpy
import json,math
import hashlib
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'validation/characters/ada'
MASTER=ROOT/'art/characters/candidates/ada'
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
bpy.ops.import_scene.gltf(filepath=str(MASTER/'standing.glb'))
parts=[o for o in bpy.context.scene.objects if o.type=='MESH']
for obj in parts:obj.data.transform(C@placement@C.inverted())
reference={o.name:[v.co.copy() for v in o.data.vertices] for o in parts}

arm_data=bpy.data.armatures.new('Ada anatomy');arm=bpy.data.objects.new('ada_rig',arm_data)
bpy.context.collection.objects.link(arm);bpy.context.view_layer.objects.active=arm;arm.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for name,b in layout['rest'].items():
    bone=arm_data.edit_bones.new(name);bone.head=(0,0,0);bone.tail=(0,.1,0)
    bone.matrix=bone_matrix(b);bone.length=(Vector(b['b'])-Vector(b['a'])).length
    if b['parent']:
        bone.parent=arm_data.edit_bones[b['parent']]
        bone.use_connect=(bone.head-bone.parent.tail).length<1e-5
bpy.ops.object.mode_set(mode='OBJECT')
anatomy=layout['anatomy']
source_points={name:Vector(value) for name,value in anatomy['center'].items()}
def distance_segment(p,a,b):
    direction=b-a; t=max(0,min(1,(p-a).dot(direction)/direction.length_squared))
    return (p-a-direction*t).length,t

def source_weights(p):
    k='L' if p.x>0 else 'R'
    a={name:Vector(value) for name,value in anatomy['sides'][k].items() if isinstance(value,list) and len(value)==3}
    ay=abs(p.x); y=p.y
    hip=Vector(anatomy['hipSource'])
    if y<anatomy['regions']['shoeTop']:return {'foot'+k:1}
    # The arm/chest split is measured in the standing source, independent of weights.
    r=anatomy['regions']; edge=r['armBase']+max(0,r['armSlopeStart']-max(y,r['armFloorY']))*r['armSlope']
    arm=smooth(edge-r['armBlend'],edge+r['armBlend'],ay)
    if y>.17:
        side=smooth(.092,.150,ay)
        root=1-smooth(.14,.23,y)
        arm=side+(arm-side)*root
    arm*=1-smooth(a['shoulder'].y,a['shoulder'].y+.035,y)
    arm*=smooth(a['fingerTip'].y-.020,a['fingerTip'].y-.010,y)
    torso=smooth(hip.y+.035,source_points['waist'].y+.05,y)
    ws={'pelvis':1-torso,'spine':torso*(1-smooth(source_points['waist'].y-.025,source_points['waist'].y+.06,y)),
        'torso':torso*smooth(source_points['waist'].y-.025,source_points['waist'].y+.06,y)}
    # Blend around Ada's own femoral head, retaining the broad source pelvis.
    # A horizontal cutoff creates a pit in front and ripples under the buttock.
    hip_angle=math.atan2(p.z-a['hip'].z,a['hip'].y-y)
    leg=smooth(-2.4,-.25,hip_angle) if hip_angle<0 else 1-smooth(.40,2.25,hip_angle)
    leg*=1-smooth(.048,.075,y)
    knee=smooth(a['knee'].y+.023,a['knee'].y-.023,y)
    if ay<r['legMaxX'] or y<a['fingerTip'].y-.02:
        ws={name:w*(1-leg) for name,w in ws.items()}
        ws['thigh'+k]=leg*(1-knee);ws['shin'+k]=leg*knee
        foot=1-smooth(r['shoeTop'],r['shoeTop']+.038,y)
        if foot:
            ws={name:w*(1-foot) for name,w in ws.items()}
            ws['foot'+k]=foot
    if arm>0:
        elbow=smooth(a['elbow'].y+.025,a['elbow'].y-.025,y)
        _,t=distance_segment(p,a['elbow'],a['wrist'])
        aw={'upperArm'+k:1-elbow}
        for j,name in enumerate(('forearm','forearmTwist','forearmWrist')):aw[name+k]=elbow*max(0,1-abs(t*2-j))
        hand=smooth(a['wrist'].y+.014,a['wrist'].y-.014,y)
        if hand>0:
            # Follow both complete anatomical branches, including the thumb tip.
            td,_=distance_segment(p,a['thumbBase'],a['thumbTip'])
            fd,_=distance_segment(p,a['knuckle'],a['fingerTip'])
            thumb=smooth(.003,-.003,td-fd)*smooth(a['thumbBase'].y+.005,a['thumbBase'].y-.008,y)
            thumb*=smooth(anatomy['sides'][k]['thumbOuterX'],anatomy['sides'][k]['thumbOuterX']-.008,ay)
            mitt=smooth(a['knuckle'].y+.008,a['knuckle'].y-.008,y)*(1-thumb)
            tip=smooth(a['fingerJoint'].y+.012,a['fingerJoint'].y-.012,y)
            thumb_tip=smooth(a['thumbJoint'].y+.006,a['thumbJoint'].y-.006,y)
            hw={'hand'+k:1-mitt-thumb,'mitt'+k:mitt*(1-tip),'mittTip'+k:mitt*tip,
                'thumb'+k:thumb*(1-thumb_tip),'thumbTip'+k:thumb*thumb_tip}
            aw={name:aw.get(name,0)*(1-hand)+hw.get(name,0)*hand for name in set(aw)|set(hw)}
        ws={name:ws.get(name,0)*(1-arm)+aw.get(name,0)*arm for name in set(ws)|set(aw)}
    head=smooth(source_points['neck'].y-.025,source_points['neck'].y+.025,y)
    if head:ws={**{name:w*(1-head) for name,w in ws.items()},'head':head}
    return ws
cache={}
for obj in parts:
    for name in layout['rest']:obj.vertex_groups.new(name=name)
    for vertex in obj.data.vertices:
        p=vertex.co;key=tuple(round(c,7) for c in p)
        if key not in cache:
            source=placement.inverted()@C.inverted()@p
            ws=source_weights(source)
            ws=dict(sorted(ws.items(),key=lambda item:item[1],reverse=True)[:4])
            total=sum(ws.values());assert total>0,'Every sculpt vertex needs a bone influence'
            cache[key]={b:w/total for b,w in ws.items() if w>1e-7}
        for name,w in cache[key].items():obj.vertex_groups[name].add([vertex.index],w,'REPLACE')
    assert all((v.co-reference[obj.name][v.index]).length==0 for v in obj.data.vertices)
    print('BOUND',obj.name,len(obj.data.vertices),flush=True)

bpy.ops.object.select_all(action='DESELECT')
for obj in parts:obj.select_set(True)
bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join()
mesh=bpy.context.object;mesh.name='ada'
for material in mesh.data.materials:
    if 'Charcoal shorts' in material.name:material.name='ada_shorts'
    for node in material.node_tree.nodes:
        if node.type=='VERTEX_COLOR':node.layer_name='Color'
modifier=mesh.modifiers.new('Native anatomical skin','ARMATURE');modifier.object=arm;mesh.parent=arm
modifier.use_deform_preserve_volume=True
mesh['skinning']='dualQuaternion'
mesh['source']='Reconstructed Ada sculpt; one uniform scale; retained simplified hand geometry'
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
bpy.ops.export_scene.gltf(filepath=str(MASTER/'ada.glb'),export_format='GLB',use_selection=True,
    export_animations=True,export_frame_range=True,export_force_sampling=True,export_animation_mode='ACTIVE_ACTIONS',
    export_nla_strips_merged_animation_name='RowingCycle',export_anim_slide_to_zero=True,export_skins=True,
    export_yup=True,export_vertex_color='MATERIAL',export_all_vertex_colors=False,export_extras=True)
bpy.ops.wm.save_as_mainfile(filepath=str(MASTER/'ada.blend'))
(OUT/'binding.json').write_text(json.dumps({'scale':scale,'restVertexDisplacement':0,'replacedMeshParts':[],
    'sourceSha256':hashlib.sha256((MASTER/'standing.glb').read_bytes()).hexdigest(),
    'sourceTriangles':sum(len(o.data.polygons) for o in [mesh]),'bones':len(arm_data.bones),'uniqueWeightSamples':len(cache)},indent=2)+'\n')
