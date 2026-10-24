"""Simulasi kantor 3D realistis (WebGL / Three.js) untuk Kantor AI Gudang.

Keadaan agent diambil dari kartu di database (sama seperti versi isometrik):

- jalan/antri -> agent duduk di meja dan mengetik
- nunggu_lu   -> agent berjalan ke meja supervisor (Yogi), berdiri, melambai
- error       -> agent menunggu di meja supervisor, tampak panik
- tidak ada   -> agent jalan-jalan (pantry, lounge, kembali ke meja)

Three.js dimuat dari CDN (jsdelivr), jadi tidak ada dependensi Python baru.
Orbit: seret = putar, scroll = zoom, klik kanan/dua jari = geser.
"""

import json

import streamlit.components.v1 as components

import core
from agents import AGENTS


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
    return {"agents": agents, "counts": hitung}


def html_kantor() -> str:
    data = json.dumps(keadaan(), ensure_ascii=False).replace("</", "<\\/")
    return HTML.replace("__DATA__", data)


def tampilkan(height: int = 560):
    components.html(html_kantor(), height=height)


HTML = r"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
html,body{margin:0;height:100%;background:#0e1117;overflow:hidden;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
#w{position:absolute;inset:0;border-radius:12px;overflow:hidden;background:#0e1117}
#v{position:absolute;inset:0}
canvas{display:block;outline:none}
#lab{position:absolute;inset:0;pointer-events:none;overflow:hidden}
.lb{position:absolute;left:0;top:0;display:flex;flex-direction:column;align-items:center;gap:5px;will-change:transform;white-space:nowrap}
.tg{pointer-events:auto;cursor:pointer;background:rgba(15,17,23,.82);color:#fff;font:600 11px system-ui,sans-serif;padding:3px 9px;border-radius:7px;backdrop-filter:blur(3px);border:1px solid rgba(255,255,255,.12)}
.tg:hover{background:rgba(40,46,60,.95)}
.bb{position:relative;max-width:230px;white-space:normal;background:#fff;color:#1b1f27;font:12px/1.35 system-ui,sans-serif;padding:6px 9px;border-radius:9px;border:2px solid #3498db;box-shadow:0 4px 14px rgba(0,0,0,.35);text-align:left}
.bb:after{content:"";position:absolute;left:50%;bottom:-7px;margin-left:-5px;border:5px solid transparent;border-top-color:inherit}
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
<div class="ttl"><b>JDC Distribution Center</b><span>Kantor AI · Cikarang</span></div>
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
const N = 10, WH = 3.0, WT = 0.12;
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
scene.background = new THREE.Color(0x0e1117);
scene.environment = new THREE.PMREMGenerator(renderer).fromScene(new RoomEnvironment(), 0.04).texture;

const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 90);
const HOME = { p: new THREE.Vector3(15.8, 10.5, 16.2), t: new THREE.Vector3(5, 0.9, 5) };
camera.position.copy(HOME.p);
const controls = new OrbitControls(camera, renderer.domElement);
controls.target.copy(HOME.t);
controls.enableDamping = true; controls.dampingFactor = 0.08;
controls.minDistance = 3.5; controls.maxDistance = 34;
controls.minPolarAngle = 0.15; controls.maxPolarAngle = 1.5;
controls.minAzimuthAngle = -0.2; controls.maxAzimuthAngle = Math.PI / 2 + 0.2;
controls.update();
const PAN_MIN = new THREE.Vector3(-1, 0, -1), PAN_MAX = new THREE.Vector3(11, 3, 11);

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
// Pencahayaan
// =====================================================================
scene.add(new THREE.HemisphereLight(0xdfeaff, 0x9a8670, 0.55));
const sun = new THREE.DirectionalLight(0xfff0d8, 3.2);
sun.position.set(-7, 11, -5); sun.target.position.set(5, 0, 5);
sun.castShadow = true;
{ const c = sun.shadow.camera; c.left = -10; c.right = 10; c.top = 10; c.bottom = -10; c.near = 1; c.far = 38; }
sun.shadow.bias = -0.0004; sun.shadow.normalBias = 0.03; sun.shadow.radius = 3;
sun.shadow.mapSize.set(2048, 2048);
scene.add(sun, sun.target);
const fill = new THREE.DirectionalLight(0xcfe0ff, 0.7); fill.position.set(14, 9, 15); scene.add(fill);
[[3, 2.6, 3.5], [7.6, 2.6, 2.8], [4.6, 2.6, 6.8], [8, 2.6, 7]].forEach(p => {
  const l = new THREE.PointLight(0xffe3bd, 9, 11, 2); l.position.set(p[0], p[1], p[2]); scene.add(l);
});

// =====================================================================
// Ruangan: lantai, dinding, jendela, dekorasi dinding
// =====================================================================
const floorT = paint(1024, 1024, (g, w, h) => {
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
      g.fillStyle = 'rgba(0,0,0,.4)'; g.fillRect(x, r * rh, 2, rh);
      x += len;
    }
    g.fillStyle = 'rgba(0,0,0,.4)'; g.fillRect(0, r * rh, w, 2);
  }
}, true, [N / 4, N / 4]);
const floor = new THREE.Mesh(new THREE.PlaneGeometry(N, N),
  P('#ffffff', { map: floorT, roughness: 0.38, clearcoat: 0.35, clearcoatRoughness: 0.3, bumpMap: noise(10, 10), bumpScale: 0.12 }));
