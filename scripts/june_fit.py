"""Stitch the reconstructed limbs to the rowing garment and closed grips."""
import math
import json
from pathlib import Path
import bpy
import bmesh
from mathutils import Matrix,Vector,Quaternion
from june_garment import tailor

def pose_matrix(sample,C):
    x,y,z,w=sample['q']
    matrix=Quaternion((w,x,y,z)).to_matrix().to_4x4()
    matrix.translation=Vector(sample['a'])
    return C@matrix

def boundary_loops(obj):
    bm=bmesh.new();bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    deform=bm.verts.layers.deform.active
    names={g.index:g.name for g in obj.vertex_groups}
    seen=set();loops=[]
    for seed in {v for e in bm.edges if e.is_boundary for v in e.verts}:
        if seed in seen:continue
        stack=[seed];loop=[]
        while stack:
            vertex=stack.pop()
            if vertex in seen:continue
            seen.add(vertex)
            weights={names[i]:w for i,w in vertex[deform].items() if w>1e-6}
            loop.append((vertex.co.copy(),weights))
            stack.extend(e.other_vert(vertex) for e in vertex.link_edges if e.is_boundary)
        loops.append(loop)
    bm.free()
    return loops

def stitch(name,first,second,frame,skin_matrices,material):
    """Retain every boundary vertex and its skin weights when joining loops."""
    def posed(item):
        p,weights=item
        return sum((w*(skin_matrices[b]@p) for b,w in weights.items()),Vector())
    inverse=frame.inverted()
    def angle(item):
        p=inverse@posed(item)
        return math.atan2(p.z,p.x)%math.tau
    first=sorted(first,key=angle);second=sorted(second,key=angle)
    points=first+second;na=len(first);nb=len(second)
    a=[angle(p) for p in first];b=[angle(p) for p in second]
    faces=[];i=j=0
    while i<na or j<nb:
        next_a=a[(i+1)%na]+(math.tau if i+1>=na else 0) if i<na else math.inf
        next_b=b[(j+1)%nb]+(math.tau if j+1>=nb else 0) if j<nb else math.inf
        if next_a<next_b:
            faces.append([i%na,(i+1)%na,na+j%nb]);i+=1
        else:
            faces.append([i%na,na+(j+1)%nb,na+j%nb]);j+=1
    world=[posed(p) for p in points]
    for face in faces:
        p,q,r=[world[i] for i in face]
        centre=inverse@((p+q+r)/3)
        radial=frame.to_3x3()@Vector((centre.x,0,centre.z))
        if (q-p).cross(r-p).dot(radial)<0:face.reverse()
    data=bpy.data.meshes.new(name);data.from_pydata([p for p,_ in points],[],faces);data.update()
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
    data.materials.append(material)
    for bone in {bone for _,weights in points for bone in weights}:obj.vertex_groups.new(name=bone)
    for i,(_,weights) in enumerate(points):
        for bone,w in weights.items():obj.vertex_groups[bone].add([i],w,'REPLACE')
    for polygon in data.polygons:polygon.use_smooth=True
    # These strips are fitted in the catch pose. Derive their lighting there,
    # then unpose the normals; bind-pose normals make the waistband look hollow.
    normals=[Vector() for _ in points]
    for face in faces:
        p,q,r=[world[i] for i in face];normal=(q-p).cross(r-p)
        for i in face:normals[i]+=normal
    rest_normals=[]
    for i,(normal,(_,weights)) in enumerate(zip(normals,points)):
        if name=='Fitted waistband':
            radial=frame.inverted()@world[i]
            normal=frame.to_3x3()@Vector((radial.x,0,radial.z)).normalized()
        transform=sum((skin_matrices[b].to_3x3()*w for b,w in weights.items()),Matrix(((0,0,0),(0,0,0),(0,0,0))))
        rest_normals.append((transform.inverted()@normal.normalized()).normalized())
    data.normals_split_custom_set([rest_normals[loop.vertex_index] for loop in data.loops])
    return obj

def cut_limb(bm,selector,point,normal):
    verts={v for v in bm.verts if selector(v.co)}
    edges=[e for e in bm.edges if all(v in verts for v in e.verts)]
    faces=[f for f in bm.faces if all(v in verts for v in f.verts)]
    bmesh.ops.bisect_plane(bm,geom=list(verts)+edges+faces,dist=1e-7,
                          plane_co=point,plane_no=normal,clear_outer=True)
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')

