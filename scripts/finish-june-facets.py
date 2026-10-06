"""Art-direct the rebuilt surface using the original June design.

All boundaries are cut through geometry. Clothing colours are unlit base
colours, skin/hair use a restrained palette, and eyes/lids/lips are authored
surface patches. There is no reconstruction texture in the exported mesh.
"""
from pathlib import Path
import json
import numpy as np
import trimesh
from scipy.spatial import cKDTree
from scipy.ndimage import gaussian_filter1d
from scipy.interpolate import PchipInterpolator
from trimesh.visual.color import uv_to_color
from trimesh.visual.material import PBRMaterial
from june_planes import SculptPlanes
from june_pattern import hem,singlet,shorts
from june_seams import conform

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'validation/reconstruction/june-final'
mesh=trimesh.load(OUT/'sculpt-surface.ply')
planes=SculptPlanes(mesh)
print('Sculpt planes:',planes.groups,flush=True)
source=trimesh.load(ROOT/'validation/reconstruction/trellis-assembled/mesh.glb')
head=source.geometry['Head']
hc=uv_to_color(head.visual.uv,head.visual.material.baseColorTexture)[:,:3].astype(float)
hp=head.vertices
hair_source=((hc[:,0]>hc[:,1]*1.38)&(hc[:,1]<112)&(hc[:,0]<190)).astype(float)
# Keep lashes, nostrils and eyebrows out of the hair region.
face_region=(hp[:,2]>.017)&(np.abs(hp[:,0])<.038)&(hp[:,1]<.404)
hair_source[face_region]=0
hair_source[hp[:,1]<.346]=0
kt=cKDTree(hp)
hairline=PchipInterpolator([-.050,-.040,-.026,-.009,.007,.025,.039,.050], [.383,.395,.408,.413,.411,.414,.399,.383])
side_hairline=PchipInterpolator([-.065,-.035,-.022,-.014,.004,.018,.030,.055], [.354,.354,.376,.402,.404,.397,.398,.414])

def hair_field(points):
    distance,ids=kt.query(points,k=12)
    weights=1/np.maximum(distance,.0003)**2
    value=np.sum(weights*hair_source[ids],axis=1)/weights.sum(axis=1)
    x,y,z=points.T
    front=np.clip((z-.016)/.014,0,1)
    value=(value-.5)*.012*(1-front)+(y-hairline(np.clip(x,-.05,.05)))*front
    side=np.clip((np.abs(x)-.027)/.012,0,1)*(1-np.clip((z-.018)/.014,0,1))
    value=value*(1-side)+(y-side_hairline(np.clip(z,-.065,.055)))*side
    back=np.clip((-.015-z)/.025,0,1)*(1-np.clip((np.abs(x)-.018)/.02,0,1))
    value=value*(1-back)+(y-.354)*back
    strand=(np.abs(x)>.040)&(z>.021)&(y>.344)&(y<.404)
    value[strand]=np.maximum(value[strand],.006)
    value[y>.433]=.010
    value[y<.347]=-.010
    return value

palette={
    'Skin': [207,151,113], 'Copper hair':[140,74,31],
    'Copper ridge':[161,78,30], 'Copper fold':[137,62,25],
    'Terracotta singlet':[177,89,57], 'Singlet binding':[155,73,45],
    'Cream stripe':[232,216,183], 'Charcoal shorts':[57,58,51],
    'Shorts stitching':[65,65,57], 'Ivory shoes':[218,210,186],
    'Shoe soles':[54,55,47], 'Shoe straps':[233,223,196],
    'Eye ivory':[237,225,199], 'Iris':[63,62,43], 'Pupil':[20,24,18],
    'Upper lash':[49,33,22], 'Lower lid':[174,116,78], 'Lid crease':[171,112,77],
    'Copper brows':[117,62,27], 'Upper lip':[173,104,71],
    'Lower lip':[197,131,91], 'Mouth crease':[117,75,48],
    'Freckles':[166,104,62], 'Nostril':[154,100,71],
}

