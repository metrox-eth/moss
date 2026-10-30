import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const $ = id => document.getElementById(id);
const stage = $('stage');
const canvas = $('scene');
const routeData = JSON.parse($('route-data').textContent);
const state = { mode: 'installed', sleeves: true, ties: true, mounts: true, labels: false, selected: null, top: false };
const kinds = new Set(['HULL', 'CORE', 'PI', 'CONTEXT', 'LID', 'STOP', 'WIRE', 'SLEEVE', 'CONNECTOR', 'MOUNT', 'TIE', 'LIDWIRE', 'LIDCONNECTOR']);
const movingKinds = new Set(['LID', 'STOP', 'LIDWIRE', 'LIDCONNECTOR']);
const hiddenInHarness = new Set(['HULL', 'CORE', 'PI', 'CONTEXT', 'LID', 'STOP', 'MOUNT', 'TIE']);
const routeKinds = new Set(['WIRE', 'SLEEVE', 'CONNECTOR', 'LIDWIRE', 'LIDCONNECTOR']);
const nodeInfo = name => { const parts = String(name || '').split('__'); return kinds.has(parts[0]) ? { kind: parts[0], token: parts[1] || '' } : null; };
const normalized = value => String(value).toLowerCase().replace(/[^a-z0-9]/g, '');
const friendly = value => String(value).replace(/[_-]+/g, ' ').replace(/\b\w/g, letter => letter.toUpperCase());
const pointVector = point => {
  const xyz = Array.isArray(point) ? point.slice(0, 3) : point && [point.x, point.y, point.z];
  return xyz && xyz.length === 3 && xyz.every(Number.isFinite) ? new THREE.Vector3(...xyz) : null;
};
const lengthString = value => Number.isFinite(value) ? `${value.toLocaleString('en-GB', { maximumFractionDigits: 1 })} mm` : '—';
const effectiveVisible = object => { for (let p = object; p; p = p.parent) if (!p.visible) return false; return true; };
let renderer, scene, camera, controls, assembly, grid, environment;
let dirty = true, tween = null, lastPointer = null;
const tagged = [], moveNodes = [], meshes = [], pickable = [], routes = new Map();

function fail(error) {
  console.error(error);
  $('loader').hidden = true;
  $('loader').style.display = 'none';
  $('load-error').hidden = false;
  $('load-error-detail').textContent = error?.message || String(error);
  $('scene-count').textContent = 'Model unavailable';
}

function getRouteRecords(data) {
  const supplied = Array.isArray(data) ? data : data?.routes;
  return Array.isArray(supplied) ? supplied : supplied && typeof supplied === 'object' ? Object.entries(supplied).map(([id, value]) => ({ id, ...value })) : [];
}

function registerRoute(raw, index = routes.size) {
  const id = String(raw.id ?? raw.route_id ?? raw.name ?? `route-${index + 1}`);
  const key = normalized(id);
  if (routes.has(key)) return routes.get(key);
  const points = (Array.isArray(raw.points_mm) ? raw.points_mm : Array.isArray(raw.centreline_points_mm) ? raw.centreline_points_mm : []).map(pointVector).filter(Boolean);
  const suppliedLength = raw.centreline_mm ?? raw.centerline_mm ?? raw.length_mm;
  let length = typeof suppliedLength === 'number' ? suppliedLength : typeof suppliedLength === 'string' && suppliedLength.trim() ? Number(suppliedLength) : NaN;
  if (!Number.isFinite(length) && points.length > 1) length = points.slice(1).reduce((sum, p, i) => sum + p.distanceTo(points[i]), 0);
  const route = { key, id, label: String(raw.label ?? raw.name ?? friendly(id)), length, points, objects: [], color: '#4b8b6a', position: null, labelNode: null, row: null, movesWithLid: false };
  routes.set(key, route);
  return route;
}
getRouteRecords(routeData).forEach(registerRoute);

function routeFor(info, create = false) {
  if (!info || !routeKinds.has(info.kind) || !info.token) return null;
  const key = normalized(info.token);
  if (routes.has(key)) return routes.get(key);
  // Some exporters sanitize an identifier before using it as a GLTF node name.
  const candidate = [...routes.values()].find(route => normalized(route.id) === key);
  if (candidate) return candidate;
  if (create && (info.kind === 'WIRE' || info.kind === 'SLEEVE' || info.kind === 'LIDWIRE')) return registerRoute({ id: info.token });
  return null;
}

