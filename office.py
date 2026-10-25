"""Simulasi kantor 3D realistis (WebGL / Three.js) untuk Kantor AI Gudang.

Denah 26 x 16 m: Ruang HRD, Ruang Admin Control, Ruang Meeting, Koridor,
Ruang Operation Control, Ruang Asset Management, Ruang HSE, Ruang Server, plus Area Parkir.
Antar-ruangan dibatasi partisi kaca berpintu; agent berjalan lewat pintu.

Keadaan agent diambil dari kartu di database (sama seperti versi isometrik):

- jalan/antri -> agent duduk di meja dan mengetik
- nunggu_lu   -> agent berjalan ke area papan kartu, berdiri, melambai
- error       -> agent menunggu di area papan kartu, tampak panik
- tidak ada   -> agent keliling (pantry, lobby, ruang rapat, kontrol gudang, dll.)

Three.js dimuat dari CDN (jsdelivr), jadi tidak ada dependensi Python baru.
Orbit: seret = putar, scroll = zoom, klik kanan/dua jari = geser.
"""

import json

import streamlit.components.v1 as components

import core
from agents import AGENTS


# Nama yang tampil di label supervisor (karakter di Ruang Supervisor).
NAMA_SUPERVISOR = "Kamu"


def keadaan() -> dict:
    kartu = core.daftar_kartu()  # terbaru dulu
    agents = []
    for kunci, a in AGENTS.items():
        milik = [k for k in kartu if k["agent"] == kunci and k["status"] != "selesai"]
        pilihan = None
        for kelompok in (("nunggu_lu",), ("error",), ("jalan", "antri")):
            cocok = [k for k in milik if k["status"] in kelompok]
            if cocok:
                pilihan = cocok[0]
                break
        pesan = ""
        if pilihan:
            pengirim = "sistem" if pilihan["status"] == "error" else a["nama"]
            mine = [m for m in core.pesan_kartu(pilihan["id"]) if m["pengirim"] == pengirim]
            if mine:
                pesan = mine[-1]["teks"]
        agents.append(
            {
                "kunci": kunci,
                "nama": a["nama"],
                "peran": a["peran"],
                "gender": a["gender"],
                "status": pilihan["status"] if pilihan else "idle",
                "kode": pilihan["kode"] if pilihan else "",
                "judul": pilihan["judul"] if pilihan else "",
                "pesan": pesan,
            }
        )
    hitung = {
        "nunggu": sum(1 for k in kartu if k["status"] in ("nunggu_lu", "error")),
        "jalan": sum(1 for k in kartu if k["status"] in ("jalan", "antri")),
        "selesai": sum(1 for k in kartu if k["status"] == "selesai"),
    }
    return {"agents": agents, "counts": hitung, "supervisor": NAMA_SUPERVISOR}


def html_kantor() -> str:
    data = json.dumps(keadaan(), ensure_ascii=False).replace("</", "<\\/")
    return HTML.replace("__DATA__", data)


def tampilkan(height: int = 700):
    components.html(html_kantor(), height=height)