floor.rotation.x = -Math.PI / 2; floor.position.set(N / 2, 0, N / 2); floor.receiveShadow = true; S.add(floor);
add(S, BX(N + WT, 0.25, N + WT), M('#2a2530'), N / 2 - WT / 2, -0.125, N / 2 - WT / 2, { nocast: true });

const wm1 = M('#7d6f86', { roughness: 0.93, bumpMap: noise(8, 3), bumpScale: 0.25 });
const wm2 = M('#9a8aa3', { roughness: 0.93, bumpMap: noise(8, 3), bumpScale: 0.25 });
const WIN_Y0 = 1.0, WIN_Y1 = 2.3;
const WX = [[0.9, 3.0], [7.0, 9.1]], WZ = [[1.0, 3.0], [6.4, 8.4]];
// dinding belakang (z=0): potongan di sekeliling jendela
add(S, BX(N + WT, WIN_Y0, WT), wm1, (N - WT) / 2, WIN_Y0 / 2, -WT / 2);
add(S, BX(N + WT, WH - WIN_Y1, WT), wm1, (N - WT) / 2, (WH + WIN_Y1) / 2, -WT / 2);
[[-WT, 0.9], [3.0, 7.0], [9.1, N]].forEach(s => add(S, BX(s[1] - s[0], WIN_Y1 - WIN_Y0, WT), wm1, (s[0] + s[1]) / 2, (WIN_Y0 + WIN_Y1) / 2, -WT / 2));
// dinding kiri (x=0)
add(S, BX(WT, WIN_Y0, N), wm2, -WT / 2, WIN_Y0 / 2, N / 2);
add(S, BX(WT, WH - WIN_Y1, N), wm2, -WT / 2, (WH + WIN_Y1) / 2, N / 2);
[[0, 1.0], [3.0, 6.4], [8.4, N]].forEach(s => add(S, BX(WT, WIN_Y1 - WIN_Y0, s[1] - s[0]), wm2, -WT / 2, (WIN_Y0 + WIN_Y1) / 2, (s[0] + s[1]) / 2));
// plint
const skirt = M('#4d4155', { roughness: 0.5 });
add(S, BX(N, 0.1, 0.025), skirt, N / 2, 0.05, 0.0125); add(S, BX(0.025, 0.1, N), skirt, 0.0125, 0.05, N / 2);

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
WX.forEach(w => win('x', w[0], w[1])); WZ.forEach(w => win('z', w[0], w[1]));

// pemandangan di luar jendela
const skyT = paint(512, 256, (g, w, h) => {
  const gr = g.createLinearGradient(0, 0, 0, h); gr.addColorStop(0, '#5aa0e6'); gr.addColorStop(0.65, '#bfe0f7'); gr.addColorStop(1, '#e9f3f0');
  g.fillStyle = gr; g.fillRect(0, 0, w, h);
  g.fillStyle = 'rgba(255,255,255,.75)';
  for (let i = 0; i < 9; i++) { const x = rnd() * w, y = 20 + rnd() * 70; for (let k = 0; k < 5; k++) { g.beginPath(); g.ellipse(x + k * 14, y + rnd() * 6, 22 + rnd() * 14, 8 + rnd() * 5, 0, 0, 6.3); g.fill(); } }
  g.fillStyle = '#93a7b8'; for (let x = 0; x < w; x += 50 + rnd() * 60) { const bw = 46 + rnd() * 80, bh = 18 + rnd() * 40; g.fillRect(x, h * 0.74 - bh, bw, bh + h); }
  g.fillStyle = '#7d9577'; g.fillRect(0, h * 0.8, w, h);
});
const SKYM = new THREE.MeshBasicMaterial({ map: skyT, toneMapped: false });
const sk1 = new THREE.Mesh(new THREE.PlaneGeometry(40, 14), SKYM); sk1.position.set(5, 4, -7); S.add(sk1);
const sk2 = new THREE.Mesh(new THREE.PlaneGeometry(40, 14), SKYM); sk2.rotation.y = Math.PI / 2; sk2.position.set(-7, 4, 5); S.add(sk2);

