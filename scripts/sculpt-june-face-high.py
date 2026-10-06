"""Independent authored June head study; original body and lower neck retained."""
import bpy, bmesh, math, json, hashlib, random
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
STUDY=ROOT/'validation/reconstruction/june-face-high-20260930'
OUT=STUDY/'candidate6';OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(STUDY/'baseline/mesh.glb'))
original_parts=[o for o in bpy.context.scene.objects if o.type=='MESH']
body_skin=bpy.data.objects['Skin']
# The plane is below the chin, so the entire chin and jaw can be remodelled.
bm=bmesh.new();bm.from_mesh(body_skin.data)
bmesh.ops.remove_doubles(bm,verts=[v for v in bm.verts if v.co.z>.323],dist=1e-8)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-8,plane_co=(0,0,.323),plane_no=(0,0,1),clear_outer=True)
bmesh.ops.remove_doubles(bm,verts=[v for v in bm.verts if abs(v.co.z-.323)<1e-8],dist=1e-9)
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
boundary=[v.co.copy() for v in bm.verts if abs(v.co.z-.323)<1e-7 and any(e.is_boundary for e in v.link_edges)]
bm.to_mesh(body_skin.data);bm.free();body_skin.data.update()
for o in original_parts:
 if o.name in ['Skin','Terracotta singlet','Singlet binding','Cream stripe','Charcoal shorts','Ivory shoes','Shoe soles','Shoe straps']:continue
 bpy.data.objects.remove(o,do_unlink=True)

# Plain linear base colours; illumination and reflections come from the scene.
def material(name,color,rough=.72):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
 bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough
 return m
skin=material('June high · Skin',(.49917,.24758,.13211))
cheek=material('June high · Cheek pigment',(.53,.220,.127))
inner_ear=material('June high · Ear pigment',(.46,.195,.108))
hair=material('June high · Copper',(.335,.100,.035))
brow=material('June high · Brow',(.16,.055,.018))
ivory=material('June high · Eye ivory',(.83,.76,.57),.24)
iris=material('June high · Iris',(.067,.038,.015),.24)
pupil=material('June high · Pupil',(.010,.009,.006),.19)
lash=material('June high · Lash',(.018,.011,.006))
upperlip=material('June high · Upper lip',(.38,.128,.069))
lowerlip=material('June high · Lower lip',(.55,.207,.117))
crease=material('June high · Mouth crease',(.13,.053,.026))
freckle=material('June high · Freckle',(.31,.126,.059))
nostril=material('June high · Nostril',(.16,.065,.032))

def mesh(name,verts,faces,mat,smooth=False):
 d=bpy.data.meshes.new(name);d.from_pydata(verts,[],faces);d.update();o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);d.materials.append(mat)
 # Recalculate normals without changing authored facets.
 b=bmesh.new();b.from_mesh(d);bmesh.ops.recalc_face_normals(b,faces=list(b.faces));b.to_mesh(d);b.free()
 for p in d.polygons:p.use_smooth=smooth
 return o

def interp(rows,z,index):
 for a,b in zip(rows,rows[1:]):
  if z<=b[0]:
   t=max(0,(z-a[0])/(b[0]-a[0]));return a[index]*(1-t)+b[index]*t
 return rows[-1][index]
