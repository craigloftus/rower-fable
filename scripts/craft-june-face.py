"""Place June's facial planes around explicit anatomical feature loops.

The closed reconstruction remains the depth guide. Constrained triangulation
connects authored eye, brow, nose, lip and cheek landmarks to the existing head
boundary, retaining a continuous neck and head surface.
"""
from pathlib import Path
import math
import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import delaunay_2d_cdt

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'validation/reconstruction/june-final'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.wm.ply_import(filepath=str(OUT/'refined-surface.ply'),forward_axis='Y',up_axis='Z')
guide=bpy.context.object
guide.data.calc_loop_triangles()
surface=BVHTree.FromPolygons([v.co for v in guide.data.vertices],[t.vertices for t in guide.data.loop_triangles],all_triangles=True)
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.ply_import(filepath=str(OUT/'approved-head.ply'),forward_axis='Y',up_axis='Z')
reference=bpy.context.object;reference.data.calc_loop_triangles()
original=BVHTree.FromPolygons([v.co for v in reference.data.vertices],[t.vertices for t in reference.data.loop_triangles],all_triangles=True)

def source_depth(x,y):
    repaired,_,_,_=surface.ray_cast(Vector((x,y,.3)),Vector((0,0,-1)))
    if repaired is None:return None
    depths=[]
    for dx,dy in [(0,0),(-.0005,0),(.0005,0),(0,-.0005),(0,.0005)]:
        hit,_,_,_=original.ray_cast(Vector((x+dx,y+dy,.3)),Vector((0,0,-1)))
        if hit is not None and hit.z>.017:depths.append(hit.z)
    if not depths:return repaired
    depths.sort();depth=depths[len(depths)//2]
    border=min((.034-abs(x))/.004,(y-.332)/.005,(.432-y)/.004)
    strength=max(0,min(1,border))
    return Vector((x,y,repaired.z*(1-strength)+depth*strength))

bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.ply_import(filepath=str(OUT/'faceted-surface.ply'),forward_axis='Y',up_axis='Z')
obj=bpy.context.object
bm=bmesh.new();bm.from_mesh(obj.data)
for co,no in [((0,0,.019),(0,0,1)),((0,.332,0),(0,1,0)),((0,.432,0),(0,1,0)),((-.034,0,0),(1,0,0)),((.034,0,0),(1,0,0))]:
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=co,plane_no=no,dist=1e-8)
selected={f for f in bm.faces if .332<f.calc_center_median().y<.432 and f.calc_center_median().z>.019 and abs(f.calc_center_median().x)<.034}
boundary=[e for e in bm.edges if sum(f in selected for f in e.link_faces)==1]
# Follow the topological boundary, including its concavities.
linked={}
for e in boundary:
    a,b=e.verts;linked.setdefault(a,[]).append(b);linked.setdefault(b,[]).append(a)
loops=[];unused=set(linked)
while unused:
    start=unused.pop();loop=[start];previous=None;current=start
    while True:
        candidates=[v for v in linked[current] if v!=previous]
        nxt=candidates[0]
        if nxt==start:break
        loop.append(nxt);unused.discard(nxt);previous,current=current,nxt
    loops.append(loop)
print('Facial boundary loops:',[len(l) for l in loops],flush=True)
assert len(loops)==1,'Face panel must have one boundary'
loop=loops[0]
area=sum(a.co.x*b.co.y-b.co.x*a.co.y for a,b in zip(loop,loop[1:]+loop[:1]))
if area<0:loop.reverse()
coords=[Vector((v.co.x,v.co.y)) for v in loop]
positions=[v.co.copy() for v in loop]
edges=[]

def point(x,y):
    hit=source_depth(x,y)
    if hit is None or hit.z<.018:return None
    coords.append(Vector((x,y)));positions.append(hit)
    return len(coords)-1

def path(points,closed=False):
    ids=[point(x,y) for x,y in points]
    for a,b in zip(ids,ids[1:]+(ids[:1] if closed else [])):
        if a is not None and b is not None:edges.append((a,b))

# Broad forehead and cheek planes, with asymmetric triangulation choices
# confined to their diagonals; landmarks themselves remain bilateral.
for y,xs in [(.427,[-.033,-.019,0,.019,.033]),(.416,[-.034,-.020,0,.020,.034]),
             (.409,[-.036,-.025,-.008,0,.008,.025,.036]),
             (.376,[-.038,-.028,-.014,.014,.028,.038]),
             (.365,[-.037,-.026,-.015,.015,.026,.037]),
             (.355,[-.032,-.022,.022,.032]),(.341,[-.024,-.013,0,.013,.024]),
             (.334,[-.012,0,.012])]:
    for x in xs:point(x,y)