def connect_limbs(parts,shorts,target,samples,C,material):
    matrices={bone:pose_matrix(samples[0]['bones'][bone.removeprefix('shorts_')],C)@rest.inverted()
              for bone,rest in target.items()}
    skin=next(obj for obj in parts if obj.name=='Skin')
    skin_loops=boundary_loops(skin)
    garment_loops=boundary_loops(shorts)
    additions=[]
    binding=next(obj for obj in parts if obj.name=='Singlet binding')
    hem=min(boundary_loops(binding),key=lambda loop:sum((C.inverted()@p).y for p,_ in loop)/len(loop))
    waist=max(garment_loops,key=lambda loop:sum((C.inverted()@p).y for p,_ in loop)/len(loop))
    bindings=[(waist,hem,pose_matrix(samples[0]['bones']['pelvis'],C),.004)]
    for side,k in [(1,'L'),(-1,'R')]:
        thigh='thigh'+k
        leg=[loop for loop in skin_loops if len(loop)>8 and all(w.get(thigh,0)>.99 for _,w in loop)]
        cuff=[loop for loop in garment_loops if all((target['shorts_'+thigh].inverted()@p).y>.10 for p,_ in loop)
              and sum((C.inverted()@p).z for p,_ in loop)*side>0]
        assert len(leg)==len(cuff)==1,f'Expected one thigh and cuff boundary: {k}'
        bindings.append((cuff[0],leg[0],pose_matrix(samples[0]['bones'][thigh],C),.004))
    tailor(shorts,bindings,matrices,C,.3175)
    garment_loops=boundary_loops(shorts)
    waist=max(garment_loops,key=lambda loop:sum((C.inverted()@p).y for p,_ in loop)/len(loop))
    additions.append(stitch('Fitted waistband',waist,hem,pose_matrix(samples[0]['bones']['pelvis'],C),matrices,shorts.data.materials[0]))
    fitted_pairs=[('waist',waist,hem,'pelvis')]
    for side,k in [(1,'L'),(-1,'R')]:
        thigh='thigh'+k
        # The fitted cuff follows the actual thigh outline. The small trim
        # bridges both loops without overlapping hidden skin underneath.
        leg=[loop for loop in skin_loops if len(loop)>8 and all(w.get(thigh,0)>.99 for _,w in loop)]
        assert len(leg)==1,f'Expected one exposed thigh boundary: {k}, {len(leg)}'
        cuff=[loop for loop in garment_loops if all(w.get(thigh,0)>.99 for _,w in loop)]
        assert len(cuff)==1,f'Expected one garment cuff: {k}'
        fitted_pairs.append(('cuff '+k,cuff[0],leg[0],thigh))
        additions.append(stitch('Tailored cuff '+k,cuff[0],leg[0],pose_matrix(samples[0]['bones'][thigh],C),matrices,shorts.data.materials[0]))
        forearm='forearm'+k;grip='grip'+k
        wrist=[loop for loop in skin_loops if len(loop)>5 and all(w.get(forearm,0)>.99 for _,w in loop)]
        assert len(wrist)==1,f'Expected one wrist boundary: {k}, {len(wrist)}'
        # This ellipse lies just inside the top of the closed palm. Its last
        # ring follows the grip while the first shares the forearm cut exactly.
        palm=[]
        for i in range(32):
            a=math.tau*i/32
            p=target[grip]@Vector((side*.035+.022*math.cos(a),.050,.030*math.sin(a)))
            palm.append((p,{grip:1}))
        additions.append(stitch('Wrist join '+k,wrist[0],palm,pose_matrix(samples[0]['bones'][grip],C),matrices,material))
    # Measure the actual skinned garment openings against the skin outlines,
    # including intermediate poses. A wide or displaced cuff fails this check.
    report=[]
    def posed(loop,transforms):
        return [sum((w*(transforms[b]@p) for b,w in weights.items()),Vector()) for p,weights in loop]
    for name,garment,body,bone in fitted_pairs:
        inverse=pose_matrix(samples[0]['bones'][bone],C).inverted()
        points=[inverse@p for p in posed(body,matrices)]
        centre=sum(points,Vector())/len(points)
        order=sorted(range(len(body)),key=lambda i:math.atan2(points[i].z-centre.z,points[i].x-centre.x))
        body=[body[i] for i in order];maximum=0
        for sample in samples[::15]:
            transforms={b:pose_matrix(sample['bones'][b.removeprefix('shorts_')],C)@rest.inverted() for b,rest in target.items()}
            ring=posed(body,transforms)
            for p in posed(garment,transforms):
                distances=[]
                for a,b in zip(ring,ring[1:]+ring[:1]):
                    edge=b-a;t=max(0,min(1,(p-a).dot(edge)/max(edge.length_squared,1e-14)))
                    distances.append((p-a-edge*t).length)
                maximum=max(maximum,min(distances))
        assert maximum<.007,f'{name} has a garment/skin step: {maximum} m'
        report.append({'opening':name,'poses':len(samples[::15]),'maximumBoundaryDistance':maximum})
    path=Path(__file__).resolve().parents[1]/'validation/reconstruction/june-final/garment-fit.json'
    path.write_text(json.dumps(report,indent=2)+'\n')
    print('GARMENT_FIT',report,flush=True)
    return additions