// permadani
const rugT = paint(512, 256, (g, w, h) => {
  g.fillStyle = '#5a3d7a'; g.fillRect(0, 0, w, h); g.fillStyle = '#6d4b8f'; g.fillRect(22, 22, w - 44, h - 44);
  g.strokeStyle = '#d9c9a8'; g.lineWidth = 5; g.strokeRect(12, 12, w - 24, h - 24); g.lineWidth = 2; g.strokeRect(30, 30, w - 60, h - 60);
  g.save(); g.beginPath(); g.rect(32, 32, w - 64, h - 64); g.clip(); g.strokeStyle = 'rgba(217,201,168,.32)'; g.lineWidth = 2;
  for (let i = -h; i < w; i += 36) { g.beginPath(); g.moveTo(i, 0); g.lineTo(i + h, h); g.stroke(); g.beginPath(); g.moveTo(i + h, 0); g.lineTo(i, h); g.stroke(); }
  g.restore();
  for (let i = 0; i < 9000; i++) { g.fillStyle = 'rgba(' + (rnd() < .5 ? 255 : 0) + ',' + (rnd() < .5 ? 255 : 0) + ',' + (rnd() < .5 ? 255 : 0) + ',.05)'; g.fillRect(rnd() * w, rnd() * h, 2, 1); }
});
const rug = new THREE.Mesh(new THREE.PlaneGeometry(4, 2), M('#ffffff', { map: rugT, roughness: 1, bumpMap: noise(10, 5), bumpScale: 1.2 }));
rug.rotation.x = -Math.PI / 2; rug.position.set(5, 0.008, 4.3); rug.receiveShadow = true; S.add(rug);

// papan kartu (data hidup)
const boardT = paint(640, 360, (g, w, h) => {
  g.fillStyle = '#f4f4ef'; g.fillRect(0, 0, w, h);
  g.fillStyle = '#222'; g.font = 'bold 34px sans-serif'; g.fillText('PAPAN KARTU', 28, 56);
  g.fillStyle = '#c9c4b6'; g.fillRect(28, 70, w - 56, 3);
  const rows = [['Nunggu lu', D.counts.nunggu, '#c0661a'], ['Berjalan', D.counts.jalan, '#1f6fb2'], ['Selesai', D.counts.selesai, '#1e8449']];
  rows.forEach((r, i) => {
    const y = 130 + i * 78; g.fillStyle = r[2]; g.beginPath(); g.arc(46, y - 14, 12, 0, 6.3); g.fill();
    g.font = '32px sans-serif'; g.fillStyle = '#333'; g.fillText(r[0], 76, y); g.font = 'bold 54px sans-serif'; g.fillStyle = r[2]; g.textAlign = 'right'; g.fillText(String(r[1]), w - 40, y + 6); g.textAlign = 'left';
  });
});
add(S, RB(3.3, 1.3, 0.04, 0.012), STEEL, 5, 1.85, 0.02);
add(S, new THREE.PlaneGeometry(3.14, 1.14), M('#ffffff', { map: boardT, roughness: 0.35 }), 5, 1.85, 0.045, { nocast: true });
add(S, BX(3.3, 0.04, 0.09), STEEL, 5, 1.19, 0.06);
['#c0392b', '#2980b9', '#27ae60'].forEach((c, i) => add(S, new THREE.CylinderGeometry(0.012, 0.012, 0.12, 8), M(c, { roughness: 0.4 }), 4.3 + i * 0.12, 1.225, 0.07, { r: [0, 0, Math.PI / 2] }));

// jam dinding (hidup)
const clkC = cv2(256, 256), clkG = clkC.getContext('2d'), clkT = ctex(clkC);
function drawClock() {
  const g = clkG, d = new Date(); g.clearRect(0, 0, 256, 256);
  g.fillStyle = '#f7f5ef'; g.beginPath(); g.arc(128, 128, 124, 0, 6.3); g.fill();
  g.strokeStyle = '#2a2a2a'; for (let i = 0; i < 60; i++) { const a = i / 60 * 6.283, l = i % 5 ? 6 : 16; g.lineWidth = i % 5 ? 1.5 : 4; g.beginPath(); g.moveTo(128 + Math.sin(a) * (118 - l), 128 - Math.cos(a) * (118 - l)); g.lineTo(128 + Math.sin(a) * 118, 128 - Math.cos(a) * 118); g.stroke(); }
  const hand = (a, l, w, c) => { g.strokeStyle = c; g.lineWidth = w; g.lineCap = 'round'; g.beginPath(); g.moveTo(128, 128); g.lineTo(128 + Math.sin(a) * l, 128 - Math.cos(a) * l); g.stroke(); };
  const s = d.getSeconds(), m = d.getMinutes() + s / 60, h = d.getHours() % 12 + m / 60;
  hand(h / 12 * 6.283, 62, 8, '#222'); hand(m / 60 * 6.283, 92, 5, '#222'); hand(s / 60 * 6.283, 100, 2, '#c0392b');
  clkT.needsUpdate = true;
}
drawClock();
{
  const g = new THREE.Group(); g.rotation.y = Math.PI / 2; g.position.set(0.02, 2.5, 4.95); S.add(g);
  add(g, new THREE.CylinderGeometry(0.25, 0.25, 0.04, 40), BLACK, 0, 0, 0.0, { r: [Math.PI / 2, 0, 0] });
  add(g, new THREE.CircleGeometry(0.22, 40), new THREE.MeshBasicMaterial({ map: clkT, toneMapped: false }), 0, 0, 0.022, { nocast: true });
}
// poster
{
  const t = paint(200, 280, (g, w, h) => {
    const gr = g.createLinearGradient(0, 0, w, h); gr.addColorStop(0, '#1f3a5f'); gr.addColorStop(1, '#e07a3f'); g.fillStyle = gr; g.fillRect(0, 0, w, h);
    g.fillStyle = 'rgba(255,255,255,.88)'; g.fillRect(28, 150, 60, 90); g.fillRect(96, 110, 70, 130); g.fillStyle = '#ffd36b'; g.beginPath(); g.arc(140, 70, 26, 0, 6.3); g.fill();
    g.fillStyle = '#fff'; g.font = 'bold 18px sans-serif'; g.fillText('GUDANG', 28, 40); g.font = '12px sans-serif'; g.fillText('Safety First', 28, 58);
  });
  const g = new THREE.Group(); g.rotation.y = Math.PI / 2; g.position.set(0.02, 1.65, 3.6); S.add(g);
  add(g, BX(0.58, 0.78, 0.03), M('#e9e4d8', { roughness: 0.5 }), 0, 0, 0);
  add(g, new THREE.PlaneGeometry(0.5, 0.7), M('#ffffff', { map: t, roughness: 0.6 }), 0, 0, 0.017, { nocast: true });
}

