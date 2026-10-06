"""Sample the reconstructed texture inside faces, not just at UV seam vertices."""
from pathlib import Path
import numpy as np
import argparse
import trimesh
from trimesh.visual.color import uv_to_color
from scipy.ndimage import map_coordinates
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'validation/characters/sol'
parser=argparse.ArgumentParser();parser.add_argument('--body',action='store_true');args=parser.parse_args()
mesh=trimesh.load(OUT/('aligned-source.glb' if args.body else 'head-reconstructed.glb'),force='mesh',process=False)
positions=[];colors=[]
image=np.asarray(mesh.visual.material.baseColorTexture.convert('RGB'))
def sample(uv):
    xy=np.array([(1-uv[:,1])*image.shape[0]-.5,uv[:,0]*image.shape[1]-.5])
    return np.stack([map_coordinates(image[:,:,channel].astype(float),xy,order=1,mode='wrap') for channel in range(3)],axis=1).astype(np.uint8)
for i in range(5):
    for j in range(5-i):
        bary=np.array([i,j,4-i-j])/4
        positions.append(np.einsum('tij,i->tj',mesh.vertices[mesh.faces],bary))
        uv=np.einsum('tij,i->tj',mesh.visual.uv[mesh.faces],bary)
        colors.append(sample(uv))
np.savez_compressed(OUT/('body-colour-samples.npz' if args.body else 'head-colour-samples.npz'),positions=np.concatenate(positions),colors=np.concatenate(colors))
print('Interior texture samples',sum(len(p) for p in positions))
