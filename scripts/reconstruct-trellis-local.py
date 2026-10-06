"""Run the installed TRELLIS.2 Apple Silicon pipeline with native MLX DINOv3.

Use the trellis2mlx virtual environment. Arguments pass through to generate.py;
for example --image art/characters/june-concept.png --steps 8 --no-cascade
--target-faces 100000 --texture-size 2048 --output validation/reconstruction/trellis-local.glb.
"""
from pathlib import Path
import sys

runtime = Path.home()/'.local/share/rower-tools/trellis2mlx'
sys.path.insert(0, str(runtime))
import generate
from trellmlx.models.dinov3 import extract_features

def native_features(image_path, resolution=512):
    features = extract_features(image_path, image_size=resolution)
    print(f'  DINOv3 features: {features.shape} (native MLX)', flush=True)
    return features

generate._extract_image_features = native_features
generate.main()
