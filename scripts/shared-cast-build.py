"""Retain the approved June rig/body, with fixed chest and donor-head choices."""
from pathlib import Path
import bpy,json,hashlib,math,shutil,bisect
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1];MASTER=ROOT/'art/characters/shared-cast';OUT=ROOT/'validation/characters/shared-cast'
MASTER.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
config=json.loads((MASTER/'cast.json').read_text());provenance=json.loads((MASTER/'head-provenance.json').read_text())
layout=json.loads((ROOT/'validation/reconstruction/fresh-rig/layout.json').read_text())
C=Matrix(((1,0,0,0),(0,0,-1,0),(0,1,0,0),(0,0,0,1)));B=Matrix(((0,0,-1,0),(0,1,0,0),(1,0,0,0),(0,0,0,1)))
P=C@Matrix.Translation(Vector(layout['hipRest']))@Matrix.Scale(layout['scale'],4)@Matrix.Translation(-(B@Vector(layout['hipSource'])))@B
PI=P.inverted();cut=(P@Vector((0,config['neckCut'],0))).z
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
def ramp(a,b,x):
 t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)
def colour(rgb):
 return [v/3294.6 if v<=10.31475 else ((v/255+.055)/1.055)**2.4 for v in rgb]+[1]
def blend(a,b,t):
 return (a[0].lerp(b[0],t),a[1].lerp(b[1],t).normalized(),{k:a[2].get(k,0)*(1-t)+b[2].get(k,0)*t for k in a[2].keys()|b[2].keys()},None)
def triangles(obj,rigid=False):
 obj.data.calc_loop_triangles();names={g.index:g.name for g in obj.vertex_groups}
 weights=[{'head':1.} if rigid else {names[g.group]:g.weight for g in v.groups} for v in obj.data.vertices]
 normals=obj.data.corner_normals
 return [([ (v.co.copy(),normals[loop].vector.copy(),weights[v.index],v.index if not rigid else None) for v,loop in zip([obj.data.vertices[i] for i in f.vertices],f.loops)],f.material_index) for f in obj.data.loop_triangles]
def clip(tris,height):
 result=[];boundary=[];points={};segments=[]
 for face,material in tris:
  inside=[v[0].z<=height for v in face]
  if all(inside):result.append((face,material));continue
  if not any(inside):continue
  poly=[];edge=[]
  for i,a in enumerate(face):
   b=face[(i+1)%3]
   if inside[i]:poly.append(a)
   if inside[i]!=inside[(i+1)%3]:
    r=blend(a,b,(height-a[0].z)/(b[0].z-a[0].z));r[0].z=height
    key=tuple(round(v,7) for v in r[0]);r=points.setdefault(key,r)
    poly.append(r);edge.append(r)
  result.extend(([poly[0],poly[i],poly[i+1]],material) for i in range(1,len(poly)-1));boundary.extend(edge);segments.append(edge)
 return result,boundary_loop(segments)
def boundary_loop(segments):
 points={};neighbors={}
 for edge in segments:
  keys=[tuple(round(v,6) for v in r[0]) for r in edge]
  if keys[0]==keys[1]:continue
  for k,r in zip(keys,edge):points.setdefault(k,r)
  for a,b in [keys,keys[::-1]]:neighbors.setdefault(a,set()).add(b)
 assert all(len(v)==2 for v in neighbors.values()),f'Neck section degree defects: {[(k,len(v)) for k,v in neighbors.items() if len(v)!=2]}'
 first=min(neighbors);current=first;previous=None;order=[]
 while current not in order:
  order.append(current);n=neighbors[current]-{previous};previous,current=current,sorted(n)[0]
 assert current==first and len(order)==len(neighbors),'Disconnected neck boundary loops'
 return [points[k] for k in order]
def ordered(records,centre):
 data=[(math.atan2(r[0].y-centre.y,r[0].x-centre.x)%(2*math.pi),r) for r in records]
 area=sum(r[1][0].x*data[(i+1)%len(data)][1][0].y-data[(i+1)%len(data)][1][0].x*r[1][0].y for i,r in enumerate(data))
 if area<0:data.reverse()
 start=min(range(len(data)),key=lambda i:data[i][0]);return data[start:]+data[:start]
def sample(loop,angle):
 angles=[v[0] for v in loop];j=bisect.bisect_right(angles,angle);i=(j-1)%len(loop);j%=len(loop)
 a,b=angles[i],angles[j]
 if b<a:b+=2*math.pi
 if angle<a:angle+=2*math.pi
 return blend(loop[i][1],loop[j][1],(angle-a)/(b-a))