def linear(rgb):
    c=np.asarray(rgb,dtype=float)/255
    return np.where(c<=.04045,c/12.92,((c+.055)/1.055)**2.4)

# Every polygon stores positions. Fields are evaluated on polygon corners and
# interpolated at an actual edge crossing, creating shared material boundaries.
def split(poly,values):
    inside=[];outside=[]
    for i,a in enumerate(poly):
        j=(i+1)%len(poly);b=poly[j];da=values[i];db=values[j]
        (inside if da<=0 else outside).append(a)
        if (da<=0)!=(db<=0):
            p=a+(b-a)*(da/(da-db));inside.append(p);outside.append(p)
    return inside,outside

parts={name:[] for name in palette}

def add(poly,name):
    if len(poly)>=3:parts[name].append(np.asarray(poly))

def partition(polys,field,inside_name):
    remainder=[]
    for poly in polys:
        values=field(np.asarray(poly))
        yes,no=split(poly,values)
        add(yes,inside_name)
        if len(no)>=3:remainder.append(np.asarray(no))
    return remainder

def partition_intersection(polys,fields,inside_name):
    """Clip each boundary separately: max(fields) is not linear along an edge."""
    remainder=[]
    for field in fields:
        clipped=[]
        for poly in polys:
            yes,no=split(poly,field(poly))
            if len(yes)>=3:clipped.append(np.asarray(yes))
            if len(no)>=3:remainder.append(np.asarray(no))
        polys=clipped
    for poly in polys:add(poly,inside_name)
    return remainder

p=mesh.vertices
def subdivide_seams(mesh,marked):
    """Split both sides of a refined edge so bending cannot open T-junctions."""
    vertices=list(mesh.vertices)
    split_edges={tuple(sorted((int(a),int(b)))) for tri in mesh.faces[marked] for a,b in zip(tri,np.roll(tri,-1))}
    midpoints={edge:len(vertices)+i for i,edge in enumerate(sorted(split_edges))}
    vertices.extend([(mesh.vertices[a]+mesh.vertices[b])/2 for a,b in sorted(split_edges)])
    faces=[]
    for tri in mesh.faces:
        polygon=[]
        for a,b in zip(tri,np.roll(tri,-1)):
            polygon.append(a)
            edge=tuple(sorted((int(a),int(b))))
            if edge in midpoints:polygon.append(midpoints[edge])
        if len(polygon)==3:faces.append(polygon);continue
        centre=len(vertices);vertices.append(mesh.vertices[tri].mean(axis=0))
        faces.extend([[a,b,centre] for a,b in zip(polygon,np.roll(polygon,-1))])
    return trimesh.Trimesh(vertices,faces,process=False)

# Resolve curved pattern borders locally, keeping subdivisions coplanar so
# this adds seam precision without creating additional visible facets.
for _ in range(1):
    tri=mesh.triangles
    scores=singlet(tri.reshape(-1,3)).reshape(-1,3)
    hems=shorts(tri.reshape(-1,3)).reshape(-1,3)
    marked=((scores.min(axis=1)<.002)&(scores.max(axis=1)>-.002))|((hems.min(axis=1)<.001)&(hems.max(axis=1)>-.001))
    mesh=subdivide_seams(mesh,marked)
# A second local cut pass resolves the scoop without scalloping its edge.
tri=mesh.triangles;scores=singlet(tri.reshape(-1,3)).reshape(-1,3)
centre=tri.mean(axis=1)
marked=(centre[:,1]>.25)&(centre[:,1]<.305)&(centre[:,2]>.015)&(np.abs(centre[:,0])<.055)&(scores.min(axis=1)<.001)&(scores.max(axis=1)>-.001)
mesh=subdivide_seams(mesh,marked)
p=mesh.vertices
body_faces=mesh.faces[np.mean(p[mesh.faces,1],axis=1)<.338]
head_faces=mesh.faces[np.mean(p[mesh.faces,1],axis=1)>=.338]
body=[tri for tri in p[body_faces]]
# Garment trims occupy the last millimetre inside the pattern, with common edges.
shirt_polys=[]
for poly in body:
    yes,no=split(poly,singlet(poly))
    if len(yes)>=3:shirt_polys.append(np.asarray(yes))
    if len(no)>=3:add(no,'Skin')
