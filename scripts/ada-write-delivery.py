"""Record Ada's exact editable package, compact inputs and final evidence."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
MASTER=ROOT/'art/characters/candidates/ada';OUT=ROOT/'validation/characters/ada'
def entry(path):
 data=path.read_bytes()
 return {'path':str(path.relative_to(ROOT)),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
assets=[MASTER/name for name in ['sculpt.blend','head-authored.blend','standing.glb','ada.blend','ada.glb','anatomy.json','README.md']]
inputs=[OUT/name for name in ['faceted-surface.ply','head-faceted-surface.ply','head-colour-layout.npz','source-provenance.json']]
evidence=[OUT/name for name in ['report.json','measurements.json','blender-parity.json','body-report.json','grip-report.json','binding.json','landmarks.json','performance.json','palette.json','head-placement.json','head-refinement.json','head-retopology.json','hand-refinement.json','colour-layout-check.json','seat-fit.json','index.html','README.md']]
for folder in ['before-rest','after','after-head','final-review']:
 evidence.extend(sorted((OUT/folder).glob('*.png')))
evidence.extend(sorted(OUT.glob('browser-*.png')))
asset=entry(MASTER/'ada.glb');native=json.loads((OUT/'report.json').read_text());parity=json.loads((OUT/'blender-parity.json').read_text())
assert native['sha256']==asset['sha256']==parity['sha256']
assert parity['blendSha256']==entry(MASTER/'ada.blend')['sha256']
assert json.loads((OUT/'binding.json').read_text())['sourceSha256']==entry(MASTER/'standing.glb')['sha256']
boat_fit=json.loads((OUT/'layout.json').read_text())['boatFit']
assert set(boat_fit)=={'catchAngle','seatFinish','pinY','inboard','gripRadius'}
report={'status':'Refinement complete; visual review accepted; runtime integration pending; not installed',
 'boatFit':boat_fit,'finalGLB':asset,'triangles':native['triangles'],
 'limitations':['Interpretation of one original illustration; unseen surfaces inferred','Retained joined fingers and deeply bent shorts remain deliberately angular','Uncompressed editable export is 8.29 MB with 147572 vertices; use verified lossless delivery compression','Desktop submission timing does not establish sustained GPU completion or Pixel 8 thermal performance'],
 'assets':list(map(entry,assets)),'curatedInputs':list(map(entry,inputs)),
 'provenance':json.loads((OUT/'source-provenance.json').read_text())['sources'],
 'authoring':list(map(entry,sorted((ROOT/'scripts').glob('ada-*')))),
 'evidence':list(map(entry,evidence))}
(MASTER/'delivery.json').write_text(json.dumps(report,indent=2)+'\n')
(OUT/'delivery-hashes.json').write_text(json.dumps({e['path']:e['sha256'] for e in report['assets']+report['curatedInputs']+report['provenance']},indent=2)+'\n')
print(asset)
print('Curated',len(assets),'assets,',len(inputs),'compact inputs,',len(report['authoring']),'scripts,',len(evidence),'evidence files')
