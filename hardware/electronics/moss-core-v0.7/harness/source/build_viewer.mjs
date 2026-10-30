/** Build one offline HTML file from the assembled GLB and optional route metadata. */
import { readFile, writeFile, mkdir, stat } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { dirname, resolve, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const source = dirname(fileURLToPath(import.meta.url));
const root = resolve(source, '..');
const require = createRequire(join(root, 'viewer_runtime', 'package.json'));
const { build } = require('esbuild');
const args = process.argv.slice(2);
const argument = (name, fallback) => {
  const i = args.indexOf(name);
  return i < 0 ? fallback : resolve(args[i + 1]);
};
const modelPath = argument('--model', join(root, 'output', 'MOSS_HARNESS_ASSEMBLY.glb'));
const routesPath = argument('--routes', join(root, 'output', 'ROUTE_LENGTHS.json'));
const outputPath = argument('--output', join(root, 'output', 'MOSS_HARNESS_VIEWER.html'));
if (args.includes('--help')) {
  console.log('node source/build_viewer.mjs [--model assembly.glb] [--routes routes.json] [--output viewer.html]');
  process.exit(0);
}

// Fail clearly before doing any work when the assembly is not yet available.
await stat(modelPath).catch(() => { throw new Error(`Assembly GLB not found: ${modelPath}`); });
const model = await readFile(modelPath);
if (model.readUInt32LE(0) !== 0x46546c67 || model.readUInt32LE(4) !== 2) {
  throw new Error('Expected a GLB version 2 file.');
}
const glbJsonLength = model.readUInt32LE(12);
const glbJson = JSON.parse(model.subarray(20, 20 + glbJsonLength).toString('utf8'));
const external = [...(glbJson.buffers || []), ...(glbJson.images || [])].filter(item => item.uri && !item.uri.startsWith('data:'));
if (external.length) throw new Error('The GLB contains external resources; pack them into the GLB before building the offline viewer.');
let routeData = { routes: [] };
try { routeData = JSON.parse(await readFile(routesPath, 'utf8')); }
catch (error) { if (error.code !== 'ENOENT') throw error; }
const bundled = await build({
  entryPoints: [join(source, 'viewer_app.js')],
  nodePaths: [join(root, 'viewer_runtime', 'node_modules')],
  bundle: true, write: false, minify: true, format: 'iife',
  target: ['es2020'], legalComments: 'inline', charset: 'utf8',
});
const css = await readFile(join(source, 'viewer.css'), 'utf8');
const shell = await readFile(join(source, 'viewer_shell.html'), 'utf8');
const escapeScript = value => value.replace(/<\//g, '<\\/').replace(/\u2028/g, '\\u2028').replace(/\u2029/g, '\\u2029');
const html = shell
  .replace('/* INLINE_VIEWER_CSS */', () => css)
  .replace('INLINE_GLB_BASE64', () => model.toString('base64'))
  .replace('INLINE_ROUTE_JSON', () => escapeScript(JSON.stringify(routeData)))
  .replace('/* INLINE_VIEWER_JS */', () => escapeScript(bundled.outputFiles[0].text));
await mkdir(dirname(outputPath), { recursive: true });
await writeFile(outputPath, html, 'utf8');
console.log(JSON.stringify({
  status: 'OFFLINE_VIEWER_READY', output: outputPath, bytes: Buffer.byteLength(html),
  model: modelPath, model_bytes: model.byteLength, route_metadata: routesPath,
  bundled_dependencies: ['three@0.170.0', 'esbuild@0.24.0'], network_requests_required: 0,
}, null, 2));