remaining=partition(shirt_polys,lambda p: -.0009-singlet(p),'Terracotta singlet')
for poly in remaining:add(poly,'Singlet binding')
# Stripe cuts the front of the singlet; separate the polygons already classified.
for name in ['Terracotta singlet','Singlet binding']:
    polys=parts[name];parts[name]=[]
    remainder=partition_intersection(polys,[lambda p:.200-p[:,1],lambda p:p[:,1]-.218,lambda p:.031-p[:,2]],'Cream stripe')
    for poly in remainder:add(poly,name)

skin=parts['Skin'];parts['Skin']=[]
skin=partition(skin,shorts,'Charcoal shorts')
skin=partition(skin,lambda p:p[:,1]+.447,'Ivory shoes')
for poly in skin:add(poly,'Skin')
shoes=parts['Ivory shoes'];parts['Ivory shoes']=[]
shoes=partition(shoes,lambda p:p[:,1]+.490,'Shoe soles')
# Two clean cream straps across the source shoe roof.
for z0 in [.003,.030]:
    shoes=partition(shoes,lambda p:np.maximum.reduce([z0-p[:,2],p[:,2]-(z0+.009),-.481-p[:,1]]),'Shoe straps')
for poly in shoes:add(poly,'Ivory shoes')

heads=[tri for tri in p[head_faces]]
heads=partition(heads,lambda p:-hair_field(p),'Copper hair')
for poly in heads:add(poly,'Skin')

# Replace the generated eye interiors with continuous convex eye surfaces.
# Leaving the reconstruction underneath causes its pupil bumps to poke through.
EYE_IN=.0115;EYE_WIDTH=.0215;EYE_UP=.0061;EYE_DOWN=.0037
def socket_field(p):
    x,y,z=p.T;t=np.clip((np.abs(x)-EYE_IN)/EYE_WIDTH,0,1)
    mid=.3847-.0006*t;arc=np.maximum(0,np.sin(np.pi*t))**.82
    return np.maximum.reduce([EYE_IN-np.abs(x),np.abs(x)-EYE_IN-EYE_WIDTH,
        y-(mid+EYE_UP*arc),mid-EYE_DOWN*arc-y,.027-z])
parts['Socket removed']=[]
parts['Skin']=partition(parts['Skin'],socket_field,'Socket removed')
parts.pop('Socket removed')

# The front projection uses the rebuilt mesh itself; details sit on the actual
# sculpt and stay attached to its shape, rather than floating in a picture plane.
ht=mesh.triangles[np.mean(mesh.triangles[:,:,1],axis=1)>.331]
lo=ht[:,:,:2].min(axis=1);hi=ht[:,:,:2].max(axis=1)
def project(x,y,offset=.00013):
    ids=np.flatnonzero((lo[:,0]<=x)&(hi[:,0]>=x)&(lo[:,1]<=y)&(hi[:,1]>=y))
    tris=ht[ids];a=tris[:,0,:2];b=tris[:,1,:2]-a;c=tris[:,2,:2]-a;d=np.array([x,y])-a
    det=b[:,0]*c[:,1]-b[:,1]*c[:,0]
    good=np.abs(det)>1e-14;tris=tris[good];b=b[good];c=c[good];d=d[good];det=det[good]
    u=(d[:,0]*c[:,1]-d[:,1]*c[:,0])/det
    v=(b[:,0]*d[:,1]-b[:,1]*d[:,0])/det
    good=(u>=-1e-6)&(v>=-1e-6)&(u+v<=1.000001)
    depth=tris[:,0,2]*(1-u-v)+tris[:,1,2]*u+tris[:,2,2]*v
    return np.array([x,y,depth[good].max()+offset])

# Restore the thin left temple lock from the approved head's measured sweep.
# Its very thin tip is below the volume repair's resolution.
lock=[]
for y in [.410,.402,.394,.386,.378,.370,.362,.354,.346]:
    mask=(hp[:,0]<-.035)&(hp[:,2]>.010)&(np.abs(hp[:,1]-y)<.004)&(hc[:,1]<90)&(hc[:,0]>hc[:,1]*1.5)
    if mask.any():lock.append(np.median(hp[mask],axis=0))
