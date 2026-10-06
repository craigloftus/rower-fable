"""Localized Blender sculpt pass against June's supplied September 30 sheets.

Run with Blender, passing baseline GLB and a candidate output directory after --.
The continuous deformation is applied equally to duplicated material boundaries.
Body geometry and the welded neck join below source height .337 remain exact.
"""
import bpy
import numpy as np
import sys
import json
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
from pathlib import Path

source, output = map(Path, sys.argv[sys.argv.index('--')+1:])
output.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(source.resolve()))
skin = bpy.data.objects['Skin']
skin_points = [v.co.copy() for v in skin.data.vertices]
skin_faces = [tuple(p.vertices) for p in skin.data.polygons]
skin_surface = BVHTree.FromPolygons(skin_points,skin_faces,all_triangles=True)

def project(x, height):
    hit, _, index, _ = skin_surface.ray_cast(Vector((x,-1,height)),Vector((0,1,0)))
    assert hit is not None, (x,height)
    return hit,index

# A rolled skin rim makes the lid an actual volume around the eye opening.
# Its outer edge returns to the existing skin, while its inner edge overlaps
# the dark lash root by a fraction of a millimetre.
lid_vertices, lid_faces, lid_colors = [], [], []
source_colors = skin.data.color_attributes['Color']
for side in (-1,1):
    for upper in (True,False):
        start = len(lid_vertices)
        for i in range(49):
            t = .0001+.9998*i/48
            x = side*(.0115+.0215*t)
            arc = np.sin(np.pi*t)**.82
            height = .3847-.0006*t+(.0061 if upper else -.0037)*arc
            width = (.0017 if upper else .0010)*np.sin(np.pi*t)
            for j in range(5):
                u = j/4
                h = height+(1 if upper else -1)*(.00008+width*u)
                hit,index = project(x,h)
                hit.y -= (.00025+.00055*np.sin(np.pi*u))*np.sin(np.pi*t)
                lid_vertices.append(hit[:])
                poly = skin.data.polygons[index]
                colour = np.mean([source_colors.data[k].color[:] for k in poly.loop_indices],axis=0)
                lid_colors.append(colour)
        for i in range(48):
            for j in range(4):
                a = start+i*5+j
                for face in [(a,a+5,a+6),(a,a+6,a+1)]:
                    p,q,r = [Vector(lid_vertices[k]) for k in face]
                    if (q-p).cross(r-p).y>0: face = tuple(reversed(face))
                    lid_faces.append(face)
mesh = bpy.data.meshes.new('Rolled eyelid rims')
mesh.from_pydata(lid_vertices,[],lid_faces); mesh.update()
obj = bpy.data.objects.new('Skin eyelid rims',mesh)
bpy.context.scene.collection.objects.link(obj)
mesh.materials.append(skin.data.materials[0])
colour = mesh.color_attributes.new(name='Color',type='BYTE_COLOR',domain='CORNER')
for loop in mesh.loops: colour.data[loop.index].color = lid_colors[loop.vertex_index]
for poly in mesh.polygons: poly.use_smooth = True

def smooth(a, b, value):
    t = np.clip((value-a)/(b-a), 0, 1)
    return t*t*(3-2*t)

def sculpt(points):
    # Anatomical coordinates: x lateral, h vertical, d forwards.
    x, h, d = points[:, 0], points[:, 2], -points[:, 1]
    moved = points.copy()
    head = smooth(.337, .349, h)
    face = smooth(.012, .029, d)*head
    # Taper the lower cheek into the chin without narrowing the upper face.
    jaw = np.exp(-((h-.341)/.017)**2)*smooth(.012, .032, abs(x))
    moved[:, 0] -= x*.13*jaw*head
    # Bring the central chin into the soft lower face and give it a fuller tip.
    chin = np.exp(-(x/.022)**2-((h-.331)/.013)**2)*face
    moved[:, 2] += .0028*chin
    moved[:, 1] -= .0035*chin
    # A recessed bridge and a shorter, rounded projecting nose.
    bridge = np.exp(-(x/.008)**2-((h-.381)/.016)**2)*face
    moved[:, 1] += .0030*bridge
    tip = np.exp(-(x/.010)**2-((h-.358)/.009)**2)*face
    moved[:, 2] += .0031*tip
    moved[:, 0] -= x*.10*tip
    # The mouth is a modest smile with real vermilion volume in profile.
    mouth = np.exp(-((h-.346)/.007)**2-(x/.020)**4)*face
    moved[:, 0] += x*.17*mouth
    moved[:, 2] += .0008*mouth*(abs(x)/.017)**2
    upper = np.exp(-((h-.347)/.0019)**2-(x/.016)**4)*face
    lower = np.exp(-((h-.3444)/.0020)**2-(x/.016)**4)*face
    moved[:, 1] -= .0019*upper+.0024*lower
    # Contain the eyeball with a gently raised lower lid and softened upper rim.
    t = np.clip((abs(x)-.0115)/.0215, 0, 1)
    eye_band = np.exp(-((abs(x)-.0222)/.013)**8-((h-.3840)/.0065)**4)*face
    lower_lid = .00035*np.exp(-((h-.3815)/.0024)**2)
    upper_lid = .00165*np.exp(-((h-.3900)/.0035)**2)
    moved[:, 2] += (lower_lid+upper_lid)*np.sin(np.pi*t)*eye_band
    # More forehead around the shallow central peak, with lower temples retained.
    hairline = np.exp(-((h-.414)/.018)**2)*smooth(.017,.040,d)*smooth(.401,.410,h)
    moved[:, 2] += (.0120-.0045*np.exp(-(x/.012)**2))*hairline
    # Ear silhouette: a smaller pinna, integrated with the temple.
    ear = np.exp(-((h-.381)/.016)**4-((d+.002)/.014)**4)*smooth(.040,.050,abs(x))
    moved[:, 0] -= np.sign(x)*.0035*ear
    bowl = np.exp(-((h-.383)/.009)**2-((d+.002)/.007)**2)*smooth(.038,.047,abs(x))
    moved[:, 0] -= np.sign(x)*.0020*bowl
    # A compact folded bun and three broad diagonal swept scalp ridges.
    bun = smooth(.438,.454,h)*(1-smooth(-.024,-.010,d))
    moved[:, 0] -= x*.09*bun
    moved[:, 1] += (d+.049)*.12*bun
    moved[:, 2] -= (h-.460)*.035*bun
    sweep = smooth(.410,.421,h)*(1-smooth(.449,.462,h))*smooth(.018,.039,d)
    ridges = sum(np.exp(-((x-(center+.90*(h-.429)))/.007)**2) for center in (-.022,.001,.022))
    moved[:, 1] -= .0015*ridges*sweep
    return moved