def bridge(lower,upper):
 centre=sum((r[0] for r in lower+upper),Vector())/len(lower+upper)
 lo=ordered(lower,centre);hi=ordered(upper,centre);rings=[lo]
 for t in [.25,.5,.75]:
  rings.append([(a,blend(sample(lo,a),sample(hi,a),t)) for a in [i*2*math.pi/64 for i in range(64)]])
 rings.append(hi);faces=[]
 for low,high in zip(rings,rings[1:]):
  i=j=0
  while i<len(low) or j<len(high):
   a=low[i%len(low)][1];b=high[j%len(high)][1]
   na=low[(i+1)%len(low)][0]+(2*math.pi if i+1>=len(low) else 0)
   nb=high[(j+1)%len(high)][0]+(2*math.pi if j+1>=len(high) else 0)
   if i<len(low) and (j==len(high) or na<nb):face=[a,low[(i+1)%len(low)][1],b];i+=1
   else:face=[a,high[(j+1)%len(high)][1],b];j+=1
   normal=(face[1][0]-face[0][0]).cross(face[2][0]-face[0][0]);radial=sum((r[0] for r in face),Vector())/3-centre;radial.z=0
   if normal.dot(radial)<0:face.reverse()
   faces.append((face,0))
 return faces

def fair_posterior_neck(faces,floor,centre):
 # Join the donor nape tangent to the new bridge, anchoring approved body.
 import numpy as np
 points=[];keys={};neighbors=[];ids=[]
 for face,_ in faces:
  row=[]
  for r in face:
   key=tuple(round(v,6) for v in r[0])
   if key not in keys:keys[key]=len(points);points.append(tuple(r[0]));neighbors.append(set())
   row.append(keys[key])
  ids.append(row)
  for a,b in zip(row,row[1:]+row[:1]):neighbors[a].add(b);neighbors[b].add(a)
 p=np.asarray(points);original=p.copy()
 w=np.array([ramp(cut,cut+.012,q[2])*(1-ramp(floor+.012,floor+.045,q[2]))*ramp(centre.x-.008,centre.x+.012,q[0]) for q in p])
 active=np.flatnonzero(w>0);adj={i:sorted(neighbors[i]) for i in active}
 for _ in range(18):
  for step in [.45,-.50]:
   delta=np.array([p[adj[i]].mean(axis=0)-p[i] for i in active])
   p[active]+=step*w[active,None]*delta
 normals=np.zeros_like(p)
 for row in ids:
  a,b,c=p[row];normal=np.cross(b-a,c-a)
  for i in row:normals[i]+=normal
 lengths=np.linalg.norm(normals,axis=1);normals/=np.maximum(lengths[:,None],1e-20)
 result=[]
 for (face,material),row in zip(faces,ids):
  updated=[]
  for r,i in zip(face,row):
   if w[i]>0:
    normal=r[1].lerp(Vector(normals[i]),float(w[i])).normalized()
    r=(Vector(p[i]),normal,r[2],r[3])
   updated.append(r)
  result.append((updated,material))
 return result,float(np.linalg.norm(p-original,axis=1).max())

def sculpt_chest(p,weights):
 s=PI@p;x,y,z=s
 if weights.get('torso',0)+weights.get('spine',0)<.999:return p.copy()
 w=ramp(.115,.145,y)*(1-ramp(.230,.270,y))*(1-ramp(.060,.087,abs(x)))*ramp(.018,.045,z)
 envelope=.070+.010*math.exp(-((y-.188)/.054)**2)-.012*(x/.085)**2
 s.z-=.8*w*max(0,z-envelope)
 return P@s if w>0 and z>envelope else p.copy()