if len(lock)>3:
    rings=[]
    for i,q in enumerate(lock):
        width=.0047*(1-i/(len(lock)-1))**.75+.00008
        rings.append([q+np.array([a*width,0,b*width]) for a,b in [(-1,0),(0,.65),(1,0),(0,-.4)]])
    for a,b in zip(rings,rings[1:]):
        for j in range(4):add([a[j],b[j],b[(j+1)%4],a[(j+1)%4]],'Copper hair')
    add(rings[0][::-1],'Copper hair');add(rings[-1],'Copper hair')

eye_boundaries={}
def eye_project(x,y,offset=0):
    sign=1 if x>0 else -1;t=np.clip((abs(x)-EYE_IN)/EYE_WIDTH,0,1)
    mid=.3847-.0006*t;arc=max(0,np.sin(np.pi*t))**.82
    bottom=mid-EYE_DOWN*arc;top=mid+EYE_UP*arc
    v=np.clip((y-bottom)/max(top-bottom,1e-7),0,1)
    lower,upper=eye_boundaries[sign]
    z=np.interp(t,np.linspace(0,1,33),lower)*(1-v)+np.interp(t,np.linspace(0,1,33),upper)*v
    # The lid rim slopes forward in the guide. Give the eye a real convex dome
    # so its upper half can reflect an overhead light instead of facing down.
    z+=.0022*4*v*(1-v)*np.sin(np.pi*t)
    return np.array([x,y,z+offset])

# Almond outlines follow the source eye sockets. Smaller irises restore the
# visible warm sclera and adult expression in the original design.
for sign in [-1,1]:
    def eye(t,upper):
        x=EYE_IN+EYE_WIDTH*t
        middle=.3847-.0006*t
        y=middle+(EYE_UP if upper else -EYE_DOWN)*np.sin(np.pi*t)**.82
        return sign*x,y
    lower=[];upper=[]
    for t in np.linspace(0,1,33):
        x,top=eye(t,True);_,bottom=eye(t,False)
        upper.append(project(x,top,.00012)[2]);lower.append(project(x,bottom,.00012)[2])
    eye_boundaries[sign]=(gaussian_filter1d(lower,.7),gaussian_filter1d(upper,.7))
    rows=[]
    for i in range(33):
        t=.0001+.9998*i/32;x,top=eye(t,True);_,bottom=eye(t,False)
        rows.append([eye_project(x,bottom+(top-bottom)*j/12) for j in range(13)])
    patches=[]
    for i in range(32):
        for j in range(12):
            patches.extend([np.array([rows[i][j],rows[i+1][j],rows[i+1][j+1]]),np.array([rows[i][j],rows[i+1][j+1],rows[i][j+1]])])
    rest=partition(patches,lambda p:((p[:,0]-sign*.0216)/.0066)**2+((p[:,1]-.3852)/.0065)**2-1,'Iris')
    for poly in rest:add(poly,'Eye ivory')
    for upper,name,width in [(True,'Upper lash',.00095),(False,'Lower lid',.0005)]:
        for i in range(32):
            quad=[]
            for t,edge in [(i/32,0),((i+1)/32,0),((i+1)/32,1),(i/32,1)]:
                x,y=eye(t,upper);dy=(1 if upper else -1)*width*(.3+.7*np.sin(np.pi*t))
                quad.append(project(x,y+dy*edge,.00034))
            add(quad,name)
    for i in range(24):
        quad=[]
        for t,edge in [(i/24,0),((i+1)/24,0),((i+1)/24,1),(i/24,1)]:
            x,y=eye(t,True)
            arc=np.sin(np.pi*t)
            quad.append(project(x,y+(.0014+.00032*edge)*arc,.00022))
        add(quad,'Lid crease')
    # Shaped brow: full at the inner end, tapering into the outer arc.
    for i in range(20):
        quad=[]
        for t,edge in [(i/20,0),((i+1)/20,0),((i+1)/20,1),(i/20,1)]:
            x=sign*(.0105+.025*t); y=.3970+.0032*np.sin(np.pi*t)-.0018*t
            quad.append(project(x,y+edge*(.0036-.0023*t),.0008))
        add(quad,'Copper brows')
