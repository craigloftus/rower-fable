"""Join the approved June meshes at exact section loops, preserving source UVs."""
import numpy as np
import trimesh
from trimesh.visual.color import uv_to_color
from trimesh.visual.material import PBRMaterial


def linear(rgb):
    rgb=np.asarray(rgb)/255
    return np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)


def clip(mesh,height,above):
    vertices=list(mesh.vertices.copy());normals=list(mesh.vertex_normals.copy());uvs=list(mesh.visual.uv.copy())
    faces=[];segments=[];cuts={}
    def intersection(a,b):
        key=tuple(sorted((int(a),int(b))))
        if key not in cuts:
            t=(height-vertices[a][1])/(vertices[b][1]-vertices[a][1])
            point=vertices[a]*(1-t)+vertices[b]*t;point[1]=height
            cuts[key]=len(vertices);vertices.append(point)
            normals.append(normals[a]*(1-t)+normals[b]*t);uvs.append(uvs[a]*(1-t)+uvs[b]*t)
        return cuts[key]
    for face in mesh.faces:
        inside=[(vertices[i][1]>=height if above else vertices[i][1]<=height) for i in face]
        if all(inside):faces.append(face);continue
        if not any(inside):continue
        polygon=[];edge=[]
        for n,a in enumerate(face):
            b=face[(n+1)%3]
            if inside[n]:polygon.append(a)
            if inside[n]!=inside[(n+1)%3]:
                i=intersection(a,b);polygon.append(i);edge.append(i)
        faces.extend([[polygon[0],polygon[i],polygon[i+1]] for i in range(1,len(polygon)-1)])
        segments.append(edge)
    vertices=np.asarray(vertices);normals=np.asarray(normals);normals/=np.linalg.norm(normals,axis=1)[:,None]
    visual=trimesh.visual.TextureVisuals(uv=np.asarray(uvs),material=mesh.visual.material)
    result=trimesh.Trimesh(vertices,faces,vertex_normals=normals,visual=visual,process=False)
    records=[]
    for edge in segments:
        material=mesh.visual.material
        colours=linear(uv_to_color(np.asarray(uvs)[edge],material.baseColorTexture)[:,:3]) if material.baseColorTexture is not None else np.ones((2,3))
        if material.baseColorFactor is not None:colours*=material.baseColorFactor[:3]/255
        records.append([(vertices[i],normals[i],colour) for i,colour in zip(edge,colours)])
    result.remove_unreferenced_vertices()
    return result,records


def section_loops(segments):
    points={};adjacency={}
    for edge in segments:
        keys=[tuple(np.round(item[0],8)) for item in edge]
        for key,item in zip(keys,edge):
            points.setdefault(key,[]).append(item)
        if keys[0]==keys[1]:continue
        for a,b in [keys,keys[::-1]]:adjacency.setdefault(a,set()).add(b)
    loops=[];unvisited=set(adjacency)
    while unvisited:
        start=next(iter(unvisited));order=[];previous=None;current=start
        while current not in order:
            order.append(current);unvisited.discard(current)
            neighbours=adjacency[current]-{previous}
            assert neighbours,'Open source neck section'
            previous,current=current,next(iter(neighbours))
        assert current==start,'Branching source neck section'
        data=np.asarray([np.mean(points[key],axis=0) for key in order])
        p=data[:,0];area=abs(np.sum(p[:,0]*np.roll(p[:,2],-1)-np.roll(p[:,0],-1)*p[:,2]))/2
        loops.append((area,data))
    return [data for _,data in sorted(loops,key=lambda item:item[0],reverse=True)]


def bridge(bottom,top):
    centre=(bottom[:,0,[0,2]].mean(axis=0)+top[:,0,[0,2]].mean(axis=0))/2
    def ordered(data):
        angle=np.mod(np.arctan2(data[:,0,2]-centre[1],data[:,0,0]-centre[0]),2*np.pi)
        # Preserve the source edge order, including tiny concavities. Sorting
        # vertices by angle would silently replace edges at those concavities.
        direction=np.sum(np.angle(np.exp(1j*(np.roll(angle,-1)-angle))))
        if direction<0:data=data[::-1];angle=angle[::-1]
        start=np.argmin(angle)
        return np.roll(angle,-start),np.roll(data,-start,axis=0)
    ab,bottom=ordered(bottom);at,top=ordered(top)
    angles=np.arange(128)*2*np.pi/128
    def sample(a,data):
        return np.stack([np.interp(angles,a,data[:,j,k],period=2*np.pi) for j in range(3) for k in range(3)],axis=1).reshape(-1,3,3)
    lo=sample(ab,bottom);hi=sample(at,top);height=hi[0,0,1]-lo[0,0,1]
    def tangent(data):
        n=data[:,1];d=-n[:,1,None]*n[:,[0,2]]/np.sum(n[:,[0,2]]**2,axis=1)[:,None]
        return np.column_stack((d[:,0],np.ones(len(d)),d[:,1]))
    d0=tangent(lo);d1=tangent(hi)
    rings=[(ab,bottom)]
    for t in np.linspace(0,1,11)[1:-1]:
        p=(2*t**3-3*t*t+1)*lo[:,0]+(t**3-2*t*t+t)*height*d0+(-2*t**3+3*t*t)*hi[:,0]+(t**3-t*t)*height*d1
        normal=lo[:,1]*(1-t)+hi[:,1]*t
        colour=lo[:,2]*(1-(3*t*t-2*t**3))+hi[:,2]*(3*t*t-2*t**3)
        rings.append((angles,np.stack((p,normal,colour),axis=1)))
    rings.append((at,top));vertices=[];normals=[];colours=[];faces=[];offsets=[]
    for _,data in rings:
        offsets.append(len(vertices));vertices.extend(data[:,0]);normals.extend(data[:,1]);colours.extend(data[:,2])
    for r in range(len(rings)-1):
        aa,a=rings[r];bb,b=rings[r+1];na=len(a);nb=len(b);i=j=0
        while i<na or j<nb:
            ia=offsets[r]+i%na;ib=offsets[r+1]+j%nb
            nexta=aa[(i+1)%na]+(2*np.pi if i+1>=na else 0)-aa[0]
            nextb=bb[(j+1)%nb]+(2*np.pi if j+1>=nb else 0)-bb[0]
            if i<na and (j==nb or nexta<nextb):
                faces.append([ia,offsets[r]+(i+1)%na,ib]);i+=1
            else:faces.append([ia,offsets[r+1]+(j+1)%nb,ib]);j+=1
    vertices=np.asarray(vertices);faces=np.asarray(faces);normal=np.cross(vertices[faces[:,1]]-vertices[faces[:,0]],vertices[faces[:,2]]-vertices[faces[:,0]])
    radial=vertices[faces].mean(axis=1);radial[:,0]-=centre[0];radial[:,2]-=centre[1];radial[:,1]=0
    if np.median(np.sum(normal*radial,axis=1))<0:faces=faces[:,::-1]
    visual=trimesh.visual.TextureVisuals(uv=np.zeros((len(vertices),2)),material=PBRMaterial(name='June neck transition',baseColorFactor=[255,255,255,255],metallicFactor=0,roughnessFactor=.9))
    visual.vertex_attributes['color']=np.column_stack((np.round(np.clip(colours,0,1)*255).astype(np.uint8),np.full(len(vertices),255,dtype=np.uint8)))
    return trimesh.Trimesh(vertices,faces,vertex_normals=normals,visual=visual,process=False)
