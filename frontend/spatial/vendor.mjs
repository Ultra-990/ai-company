// Reproducible local assets; browsers never contact a CDN.
import { readFile, writeFile, mkdir, copyFile } from 'node:fs/promises';
const source = new URL('./node_modules/three/', import.meta.url);
const target = new URL('../../app/static/spatial/vendor/', import.meta.url);
await mkdir(target, {recursive:true});
for (const name of ['three.module.js', 'three.core.js']) {
  await copyFile(new URL(`build/${name}`, source), new URL(name, target));
}
const renderer = await readFile(new URL('examples/jsm/renderers/CSS3DRenderer.js', source), 'utf8');
await writeFile(new URL('CSS3DRenderer.js', target), renderer.replace("from 'three'", "from './three.module.js'"));
await copyFile(new URL('LICENSE', source), new URL('THREE-LICENSE.txt', target));