# Iris and pupil are cut together, so the white/iris border never overlaps.
irises=parts['Iris'];parts['Iris']=[]
irises=partition(irises,lambda p:((np.abs(p[:,0])-.0216)/.0036)**2+((p[:,1]-.3852)/.0042)**2-1,'Pupil')
for poly in irises:add(poly,'Iris')

for sign in [-1,1]:
    poly=[project(sign*.0052+.0012*np.cos(a),.3548+.0004*np.sin(a),.0005) for a in np.linspace(0,2*np.pi,10,endpoint=False)]
    add(poly,'Nostril')

# Soft closed smile with a cupid's bow, not a dark horizontal slot.
for i in range(40):
    for name,side in [('Upper lip',1),('Lower lip',-1)]:
        quad=[]
        for t,edge in [(i/40,0),((i+1)/40,0),((i+1)/40,1),(i/40,1)]:
            x=(t*2-1)*.0144;u=x/.0144
            crease=.3455+.0028*u*u
            bow=.0017*(1-u*u)+.0006*np.exp(-((abs(u)-.26)/.2)**2)
            fullness=bow if side>0 else .0021*(1-u*u)
            quad.append(project(x,crease+side*fullness*edge,.00024))
        add(quad,name)
    quad=[]
    for t,edge in [(i/40,0),((i+1)/40,0),((i+1)/40,1),(i/40,1)]:
        x=(t*2-1)*.0144;u=x/.0144;y=.3455+.0028*u*u
        quad.append(project(x,y+(.00035*edge-.00015)*(1-u*u),.00032))
    add(quad,'Mouth crease')

# Subtle, sparse geometry freckles. Fixed seed makes the authoring repeatable.
rng=np.random.default_rng(24)
for _ in range(84):
    x=rng.uniform(-.035,.035); y=rng.uniform(.369,.380)
    if abs(x)<.009 and y<.375:continue
    radius=rng.uniform(.00013,.00027)
    poly=[project(x+radius*np.cos(a),y+radius*.7*np.sin(a),.00020) for a in np.linspace(0,2*np.pi,6,endpoint=False)]
    add(poly,'Freckles')

