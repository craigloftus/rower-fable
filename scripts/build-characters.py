"""Rowing-specific faceted meshes, closed grips, deform rigs and phase bake.
Run through scripts/blender-mcp.py, or Blender's --background --python.
All input motion comes from sample-stroke.mjs (the actual game geometry).
"""
import bpy
import json
import math
import sys
import random
from mathutils.bvhtree import BVHTree
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import importlib
import anatomy
importlib.reload(anatomy)
from anatomy import make_body, load_anatomy
import june_sculpt
importlib.reload(june_sculpt)
SAMPLES = json.loads((ROOT / 'art/characters/stroke-samples.json').read_text())
OUT = ROOT / 'public/characters'
OUT.mkdir(exist_ok=True)
# Three.js Y-up to Blender Z-up.
C = Matrix(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)))
CAST = [
    ('kai', '#a97145', '#748151', '#292720', 'curl'),
    ('june', '#eab48e', '#ad5c40', '#9c4a28', 'bun'),
    ('sol', '#c19367', '#c39b3d', '#242725', 'sweep'),
    ('ada', '#805039', '#688b9b', '#bfc5bf', 'crop'),
]

def frame_matrix(b):
    x,y,z,w = b['q']
    m = Quaternion((w,x,y,z)).to_matrix().to_4x4()
    m.translation = Vector(b['a'])
    return C @ m

def material(name, hex_color):
    values = [int(hex_color[i:i+2],16)/255 for i in (1,3,5)]
    # Colors in references are sRGB; Blender materials use linear values.
    values = [v/12.92 if v<.04045 else ((v+.055)/1.055)**2.4 for v in values]
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*values,1)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*values,1)
    bsdf.inputs['Roughness'].default_value = .88
    return m

