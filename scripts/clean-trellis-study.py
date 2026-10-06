"""Prepare reconstructed June meshes for sculpt review, retaining source UVs.

Removes the generated head pedestal and replaces noisy garment materials with
the reference's simple rowing kit. This does not change the production rig.
Run with the TripoSR virtual environment (trimesh, numpy, Pillow).
"""
from pathlib import Path
import numpy as np
import trimesh
from trimesh.visual.color import uv_to_color
from trimesh.visual.material import PBRMaterial

ROOT = Path(__file__).resolve().parents[1]/'validation/reconstruction'

def matte(mesh):
    mesh.visual.material.metallicFactor = 0
    mesh.visual.material.roughnessFactor = .9
    mesh.visual.material.alphaMode = 'OPAQUE'
    return mesh

def solid(name, rgb, roughness=.9):
    srgb = np.array(rgb)/255
    linear = np.where(srgb<=.04045, srgb/12.92, ((srgb+.055)/1.055)**2.4)
    factor = np.append(np.round(linear*255),255).astype(np.uint8)
    return PBRMaterial(name=name, baseColorFactor=factor, metallicFactor=0, roughnessFactor=roughness)

body = matte(trimesh.load(ROOT/'trellis/mesh.glb', force='mesh'))
colour = uv_to_color(body.visual.uv, body.visual.material.baseColorTexture)[body.faces].mean(axis=1)
p = body.triangles_center
r, g, b = colour[:, :3].T
torso = (p[:, 1]>.045)&(p[:, 1]<.32)&(np.abs(p[:, 0])<.13)
shirt = torso&(r>1.7*g)&(g<110)
stripe = torso&(r>190)&(g>160)&(b>130)&(p[:, 1]<.24)
shorts = (p[:, 1]>-.17)&(p[:, 1]<.10)&(np.abs(p[:, 0])<.13)&(r<75)&(g<65)
shirt |= (p[:,1]>.185)&(p[:,1]<.23)&(np.abs(p[:,0])<.082)&(p[:,2]>.04)
scene = trimesh.Scene()
for name, mask, rgba in [
    ('Skin hair and shoes', ~(shirt|stripe|shorts), None),
    ('Charcoal shorts', shorts, [51, 54, 50, 255]),
]:
    part = body.submesh([np.flatnonzero(mask)], append=True)
    if rgba:part.visual.material = solid(name, rgba[:3])
    scene.add_geometry(part, geom_name=name)

# Cut the cream band through actual triangles, giving it a clean garment edge.
# Each polygon entry contains a position and the source surface normal.
def split(poly, height):
    above=[];below=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        da=a[0][1]-height;db=b[0][1]-height
        (above if da>=0 else below).append(a)
        if (da>=0)!=(db>=0):
            t=da/(da-db);point=(a[0]*(1-t)+b[0]*t,a[1]*(1-t)+b[1]*t)
            above.append(point);below.append(point)
    return above,below
polys={'Terracotta singlet':[], 'Cream stripe':[]}
for face in body.faces[shirt|stripe]:
    poly=[(body.vertices[i],body.vertex_normals[i]) for i in face]
    if np.mean([p[0][2] for p in poly])>.035:
        top,lower=split(poly,.218);middle,bottom=split(lower,.200)
        polys['Terracotta singlet'] += [top,bottom]
        polys['Cream stripe'].append(middle)
    else:polys['Terracotta singlet'].append(poly)
for name,rgb in [('Terracotta singlet',[173,92,64]),('Cream stripe',[239,225,194])]:
    verts=[];normals=[];faces=[]
    for poly in polys[name]:
        start=len(verts)
        for p,n in poly:verts.append(p);normals.append(n/np.linalg.norm(n))
        faces.extend([[start,start+i,start+i+1] for i in range(1,len(poly)-1)])
    part=trimesh.Trimesh(verts,faces,vertex_normals=normals,process=False,
        visual=trimesh.visual.TextureVisuals(uv=np.zeros((len(verts),2)),material=solid(name,rgb)))
    scene.add_geometry(part,geom_name=name)
out = ROOT/'trellis-clean'
out.mkdir(exist_ok=True)
scene.export(out/'mesh.glb', include_normals=True)

head = matte(trimesh.load(ROOT/'trellis-head/mesh.glb', force='mesh'))
keep = (head.vertices[head.faces, 1]>-.175).all(axis=1)
head = head.submesh([np.flatnonzero(keep)], append=True)
out = ROOT/'trellis-clean-head'
out.mkdir(exist_ok=True)
p = head.triangles_center
# The reconstruction filled the sclera with iris colour. Restore the corners
# on the existing curved eye surface while retaining the upper lash and iris.
eye = (np.abs(p[:, 0])>.018)&(np.abs(p[:, 0])<.082)&(p[:, 1]>-.028)&(p[:, 1]<.023)&(p[:, 2]>.15)
eye_mesh = head.submesh([np.flatnonzero(eye)], append=True)
# Add resolution only where the curved iris boundary crosses source triangles.
# Interpolate source UVs and normals so this does not change the sculpted surface.
vs=[]; uvs=[]; normals=[]; fs=[]
n=8
for face in eye_mesh.faces:
    grid={}
    for i in range(n+1):
        for j in range(n+1-i):
            weights=np.array([1-(i+j)/n,i/n,j/n])
            grid[i,j]=len(vs)
            vs.append(weights@eye_mesh.vertices[face])
            uvs.append(weights@eye_mesh.visual.uv[face])
            normal=weights@eye_mesh.vertex_normals[face]
            normals.append(normal/np.linalg.norm(normal))
    for i in range(n):
        for j in range(n-i):
            fs.append([grid[i,j],grid[i+1,j],grid[i,j+1]])
            if i+j<n-1:fs.append([grid[i+1,j],grid[i+1,j+1],grid[i,j+1]])
detail=trimesh.Trimesh(vs,fs,vertex_normals=normals,process=False,
    visual=trimesh.visual.TextureVisuals(uv=uvs,material=head.visual.material))
p=detail.triangles_center
uv=detail.visual.uv[detail.faces].mean(axis=1)
colour=uv_to_color(uv,head.visual.material.baseColorTexture)
outside_iris=((np.abs(p[:,0])-.048)/.014)**2+((p[:,1]+.002)/.019)**2>1
white=outside_iris&(colour[:,:3].max(axis=1)<85)&(p[:,1]<.010)
scene = trimesh.Scene()
scene.add_geometry(head.submesh([np.flatnonzero(~eye)], append=True), geom_name='Head')
scene.add_geometry(detail.submesh([np.flatnonzero(~white)], append=True),geom_name='Iris and lids')
sclera = detail.submesh([np.flatnonzero(white)], append=True)
sclera.visual.material = solid('Warm sclera', [245, 232, 206], .45)
scene.add_geometry(sclera, geom_name='Eye whites')
scene.export(out/'mesh.glb', include_normals=True)
print('Clean head:', len(head.faces), 'triangles; body garment faces:', int(shirt.sum()), int(stripe.sum()), int(shorts.sum()))
