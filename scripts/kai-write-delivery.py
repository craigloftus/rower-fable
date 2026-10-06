"""Record the exact Kai package and final validation witnesses."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
MASTER=ROOT/'art/characters/candidates/kai';OUT=ROOT/'validation/characters/kai'
def entry(path):
 data=path.read_bytes()
 return {'path':str(path.relative_to(ROOT)),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
assets=[MASTER/name for name in ['sculpt.blend','head-authored.blend','standing.glb','kai.blend','kai.glb','anatomy.json','README.md']]
inputs=[OUT/name for name in ['faceted-surface.ply','head-faceted-surface.ply','head-refined-surface.ply','head-colour-layout.npz','source-provenance.json']]
sources=json.loads((OUT/'source-provenance.json').read_text())
evidence=[OUT/name for name in ['report.json','measurements.json','blender-parity.json','body-report.json','grip-report.json','binding.json','performance.json','palette.json','head-placement.json','head-authoring.json','seat-fit.json','index.html']]
for folder in ['before-rest','after','after-head','final-review']:
 evidence.extend(sorted((OUT/folder).glob('*.png')))
evidence.extend(sorted(OUT.glob('browser-*.png')))
asset=entry(MASTER/'kai.glb');native=json.loads((OUT/'report.json').read_text());parity=json.loads((OUT/'blender-parity.json').read_text())
assert native['sha256']==asset['sha256']==parity['sha256']
assert parity['blendSha256']==entry(MASTER/'kai.blend')['sha256']
assert json.loads((OUT/'binding.json').read_text())['sourceSha256']==entry(MASTER/'standing.glb')['sha256']
report={'status':'Refinement complete; final runtime integration review pending; not installed',
 'boatFit':{'catchAngle':1.0,'seatFinish':.36,'pinY':.45,'inboard':.8,'gripRadius':.02},
 'finalGLB':asset,'triangles':native['triangles'],
 'limitations':['Interpretation of a single original illustration, not a pixel-identical likeness','Retained joined fingers have angular tips; bent shorts retain a normal hip fold','Headless desktop call timings do not establish Pixel 8 thermal performance'],
 'assets':list(map(entry,assets)),'curatedInputs':list(map(entry,inputs)),'provenance':sources,
 'authoring':list(map(entry,sorted((ROOT/'scripts').glob('kai-*')))),
 'evidence':list(map(entry,evidence))}
(MASTER/'delivery.json').write_text(json.dumps(report,indent=2)+'\n')
(OUT/'delivery-hashes.json').write_text(json.dumps({e['path']:e['sha256'] for e in report['assets']+report['curatedInputs']+report['provenance']},indent=2)+'\n')
print(asset)
