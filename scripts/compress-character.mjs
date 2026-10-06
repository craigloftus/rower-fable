// Lossless transport compression. No decimation, quantization or animation resampling.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS, EXTMeshoptCompression } from '@gltf-transform/extensions';
import { MeshoptEncoder, MeshoptDecoder } from 'meshoptimizer';

const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const arrayHash = accessor => hash(new Uint8Array(accessor.getArray().buffer,
  accessor.getArray().byteOffset, accessor.getArray().byteLength));

function snapshot(document) {
  const root = document.getRoot();
  return {
    nodes: root.listNodes().map(node => ({name:node.getName(), extras:node.getExtras(),
      translation:node.getTranslation(), rotation:node.getRotation(), scale:node.getScale(),
      children:node.listChildren().map(child=>child.getName())})),
    skins: root.listSkins().map(skin => ({joints:skin.listJoints().map(joint=>joint.getName()),
      matrices:arrayHash(skin.getInverseBindMatrices())})),
    meshes: root.listMeshes().map(mesh => ({extras:mesh.getExtras(), primitives:mesh.listPrimitives().map(primitive => ({
      attributes:primitive.listSemantics().sort().map(semantic=>[semantic,arrayHash(primitive.getAttribute(semantic))]),
      material:primitive.getMaterial()?.getName(), mode:primitive.getMode(),
    }))})),
    animations: root.listAnimations().map(animation => ({name:animation.getName(), channels:animation.listChannels().map(channel=>({
      node:channel.getTargetNode().getName(), path:channel.getTargetPath(),
      interpolation:channel.getSampler().getInterpolation(),
      input:arrayHash(channel.getSampler().getInput()), output:arrayHash(channel.getSampler().getOutput()),
    }))})),
    materials: root.listMaterials().map(material=>({name:material.getName(), colour:material.getBaseColorFactor(),
      roughness:material.getRoughnessFactor(), metalness:material.getMetallicFactor(),
      emissive:material.getEmissiveFactor(), alpha:material.getAlphaMode(), doubleSided:material.getDoubleSided()})),
    textures:root.listTextures().map(texture=>hash(texture.getImage())),
  };
}

// The SDK omits near-identity node transforms. Retain Blender's exact values.
function preserveTransforms(source, encoded) {
  const readJSON = bytes => JSON.parse(Buffer.from(bytes).subarray(20,20+Buffer.from(bytes).readUInt32LE(12)));
  const original = readJSON(source), json = readJSON(encoded);
  assert.equal(json.nodes.length,original.nodes.length);
  json.nodes.forEach((node,i)=>{
    assert.equal(node.name,original.nodes[i].name);
    for(const key of ['translation','rotation','scale','matrix']) {
      if(key in original.nodes[i])node[key]=original.nodes[i][key];
      else delete node[key];
    }
  });
  const text=Buffer.from(JSON.stringify(json));
  const size=Math.ceil(text.length/4)*4;
  const chunk=Buffer.from(encoded).subarray(20+Buffer.from(encoded).readUInt32LE(12));
  const output=Buffer.alloc(20+size+chunk.length,32);
  output.writeUInt32LE(0x46546c67,0);output.writeUInt32LE(2,4);output.writeUInt32LE(output.length,8);
  output.writeUInt32LE(size,12);output.writeUInt32LE(0x4e4f534a,16);
  text.copy(output,20);chunk.copy(output,20+size);
  return output;
}

export async function compressCharacter(input, output) {
  assert.notEqual(resolve(input),resolve(output),'Keep the editable export separate from its compressed delivery');
  await Promise.all([MeshoptEncoder.ready,MeshoptDecoder.ready]);
  const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({
    'meshopt.encoder':MeshoptEncoder,'meshopt.decoder':MeshoptDecoder,
  });
  const original = await readFile(input);
  const document = await io.readBinary(original);
  const before = snapshot(document);
  document.createExtension(EXTMeshoptCompression).setRequired(true)
    // QUANTIZE selects the unfiltered encoder; no quantize() transform is applied.
    .setEncoderOptions({method:EXTMeshoptCompression.EncoderMethod.QUANTIZE});
  const compressed = preserveTransforms(original,await io.writeBinary(document));
  const decoded = await io.readBinary(compressed);
  assert.deepEqual(snapshot(decoded),before,'Decoded geometry, shading, skinning and animation must be bit-identical');
  // Meshopt can rotate triangle corners, but never reverse or reorder triangles.
  document.getRoot().listMeshes().forEach((mesh,m)=>mesh.listPrimitives().forEach((primitive,p)=>{
    const a=primitive.getIndices().getArray(),b=decoded.getRoot().listMeshes()[m].listPrimitives()[p].getIndices().getArray();
    assert.equal(a.length,b.length);
    for(let i=0;i<a.length;i+=3) {
      assert([0,1,2].some(rotation=>[0,1,2].every(j=>a[i+j]===b[i+(j+rotation)%3])),`Triangle changed at ${m}/${p}/${i/3}`);
    }
  }));
  await mkdir(dirname(output),{recursive:true});
  await writeFile(output,compressed);
  const report={input,output,sourceSha256:hash(original),sha256:hash(compressed),
    sourceBytes:original.length,bytes:compressed.length,savedPercent:100*(1-compressed.length/original.length),
    lossless:true,trianglesRemoved:0};
  await writeFile(`${output}.json`,JSON.stringify(report,null,2)+'\n');
  return report;
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href) {
  const [input,output]=process.argv.slice(2);
  assert(input&&output,'Usage: node scripts/compress-character.mjs input.glb output.glb');
  console.log(await compressCharacter(input,output));
}
