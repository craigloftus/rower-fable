"""Restore Sol's reference palette on the closed body, using source garment borders."""
from pathlib import Path
import json,sys
import numpy as np
import trimesh
from scipy.spatial import cKDTree
from trimesh.visual.material import PBRMaterial
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'validation/characters/sol'
MASTER=ROOT/'art/characters/candidates/sol'
mesh=trimesh.load(OUT/'assembled-surface.ply')
placement=json.loads((OUT/'head-placement.json').read_text());head_scale=placement['scale'];head_offset=np.asarray(placement['translation'])
pack='--pack-layout' in sys.argv
data=np.load(OUT/('head-colour-samples.npz' if pack else 'head-colour-layout.npz'));queried=[]
samples=data['colors'].astype(float);tree=cKDTree(data['positions']*head_scale+head_offset)
def head_points(p):return (p-head_offset)/head_scale
palette={'Skin':[193,142,86],'Swept black hair':[45,44,39],'Mustard singlet':[221,174,51],
 'Cream stripe':[239,226,190],'Charcoal shorts':[55,57,55],'Ivory shoes':[228,218,191],'Shoe soles':[54,54,47],'Shoe straps':[242,229,198],'Brows':[53,43,30],'Eye ivory':[230,218,190],'Iris':[76,50,25],'Pupil':[12,10,8],'Upper lid':[98,60,32],'Mouth':[142,91,50],'Lips':[177,112,61]}
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
 distance,ids=tree.query(p,k=12)
 if pack:queried.extend(ids.ravel())
 weights=1/np.maximum(distance,.001)**2
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
def hair(p):
 q=head_points(p);x,y,z=q.T;r=source_colors(p)[:,0]
 return np.maximum.reduce([(r-105)/1200,-.32-y,np.minimum.reduce([.14-y,z-.14,.215-abs(x)])])
polys=partition(polys,[hair],'Swept black hair')
def brow(p):
 q=head_points(p);x,y,z=q.T;r=source_colors(p)[:,0]
 return np.maximum.reduce([(r-80)/1200,.10-y,y-.18,.03-abs(x-.011),abs(x-.011)-.21,.18-z])
polys=partition(polys,[brow],'Brows')
def ocular_surface(polys,cx,cy):
    half=.061*head_scale
    def arc(p):return np.maximum(0,1-((p[:,0]-cx)/half)**2)**.65
    fields=[lambda p:cx-half-p[:,0],lambda p:p[:,0]-cx-half,
        lambda p:p[:,1]-cy-.030*head_scale*arc(p)**.7,lambda p:cy-.021*head_scale*arc(p)-p[:,1],lambda p:head_offset[2]+.16*head_scale-p[:,2]]
    parts['Socket']=[];remaining=partition(polys,fields,'Socket');removed=parts.pop('Socket')
    edges={};points={}
    for poly in removed:
        for a,b in zip(poly,np.roll(poly,-1,axis=0)):
            ka=tuple(np.round(a,7));kb=tuple(np.round(b,7));key=tuple(sorted((ka,kb)))
            edges[key]=edges.get(key,0)+1;points[ka]=a;points[kb]=b
    boundary={key for edge,count in edges.items() if count==1 for key in edge}
    rim=np.asarray([points[k] for k in boundary])
    angles=np.arctan2((rim[:,1]-cy)/(.027*head_scale),(rim[:,0]-cx)/half)
    rim=rim[np.argsort(angles)];centre=np.array([cx,cy,np.quantile(rim[:,2],.45)+.004*head_scale])
    globe_radius=.068*head_scale
    globe_centres.append(centre-np.array([0,0,globe_radius]))
    rings=[]
    for radius in [1,.94,.84,.65,.45,.30,.18,.08]:
        ring=centre+(rim-centre)*radius
        radial=np.sum((ring[:,:2]-centre[:2])**2,axis=1)
        sphere=centre[2]-globe_radius+np.sqrt(np.maximum(globe_radius**2-radial,0))
        if radius<1:ring[:,2]=sphere+head_scale*(.004 if radius==.94 else .0015 if radius==.84 else 0)
        rings.append(ring)
    eye=[]
    for j in range(len(rings)-1):
        for i in range(len(rim)):
            n=(i+1)%len(rim)
            for ids in [(rings[j][i],rings[j][n],rings[j+1][n]),(rings[j][i],rings[j+1][n],rings[j+1][i])]:
                poly=np.asarray(ids)
                if np.cross(poly[1]-poly[0],poly[2]-poly[0])[2]<0:poly=poly[::-1]
                if j<2:parts['Upper lid' if j==1 and poly.mean(axis=0)[1]>cy else 'Skin'].append(poly)
                else:eye.append(poly)
    for i in range(len(rim)):
        poly=np.array([rings[-1][i],rings[-1][(i+1)%len(rim)],centre])
        if np.cross(poly[1]-poly[0],poly[2]-poly[0])[2]<0:poly=poly[::-1]
        eye.append(poly)
    # Clip iris and pupil colour onto the same convex eye, with no fixed glint.
    iris_field=lambda p:((p[:,0]-cx+.002*head_scale)/(.027*head_scale))**2+((p[:,1]-cy-.013*head_scale)/(.027*head_scale))**2-1
    parts['Iris temp']=[];white=partition(eye,[iris_field],'Iris temp')
    colored=parts.pop('Iris temp')
    pupil=lambda p:((p[:,0]-cx+.002*head_scale)/(.011*head_scale))**2+((p[:,1]-cy-.013*head_scale)/(.011*head_scale))**2-1
    parts['Iris'].extend(partition(colored,[pupil],'Pupil'));parts['Eye ivory'].extend(white)
    return remaining