function createRenderer() {
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setClearColor(0xf4f2ed, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.18;
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(39, 1, 0.1, 100000);
  camera.up.set(0, 0, 1);
  camera.position.set(350, -440, 320);
  controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.rotateSpeed = 0.7;
  controls.zoomSpeed = 0.8;
  controls.panSpeed = 0.75;
  controls.minPolarAngle = 0.0001;
  controls.maxPolarAngle = Math.PI - 0.015;
  controls.addEventListener('change', () => { dirty = true; });
  controls.addEventListener('start', () => { tween = null; setTopState(false); });
  scene.add(new THREE.HemisphereLight(0xffffff, 0x71817d, 2.05));
  const key = new THREE.DirectionalLight(0xfffcf3, 2.6);
  key.position.set(-180, -250, 420); scene.add(key);
  const fill = new THREE.DirectionalLight(0xd8e9ff, 1.05);
  fill.position.set(210, 170, 200); scene.add(fill);
  const pmrem = new THREE.PMREMGenerator(renderer);
  const room = new RoomEnvironment();
  environment = pmrem.fromScene(room, 0.04);
  scene.environment = environment.texture;
  room.dispose(); pmrem.dispose();
  new ResizeObserver(resize).observe(stage);
  resize();
  requestAnimationFrame(frame);
}

function resize() {
  if (!renderer) return;
  const width = Math.max(stage.clientWidth, 1), height = Math.max(stage.clientHeight, 1);
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  dirty = true;
}

function findInfo(object) {
  for (let p = object; p && p !== assembly; p = p.parent) {
    const info = nodeInfo(p.name);
    if (info) return info;
  }
  return null;
}

function routeColor(object) {
  const material = Array.isArray(object.material) ? object.material[0] : object.material;
  const attribute = object.geometry?.attributes?.color;
  if (attribute?.count) return new THREE.Color(attribute.getX(0), attribute.getY(0), attribute.getZ(0)).getStyle();
  return material?.color?.getStyle() || '#4b8b6a';
}

function inspectAssembly(root) {
  assembly = root;
  assembly.name = 'MOSS_HARNESS_ASSEMBLY';
  assembly.scale.multiplyScalar(1000); // Exported metres -> world-frame millimetres.
  scene.add(assembly);
  assembly.updateMatrixWorld(true);
  // Discover routes before associating connectors, independent of GLB node order.
  assembly.traverse(object => { const info = nodeInfo(object.name); if (info) routeFor(info, true); });
  assembly.traverse(object => {
    const info = nodeInfo(object.name);
    if (info) tagged.push({ object, ...info });
    if (!object.isMesh) return;
    const inherited = findInfo(object);
    const route = routeFor(inherited, true);
    // Clone before highlighting: GLTF materials may be shared across routes or the PCB.
    const originals = Array.isArray(object.material) ? object.material : [object.material];
    const clones = originals.map(material => {
      const copy = material.clone();
      copy.userData.harnessBase = { opacity: copy.opacity, transparent: copy.transparent, depthWrite: copy.depthWrite, emissive: copy.emissive?.clone(), emissiveIntensity: copy.emissiveIntensity };
      return copy;
    });
    object.material = Array.isArray(object.material) ? clones : clones[0];
    meshes.push({ object, info: inherited, route });
    if (route) { route.objects.push(object); pickable.push(object); if (route.objects.length === 1) route.color = routeColor(object); }
  });
  for (const record of tagged) {
    if (!movingKinds.has(record.kind)) continue;
    let ancestorMoves = false;
    for (let p = record.object.parent; p && p !== assembly; p = p.parent) if (movingKinds.has(nodeInfo(p.name)?.kind)) { ancestorMoves = true; break; }
    if (ancestorMoves) continue;
    const object = record.object;
    const startWorld = object.getWorldPosition(new THREE.Vector3());
    const raisedWorld = startWorld.clone().add(new THREE.Vector3(0, 0, 100));
    moveNodes.push({ object, installed: object.position.clone(), open: object.parent.worldToLocal(raisedWorld) });
  }
  for (const route of routes.values()) {
    if (route.points.length > 1) {
      const total = route.points.slice(1).reduce((sum, point, i) => sum + point.distanceTo(route.points[i]), 0);
      let distance = 0;
      for (let i = 1; i < route.points.length; i++) {
        const segment = route.points[i].distanceTo(route.points[i - 1]);
        if (distance + segment >= total / 2) { route.position = route.points[i - 1].clone().lerp(route.points[i], segment ? (total / 2 - distance) / segment : 0); break; }
        distance += segment;
      }
    } else if (route.points.length === 1) route.position = route.points[0].clone();
    if (!route.position && route.objects.length) {
      const box = new THREE.Box3();
      for (const object of route.objects) box.expandByObject(object);
      route.position = box.getCenter(new THREE.Vector3());
    }
    route.movesWithLid = route.objects.length > 0 && route.objects.every(object => ['LIDWIRE', 'LIDCONNECTOR'].includes(findInfo(object)?.kind));
  }
  const box = new THREE.Box3().setFromObject(assembly);
  const size = box.getSize(new THREE.Vector3());
  const extent = Math.ceil(Math.max(size.x, size.y) * 1.35 / 50) * 50;
  grid = new THREE.GridHelper(extent, Math.max(10, Math.round(extent / 20)), 0xa9b5a3, 0xbec9b7);
  grid.rotation.x = Math.PI / 2;
  grid.position.set(box.getCenter(new THREE.Vector3()).x, box.getCenter(new THREE.Vector3()).y, box.min.z - 1.5);
  grid.material.transparent = true; grid.material.opacity = 0.16; grid.material.depthWrite = false;
  scene.add(grid);
  buildRouteList();
  applyVisibility();
  fitView(false, true);
  $('scene-count').textContent = `${routes.size} routes`;
  $('loader').classList.add('done');
  setTimeout(() => { $('loader').style.display = 'none'; }, 450);
  dirty = true;
  window.__MOSS_HARNESS_VIEWER__ = { ready: true, routeCount: routes.size, taggedNodeCount: tagged.length, meshCount: meshes.length, units: 'mm', embedded: true, state, setMode, selectRoute, resetView: () => fitView(false, true) };
}

function buildRouteList() {
  const list = $('route-list'); list.replaceChildren();
  $('route-count').textContent = String(routes.size).padStart(2, '0');
  if (!routes.size) {
    const empty = document.createElement('div'); empty.className = 'route-empty';
    empty.textContent = 'The assembly is ready. Route details are not included in this model.';
    list.append(empty); return;
  }
  for (const route of routes.values()) {
    const row = document.createElement('button'); row.className = 'route-row'; row.type = 'button'; row.setAttribute('aria-pressed', 'false');
    row.style.setProperty('--route-color', route.color);
    const dot = document.createElement('span'); dot.className = 'route-dot';
    const name = document.createElement('span'); name.className = 'route-name'; name.textContent = route.label;
    const length = document.createElement('span'); length.className = 'route-length'; length.textContent = lengthString(route.length);
    row.append(dot, name, length);
    row.title = `${route.label}${Number.isFinite(route.length) ? ` · ${lengthString(route.length)} centreline` : ''}`;
    row.addEventListener('click', () => selectRoute(state.selected === route.key ? null : route.key));
    route.row = row; list.append(row);
    const label = document.createElement('div'); label.className = 'route-label'; label.textContent = route.label; label.style.setProperty('--route-color', route.color); label.hidden = true;
    route.labelNode = label; $('labels').append(label);
  }
}

function applyVisibility() {
  for (const record of tagged) {
    let visible = true;
    if (state.mode === 'installed' && record.kind === 'LID') visible = false;
    if (state.mode === 'harness' && hiddenInHarness.has(record.kind)) visible = false;
    if ((record.kind === 'SLEEVE' || (record.kind === 'LIDWIRE' && /split_sleeve|braid_|band_/.test(record.object.name))) && !state.sleeves) visible = false;
    if (record.kind === 'TIE' && !state.ties) visible = false;
    if (record.kind === 'MOUNT' && !state.mounts) visible = false;
    record.object.visible = visible;
  }
  for (const record of moveNodes) record.object.position.copy(state.mode === 'open' ? record.open : record.installed);
  assembly?.updateMatrixWorld(true);
  dirty = true;
}

function setMode(mode) {
  if (!['installed', 'harness', 'open'].includes(mode)) return;
  state.mode = mode;
  for (const button of document.querySelectorAll('[data-mode]')) {
    const active = button.dataset.mode === mode; button.classList.toggle('active', active); button.setAttribute('aria-pressed', String(active));
  }
  $('scene-mode').textContent = { installed: 'Installed assembly', harness: 'Harness only', open: 'Lid raised · 100 mm' }[mode];
  applyVisibility();
  if (assembly) fitView(false);
}

function selectRoute(key) {
  const normalizedKey = key === null ? null : normalized(key);
  state.selected = routes.has(normalizedKey) ? normalizedKey : null;
  for (const route of routes.values()) {
    const active = route.key === state.selected;
    route.row?.classList.toggle('active', active); route.row?.setAttribute('aria-pressed', String(active)); route.labelNode?.classList.toggle('active', active);
  }
  for (const record of meshes) {
    const materials = Array.isArray(record.object.material) ? record.object.material : [record.object.material];
    for (const material of materials) {
      const base = material.userData.harnessBase;
      const dim = state.selected && record.route && record.route.key !== state.selected;
      material.opacity = dim ? Math.min(base.opacity, 0.2) : base.opacity;
      material.transparent = dim ? true : base.transparent;
      material.depthWrite = dim ? false : base.depthWrite;
      if (material.emissive && base.emissive) {
        material.emissive.copy(base.emissive);
        material.emissiveIntensity = base.emissiveIntensity;
        if (record.route && record.route.key === state.selected) { material.emissive.set(0x2d6548); material.emissiveIntensity = 0.24; }
      }
      material.needsUpdate = true;
    }
  }
  const route = routes.get(state.selected);
  $('selection-chip').hidden = !route;
  if (route) {
    $('selection-name').textContent = route.label;
    $('selection-length').textContent = Number.isFinite(route.length) ? `${lengthString(route.length)} · modeled centreline` : 'Centreline length unavailable';
    $('selection-dot').style.background = route.color;
  }
  dirty = true;
}

function visibleBounds() {
  const box = new THREE.Box3();
  for (const record of meshes) {
    const object = record.object;
    if (!effectiveVisible(object)) continue;
    if (!object.geometry.boundingBox) object.geometry.computeBoundingBox();
    box.union(object.geometry.boundingBox.clone().applyMatrix4(object.matrixWorld));
  }
  return box.isEmpty() ? new THREE.Box3(new THREE.Vector3(-100, -100, 0), new THREE.Vector3(100, 100, 80)) : box;
}

function setTopState(top) { state.top = top; $('top-view').classList.toggle('active', top); $('top-view').setAttribute('aria-pressed', String(top)); }
function fitView(top = false, immediate = false) {
  if (!assembly) return;
  const bounds = visibleBounds();
  const sphere = bounds.getBoundingSphere(new THREE.Sphere());
  const target = sphere.center.clone();
  const vfov = THREE.MathUtils.degToRad(camera.fov), hfov = 2 * Math.atan(Math.tan(vfov / 2) * camera.aspect);
  const distance = sphere.radius / Math.sin(Math.min(vfov, hfov) / 2) * 1.12;
  const direction = top ? new THREE.Vector3(0, -0.0002, 1) : new THREE.Vector3(0.92, -1.25, 1.03);
  const position = target.clone().add(direction.normalize().multiplyScalar(distance));
  controls.minDistance = Math.max(sphere.radius * 0.13, 8); controls.maxDistance = Math.max(distance * 7, 1000);
  setTopState(top);
  if (immediate || window.matchMedia('(prefers-reduced-motion: reduce)').matches) { camera.position.copy(position); controls.target.copy(target); tween = null; controls.update(); }
  else tween = { start: performance.now(), duration: 420, from: camera.position.clone(), to: position, fromTarget: controls.target.clone(), toTarget: target };
  dirty = true;
}

function updateLabels() {
  if (!assembly) return;
  const width = stage.clientWidth, height = stage.clientHeight;
  for (const route of routes.values()) {
    if (!route.labelNode) continue;
    const isVisible = state.labels && route.position && route.objects.some(effectiveVisible);
    if (!isVisible) { route.labelNode.hidden = true; continue; }
    const position = route.position.clone();
    if (state.mode === 'open' && route.movesWithLid) position.z += 100;
    position.project(camera);
    const x = (position.x * 0.5 + 0.5) * width + 10, y = (-position.y * 0.5 + 0.5) * height - 20;
    route.labelNode.hidden = position.z < -1 || position.z > 1 || x < 0 || x > width - 20 || y < 0 || y > height - 80;
    route.labelNode.style.transform = `translate(${Math.round(x)}px,${Math.round(y)}px)`;
  }
}

function frame(time) {
  requestAnimationFrame(frame);
  if (!renderer) return;
  if (tween) {
    const progress = Math.min(1, (time - tween.start) / tween.duration), eased = progress * progress * (3 - 2 * progress);
    camera.position.lerpVectors(tween.from, tween.to, eased); controls.target.lerpVectors(tween.fromTarget, tween.toTarget, eased);
    if (progress === 1) tween = null;
    dirty = true;
  }
  const moved = controls.update();
  if (dirty || moved) { renderer.render(scene, camera); updateLabels(); dirty = false; }
}

for (const button of document.querySelectorAll('[data-mode]')) button.addEventListener('click', () => setMode(button.dataset.mode));
$('top-view').addEventListener('click', () => fitView(true));
$('reset-view').addEventListener('click', () => { selectRoute(null); fitView(false); });
$('clear-route').addEventListener('click', () => selectRoute(null));
for (const key of ['sleeves', 'ties', 'mounts', 'labels']) $('toggle-' + key).addEventListener('change', event => { state[key] = event.target.checked; applyVisibility(); });
$('mobile-details').addEventListener('click', () => { const open = $('details').classList.toggle('open'); $('mobile-details').setAttribute('aria-expanded', String(open)); });
window.addEventListener('keydown', event => {
  if (event.target.matches('input,textarea,select') || event.ctrlKey || event.altKey || event.metaKey) return;
  if (event.key === '1') setMode('installed');
  else if (event.key === '2') setMode('harness');
  else if (event.key === '3') setMode('open');
  else if (event.key.toLowerCase() === 't') fitView(true);
  else if (event.key.toLowerCase() === 'r') { selectRoute(null); fitView(false); }
  else if (event.key === 'Escape') { selectRoute(null); $('details').classList.remove('open'); $('mobile-details').setAttribute('aria-expanded', 'false'); }
});
canvas.addEventListener('pointerdown', event => { if (event.button === 0) lastPointer = { x: event.clientX, y: event.clientY }; });
canvas.addEventListener('pointerup', event => {
  if (!lastPointer || event.button !== 0) return;
  const moved = Math.hypot(event.clientX - lastPointer.x, event.clientY - lastPointer.y); lastPointer = null;
  if (moved > 5 || !assembly) return;
  const rect = canvas.getBoundingClientRect();
  const ray = new THREE.Raycaster(); ray.setFromCamera(new THREE.Vector2((event.clientX - rect.left) / rect.width * 2 - 1, -(event.clientY - rect.top) / rect.height * 2 + 1), camera);
  const hit = ray.intersectObjects(pickable.filter(effectiveVisible), false)[0];
  if (hit) { const route = routeFor(findInfo(hit.object)); if (route) selectRoute(route.key); }
});
canvas.addEventListener('pointercancel', () => { lastPointer = null; });

try {
  createRenderer();
  requestAnimationFrame(() => {
    try {
      const encoded = $('model-data').textContent.trim();
      const binary = atob(encoded), bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      new GLTFLoader().parse(bytes.buffer, '', gltf => {
        try { inspectAssembly(gltf.scene); } catch (error) { fail(error); }
      }, fail);
      // The loaded arrays own their data; the bulky source text is no longer needed.
      $('model-data').textContent = '';
    } catch (error) { fail(error); }
  });
} catch (error) { fail(error); }