# z, width, front depth, rear depth; deliberate cheek, jaw and brow changes.
rows=[(.329,.0195,.038,.035),(.332,.023,.040,.037),(.335,.025,.040,.039),(.338,.027,.039,.040),(.346,.036,.040,.046),(.352,.039,.039,.047),(.354,.040,.0387,.0475),(.356,.041,.0384,.048),(.358,.0415,.038,.048),(.360,.0422,.0379,.048),(.362,.0429,.0377,.048),(.365,.044,.0375,.048),(.372,.045,.037,.047),(.380,.045,.0365,.046),(.386,.0445,.037,.045),(.392,.045,.039,.045),(.398,.0455,.041,.046),(.405,.046,.042,.046),(.413,.045,.043,.047),(.422,.043,.042,.044),(.431,.037,.037,.039),(.439,.026,.027,.029),(.444,.010,.014,.016)]
nose_rows=[(.347,0,.009),(.351,.001,.010),(.354,.006,.010),(.357,.017,.0080),(.360,.022,.0074),(.363,.020,.0065),(.368,.014,.0055),(.376,.010,.0048),(.385,.006,.0042),(.395,.001,.0045),(.400,0,.005)]
def front_y(x,z):
 w=interp(rows,z,1);f=interp(rows,z,2)
 c=math.sqrt(max(0,1-(x/w)**2));y=-f*c**.48
 n=.86*interp(nose_rows,z-.0027,1);nw=interp(nose_rows,z-.0027,2)
 y-=n*math.exp(-(abs(x)/nw)**2)
 # Nasal wings, a modest philtrum and a soft projecting mouth/chin plane.
 y-=.0040*math.exp(-((abs(x)-.0065)/.0035)**2-((z-.3577)/.0028)**2)
 y-=.0070*math.exp(-(x/.015)**2-((z-.346)/.006)**2)
 y-=.0010*math.exp(-(x/.012)**2-((z-.332)/.004)**2)
 # Eye sockets retreat behind the enclosing lid rim.
 y+=.0038*math.exp(-((abs(x)-.0215)/.011)**4-((z-.386)/.007)**4)
 # cheek prominence, with a broad plane instead of a protruding round lump.
 y-=.0025*math.exp(-((abs(x)-.027)/.012)**4-((z-.369)/.011)**2)
 return y
TH=sorted(set([2*math.pi*j/48 for j in range(48)]+[(j*.025)%(2*math.pi) for j in range(-17,18)]))
N=len(TH)
verts=[]
for i,(z,w,f,b) in enumerate(rows):
 for j in range(N):
  t=TH[j];x=w*math.sin(t);c=math.cos(t)
  y=front_y(x,z) if c>=0 else b*(-c)**.82
  zz=z
  zz+=max(0,.012*(.353-z)/.024)*(1-c)/2
  verts.append((x,y,zz))
faces=[]
for i in range(len(rows)-1):
 for j in range(N):
  a=i*N+j;b=i*N+(j+1)%N;c=b+N;d=a+N
  # Checker orientation creates finite planar cheek facets, not random noise.
  faces.extend([(a,b,c),(a,c,d)] if (i+j)%2==0 else [(a,b,d),(b,c,d)])
cap=len(verts);verts.append((0,.003,.445))
for j in range(N):faces.append(((len(rows)-1)*N+j,(len(rows)-1)*N+(j+1)%N,cap))
# Exact neck seam coordinates, joined to the new lower head ring by angular zipper.
boundary.sort(key=lambda p:math.atan2(p.x,-(p.y-.018))%(2*math.pi))
start=len(verts);verts.extend(tuple(p) for p in boundary)
bangles=[math.atan2(p.x,-(p.y-.018))%(2*math.pi) for p in boundary]
i=j=0
while i<len(boundary) or j<N:
 ai=bangles[(i+1)%len(boundary)] if i+1<len(boundary) else 2*math.pi+bangles[0]
 aj=TH[j+1] if j+1<N else 2*math.pi
 a=start+i%len(boundary);b=j%N
 if i<len(boundary) and (j==N or ai<aj):
  faces.append((a,start+(i+1)%len(boundary),b));i+=1
 else:
  faces.append((a,(j+1)%N,b));j+=1
head=mesh('Authored head and neck bridge',verts,faces,skin)
# Continuous warm cheek pigment; no colour facet encodes lighting.
attr=head.data.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='CORNER')
for loop in head.data.loops:
 c=head.data.vertices[loop.vertex_index].co
 amount=.7*math.exp(-((abs(c.x)-.026)/.014)**2-((c.z-.370)/.010)**2) if c.y<0 else 0
 attr.data[loop.index].color=(.49917+.035*amount,.24758-.025*amount,.13211-.008*amount,1)