HTML = r"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
html,body{margin:0;height:100%;background:#0e1117;overflow:hidden;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
#w{position:absolute;inset:0;border-radius:12px;overflow:hidden;background:#0e1117}
#v{position:absolute;inset:0}
canvas{display:block;outline:none}
#lab{position:absolute;inset:0;pointer-events:none;overflow:hidden}
.lb{z-index:4;position:absolute;left:0;top:0;display:flex;flex-direction:column;align-items:center;gap:5px;will-change:transform;white-space:nowrap}
.tg{pointer-events:auto;cursor:pointer;background:rgba(15,17,23,.82);color:#fff;font:600 11px system-ui,sans-serif;padding:3px 9px;border-radius:7px;backdrop-filter:blur(3px);border:1px solid rgba(255,255,255,.12)}
.tg:hover{background:rgba(40,46,60,.95)}
.bb{position:relative;max-width:230px;white-space:normal;background:#fff;color:#1b1f27;font:12px/1.35 system-ui,sans-serif;padding:6px 9px;border-radius:9px;border:2px solid #3498db;box-shadow:0 4px 14px rgba(0,0,0,.35);text-align:left}
.bb:after{content:"";position:absolute;left:50%;bottom:-7px;margin-left:-5px;border:5px solid transparent;border-top-color:inherit}
.rl{z-index:1;position:absolute;left:0;top:0;will-change:transform;font:700 9px system-ui,sans-serif;letter-spacing:.12em;color:rgba(255,255,255,.8);background:rgba(15,17,23,.5);padding:2px 7px;border-radius:5px;white-space:nowrap}
.ttl{position:absolute;left:14px;top:10px;color:#e8e2d6;text-shadow:0 1px 4px rgba(0,0,0,.6);pointer-events:none}
.ttl b{display:block;font-size:13px}.ttl span{font-size:11px;color:#9aa3b2}
.hud{position:absolute;right:10px;top:10px;display:flex;gap:6px;align-items:center}
.hud button{background:rgba(15,17,23,.78);color:#e8e2d6;border:1px solid rgba(255,255,255,.16);border-radius:8px;padding:5px 10px;font:600 11px system-ui,sans-serif;cursor:pointer}
.hud button:hover{background:rgba(45,52,70,.95)}
.hud input{width:70px;accent-color:#9aa3b2}
#err{position:absolute;inset:0;display:none;align-items:center;justify-content:center;color:#e8e2d6;font:13px system-ui;text-align:center;padding:20px}
</style>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script>
</head><body>
<div id="w"><div id="v"></div><div id="lab"></div>
<div class="ttl"><b>JDC Distribution Center</b><span>Kantor AI · Cikarang · v8 pintu geser</span></div>
<div class="hud"><span style="font-size:11px;color:#9aa3b2">☀</span><input id="ex" type="range" min=".5" max="2" step=".05" value="1.1" title="Kecerahan"><button id="b1">⟲ Kamera</button><button id="b2">Kualitas: Auto</button></div>
<div id="err"></div></div>
<script>setTimeout(function(){if(!window.__ok){var e=document.getElementById('err');e.style.display='flex';e.textContent='Gagal memuat Three.js dari CDN (jsdelivr). Pastikan koneksi internet aktif lalu muat ulang halaman.';}},9000);</script>
<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
window.__ok = 1;

const D = __DATA__;
const SUP = D.supervisor || 'Supervisor';
const NX = 26, NZ = 16, WH = 3.0, WT = 0.12;
const $v = document.getElementById('v'), $lab = document.getElementById('lab');
const rnd = Math.random, lerp = (a, b, t) => a + (b - a) * t;

// =====================================================================
// Renderer, kamera, kontrol
// =====================================================================
let renderer;
try { renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' }); }
catch (e) { const el = document.getElementById('err'); el.style.display = 'flex'; el.textContent = 'WebGL tidak tersedia di browser ini.'; throw e; }
const MAXPR = Math.min(window.devicePixelRatio || 1, 2);
let pr = MAXPR;
renderer.setPixelRatio(pr);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.1;
$v.appendChild(renderer.domElement);
const ANI = Math.min(8, renderer.capabilities.getMaxAnisotropy());

const scene = new THREE.Scene();
const HORIZON = new THREE.Color('#d3e4f1');
scene.background = HORIZON;
scene.fog = new THREE.Fog(HORIZON, 55, 250);
scene.environment = new THREE.PMREMGenerator(renderer).fromScene(new RoomEnvironment(), 0.04).texture;

const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 520);
const HOME = { p: new THREE.Vector3(33, 24, 37.5), t: new THREE.Vector3(13, 0.6, 11) };
camera.position.copy(HOME.p);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.copy(HOME.t);
controls.enableDamping = true; controls.dampingFactor = 0.08;
controls.minDistance = 6; controls.maxDistance = 95;
// zoom roda mouse: langkah tetap kecil per "klik", tidak peduli seberapa besar delta dari mouse/trackpad
controls.enableZoom = false;
{ let lastW = 0;
  renderer.domElement.addEventListener('wheel', e => {
    e.preventDefault(); const now = performance.now(); if (now - lastW < 70) return; lastW = now;
    const off = camera.position.clone().sub(controls.target), d = off.length(), k = e.deltaY > 0 ? 1.07 : 1 / 1.07;
    off.setLength(Math.min(controls.maxDistance, Math.max(controls.minDistance, d * k))); camera.position.copy(controls.target).add(off);
  }, { passive: false });
}
controls.minPolarAngle = 0.15; controls.maxPolarAngle = 1.5;
controls.minAzimuthAngle = -0.2; controls.maxAzimuthAngle = Math.PI / 2 + 0.2;
controls.update();
const PAN_MIN = new THREE.Vector3(-4, 0, -4), PAN_MAX = new THREE.Vector3(30, 3, 25);

// =====================================================================
// Util: tekstur kanvas, material, mesh
// =====================================================================
function cv2(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; }
function ctex(c, srgb, rep) {
  const t = new THREE.CanvasTexture(c);
  if (srgb !== false) t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = ANI;
  if (rep) { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(rep[0], rep[1]); }
  return t;
}
function paint(w, h, fn, srgb, rep) { const c = cv2(w, h); fn(c.getContext('2d'), w, h); return ctex(c, srgb, rep); }
const NOISE = paint(256, 256, (g, w, h) => {
  const im = g.createImageData(w, h);
  for (let i = 0; i < w * h; i++) { const v = 100 + rnd() * 110; im.data[i * 4] = im.data[i * 4 + 1] = im.data[i * 4 + 2] = v; im.data[i * 4 + 3] = 255; }
  g.putImageData(im, 0, 0);
}, false, [1, 1]);
function noise(rx, ry) { const t = NOISE.clone(); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(rx, ry); t.needsUpdate = true; return t; }
const M = (c, o) => new THREE.MeshStandardMaterial(Object.assign({ color: c, roughness: 0.7, metalness: 0 }, o || {}));
const P = (c, o) => new THREE.MeshPhysicalMaterial(Object.assign({ color: c, roughness: 0.5, metalness: 0 }, o || {}));
const FAB = noise(5, 5);
const cloth = (c, r) => M(c, { roughness: r || 0.9, bumpMap: FAB, bumpScale: 0.7 });
const BX = (w, h, d) => new THREE.BoxGeometry(w, h, d);
const RB = (w, h, d, r) => new RoundedBoxGeometry(w, h, d, 3, r || 0.01);
function add(par, geo, mat, x, y, z, o) {
  const m = new THREE.Mesh(geo, mat);
  m.position.set(x || 0, y || 0, z || 0);
  if (o && o.r) m.rotation.set(o.r[0], o.r[1], o.r[2]);
  m.castShadow = !(o && o.nocast); m.receiveShadow = !(o && o.norecv);
  par.add(m); return m;
}
const S = new THREE.Group(); scene.add(S);   // semua objek statis (dibekukan di akhir)

const STEEL = M('#8d939b', { metalness: 0.85, roughness: 0.32 });
const BLACK = M('#15171b', { roughness: 0.5 });
const PLASTIC = M('#2a2d34', { roughness: 0.55 });
const WOOD = paint(512, 512, (g, w, h) => {
  g.fillStyle = '#b98a5a'; g.fillRect(0, 0, w, h);
  for (let i = 0; i < 150; i++) {
    g.strokeStyle = 'rgba(' + (70 + rnd() * 40 | 0) + ',' + (40 + rnd() * 25 | 0) + ',20,' + (0.05 + rnd() * 0.1) + ')';
    g.lineWidth = 0.5 + rnd() * 1.6; g.beginPath(); const y = rnd() * h; g.moveTo(0, y);
    g.bezierCurveTo(w * 0.3, y + rnd() * 14 - 7, w * 0.6, y + rnd() * 14 - 7, w, y); g.stroke();
  }
});
const AOT = paint(128, 128, (g, w, h) => {
  const r = g.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w / 2);
  r.addColorStop(0, 'rgba(0,0,0,.9)'); r.addColorStop(.55, 'rgba(0,0,0,.45)'); r.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = r; g.fillRect(0, 0, w, h);
});
const AOM = new THREE.MeshBasicMaterial({ map: AOT, transparent: true, opacity: 0.55, depthWrite: false, toneMapped: false });
function ao(cx, cz, w, d, o) {
  const m = new THREE.Mesh(new THREE.PlaneGeometry(w, d), o ? AOM.clone() : AOM);
  if (o) m.material.opacity = o;
  m.rotation.x = -Math.PI / 2; m.position.set(cx, 0.012, cz); m.renderOrder = 1; S.add(m); return m;
}

// =====================================================================
// Langit: kubah gradien + awan lembut
// =====================================================================
{
  const skyDome = paint(1024, 512, (g, w, h) => {
    const gr = g.createLinearGradient(0, 0, 0, h);
    gr.addColorStop(0, '#2f78d0'); gr.addColorStop(0.3, '#5fa3e6'); gr.addColorStop(0.44, '#a8d0f0'); gr.addColorStop(0.5, '#d3e4f1'); gr.addColorStop(1, '#d3e4f1');
    g.fillStyle = gr; g.fillRect(0, 0, w, h);
    for (let i = 0; i < 30; i++) {
      const cx = rnd() * w, cy = 60 + rnd() * 140, sc = 0.7 + rnd() * 1.2;
      for (let k = 0; k < 10; k++) {
        const x = cx + (k - 4.5) * 17 * sc, y = cy + (rnd() - 0.5) * 12 * sc, r = (18 + rnd() * 24) * sc;
        const rg = g.createRadialGradient(x, y, 0, x, y, r); rg.addColorStop(0, 'rgba(255,255,255,.62)'); rg.addColorStop(0.6, 'rgba(255,255,255,.22)'); rg.addColorStop(1, 'rgba(255,255,255,0)');
        g.fillStyle = rg; g.beginPath(); g.ellipse(x, y, r * 1.5, r * 0.62, 0, 0, 6.3); g.fill();
      }
    }
  });
  const dome = new THREE.Mesh(new THREE.SphereGeometry(400, 40, 20), new THREE.MeshBasicMaterial({ map: skyDome, side: THREE.BackSide, fog: false, toneMapped: false, depthWrite: false }));
  dome.renderOrder = -10; scene.add(dome);
}

// =====================================================================
// Pencahayaan
// =====================================================================
scene.add(new THREE.HemisphereLight(0xdfeaff, 0x9a8670, 0.55));
const sun = new THREE.DirectionalLight(0xfff0d8, 3.2);
sun.position.set(4, 14, -4); sun.target.position.set(13, 0, 8);
sun.castShadow = true;
{ const c = sun.shadow.camera; c.left = -21; c.right = 21; c.top = 17; c.bottom = -17; c.near = 1; c.far = 52; }
sun.shadow.bias = -0.0005; sun.shadow.normalBias = 0.05; sun.shadow.radius = 3;
sun.shadow.mapSize.set(3072, 3072);
scene.add(sun, sun.target);
const fill = new THREE.DirectionalLight(0xcfe0ff, 0.7); fill.position.set(30, 14, 30); scene.add(fill);
const LIGHTS = [];
[[4.5, 2.7, 4], [13, 2.7, 4], [21.5, 2.7, 4], [13, 2.7, 9], [3.5, 2.7, 13], [10.5, 2.7, 13], [17, 2.7, 13]].forEach(p => {
  const l = new THREE.PointLight(0xffe3bd, 9, 12, 2); l.position.set(p[0], p[1], p[2]); scene.add(l); LIGHTS.push(l);
});
{ const l = new THREE.PointLight(0x6fa8ff, 5, 6, 2); l.position.set(23, 2.2, 13); scene.add(l); LIGHTS.push(l); }

// rintangan untuk pathfinding
const OB = [];
function ob(x0, z0, x1, z1) { OB.push([Math.min(x0, x1), Math.min(z0, z1), Math.max(x0, x1), Math.max(z0, z1)]); }

// =====================================================================
// Lantai per zona
// =====================================================================
const grid = (g, w, h, n, c, lw) => { g.strokeStyle = c; g.lineWidth = lw; for (let i = 0; i <= n; i++) { const p = i * w / n; g.beginPath(); g.moveTo(p, 0); g.lineTo(p, h); g.stroke(); g.beginPath(); g.moveTo(0, p); g.lineTo(w, p); g.stroke(); } };
const speck = (g, w, h, n, a) => { for (let i = 0; i < n; i++) { const v = rnd() < 0.5 ? 255 : 0; g.fillStyle = 'rgba(' + v + ',' + v + ',' + v + ',' + a + ')'; g.fillRect(rnd() * w, rnd() * h, 2, 2); } };
const woodT = paint(1024, 1024, (g, w, h) => {
  const rows = 22, rh = h / rows;
  for (let r = 0; r < rows; r++) {
    let x = 0;
    while (x < w) {
      const len = Math.min(w - x, 250 + rnd() * 350), l = 38 + rnd() * 9, hue = 26 + rnd() * 7;
      g.fillStyle = 'hsl(' + hue + ',' + (38 + rnd() * 12) + '%,' + l + '%)'; g.fillRect(x, r * rh, len, rh);
      for (let k = 0; k < 14; k++) {
        g.strokeStyle = 'rgba(60,35,15,' + (0.05 + rnd() * 0.08) + ')'; g.lineWidth = 1; g.beginPath();
        const yy = r * rh + rnd() * rh; g.moveTo(x, yy);
        g.bezierCurveTo(x + len * 0.3, yy + rnd() * 4 - 2, x + len * 0.6, yy + rnd() * 4 - 2, x + len, yy); g.stroke();
      }
      g.fillStyle = 'rgba(0,0,0,.4)'; g.fillRect(x, r * rh, 2, rh); x += len;
    }
    g.fillStyle = 'rgba(0,0,0,.4)'; g.fillRect(0, r * rh, w, 2);
  }
}, true, [1, 1]);
const carpetT = paint(512, 512, (g, w, h) => { g.fillStyle = '#4b566a'; g.fillRect(0, 0, w, h); speck(g, w, h, 16000, 0.07); grid(g, w, h, 4, 'rgba(0,0,0,.28)', 2); }, true, [1, 1]);
const marbleT = paint(512, 512, (g, w, h) => {
  g.fillStyle = '#ebe8e2'; g.fillRect(0, 0, w, h);
  for (let i = 0; i < 30; i++) { g.strokeStyle = 'rgba(120,115,110,' + (0.05 + rnd() * 0.1) + ')'; g.lineWidth = 1 + rnd() * 2; g.beginPath(); let x = rnd() * w, y = rnd() * h; g.moveTo(x, y); for (let k = 0; k < 5; k++) { x += rnd() * 120 - 40; y += rnd() * 120 - 40; g.lineTo(x, y); } g.stroke(); }
  grid(g, w, h, 2, 'rgba(90,85,80,.45)', 3);
}, true, [1, 1]);
const tileT = paint(512, 512, (g, w, h) => { for (let i = 0; i < 8; i++) for (let j = 0; j < 8; j++) { g.fillStyle = (i + j) % 2 ? '#d9d4c6' : '#8b9699'; g.fillRect(i * 64, j * 64, 64, 64); } speck(g, w, h, 6000, 0.05); }, true, [1, 1]);
const concT = paint(512, 512, (g, w, h) => { g.fillStyle = '#8d9095'; g.fillRect(0, 0, w, h); speck(g, w, h, 20000, 0.06); grid(g, w, h, 2, 'rgba(30,30,30,.4)', 3); }, true, [1, 1]);
const raisedT = paint(512, 512, (g, w, h) => { g.fillStyle = '#aab3bc'; g.fillRect(0, 0, w, h); grid(g, w, h, 8, 'rgba(40,50,60,.5)', 2); for (let i = 0; i < 8; i++) for (let j = 0; j < 8; j++) { g.fillStyle = 'rgba(40,50,60,.35)'; g.fillRect(i * 64 + 30, j * 64 + 30, 4, 4); } }, true, [1, 1]);
const asphT = paint(256, 256, (g, w, h) => { g.fillStyle = '#34373c'; g.fillRect(0, 0, w, h); speck(g, w, h, 6000, 0.08); }, true, [1, 1]);
const BN = noise(2, 2);
const FL = {
  wood: P('#ffffff', { map: woodT, roughness: 0.38, clearcoat: 0.35, clearcoatRoughness: 0.3, bumpMap: BN, bumpScale: 0.1 }),
  carpet: M('#ffffff', { map: carpetT, roughness: 1, bumpMap: BN, bumpScale: 0.8 }),
  marble: P('#ffffff', { map: marbleT, roughness: 0.18, clearcoat: 0.8, clearcoatRoughness: 0.1 }),
  tile: P('#ffffff', { map: tileT, roughness: 0.3, clearcoat: 0.5, clearcoatRoughness: 0.2 }),
  conc: M('#ffffff', { map: concT, roughness: 0.6 }),
  raised: M('#ffffff', { map: raisedT, roughness: 0.5, metalness: 0.2 }),
  asph: M('#ffffff', { map: asphT, roughness: 0.95 })
};
function zone(x0, z0, x1, z1, mat, tile) {
  const w = x1 - x0, d = z1 - z0, g = new THREE.PlaneGeometry(w, d), uv = g.attributes.uv;
  for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * w / tile, uv.getY(i) * d / tile);
  const m = new THREE.Mesh(g, mat); m.rotation.x = -Math.PI / 2; m.position.set((x0 + x1) / 2, 0, (z0 + z1) / 2); m.receiveShadow = true; S.add(m);
}
zone(0, 0, 9, 8, FL.wood, 4); zone(9, 0, 26, 8, FL.carpet, 2); zone(0, 8, 26, 10, FL.conc, 4);
zone(0, 10, 7, 16, FL.carpet, 2); zone(7, 10, 14, 16, FL.conc, 4); zone(14, 10, 20, 16, FL.tile, 4);
zone(20, 10, 26, 16, FL.raised, 4); zone(-1, 16, 27, 21.4, FL.asph, 4);
add(S, BX(NX + WT, 0.24, NZ + WT), M('#2a2530'), NX / 2 - WT / 2, -0.13, NZ / 2 - WT / 2, { nocast: true });
add(S, BX(28, 0.24, 5.4), M('#2a2d31'), 13, -0.13, 18.7, { nocast: true });
add(S, BX(28, 0.1, 0.18), M('#9a9a96'), 13, 0.05, 16.09);

// =====================================================================
// Dinding luar, jendela, partisi kaca
// =====================================================================
const WIN_Y0 = 1.0, WIN_Y1 = 2.3;
const wm1 = M('#7d6f86', { roughness: 0.93, bumpMap: noise(14, 3), bumpScale: 0.25 });
const wm2 = M('#9a8aa3', { roughness: 0.93, bumpMap: noise(8, 3), bumpScale: 0.25 });
const GLASS = P('#cfe8ff', { roughness: 0.04, transparent: true, opacity: 0.1, envMapIntensity: 1.3, depthWrite: false });
function win(ax, a, b) {
  const L = b - a, H = WIN_Y1 - WIN_Y0, t = 0.05, fm = M('#ece8df', { roughness: 0.5 }), g = new THREE.Group();
  add(g, BX(L, t, 0.09), fm, 0, H / 2 - t / 2, 0); add(g, BX(L, t, 0.09), fm, 0, -H / 2 + t / 2, 0);
  add(g, BX(t, H, 0.09), fm, -L / 2 + t / 2, 0, 0); add(g, BX(t, H, 0.09), fm, L / 2 - t / 2, 0, 0);
  add(g, BX(0.035, H, 0.06), fm, 0, 0, 0); add(g, BX(L, 0.035, 0.06), fm, 0, 0.1, 0);
  add(g, new THREE.PlaneGeometry(L, H), GLASS, 0, 0, 0, { nocast: true, norecv: true });
  add(g, BX(L + 0.12, 0.04, 0.22), fm, 0, -H / 2 - 0.02, 0.1);
  const cy = (WIN_Y0 + WIN_Y1) / 2, cx = (a + b) / 2;
  if (ax === 'x') g.position.set(cx, cy, -WT / 2); else { g.rotation.y = Math.PI / 2; g.position.set(-WT / 2, cy, cx); }
  S.add(g);
}
function outerWall(axis, len, ops, mat) {
  const s0 = axis === 'x' ? -WT : 0;
  const put = (a, b, y0, y1) => {
    if (b - a < 1e-3) return; const w = b - a, h = y1 - y0, m = (a + b) / 2, cy = (y0 + y1) / 2;
    if (axis === 'x') add(S, BX(w, h, WT), mat, m, cy, -WT / 2); else add(S, BX(WT, h, w), mat, -WT / 2, cy, m);
  };
  put(s0, len, 0, WIN_Y0); put(s0, len, WIN_Y1, WH);
  let p = s0; ops.forEach(o => { put(p, o[0], WIN_Y0, WIN_Y1); p = o[1]; }); put(p, len, WIN_Y0, WIN_Y1);
  ops.forEach(o => win(axis, o[0], o[1]));
}
outerWall('x', NX, [[1, 3.5], [5.5, 8.5], [10, 12.5], [13.5, 16], [18, 21], [22, 25]], wm1);
outerWall('z', NZ, [[1, 3], [6.5, 7.8], [11, 13], [14, 15.5]], wm2);
const skirt = M('#4d4155', { roughness: 0.5 });
add(S, BX(NX, 0.1, 0.025), skirt, NX / 2, 0.05, 0.0125); add(S, BX(0.025, 0.1, NZ), skirt, 0.0125, 0.05, NZ / 2);

const PM = M('#ebe8e1', { roughness: 0.85 });
// pintu berdaun: terbuka otomatis saat ada karakter mendekat, menutup lagi setelah lewat
const DOORS = [];
const DOOR_WOOD = P('#9a7a5a', { map: WOOD, roughness: 0.45, clearcoat: 0.3 });
function makeDoor(alongX, fx, a, b) {
  const L = b - a - 0.05, H = 2.16, g = new THREE.Group(), leaf = new THREE.Group();
  g.add(leaf); S.add(g);
  const A = (geo, mat, x, y, z, o) => add(leaf, geo, mat, x, y, z, o);
  A(BX(L, 0.95, 0.045), DOOR_WOOD, L / 2, 0.5, 0);
  A(BX(L, 0.06, 0.06), STEEL, L / 2, 0.98, 0); A(BX(L, 0.06, 0.06), STEEL, L / 2, H, 0);
  A(BX(0.06, H - 0.98, 0.06), STEEL, 0.03, (H + 0.98) / 2, 0); A(BX(0.06, H - 0.98, 0.06), STEEL, L - 0.03, (H + 0.98) / 2, 0);
  A(new THREE.PlaneGeometry(L - 0.1, H - 1.05), GLASS, L / 2, (H + 0.98) / 2, 0, { nocast: true, norecv: true });
  A(new THREE.CylinderGeometry(0.018, 0.018, 0.22, 10), STEEL, L - 0.12, 1.0, 0.06);
  if (alongX) g.position.set(a + 0.025, 0, fx); else { g.position.set(fx, 0, a + 0.025); g.rotation.y = -Math.PI / 2; }
  return { g, leaf, L: L + 0.04, alongX, fx, cx: alongX ? (a + b) / 2 : fx, cz: alongX ? fx : (a + b) / 2, o: 0, sd: 1 };
}
function updateDoors(dt, people) {   // pintu geser otomatis: daun meluncur ke samping dinding, tidak menyapu ruang jalan
  DOORS.forEach(d => {
    let near = false;
    for (const c of people) {
      const dx = d.cx - c.x, dz = d.cz - c.y, q = Math.hypot(dx, dz);
      if (q < 1.15) { near = true; break; }
      if (q < 2.4 && c.walking) {   // sedang berjalan menuju pintu -> buka lebih awal
        const wp = c.path && c.path.length ? c.path[0] : [c.tx, c.ty], vx = wp[0] - c.x, vz = wp[1] - c.y, vl = Math.hypot(vx, vz) || 1;
        const perp = d.alongX ? Math.abs(dz) : Math.abs(dx), along = d.alongX ? Math.abs(dx) : Math.abs(dz);
        if ((vx * dx + vz * dz) / (vl * q) > 0.55 && along < 1.1 && perp < 2.4) { near = true; break; }
      }
    }
    d.o += ((near ? 1 : 0) - d.o) * Math.min(1, dt * (near ? 9 : 3));
    d.leaf.scale.x = 1 - 0.85 * d.o; d.leaf.position.x = -d.o * d.L * 0.8; d.leaf.position.z = Math.min(1, d.o * 6) * 0.085; d.leaf.visible = d.o < 0.97;
  });
}
function part(x0, z0, x1, z1, doors, o) {
  o = o || {}; const alongX = Math.abs(z1 - z0) < 1e-6, a0 = alongX ? x0 : z0, a1 = alongX ? x1 : z1, fx = alongX ? z0 : x0;
  const put = (a, b, y0, y1, mat, t, cast) => {
    if (b - a < 0.01) return; const L = b - a, h = y1 - y0, m = (a + b) / 2, cy = (y0 + y1) / 2;
    if (alongX) add(S, BX(L, h, t), mat, m, cy, fx, { nocast: !cast }); else add(S, BX(t, h, L), mat, fx, cy, m, { nocast: !cast });
  };
  const ds = (doors || []).slice().sort((u, v) => u[0] - v[0]), segs = []; let p = a0;
  ds.forEach(d => { segs.push([p, d[0]]); p = d[1]; }); segs.push([p, a1]);
  segs.forEach(s => {
    if (s[1] - s[0] < 0.01) return;
    put(s[0], s[1], 0, o.solid ? WH : 1.0, PM, 0.1, true);
    if (!o.solid) {
      put(s[0], s[1], 1.0, 2.6, GLASS, 0.02, false); put(s[0], s[1], 2.6, 2.66, STEEL, 0.07, true);
      for (let k = s[0] + 1.6; k < s[1] - 0.2; k += 1.6) put(k - 0.02, k + 0.02, 1.0, 2.6, STEEL, 0.05, true);
    }
    if (alongX) ob(s[0], fx - 0.06, s[1], fx + 0.06); else ob(fx - 0.06, s[0], fx + 0.06, s[1]);
  });
  ds.forEach(d => DOORS.push(makeDoor(alongX, fx, d[0], d[1])));
  ds.forEach(d => { put(d[0], d[1], 2.2, 2.66, PM, 0.1, true); put(d[0] - 0.03, d[0] + 0.03, 0, 2.2, STEEL, 0.11, true); put(d[1] - 0.03, d[1] + 0.03, 0, 2.2, STEEL, 0.11, true); });
}
part(0, 8, NX, 8, [[4.0, 5.3], [12.0, 13.3], [20.8, 22.1]]);
part(0, 10, NX, 10, [[5.6, 6.9], [9.8, 11.1], [16.4, 17.7], [22.2, 23.5]]);
part(9, 0, 9, 8, [[4.6, 5.9]]); part(17, 0, 17, 8, [[4.6, 5.9]]);
part(7, 10, 7, 16, [[12.8, 14.1]]); part(14, 10, 14, 16, [[12.5, 13.8]]);
part(20, 10, 20, 16, [[11.2, 12.5], [14.0, 15.3]]); 

// pemandangan di luar jendela
// kota di kejauhan (kotak 3D berkabut) untuk pemandangan dari jendela
{
  const winT = paint(128, 256, (g, w, h) => { g.fillStyle = '#b4c5d6'; g.fillRect(0, 0, w, h); for (let y = 8; y < h; y += 16) for (let x = 6; x < w; x += 14) { g.fillStyle = rnd() < 0.25 ? '#eef5fb' : '#8ea5bb'; g.fillRect(x, y, 8, 9); } }, true, [1, 1]);
  const cols = ['#b6c6d6', '#a9bccd', '#c3cfdb'];
  const bld = (x, z, w, d, h, i) => {
    const tx = winT.clone(); tx.wrapS = tx.wrapT = THREE.RepeatWrapping; tx.repeat.set(Math.max(1, Math.round(w / 6)), Math.max(1, Math.round(h / 10))); tx.needsUpdate = true;
    add(S, BX(w, h, d), new THREE.MeshStandardMaterial({ color: cols[i % 3], map: tx, roughness: 0.9 }), x, h / 2 - 0.12, z, { nocast: true, norecv: true });
  };
  let bi = 0;
  for (let x = -110; x < 150; x += 16 + rnd() * 12) bld(x, -95 - rnd() * 45, 10 + rnd() * 10, 10 + rnd() * 8, 12 + rnd() * 34, bi++);
  for (let z = -90; z < 130; z += 16 + rnd() * 12) bld(-95 - rnd() * 45, z, 10 + rnd() * 8, 10 + rnd() * 10, 12 + rnd() * 34, bi++);
}

// =====================================================================
// Layar (kanvas hidup), monitor, meja, kursi
// =====================================================================
const screens = [];
function mkScreen(kind, owner) {
  const c = cv2(256, 144), tex = ctex(c);
  screens.push({ g: c.getContext('2d'), tex, ch: null, owner: owner || null, kind, last: -1 });
  return new THREE.MeshBasicMaterial({ map: tex, toneMapped: false });
}
function drawScreen(sc, on, t) {
  const g = sc.g, w = 256, h = 144;
  if (!on) { g.fillStyle = '#0b1118'; g.fillRect(0, 0, w, h); g.fillStyle = 'rgba(255,255,255,.05)'; g.fillRect(0, 0, w, h / 2); sc.tex.needsUpdate = true; return; }
  const gr = g.createLinearGradient(0, 0, w, h); gr.addColorStop(0, '#10243f'); gr.addColorStop(1, '#17375e'); g.fillStyle = gr; g.fillRect(0, 0, w, h);
  g.fillStyle = '#0a121d'; g.fillRect(0, 0, w, 14);
  ['#ff5f56', '#ffbd2e', '#27c93f'].forEach((c, i) => { g.fillStyle = c; g.beginPath(); g.arc(9 + i * 12, 7, 3.4, 0, 6.3); g.fill(); });
  const v = [D.counts.nunggu, D.counts.jalan, D.counts.selesai], cl = ['#e67e22', '#3498db', '#2ecc71'], mx = Math.max(1, ...v);
  if (sc.kind === 'dash') {
    v.forEach((x, i) => { g.fillStyle = cl[i]; g.fillRect(24 + i * 74, 118 - x / mx * 80, 52, x / mx * 80); g.fillStyle = '#fff'; g.font = 'bold 14px sans-serif'; g.fillText(String(x), 40 + i * 74, 112 - x / mx * 80); });
  } else if (sc.kind === 'wall') {
    g.strokeStyle = 'rgba(255,255,255,.12)'; for (let i = 1; i < 5; i++) { g.beginPath(); g.moveTo(8, 14 + i * 26); g.lineTo(w - 8, 14 + i * 26); g.stroke(); }
    [['#3498db', 0], ['#2ecc71', 2], ['#e67e22', 4]].forEach(s => { g.strokeStyle = s[0]; g.lineWidth = 2; g.beginPath(); for (let x = 0; x <= 240; x += 6) { const y = 78 + Math.sin(x * 0.05 + t * 1.5 + s[1]) * 22 + Math.sin(x * 0.13 + t + s[1]) * 8; if (x) g.lineTo(8 + x, y); else g.moveTo(8, y); } g.stroke(); });
    g.lineWidth = 1; g.fillStyle = '#9ad'; g.font = '10px sans-serif'; g.fillText('THROUGHPUT  ' + (180 + (Math.sin(t) * 12 | 0)) + ' plt/jam', 10, 134);
  } else if (sc.kind === 'meet') {
    g.fillStyle = '#fff'; g.font = 'bold 15px sans-serif'; g.fillText('Rapat Mingguan', 14, 38); g.font = '11px sans-serif'; g.fillStyle = '#9ad'; g.fillText('JDC Distribution Center · Cikarang', 14, 54);
    v.forEach((x, i) => { g.fillStyle = cl[i]; g.fillRect(20 + i * 76, 124 - x / mx * 56, 50, x / mx * 56); });
  } else {
    const cols = ['#7fe0ff', '#9be08a', '#f5c26b', '#d6a2ff', '#cfd8e3'];
    for (let i = 0; i < 10; i++) {
      const k = Math.floor(t * 2 + i), wd = 30 + Math.abs(Math.sin(k * 12.9898 + i * 4.1)) * 150, ind = (k % 3) * 10;
      g.fillStyle = cols[(k + i) % cols.length]; g.globalAlpha = 0.85; g.fillRect(14 + ind, 24 + i * 11, wd, 5); g.globalAlpha = 1;
    }
    g.fillStyle = 'rgba(255,255,255,.8)'; if (Math.floor(t * 2) % 2) g.fillRect(14, 24 + 10 * 11, 5, 8);
  }
  sc.tex.needsUpdate = true;
}
function monitor(par, x, y, z, mat, ry, sc) {
  const m = new THREE.Group(); m.position.set(x, y, z); m.rotation.y = ry; m.scale.setScalar(sc || 1); par.add(m);
  add(m, RB(0.62, 0.37, 0.025, 0.006), BLACK, 0, 0.26, 0);
  add(m, new THREE.PlaneGeometry(0.58, 0.33), mat, 0, 0.26, 0.0135, { nocast: true });
  add(m, BX(0.04, 0.2, 0.03), STEEL, 0, 0.1, -0.02); add(m, RB(0.24, 0.012, 0.17, 0.004), STEEL, 0, 0.006, -0.02);
}
const KEYT = paint(256, 96, (g, w, h) => { g.fillStyle = '#23262d'; g.fillRect(0, 0, w, h); g.fillStyle = '#3a3e48'; for (let r = 0; r < 5; r++) for (let c = 0; c < 15; c++) g.fillRect(6 + c * 16.2, 6 + r * 16.5, 13, 13); });
// meja: x,z = pojok minimum, ry=0 -> duduk di sisi utara (menghadap selatan); ry=PI -> sisi selatan
function desk(x, z, w, d, tint, kind, owner, ry) {
  ry = ry || 0; const g = new THREE.Group(); g.position.set(x + w / 2, 0, z + d / 2); g.rotation.y = ry; S.add(g);
  const A = (geo, mat, lx, y, lz, o) => add(g, geo, mat, lx - w / 2, y, lz - d / 2, o);
  const top = P(tint, { map: WOOD, roughness: 0.42, clearcoat: 0.3, clearcoatRoughness: 0.4 });
  A(RB(w, 0.04, d, 0.012), top, w / 2, 0.74, d / 2);
  A(BX(0.03, 0.72, d - 0.1), STEEL, 0.05, 0.36, d / 2); A(BX(0.03, 0.72, d - 0.1), STEEL, w - 0.05, 0.36, d / 2);
  A(BX(w - 0.12, 0.4, 0.02), M('#cfcac0', { roughness: 0.6 }), w / 2, 0.5, d - 0.06);
  A(RB(0.46, 0.5, d - 0.25, 0.01), M('#d8d4cc', { roughness: 0.55 }), w - 0.34, 0.45, d / 2 + 0.02);
  for (let i = 0; i < 3; i++) { A(RB(0.44, 0.15, 0.015, 0.006), M('#e6e2da', { roughness: 0.45 }), w - 0.34, 0.6 - i * 0.16, 0.16); A(BX(0.12, 0.012, 0.02), STEEL, w - 0.34, 0.64 - i * 0.16, 0.18); }
  A(RB(0.42, 0.016, 0.14, 0.006), new THREE.MeshStandardMaterial({ map: KEYT, roughness: 0.6 }), w / 2, 0.768, 0.14);
  A(RB(0.06, 0.026, 0.1, 0.012), BLACK, w / 2 + 0.34, 0.772, 0.15);
  monitor(g, 0, 0.76, 0.52 - d / 2, mkScreen(kind, owner), Math.PI);
  A(new THREE.CylinderGeometry(0.04, 0.035, 0.09, 16), M('#f2f0ea', { roughness: 0.3 }), w / 2 - 0.62, 0.805, 0.3);
  A(RB(0.2, 0.02, 0.28, 0.006), M('#c0392b', { roughness: 0.6 }), 0.34, 0.76, 0.36, { r: [0, 0.3, 0] });
  ob(x, z, x + w, z + d); ao(x + w / 2, z + d / 2, w + 0.9, d + 0.9, 0.5);
  return ry ? [x + w / 2, z + d + 0.45] : [x + w / 2, z - 0.45];
}
function chair(s, ry) {
  ry = ry || 0; const g = new THREE.Group(); g.position.set(s[0], 0, s[1] + (ry ? 0.07 : -0.07)); g.rotation.y = ry; S.add(g);
  const fab = cloth('#2c3340', 0.95), pl = M('#1a1c20', { roughness: 0.5 });
  add(g, RB(0.5, 0.09, 0.48, 0.04), fab, 0, 0.415, 0); add(g, RB(0.46, 0.5, 0.07, 0.03), fab, 0, 0.75, -0.23, { r: [-0.1, 0, 0] });
  add(g, new THREE.CylinderGeometry(0.025, 0.025, 0.3, 12), STEEL, 0, 0.24, 0);
  for (let i = 0; i < 5; i++) { const l = new THREE.Group(); l.rotation.y = i / 5 * 6.283; g.add(l); add(l, BX(0.3, 0.03, 0.045), pl, 0.15, 0.075, 0); add(l, new THREE.SphereGeometry(0.03, 10, 8), pl, 0.3, 0.03, 0); }
  [-1, 1].forEach(q => { add(g, RB(0.05, 0.03, 0.26, 0.01), pl, q * 0.27, 0.62, -0.02); add(g, BX(0.03, 0.15, 0.03), pl, q * 0.27, 0.54, 0.05); });
  ao(s[0], s[1], 0.9, 0.9, 0.45);
}
function chairL(x, z, ry, col) {
  const g = new THREE.Group(); g.position.set(x, 0, z); g.rotation.y = ry || 0; S.add(g); const f = cloth(col || '#3a4252', 0.95);
  add(g, RB(0.46, 0.08, 0.44, 0.03), f, 0, 0.45, 0); add(g, RB(0.44, 0.46, 0.06, 0.025), f, 0, 0.74, -0.2, { r: [-0.08, 0, 0] });
  add(g, new THREE.CylinderGeometry(0.03, 0.03, 0.4, 10), STEEL, 0, 0.22, 0); add(g, new THREE.CylinderGeometry(0.24, 0.24, 0.03, 16), PLASTIC, 0, 0.03, 0);
}

// =====================================================================
// Perabot umum
// =====================================================================
function rugAt(cx, cz, w, d, tx) {
  const r = new THREE.Mesh(new THREE.PlaneGeometry(w, d), M('#ffffff', { map: tx, roughness: 1, bumpMap: noise(w * 2.5, d * 2.5), bumpScale: 1.2 }));
  r.rotation.x = -Math.PI / 2; r.position.set(cx, 0.008, cz); r.receiveShadow = true; S.add(r);
}
function sofa(x, z, ry, cA, cB) {
  const g = new THREE.Group(); g.position.set(x, 0, z); g.rotation.y = ry || 0; S.add(g);
  const f = cloth(cA || '#8a3b4a', 0.95), f2 = cloth(cB || '#7a2f3e', 0.95);
  add(g, RB(2.4, 0.36, 0.95, 0.06), f2, 1.2, 0.3, 0.5); add(g, RB(2.4, 0.5, 0.26, 0.07), f2, 1.2, 0.7, 0.14);
  [0.11, 2.29].forEach(q => add(g, RB(0.22, 0.28, 0.95, 0.06), f2, q, 0.58, 0.5));
  [0.62, 1.78].forEach(q => { add(g, RB(1.0, 0.14, 0.7, 0.05), f, q, 0.55, 0.58); add(g, RB(0.98, 0.42, 0.16, 0.06), f, q, 0.8, 0.3, { r: [-0.2, 0, 0] }); });
  add(g, RB(0.38, 0.38, 0.12, 0.05), cloth('#d9b36b', 0.95), 0.4, 0.78, 0.5, { r: [-0.3, 0.4, 0.2] });
  [[0.1, 0.1], [2.3, 0.1], [0.1, 0.88], [2.3, 0.88]].forEach(p => add(g, new THREE.CylinderGeometry(0.03, 0.025, 0.1, 8), BLACK, p[0], 0.05, p[1]));
}
function plant(x, z, sc) {
  const g = new THREE.Group(); g.position.set(x, 0, z); g.scale.setScalar(sc || 1); S.add(g);
  add(g, new THREE.CylinderGeometry(0.2, 0.15, 0.34, 24), P('#d8d2c4', { roughness: 0.5, clearcoat: 0.2 }), 0, 0.17, 0);
  add(g, new THREE.CylinderGeometry(0.185, 0.185, 0.02, 20), M('#2b2118'), 0, 0.33, 0);
  add(g, new THREE.CylinderGeometry(0.018, 0.03, 0.9, 8), M('#6b4a2f'), 0, 0.78, 0);
  const im = new THREE.InstancedMesh(new THREE.SphereGeometry(1, 8, 6), M('#ffffff', { roughness: 0.55 }), 80), o = new THREE.Object3D();
  for (let i = 0; i < 80; i++) {
    const a = rnd() * 6.283, b = Math.acos(rnd() * 2 - 1), r = 0.15 + rnd() * 0.32;
    o.position.set(Math.sin(b) * Math.cos(a) * r, 1.3 + Math.cos(b) * r * 0.9, Math.sin(b) * Math.sin(a) * r);
    o.rotation.set(rnd() * 6.28, rnd() * 6.28, rnd() * 6.28); o.scale.set(0.07, 0.012, 0.16); o.updateMatrix();
    im.setMatrixAt(i, o.matrix); im.setColorAt(i, new THREE.Color().setHSL(0.31 + rnd() * 0.05, 0.5, 0.2 + rnd() * 0.12));
  }
  im.castShadow = true; im.receiveShadow = true; g.add(im); ao(x, z, 0.9 * (sc || 1), 0.9 * (sc || 1), 0.5);
}
function lamp(x, z, pl) {
  const g = new THREE.Group(); g.position.set(x, 0, z); S.add(g);
  add(g, new THREE.CylinderGeometry(0.16, 0.18, 0.03, 24), BLACK, 0, 0.015, 0); add(g, new THREE.CylinderGeometry(0.012, 0.012, 1.5, 8), STEEL, 0, 0.77, 0);
  add(g, new THREE.CylinderGeometry(0.17, 0.24, 0.3, 24, 1, true), new THREE.MeshStandardMaterial({ color: '#f5e6c8', emissive: '#ffcf8a', emissiveIntensity: 0.9, side: THREE.DoubleSide, roughness: 0.9 }), 0, 1.6, 0, { nocast: true });
  if (pl) { const l = new THREE.PointLight(0xffd9a0, 4, 5, 2); l.position.set(x, 1.6, z); scene.add(l); LIGHTS.push(l); }
}
function dispenser(x, z) {
  add(S, RB(0.38, 1.05, 0.38, 0.03), M('#e5e8ec', { roughness: 0.4 }), x, 0.53, z); add(S, new THREE.CylinderGeometry(0.13, 0.13, 0.32, 20), P('#7bbcf0', { roughness: 0.05, transparent: true, opacity: 0.6 }), x, 1.2, z); ob(x - 0.2, z - 0.2, x + 0.2, z + 0.2);
}
function extinguisher(x, z, ry) {
  const g = new THREE.Group(); g.position.set(x, 0, z); g.rotation.y = ry || 0; S.add(g);
  add(g, new THREE.CylinderGeometry(0.065, 0.065, 0.42, 14), M('#c0261e', { roughness: 0.35 }), 0, 0.55, 0); add(g, new THREE.CylinderGeometry(0.02, 0.025, 0.08, 8), BLACK, 0, 0.8, 0);
  add(g, BX(0.28, 0.28, 0.01), M('#e8e6df'), 0, 1.5, -0.04);
}
function glow(w, h, tx) { return new THREE.MeshStandardMaterial({ map: tx, emissive: '#ffffff', emissiveMap: tx, emissiveIntensity: 0.6, roughness: 0.5 }); }

// =====================================================================
// 7 RUANGAN: atas = HRD | MANAGER OPERATION | MEETING ; bawah = OPERATION CONTROL | ASSET MANAGEMENT | HSE | SERVER
// =====================================================================
const SEAT = {}, FACE = {};
function signBoard(x, y, z, w, h, ry, title, lines, accent) {
  const t = paint(512, Math.round(512 * h / w), (g, W, H) => {
    g.fillStyle = '#f6f5f0'; g.fillRect(0, 0, W, H); g.fillStyle = accent; g.fillRect(0, 0, W, 54);
    g.fillStyle = '#fff'; g.font = 'bold 30px sans-serif'; g.fillText(title, 18, 38);
    lines.forEach((l, i) => { g.fillStyle = accent; g.beginPath(); g.arc(28, 92 + i * 38, 6, 0, 6.3); g.fill(); g.fillStyle = '#2a2d33'; g.font = '24px sans-serif'; g.fillText(l, 46, 100 + i * 38); });
  });
  const g = new THREE.Group(); g.position.set(x, y, z); g.rotation.y = ry; S.add(g);
  add(g, RB(w, h, 0.04, 0.012), STEEL, 0, 0, 0); add(g, new THREE.PlaneGeometry(w - 0.1, h - 0.1), M('#ffffff', { map: t, roughness: 0.4 }), 0, 0, 0.025, { nocast: true });
}
function bookshelf(px, pz) {
  const g = new THREE.Group(); g.position.set(px, 0, pz); S.add(g);
  const wd = P('#8a6a4a', { map: WOOD, roughness: 0.55 });
  add(g, BX(0.72, 2.0, 0.04), wd, 0.38, 1.0, 0.02); add(g, BX(0.72, 2.0, 0.04), wd, 0.38, 1.0, 1.98); add(g, BX(0.02, 2.0, 2.0), wd, 0.02, 1.0, 1.0);
  for (let l = 0; l <= 5; l++) add(g, BX(0.72, 0.03, 1.96), wd, 0.38, 0.02 + l * 0.39, 1.0);
  const im = new THREE.InstancedMesh(BX(1, 1, 1), M('#ffffff', { roughness: 0.7 }), 170), o = new THREE.Object3D(), pal = ['#c0392b', '#2980b9', '#27ae60', '#f39c12', '#8e44ad', '#ecf0f1', '#34495e', '#d35400'];
  let n = 0;
  for (let l = 0; l < 5; l++) {
    let z = 0.07;
    while (z < 1.88 && n < 170) {
      if (rnd() < 0.07) { z += 0.12; continue; }
      const t = 0.025 + rnd() * 0.035, h = 0.22 + rnd() * 0.12;
      o.position.set(0.42, 0.035 + l * 0.39 + 0.015 + h / 2, z + t / 2); o.scale.set(0.22, h, t); o.rotation.set(0, 0, 0); o.updateMatrix();
      im.setMatrixAt(n, o.matrix); im.setColorAt(n, new THREE.Color(pal[Math.floor(rnd() * pal.length)]).multiplyScalar(0.8 + rnd() * 0.3)); n++; z += t + 0.003;
    }
  }
  im.count = n; im.castShadow = true; im.receiveShadow = true; g.add(im); ao(px + 0.47, pz + 1.0, 1.3, 2.7, 0.5); ob(px + 0.02, pz, px + 0.82, pz + 2.0);
}
function cabinet(cx, cz, w, col) {
  add(S, RB(w, 0.9, 0.4, 0.015), M(col || '#cfc9bd', { roughness: 0.6 }), cx, 0.45, cz); ob(cx - w / 2, cz - 0.2, cx + w / 2, cz + 0.2);
  add(S, RB(w + 0.04, 0.04, 0.44, 0.01), P('#8a6b5a', { map: WOOD, roughness: 0.4 }), cx, 0.92, cz);
}
function palletRack(x, z, L) {
  const g = new THREE.Group(); g.position.set(x, 0, z); S.add(g);
  const og = M('#e8751a', { roughness: 0.5, metalness: 0.4 }), bl = M('#1f5fa8', { roughness: 0.5, metalness: 0.4 }), slat = M('#a58a63', { roughness: 0.8 });
  const bays = Math.max(1, Math.round(L / 1.7)), bw = L / bays;
  for (let i = 0; i <= bays; i++) [0, 0.9].forEach(zz => add(g, BX(0.07, 2.6, 0.07), og, i * bw, 1.3, zz + 0.035));
  const ys = [0.35, 1.2, 2.05], im = new THREE.InstancedMesh(BX(1, 1, 1), M('#ffffff', { roughness: 0.85 }), 80), o = new THREE.Object3D(); let n = 0;
  for (let b = 0; b < bays; b++) ys.forEach(y => {
    [0.03, 0.87].forEach(zz => add(g, BX(bw, 0.1, 0.05), bl, b * bw + bw / 2, y, zz)); add(g, BX(bw - 0.1, 0.025, 0.8), slat, b * bw + bw / 2, y + 0.06, 0.45);
    for (let k = 0; k < 3 && n < 80; k++) { const w = 0.35 + rnd() * 0.15, h = 0.3 + rnd() * 0.25; o.position.set(b * bw + 0.3 + k * (bw - 0.5) / 3 + 0.1, y + 0.07 + h / 2, 0.45); o.scale.set(w, h, 0.5 + rnd() * 0.2); o.rotation.set(0, 0, 0); o.updateMatrix(); im.setMatrixAt(n, o.matrix); im.setColorAt(n, new THREE.Color('#b08a55').multiplyScalar(0.8 + rnd() * 0.35)); n++; }
  });
  im.count = n; im.castShadow = true; im.receiveShadow = true; g.add(im); ob(x - 0.1, z, x + L + 0.1, z + 0.95); ao(x + L / 2, z + 0.45, L + 1, 1.8, 0.5);
}
function crateStack(x, z) {
  const pc = M('#a58a63', { roughness: 0.8 }); add(S, BX(1.0, 0.12, 1.0), M('#8a6a4a', { roughness: 0.8 }), x, 0.06, z); add(S, BX(0.8, 0.5, 0.8), pc, x, 0.37, z); add(S, BX(0.7, 0.4, 0.7), pc, x, 0.82, z); ob(x - 0.5, z - 0.5, x + 0.5, z + 0.5);
}
const clkC = cv2(256, 256), clkG = clkC.getContext('2d'), clkT = ctex(clkC);
function drawClock() {
  const g = clkG, d = new Date(); g.clearRect(0, 0, 256, 256);
  g.fillStyle = '#f7f5ef'; g.beginPath(); g.arc(128, 128, 124, 0, 6.3); g.fill();
  g.strokeStyle = '#2a2a2a'; for (let i = 0; i < 60; i++) { const a = i / 60 * 6.283, l = i % 5 ? 6 : 16; g.lineWidth = i % 5 ? 1.5 : 4; g.beginPath(); g.moveTo(128 + Math.sin(a) * (118 - l), 128 - Math.cos(a) * (118 - l)); g.lineTo(128 + Math.sin(a) * 118, 128 - Math.cos(a) * 118); g.stroke(); }
  const hand = (a, l, w, c) => { g.strokeStyle = c; g.lineWidth = w; g.lineCap = 'round'; g.beginPath(); g.moveTo(128, 128); g.lineTo(128 + Math.sin(a) * l, 128 - Math.cos(a) * l); g.stroke(); };
  const s = d.getSeconds(), m = d.getMinutes() + s / 60, h = d.getHours() % 12 + m / 60;
  hand(h / 12 * 6.283, 62, 8, '#222'); hand(m / 60 * 6.283, 92, 5, '#222'); hand(s / 60 * 6.283, 100, 2, '#c0392b'); clkT.needsUpdate = true;
}
drawClock();

// ---------------------------------------------------------------------
// RUANG HRD (0-9 x 0-8)
// ---------------------------------------------------------------------
SEAT.hrd = desk(1.4, 2.4, 2, 1.1, '#d0a070', 'code', 'hrd', 0);
SEAT.staf1 = desk(5.6, 2.4, 2, 1.1, '#d0a070', 'code', 'staf1', 0);
chair(SEAT.hrd, 0); chair(SEAT.staf1, 0);
bookshelf(0.08, 4.2);
{ // mesin fotokopi
  add(S, RB(0.9, 0.85, 0.6, 0.02), M('#d8d6d0', { roughness: 0.5 }), 8.2, 0.43, 0.4); add(S, RB(0.8, 0.12, 0.5, 0.02), BLACK, 8.2, 0.92, 0.4); add(S, RB(0.5, 0.01, 0.35, 0.004), M('#f4f4f0'), 8.2, 0.99, 0.4);
  ob(7.7, 0.1, 8.7, 0.7); ao(8.2, 0.5, 1.5, 1.2, 0.45);
}
signBoard(4.5, 1.75, 0.03, 1.7, 1.0, 0, 'RUANG HRD', ['Absensi & kehadiran', 'Cuti & lembur', 'Manpower & rekrutmen'], '#c2417a');
add(S, new THREE.CylinderGeometry(0.55, 0.55, 0.05, 28), P('#d0a070', { map: WOOD, roughness: 0.4 }), 6.3, 0.74, 6.2); add(S, new THREE.CylinderGeometry(0.04, 0.04, 0.72, 10), STEEL, 6.3, 0.37, 6.2); ob(5.7, 5.6, 6.9, 6.8);
chairL(6.3, 5.3, 0, '#8a4560'); chairL(6.3, 7.1, Math.PI, '#8a4560');
plant(0.8, 7.3, 1); plant(8.4, 7.0, 0.9); plant(0.6, 0.9, 0.9);
{
  const g = new THREE.Group(); g.rotation.y = Math.PI / 2; g.position.set(0.02, 2.5, 4.95); S.add(g);
  add(g, new THREE.CylinderGeometry(0.25, 0.25, 0.04, 40), BLACK, 0, 0, 0, { r: [Math.PI / 2, 0, 0] });
  add(g, new THREE.CircleGeometry(0.22, 40), new THREE.MeshBasicMaterial({ map: clkT, toneMapped: false }), 0, 0, 0.022, { nocast: true });
  const t = paint(200, 280, (c, w, h) => {
    const gr = c.createLinearGradient(0, 0, w, h); gr.addColorStop(0, '#1f3a5f'); gr.addColorStop(1, '#e07a3f'); c.fillStyle = gr; c.fillRect(0, 0, w, h);
    c.fillStyle = 'rgba(255,255,255,.88)'; c.fillRect(28, 150, 60, 90); c.fillRect(96, 110, 70, 130); c.fillStyle = '#ffd36b'; c.beginPath(); c.arc(140, 70, 26, 0, 6.3); c.fill();
    c.fillStyle = '#fff'; c.font = 'bold 18px sans-serif'; c.fillText('GUDANG', 28, 40); c.font = '12px sans-serif'; c.fillText('Safety First', 28, 58);
  });
  const p = new THREE.Group(); p.rotation.y = Math.PI / 2; p.position.set(0.02, 1.65, 3.6); S.add(p);
  add(p, BX(0.58, 0.78, 0.03), M('#e9e4d8', { roughness: 0.5 }), 0, 0, 0); add(p, new THREE.PlaneGeometry(0.5, 0.7), M('#ffffff', { map: t, roughness: 0.6 }), 0, 0, 0.017, { nocast: true });
}

// ---------------------------------------------------------------------
// RUANG ADMIN CONTROL (9-17 x 0-8) 
// ---------------------------------------------------------------------
SEAT.admin_control = desk(10.2, 1.5, 2.2, 1.1, '#6d5a4e', 'code', 'admin_control', 0); chair(SEAT.admin_control, 0);
const boardT = paint(640, 360, (g, w, h) => {
  g.fillStyle = '#f4f4ef'; g.fillRect(0, 0, w, h); g.fillStyle = '#222'; g.font = 'bold 34px sans-serif'; g.fillText('PAPAN KARTU', 28, 56); g.fillStyle = '#c9c4b6'; g.fillRect(28, 70, w - 56, 3);
  [['Nunggu lu', D.counts.nunggu, '#c0661a'], ['Berjalan', D.counts.jalan, '#1f6fb2'], ['Selesai', D.counts.selesai, '#1e8449']].forEach((r, i) => {
    const y = 130 + i * 78; g.fillStyle = r[2]; g.beginPath(); g.arc(46, y - 14, 12, 0, 6.3); g.fill();
    g.font = '32px sans-serif'; g.fillStyle = '#333'; g.fillText(r[0], 76, y); g.font = 'bold 54px sans-serif'; g.fillStyle = r[2]; g.textAlign = 'right'; g.fillText(String(r[1]), w - 40, y + 6); g.textAlign = 'left';
  });
});
add(S, RB(3.0, 1.2, 0.04, 0.012), STEEL, 13.3, 1.85, 0.02); add(S, new THREE.PlaneGeometry(2.84, 1.04), M('#ffffff', { map: boardT, roughness: 0.35 }), 13.3, 1.85, 0.045, { nocast: true });
add(S, BX(3.0, 0.04, 0.09), STEEL, 13.3, 1.24, 0.06);
['#c0392b', '#2980b9', '#27ae60'].forEach((c, i) => add(S, new THREE.CylinderGeometry(0.012, 0.012, 0.12, 8), M(c, { roughness: 0.4 }), 12.6 + i * 0.12, 1.275, 0.07, { r: [0, 0, Math.PI / 2] }));
const rugT = paint(512, 256, (g, w, h) => {
  g.fillStyle = '#5a3d7a'; g.fillRect(0, 0, w, h); g.fillStyle = '#6d4b8f'; g.fillRect(22, 22, w - 44, h - 44);
  g.strokeStyle = '#d9c9a8'; g.lineWidth = 5; g.strokeRect(12, 12, w - 24, h - 24); g.lineWidth = 2; g.strokeRect(30, 30, w - 60, h - 60);
  g.save(); g.beginPath(); g.rect(32, 32, w - 64, h - 64); g.clip(); g.strokeStyle = 'rgba(217,201,168,.32)';
  for (let i = -h; i < w; i += 36) { g.beginPath(); g.moveTo(i, 0); g.lineTo(i + h, h); g.stroke(); g.beginPath(); g.moveTo(i + h, 0); g.lineTo(i, h); g.stroke(); }
  g.restore(); speck(g, w, h, 9000, 0.05);
});
rugAt(14.4, 4.3, 3.8, 1.9, rugT);
cabinet(16.1, 0.28, 1.2, '#cfc9bd');
add(S, new THREE.CylinderGeometry(0.55, 0.55, 0.05, 28), P('#8a6b5a', { map: WOOD, roughness: 0.4 }), 10.8, 0.74, 6.5); add(S, new THREE.CylinderGeometry(0.04, 0.04, 0.72, 10), STEEL, 10.8, 0.37, 6.5); ob(10.2, 5.9, 11.4, 7.1);
chairL(10.0, 6.5, Math.PI / 2, '#6a4c58'); chairL(11.6, 6.5, -Math.PI / 2, '#6a4c58');
plant(16.4, 7.2, 1); plant(9.6, 0.9, 0.9); lamp(16.5, 4.6, false);

// ---------------------------------------------------------------------
// RUANG MEETING (17-26 x 0-8)
// ---------------------------------------------------------------------
{
  const tw = P('#6d5a4e', { map: WOOD, roughness: 0.4, clearcoat: 0.35, clearcoatRoughness: 0.35 });
  add(S, RB(5.6, 0.06, 1.5, 0.02), tw, 21.5, 0.74, 3.7); [19.3, 23.7].forEach(x => { add(S, BX(0.08, 0.7, 1.2), STEEL, x, 0.37, 3.7); add(S, BX(0.08, 0.04, 1.3), STEEL, x, 0.02, 3.7); });
  for (let i = 0; i < 5; i++) { chairL(19.3 + i * 1.1, 2.4, 0, '#33415c'); chairL(19.3 + i * 1.1, 5.0, Math.PI, '#33415c'); }
  chairL(17.95, 3.7, Math.PI / 2, '#33415c'); chairL(25.05, 3.7, -Math.PI / 2, '#33415c');
  [[20.3, 3.3, 0.2], [22.8, 4.1, -0.3]].forEach(l => { add(S, RB(0.34, 0.015, 0.24, 0.004), M('#9aa0a8', { metalness: 0.8, roughness: 0.3 }), l[0], 0.78, l[1], { r: [0, l[2], 0] }); add(S, RB(0.34, 0.01, 0.23, 0.004), BLACK, l[0], 0.88, l[1] - 0.12, { r: [-1.2, l[2], 0] }); });
  add(S, new THREE.CylinderGeometry(0.1, 0.1, 0.02, 20), BLACK, 21.5, 0.78, 3.7); [21.0, 22.0].forEach(x => add(S, new THREE.CylinderGeometry(0.03, 0.025, 0.2, 12), P('#7bbcf0', { roughness: 0.05, transparent: true, opacity: 0.6 }), x, 0.87, 3.4));
  ob(18.7, 2.9, 24.3, 4.5); ao(21.5, 3.7, 7.4, 3.6, 0.5);
  const g = new THREE.Group(); g.position.set(21.5, 1.4, 0.03); S.add(g);
  add(g, RB(2.1, 1.2, 0.05, 0.01), BLACK, 0, 0, 0); add(g, new THREE.PlaneGeometry(2.0, 1.1), mkScreen('meet', null), 0, 0, 0.027, { nocast: true });
  plant(25.2, 0.9, 1); plant(25.2, 7.2, 1); plant(17.8, 0.8, 0.9); lamp(25.4, 4.2, false);
}

// ---------------------------------------------------------------------
// KORIDOR (0-26 x 8-10)
// ---------------------------------------------------------------------
{
  const yl = M('#e5b800', { roughness: 0.6 });
  [8.4, 9.6].forEach(z => { const m = new THREE.Mesh(new THREE.PlaneGeometry(NX - 0.4, 0.08), yl); m.rotation.x = -Math.PI / 2; m.position.set(NX / 2, 0.011, z); S.add(m); });
  plant(0.8, 9.0, 0.9); plant(25.2, 9.0, 0.9); dispenser(1.6, 9.3);
  extinguisher(7.4, 8.2, 0); extinguisher(15.0, 9.8, Math.PI); extinguisher(19.4, 8.2, 0);
  add(S, BX(0.7, 0.2, 0.04), new THREE.MeshStandardMaterial({ color: '#0d6b3a', emissive: '#18e07a', emissiveIntensity: 1.2 }), 25.3, 2.45, 8.07, { nocast: true });
}

// ---------------------------------------------------------------------
// RUANG OPERATION CONTROL (0-7 x 10-16)
// ---------------------------------------------------------------------
{
  SEAT.op_control = desk(0.8, 12.1, 1.6, 1.0, '#9aa3ad', 'code', 'op_control', Math.PI); SEAT.op1 = desk(3.5, 12.1, 1.6, 1.0, '#9aa3ad', 'code', 'op1', Math.PI);
  FACE.op_control = FACE.op1 = Math.PI; chair(SEAT.op_control, Math.PI); chair(SEAT.op1, Math.PI);
  const vw = new THREE.Group(); vw.position.set(3.2, 1.82, 10.12); S.add(vw);
  add(vw, RB(4.8, 0.82, 0.05, 0.01), BLACK, 0, 0, 0);
  for (let i = 0; i < 4; i++) add(vw, new THREE.PlaneGeometry(1.12, 0.7), mkScreen('wall', null), -1.77 + i * 1.18, 0, 0.028, { nocast: true });
  add(vw, BX(4.8, 0.06, 0.1), STEEL, 0, -0.46, 0.04);
  const mapT = paint(512, 256, (g, w, h) => { g.fillStyle = '#e9e4d8'; g.fillRect(0, 0, w, h); g.strokeStyle = '#a89f8c'; g.lineWidth = 2; for (let i = 0; i < 16; i++) g.strokeRect(20 + (i % 8) * 58, 30 + (i >> 3) * 100, 50, 80); g.fillStyle = '#1f3a5f'; g.font = 'bold 20px sans-serif'; g.fillText('DENAH GUDANG WH-01', 20, 22); });
  const mp = new THREE.Group(); mp.position.set(6.9, 1.5, 11.6); mp.rotation.y = -Math.PI / 2; S.add(mp);
  add(mp, RB(1.5, 0.8, 0.03, 0.01), STEEL, 0, 0, 0); add(mp, new THREE.PlaneGeometry(1.42, 0.72), M('#ffffff', { map: mapT, roughness: 0.4 }), 0, 0, 0.02, { nocast: true });
  plant(6.4, 15.3, 1); plant(0.6, 10.9, 0.9); extinguisher(0.7, 15.6, 0);
}

// ---------------------------------------------------------------------
// RUANG ASSET MANAGEMENT (7-14 x 10-16)
// ---------------------------------------------------------------------
{
  SEAT.asset = desk(8.0, 11.9, 1.9, 1.0, '#a58a63', 'code', 'asset', Math.PI); FACE.asset = Math.PI; chair(SEAT.asset, Math.PI);
  palletRack(8.0, 15.0, 5.2);
  crateStack(12.8, 11.3);
  cabinet(8.2, 10.35, 1.2, '#b9bfc6');
  signBoard(7.1, 1.7, 11.0, 1.5, 0.95, Math.PI / 2, 'ASSET REGISTER', ['Forklift & alat berat', 'Rak & pallet', 'Perangkat & inventaris'], '#1f6f8b');
  plant(13.55, 10.6, 0.9);
  add(S, RB(1.0, 0.05, 0.6, 0.015), P('#8a6b5a', { map: WOOD, roughness: 0.4 }), 11.0, 0.78, 14.0); [[10.55, 13.75], [11.45, 13.75], [10.55, 14.25], [11.45, 14.25]].forEach(p => add(S, BX(0.04, 0.76, 0.04), STEEL, p[0], 0.38, p[1]));
  ob(10.5, 13.7, 11.5, 14.3);
}

// ---------------------------------------------------------------------
// RUANG HSE (14-20 x 10-16)
// ---------------------------------------------------------------------
{
  SEAT.hse = desk(14.7, 11.8, 1.7, 1.0, '#b08a55', 'code', 'hse', Math.PI); FACE.hse = Math.PI; chair(SEAT.hse, Math.PI);
  const lk = M('#e8751a', { roughness: 0.45, metalness: 0.3 });
  for (let i = 0; i < 5; i++) { add(S, RB(0.48, 1.8, 0.42, 0.015), lk, 14.75 + i * 0.5, 0.9, 15.7); add(S, BX(0.3, 0.02, 0.02), STEEL, 14.75 + i * 0.5, 1.2, 15.48); }
  ob(14.45, 15.3, 17.3, 15.95); ao(15.9, 15.6, 3.2, 1.2, 0.5);
  add(S, new THREE.CylinderGeometry(0.6, 0.6, 0.05, 28), P('#d8d2c4', { roughness: 0.3, clearcoat: 0.5 }), 18.3, 0.74, 14.0); add(S, new THREE.CylinderGeometry(0.04, 0.04, 0.72, 10), STEEL, 18.3, 0.37, 14.0); ob(17.65, 13.35, 18.95, 14.65);
  chairL(18.3, 13.1, 0, '#c4572e'); chairL(17.45, 14.0, Math.PI / 2, '#c4572e'); chairL(19.15, 14.0, -Math.PI / 2, '#c4572e');
  for (let i = 0; i < 3; i++) add(S, new THREE.SphereGeometry(0.11, 14, 10, 0, 6.283, 0, 1.57), M(['#ffffff', '#f2c200', '#e8751a'][i], { roughness: 0.4 }), 18.0 + i * 0.3, 0.77, 13.95);
  signBoard(19.9, 1.7, 13.25, 1.3, 0.9, -Math.PI / 2, 'ZERO ACCIDENT', ['APD wajib', 'Lapor near miss', 'Jalur evakuasi'], '#d9541e');
  add(S, BX(0.04, 0.4, 0.4), M('#f4f4f0', { roughness: 0.5 }), 14.12, 1.4, 11.0); add(S, BX(0.045, 0.22, 0.06), M('#c0261e'), 14.14, 1.4, 11.0); add(S, BX(0.045, 0.06, 0.22), M('#c0261e'), 14.14, 1.4, 11.0);
  extinguisher(19.6, 10.35, 0); plant(19.4, 15.4, 0.9);
}

// ---------------------------------------------------------------------
// RUANG SERVER (20-26 x 10-16)
// ---------------------------------------------------------------------
const LEDT = paint(64, 128, (g, w, h) => { g.fillStyle = '#000'; g.fillRect(0, 0, w, h); for (let r = 0; r < 14; r++) for (let c = 0; c < 5; c++) if (rnd() < 0.8) { g.fillStyle = rnd() < 0.7 ? '#19ff7a' : rnd() < 0.5 ? '#ffb020' : '#3aa0ff'; g.fillRect(6 + c * 11, 6 + r * 8.6, 5, 4); } });
const LEDM = new THREE.MeshStandardMaterial({ color: '#0d0f12', emissive: '#ffffff', emissiveMap: LEDT, emissiveIntensity: 1, roughness: 0.6 });
function rack(x, z, ry) {
  const g = new THREE.Group(); g.position.set(x, 0, z); g.rotation.y = ry; S.add(g);
  add(g, RB(0.72, 2.1, 0.95, 0.02), M('#16181c', { roughness: 0.45, metalness: 0.4 }), 0, 1.05, 0);
  add(g, new THREE.PlaneGeometry(0.6, 1.9), LEDM, 0, 1.05, 0.485, { nocast: true });
  add(g, BX(0.02, 1.9, 0.02), STEEL, 0.33, 1.05, 0.49);
}
[20.85, 21.7, 23.9, 24.75].forEach(x => rack(x, 10.8, 0));
ob(20.45, 10.3, 22.1, 11.3); ob(23.5, 10.3, 25.15, 11.3);
[20.9, 21.8, 22.7, 23.6, 24.5].forEach(x => rack(x, 15.0, Math.PI));
ob(20.5, 14.5, 24.9, 15.5); ao(22.7, 15.0, 5.2, 1.8, 0.5); ao(22.8, 10.8, 5.6, 1.8, 0.5);
add(S, RB(1.0, 1.9, 0.7, 0.03), M('#dfe3e8', { roughness: 0.35 }), 25.3, 0.95, 13.0); ob(24.75, 12.6, 25.9, 13.4); // unit pendingin

// =====================================================================
// AREA PARKIR (di depan gedung)
// =====================================================================
function car(x, z, col, ry) {
  const g = new THREE.Group(); g.position.set(x, 0, z); g.rotation.y = ry || 0; S.add(g);
  const body = P(col, { roughness: 0.25, metalness: 0.5, clearcoat: 1, clearcoatRoughness: 0.05 }), gl = P('#16202c', { roughness: 0.05, metalness: 0.2, transparent: true, opacity: 0.88 });
  add(g, RB(1.8, 0.5, 4.3, 0.18), body, 0, 0.55, 0); add(g, RB(1.6, 0.5, 2.3, 0.2), gl, 0, 1.05, -0.1); add(g, RB(1.58, 0.06, 2.0, 0.05), body, 0, 1.32, -0.1);
  [[-0.82, 1.35], [0.82, 1.35], [-0.82, -1.35], [0.82, -1.35]].forEach(w => add(g, new THREE.CylinderGeometry(0.34, 0.34, 0.24, 18), BLACK, w[0], 0.34, w[1], { r: [0, 0, Math.PI / 2] }));
  [-0.6, 0.6].forEach(q => { add(g, BX(0.4, 0.12, 0.05), new THREE.MeshStandardMaterial({ color: '#fff', emissive: '#ffffdd', emissiveIntensity: 2 }), q, 0.62, 2.16); add(g, BX(0.4, 0.1, 0.05), new THREE.MeshStandardMaterial({ color: '#900', emissive: '#c00', emissiveIntensity: 1 }), q, 0.62, -2.16); });
  ao(x, z, 2.6, 5.0, 0.55);
}
{
  const ln = M('#e8e8e0', { roughness: 0.7 });
  for (let k = 0; k < 7; k++) { const m = new THREE.Mesh(new THREE.PlaneGeometry(0.12, 3.8), ln); m.rotation.x = -Math.PI / 2; m.position.set(2 + k * 4, 0.011, 18.6); S.add(m); }
  car(4, 18.7, '#b22b2b', Math.PI); car(12, 18.7, '#e8e8ea', Math.PI); car(20, 18.7, '#1f4e8f', Math.PI);
  [[24.6, 18.6], [26.2, 19.8]].forEach(p => {
    add(S, new THREE.CylinderGeometry(0.1, 0.14, 1.6, 10), M('#6b4a2f'), p[0], 0.8, p[1]);
    [[0, 2.0, 0, 0.9], [0.4, 2.5, 0.2, 0.7], [-0.35, 2.4, -0.2, 0.65]].forEach(f => add(S, new THREE.SphereGeometry(f[3], 14, 10), M('#2e6b3a', { roughness: 0.8, bumpMap: FAB, bumpScale: 1 }), p[0] + f[0], f[1], p[1] + f[2]));
  });
}
// =====================================================================
// LINGKUNGAN LUAR: halaman rumput, trotoar, jalan, pohon, lampu jalan
// =====================================================================
{
  const grassT = paint(512, 512, (g, w, h) => {
    g.fillStyle = '#5c8f4a'; g.fillRect(0, 0, w, h);
    for (let i = 0; i < 90; i++) { g.fillStyle = 'hsla(' + (92 + rnd() * 26) + ',' + (32 + rnd() * 20) + '%,' + (30 + rnd() * 16) + '%,' + (0.12 + rnd() * 0.14) + ')'; g.beginPath(); g.ellipse(rnd() * w, rnd() * h, 14 + rnd() * 46, 8 + rnd() * 26, rnd() * 3, 0, 6.3); g.fill(); }
    for (let i = 0; i < 9000; i++) { g.fillStyle = rnd() < 0.5 ? 'rgba(20,50,15,.22)' : 'rgba(150,200,90,.2)'; g.fillRect(rnd() * w, rnd() * h, 1.5, 2.5); }
  }, true, [1, 1]);
  const walkT = paint(256, 256, (g, w, h) => { g.fillStyle = '#c9c6bd'; g.fillRect(0, 0, w, h); speck(g, w, h, 5000, 0.06); grid(g, w, h, 2, 'rgba(60,58,52,.38)', 2); }, true, [1, 1]);
  const roadT = paint(256, 256, (g, w, h) => { g.fillStyle = '#2f3237'; g.fillRect(0, 0, w, h); speck(g, w, h, 9000, 0.08); }, true, [1, 1]);
  const flat = (x0, z0, x1, z1, mat, tile, y) => {
    const w = x1 - x0, d = z1 - z0, g = new THREE.PlaneGeometry(w, d), uv = g.attributes.uv;
    for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * w / tile, uv.getY(i) * d / tile);
    const m = new THREE.Mesh(g, mat); m.rotation.x = -Math.PI / 2; m.position.set((x0 + x1) / 2, y, (z0 + z1) / 2); m.receiveShadow = true; S.add(m);
  };
  flat(-390, -390, 410, 410, M('#ffffff', { map: grassT, roughness: 1, bumpMap: BN, bumpScale: 0.5 }), 8, -0.12);
  flat(-14, 21.4, 40, 23.6, M('#ffffff', { map: walkT, roughness: 0.85 }), 2, -0.105);
  flat(-80, 26.2, 110, 34, M('#ffffff', { map: roadT, roughness: 0.95 }), 4, -0.105);
  const paintM = M('#e9e3c0', { roughness: 0.7 });
  for (let x = -76; x < 108; x += 4.5) { const m = new THREE.Mesh(new THREE.PlaneGeometry(2.4, 0.16), paintM); m.rotation.x = -Math.PI / 2; m.position.set(x, -0.1, 30.1); S.add(m); }
  [26.6, 33.6].forEach(z => { const m = new THREE.Mesh(new THREE.PlaneGeometry(190, 0.12), M('#e8e8e0', { roughness: 0.7 })); m.rotation.x = -Math.PI / 2; m.position.set(15, -0.1, z); S.add(m); });
  add(S, BX(28.4, 0.12, 0.16), M('#b9b6ae', { roughness: 0.8 }), 13, -0.05, 21.48);
  add(S, RB(52, 0.74, 0.6, 0.06), M('#2f6b35', { roughness: 0.92, bumpMap: FAB, bumpScale: 1.6 }), 13, 0.25, 24.3, {});
  const TR = M('#6b4a2f', { roughness: 0.9, bumpMap: FAB, bumpScale: 1 });
  const LEAF = ['#2e6b3a', '#3b7d3f', '#2a5e34'].map(c => M(c, { roughness: 0.85, bumpMap: FAB, bumpScale: 1.2 }));
  const tree = (x, z, sc, k) => {
    const g = new THREE.Group(); g.position.set(x, -0.12, z); g.scale.setScalar(sc); S.add(g);
    add(g, new THREE.CylinderGeometry(0.12, 0.2, 2.2, 10), TR, 0, 1.1, 0);
    [[0, 2.9, 0, 1.25], [0.7, 2.5, 0.3, 0.95], [-0.65, 2.6, -0.25, 1.0], [0.1, 3.7, 0.1, 0.9], [-0.3, 3.3, 0.6, 0.8]].forEach((f, i) => add(g, new THREE.IcosahedronGeometry(f[3], 2), LEAF[(k + i) % 3], f[0], f[1], f[2]));
  };
  [[-3, -5, 1.0], [6, -7, 1.15], [16, -6, 0.95], [26, -7, 1.1], [35, -5, 1.0], [-6, 3, 1.05], [-8, 11, 1.2], [-6, 18, 1.0],
   [31.5, 4, 1.1], [33.5, 12, 1.0], [32, 19, 1.15], [-6.5, 22.2, 0.95], [33, 22.4, 1.0], [44, 22.4, 1.1], [-18, 22.4, 1.05]].forEach((t, i) => tree(t[0], t[1], t[2], i));
  const post = (x, z) => {
    add(S, new THREE.CylinderGeometry(0.05, 0.07, 4.2, 10), STEEL, x, 1.98, z);
    add(S, RB(0.95, 0.12, 0.3, 0.04), BLACK, x + 0.42, 4.1, z);
    add(S, BX(0.7, 0.02, 0.22), new THREE.MeshStandardMaterial({ color: '#fff', emissive: '#fff2c9', emissiveIntensity: 1.6 }), x + 0.42, 4.03, z, { nocast: true });
  };
  [1, 13, 25, 37, -11].forEach(x => post(x, 22.5));
}
const ROOMS = [['RUANG HRD', 4.5, 0.4, 2.7], ['RUANG ADMIN CONTROL', 13, 0.4, 2.7], ['RUANG MEETING', 21.5, 0.4, 2.7], ['KORIDOR', 3, 8.2, 2.7], ['RUANG OPERATION CONTROL', 3.5, 10.4, 2.7], ['RUANG ASSET MANAGEMENT', 10.5, 10.4, 2.7], ['RUANG HSE', 17, 10.4, 2.7], ['RUANG SERVER', 23, 10.4, 2.7], ['AREA PARKIR', 13, 16.6, 0.3]];

// =====================================================================
// Karakter manusia (humanoid prosedural, PBR)
// =====================================================================
const LOOK = {
  hrd: { female: true, skin: '#e8b894', hair: '#2a1a14', shirt: '#e0568a', pants: '#2b2f3f', sleeve: 'short' },
  admin_control: { female: false, skin: '#d9a47c', hair: '#161616', shirt: '#2f6fd1', pants: '#2b3350', tie: '#b3261e', glasses: true, sleeve: 'long' },
  asset: { female: true, skin: '#e6b48f', hair: '#2a1a14', shirt: '#1f6f8b', pants: '#2b2f3f', sleeve: 'long' },
  hse: { female: false, skin: '#c68e65', hair: '#1c1c1c', shirt: '#e8751a', pants: '#2b3350', vest: true, hat: '#ffffff', sleeve: 'long' },
  op1: { female: false, skin: '#c68e65', hair: '#1c1c1c', shirt: '#3d4b5c', pants: '#2b3350', glasses: true, sleeve: 'long' },
  op2: { female: true, skin: '#e0b08a', hair: '#3a2a1a', shirt: '#7a5ccf', pants: '#2b2f3f', sleeve: 'short' },
  satpam: { female: false, skin: '#a9754f', hair: '#111111', shirt: '#22304a', pants: '#1b2233', hat: '#1c2740', sleeve: 'long' },
  staf1: { female: false, skin: '#d9a47c', hair: '#2a1a14', shirt: '#8a5a44', pants: '#2f3340', sleeve: 'long' },
  staf2: { female: true, skin: '#e8b894', hair: '#4a2f20', shirt: '#2fa6a0', pants: '#2b3350', sleeve: 'short' },
  op_control: { female: false, skin: '#b9825a', hair: '#3a2a1a', shirt: '#4b5563', pants: '#2c3340', vest: true, hat: '#f2c200', sleeve: 'long' },
  kamu: { female: false, skin: '#e0b08a', hair: '#222222', shirt: '#8d99ae', pants: '#2a2f3a', sleeve: 'long' }
};
const FALL = [{ female: false, skin: '#d9a47c', hair: '#222', shirt: '#7a5ccf', pants: '#2b3350', sleeve: 'long' }, { female: true, skin: '#e6b48f', hair: '#3a2a1a', shirt: '#2fa6a0', pants: '#2b2f3f', sleeve: 'short' }];

function makePerson(look) {
  const W = look.female ? 0.9 : 1;
  const skin = P(look.skin, { roughness: 0.55, sheen: 0.6, sheenRoughness: 0.45, sheenColor: new THREE.Color('#ff9c88'), clearcoat: 0.04, clearcoatRoughness: 0.5 });
  const shirt = cloth(look.shirt, 0.85), pants = cloth(look.pants, 0.9), shoe = M('#16171b', { roughness: 0.38 }), hair = M(look.hair, { roughness: 0.5, metalness: 0.1 });
  const eyeW = M('#f4f1ea', { roughness: 0.2 }), iris = M('#2a1a10', { roughness: 0.2 }), lip = M(look.female ? '#b8485a' : '#a9584e', { roughness: 0.5 });
  const root = new THREE.Group(), hips = new THREE.Group(); root.add(hips);
  const mk = (p, g, m, x, y, z) => { const o = new THREE.Mesh(g, m); o.position.set(x || 0, y || 0, z || 0); o.castShadow = true; o.receiveShadow = true; p.add(o); return o; };
  const sph = (r, x, y, z) => { const g = new THREE.SphereGeometry(r, 20, 14); g.scale(x, y, z); return g; };
  const cap = (r, l, x, z) => { const g = new THREE.CapsuleGeometry(r, l, 6, 16); g.scale(x || 1, 1, z || 1); return g; };

  mk(hips, sph(0.15, 1.2 * W, 0.8, 0.85), pants);
  const spine = new THREE.Group(); spine.position.y = 0.05; hips.add(spine);
  const chest = mk(spine, cap(0.125, 0.26, 1.2 * W, 0.72), shirt, 0, 0.24, 0);
  mk(spine, cap(0.11, 0.1, 1.05 * W, 0.7), shirt, 0, 0.04, 0);
  [-1, 1].forEach(s => mk(spine, sph(0.06, 1, 1, 1), shirt, s * 0.19 * W, 0.41, 0));
  if (look.vest) {
    mk(spine, cap(0.133, 0.26, 1.2 * W, 0.74), M('#c9dc1a', { roughness: 0.75, bumpMap: FAB, bumpScale: 0.5 }), 0, 0.24, 0);
    const rf = M('#d9dde0', { roughness: 0.3, metalness: 0.6 });
    [0.17, 0.31].forEach(y => { const g = new THREE.CylinderGeometry(0.137, 0.137, 0.03, 28, 1, true); g.scale(1.2 * W, 1, 0.74); mk(spine, g, rf, 0, y, 0); });
  }
  if (look.tie) {
    const tg = new THREE.CylinderGeometry(0.014, 0.025, 0.24, 6); tg.scale(1, 1, 0.35);
    mk(spine, tg, P(look.tie, { roughness: 0.4, sheen: 1, sheenColor: new THREE.Color('#ffffff') }), 0, 0.33, 0.094); mk(spine, sph(0.02, 1, 0.9, 0.7), M(look.tie, { roughness: 0.4 }), 0, 0.45, 0.092);
  }
  mk(spine, new THREE.CylinderGeometry(0.05, 0.056, 0.12, 16), skin, 0, 0.5, 0);
  { const col = new THREE.TorusGeometry(0.058, look.tie ? 0.017 : 0.013, 8, 24); col.rotateX(Math.PI / 2); mk(spine, col, look.tie ? M('#f4f4f2', { roughness: 0.6 }) : shirt, 0, 0.465, 0); }

  const head = new THREE.Group(); head.position.set(0, 0.55, 0); spine.add(head);
  mk(head, sph(0.088, 1, 1.22, 1.1), skin, 0, 0.1, 0);
  mk(head, sph(0.07, 0.95, 0.85, 1), skin, 0, 0.035, 0.02);
  { const ng = new THREE.ConeGeometry(0.013, 0.035, 8); ng.rotateX(Math.PI / 2); mk(head, ng, skin, 0, 0.082, 0.097); }
  { const lg = new THREE.CapsuleGeometry(0.0055, 0.028, 4, 8); lg.rotateZ(Math.PI / 2); mk(head, lg, lip, 0, 0.05, 0.091); }
  const eyes = [];
  [-1, 1].forEach(s => {
    const e = mk(head, sph(0.0135, 1, 0.85, 0.7), eyeW, s * 0.033, 0.108, 0.083); mk(e, sph(0.0075, 1, 1, 0.5), iris, 0, 0, 0.0085); eyes.push(e);
    const b = mk(head, BX(0.034, 0.006, 0.01), hair, s * 0.034, 0.133, 0.09); b.rotation.z = s * 0.1;
    mk(head, sph(0.016, 0.5, 1, 0.8), skin, s * 0.089, 0.095, -0.005);
    if (look.glasses) mk(head, new THREE.TorusGeometry(0.021, 0.0022, 8, 20), BLACK, s * 0.034, 0.108, 0.095);
  });
  if (look.glasses) mk(head, BX(0.02, 0.003, 0.003), BLACK, 0, 0.112, 0.096);
  const hc = new THREE.SphereGeometry(1, 28, 16, 0, Math.PI * 2, 0, Math.PI * 0.52); hc.scale(0.097, 0.118, 0.106);
  mk(head, hc, hair, 0, 0.104, -0.006).rotation.x = -0.42;   // garis rambut di atas alis (mata terlihat)
  if (look.female) {
    mk(head, cap(0.095, 0.28, 1, 0.7), hair, 0, -0.04, -0.075);
    [-1, 1].forEach(s => mk(head, cap(0.026, 0.16, 1, 1), hair, s * 0.088, 0.06, -0.015));
  }
  if (look.hat) {
    const hm = P(look.hat, { roughness: 0.3, clearcoat: 0.7, clearcoatRoughness: 0.2 });
    const hg = new THREE.SphereGeometry(1, 24, 12, 0, Math.PI * 2, 0, Math.PI * 0.5); hg.scale(0.108, 0.098, 0.116); mk(head, hg, hm, 0, 0.15, 0);
    const br = new THREE.CylinderGeometry(0.11, 0.112, 0.008, 28); br.scale(1, 1, 1.25); mk(head, br, hm, 0, 0.148, 0.02);
  }

  const arms = {};
  [1, -1].forEach(s => {
    const sh = new THREE.Group(); sh.position.set(s * 0.19 * W, 0.41, 0); spine.add(sh);
    mk(sh, cap(0.047, 0.2, 1, 1), shirt, 0, -0.15, 0);
    const el = new THREE.Group(); el.position.y = -0.3; sh.add(el);
    mk(el, sph(0.043, 1, 1, 1), look.sleeve === 'long' ? shirt : skin, 0, 0, 0);
    mk(el, cap(0.037, 0.2, 1, 1), look.sleeve === 'long' ? shirt : skin, 0, -0.14, 0);
    const hd = new THREE.Group(); hd.position.y = -0.27; el.add(hd);
    mk(hd, sph(0.036, 1, 1.45, 0.55), skin, 0, -0.045, 0); mk(hd, sph(0.011, 1, 2.2, 1), skin, -s * 0.03, -0.035, 0.012);
    arms[s] = { sh, el, hd };
  });
  const legs = {};
  [1, -1].forEach(s => {
    const hp = new THREE.Group(); hp.position.set(s * 0.095 * W, -0.03, 0); hips.add(hp);
    mk(hp, cap(0.078, 0.3, 1, 1.05), pants, 0, -0.23, 0);
    const kn = new THREE.Group(); kn.position.y = -0.47; hp.add(kn);
    mk(kn, sph(0.062, 1, 1, 1), pants); mk(kn, cap(0.058, 0.3, 1, 1), pants, 0, -0.22, 0);
    const an = new THREE.Group(); an.position.y = -0.43; kn.add(an);
    const fg = new THREE.CapsuleGeometry(0.047, 0.1, 6, 12); fg.rotateX(Math.PI / 2); fg.scale(1, 0.75, 1); mk(an, fg, shoe, 0, -0.045, 0.05); mk(an, new THREE.BoxGeometry(0.092, 0.012, 0.2), M('#e6e3dc', { roughness: 0.7 }), 0, -0.076, 0.052);
    legs[s] = { hp, kn, an };
  });
  scene.add(root);
  return { root, hips, spine, chest, head, eyes, arms, legs };
}

// =====================================================================
// Pergerakan agent (lewat pintu, menghindari perabot dan partisi)
// =====================================================================
const WAIT = [[13.3, 3.7], [14.4, 4.0], [15.5, 3.7]];
const IDLE = [[12.6, 9.0], [4.6, 9.0], [21.0, 9.0], [8.2, 9.0], [17.0, 9.0], [2.6, 6.4], [4.0, 6.2], [13.0, 6.6], [22.5, 6.4], [9.6, 14.3], [17.0, 14.2], [23.2, 13.0], [2.6, 14.9], [6.0, 8.8]];
const PAT = [[22, 9], [12.5, 9], [3, 9], [8, 9], [17, 9]];
const WAN2 = [[12.6, 9.0], [21, 6.4], [3.0, 9.0], [23.2, 13.0], [9.6, 14.3]];
function hit(ax, ay, bx, by, r, m) {
  const x0 = r[0] - m, y0 = r[1] - m, x1 = r[2] + m, y1 = r[3] + m, dx = bx - ax, dy = by - ay;
  const p = [-dx, dx, -dy, dy], q = [ax - x0, x1 - ax, ay - y0, y1 - ay]; let t0 = 0, t1 = 1;
  for (let i = 0; i < 4; i++) {
    if (p[i] === 0) { if (q[i] < 0) return false; }
    else { const t = q[i] / p[i]; if (p[i] < 0) { if (t > t1) return false; if (t > t0) t0 = t; } else { if (t < t0) return false; if (t < t1) t1 = t; } }
  }
  return t0 < t1;
}
const clear = (ax, ay, bx, by) => !OB.some(r => hit(ax, ay, bx, by, r, 0.28));
const CORN = [];
OB.forEach(r => [[r[0] - 0.45, r[1] - 0.45], [r[2] + 0.45, r[1] - 0.45], [r[2] + 0.45, r[3] + 0.45], [r[0] - 0.45, r[3] + 0.45]].forEach(w => {
  if (w[0] < 0.3 || w[0] > NX - 0.3 || w[1] < 0.3 || w[1] > NZ - 0.3) return;
  if (OB.some(o => w[0] > o[0] - 0.28 && w[0] < o[2] + 0.28 && w[1] > o[1] - 0.28 && w[1] < o[3] + 0.28)) return;
  CORN.push(w);
}));
const ADJ = CORN.map(() => []);
for (let i = 0; i < CORN.length; i++) for (let j = i + 1; j < CORN.length; j++) {
  if (clear(CORN[i][0], CORN[i][1], CORN[j][0], CORN[j][1])) { const d = Math.hypot(CORN[i][0] - CORN[j][0], CORN[i][1] - CORN[j][1]); ADJ[i].push([j, d]); ADJ[j].push([i, d]); }
}
const inObs = (x, y) => OB.some(o => x > o[0] - 0.28 && x < o[2] + 0.28 && y > o[1] - 0.28 && y < o[3] + 0.28);
function nearFree(x, y) {   // titik bebas terdekat bila posisi berada terlalu dekat tembok/perabot
  if (!inObs(x, y)) return null;
  for (let r = 0.1; r <= 1.8; r += 0.1) for (let k = 0; k < 24; k++) {
    const a = k / 24 * 6.283, px = x + Math.cos(a) * r, py = y + Math.sin(a) * r;
    if (px > 0.3 && px < NX - 0.3 && py > 0.3 && py < NZ - 0.3 && !inObs(px, py) && !OB.some(o => hit(x, y, px, py, o, 0.06))) return [px, py];
  }
  return null;
}
function route(ax, ay, bx, by) {
  const s = nearFree(ax, ay), e = nearFree(bx, by);
  const p = route0(s ? s[0] : ax, s ? s[1] : ay, e ? e[0] : bx, e ? e[1] : by);
  if (e) p.push([bx, by]);
  return s ? [s].concat(p) : p;
}
function route0(ax, ay, bx, by) {   // graf visibilitas (dihitung sekali) + Dijkstra
  if (clear(ax, ay, bx, by)) return [[bx, by]];
  const n = CORN.length, S0 = n, E0 = n + 1, dist = new Array(n + 2).fill(1e9), prev = new Array(n + 2).fill(-1), done = new Array(n + 2).fill(false), visS = [], visE = new Array(n).fill(false);
  for (let i = 0; i < n; i++) { if (clear(ax, ay, CORN[i][0], CORN[i][1])) visS.push(i); if (clear(CORN[i][0], CORN[i][1], bx, by)) visE[i] = true; }
  dist[S0] = 0;
  const relax = (u, v, l) => { if (dist[u] + l < dist[v]) { dist[v] = dist[u] + l; prev[v] = u; } };
  for (let it = 0; it < n + 2; it++) {
    let u = -1; for (let i = 0; i < n + 2; i++) if (!done[i] && dist[i] < 1e9 && (u < 0 || dist[i] < dist[u])) u = i;
    if (u < 0) break; done[u] = true; if (u === E0) break;
    if (u === S0) visS.forEach(i => relax(u, i, Math.hypot(ax - CORN[i][0], ay - CORN[i][1])));
    else { ADJ[u].forEach(e => relax(u, e[0], e[1])); if (visE[u]) relax(u, E0, Math.hypot(CORN[u][0] - bx, CORN[u][1] - by)); }
  }
  if (prev[E0] < 0) return [[bx, by]];
  const out = []; for (let i = E0; i !== S0; i = prev[i]) out.unshift(i === E0 ? [bx, by] : CORN[i]);
  return out;
}
function working(c) { return c.status === 'jalan' || c.status === 'antri'; }
function waiting(c) { return c.status === 'nunggu_lu' || c.status === 'error'; }
function seatOf(c) { return SEAT[c.kunci] || IDLE[c.idx % IDLE.length]; }
function goto(c, x, y, seat) { c.tx = x; c.ty = y; c.atSeat = !!seat; c.path = route(c.x, c.y, x, y); }
function pickIdle(c) {
  if (!c.npc && rnd() < 0.3 && SEAT[c.kunci]) { const s = SEAT[c.kunci]; goto(c, s[0], s[1], true); c.dwell = 4 + rnd() * 4; }
  else { const pts = c.pts || IDLE, p = pts[Math.floor(rnd() * pts.length)]; goto(c, p[0], p[1], false); c.dwell = 4 + rnd() * 5; }
}
function pickTarget(c) {
  if (working(c) && SEAT[c.kunci]) { const s = SEAT[c.kunci]; goto(c, s[0], s[1], true); }
  else if (waiting(c)) { const w = WAIT[c.idx % WAIT.length]; goto(c, w[0], w[1], false); }
  else pickIdle(c);
}
let saved = {};
try { saved = JSON.parse(sessionStorage.getItem('kantor_pos3d_v3') || '{}'); } catch (e) {}
function newState(sit) { return { sit: sit ? 1 : 0, walk: 0, typ: 0, wave: 0, err: 0, ph: 0 }; }
function person(o) {
  const c = Object.assign({ walking: false, sitting: false, atSeat: false, dwell: 0, seed: rnd() * 9, h: 0, hT: 0, path: [], face: 0, status: 'idle', pts: null, fixed: false, npc: false, typing: false, x: 0, y: 0, tx: 0, ty: 0, idx: 0 }, o);
  c.rig = makePerson(o.look); c.q = newState(false); return c;
}
const chars = D.agents.map((a, i) => {
  const c = person(Object.assign({}, a, { id: a.kunci, idx: i, seed: i * 2.1, look: LOOK[a.kunci] || FALL[i % FALL.length], face: FACE[a.kunci] || 0 }));
  const s = seatOf(c);
  if (saved[a.kunci] && !inObs(saved[a.kunci][0], saved[a.kunci][1])) { c.x = saved[a.kunci][0]; c.y = saved[a.kunci][1]; }
  else if (working(c)) { c.x = s[0]; c.y = s[1]; c.q.sit = 1; c.sitting = true; c.h = c.hT = c.face; }
  else if (waiting(c)) { const w = WAIT[i % WAIT.length]; c.x = w[0]; c.y = w[1]; c.hT = c.h = Math.PI; }
  else { const p = IDLE[(i * 2 + 1) % IDLE.length]; c.x = p[0]; c.y = p[1]; }
  pickTarget(c);
  c.blob = ao(c.x, c.y, 0.8, 0.8, 0.55); c.blob.removeFromParent(); scene.add(c.blob);
  return c;
});
// staf figuran (tanpa label): resepsionis, operator kontrol, staf kerja, satpam, staf pantry
const npcs = [];
function npcSit(id, seat, face) { const c = person({ id, kunci: id, look: LOOK[id], npc: true, fixed: true, typing: true, face }); c.x = c.tx = seat[0]; c.y = c.ty = seat[1]; c.sitting = true; c.q.sit = 1; c.h = c.hT = face; npcs.push(c); }
function npcWalk(id, pts, i0) { const c = person({ id, kunci: id, look: LOOK[id], npc: true, pts, idx: i0 }); const p = pts[i0 % pts.length]; c.x = p[0]; c.y = p[1]; pickIdle(c); c.blob = ao(c.x, c.y, 0.8, 0.8, 0.55); c.blob.removeFromParent(); scene.add(c.blob); npcs.push(c); }
npcSit('staf1', SEAT.staf1, 0); npcSit('asset', SEAT.asset, FACE.asset); npcSit('hse', SEAT.hse, FACE.hse); npcSit('op1', SEAT.op1, FACE.op1);
npcWalk('satpam', PAT, 0); npcWalk('staf2', WAN2, 1);
const people = chars.concat(npcs);
updateDoors(1, people);   // saat dimuat, pintu langsung terbuka bila ada orang di dekatnya
screens.forEach(sc => { sc.ch = sc.owner ? (people.filter(p => p.id === sc.owner)[0] || null) : null; });

function update(c, dt) {
  if (c.fixed) return;
  const wp = c.path.length ? c.path[0] : [c.tx, c.ty];
  const dx = wp[0] - c.x, dy = wp[1] - c.y, d = Math.hypot(dx, dy);
  if (d > 0.05) {
    const s = Math.min(d, 1.6 * dt); c.x += dx / d * s; c.y += dy / d * s; c.walking = true; c.sitting = false; c.hT = Math.atan2(dx, dy);
  } else if (c.path.length) { c.path.shift(); }
  else {
    c.walking = false; c.x = c.tx; c.y = c.ty; c.sitting = c.atSeat;
    if (c.sitting) c.hT = c.face || 0; else if (waiting(c)) c.hT = Math.PI;
    if (c.status === 'idle') { c.dwell -= dt; if (c.dwell <= 0) pickIdle(c); }
  }
}
setInterval(() => { try { const o = {}; chars.forEach(c => { o[c.kunci] = [c.x, c.y]; }); sessionStorage.setItem('kantor_pos3d_v3', JSON.stringify(o)); } catch (e) {} }, 1000);

function pose(c, dt, t) {
  const r = c.rig, q = c.q, k = Math.min(1, dt * 4);
  q.sit += ((c.sitting ? 1 : 0) - q.sit) * k;
  q.walk += ((c.walking ? 1 : 0) - q.walk) * Math.min(1, dt * 6);
  const typT = c.sitting && (working(c) || (c.typing && Math.sin(t * 0.4 + c.seed) > -0.5) || (c.kunci === 'kamu' && Math.sin(t * 0.35 + 1) > -0.2)) ? 1 : 0;
  q.typ += (typT - q.typ) * k;
  q.wave += ((!c.walking && !c.sitting && c.status === 'nunggu_lu' ? 1 : 0) - q.wave) * k;
  q.err += ((!c.walking && !c.sitting && c.status === 'error' ? 1 : 0) - q.err) * k;
  if (c.walking) q.ph += dt * 6.2;
  const s = q.sit, w = q.walk, sw = Math.sin(q.ph) * w;
  let dh = c.hT - c.h; dh = Math.atan2(Math.sin(dh), Math.cos(dh)); c.h += dh * Math.min(1, dt * 7);
  r.root.rotation.y = c.h; r.root.position.set(c.x, 0, c.y);
  r.hips.position.y = lerp(1.01 - Math.abs(Math.sin(q.ph)) * 0.03 * w, 0.575, s);
  r.hips.rotation.y = -sw * 0.12 * (1 - s); r.spine.rotation.y = sw * 0.14;
  r.spine.rotation.x = lerp(0, 0.1, q.typ) + Math.sin(t * 1.5 + c.seed) * 0.008 + q.err * 0.2;
  r.chest.scale.z = 1 + Math.sin(t * 1.7 + c.seed) * 0.014;
  r.head.rotation.x = lerp(0.02, 0.2, q.typ) + q.err * 0.3;
  r.head.rotation.y = Math.sin(t * 0.45 + c.seed) * 0.28 * (1 - s) * (1 - w) * (1 - q.wave) + Math.sin(t * 0.9 + c.seed) * 0.04 * s;
  [1, -1].forEach((sg, i) => {
    const l = r.legs[sg], th = lerp(sg * sw * 0.55, -1.45, s), kn = lerp(Math.max(0, -Math.sin(q.ph + (i ? Math.PI : 0) + 0.5)) * 0.95 * w + 0.04, 1.7, s);
    l.hp.rotation.x = th; l.kn.rotation.x = kn; l.an.rotation.x = -(th + kn) * 0.9;
    const a = r.arms[sg], wr = s * (1 - q.typ);
    let sh = -sg * sw * 0.5 - 0.04, el = -0.2 - 0.35 * w, sz = sg * 0.07 * (1 - w * 0.5) * (1 - s);
    sh += (-0.9 - sh) * q.typ; el += (-0.62 - el) * q.typ;
    sh += (-0.6 - sh) * wr; el += (-1.0 - el) * wr; sz *= 1 - q.typ;
    if (sg < 0) { sh += (-2.7 - sh) * q.wave; el += (-0.4 + Math.sin(t * 9) * 0.4 - el) * q.wave; sz += (-0.3 - sz) * q.wave; }
    sh += (-2.3 - sh) * q.err; el += (-2.2 - el) * q.err;
    sh += Math.sin(t * 13 + sg) * 0.02 * q.typ; el += Math.cos(t * 17 + sg * 2) * 0.06 * q.typ;
    a.sh.rotation.set(sh, 0, sz); a.el.rotation.x = el; a.hd.rotation.x = Math.sin(t * 15 + sg * 1.3) * 0.08 * q.typ;
  });
  const bl = ((t + c.seed * 3.1) % 4.2) < 0.12 ? 0.1 : 1; r.eyes.forEach(e => { e.scale.y = bl; });
  if (c.blob) c.blob.position.set(c.x, 0.013, c.y);
}

// =====================================================================
// Label & gelembung ucapan (DOM overlay, tajam di semua zoom)
// =====================================================================
function bubbleFor(c) {
  if (c.status === 'nunggu_lu') return { text: '🙋 ' + (c.pesan || c.judul), color: '#e67e22' };
  if (c.status === 'error') return { text: '⚠️ ' + (c.pesan || 'Gagal memanggil AI. Cek API key / kuota Groq.'), color: '#e74c3c' };
  if (working(c)) return { text: '⚙️ ' + c.kode + ': ' + c.judul, color: '#3498db' };
  return null;
}
people.forEach(c => {
  if (c.npc) return;
  const el = document.createElement('div'); el.className = 'lb'; el.innerHTML = '<div class="bb"></div><div class="tg"></div>'; $lab.appendChild(el);
  c.el = el; c.bb = el.firstChild; c.tg = el.lastChild;
  c.tg.textContent = c.kunci === 'kamu' ? SUP + ' (Supervisor)' : c.nama + ' · ' + c.peran;
  const b = c.kunci === 'kamu' ? null : bubbleFor(c);
  if (b) { c.bb.textContent = b.text.length > 150 ? b.text.slice(0, 148) + '…' : b.text; c.bb.style.borderColor = b.color; } else c.bb.style.display = 'none';
  c.tg.addEventListener('click', () => focus(c));
});
const _v = new THREE.Vector3();
const rls = ROOMS.map(r => { const el = document.createElement('div'); el.className = 'rl'; el.textContent = r[0]; $lab.appendChild(el); return { el, p: r }; });
function labels(w, h) {
  const ro = Math.max(0, Math.min(1, (camera.position.distanceTo(controls.target) - 14) / 14));
  rls.forEach(r => {
    _v.set(r.p[1], r.p[3], r.p[2]).project(camera);
    if (_v.z > 1 || _v.z < -1) { r.el.style.display = 'none'; return; }
    r.el.style.display = ro < 0.02 ? 'none' : 'block'; r.el.style.opacity = ro.toFixed(2);
    r.el.style.transform = 'translate(' + ((_v.x * 0.5 + 0.5) * w).toFixed(1) + 'px,' + ((-_v.y * 0.5 + 0.5) * h).toFixed(1) + 'px) translate(-50%,-50%)';
  });
  people.forEach(c => {
    if (c.npc) return;
    _v.set(c.x, 1.86 - 0.4 * c.q.sit, c.y).project(camera);
    if (_v.z > 1 || _v.z < -1) { c.el.style.display = 'none'; return; }
    c.el.style.display = 'flex';
    c.el.style.transform = 'translate(' + ((_v.x * 0.5 + 0.5) * w).toFixed(1) + 'px,' + ((-_v.y * 0.5 + 0.5) * h).toFixed(1) + 'px) translate(-50%,-100%)';
  });
}

// =====================================================================
// Kamera: reset / fokus, kualitas adaptif
// =====================================================================
let tw = null;
function tween(p, t) { tw = { p0: camera.position.clone(), t0: controls.target.clone(), p1: p, t1: t, k: 0 }; }
controls.addEventListener('start', () => { tw = null; });
function focus(c) {
  const t = new THREE.Vector3(c.x, 1.0, c.y), dir = camera.position.clone().sub(controls.target).normalize();
  tween(t.clone().add(dir.multiplyScalar(5.5)), t);
}
const b1 = document.getElementById('b1'), b2 = document.getElementById('b2'), ex = document.getElementById('ex');
b1.onclick = () => tween(HOME.p.clone(), HOME.t.clone());
ex.oninput = () => { renderer.toneMappingExposure = parseFloat(ex.value); };

const STEPS = [MAXPR, MAXPR * 0.8, MAXPR * 0.65, 1, 0.8, 0.65].filter((v, i, a) => i === 0 || v < a[i - 1] - 0.05);
let idx = 0, qm = 'auto';
const QM = { auto: 'Auto', high: 'Tinggi', mid: 'Sedang', low: 'Rendah' }, QO = ['auto', 'high', 'mid', 'low'];
function setShadow(sz) { if (sun.shadow.mapSize.x !== sz) { sun.shadow.mapSize.set(sz, sz); if (sun.shadow.map) { sun.shadow.map.dispose(); sun.shadow.map = null; } } }
function setPR(v) { if (Math.abs(v - pr) > 0.01) { pr = v; renderer.setPixelRatio(pr); resize(); } }
function applyQ() {
  if (qm === 'auto') { setPR(STEPS[idx]); setShadow(idx === 0 ? 3072 : idx > 3 ? 1024 : 2048); }
  else if (qm === 'high') { setPR(MAXPR); setShadow(4096); }
  else if (qm === 'mid') { setPR(Math.min(MAXPR, 1.25)); setShadow(2048); }
  else { setPR(1); setShadow(1024); }
  LIGHTS.forEach(l => { l.visible = qm !== 'low' && !(qm === 'auto' && idx >= 3); });
  b2.textContent = 'Kualitas: ' + QM[qm];
}
b2.onclick = () => { qm = QO[(QO.indexOf(qm) + 1) % QO.length]; applyQ(); };

let W0 = 1, H0 = 1;
function resize() {
  W0 = Math.max(1, $v.clientWidth); H0 = Math.max(1, $v.clientHeight);
  renderer.setSize(W0, H0); camera.aspect = W0 / H0;
  camera.fov = camera.aspect < 1.5 ? 32 + (1.5 - camera.aspect) * 20 : 32; camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe($v); resize();

// bekukan objek statis (hemat CPU) lalu mulai
S.updateMatrixWorld(true); S.traverse(o => { o.matrixAutoUpdate = false; });

// =====================================================================
// Loop render
// =====================================================================
let last = performance.now(), vis = true, ema = 16.7, since = 0, scrT = 0, clkT0 = 0, warm = 0;
new IntersectionObserver(e => { vis = e[0].isIntersecting; }).observe($v);
function frame(now) {
  requestAnimationFrame(frame);
  if (document.hidden || !vis) { last = now; return; }
  const raw = now - last, dt = Math.min(0.05, raw / 1000); last = now; const t = now / 1000;
  people.forEach(c => { update(c, dt); pose(c, dt, t); });
  updateDoors(dt, people);
  if (tw) { tw.k = Math.min(1, tw.k + dt / 0.9); const e = tw.k * tw.k * (3 - 2 * tw.k); camera.position.lerpVectors(tw.p0, tw.p1, e); controls.target.lerpVectors(tw.t0, tw.t1, e); if (tw.k >= 1) tw = null; }
  controls.update(); controls.target.clamp(PAN_MIN, PAN_MAX);
  if (now - scrT > 200) {
    scrT = now; LEDM.emissiveIntensity = 0.5 + rnd() * 0.9;
    screens.forEach(sc => { const on = sc.kind !== 'code' ? 1 : (sc.ch && sc.ch.sitting && (working(sc.ch) || sc.ch.typing) ? 1 : 0); if (on || sc.last !== on) drawScreen(sc, on, t); sc.last = on; });
  }
  if (now - clkT0 > 1000) { clkT0 = now; drawClock(); }
  renderer.render(scene, camera);
  labels(W0, H0);
  if (++warm > 30) {   // penyesuaian kualitas otomatis
    ema += (raw - ema) * 0.05; since += raw;
    if (qm === 'auto' && since > 2500) { since = 0; if (ema > 27 && idx < STEPS.length - 1) { idx++; applyQ(); } }
  }
}
requestAnimationFrame(frame);
addEventListener('pagehide', () => { try { renderer.dispose(); } catch (e) {} });
</script></body></html>"""