for sign in [-1,1]:
    # Actual eye aperture plus an outer orbital loop for eyelid thickness.
    for margin in [0,.0024]:
        shape=[]
        for t in [i/12 for i in range(13)]:
            x=.0105+.024*t;mid=.3847-.0006*t
            shape.append((sign*(x+margin*(2*t-1)),mid+.0058*math.sin(math.pi*t)**.82+margin*.6))
        for t in [i/12 for i in range(11,-1,-1)]:
            x=.0105+.024*t;mid=.3847-.0006*t
            shape.append((sign*(x+margin*(2*t-1)),mid-.0043*math.sin(math.pi*t)**.82-margin*.6))
        path(shape,True)
    path([(sign*x,y) for x,y in [(.009,.398),(.019,.401),(.031,.399),(.037,.395)]])
    # Nasal bridge, side wall, alar corner, and the cheek beside the mouth.
    path([(sign*x,y) for x,y in [(.005,.406),(.006,.394),(.006,.382),(.006,.369),(.008,.359),(.010,.355),(.006,.352)]])
    path([(sign*x,y) for x,y in [(.015,.384),(.018,.374),(.016,.361),(.021,.350),(.013,.342)]])
path([(0,y) for y in [.407,.396,.386,.375,.366,.359,.354,.350]])
# Separate upper and lower vermilion borders and the closed mouth crease.
for side in [-1,0,1]:
    points=[]
    for i in range(17):
        u=i/8-1;x=u*.0144;y=.3455+.0028*u*u
        if side>0:y+=.0017*(1-u*u)+.0006*math.exp(-((abs(u)-.26)/.2)**2)
        if side<0:y-=.0021*(1-u*u)
        points.append((x,y))
    path(points)

out_v,_,out_f,orig_v,_,_=delaunay_2d_cdt(coords,edges,[list(range(len(loop)))],1,1e-8,True)
bmesh.ops.delete(bm,geom=list(selected),context='FACES_ONLY')
lookup=[]
for xy,ids in zip(out_v,orig_v):
    boundary_id=next((i for i in ids if i<len(loop)),None)
    if boundary_id is not None:lookup.append(loop[boundary_id]);continue
    hit=source_depth(xy.x,xy.y)
    lookup.append(bm.verts.new(hit))
for f in out_f:
    bm.faces.new([lookup[i] for i in f])
# Remove the old face interior's now unused topology.
bmesh.ops.delete(bm,geom=[e for e in bm.edges if not e.link_faces],context='EDGES')
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_edges],context='VERTS')
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
# Restore the ear's helix and concha from the approved sculpt. These small
# concavities need their own local sampling; general fairing flattens them.
def ear_region(p):
    return ((p.y-.380)/.022)**2+((p.z-.001)/.018)**2

ear_faces=[f for f in bm.faces if abs(f.calc_center_median().x)>.038 and ear_region(f.calc_center_median())<1.2]
ear_edges=list({e for f in ear_faces for e in f.edges})
bmesh.ops.subdivide_edges(bm,edges=ear_edges,cuts=1,use_grid_fill=True)
for vert in bm.verts:
    p=vert.co;region=ear_region(p)
    if abs(p.x)<.038 or region>1.3:continue
    sign=1 if p.x>0 else -1;depths=[]
    for dy,dz in [(0,0),(-.0003,0),(.0003,0),(0,-.0003),(0,.0003)]:
        hit,_,_,_=original.ray_cast(Vector((sign*.2,p.y+dy,p.z+dz)),Vector((-sign,0,0)))
        if hit is not None and hit.x*sign>.032:depths.append(hit.x)
    if depths:
        depths.sort();weight=max(0,min(1,(1.3-region)/.4))*max(0,min(1,(abs(p.x)-.038)/.006))
        p.x=p.x*(1-weight)+depths[len(depths)//2]*weight
bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='BEAUTY',ngon_method='BEAUTY')
bm.to_mesh(obj.data);bm.free()
bpy.ops.wm.ply_export(filepath=str(OUT/'crafted-surface.ply'),export_selected_objects=True,forward_axis='Y',up_axis='Z')
print('Crafted facial panel:',len(out_f),'triangles; surface',len(obj.data.polygons),flush=True)