report = {}
for obj in bpy.context.scene.objects:
    if obj.type != 'MESH':
        continue
    mesh = obj.data
    # Refine only the large facial cells before shaping nose, lips and chin.
    # Keep the existing colour attributes and interpolate the authored normal
    # field onto the extra vertices; the body retains its original loop normals.
    if obj.name == 'Skin':
        old_points = np.array([v.co[:] for v in mesh.vertices])
        old_normals = np.array([n.vector[:] for n in mesh.corner_normals])
        old_faces = [tuple(p.vertices) for p in mesh.polygons]
        corner_field = [old_normals[p.loop_start:p.loop_start+p.loop_total] for p in mesh.polygons]
        surface = BVHTree.FromPolygons(old_points.tolist(),old_faces,all_triangles=True)
        bm = bmesh.new(); bm.from_mesh(mesh)
        edges = [e for e in bm.edges if all(.338<v.co.z<.379 and abs(v.co.x)<.036 and v.co.y<-.024 for v in e.verts) and e.calc_length()>.005]
        bmesh.ops.subdivide_edges(bm, edges=edges, cuts=2, use_grid_fill=True)
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        bm.to_mesh(mesh); bm.free()
        normals = [None]*len(mesh.loops)
        for poly in mesh.polygons:
            center = sum((mesh.vertices[i].co for i in poly.vertices),Vector())/3
            _,_,index,_ = surface.find_nearest(center)
            triangle = [Vector(old_points[i]) for i in old_faces[index]]
            field = [Vector(n) for n in corner_field[index]]
            for loop_index in poly.loop_indices:
                point = mesh.vertices[mesh.loops[loop_index].vertex_index].co
                normal = barycentric_transform(point,*triangle,*field).normalized()
                normals[loop_index] = normal
        mesh.normals_split_custom_set(normals)
    points = np.empty(len(mesh.vertices)*3, dtype=np.float64)
    mesh.vertices.foreach_get('co', points)
    points = points.reshape(-1,3)
    if obj.name == 'Copper brows':
        t = np.clip((abs(points[:,0])-.0105)/.025,0,1)
        points[:,2] -= .0012*np.sin(np.pi*t)
        for point in points:
            hit,_ = project(point[0],point[2])
            point[1] = hit.y-.0008
    normals = np.array([n.vector[:] for n in mesh.corner_normals])
    moved = sculpt(points)
    # Transform the existing authored normals by the inverse Jacobian. Keeping
    # the body normals exact also preserves its accepted faceted treatment.
    ids = np.array([loop.vertex_index for loop in mesh.loops])
    active = points[:,2]>.337
    jac = np.broadcast_to(np.eye(3), (len(points),3,3)).copy()
    for axis in range(3):
        delta = np.zeros_like(points[active]); delta[:,axis] = .00001
        jac[active,:,axis] = (sculpt(points[active]+delta)-sculpt(points[active]-delta))/.00002
    normals = np.einsum('nij,nj->ni', np.swapaxes(np.linalg.inv(jac[ids]),1,2), normals)
    normals /= np.linalg.norm(normals,axis=1)[:,None]
    mesh.vertices.foreach_set('co', moved.ravel())
    mesh.update()
    mesh.normals_split_custom_set(normals.tolist())
    assert np.array_equal(points[~active], moved[~active]), 'Body or neck join moved'
    report[obj.name] = {'vertices':len(points), 'movedVertices':int(np.count_nonzero(np.linalg.norm(moved-points,axis=1)>1e-9)), 'maxDisplacement':float(np.linalg.norm(moved-points,axis=1).max())}

# Pack the two user-supplied original sheets into this editable candidate.
for filename in ['ChatGPT Image 30 Sept 2026, 19_34_45.png', 'ChatGPT Image 30 Sept 2026, 19_34_55.png']:
    image = bpy.data.images.load(str(Path('/Users/craig/Downloads')/filename), check_existing=True)
    image.pack()
bpy.context.scene['reference'] = 'Original June front/profile/three-quarter sheets supplied September 30, 2026'
bpy.ops.wm.save_as_mainfile(filepath=str((output/'june-face-sculpt.blend').resolve()))
bpy.ops.export_scene.gltf(filepath=str((output/'mesh.glb').resolve()), export_format='GLB', export_animations=False, export_yup=True)
(output/'sculpt-report.json').write_text(json.dumps(report,indent=2)+'\n')
