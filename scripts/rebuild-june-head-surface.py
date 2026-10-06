"""Fine-resolution head repair preserving ear, lip and hair contours.

The body repair grid is too coarse for these features. Build the head at
0.3 mm source resolution, closing only sub-millimetre reconstruction cracks.
"""
from pathlib import Path
import numpy as np
import trimesh
from scipy import ndimage
from skimage.measure import marching_cubes
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'validation/reconstruction/june-final'
source=trimesh.load(ROOT/'validation/reconstruction/trellis-assembled/mesh.glb').geometry['Head']
mesh=trimesh.Trimesh(source.vertices,source.faces,process=True)
pitch=.0003
cache=OUT/'head-occupancy.npz'
if cache.exists():
    data=np.load(cache);shell=data['shell'];origin=data['origin']
else:
    print('Rasterising native head at',pitch,flush=True)
    vox=mesh.voxelized(pitch);shell=np.pad(vox.matrix,6)
    origin=vox.transform[:3,3]-6*pitch
    # Close only the intentionally open base of the neck before filling.
    lower=6
    shell[:,lower,:]=ndimage.binary_fill_holes(ndimage.binary_closing(shell[:,lower,:],iterations=2))
    np.savez_compressed(cache,shell=shell,origin=origin)
solid=shell.copy()
for axis in range(3):
    sections=np.moveaxis(solid,axis,0)
    for section in sections:
        section[:]=ndimage.binary_fill_holes(ndimage.binary_closing(section,iterations=2))
solid=ndimage.binary_fill_holes(ndimage.binary_closing(solid,iterations=2))
labels,_=ndimage.label(solid);sizes=np.bincount(labels.ravel());sizes[0]=0
solid=labels==sizes.argmax()
print('Head volume:',solid.sum()*pitch**3,flush=True)
field=ndimage.gaussian_filter(solid.astype(np.float32),sigma=.5)
v,f,_,_=marching_cubes(field,.5,spacing=(pitch,)*3)
v+=origin
result=trimesh.Trimesh(v,f,process=True);result.fix_normals()
result.export(OUT/'fine-head-solid.ply')
print('Fine head:',len(result.faces),'triangles',result.is_watertight,result.volume,flush=True)