headskin=skin.copy();headskin.name='June high · Skin with cheek pigment'
bs=headskin.node_tree.nodes.get('Principled BSDF');vc=headskin.node_tree.nodes.new('ShaderNodeVertexColor');vc.layer_name='Color'
headskin.node_tree.links.new(vc.outputs['Color'],bs.inputs['Base Color']);head.data.materials[0]=headskin

# Blend normals on the facial surface to avoid visible horizontal section bands.
# Broad planes retain a little normal discontinuity; the nasal tip is gentler.
for p in head.data.polygons:p.use_smooth=True
head.data.update()
normals=[]
for p in head.data.polygons:
 for li in p.loop_indices:
  vi=head.data.loops[li].vertex_index;v=head.data.vertices[vi]
  blend=.16 if abs(v.co.x)<.012 and v.co.z>.350 else .18
  normals.append(tuple((v.normal*(1-blend)+p.normal*blend).normalized()))
head.data.normals_split_custom_set(normals)

# Eye patches are almond-shaped convex lenses enclosed by actual eyelid volumes.
EX=.0218;EZ=.3854;EW=.0105

def eye_edge(u,upper):
 z=EZ+.0010*u + (.0053 if upper else -.0038)*math.sin(math.pi*(u+1)/2)**.83
 return z

def eye_y(u,z):
 x=EX+EW*u;lo=eye_edge(u,False);hi=eye_edge(u,True)
 v=2*(z-lo)/(hi-lo)-1 if hi-lo>1e-9 else 0
 # Outer corner retreats into the temporal plane; centre remains under lids.
 return front_y(x,z)-.0007-.0016*(1-u*u)*(1-v*v)

def eye_point(side,u,v):
 lo=eye_edge(u,False);hi=eye_edge(u,True);z=lo+(hi-lo)*(v+1)/2
 return (side*(EX+EW*u),eye_y(u,z),z)
for side in [-1,1]:
 v=[];f=[];nu=24;nv=8
 for i in range(nu+1):
  for j in range(nv+1):v.append(eye_point(side,-1+2*i/nu,-1+2*j/nv))
 for i in range(nu):
  for j in range(nv):
   a=i*(nv+1)+j;f.append((a,a+nv+1,a+nv+2,a+1))
 mesh('Almond eye '+str(side),v,f,ivory,True)
 # Iris/pupil disks are clipped by the eyelid opening at every angle.
 for name,rx,rz,mat,offset in [('Iris',.0047,.0048,iris,.00010),('Pupil',.0026,.0032,pupil,.00018)]:
  v=[(side*EX,eye_y(0,EZ)-offset-.00030,EZ)];f=[];nr=5;nt=40
  for ring in range(1,nr+1):
   r=ring/nr
   for j in range(nt):
    t=2*math.pi*j/nt;dx=rx*r*math.cos(t);z=EZ+rz*r*math.sin(t);u=dx/EW
    z=max(eye_edge(u,False)+.00003,min(eye_edge(u,True)-.00003,z))
    v.append((side*(EX+dx),eye_y(u,z)-offset-.00030,z))
  for j in range(nt):f.append((0,1+j,1+(j+1)%nt))
  for ring in range(nr-1):
   for j in range(nt):
    a=1+ring*nt+j;b=1+ring*nt+(j+1)%nt
    f.append((a,b,b+nt,a+nt))
  mesh(name+' '+str(side),v,f,mat,True)
 for upper in [True,False]:
  v=[];f=[];count=24
  for i in range(count+1):
   u=-1+2*i/count;x=EX+EW*u;z=eye_edge(u,upper);a=math.sin(math.pi*(u+1)/2)**.6
   inner=Vector((side*x,eye_y(u,z)-.0003,z))
   dz=(.0026 if upper else -.0020)*a
   outer=Vector((side*(x+.0009*u*a),front_y(x+.0009*u*a,z+dz)-.0001,z+dz))
   ridge=(inner+outer)/2;ridge.y-=.00085*a
   v.extend([tuple(inner),tuple(ridge),tuple(outer)])
  for i in range(count):
   a=i*3;f.extend([(a,a+3,a+4,a+1),(a+1,a+4,a+5,a+2)])
  mesh(('Upper' if upper else 'Lower')+' enclosing eyelid '+str(side),v,f,skin,True)
  if upper:
   v=[];f=[]
   for i in range(count+1):
    u=-1+2*i/count;x=EX+EW*u;z=eye_edge(u,True);a=math.sin(math.pi*(u+1)/2)**.5
    y=eye_y(u,z)-.00040
    v.extend([(side*x,y,z),(side*x,y-.00002,z+.00055*a)])
   for i in range(count):f.append((2*i,2*i+2,2*i+3,2*i+1))
   mesh('Tapered upper lash '+str(side),v,f,lash,True)
 # Brows have height and a taper, with no painted shadow strip.
 v=[];f=[]
 for i in range(13):
  u=i/12;x=.0095+.0255*u;z=.3991+.0028*math.sin(math.pi*u)-.0012*u;th=.0033*(1-.65*u)
  for dz,dep in [(0,0),(th*.55,-.0004),(th,0)]:v.append((side*x,front_y(x,z+dz)-.0006+dep,z+dz))
 for i in range(12):
  a=3*i;f.extend([(a,a+3,a+4,a+1),(a+1,a+4,a+5,a+2)])
 mesh('Shaped brow '+str(side),v,f,brow)