def build_character(spec):
    ident, skin, shirt, hair, style = spec
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for action in list(bpy.data.actions): bpy.data.actions.remove(action)
    palette = {k:material(ident+'_'+k,v) for k,v in dict(
        skin=skin, shirt=shirt, hair=hair, shorts='#343d3c', cream='#e9e4d1',
        eye='#232b29', iris='#63513b', lip='#b9775e' if ident=='june' else '#976c57', sole='#666f66', hairLight='#ac5430' if ident=='june' else hair, hairDark='#78371e' if ident=='june' else hair, freckle='#bd805b', strap='#d8d4c2').items()}
    mats = list(palette)
    verts=[]; faces=[]; face_mats=[]; weights={}
    rest=SAMPLES[0]['bones']
    body_vs,body_fs,body_colors,body_weights,matrices,body_source=make_body(ROOT,C,SAMPLES,ident)
    verts.extend(body_vs);faces.extend(body_fs)
    face_mats.extend(mats.index(c) for c in body_colors)
    for i,ws in enumerate(body_weights):
        for bone,w in ws.items(): weights.setdefault(bone,[]).append((i,w))
    if ident=='june':
        trim_vs,trim_fs,trim_weights=june_sculpt.garment_binding(body_vs,body_fs,body_colors,body_weights)
        offset=len(verts)
        verts.extend(trim_vs);faces.extend(tuple(offset+i for i in f) for f in trim_fs)
        face_mats.extend([mats.index('shirt')]*len(trim_fs))
        for i,ws in enumerate(trim_weights):
            for bone,w in ws.items():weights.setdefault(bone,[]).append((offset+i,w))
    def mesh(vs, fs, color, bone):
        offset=len(verts)
        if bone == 'gripR':
            vs = [(-v[0],v[1],v[2]) for v in vs]
            fs = [tuple(reversed(f)) for f in fs]
        if bone == 'torso': vs = [(v[0],v[1]*1.3,v[2]) for v in vs]
        verts.extend([matrices[bone] @ Vector(v) for v in vs])
        weights.setdefault(bone,[]).extend((i,1) for i in range(offset,len(verts)))
        faces.extend([tuple(offset+i for i in f) for f in fs])
        face_mats.extend([mats.index(color)]*len(fs))
    def ellipsoid(center, scale, color, bone, segments=12, rings=8):
        vs=[]; fs=[]
        for j in range(rings+1):
            phi=math.pi*j/rings
            for i in range(segments):
                a=2*math.pi*i/segments
                vs.append((center[0]+scale[0]*math.sin(phi)*math.cos(a),
                           center[1]+scale[1]*math.cos(phi),
                           center[2]+scale[2]*math.sin(phi)*math.sin(a)))
        for j in range(rings):
            for i in range(segments):
                a=j*segments+i; b=j*segments+(i+1)%segments
                fs.append((a,b,b+segments,a+segments))
        mesh(vs,fs,color,bone)
    def tube(points, radius, color, bone, segments=8):
        vs=[]; fs=[]
        for j,p in enumerate(points):
            tangent=Vector(points[min(j+1,len(points)-1)])-Vector(points[max(0,j-1)])
            q=Vector((0,1,0)).rotation_difference(tangent.normalized())
            for i in range(segments):
                a=2*math.pi*i/segments
                r=radius[j] if isinstance(radius,list) else radius
                vs.append(Vector(p)+q@Vector((r*math.cos(a),0,r*math.sin(a))))
        for j in range(len(points)-1):
            for i in range(segments):
                a=j*segments+i; b=j*segments+(i+1)%segments
                fs.append((a,b,b+segments,a+segments))
        fs.extend([tuple(reversed(range(segments))),tuple(range(len(vs)-segments,len(vs)))])
        mesh(vs,[tuple(reversed(f)) for f in fs],color,bone)
    # The neck and face now continue directly from the shared body surface.
    source,source_groups,joints=load_anatomy(ROOT,ident)
    neck=joints['joint-neck'];hip=(joints['joint-l-upper-leg']+joints['joint-r-upper-leg'])*.5
    def hp(p):
        x,y,z=p
        return Vector((-(z-hip.z)*.104,(y-neck.y)*.61/(neck.y-hip.y),x*.115))
    head_surface=BVHTree.FromPolygons([hp(p) for p in source],source_groups['body'])
    def project(x,y):
        point=hp((x,y,0));hit,normal,_,_=head_surface.ray_cast(Vector((-1,point.y,point.z)),Vector((1,0,0)))
        return hit,normal
    for sd in [-1,1]:
        eye=joints['joint-l-eye' if sd==1 else 'joint-r-eye']
        center=hp(eye)
        eye_group=source_groups['helper-l-eye' if sd==1 else 'helper-r-eye']
        eye_ids=sorted(set(i for f in eye_group for i in f));eye_index={i:n for n,i in enumerate(eye_ids)}
        mesh([hp(source[i]) for i in eye_ids],[[eye_index[i] for i in f] for f in eye_group],'cream','head')
        front=min(hp(source[i]).x for i in eye_ids)
        iris_radius=(max(hp(source[i]).y for i in eye_ids)-min(hp(source[i]).y for i in eye_ids))*.22
        if ident=='june':iris_radius=(max(hp(source[i]).z for i in eye_ids)-min(hp(source[i]).z for i in eye_ids))*.25
        if ident=='june':
            # Lay the iris on the curved eyeball so the eyelids occlude it.
            # A flat disc in front of the ball protrudes through the upper lid.
            eye_surface=BVHTree.FromPolygons([hp(source[i]) for i in eye_ids],[[eye_index[i] for i in f] for f in eye_group])
            def eye_point(y,z,lift):
                hit,normal,_,_=eye_surface.ray_cast(Vector((-1,y,z)),Vector((1,0,0)))
                return hit+normal*lift
            for radius,color,lift in [(iris_radius,'iris',.00035),(iris_radius*.66,'eye',.00055)]:
                vs=[eye_point(center.y,center.z,lift)]
                for ring in range(1,9):
                    for j in range(40):
                        a=j*math.tau/40;r=radius*ring/8
                        vs.append(eye_point(center.y+r*math.sin(a),center.z+r*math.cos(a),lift))
                fs=[(0,1+j,1+(j+1)%40) for j in range(40)]
                for ring in range(7):
                    for j in range(40):
                        a=1+ring*40+j;b=1+ring*40+(j+1)%40;fs.append((a,a+40,b+40,b))
                mesh(vs,fs,color,'head')
            highlight=eye_point(center.y+.003,center.z-.003,.00075)
            ellipsoid(highlight,(.0004,.0012,.0012),'cream','head',10,6)
            # Find the actual upper aperture where skin meets eyeball, then
            # trace a tapered lash against that surface rather than guessing.
            width=(max(hp(source[i]).z for i in eye_ids)-min(hp(source[i]).z for i in eye_ids))*.5
            height=(max(hp(source[i]).y for i in eye_ids)-min(hp(source[i]).y for i in eye_ids))*.5
            lash=[]
            def exposed_eye(y,z):
                origin=Vector((-1,y,z));direction=Vector((1,0,0))
                eye_hit=eye_surface.ray_cast(origin,direction)[0]
                skin_hit=head_surface.ray_cast(origin,direction)[0]
                return eye_hit is not None and skin_hit is not None and eye_hit.x<skin_hit.x
            for j in range(33):
                z=center.z+width*(-.90+1.80*j/32)
                visible=[center.y+height*(-1+2*k/80) for k in range(81) if exposed_eye(center.y+height*(-1+2*k/80),z)]
                if not visible:continue
                low=max(visible);high=low+height/40
                for _ in range(10):
                    mid=(low+high)/2
                    if exposed_eye(mid,z):low=mid
                    else:high=mid
                hit,normal,_,_=head_surface.ray_cast(Vector((-1,high+.0003,z)),Vector((1,0,0)))
                lash.append(hit+normal*.0004)
            tube(lash,[.0003+.0006*math.sin(math.pi*i/(len(lash)-1)) for i in range(len(lash))],'eye','head',6)
        else:
            ellipsoid((front-.0004,center.y,center.z),(.0009,iris_radius,iris_radius),'eye','head',24,10)
            ellipsoid((front-.0012,center.y+.002,center.z-.002),(.0003,.0015,.0015),'cream','head',8,6)
        # Tapered brows hug the forehead rather than floating over the eyes.
        vs=[]
        for j in range(9):
            t=j/8;x=sd*(.10+.44*t) if ident=='june' else sd*(.12+.38*t)
            y=7.105+.028*math.sin(math.pi*t)-.028*t if ident=='june' else 7.035+.047*math.sin(math.pi*t)-.035*t
            width=.033*(1-.78*t*t) if ident=='june' else .020*math.sin(math.pi*(.10+.80*t))
            for dy in [-width,width]:
                hit,normal=project(x,y+dy);vs.append(hit+normal*.0008)
        mesh(vs,[(j*2,j*2+1,j*2+3,j*2+2) for j in range(8)],'hairDark','head')
    if ident=='june':
        rng=random.Random(18)
        for i in range(76):
            x=rng.uniform(-.57,.57);y=rng.uniform(6.44,6.66)
            hit,normal=project(x,y)
            radius=rng.uniform(.00045,.0011)
            q=Vector((0,1,0)).rotation_difference(normal)
            vs=[hit+normal*.00035+q@Vector((radius*math.cos(j*math.tau/7),0,radius*math.sin(j*math.tau/7))) for j in range(7)]
            mesh(vs,[tuple(reversed(range(7)))],'freckle','head')
    # Fit the scalp to the actual head surface in every direction. An
    # approximate ellipsoid left exposed patches at the rear of the cranium.
    def hair_edge(a):
        if ident=='june': return june_sculpt.hairline(a)
        return 1.50+.48*max(0,math.cos(a))**.7-.34*max(0,-math.cos(a))**.6
    def scalp(a,phi,ridge=0):
        center=Vector((-.045,.183,0))
        direction=Vector((.102*math.sin(phi)*math.cos(a),.119*math.cos(phi),.087*math.sin(phi)*math.sin(a))).normalized()
        hit,normal,_,_=head_surface.ray_cast(center,direction)
        return hit+normal*(.005+ridge)
    vs=[];fs=[];n=32
    for j in range(10):
        for i in range(n):
            a=2*math.pi*i/n
            phi=hair_edge(a)*j/9
            vs.append(scalp(a,phi))
    for j in range(9):
        for i in range(n):
            a=j*n+i;b=j*n+(i+1)%n;fs.append((a,b,b+n,a+n))
    mesh(vs,fs,'hair','head')
    if style=='pony':
        ellipsoid((.053,.19,0),(.047,.055,.046),'hair','head')
        ellipsoid((.075,.075,0),(.040,.115,.043),'hair','head')
    if style=='bun':
        june_sculpt.sculpt_hair(mesh,scalp)
    if style=='curl':
        for i in range(17):
            a=i*2.4
            center=scalp(a,.20+1.05*(i%4)/3,.008)
            ellipsoid(center,(.025,.024,.027),'hair','head',8,6)
    if style=='sweep':
        for lock in range(6):
            angle=math.pi-.55+lock*.22;vs=[];fs=[]
            for j in range(11):
                t=j/10;theta=angle-.85*t
                for k in range(5):
                    cross=(k-2)/2;a=theta+cross*.17
                    phi=hair_edge(a)*(1-t)+.22*t
                    ridge=.001+.018*math.sin(math.pi*t)*(1-cross*cross)
                    vs.append(scalp(a,phi,ridge))
            for j in range(10):
                for k in range(4):
                    a=j*5+k;fs.append((a,a+5,a+6,a+1))
            mesh(vs,fs,'hair','head')
    for sd in ['L','R']:
        # A shaped sole and upper, with the sole facing the foot stretcher.
        bone='foot'+sd
        shoe_rings=[(-.075,.038,.036),(-.035,.052,.065),(.025,.056,.062),(.095,.060,.045),(.155,.055,.028),(.185,.032,.008)]
        vs=[];fs=[];n=16
        for y,width,top in shoe_rings:
            for i in range(n):
                a=2*math.pi*i/n
                x=-.030+(top+.030)*((1+math.cos(a))/2)
                vs.append((x,y,width*math.sin(a)))
        for j in range(len(shoe_rings)-1):
            for i in range(n):
                a=j*n+i;b=j*n+(i+1)%n;fs.append((a,a+n,b+n,b))
        fs.extend([tuple(range(n)),tuple(reversed(range(len(vs)-n,len(vs))))])
        mesh(vs,fs,'cream',bone)
        # Separate thin outsole with a flat contact face and rounded toe.
        sv=[];sf=[]
        for x in [-.042,-.028]:
            for y,width,top in shoe_rings:
                sv.extend([(x,y,-width),(x,y,width)])
        m=len(shoe_rings)*2
        for j in range(len(shoe_rings)-1):
            a=j*2
            sf.extend([(a,a+2,a+3,a+1),(a+m,a+1+m,a+3+m,a+2+m),
                       (a,a+m,a+2+m,a+2),(a+1,a+3,a+3+m,a+1+m)])
        sf.extend([(0,1,1+m,m),(m-2,2*m-2,2*m-1,m-1)])
        mesh(sv,sf,'sole',bone)
        # Two broad velcro straps follow the upper's actual elliptical surface.
        def shoe_surface(y,theta,lift=.002):
            for i in range(len(shoe_rings)-1):
                a,aw,at=shoe_rings[i];b,bw,bt=shoe_rings[i+1]
                if a<=y<=b:
                    t=(y-a)/(b-a);width=aw+(bw-aw)*t;top=at+(bt-at)*t
                    return (-.030+(top+.030)*(1+math.cos(theta))/2+lift,y,(width+.001)*math.sin(theta))
        for y in [.025,.090]:
            vs=[]
            for dy in [-.013,.013]:
                for j in range(13):vs.append(shoe_surface(y+dy,-math.pi/2+math.pi*j/12))
            mesh(vs,[(j,j+1,j+14,j+13) for j in range(12)],'strap',bone)
            tube([shoe_surface(y-.014,-math.pi/2+math.pi*j/12,.0025) for j in range(13)],.0012,'sole',bone,6)
        # A small heel pull and reinforced rear seam.
        tube([(.008,-.077,-.017),(.038,-.086,-.017),(.038,-.086,.017),(.008,-.077,.017)],.0035,'strap',bone,6)
        # Four fingers wrap the actual 28mm-radius handle. The hand origin
        # is the grip's centre, never an approximate wrist endpoint.
        b='grip'+sd
        ellipsoid((.033,.038,0),(.039,.019,.047),'skin',b,10,6)
        for z in [-.033,-.011,.011,.033]:
            points=[]
            for i in range(9):
                a=.55+(4.35-.55)*i/8
                points.append((.038*math.cos(a),.038*math.sin(a),z))
            tube(points,[.010,.010,.0095,.009,.009,.0085,.008,.0078,.0075],'skin',b,8)
        tube([(.053,.028,.050),(.045,.008,.052),(.035,-.025,.050),(.016,-.040,.037)],[.012,.011,.010,.0085],'skin',b,8)

    arm_data=bpy.data.armatures.new(ident+'_rowing_rig')
    arm=bpy.data.objects.new(ident+'_rig',arm_data)
    bpy.context.collection.objects.link(arm)
    bpy.context.view_layer.objects.active=arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    root=arm_data.edit_bones.new('root');root.head=(0,0,0);root.tail=(0,.1,0)
    for name,m in matrices.items():
        bone=arm_data.edit_bones.new(name)
        bone.head=(0,0,0);bone.tail=(0,.1,0);bone.matrix=m;bone.length=.1
        bone.parent=root
    bpy.ops.object.mode_set(mode='OBJECT')
    data=bpy.data.meshes.new(ident+'_mesh'); data.from_pydata(verts,[],faces);data.update()
    obj=bpy.data.objects.new(ident,data);bpy.context.collection.objects.link(obj)
    for name in mats:data.materials.append(palette[name])
    facet_faces=set()
    for poly,mi in zip(data.polygons,face_mats):
        poly.material_index=mi
        poly.use_smooth=poly.index<len(body_fs) and any(body_weights[i].get('head',0)>.2 for i in poly.vertices)
        if ident=='june' and poly.use_smooth:
            p=sum((body_source[i] for i in poly.vertices),Vector())/len(poly.vertices)
            # Broad cheek, jaw and forehead facets surround smooth eyelids
            # and lips; the reference uses planes rather than a waxy surface.
            eye_detail=((abs(p.x)-.30)/.27)**2+((p.y-6.80)/.23)**2<1.35
            lip_detail=abs(p.x)<.38 and 6.10<p.y<6.41
            ear_detail=abs(p.x)>.69 and 6.10<p.y<6.95
            detail=eye_detail or lip_detail or ear_detail
            poly.use_smooth=detail or p.y<5.9
            if not poly.use_smooth:facet_faces.add(poly.index)
    # Bake subtle facial pigmentation into glTF vertex colours. It uses the
    # same mesh in Blender and Three.js and needs no external texture files.
    lip_strength={}
    for part,scale in [('upper',.018),('lower',.035)]:
        for line in (ROOT/'art/source'/('mouth-'+part+'lip-volume-incr.target')).read_text().splitlines():
            if not line.strip() or line.startswith('#'):continue
            i,x,y,z=line.split();key=tuple(round(v,6) for v in source[int(i)])
            lip_strength[key]=max(lip_strength.get(key,0),min(1,max(0,float(z)/scale)))
    skin_color=Vector(palette['skin'].diffuse_color[:3]);lip_color=Vector(palette['lip'].diffuse_color[:3])
    blush_color=Vector((.64,.26,.15))
    painted=data.color_attributes.new(name='Complexion',type='FLOAT_COLOR',domain='CORNER')
    for poly in data.polygons:
        for loop in poly.loop_indices:
            i=data.loops[loop].vertex_index
            color=Vector((1,1,1))
            if mats[poly.material_index]=='skin':
                color=skin_color.copy()
                if i<len(body_source):
                    p=body_source[i];key=tuple(round(v,6) for v in p)
                    color=color.lerp(lip_color,.9*lip_strength.get(key,0))
                    if ident=='june' and p.z>.8:
                        blush=.36*math.exp(-((abs(p.x)-.46)/.26)**2-((p.y-6.57)/.19)**2)
                        color=color.lerp(blush_color,blush)
                        lip=.60*math.exp(-((p.y-(6.27+.08*(abs(p.x)/.3)**2))/.055)**4)
                        lip*=max(0,min(1,(.33-abs(p.x))/.10))*max(0,min(1,(p.z-1.24)/.10))
                        color=color.lerp(lip_color,lip)
            painted.data[loop].color=(*color,1)
    skin_shader=palette['skin'].node_tree
    vertex_color=skin_shader.nodes.new('ShaderNodeVertexColor');vertex_color.layer_name='Complexion'
    skin_shader.links.new(vertex_color.outputs['Color'],skin_shader.nodes.get('Principled BSDF').inputs['Base Color'])
    for bone,entries in weights.items():
        group=obj.vertex_groups.new(name=bone)
        for i,w in entries: group.add([i],w,'REPLACE')
    if ident=='june':
        import bmesh
        bm=bmesh.new();bm.from_mesh(data);bm.faces.ensure_lookup_table()
        # Remove the source mesh's grid within the broad facial planes. Keep
        # the fine eye/lip topology and every garment/rigging boundary intact.
        edges=[e for e in bm.edges if len(e.link_faces)==2 and all(f.index in facet_faces for f in e.link_faces)]
        bmesh.ops.dissolve_limit(bm,angle_limit=.15,verts=[],edges=edges,delimit={'MATERIAL'},use_dissolve_boundaries=False)
        faceted_materials={mats.index(c) for c in ('skin','shirt','shorts')}
        bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>4 or (len(f.verts)==4 and not f.smooth and f.material_index in faceted_materials)],quad_method='BEAUTY',ngon_method='BEAUTY')
        bm.to_mesh(data);bm.free();data.update()
        # Re-seat freckles on the final facial planes after the topology pass.
        surface=BVHTree.FromPolygons([v.co for v in data.vertices],[list(p.vertices) for p in data.polygons if p.material_index==mats.index('skin')])
        for poly in data.polygons:
            if poly.material_index!=mats.index('freckle'):continue
            center=sum((data.vertices[i].co for i in poly.vertices),Vector())/len(poly.vertices)
            hit,normal,_,_=surface.find_nearest(center)
            rotation=poly.normal.rotation_difference(normal)
            for i in poly.vertices:data.vertices[i].co=hit+normal*.00035+rotation@(data.vertices[i].co-center)
        data.update()
        # Blend the broad planes into the delicate eye/lip loops; an abrupt
        # flat/smooth boundary creates a visible band across the cheeks.
        inverse_head=matrices['head'].inverted()
        head_group=obj.vertex_groups['head'].index
        head_ids={v.index for v in data.vertices if any(g.group==head_group and g.weight>.8 for g in v.groups)}
        normals=[]
        for poly in data.polygons:
            face_skin=poly.material_index==mats.index('skin') and all(i in head_ids for i in poly.vertices)
            smooth_face=poly.use_smooth
            if face_skin:poly.use_smooth=True
            for loop in poly.loop_indices:
                v=data.vertices[data.loops[loop].vertex_index]
                if face_skin:
                    local=inverse_head@v.co;x=local.z/.115;y=local.y*(neck.y-hip.y)/.61+neck.y
                    eyes=math.exp(-((abs(x)-.30)/.30)**4-((y-6.8)/.27)**4)
                    mouth=math.exp(-(x/.40)**4-((y-6.25)/.20)**4)
                    ears=max(0,min(1,(abs(x)-.64)/.08))
                    amount=.72*(1-max(eyes,mouth,ears))
                    normals.append(v.normal.lerp(poly.normal,amount).normalized())
                else:normals.append(v.normal if smooth_face else poly.normal)
        data.normals_split_custom_set(normals)
    mod=obj.modifiers.new('Rowing deform','ARMATURE');mod.object=arm
    obj.parent=arm
    arm['description']='Shared anatomical rowing body; blended shoulder, hip, elbow and knee loops; closed grip and shaped shoes.'
    arm['phase_mapping']='drive p -> seconds p; recovery p -> seconds 1+p'
    arm['reference']=f'art/characters/{ident}-concept.png'
    for frame in SAMPLES:
        for name,b in frame['bones'].items():
            pb=arm.pose.bones[name]
            pb.rotation_mode='QUATERNION'
            basis=arm.data.bones[name].matrix_local.inverted() @ frame_matrix(b)
            pb.location=basis.to_translation()
            pb.rotation_quaternion=basis.to_quaternion()
            pb.keyframe_insert('location',frame=1+round(frame['time']*120),group=name)
            pb.keyframe_insert('rotation_quaternion',frame=1+round(frame['time']*120),group=name)
    arm.animation_data.action.name='RowingCycle'
    scene=bpy.context.scene
    scene.render.fps=120;scene.frame_start=1;scene.frame_end=241;scene.frame_set(1)
    # Selection-only export excludes studio camera and lights.
    bpy.ops.object.select_all(action='DESELECT');arm.select_set(True);obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(OUT/(ident+'.glb')),export_format='GLB',use_selection=True,export_vertex_color='ACTIVE',export_all_vertex_colors=False,
        export_animations=True,export_frame_range=True,export_force_sampling=True,
        export_animation_mode='ACTIVE_ACTIONS',export_nla_strips_merged_animation_name='RowingCycle',export_anim_slide_to_zero=True,export_skins=True,export_yup=True)
    # A portrait from the actual mesh is the most honest avatar preview.
    scene.world.use_nodes=True
    scene.world.node_tree.nodes.get('Background').inputs['Color'].default_value=(.72,.70,.63,1)
    scene.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.8
    scene.render.engine='CYCLES';scene.cycles.samples=24
    scene.render.resolution_x=320;scene.render.resolution_y=320;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
    scene.view_settings.view_transform='Standard'
    headpos=Vector(rest['head']['a'])+Vector((0,.16,0));headpos=C@headpos
    for loc,power,size in [((-3,-4,6),450,4),((2,2,4),250,3)]:
        data=bpy.data.lights.new('Studio','AREA');data.energy=power;data.shape='DISK';data.size=size
        light=bpy.data.objects.new('Studio',data);scene.collection.objects.link(light);light.location=loc
        light.rotation_euler=(headpos-light.location).to_track_quat('-Z','Y').to_euler()
    camdata=bpy.data.cameras.new('Portrait');cam=bpy.data.objects.new('Portrait',camdata)
    scene.collection.objects.link(cam);scene.camera=cam
    cam.location=headpos+Vector((-.9,-.45,.18));cam.rotation_euler=(headpos-Vector((0,0,.045))-cam.location).to_track_quat('-Z','Y').to_euler()
    camdata.type='ORTHO';camdata.ortho_scale=.56
    scene.render.filepath=str(OUT/(ident+'.png'))
    bpy.ops.render.render(write_still=True)
    # Keep a useful full-body viewport and editable source.
    bpy.context.view_layer.objects.active=arm
    bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'art/characters'/(ident+'.blend')))
    print(f'BUILT {ident}: {len(verts)} vertices, {len(faces)} faces, {len(rest)} deform bones')

selected = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
for spec in CAST:
    if spec[0]=='june':continue  # June uses build-final-june.mjs and its approved sculpt.
    if selected and spec[0] not in selected: continue
    build_character(spec)