shutil.copy2(ROOT/config['sourceBlend'],MASTER/'shared-body.blend')
entries=[]
for setting in config['characters']:
 character=setting['id'];folder=OUT/character;folder.mkdir(parents=True,exist_ok=True)
 if character=='june':
  shutil.copy2(ROOT/config['sourceGLB'],MASTER/'june.glb');shutil.copy2(ROOT/config['sourceBlend'],MASTER/'june.blend')
  entries.append({**setting,'file':'june.glb','editableBlend':'june.blend','sha256':sha(MASTER/'june.glb'),'triangles':45777,'bodyIdentityCheck':{'passed':True,'method':'Byte-identical approved June source'},'clipIdentityCheck':{'passed':True,'method':'Byte-identical approved June source'}});continue
 bpy.ops.wm.open_mainfile(filepath=str(MASTER/'shared-body.blend'))
 body=bpy.data.objects['june'];arm=bpy.data.objects['june_rig'];materials=list(body.data.materials);original=triangles(body)
 eyeids={i for f in body.data.polygons if 'Eye ivory' in materials[f.material_index].name for i in f.vertices}
 eyeheight=(min(body.data.vertices[i].co.z for i in eyeids)+max(body.data.vertices[i].co.z for i in eyeids))/2
 bodyfaces,lower=clip(original,cut)
 original_positions={v.index:v.co.copy() for v in body.data.vertices};original_weights={v.index:{body.vertex_groups[g.group].name:g.weight for g in v.groups} for v in body.data.vertices}
 bpy.ops.object.select_all(action='DESELECT');before=set(bpy.context.scene.objects)
 bpy.ops.import_scene.gltf(filepath=str(MASTER/f'{character}-head.glb'))
 heads=[o for o in bpy.context.scene.objects if o not in before and o.type=='MESH']
 eye=[v.co.z for o in heads if 'Eye ivory' in o.data.materials[0].name for v in o.data.vertices]
 donorEye=(min(eye)+max(eye))/2
 # Uniform head scale and eye/chin/neck placement never use June's bun height.
 factor=setting['headScale'];heightShift=eyeheight-(P@Vector((0,donorEye*factor,0))).z
 for o in heads:
  transform=P@Matrix.Scale(factor,4)@C.inverted();o.data.transform(transform)
  for v in o.data.vertices:v.co.z+=heightShift
 headfloor=min(v.co.z for o in heads for v in o.data.vertices)
 edges={};edgeRecords={}
 for o in heads:
  for face,_ in triangles(o,True):
   for a,b in zip(face,face[1:]+face[:1]):
    if abs(a[0].z-headfloor)<1e-6 and abs(b[0].z-headfloor)<1e-6:
     key=tuple(sorted(tuple(round(v,6) for v in r[0]) for r in [a,b]))
     if key[0]==key[1]:continue
     edges[key]=edges.get(key,0)+1;edgeRecords[key]=[a,b]
 upper=boundary_loop([edgeRecords[k] for k,n in edges.items() if n==1])
 lowCentre=sum((r[0] for r in lower),Vector())/len(lower);upCentre=sum((r[0] for r in upper),Vector())/len(upper)
 shift=lowCentre-upCentre;shift.z=0
 for o in heads:
  for v in o.data.vertices:v.co+=shift
  o.data.update()
 for r in upper:
  r[0].x+=shift.x;r[0].y+=shift.y
 # Match skin exactly to the donor's palette material; recolour only albedo.
 skin=next(o.data.materials[0] for o in heads if o.data.materials[0].name.endswith(' · Skin'))
 skin.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=colour(setting['skinColour'])
 materials[0]=skin
 for index,m in enumerate(materials):
  if 'Terracotta singlet' in m.name or 'Singlet binding' in m.name:
   m=m.copy();m.name=f'{character} · '+('Singlet binding' if 'binding' in m.name else 'Singlet')
   rgb=setting['topColour'];linear=colour(rgb)
   if 'binding' in m.name:linear=[c*.78 for c in linear[:3]]+[1]
   m.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=linear;materials[index]=m
 material_index={m.name:i for i,m in enumerate(materials)};headfaces=[]
 for o in heads:
  local={}
  for i,m in enumerate(o.data.materials):
   if m.name not in material_index:material_index[m.name]=len(materials);materials.append(m)
   local[i]=material_index[m.name]
  headfaces.extend((face,local[mat]) for face,mat in triangles(o,True))
 # A fixed authoring variant, never a morph target or animated body scale.
 changed=set();maxdelta=0.;protected=0
 if setting['chestVariant']=='flat':
  for face,_ in bodyfaces:
   for i,r in enumerate(face):
    p=sculpt_chest(r[0],r[2]);delta=(p-r[0]).length
    if delta>0:
     if r[3] is not None:changed.add(r[3])
     maxdelta=max(maxdelta,delta)
     eps=.0001;columns=[]
     for axis in range(3):
      step=Vector();step[axis]=eps
      columns.append((sculpt_chest(r[0]+step,r[2])-sculpt_chest(r[0]-step,r[2]))/(2*eps))
     jacobian=Matrix(columns).transposed()
     assert jacobian.determinant()>.1,'Chest compression must retain positive local depth'
     normal=(jacobian.inverted().transposed()@r[1]).normalized()
     face[i]=(p,normal,r[2],r[3])
 for face,_ in bodyfaces:
  for r in face:
   if r[3] is not None:
    assert r[2]==original_weights[r[3]],'Approved body weights changed'
    if r[3] not in changed:assert r[0]==original_positions[r[3]];protected+=1
 allfaces=bodyfaces+bridge(lower,upper)+headfaces
 allfaces,neck_fairing=fair_posterior_neck(allfaces,headfloor,lowCentre)
 positions=[];weights=[];faces=[];normalvalues=[];matids=[];weld={};facekeys=set()
 for face,mat in allfaces:
  ids=[]
  for r in face:
   key=tuple(round(v,6) for v in r[0]) if cut-1e-7<=r[0].z<=headfloor+.001 else None
   index=weld.get(key) if key is not None else None
   if index is None:
    index=len(positions);positions.append(tuple(r[0]));weights.append(r[2])
    if key is not None:weld[key]=index
   ids.append(index)
  if len(set(ids))<3 or tuple(sorted(ids)) in facekeys:continue
  facekeys.add(tuple(sorted(ids)))
  faces.append(ids);matids.append(mat);normalvalues.extend(tuple(r[1]) for r in face)
 from collections import Counter
 edgecounts=Counter()
 for face in faces:
  keys=[tuple(round(v,6) for v in positions[i]) for i in face]
  if len(set(keys))<3:continue
  for a,b in zip(keys,keys[1:]+keys[:1]):edgecounts[tuple(sorted((a,b)))]+=1
 neckedges={edge:n for edge,n in edgecounts.items() if all(cut-1e-6<=p[2]<=headfloor+1e-6 for p in edge)}
 defects=[(edge,n) for edge,n in neckedges.items() if n!=2]
 assert not defects,f'Neck boundary/nonmanifold edges: {defects[:8]}'
 mesh=bpy.data.meshes.new(f'{character} shared June body');mesh.from_pydata(positions,[],faces);mesh.update()
 for m in materials:mesh.materials.append(m)
 for face,mat in zip(mesh.polygons,matids):face.material_index=mat;face.use_smooth=True
 assert len(normalvalues)==len(mesh.loops)
 assert not mesh.validate(verbose=True,clean_customdata=False),'Invalid assembled topology'
 mesh.normals_split_custom_set(normalvalues)
 obj=bpy.data.objects.new(character,mesh);bpy.context.collection.objects.link(obj)
 for name in [g.name for g in body.vertex_groups]:obj.vertex_groups.new(name=name)
 for i,ws in enumerate(weights):
  for name,w in sorted(ws.items()):
   if w>1e-8:obj.vertex_groups[name].add([i],w,'REPLACE')
 modifier=obj.modifiers.new('Approved June Preserve Volume','ARMATURE');modifier.object=arm;modifier.use_deform_preserve_volume=True;obj.parent=arm
 obj['skinning']='dualQuaternion';obj['chestVariant']=setting['chestVariant'];obj['source']='Approved June body/rig with fixed donor head and palette'
 for o in [body]+heads:bpy.data.objects.remove(o,do_unlink=True)
 scene=bpy.context.scene;scene.frame_set(1)
 bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);arm.select_set(True);bpy.context.view_layer.objects.active=obj
 bpy.ops.export_scene.gltf(filepath=str(MASTER/f'{character}.glb'),export_format='GLB',use_selection=True,export_animations=True,export_frame_range=True,export_force_sampling=True,export_animation_mode='ACTIVE_ACTIONS',export_nla_strips_merged_animation_name='RowingCycle',export_anim_slide_to_zero=True,export_skins=True,export_yup=True,export_vertex_color='MATERIAL',export_all_vertex_colors=False,export_extras=True)
 bpy.ops.wm.save_as_mainfile(filepath=str(MASTER/f'{character}.blend'))
 report={'passed':True,'protectedBodyCorners':protected,'maximumProtectedPositionDelta':0,'maximumBodyWeightDelta':0,'changedChestVertices':len(changed),'maximumChestDisplacement':maxdelta,'neckCutSourceHeight':config['neckCut'],'eyeHeight':eyeheight,'headUniformScale':factor,'headTranslation':list(shift),'verticalHeadShift':heightShift,'maximumPosteriorNeckFairing':neck_fairing,'neckBridgeTriangles':len(allfaces)-len(bodyfaces)-len(headfaces),'neckTopologyCheck':{'passed':True,'edges':len(neckedges),'boundaryEdges':0,'nonManifoldEdges':0}}
 (folder/'source-identity.json').write_text(json.dumps(report,indent=2)+'\n')
 entries.append({**setting,'file':f'{character}.glb','editableBlend':f'{character}.blend','sha256':sha(MASTER/f'{character}.glb'),'triangles':len(faces),'bodyIdentityCheck':report,'clipIdentityCheck':{'passed':False,'reason':'Awaiting exact exported track comparison'},'donor':provenance[character]})
manifest={'sourceBlend':config['sourceBlend'],'sourceBlendSha256':sha(ROOT/config['sourceBlend']),'sourceGLB':config['sourceGLB'],'sourceGLBSha256':sha(ROOT/config['sourceGLB']),'boatFit':config['boatFit'],'characters':entries}
(MASTER/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