# Closed smile: four cross-sectional rings describe rolled lips and Cupid's bow.
MW=.0161;MZ=.3462
v=[];f=[];lip_m=[]
for i in range(33):
 u=-1+2*i/32;x=MW*u;a=max(0,1-u*u);line=MZ+.0022*abs(u)**2
 upper=line+(.0019+.00075*math.exp(-((abs(u)-.28)/.18)**2)-.00045*math.exp(-(u/.12)**2))*a
 lower=line-.0035*a
 rows_l=[(upper,0),(line+.0006*a,.0017*a),(line, .0014*a),(line-.0016*a,.0026*a),(lower,0)]
 for z,dep in rows_l:v.append((x,front_y(x,z)-dep-.00016,z))
for i in range(32):
 for k in range(4):
  a=i*5+k;f.append((a,a+5,a+6,a+1));lip_m.append(0 if k<2 else 1)
lips=mesh('Rolled upper and lower lips',v,f,upperlip,True);lips.data.materials.append(lowerlip)
for p,m in zip(lips.data.polygons,lip_m):p.material_index=m
v=[];f=[]
for i in range(33):
 u=-1+2*i/32;x=MW*u;a=max(0,1-u*u);z=MZ+.0022*abs(u)**2
 for dz in [0,-.00030*a]:v.append((x,front_y(x,z)-.0014*a-.00023,z+dz))
for i in range(32):f.append((2*i,2*i+2,2*i+3,2*i+1))
mesh('Closed smile seam',v,f,crease,True)
# Small inset nostrils face down/back; nostril base cannot become a black moustache.
for s in [-1,1]:
 v=[(s*.0056,front_y(.0056,.3572)-.00008,.3572)];f=[]
 for j in range(12):
  t=2*math.pi*j/12;x=s*(.0056+.0018*math.cos(t));z=.3572+.00065*math.sin(t)
  v.append((x,front_y(abs(x),z)-.00010,z))
 for j in range(12):f.append((0,1+j,1+(j+1)%12))
 mesh('Nostril inset '+str(s),v,f,nostril,True)