parts=conform(parts)
scene=trimesh.Scene()
counts={}
normal_tree=cKDTree(mesh.vertices)
source_normals=mesh.vertex_normals.copy()
for name,polys in parts.items():
    if not polys:continue
    verts=[];faces=[]
    for poly in polys:
        start=len(verts);verts.extend(poly)
        faces.extend([[start,start+i,start+i+1] for i in range(1,len(poly)-1)])
    verts=np.asarray(verts);faces=np.asarray(faces)
    mat=PBRMaterial(name='June · '+name,baseColorFactor=np.r_[np.round(linear(palette[name])*255),255].astype(np.uint8),metallicFactor=0,roughnessFactor=.86)
    # A continuous glossy eye surface produces highlights from the scene lights.
    # There is no painted glint, emissive spot, or separate highlight geometry.
    if name in ['Eye ivory','Iris','Pupil']:mat.roughnessFactor=.19
    part=trimesh.Trimesh(verts,faces,process=False,
        visual=trimesh.visual.TextureVisuals(uv=np.zeros((len(verts),2)),material=mat))
    # Surface patches have a front-facing winding on both sides of the face.
    if name in ['Eye ivory','Iris','Pupil','Upper lash','Lower lid','Lid crease','Copper brows','Upper lip','Lower lip','Mouth crease','Freckles','Nostril','Copper ridge','Copper fold']:
        flip=part.face_normals[:,2]<0;part.faces[flip]=part.faces[flip,::-1]
    # Continuous skin tone from shoulders to face. Only a restrained cheek flush.
    if name=='Skin':
        blush=np.exp(-((np.abs(verts[:,0])-.026)/.013)**2-((verts[:,1]-.373)/.0105)**2)*np.clip((verts[:,2]-.017)/.025,0,1)*.80
        colour=linear(palette[name])[None,:]*(1-blush[:,None])+linear([212,129,91])[None,:]*blush[:,None]
        # Intentional pigmentation only; no source-render luminance is sampled.
        # The pinna has a warm recessed bowl inside a lighter helix. Keep it
        # local to the ears, with continuous colour into the temple and neck.
        x,y,z=verts.T
        ear=np.exp(-2*((y-.381)/.013)**2-2*((z+.002)/.011)**2)
        ear*=np.clip((np.abs(x)-.036)/.008,0,1)*.48
        colour=colour*(1-ear[:,None])+linear([164,105,75])[None,:]*ear[:,None]
        part.visual.material.baseColorFactor=[255,255,255,255]
        part.visual.vertex_attributes['color']=np.column_stack([np.round(colour*255).astype(np.uint8),np.full(len(verts),255,dtype=np.uint8)])
    # Blend the anatomical normal field into each plane. This is the same
    # restrained weighted-normal treatment used for stylised hard-surface art:
    # planes read clearly without turning the cheeks into metallic triangles.
    distances,ids=normal_tree.query(verts,k=4)
    weights=1/np.maximum(distances,.00025)**2
    soft=(source_normals[ids]*weights[:,:,None]).sum(axis=1)/weights.sum(axis=1)[:,None]
    soft/=np.linalg.norm(soft,axis=1)[:,None]
    face_planes=planes.at(part.triangles_center)
    hard=np.zeros_like(verts)
    for corner in range(3):np.add.at(hard,faces[:,corner],face_planes)
    hard/=np.maximum(np.linalg.norm(hard,axis=1)[:,None],1e-12)
    amount=.92 if 'hair' in name.lower() or 'Copper' in name else .72
    face=(verts[:,1]>.335)&(verts[:,2]>.015)
    mix=np.full(len(verts),amount)
    if name=='Skin':mix[face]=.58
    if name=='Skin':
        # Use a broader, continuous normal field across the dense neck bridge.
        # Tiny bridge cells should not produce speckled lighting at the seam.
        neck=(verts[:,1]>.287)&(verts[:,1]<.345)
        d,near=normal_tree.query(verts[neck],k=48)
        w=np.exp(-(d/.008)**2)
        neck_normal=(source_normals[near]*w[:,:,None]).sum(axis=1)
        neck_normal/=np.linalg.norm(neck_normal,axis=1)[:,None]
        blend=np.clip((verts[neck,1]-.287)/.014,0,1)*np.clip((.345-verts[neck,1])/.014,0,1)
        soft[neck]=soft[neck]*(1-blend[:,None])+neck_normal*blend[:,None]
        mix[neck]*=1-.65*blend
    if name in ['Eye ivory','Iris','Pupil','Upper lash','Lower lid','Lid crease','Copper brows','Upper lip','Lower lip','Mouth crease','Freckles','Nostril']:mix[:]=0
    normals=hard*mix[:,None]+soft*(1-mix[:,None])
    normals/=np.linalg.norm(normals,axis=1)[:,None]
    if name in ['Eye ivory','Iris','Pupil']:
        normals=[]
        for x,y,z in verts:
            dx=(eye_project(x+.00002,y)[2]-eye_project(x-.00002,y)[2])/.00004
            dy=(eye_project(x,y+.00002)[2]-eye_project(x,y-.00002)[2])/.00004
            n=np.array([-dx,-dy,1]);normals.append(n/np.linalg.norm(n))
        normals=np.asarray(normals)
    part.vertex_normals=normals
    scene.add_geometry(part,geom_name=name)
    counts[name]=len(faces)
scene.export(OUT/'mesh.glb',include_normals=True)
(OUT/'palette.json').write_text(json.dumps({'srgb':palette,'triangles':counts,'totalTriangles':sum(counts.values())},indent=2))
print('Finished June:',sum(counts.values()),'triangles',flush=True)