globe_centres=[]
for x in [-.090,.108]:
 cx=x*head_scale+head_offset[0];cy=.050*head_scale+head_offset[1]
 polys=ocular_surface(polys,cx,cy)
def mouth_y(p):
 q=head_points(p);return -.166+.008*((q[:,0]-.011)/.077)**2
mouth_fields=[lambda p:-.066-head_points(p)[:,0],lambda p:head_points(p)[:,0]-.088,
 lambda p:head_points(p)[:,1]-mouth_y(p)-.0011,
 lambda p:mouth_y(p)-.0011-head_points(p)[:,1],lambda p:.18-head_points(p)[:,2]]
polys=partition(polys,mouth_fields,'Mouth')
lip_fields=[lambda p:-.064-head_points(p)[:,0],lambda p:head_points(p)[:,0]-.086,
 lambda p:head_points(p)[:,1]-mouth_y(p)-.009*np.maximum(0,1-((head_points(p)[:,0]-.011)/.075)**2),
 lambda p:mouth_y(p)-.014*np.maximum(0,1-((head_points(p)[:,0]-.011)/.075)**2)-head_points(p)[:,1],
 lambda p:.18-head_points(p)[:,2]]
polys=partition(polys,lip_fields,'Lips')
parts['Skin'].extend(polys)
# Tiny isolated skin islands inside hair come from damaged source texels.
# Keep the connected face/ears/neck; recolour only fully enclosed speckles.
skin=parts['Skin'];parent=list(range(len(skin)));owners={}
def root(i):
 while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
 return i
for i,poly in enumerate(skin):
 for vertex in poly:
  key=tuple(np.round(vertex,7))
  if key in owners:parent[root(i)]=root(owners[key])
  else:owners[key]=i
groups={}
for i in range(len(skin)):groups.setdefault(root(i),[]).append(i)
recolour=set()
for ids in groups.values():
 points=np.concatenate([skin[i] for i in ids]);q=head_points(points)
 if len(ids)<70 and q[:,1].min()>-.32 and (q[:,1].mean()>.10 or q[:,2].mean()<.12):recolour.update(ids)
parts['Swept black hair'].extend(skin[i] for i in recolour)
parts['Skin']=[poly for i,poly in enumerate(skin) if i not in recolour]

# Shallow upper/lower lip volumes share the existing smiling seam and corners.
for polygons in parts.values():
 for poly in polygons:
  q=head_points(poly);u=(q[:,0]-.011)/.075;v=q[:,1]-mouth_y(poly)
  taper=np.maximum(0,1-u*u)**1.4;front=np.clip((q[:,2]-.18)/.06,0,1)
  upper=.008*np.exp(-((v-.006)/.006)**2);lower=.009*np.exp(-((v+.008)/.007)**2)
  crease=.002*np.exp(-(v/.0018)**2)
  poly[:,2]+=head_scale*taper*front*(upper+lower-crease)

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
    material=PBRMaterial(name=name,baseColorFactor=np.r_[np.round(color*255),255].astype(np.uint8),metallicFactor=0,roughnessFactor=.6 if name in ('Iris','Pupil','Eye ivory') else .9)
    part=trimesh.Trimesh(vertices,faces,process=True)
    part.update_faces(part.area_faces>1e-14);part.remove_unreferenced_vertices()
    if name in ('Eye ivory','Iris','Pupil'):
        centres=np.asarray(globe_centres);nearest=np.argmin(np.linalg.norm(part.vertices[:,None,:2]-centres[None,:,:2],axis=2),axis=1)
        normals=part.vertices-centres[nearest];normals/=np.linalg.norm(normals,axis=1)[:,None];part.vertex_normals=normals
    else:
        normals=part.vertex_normals[part.faces].reshape(-1,3).copy();part.unmerge_vertices()
        # Broad authored head planes get flat normals. Preserve body shading
        # until its source-form and joint review, blending only over the neck.
        flat=np.repeat(part.face_normals,3,axis=0)
        if part.vertices[:,1].min()>.335:part.vertex_normals=flat
        else:
            smooth=normals;t=np.clip((part.vertices[:,1]-.325)/.02,0,1)
            blended=smooth*(1-t[:,None])+flat*t[:,None];blended/=np.linalg.norm(blended,axis=1)[:,None];part.vertex_normals=blended
    part.visual=trimesh.visual.TextureVisuals(uv=np.zeros((len(part.vertices),2)),material=material)
    scene.add_geometry(part,geom_name=name);counts[name]=len(part.faces)
def eye_specular(tree):
    tree.setdefault('extensionsUsed',[]).append('KHR_materials_specular')
    for material in tree['materials']:
        if material['name'] in ('Iris','Pupil'):
            material['extensions']={'KHR_materials_specular':{'specularFactor':.25}}
scene.export(MASTER/'standing.glb',include_normals=True,tree_postprocessor=eye_specular)
(OUT/'palette.json').write_text(json.dumps({'palette':palette,'triangles':counts,'totalTriangles':sum(counts.values())},indent=2)+'\n')
print(counts,flush=True)

if pack:
 keep=np.unique(queried)
 np.savez_compressed(OUT/'head-colour-layout.npz',positions=data['positions'][keep],colors=data['colors'][keep])
 print('Packed exact queried colour cloud:',len(keep),'samples',flush=True)
