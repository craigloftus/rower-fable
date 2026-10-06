"""Construct a closed outer surface from Sol's reconstruction.

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
from skimage.measure import marching_cubes
from skimage.morphology import convex_hull_image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'validation/characters/sol'
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
    print('Rasterising Sol reconstruction', flush=True)
    vox = mesh.voxelized(pitch)
    shell = np.pad(vox.matrix, 10)
    origin = vox.transform[:3,3]-10*pitch
    np.savez_compressed(cache, shell=shell, origin=origin)
eye_closures=[]
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
if args.prefix=='head-':
    # Close the reconstructed neck windows in 3D. A convex horizontal fill
    # incorrectly bridged the chin to the throat, so preserve that concavity.
    neck=ndimage.binary_closing(solid,iterations=12)
    rows=origin[1]+np.arange(solid.shape[1])*pitch<-.22
    solid[:,rows,:]=neck[:,rows,:]
    # The source has narrow cheek caves left by missing triangles. Close their
    # volume locally rather than pulling the surrounding face into the pits.
    repaired=ndimage.binary_closing(solid,iterations=20)
    xx=origin[0]+np.arange(solid.shape[0])*pitch
    yy=origin[1]+np.arange(solid.shape[1])*pitch
    zz=origin[2]+np.arange(solid.shape[2])*pitch
    cheek=(abs(xx[:,None,None])>.105)&(abs(xx[:,None,None])<.245)&(yy[None,:,None]>-.20)&(yy[None,:,None]<.015)&(zz[None,None,:]>.10)
    solid|=repaired&cheek
print('Volume cells:', int(solid.sum()), 'surface cells:', int(shell.sum()), flush=True)
field = ndimage.gaussian_filter(solid.astype(np.float32), sigma=1.25)
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