# Small ears: raised helix, recessed bowl, tragus and attached lobe.
for s in [-1,1]:
 v=[];f=[];n=24
 for ring in range(4):
  r=[1,.84,.56,0][ring]
  for j in range(n):
   t=2*math.pi*j/n;y=.005+.0088*r*math.cos(t);z=.375+.0131*r*math.sin(t)
   # outer rim curls outward; bowl sits closer to the skull.
   x=s*(.0452+[.0015,.0042,.0004,-.0010][ring])
   x+=s*.001*math.sin(t)
   v.append((x,y,z))
 for i in range(3):
  for j in range(n):f.append((i*n+j,i*n+(j+1)%n,(i+1)*n+(j+1)%n,(i+1)*n+j))
 ear=mesh('Sculpted helix and concha '+str(s),v,f,skin)
 ear.data.materials.append(inner_ear)
 for p in ear.data.polygons:
  if p.index>=2*n:p.material_index=1
 # curved tragus volume joins the bowl to the cheek, hiding a simple edge.
 bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=6,radius=1,location=(s*.0465,-.0012,.3725))
 o=bpy.context.object;o.name='Ear tragus '+str(s);o.scale=(.0020,.0030,.0038);o.data.materials.append(skin)
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)

# Freckles are tiny surface geometry with pigment only, spread over cheek and nose.
rng=random.Random(61);v=[];f=[]
for i in range(145):
 x=rng.uniform(-.034,.034);z=rng.uniform(.363,.377)
 if abs(x)<.008 and rng.random()<.55:continue
 r=rng.uniform(.00011,.00026);base=len(v)
 for j in range(5):
  t=2*math.pi*j/5;xx=x+r*math.cos(t);zz=z+r*math.sin(t);v.append((xx,front_y(xx,zz)-.000055,zz))
 f.append(tuple(range(base,base+5)))
mesh('Cheek and bridge freckles',v,f,freckle)

# A closed scalp cap and broad swept locks: facets describe thick hair flow.
HN=40;HB=8;v=[];f=[]
def hairline(t):
 a=min(t,2*math.pi-t)
 pts=[(0,.419),(.45,.425),(.85,.417),(1.25,.390),(1.6,.385),(2,.369),(2.5,.355),(math.pi,.351)]
 return interp(pts,a,1)
def cap_point(t,k):
 z0=hairline(t);q=k/HB
 z=z0+(.452-z0)*q
 z+=.0030*math.sin(t+.5)*math.sin(q*math.pi)**2
 hair_rows=[(.350,.041,.043,.053),(.370,.049,.048,.057),(.390,.051,.048,.059),(.410,.052,.048,.057),(.427,.050,.046,.051),(.440,.037,.036,.038),(.448,.021,.020,.022),(.452,0,0,0)]
 width=interp(hair_rows,z,1)
 front=interp(hair_rows,z,2)
 rear=interp(hair_rows,z,3)
 x=width*math.sin(t);c=math.cos(t)
 y=-front*c**.5 if c>=0 else rear*(-c)**.82
 return Vector((x,y,z))
for k in range(HB):
 for j in range(HN):v.append(tuple(cap_point(2*math.pi*j/HN,k)))
for k in range(HB-1):
 for j in range(HN):
  a=k*HN+j;b=k*HN+(j+1)%HN;c=b+HN;d=a+HN
  f.extend([(a,b,c),(a,c,d)] if (j+k)%2==0 else [(a,b,d),(b,c,d)])
