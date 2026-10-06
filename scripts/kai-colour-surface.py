"""Cut Kai's reference kit into a single closed sculpt and remove baked lighting."""
from pathlib import Path
import json,sys
import numpy as np
import trimesh
from scipy.spatial import cKDTree
from trimesh.visual.material import PBRMaterial
from trimesh.visual.color import uv_to_color

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'validation/characters/kai';MASTER=ROOT/'art/characters/candidates/kai'
mesh=trimesh.load(OUT/'assembled-surface.ply')
placement=json.loads((OUT/'head-placement.json').read_text())
head_scale=placement['scale'];head_offset=np.asarray(placement['translation'])
pack='--pack-layout' in sys.argv
data=np.load(OUT/('head-colour-samples.npz' if pack else 'head-colour-layout.npz'))
queried=[]
samples=data['colors']
tree=cKDTree(data['positions']*head_scale+head_offset)
palette={'Skin':[171,115,69],'Black curls':[39,35,28],'Olive singlet':[99,109,64],
    'Cream stripe':[236,225,190],'Charcoal shorts':[54,55,51],'Ivory shoes':[221,215,194],
    'Shoe soles':[48,49,44],'Shoe straps':[236,227,205], 'Brows':[52,43,32],
    'Eye ivory':[232,220,191],'Iris':[97,66,32],'Pupil':[13,17,13],'Upper lid':[85,52,29],'Mouth':[113,72,44],'Lips':[160,101,62]}
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
def hem(p):return .073+.006*(abs(p[:,0])/.095)**2
def singlet(p):
    x,y,z=p.T
    front=np.clip((z+.045)/.06,0,1);front=front*front*(3-2*front)
    collar=(.291+.035*(abs(x)/.06)**2)*(1-front)+(.246+.070*(abs(x)/.073)**2)*front
    width=.095-.016*np.exp(-((y-.245)/.05)**2)+.012*np.clip((.17-y)/.1,0,1)
    return np.maximum.reduce([abs(x)-width,y-collar,hem(p)-y,y-.307])
def shorts(p):
    x,y,z=p.T
    return np.maximum.reduce([y-hem(p),-.106-.006*np.clip(abs(x)/.11,0,1)-y,abs(x)-.136])

polys=list(mesh.triangles)
polys=partition(polys,[singlet],'Olive singlet')
shirt=parts['Olive singlet'];parts['Olive singlet']=[]
parts['Olive singlet']=partition(shirt,[lambda p:.197-p[:,1],lambda p:p[:,1]-.216,lambda p:.018-p[:,2]],'Cream stripe')
polys=partition(polys,[shorts],'Charcoal shorts')
polys=partition(polys,[lambda p:p[:,1]+.438],'Ivory shoes')
shoes=parts['Ivory shoes'];parts['Ivory shoes']=[]
shoes=partition(shoes,[lambda p:p[:,1]+.489],'Shoe soles')
for z in [.006,.032]:
    shoes=partition(shoes,[lambda p,z=z:z-p[:,2],lambda p,z=z:p[:,2]-z-.010,lambda p:-.476-p[:,1]],'Shoe straps')
parts['Ivory shoes']=shoes
def head_points(p):return (p-head_offset)/head_scale
def source_colors(p):
    distance,ids=tree.query(p,k=5)
    if pack:queried.extend(ids.ravel())
    weights=1/np.maximum(distance,.0002)**2
    return (samples[ids]*weights[:,:,None]).sum(axis=1)/weights.sum(axis=1)[:,None]
def hair(p):
    q=head_points(p);x,y,z=q.T;r=source_colors(p)[:,0]
    return np.maximum.reduce([(r-70)/1200,-.11-y,np.minimum.reduce([.11-y,z-.01,.16-abs(x-.009)])])
polys=partition(polys,[hair],'Black curls')
def brow(p):
    q=head_points(p);x,y,z=q.T;r=source_colors(p)[:,0]
    return np.maximum.reduce([(r-70)/1200,.043-y,y-.11,.033-abs(x-.009),abs(x-.009)-.17,.1-z])
