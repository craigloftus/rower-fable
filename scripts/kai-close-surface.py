"""Construct a closed outer surface from Kai's reconstruction.

The TRELLIS mesh contains open, doubled shells. Rasterise their surface, close
sub-millimetre cracks, and fill the enclosed volume before retopology. This
avoids interpreting the thin shell itself as the character's solid anatomy.
Run with the existing reconstruction Python environment.
"""
from pathlib import Path
import argparse
import json
import numpy as np
import trimesh
from trimesh.visual.color import uv_to_color
from scipy import ndimage
from scipy.interpolate import PchipInterpolator
from skimage.measure import marching_cubes

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'validation/characters/kai'
OUT.mkdir(exist_ok=True)
parser=argparse.ArgumentParser();parser.add_argument('--source',default='reconstructed.glb')
parser.add_argument('--prefix',default='');parser.add_argument('--pitch',type=float,default=.0012)
args=parser.parse_args()
mesh = trimesh.load(OUT/args.source,force='mesh')
# 1.1 mm in source units; the eventual adult rig is approximately 1.8x larger.
pitch = args.pitch
cache = OUT/(args.prefix+'surface-occupancy.npz')
if cache.exists():
    data = np.load(cache); shell = data['shell']; origin = data['origin']
else:
    print('Rasterising Kai reconstruction', flush=True)
    vox = mesh.voxelized(pitch)
    shell = np.pad(vox.matrix, 10)
    origin = vox.transform[:3,3]-10*pitch
    np.savez_compressed(cache, shell=shell, origin=origin)
# Recover the two reconstructed eye surfaces from their own observed points.
# Missing pupil triangles otherwise turn the eye globes into empty sockets.
# The convex closures retain the source eye extents; they are not new spheres.
eye_closures=[]
if args.prefix=='head-':
    data=np.load(OUT/'head-colour-samples.npz');p=data['positions'];c=data['colors'].astype(float)
    eye_color=((c[:,1]>c[:,0]*1.1)&(c[:,2]>c[:,0]*.9))|((c[:,0]<65)&(c[:,1]<65))
    for lower,upper in [(-.13,-.025),(.04,.15)]:
        mask=eye_color&(p[:,0]>lower)&(p[:,0]<upper)&(p[:,1]>-.04)&(p[:,1]<.058)&(p[:,2]>.145)
        eye=trimesh.convex.convex_hull(p[mask]);vox=eye.voxelized(pitch).fill()
        ids=np.round((vox.points-origin)/pitch).astype(int);shell[tuple(ids.T)]=True
        eye_closures.append({'sourcePoints':int(mask.sum()),'bounds':eye.bounds.tolist()})
# A 3D hole can leak through one damaged source triangle. Fill closed 2D
# sections in all three orientations first, then close the residual cracks.
solid = shell.copy()
for axis in range(3):
    sections = np.moveaxis(solid, axis, 0)
    for section in sections:
        section[:] = ndimage.binary_fill_holes(ndimage.binary_closing(section, iterations=3))
solid = ndimage.binary_fill_holes(ndimage.binary_closing(solid, iterations=3))
labels, count = ndimage.label(solid)
sizes = np.bincount(labels.ravel()); sizes[0] = 0
solid = labels == sizes.argmax()
print('Volume cells:', int(solid.sum()), 'surface cells:', int(shell.sum()), flush=True)
field = ndimage.gaussian_filter(solid.astype(np.float32), sigma=1.25)
if not args.prefix:
    # The singlet spans the ribcage as cloth. Remove reconstruction grooves
    # without rounding away the shoulder, arm or hand silhouettes.
    cloth = ndimage.gaussian_filter(solid.astype(np.float32), sigma=3.5)
    x=origin[0]+np.arange(solid.shape[0])*pitch
    y=origin[1]+np.arange(solid.shape[1])*pitch
    side=np.clip((.125-np.abs(x))/.02,0,1)
    vertical=np.minimum(np.clip((y-.05)/.035,0,1),np.clip((.31-y)/.03,0,1))
    blend=side[:,None,None]*vertical[None,:,None]
    field=field*(1-blend)+cloth*blend
    # Measured front envelopes span the source singlet. Its large recessed
    # grooves are inference damage, so rebuild that cloth span inside the
    # measured silhouette before extracting a closed surface.
    z=origin[2]+np.arange(solid.shape[2])*pitch
    levels=[.05,.08,.12,.16,.20,.24,.28,.31]
    width=np.interp(y,levels,[.082,.078,.077,.09,.107,.119,.114,.075])
    front=np.interp(y,levels,[.079,.079,.079,.081,.079,.064,.033,.023])
    ratio=np.abs(x[:,None])/width[None,:]
    envelope=.005+(front[None,:]-.005)*np.sqrt(np.maximum(0,1-ratio**2))
    target=np.clip((envelope[:,:,None]-z[None,None,:])/(pitch*2)+.5,0,1)
    edge=np.clip((.98-ratio)/.16,0,1)
    span=np.minimum(np.clip((y-.055)/.025,0,1),np.clip((.28-y)/.035,0,1))
    facing=np.clip((z+.002)/.015,0,1)
    blend=edge[:,:,None]*span[None,:,None]*facing[None,None,:]
    field=field*(1-blend)+target*blend
    # A smooth posterior cloth span removes the inferred accordion folds.
    # These values follow the original back/waist silhouette, not the rowing pose.
    back=PchipInterpolator(levels,[-.052,-.046,-.051,-.069,-.088,-.095,-.084,-.065])(y)
    back=np.clip(back,-.10,-.03)
    envelope=-.008+(back[None,:]+.008)*np.sqrt(np.maximum(0,1-ratio**2))
    target=np.clip((z[None,None,:]-envelope[:,:,None])/(pitch*2)+.5,0,1)
    span=np.minimum(np.clip((y-.05)/.03,0,1),np.clip((.31-y)/.04,0,1))
    facing=np.clip((-.008-z)/.018,0,1)
    blend=edge[:,:,None]*span[None,:,None]*facing[None,None,:]
    field=field*(1-blend)+target*blend
v, f, _, _ = marching_cubes(field, .5, spacing=(pitch,)*3,allow_degenerate=False)
v += origin
result = trimesh.Trimesh(v, f, process=False)
result.fix_normals()
assert result.is_watertight and result.volume > .006
result.export(OUT/(args.prefix+'solid.ply'))
(OUT/(args.prefix+'surface-report.json')).write_text(json.dumps({
    'sourceTriangles':len(mesh.faces), 'solidTriangles':len(result.faces),
    'pitch':pitch, 'volume':result.volume, 'watertight':result.is_watertight,
    'sourceEyeClosures':eye_closures,
    'method':'Surface occupancy, morphological crack closure, filled volume; not shell remeshing',
}, indent=2))
print('Saved solid:', len(result.faces), 'triangles', 'volume', result.volume, flush=True)