// =====================================================================
// Perabot
// =====================================================================
const DESK = { hrd: [1.2, 2.2], manager_ops: [6.4, 1.6], op_control: [3.6, 6.0] };
const SEAT = { hrd: [2.2, 1.75], manager_ops: [7.4, 1.15], op_control: [4.6, 5.55] };
const SUP_SEAT = [4.95, 2.35];

const screens = [];
function mkScreen(ch, kind) {
  const c = cv2(256, 144), tex = ctex(c);
  screens.push({ g: c.getContext('2d'), tex, ch, kind, last: -1 });
  return new THREE.MeshBasicMaterial({ map: tex, toneMapped: false });
}
function drawScreen(sc, on, t) {
  const g = sc.g, w = 256, h = 144;
  if (!on) { g.fillStyle = '#0b1118'; g.fillRect(0, 0, w, h); g.fillStyle = 'rgba(255,255,255,.05)'; g.fillRect(0, 0, w, h / 2); sc.tex.needsUpdate = true; return; }
  const gr = g.createLinearGradient(0, 0, w, h); gr.addColorStop(0, '#10243f'); gr.addColorStop(1, '#17375e'); g.fillStyle = gr; g.fillRect(0, 0, w, h);
  g.fillStyle = '#0a121d'; g.fillRect(0, 0, w, 14);
  ['#ff5f56', '#ffbd2e', '#27c93f'].forEach((c, i) => { g.fillStyle = c; g.beginPath(); g.arc(9 + i * 12, 7, 3.4, 0, 6.3); g.fill(); });
  if (sc.kind === 'dash') {
    const v = [D.counts.nunggu, D.counts.jalan, D.counts.selesai], cl = ['#e67e22', '#3498db', '#2ecc71'], mx = Math.max(1, ...v);
    v.forEach((x, i) => { g.fillStyle = cl[i]; g.fillRect(24 + i * 74, 118 - x / mx * 80, 52, x / mx * 80); g.fillStyle = '#fff'; g.font = 'bold 14px sans-serif'; g.fillText(String(x), 40 + i * 74, 112 - x / mx * 80); });
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
function monitor(par, x, y, z, mat, ry) {
  const m = new THREE.Group(); m.position.set(x, y, z); m.rotation.y = ry; par.add(m);
  add(m, RB(0.62, 0.37, 0.025, 0.006), BLACK, 0, 0.26, 0);
  add(m, new THREE.PlaneGeometry(0.58, 0.33), mat, 0, 0.26, 0.0135, { nocast: true });
  add(m, BX(0.04, 0.2, 0.03), STEEL, 0, 0.1, -0.02); add(m, RB(0.24, 0.012, 0.17, 0.004), STEEL, 0, 0.006, -0.02);
}
const KEYT = paint(256, 96, (g, w, h) => {
  g.fillStyle = '#23262d'; g.fillRect(0, 0, w, h); g.fillStyle = '#3a3e48';
  for (let r = 0; r < 5; r++) for (let c = 0; c < 15; c++) g.fillRect(6 + c * 16.2, 6 + r * 16.5, 13, 13);
});
function desk(x, z, w, d, tint, kind, who) {
  const g = new THREE.Group(); g.position.set(x, 0, z); S.add(g);
  const top = P(tint, { map: WOOD, roughness: 0.42, clearcoat: 0.3, clearcoatRoughness: 0.4 });
  add(g, RB(w, 0.04, d, 0.012), top, w / 2, 0.74, d / 2);
  add(g, BX(0.03, 0.72, d - 0.1), STEEL, 0.05, 0.36, d / 2);
  add(g, BX(0.03, 0.72, d - 0.1), STEEL, w - 0.05, 0.36, d / 2);
  add(g, BX(w - 0.12, 0.4, 0.02), M('#cfcac0', { roughness: 0.6 }), w / 2, 0.5, d - 0.06);
  add(g, RB(0.46, 0.5, d - 0.25, 0.01), M('#d8d4cc', { roughness: 0.55 }), w - 0.34, 0.45, d / 2 + 0.02);
  for (let i = 0; i < 3; i++) {
    add(g, RB(0.44, 0.15, 0.015, 0.006), M('#e6e2da', { roughness: 0.45 }), w - 0.34, 0.6 - i * 0.16, 0.16);
    add(g, BX(0.12, 0.012, 0.02), STEEL, w - 0.34, 0.64 - i * 0.16, 0.18);
  }
  add(g, RB(0.42, 0.016, 0.14, 0.006), new THREE.MeshStandardMaterial({ map: KEYT, roughness: 0.6 }), w / 2, 0.768, 0.14);
  add(g, RB(0.06, 0.026, 0.1, 0.012), BLACK, w / 2 + 0.34, 0.772, 0.15);
  monitor(g, w / 2, 0.76, 0.52, mkScreen(who, kind), Math.PI);
  add(g, new THREE.CylinderGeometry(0.04, 0.035, 0.09, 16), M('#f2f0ea', { roughness: 0.3 }), w / 2 - 0.62, 0.805, 0.3);
  add(g, RB(0.2, 0.02, 0.28, 0.006), M('#c0392b', { roughness: 0.6 }), 0.34, 0.76, 0.36, { r: [0, 0.3, 0] });
  ao(x + w / 2, z + d / 2, w + 0.9, d + 0.9, 0.5);
}
function chair(x, z) {
  const g = new THREE.Group(); g.position.set(x, 0, z); S.add(g);
  const fab = cloth('#2c3340', 0.95), pl = M('#1a1c20', { roughness: 0.5 });
  add(g, RB(0.5, 0.09, 0.48, 0.04), fab, 0, 0.415, 0);
  add(g, RB(0.46, 0.5, 0.07, 0.03), fab, 0, 0.75, -0.23, { r: [-0.1, 0, 0] });
  add(g, new THREE.CylinderGeometry(0.025, 0.025, 0.3, 12), STEEL, 0, 0.24, 0);
  for (let i = 0; i < 5; i++) {
    const l = new THREE.Group(); l.rotation.y = i / 5 * 6.283; g.add(l);
    add(l, BX(0.3, 0.03, 0.045), pl, 0.15, 0.075, 0); add(l, new THREE.SphereGeometry(0.03, 10, 8), pl, 0.3, 0.03, 0);
  }
  [-1, 1].forEach(s => { add(g, RB(0.05, 0.03, 0.26, 0.01), pl, s * 0.27, 0.62, -0.02); add(g, BX(0.03, 0.15, 0.03), pl, s * 0.27, 0.54, 0.05); });
  ao(x, z, 0.9, 0.9, 0.45);
}
desk(DESK.hrd[0], DESK.hrd[1], 2, 1.1, '#d0a070', 'code', null);
desk(DESK.manager_ops[0], DESK.manager_ops[1], 2, 1.1, '#d0a070', 'code', null);
desk(DESK.op_control[0], DESK.op_control[1], 2, 1.1, '#d0a070', 'code', null);
Object.keys(SEAT).forEach(k => chair(SEAT[k][0], SEAT[k][1] - 0.07));
// meja supervisor
desk(4.0, 2.8, 1.9, 0.9, '#8a6b5a', 'dash', null);
chair(SUP_SEAT[0], SUP_SEAT[1] - 0.07);

// sofa
{
  const g = new THREE.Group(); g.position.set(7.0, 0, 3.9); S.add(g);
  const f = cloth('#8a3b4a', 0.95), f2 = cloth('#7a2f3e', 0.95);
  add(g, RB(2.4, 0.36, 0.95, 0.06), f2, 1.2, 0.3, 0.5);
  add(g, RB(2.4, 0.5, 0.26, 0.07), f2, 1.2, 0.7, 0.14);
  [0.11, 2.29].forEach(x => add(g, RB(0.22, 0.28, 0.95, 0.06), f2, x, 0.58, 0.5));
  [0.62, 1.78].forEach(x => { add(g, RB(1.0, 0.14, 0.7, 0.05), f, x, 0.55, 0.58); add(g, RB(0.98, 0.42, 0.16, 0.06), f, x, 0.8, 0.3, { r: [-0.2, 0, 0] }); });
  add(g, RB(0.38, 0.38, 0.12, 0.05), cloth('#d9b36b', 0.95), 0.4, 0.78, 0.5, { r: [-0.3, 0.4, 0.2] });
  [[0.1, 0.1], [2.3, 0.1], [0.1, 0.88], [2.3, 0.88]].forEach(p => add(g, new THREE.CylinderGeometry(0.03, 0.025, 0.1, 8), BLACK, p[0], 0.05, p[1]));
  ao(8.2, 4.4, 3.2, 1.8, 0.55);
}
// pantry
{
  const g = new THREE.Group(); g.position.set(7.2, 0, 8.4); S.add(g);
  add(g, RB(2.4, 0.86, 0.9, 0.01), M('#3b3f46', { roughness: 0.55 }), 1.2, 0.43, 0.45);
  [0, 1, 2, 3].forEach(i => { [0.0, 0.9].forEach(z => add(g, RB(0.56, 0.74, 0.012, 0.005), M('#4b505a', { roughness: 0.45 }), 0.32 + i * 0.58, 0.43, z + (z ? 0.006 : -0.006))); });
  add(g, RB(2.46, 0.04, 0.96, 0.01), P('#e8e6df', { roughness: 0.25, clearcoat: 0.5 }), 1.2, 0.88, 0.45);
  add(g, RB(0.34, 0.36, 0.3, 0.02), M('#1c1e23', { roughness: 0.4 }), 0.5, 1.08, 0.5); add(g, BX(0.3, 0.02, 0.26), STEEL, 0.5, 0.9, 0.5);
  add(g, new THREE.CylinderGeometry(0.035, 0.03, 0.08, 12), M('#f2f0ea', { roughness: 0.3 }), 0.5, 0.94, 0.55);
  add(g, new THREE.CylinderGeometry(0.1, 0.12, 0.2, 16), STEEL, 1.5, 0.99, 0.5);
  [1.9, 2.0].forEach((x, i) => add(g, new THREE.CylinderGeometry(0.035, 0.03, 0.08, 12), M(i ? '#2980b9' : '#f2f0ea', { roughness: 0.3 }), x, 0.94, 0.6));
  add(g, RB(0.38, 1.05, 0.38, 0.03), M('#e5e8ec', { roughness: 0.4 }), 2.7, 0.53, 0.3);
  add(g, new THREE.CylinderGeometry(0.13, 0.13, 0.32, 20), P('#7bbcf0', { roughness: 0.05, transparent: true, opacity: 0.6 }), 2.7, 1.2, 0.3);
  ao(8.4, 8.85, 3.4, 1.8, 0.5);
}
// rak buku + buku (InstancedMesh)
{
  const g = new THREE.Group(); g.position.set(0.08, 0, 4.2); S.add(g);
  const wd = P('#8a6a4a', { map: WOOD, roughness: 0.55 });
  add(g, BX(0.72, 2.0, 0.04), wd, 0.38, 1.0, 0.02); add(g, BX(0.72, 2.0, 0.04), wd, 0.38, 1.0, 1.98);
  add(g, BX(0.02, 2.0, 2.0), wd, 0.02, 1.0, 1.0);
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
  im.count = n; im.castShadow = true; im.receiveShadow = true; g.add(im);
  ao(0.55, 5.2, 1.3, 2.7, 0.5);
}
// tanaman (daun = InstancedMesh)
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
  im.castShadow = true; im.receiveShadow = true; g.add(im);
  ao(x, z, 0.9 * (sc || 1), 0.9 * (sc || 1), 0.5);
}
plant(1.0, 7.4, 1); plant(9.0, 0.7, 1); plant(0.6, 0.9, 0.9);
// lampu lantai + tempat sampah
{
  const g = new THREE.Group(); g.position.set(9.3, 0, 3.5); S.add(g);
  add(g, new THREE.CylinderGeometry(0.16, 0.18, 0.03, 24), BLACK, 0, 0.015, 0); add(g, new THREE.CylinderGeometry(0.012, 0.012, 1.5, 8), STEEL, 0, 0.77, 0);
  add(g, new THREE.CylinderGeometry(0.17, 0.24, 0.3, 24, 1, true), new THREE.MeshStandardMaterial({ color: '#f5e6c8', emissive: '#ffcf8a', emissiveIntensity: 0.9, side: THREE.DoubleSide, roughness: 0.9 }), 0, 1.6, 0, { nocast: true });
  const l = new THREE.PointLight(0xffd9a0, 5, 6, 2); l.position.set(9.3, 1.6, 3.5); scene.add(l);
  const b = new THREE.Group(); b.position.set(6.4, 0, 0.5); S.add(b); add(b, new THREE.CylinderGeometry(0.13, 0.1, 0.3, 16, 1, true), PLASTIC, 0, 0.15, 0);
}

// =====================================================================
// Karakter manusia (humanoid prosedural, PBR)
// =====================================================================
const LOOK = {
  hrd: { female: true, skin: '#e8b894', hair: '#2a1a14', shirt: '#e0568a', pants: '#2b2f3f', sleeve: 'short' },
  manager_ops: { female: false, skin: '#d9a47c', hair: '#161616', shirt: '#2f6fd1', pants: '#2b3350', tie: '#b3261e', glasses: true, sleeve: 'long' },
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
    mk(spine, tg, M(look.tie, { roughness: 0.4, sheen: 1 }), 0, 0.33, 0.094); mk(spine, sph(0.02, 1, 0.9, 0.7), M(look.tie, { roughness: 0.4 }), 0, 0.45, 0.092);
  }
  mk(spine, new THREE.CylinderGeometry(0.05, 0.056, 0.12, 16), skin, 0, 0.5, 0);
  { const col = new THREE.TorusGeometry(0.058, 0.013, 8, 20); col.rotateX(Math.PI / 2); mk(spine, col, shirt, 0, 0.465, 0); }

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
  const hc = new THREE.SphereGeometry(1, 24, 14, 0, Math.PI * 2, 0, Math.PI * 0.6); hc.scale(0.098, 0.12, 0.108);
  mk(head, hc, hair, 0, 0.108, -0.006).rotation.x = -0.3;
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
    const fg = new THREE.CapsuleGeometry(0.047, 0.1, 6, 12); fg.rotateX(Math.PI / 2); fg.scale(1, 0.75, 1); mk(an, fg, shoe, 0, -0.045, 0.05);
    legs[s] = { hp, kn, an };
  });
  scene.add(root);
  return { root, hips, spine, chest, head, eyes, arms, legs };
}

