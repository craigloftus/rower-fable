"""Shared rowing body, adapted from MakeHuman's CC0 anatomical mesh/weights.

The source is reshaped in an A-pose before binding. Shoulder and hip vertices
blend across real joint loops rather than overlapping capped cylinders.
"""
import json
import math
from mathutils import Vector, Matrix

def smooth(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)))
    return t*t*(3-2*t)

def load_anatomy(root, ident='june'):
    positions=[]; groups={}; group=''
    for line in (root/'art/source/makehuman-base.obj').read_text().splitlines():
        parts=line.split()
        if not parts: continue
        if parts[0]=='v': positions.append(Vector(tuple(map(float,parts[1:4]))))
        elif parts[0]=='g': group=parts[1]
        elif parts[0]=='f':
            face=[int(p.split('/')[0])-1 for p in parts[1:]]
            groups.setdefault(group,[]).append(face)
    profile='male' if ident in ('kai','sol') else 'female'
    targets=[(profile+'-young.target',1),(profile+'-athletic.target',1)]
    if ident=='june':
        targets += [('eye-left-larger.target',.95),('eye-right-larger.target',.95),
                    ('mouth-smile.target',.70),('nose-shorter.target',.38),('chin-softer.target',.25)]
    for name,strength in targets:
        for line in (root/'art/source'/name).read_text().splitlines():
            if not line.strip() or line.startswith('#'): continue
            i,x,y,z=line.split();positions[int(i)]+=Vector((float(x),float(y),float(z)))*strength
    # Profile targets have different origin heights. Put every profile in a
    # common anatomical coordinate system before cutting clothes or locating
    # face details; the body shapes and source vertex indices are preserved.
    def center(name):
        ids=set(i for f in groups['joint-'+name] for i in f)
        return sum((positions[i] for i in ids),Vector())/len(ids)
    hip_y=(center('l-upper-leg').y+center('r-upper-leg').y)/2
    neck_y=center('neck').y
    crown_y=max(positions[i].y for f in groups['body'] for i in f)
    for p in positions:
        if p.y>neck_y:p.y=5.394+(p.y-neck_y)*(7.8643-5.394)/(crown_y-neck_y)
        else:p.y=.02815+(p.y-hip_y)*(5.394-.02815)/(neck_y-hip_y)
    if ident=='june':
        from june_sculpt import sculpt_face
        sculpt_face(positions)
    # Relax dense chest detail beneath the athletic top, so the fabric bridges
    # small anatomical features instead of looking painted onto bare skin.
    adjacent={}
    for f in groups['body']:
        for a,b in zip(f,f[1:]+f[:1]):
            adjacent.setdefault(a,set()).add(b);adjacent.setdefault(b,set()).add(a)
    for _ in range(12):
        changed={}
        for i,neighbors in adjacent.items():
            p=positions[i]
            influence=max(0,1-abs(p.y-3.3)/1.5)*max(0,min(1,p.z/.4))
            if influence and abs(p.x)<1.5:
                mean=sum((positions[j] for j in neighbors),Vector())/len(neighbors)
                changed[i]=p.lerp(mean,.5*influence)
        for i,p in changed.items():positions[i]=p
    if ident=='june':
        # A tensioned vest bridges the breast contours with a broad convex
        # fabric plane, retaining volume without tracing the anatomical cups.
        for p in positions:
            amount=math.exp(-((p.y-3.45)/.65)**4)*smooth(.55,1.15,p.z)
            amount*=1-smooth(1.20,1.65,abs(p.x))
            surface=1.47-.12*(abs(p.x)/1.2)**2
            p.z+=(surface-p.z)*amount*.88
    # Compression shorts bridge the centre instead of reproducing a hanging
    # anatomical contour. Blend the raised, flatter crotch into both legs.
    for p in positions:
        if -1.25<p.y<.35:
            centre=1-smooth(.12,.52,abs(p.x))
            lower=1-smooth(-.25,.35,p.y)
            p.y+=max(0,-.48-p.y)*centre
            p.z-=max(0,p.z-.38)*centre*lower
    joints={}
    for name,polys in groups.items():
        if name.startswith('joint-'):
            ids=set(i for f in polys for i in f)
            joints[name]=sum((positions[i] for i in ids),Vector())/len(ids)
    return positions,groups,joints

def frame(a,b,hinge=None):
    y=(b-a).normalized()
    if hinge is None:
        m=Vector((0,1,0)).rotation_difference(y).to_matrix().to_4x4()
    else:
        z=hinge.normalized();x=y.cross(z).normalized()
        m=Matrix((x,y,z)).transposed().to_4x4()
    m.translation=a
    return m