polys=partition(polys,[brow],'Brows')
# Restore each eye as a fitted convex surface with the original compact
# almond opening. The edge uses the exact cut skull loop, so it is connected.
def ocular_surface(polys,cx,cy):
    half=.0102
    def arc(p):return np.maximum(0,1-((p[:,0]-cx)/half)**2)**.65
    fields=[lambda p:cx-half-p[:,0],lambda p:p[:,0]-cx-half,
        lambda p:p[:,1]-cy-.0055*arc(p),lambda p:cy-.0039*arc(p)-p[:,1],lambda p:.040-p[:,2]]
    parts['Socket']=[];remaining=partition(polys,fields,'Socket');removed=parts.pop('Socket')
    edges={};points={}
    for poly in removed:
        for a,b in zip(poly,np.roll(poly,-1,axis=0)):
            ka=tuple(np.round(a,7));kb=tuple(np.round(b,7));key=tuple(sorted((ka,kb)))
            edges[key]=edges.get(key,0)+1;points[ka]=a;points[kb]=b
    boundary={key for edge,count in edges.items() if count==1 for key in edge}
    rim=np.asarray([points[k] for k in boundary])
    angles=np.arctan2((rim[:,1]-cy)/.0027,(rim[:,0]-cx)/half)
    rim=rim[np.argsort(angles)];centre=np.array([cx,cy,np.quantile(rim[:,2],.80)+.003])
    radius_globe=.0135
    globe_centres.append(np.array([cx,cy,centre[2]-radius_globe]))
    rings=[]
    for radius in [1,.94,.84,.65,.32]:
        ring=centre+(rim-centre)*radius
        radial=np.sum((ring[:,:2]-centre[:2])**2,axis=1)
        sphere=centre[2]-radius_globe+np.sqrt(np.maximum(radius_globe**2-radial,0))
        if radius<1:
            ring[:,2]=sphere+(.0010 if radius==.94 else .00035 if radius==.84 else 0)
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
    iris_field=lambda p:((p[:,0]-cx+.0005)/.0052)**2+((p[:,1]-cy-.0012)/.0052)**2-1
    parts['Iris temp']=[];white=partition(eye,[iris_field],'Iris temp')
    colored=parts.pop('Iris temp')
    pupil=lambda p:((p[:,0]-cx+.0005)/.0027)**2+((p[:,1]-cy-.0012)/.0027)**2-1
    parts['Iris'].extend(partition(colored,[pupil],'Pupil'));parts['Eye ivory'].extend(white)
    return remaining
globe_centres=[]
for cx,cy in [(-.0217,.4113),(.0268,.4118)]:polys=ocular_surface(polys,cx,cy)
def mouth_y(p):
    q=head_points(p);return -.153+.006*((q[:,0]-.009)/.075)**2
mouth_fields=[lambda p:-.066-head_points(p)[:,0],lambda p:head_points(p)[:,0]-.084,
    lambda p:head_points(p)[:,1]-mouth_y(p)-.0009,
    lambda p:mouth_y(p)-.0009-head_points(p)[:,1],lambda p:.12-head_points(p)[:,2]]
polys=partition(polys,mouth_fields,'Mouth')
lip_fields=[lambda p:-.064-head_points(p)[:,0],lambda p:head_points(p)[:,0]-.082,
    lambda p:head_points(p)[:,1]-mouth_y(p)-.008*np.maximum(0,1-((head_points(p)[:,0]-.009)/.073)**2),
    lambda p:mouth_y(p)-.013*np.maximum(0,1-((head_points(p)[:,0]-.009)/.073)**2)-head_points(p)[:,1],
    lambda p:.12-head_points(p)[:,2]]
polys=partition(polys,lip_fields,'Lips')
# Two isolated kit cuts landed on the inner upper arms. They are skin.
shirt=[]
for poly in parts['Olive singlet']:
    x,y,z=poly.mean(axis=0)
    if abs(x)>.087 and .185<y<.206 and abs(z)<.008:parts['Skin'].append(poly)
    else:shirt.append(poly)
parts['Olive singlet']=shirt
parts['Skin'].extend(polys)

# The source mouth keeps its restrained smile. Give each lip a shallow convex
# section on the same continuous surface, tapering to zero at both corners.
for name,polygons in parts.items():
    for poly in polygons:
        q=head_points(poly);u=(q[:,0]-.009)/.073;v=q[:,1]-mouth_y(poly)
        taper=np.maximum(0,1-u*u)**1.4
        front=np.clip((q[:,2]-.12)/.06,0,1)
        upper=.006*np.exp(-((v-.0055)/.0055)**2)
        lower=.007*np.exp(-((v+.0075)/.0065)**2)
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
    material=PBRMaterial(name=name,baseColorFactor=np.r_[np.round(color*255),255].astype(np.uint8),metallicFactor=0,roughnessFactor=.3 if name in ('Iris','Pupil','Eye ivory') else .9)
    part=trimesh.Trimesh(vertices,faces,process=True)
    if name in ('Eye ivory','Iris','Pupil'):
        centres=np.asarray(globe_centres);nearest=np.argmin(np.linalg.norm(part.vertices[:,None,:2]-centres[None,:,:2],axis=2),axis=1)
        normals=part.vertices-centres[nearest];normals/=np.linalg.norm(normals,axis=1)[:,None];part.vertex_normals=normals
    else:
        part.unmerge_vertices();part.vertex_normals=np.repeat(part.face_normals,3,axis=0)
    part.visual=trimesh.visual.TextureVisuals(uv=np.zeros((len(part.vertices),2)),material=material)
    scene.add_geometry(part,geom_name=name);counts[name]=len(part.faces)
scene.export(MASTER/'standing.glb',include_normals=True)
(OUT/'palette.json').write_text(json.dumps({'palette':palette,'triangles':counts,'totalTriangles':sum(counts.values())},indent=2)+'\n')
print(counts,flush=True)

if pack:
    keep=np.unique(queried)
    np.savez_compressed(OUT/'head-colour-layout.npz',positions=data['positions'][keep],colors=samples[keep])
    print('Packed exact colour layout:',len(keep),'samples',flush=True)