// =====================================================================
// Pergerakan agent (rute menghindari perabot)
// =====================================================================
const WAIT = [[3.0, 4.6], [4.2, 4.9], [5.4, 5.2]];
const IDLE = [[7.6, 7.5], [8.4, 5.7], [1.8, 6.2], [5.8, 8.6], [1.8, 4.6], [6.2, 7.0]];
const OB = [[1.2, 2.2, 3.2, 3.3], [6.4, 1.6, 8.4, 2.7], [3.6, 6.0, 5.6, 7.1], [4.0, 2.8, 5.9, 3.7], [7.0, 3.9, 9.4, 4.9], [7.2, 8.4, 9.6, 9.3], [0.1, 4.2, 0.9, 6.2]];
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
  if (w[0] < 0.3 || w[0] > N - 0.3 || w[1] < 0.3 || w[1] > N - 0.3) return;
  if (OB.some(o => w[0] > o[0] - 0.28 && w[0] < o[2] + 0.28 && w[1] > o[1] - 0.28 && w[1] < o[3] + 0.28)) return;
  CORN.push(w);
}));
function route(ax, ay, bx, by) {   // visibility graph + Dijkstra
  if (clear(ax, ay, bx, by)) return [[bx, by]];
  const nd = [[ax, ay]].concat(CORN, [[bx, by]]), n = nd.length, dist = new Array(n).fill(1e9), prev = new Array(n).fill(-1), done = new Array(n).fill(false);
  dist[0] = 0;
  for (let it = 0; it < n; it++) {
    let u = -1; for (let i = 0; i < n; i++) if (!done[i] && (u < 0 || dist[i] < dist[u])) u = i;
    if (u < 0 || dist[u] >= 1e9) break; done[u] = true; if (u === n - 1) break;
    for (let v = 0; v < n; v++) {
      if (done[v]) continue;
      const l = Math.hypot(nd[u][0] - nd[v][0], nd[u][1] - nd[v][1]);
      if (dist[u] + l < dist[v] && clear(nd[u][0], nd[u][1], nd[v][0], nd[v][1])) { dist[v] = dist[u] + l; prev[v] = u; }
    }
  }
  if (prev[n - 1] < 0) return [[bx, by]];
  const out = []; for (let i = n - 1; i > 0; i = prev[i]) out.unshift(nd[i]);
  return out;
}
function working(c) { return c.status === 'jalan' || c.status === 'antri'; }
function waiting(c) { return c.status === 'nunggu_lu' || c.status === 'error'; }
function seatOf(c) { return SEAT[c.kunci] || IDLE[c.idx % IDLE.length]; }
function goto(c, x, y, seat) { c.tx = x; c.ty = y; c.atSeat = !!seat; c.path = route(c.x, c.y, x, y); }
function pickIdle(c) {
  if (rnd() < 0.3 && SEAT[c.kunci]) { const s = SEAT[c.kunci]; goto(c, s[0], s[1], true); c.dwell = 4 + rnd() * 4; }
  else { const p = IDLE[Math.floor(rnd() * IDLE.length)]; goto(c, p[0], p[1], false); c.dwell = 4 + rnd() * 5; }
}
function pickTarget(c) {
  if (working(c) && SEAT[c.kunci]) { const s = SEAT[c.kunci]; goto(c, s[0], s[1], true); }
  else if (waiting(c)) { const w = WAIT[c.idx % WAIT.length]; goto(c, w[0], w[1], false); }
  else pickIdle(c);
}
let saved = {};
try { saved = JSON.parse(sessionStorage.getItem('kantor_pos3d') || '{}'); } catch (e) {}