def make_body(root, C, samples, ident):
    source,groups,joints=load_anatomy(root,ident)
    # MakeHuman X=left, Y=up, Z=forward -> boat X=back, Y=up, Z=left.
    convert=lambda p:Vector((-p.z,p.y,p.x))
    jp=lambda name:convert(joints['joint-'+name])
    src={}; dst={}
    pelvis=(jp('l-upper-leg')+jp('r-upper-leg'))*.5
    neck=jp('neck')
    # The source pelvis and torso use the same vertical axis. Separate skin
    # weights produce the hip hinge without exposing either thigh root.
    for name,start,end in [('pelvis',pelvis,pelvis+Vector((0,1,0))),
                           ('torso',pelvis,neck),('head',neck,neck+Vector((0,2.5,0)))]:
        src[name]=frame(start,end)
    hip=Vector((0,.415,0))
    dst['pelvis']=frame(hip,hip+Vector((0,.12,0)))
    dst['torso']=frame(hip+Vector((0,.10,0)),hip+Vector((0,.61,0)))
    dst['head']=frame(hip+Vector((0,.61,0)),hip+Vector((0,.91,0)))
    maps={}
    # Source-body coordinate maps keep the chest and pelvis continuous.
    body_scale=Matrix.Diagonal((.104,.61/(neck.y-pelvis.y),.115,1))
    body_map=Matrix.Translation(hip) @ body_scale @ Matrix.Translation(-pelvis)
    maps['pelvis']=body_map;maps['torso']=body_map;maps['head']=body_map
    for sd,k,label in [(1,'L','l'),(-1,'R','r')]:
        h=jp(label+'-upper-leg'); knee=jp(label+'-knee'); ankle=jp(label+'-ankle')
        shoulder=jp(label+'-shoulder'); elbow=jp(label+'-elbow'); wrist=jp(label+'-hand')
        dh=hip+Vector((0,0,sd*.105))
        ds=hip+Vector((0,.56,sd*.185))
        dk=dh+(knee-h).normalized()*.45
        da=dk+(ankle-knee).normalized()*.44
        de=ds+(elbow-shoulder).normalized()*.34
        dw=de+(wrist-elbow).normalized()*.34
        leg_hinge=(knee-h).cross(ankle-knee).normalized()
        arm_hinge=-(elbow-shoulder).cross(wrist-elbow).normalized()
        for name,a,b,ta,tb,radial in [
            ('thigh',h,knee,dh,dk,.085),('shin',knee,ankle,dk,da,.092),
            ('upperArm',shoulder,elbow,ds,de,.095),('forearm',elbow,wrist,de,dw,.093)]:
            bone=name+k
            hinge=leg_hinge if name in ('thigh','shin') else arm_hinge
            src[bone]=frame(a,b,hinge);dst[bone]=frame(ta,tb,hinge)
            scale=Matrix.Diagonal((radial,(tb-ta).length/(b-a).length,radial,1))
            maps[bone]=dst[bone] @ scale @ src[bone].inverted()
        # Remaining pieces are authored bone-local (hands, shoes, head).
        dst['foot'+k]=frame(da,da+Vector((-.10,.14,0)))
        grip=samples[0]['bones']['grip'+k]
        x,y,z,w=grip['q']
        from mathutils import Quaternion
        dst['grip'+k]=Quaternion((w,x,y,z)).to_matrix().to_4x4()
        dst['grip'+k].translation=Vector(grip['a'])

    raw=json.loads((root/'art/source/default_weights.mhw').read_text())['weights']
    weights=[{} for _ in source]
    def bone_name(name):
        k=name[-1]
        if name.startswith('upperarm'): return 'upperArm'+k
        if name.startswith('lowerarm'): return 'forearm'+k
        if name.startswith('upperleg'): return 'thigh'+k
        if name.startswith('lowerleg'): return 'shin'+k
        if name.startswith(('pelvis','root','spine04','spine05')): return 'pelvis'
        if name.startswith(('spine','breast','clavicle','shoulder')): return 'torso'
        if name.startswith(('head','jaw','neck','levator','oculi','orbicularis','oris','risorius','special')): return 'head'
        return None
    for name,entries in raw.items():
        mapped=bone_name(name)
        if mapped:
            for i,w in entries: weights[i][mapped]=weights[i].get(mapped,0)+w
    for ws in weights:
        total=sum(ws.values())
        if total:
            for k in ws: ws[k]/=total

    # Anchor the posterior sitting pads to the pelvis. Standing-body thigh
    # weights otherwise lift the buttocks when the knees come up to the catch.
    contact=[]
    for i,p in enumerate(source):
        pad=(1-smooth(-.10,.40,p.y))*(1-smooth(-.25,.15,p.z))*(1-smooth(.95,1.35,abs(p.x)))
        pad*=smooth(-1.50,-1.05,p.y)
        contact.append(pad)
        if pad and weights[i]:
            weights[i]={b:w*(1-pad) for b,w in weights[i].items()}
            weights[i]['pelvis']=weights[i].get('pelvis',0)+pad
    seat_top=json.loads((root/'art/characters/rig-layout.json').read_text())['seat']['top']
    # Keep the continuous body and head; hands and shoes are authored for the grips and stretcher.
    keep=set()
    for i,p in enumerate(source):
        if not weights[i]: continue
        k='L' if p.x>0 else 'R'
        limb_weight=sum(w for b,w in weights[i].items() if b.startswith(('upperArm','forearm')))
        foot_weight=sum(w for b,w in weights[i].items() if b.startswith('shin'))
        if limb_weight>.5:
            local=src['forearm'+k].inverted() @ convert(p)
            length=(jp(('l' if k=='L' else 'r')+'-hand')-jp(('l' if k=='L' else 'r')+'-elbow')).length
            if local.y>length-.10: continue
        if foot_weight>.5 and p.y<joints['joint-l-ankle'].y+.10: continue
        keep.add(i)
    polys=[f for f in groups['body'] if all(i in keep for i in f)]
    ids=sorted(set(i for f in polys for i in f));index={old:new for new,old in enumerate(ids)}
    positions=[]; vertex_weights=[]
    for i in ids:
        p=convert(source[i]);ws=weights[i]
        point=sum((w*(maps[b]@p) for b,w in ws.items()),Vector())
        # A broad flattened contact patch, with a soft transition to the hips.
        if contact[i]:
            seated=max(seat_top+.0004,point.y-.026)
            point.y+=(seated-point.y)*contact[i]
        positions.append(C @ point)
        vertex_weights.append(ws)
    # Split the clothing boundaries through the topology. Interpolating the
    # positions and weights at each cut keeps clean hems continuous when posed.
    vertices=[(source[i],positions[n],vertex_weights[n]) for n,i in enumerate(ids)]
    def lerp(a,b,t):
        sa,pa,wa=a;sb,pb,wb=b
        keys=wa.keys()|wb.keys()
        return (sa.lerp(sb,t),pa.lerp(pb,t),{k:wa.get(k,0)*(1-t)+wb.get(k,0)*t for k in keys})
    def split(poly,field):
        positive=[];negative=[]
        for a,b in zip(poly,poly[1:]+poly[:1]):
            fa,fb=field(a),field(b)
            (positive if fa>=0 else negative).append(a)
            if (fa>=0)!=(fb>=0):
                v=lerp(a,b,fa/(fa-fb));positive.append(v);negative.append(v)
        return positive,negative
    result=[]
    def add(poly,color):
        if len(poly)>=3:result.append((poly,color))
    for face in polys:
        poly=[vertices[index[i]] for i in face]
        # Shorts meet the vest at the waist and finish above the knee.
        upper,lower=split(poly,lambda v:v[0].y-1.0)
        shorts,legs=split(lower,lambda v:v[0].y+1.65)
        add(shorts,'shorts');add(legs,'skin')
        # A clean underarm cut meets the neckline and straps. The back is
        # slightly higher, while the lower vest covers the whole waist.
        clothed,arm=split(upper,lambda v:min(1.30-.20*math.exp(-((v[0].y-4.30)/.50)**2)+max(0,3.5-v[0].y)*2-abs(v[0].x),.50-sum(w for b,w in v[2].items() if b.startswith(('upperArm','forearm')))))
        add(arm,'skin')
        def neckline(v):
            p=v[0]
            if ident=='june':
                # A broad scoop with narrower straps, as in the concept.
                return min(5.27,4.30+1.55*(abs(p.x)/.87)**4+(.38 if p.z<.1 else 0))-p.y
            return min(5.53,4.30+3.0*(abs(p.x)/.80)**4 + (.25 if p.z<.1 else 0))-p.y
        shirt,exposed=split(clothed,neckline)
        add(exposed,'skin')
        above,below=split(shirt,lambda v:v[0].y-3.78)
        stripe,top=split(above,lambda v:4.0-v[0].y)
        add(below,'shirt');add(stripe,'cream');add(top,'shirt')
    # Weld shared cut points, including their interpolated skin weights.
    positions=[];vertex_weights=[];source_points=[];faces=[];colors=[];lookup={}
    for poly,color in result:
        face=[]
        for source_p,p,ws in poly:
            key=tuple(round(x,7) for x in p)
            if key not in lookup:
                lookup[key]=len(positions);positions.append(p);vertex_weights.append(ws);source_points.append(source_p)
            face.append(lookup[key])
        if len(set(face))>=3: faces.append(face);colors.append(color)
    return positions,faces,colors,vertex_weights,{k:C@m for k,m in dst.items()},source_points
