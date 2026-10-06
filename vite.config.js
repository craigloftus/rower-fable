import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';

// Couple cached GLBs to the character build shipped with this application.
const characterRevision=createHash('sha256');
for(const id of ['kai','june','sol','ada']) {
  characterRevision.update(readFileSync(new URL(`./public/characters/${id}.glb`,import.meta.url)));
}

export default {
  base: '/rower-fable/',
  define: {'import.meta.env.CHARACTER_REVISION': JSON.stringify(characterRevision.digest('hex').slice(0,16))},
  server: {
    port: Number(process.env.PORT) || 5173,
    strictPort: !!process.env.PORT,
  },
};