function newState(sit) { return { sit: sit ? 1 : 0, walk: 0, typ: 0, wave: 0, err: 0, ph: 0 }; }
const chars = D.agents.map((a, i) => {
  const look = LOOK[a.kunci] || FALL[i % FALL.length];
  const c = Object.assign({}, a, { idx: i, walking: false, sitting: false, atSeat: false, dwell: 0, seed: i * 2.1, h: 0, hT: 0, path: [], rig: makePerson(look), q: newState(false) });
  const s = seatOf(c);
  if (saved[a.kunci]) { c.x = saved[a.kunci][0]; c.y = saved[a.kunci][1]; }
  else if (working(c)) { c.x = s[0]; c.y = s[1]; c.q.sit = 1; c.sitting = true; }
  else if (waiting(c)) { c.x = WAIT[i % WAIT.length][0]; c.y = WAIT[i % WAIT.length][1]; c.hT = c.h = Math.PI; }
  else { const p = IDLE[(i * 2 + 1) % IDLE.length]; c.x = p[0]; c.y = p[1]; }
  pickTarget(c);
  c.blob = ao(c.x, c.y, 0.8, 0.8, 0.55); c.blob.removeFromParent(); scene.add(c.blob);
  return c;
});
// hubungkan monitor ke pemiliknya
{ const keys = ['hrd', 'manager_ops', 'op_control']; keys.forEach((k, i) => { const sc = screens[i]; if (sc) sc.ch = chars.filter(c => c.kunci === k)[0] || null; }); }
const kamu = { kunci: 'kamu', nama: 'Yogi', peran: 'Supervisor', status: 'idle', x: SUP_SEAT[0], y: SUP_SEAT[1], h: 0, hT: 0, sitting: true, walking: false, seed: 1.3, rig: makePerson(LOOK.kamu), q: newState(true) };
const sk = screens[3]; if (sk) sk.ch = null;
const people = chars.concat([kamu]);

