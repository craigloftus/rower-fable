"""Construct a closed outer surface from June's approved reconstruction.

The TRELLIS mesh contains open, doubled shells. Rasterise their surface, close
sub-millimetre cracks, and fill the enclosed volume before retopology. This
avoids interpreting the thin shell itself as the character's solid anatomy.
Run with the TripoSR Python environment, then retopologize-june.py in Blender.
"""
from pathlib import Path
import json
import numpy as np
import trimesh
from scipy import ndimage
from skimage.measure import marching_cubes

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'validation/reconstruction/june-final'
OUT.mkdir(exist_ok=True)
source = trimesh.load(ROOT/'validation/reconstruction/trellis-assembled/mesh.glb')
mesh = trimesh.util.concatenate(list(source.geometry.values()))
# 1.1 mm in source units; the eventual adult rig is approximately 1.8x larger.
pitch = .001
cache = OUT/'surface-occupancy.npz'
if cache.exists():
    data = np.load(cache); shell = data['shell']; origin = data['origin']
else:
    print('Rasterising approved shape', flush=True)
    vox = mesh.voxelized(pitch)
    shell = np.pad(vox.matrix, 10)
    origin = vox.transform[:3,3]-10*pitch
    np.savez_compressed(cache, shell=shell, origin=origin)
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
field = ndimage.gaussian_filter(solid.astype(np.float32), sigma=.55)
v, f, _, _ = marching_cubes(field, .5, spacing=(pitch,)*3)
v += origin
result = trimesh.Trimesh(v, f, process=True)
result.fix_normals()
assert result.is_watertight and result.volume > .006
result.export(OUT/'solid.ply')
(OUT/'surface-report.json').write_text(json.dumps({
    'sourceTriangles':len(mesh.faces), 'solidTriangles':len(result.faces),
    'pitch':pitch, 'volume':result.volume, 'watertight':result.is_watertight,
    'method':'Surface occupancy, morphological crack closure, filled volume; not shell remeshing',
}, indent=2))
print('Saved solid:', len(result.faces), 'triangles', 'volume', result.volume, flush=True)