top=len(v);v.append((0,.006,.451))
for j in range(HN):f.append(((HB-1)*HN+j,(HB-1)*HN+(j+1)%HN,top))
mesh('Swept scalp foundation',v,f,hair)
# Each lock is a broad convex patch that travels from hairline towards the knot.
for t0,t1,width,lift in [(-.62,-2.55,.48,.0050),(.17,2.50,.49,.0040),(.74,2.65,.36,.0036),(-1.07,-2.75,.33,.0038)]:
 v=[];f=[];steps=10
 for i in range(steps+1):
  q=i/steps;t=t0+(t1-t0)*q*.70;k=.25+6.1*math.sin(q*math.pi/2)
  for j in range(5):
   u=-1+2*j/4;tt=(t+width*u*(1-.48*q))%(2*math.pi);p=cap_point(tt,k)
   normal=Vector((p.x,p.y-.004,(p.z-.382)*.8)).normalized()
   p+=normal*lift*(1-u*u)*math.sin(math.pi*(q*.83+.1));v.append(tuple(p))
 for i in range(steps):
  for j in range(4):
   a=5*i+j;f.append((a,a+1,a+6,a+5))
 mesh('Thick swept lock '+str(t0),v,f,hair)
# Interlocking knot lobes give the bun a folded rather than circular silhouette.
for name,loc,scale,rot in [
 ('Bun crossing main fold',(.003,.039,.463),(.029,.025,.029),-.34),
 ('Bun upper folded lobe',(-.013,.036,.475),(.019,.024,.018),.38),
 ('Bun lower tucked lobe',(.017,.036,.453),(.019,.023,.020),-.70)]:
 bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=1,location=loc)
 o=bpy.context.object;o.name=name
 for vertex in o.data.vertices:
  p=vertex.co
  p*=1+.055*math.sin(3*math.atan2(p.x,p.z)+.7)*math.cos(p.y*2)
 o.scale=scale;o.rotation_euler[1]=rot;o.data.materials.append(hair)
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
# Face framing strands have an angular swept cross section and pointed tips.
for s in [-1,1]:
 path=[(.035,-.043,.420,.0045),(.040,-.036,.405,.0040),(.041,-.030,.389,.0032),(.040,-.029,.373,.0026),(.039,-.026,.357,.0018),(.035,-.022,.347,.00025)]
 v=[];f=[]
 for i,(x,y,z,r) in enumerate(path):
  for j in range(6):
   t=2*math.pi*j/6;v.append((s*(x+r*math.cos(t)),y+r*.65*math.sin(t),z))
 for i in range(len(path)-1):
  for j in range(6):f.append((i*6+j,i*6+(j+1)%6,(i+1)*6+(j+1)%6,(i+1)*6+j))
 f.extend([tuple(reversed(range(6))),tuple(range((len(path)-1)*6,len(path)*6))])
 mesh('Tapered face framing lock '+str(s),v,f,hair)

# References are packed into the editable file, hidden from export and rendering.
refs=bpy.data.collections.new('Original June reference sheets');bpy.context.scene.collection.children.link(refs)
for filename,name,loc in [('ChatGPT Image 30 Sept 2026, 19_34_55.png','Face front profile three-quarter',(.23,.10,.40)),('ChatGPT Image 30 Sept 2026, 19_34_45.png','Body front profile back',(-.30,.10,.05))]:
 im=bpy.data.images.load('/Users/craig/Downloads/'+filename);im.pack()
 o=bpy.data.objects.new(name,None);o.empty_display_type='IMAGE';o.data=im;o.empty_display_size=.25;o.location=loc;o.rotation_euler=(math.pi/2,0,0);o.hide_render=True;refs.objects.link(o)
refs.hide_viewport=True
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.context.scene.objects:
 if o.type=='MESH':o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(OUT/'mesh.glb'),export_format='GLB',use_selection=True,export_animations=False,export_yup=True,export_vertex_color='MATERIAL')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'sculpt.blend'))
meta={'inputSha256':hashlib.sha256((STUDY/'baseline/mesh.glb').read_bytes()).hexdigest(),'source':'scripts/sculpt-june-face-high.py','neckCutZ':.323,'neckBoundaryVertices':len(boundary),'design':'Locally rebuilt head with structured cheek/jaw/nose surface, enclosed almond lenses, lip rolls, recessed ear bowls and swept copper hair masses. Body geometry below the neck cut is preserved.'}
(OUT/'modelling.json').write_text(json.dumps(meta,indent=2)+'\n')