function update(c, dt) {
  const wp = c.path.length ? c.path[0] : [c.tx, c.ty];
  const dx = wp[0] - c.x, dy = wp[1] - c.y, d = Math.hypot(dx, dy);
  if (d > 0.05) {
    const s = Math.min(d, 1.5 * dt); c.x += dx / d * s; c.y += dy / d * s; c.walking = true; c.sitting = false; c.hT = Math.atan2(dx, dy);
  } else if (c.path.length) { c.path.shift(); }
  else {
    c.walking = false; c.x = c.tx; c.y = c.ty; c.sitting = c.atSeat;
    if (c.sitting) c.hT = 0; else if (waiting(c)) c.hT = Math.PI;
    if (c.status === 'idle') { c.dwell -= dt; if (c.dwell <= 0) pickIdle(c); }
  }
}
setInterval(() => { try { const o = {}; chars.forEach(c => { o[c.kunci] = [c.x, c.y]; }); sessionStorage.setItem('kantor_pos3d', JSON.stringify(o)); } catch (e) {} }, 1000);

function pose(c, dt, t) {
  const r = c.rig, q = c.q, k = Math.min(1, dt * 4);
  q.sit += ((c.sitting ? 1 : 0) - q.sit) * k;
  q.walk += ((c.walking ? 1 : 0) - q.walk) * Math.min(1, dt * 6);
  const typT = c.sitting && (working(c) || (c.kunci === 'kamu' && Math.sin(t * 0.35 + 1) > -0.2)) ? 1 : 0;
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
  const el = document.createElement('div'); el.className = 'lb'; el.innerHTML = '<div class="bb"></div><div class="tg"></div>'; $lab.appendChild(el);
  c.el = el; c.bb = el.firstChild; c.tg = el.lastChild;
  c.tg.textContent = c.kunci === 'kamu' ? 'Yogi (Supervisor)' : c.nama + ' · ' + c.peran;
  const b = c.kunci === 'kamu' ? null : bubbleFor(c);
  if (b) { c.bb.textContent = b.text.length > 150 ? b.text.slice(0, 148) + '…' : b.text; c.bb.style.borderColor = b.color; } else c.bb.style.display = 'none';
  c.tg.addEventListener('click', () => focus(c));
});
const _v = new THREE.Vector3();
function labels(w, h) {
  people.forEach(c => {
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
  if (qm === 'auto') { setPR(STEPS[idx]); setShadow(idx > 3 ? 1024 : 2048); }
  else if (qm === 'high') { setPR(MAXPR); setShadow(2048); }
  else if (qm === 'mid') { setPR(Math.min(MAXPR, 1.25)); setShadow(1024); }
  else { setPR(1); setShadow(512); }
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
  chars.forEach(c => update(c, dt)); people.forEach(c => pose(c, dt, t));
  if (tw) { tw.k = Math.min(1, tw.k + dt / 0.9); const e = tw.k * tw.k * (3 - 2 * tw.k); camera.position.lerpVectors(tw.p0, tw.p1, e); controls.target.lerpVectors(tw.t0, tw.t1, e); if (tw.k >= 1) tw = null; }
  controls.update(); controls.target.clamp(PAN_MIN, PAN_MAX);
  if (now - scrT > 200) {
    scrT = now;
    screens.forEach(sc => { const on = sc.kind === 'dash' ? 1 : (sc.ch && sc.ch.sitting && working(sc.ch) ? 1 : 0); if (on || sc.last !== on) drawScreen(sc, on, t); sc.last = on; });
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
