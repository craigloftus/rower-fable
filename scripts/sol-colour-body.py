"""Restore Sol's reference palette on the closed body, using source garment borders."""
from pathlib import Path
import json
import numpy as np
import trimesh
from scipy.spatial import cKDTree
from trimesh.visual.material import PBRMaterial
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'validation/characters/sol'
mesh=trimesh.load(OUT/'refined-body.ply')
data=np.load(OUT/'body-colour-samples.npz');samples=data['colors'].astype(float);tree=cKDTree(data['positions'])
palette={'Skin':[193,142,86],'Swept black hair':[45,44,39],'Mustard singlet':[221,174,51],
 'Cream stripe':[239,226,190],'Charcoal shorts':[55,57,55],'Ivory shoes':[228,218,191],'Shoe soles':[54,54,47]}
parts={name:[] for name in palette}
def split(poly,values):
    inside=[];outside=[]
    for i,a in enumerate(poly):
        b=poly[(i+1)%len(poly)];da=values[i];db=values[(i+1)%len(poly)]
        (inside if da<=0 else outside).append(a)
        if (da<=0)!=(db<=0):
            p=a+(b-a)*da/(da-db);inside.append(p);outside.append(p)
    return np.asarray(inside),np.asarray(outside)
def partition(polys,fields,name):
    remainder=[]
    for field in fields:
        keep=[]
        for poly in polys:
            a,b=split(poly,field(poly))
            if len(a)>=3:keep.append(a)
            if len(b)>=3:remainder.append(b)
        polys=keep
    parts[name].extend(polys)
    return remainder

def source_colors(p):
 distance,ids=tree.query(p,k=12);weights=1/np.maximum(distance,.001)**2
 return (samples[ids]*weights[:,:,None]).sum(axis=1)/weights.sum(axis=1)[:,None]
def hem(p):
 x,y,z=p.T
 back=1-np.clip((z+.015)/.07,0,1)
 return .077+.012*(abs(x)/.10)**2+.010*back
def shirt(p):
 x,y,z=p.T
 front=np.clip((z+.035)/.075,0,1);front=front*front*(3-2*front)
 collar=(.302+.025*(abs(x)/.07)**2)*(1-front)+(.265+.062*(abs(x)/.07)**2)*front
 width=.092-.026*np.exp(-((y-.268)/.057)**2)
 return np.maximum.reduce([abs(x)-width,y-collar,hem(p)-y,y-.321])
polys=list(mesh.triangles)
polys=partition(polys,[shirt],'Mustard singlet')
parts['Mustard singlet']=partition(parts['Mustard singlet'],[lambda p:.200-p[:,1],lambda p:p[:,1]-.220,lambda p:.025-p[:,2]],'Cream stripe')
polys=partition(polys,[lambda p:p[:,1]-hem(p),lambda p:-.107+.075*p[:,0]-p[:,1],lambda p:abs(p[:,0])-(.130-.048*np.clip((p[:,1]+.01)/.12,0,1))],'Charcoal shorts')
polys=partition(polys,[lambda p:p[:,1]+.419],'Ivory shoes')
parts['Ivory shoes']=partition(parts['Ivory shoes'],[lambda p:p[:,1]+.476],'Shoe soles')
polys=partition(polys,[lambda p:(source_colors(p)[:,0]-70)/1000,lambda p:.345-p[:,1]],'Swept black hair')
parts['Skin'].extend(polys)
# Insert all cut-edge points into neighboring faces before triangulation.
points=np.unique(np.round(np.concatenate([p for polys in parts.values() for p in polys]),8),axis=0)
edge_tree=cKDTree(points);cache={}
def between(a,b):
    key=(tuple(np.round(a,8)),tuple(np.round(b,8)))
    if key in cache:return cache[key]
    d=b-a;length=np.dot(d,d)
    if length<1e-16:return []
    candidates=points[edge_tree.query_ball_point((a+b)/2,np.sqrt(length)/2+1e-7)]
    t=(candidates-a)@d/length;gap=np.linalg.norm(candidates-(a+t[:,None]*d),axis=1)
    mask=(t>1e-6)&(t<1-1e-6)&(gap<1e-7)&(np.linalg.norm(candidates-a,axis=1)>2e-7)&(np.linalg.norm(candidates-b,axis=1)>2e-7)
    result=candidates[mask][np.argsort(t[mask])]
    cache[key]=result;cache[(key[1],key[0])]=result[::-1];return result
scene=trimesh.Scene();counts={}
for name,polys in parts.items():
    if not polys:continue
    vertices=[];faces=[]
    for poly in polys:
        outline=[]
        for a,b in zip(poly,np.roll(poly,-1,axis=0)):
            outline.append(a);outline.extend(between(a,b))
        start=len(vertices);vertices.extend(outline)
        if len(outline)==3:
            faces.append([start,start+1,start+2]);continue
        vertices.append(np.mean(poly,axis=0));center=len(vertices)-1
        for i in range(len(outline)):
            a=start+i;b=start+(i+1)%len(outline)
            if np.linalg.norm(np.cross(vertices[a]-vertices[center],vertices[b]-vertices[center]))>1e-13:faces.append([a,b,center])
    color=np.asarray(palette[name])/255;color=np.where(color<=.04045,color/12.92,((color+.055)/1.055)**2.4)
    material=PBRMaterial(name=name,baseColorFactor=np.r_[np.round(color*255),255].astype(np.uint8),metallicFactor=0,roughnessFactor=.3 if name in ('Iris','Pupil','Eye ivory') else .9)
    part=trimesh.Trimesh(vertices,faces,process=True)
    part.visual=trimesh.visual.TextureVisuals(uv=np.zeros((len(part.vertices),2)),material=material)
    scene.add_geometry(part,geom_name=name);counts[name]=len(part.faces)
scene.export(OUT/'body-colour.glb',include_normals=True)
(OUT/'body-palette.json').write_text(json.dumps({'palette':palette,'triangles':counts,'totalTriangles':sum(counts.values())},indent=2)+'\n')
print(counts,flush=True)
