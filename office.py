"""Simulasi office isometrik (canvas HTML) untuk Kantor AI Gudang.

Keadaan agent diambil dari kartu di database:
- jalan/antri  -> agent duduk di meja dan mengetik
- nunggu_lu    -> agent berjalan ke meja supervisor (kamu) dan menunggu jawaban
- error        -> agent menunggu di meja supervisor dengan tanda peringatan
- tidak ada    -> agent jalan-jalan (pantry, lounge, kembali ke meja)
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


def tampilkan(height: int = 490):
    components.html(html_kantor(), height=height)


HTML = r"""<!doctype html><html><head><meta charset="utf-8">
<style>
html,body{margin:0;background:#0e1117;overflow:hidden}
canvas{display:block;width:100%;height:auto;border-radius:12px}
</style></head><body>
<canvas id="c" width="720" height="470"></canvas>
<script>
const D = __DATA__;
const cv = document.getElementById('c'), ctx = cv.getContext('2d');
const W = 720, H = 470, TW = 72, TH = 36, OX = W / 2, OY = 110, N = 10, WH = 92;

function P(x, y, z) { z = z || 0; return [OX + (x - y) * TW / 2, OY + (x + y) * TH / 2 - z]; }
function poly(pts, fill, stroke) {
  ctx.beginPath();
  pts.forEach(function (p, i) { if (i) ctx.lineTo(p[0], p[1]); else ctx.moveTo(p[0], p[1]); });
  ctx.closePath();
  ctx.fillStyle = fill; ctx.fill();
  if (stroke) { ctx.strokeStyle = stroke; ctx.lineWidth = 1; ctx.stroke(); }
}
function shade(hex, f) {
  const n = parseInt(hex.slice(1), 16);
  const r = Math.min(255, Math.round(((n >> 16) & 255) * f));
  const g = Math.min(255, Math.round(((n >> 8) & 255) * f));
  const b = Math.min(255, Math.round((n & 255) * f));
  return 'rgb(' + r + ',' + g + ',' + b + ')';
}
function box(x, y, w, d, h, c, z0) {
  z0 = z0 || 0;
  poly([P(x, y, z0 + h), P(x + w, y, z0 + h), P(x + w, y + d, z0 + h), P(x, y + d, z0 + h)], shade(c, 1.12));
  poly([P(x, y + d, z0), P(x + w, y + d, z0), P(x + w, y + d, z0 + h), P(x, y + d, z0 + h)], shade(c, 0.86));
  poly([P(x + w, y, z0), P(x + w, y + d, z0), P(x + w, y + d, z0 + h), P(x + w, y, z0 + h)], shade(c, 0.66));
}
function rect(x, y, w, h, c) { ctx.fillStyle = c; ctx.fillRect(Math.round(x), Math.round(y), w, h); }
function rrect(x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y); ctx.lineTo(x + w - r, y); ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r); ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h); ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r); ctx.quadraticCurveTo(x, y, x + r, y); ctx.closePath();
}

// ---------- Posisi ----------
const DESK = { hrd: [1.2, 2.2], manager_ops: [6.4, 1.6], op_control: [3.6, 6.0] };
const SEAT = { hrd: [2.2, 1.75], manager_ops: [7.4, 1.15], op_control: [4.6, 5.55] };
const WAIT = [[3.0, 4.6], [4.2, 4.9], [5.4, 5.2]];
const IDLE = [[7.6, 7.5], [8.4, 5.7], [1.8, 6.2], [5.8, 8.6], [1.8, 4.6], [6.2, 7.0]];
const LOOK = {
  hrd: { shirt: '#e0568a', hair: '#2a1a14', female: true },
  manager_ops: { shirt: '#2f6fd1', hair: '#1c1c1c', female: false },
  op_control: { shirt: '#2fa66b', hair: '#3a2a1a', female: false }
};

// ---------- Karakter ----------
let saved = {};
try { saved = JSON.parse(sessionStorage.getItem('kantor_pos') || '{}'); } catch (e) {}

function working(c) { return c.status === 'jalan' || c.status === 'antri'; }
function waiting(c) { return c.status === 'nunggu_lu' || c.status === 'error'; }

const chars = D.agents.map(function (a, i) {
  const c = Object.assign({}, a, { idx: i, walking: false, sitting: false, atSeat: false, dwell: 0, seed: i * 2.1 });
  const s = SEAT[a.kunci];
  if (saved[a.kunci]) { c.x = saved[a.kunci][0]; c.y = saved[a.kunci][1]; }
  else if (working(c)) { c.x = s[0]; c.y = s[1]; }
  else if (waiting(c)) { c.x = WAIT[i][0]; c.y = WAIT[i][1]; }
  else { const p = IDLE[(i * 2 + 1) % IDLE.length]; c.x = p[0]; c.y = p[1]; }
  pickTarget(c);
  return c;
});

function pickIdle(c) {
  if (Math.random() < 0.3) {
    const s = SEAT[c.kunci]; c.tx = s[0]; c.ty = s[1]; c.atSeat = true; c.dwell = 4 + Math.random() * 4;
  } else {
    const p = IDLE[Math.floor(Math.random() * IDLE.length)];
    c.tx = p[0]; c.ty = p[1]; c.atSeat = false; c.dwell = 4 + Math.random() * 5;
  }
}
function pickTarget(c) {
  if (working(c)) { const s = SEAT[c.kunci]; c.tx = s[0]; c.ty = s[1]; c.atSeat = true; }
  else if (waiting(c)) { const w = WAIT[c.idx]; c.tx = w[0]; c.ty = w[1]; c.atSeat = false; }
  else pickIdle(c);
}
function update(c, dt) {
  const dx = c.tx - c.x, dy = c.ty - c.y, dist = Math.hypot(dx, dy);
  if (dist > 0.06) {
    const s = Math.min(dist, 2.0 * dt);
    c.x += dx / dist * s; c.y += dy / dist * s;
    c.walking = true; c.sitting = false;
  } else {
    c.walking = false; c.x = c.tx; c.y = c.ty; c.sitting = c.atSeat;
    if (c.status === 'idle') { c.dwell -= dt; if (c.dwell <= 0) pickIdle(c); }
  }
}
setInterval(function () {
  try {
    const o = {}; chars.forEach(function (c) { o[c.kunci] = [c.x, c.y]; });
    sessionStorage.setItem('kantor_pos', JSON.stringify(o));
  } catch (e) {}
}, 1000);

function drawChar(c, t, look, isKamu) {
  const sit = c.sitting;
  const p = P(c.x, c.y, sit ? 8 : 0);
  const px = p[0]; let py = p[1];
  ctx.fillStyle = 'rgba(0,0,0,.25)';
  ctx.beginPath(); ctx.ellipse(px, py, 9, 4, 0, 0, 6.3); ctx.fill();
  const ph = Math.sin(t * 10 + c.seed);
  if (c.walking) py -= Math.abs(ph) * 2;
  const pants = '#2b3350', skin = '#f1c8a0';
  if (sit) rect(px - 4, py - 7, 8, 4, pants);
  else {
    const w = c.walking ? ph * 2 : 0;
    rect(px - 4, py - 9, 3, 9 + w, pants); rect(px + 1, py - 9, 3, 9 - w, pants);
    rect(px - 4, py - 1 + w, 3, 2, '#1b1b1b'); rect(px + 1, py - 1 - w, 3, 2, '#1b1b1b');
  }
  rect(px - 5, py - 20, 10, 12, look.shirt);
  if (c.kunci === 'manager_ops') { rect(px - 1, py - 20, 2, 7, '#c0392b'); rect(px - 3, py - 20, 6, 1, '#fff'); }
  if (c.kunci === 'op_control') rect(px - 5, py - 15, 10, 2, '#f1c40f');
  if (c.kunci === 'hrd') rect(px - 1, py - 17, 3, 4, '#fff');
  const typing = sit && working(c);
  const a1 = typing ? Math.sin(t * 14) * 1.5 : 0, a2 = typing ? Math.cos(t * 14) * 1.5 : 0;
  if (typing || (sit && !isKamu)) {
    rect(px - 7, py - 18 + a1, 2, 8, look.shirt); rect(px + 5, py - 18 + a2, 2, 8, look.shirt);
    rect(px - 7, py - 10 + a1, 2, 2, skin); rect(px + 5, py - 10 + a2, 2, 2, skin);
  } else {
    const sw = c.walking ? ph * 2 : 0;
    rect(px - 7, py - 19 + sw, 2, 9, look.shirt); rect(px + 5, py - 19 - sw, 2, 9, look.shirt);
    rect(px - 7, py - 10 + sw, 2, 2, skin); rect(px + 5, py - 10 - sw, 2, 2, skin);
  }
  rect(px - 4, py - 28, 8, 8, skin);
  rect(px - 2, py - 25, 1, 2, '#222'); rect(px + 1, py - 25, 1, 2, '#222');
  if (look.female) {
    rect(px - 5, py - 30, 10, 4, look.hair);
    rect(px - 5, py - 28, 2, 11, look.hair); rect(px + 3, py - 28, 2, 11, look.hair);
  } else {
    rect(px - 4, py - 30, 8, 3, look.hair);
    if (c.kunci === 'op_control') rect(px - 5, py - 31, 10, 3, '#f1c40f');
  }
}

// ---------- Teks / gelembung ----------
function wrap(text, maxc, maxLines) {
  const words = String(text).split(/\s+/), lines = []; let cur = '';
  for (let i = 0; i < words.length; i++) {
    const w = words[i];
    if ((cur + ' ' + w).trim().length > maxc) { if (cur) lines.push(cur); cur = w; }
    else cur = (cur + ' ' + w).trim();
  }
  if (cur) lines.push(cur);
  if (lines.length > maxLines) { lines.length = maxLines; lines[maxLines - 1] = lines[maxLines - 1].replace(/.{0,2}$/, '') + '…'; }
  return lines;
}
function tag(text, cx, y, bg) {
  ctx.font = 'bold 10px sans-serif';
  const w = ctx.measureText(text).width + 10;
  rrect(cx - w / 2, y - 11, w, 14, 4); ctx.fillStyle = bg || 'rgba(15,17,23,.85)'; ctx.fill();
  ctx.fillStyle = '#fff'; ctx.textAlign = 'center'; ctx.fillText(text, cx, y); ctx.textAlign = 'left';
}
function bubble(text, cx, bottom, color) {
  ctx.font = '10px sans-serif';
  const lines = wrap(text, 30, 4);
  let w = 0; lines.forEach(function (l) { w = Math.max(w, ctx.measureText(l).width); });
  w += 12; const h = lines.length * 12 + 8;
  let x = Math.min(Math.max(cx - w / 2, 4), W - w - 4); const y = bottom - h;
  rrect(x, y, w, h, 6); ctx.fillStyle = '#fff'; ctx.fill(); ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.stroke();
  ctx.beginPath(); ctx.moveTo(cx - 4, bottom); ctx.lineTo(cx + 4, bottom); ctx.lineTo(cx, bottom + 5); ctx.closePath();
  ctx.fillStyle = '#fff'; ctx.fill();
  ctx.fillStyle = '#1b1f27';
  lines.forEach(function (l, i) { ctx.fillText(l, x + 6, y + 13 + i * 12); });
}
function bubbleFor(c) {
  if (c.status === 'nunggu_lu') return { text: '🙋 ' + (c.pesan || c.judul), color: '#e67e22' };
  if (c.status === 'error') return { text: '⚠️ ' + (c.pesan || 'Gagal memanggil AI. Cek API key / kuota Groq.'), color: '#e74c3c' };
  if (working(c)) return { text: '⚙️ ' + c.kode + ': ' + c.judul, color: '#3498db' };
  return null;
}

// ---------- Ruangan ----------
function drawRoom() {
  for (let i = 0; i < N; i++) for (let j = 0; j < N; j++)
    poly([P(i, j), P(i + 1, j), P(i + 1, j + 1), P(i, j + 1)], ((i + j) % 2) ? '#c9a77c' : '#bf9b6f');
  poly([P(3.0, 3.3), P(7.0, 3.3), P(7.0, 5.3), P(3.0, 5.3)], '#5a3d7a');
  poly([P(3.2, 3.5), P(6.8, 3.5), P(6.8, 5.1), P(3.2, 5.1)], '#6d4b8f');
  poly([P(0, 0, 0), P(N, 0, 0), P(N, 0, WH), P(0, 0, WH)], '#6b5b73');
  poly([P(0, 0, 0), P(0, N, 0), P(0, N, WH), P(0, 0, WH)], '#85708d');
  poly([P(0, 0, 0), P(N, 0, 0), P(N, 0, 8), P(0, 0, 8)], '#4d4155');
  poly([P(0, 0, 0), P(0, N, 0), P(0, N, 8), P(0, 0, 8)], '#5e4a66');
  [[0.9, 3.0], [7.0, 9.1]].forEach(function (r) {
    poly([P(r[0], 0, 36), P(r[1] - 0.0, 0, 36), P(r[1], 0, 80), P(r[0], 0, 80)], '#a9dcff', '#e8e2d6');
  });
  [[1.0, 3.0], [6.4, 8.4]].forEach(function (r) {
    poly([P(0, r[0], 36), P(0, r[1], 36), P(0, r[1], 80), P(0, r[0], 80)], '#a9dcff', '#e8e2d6');
  });
  // papan kartu di dinding
  const b0 = P(3.6, 0, 82);
  poly([P(3.4, 0, 30), P(6.6, 0, 30), P(6.6, 0, 86), P(3.4, 0, 86)], '#f4f4ef', '#8a7f6a');
  ctx.save(); ctx.transform(1, TH / TW, 0, 1, P(3.4, 0, 86)[0], P(3.4, 0, 86)[1]);
  ctx.fillStyle = '#222'; ctx.font = 'bold 9px sans-serif'; ctx.fillText('PAPAN KARTU', 10, 14);
  ctx.font = '9px sans-serif';
  ctx.fillStyle = '#c0661a'; ctx.fillText('Nunggu lu: ' + D.counts.nunggu, 10, 29);
  ctx.fillStyle = '#1f6fb2'; ctx.fillText('Berjalan: ' + D.counts.jalan, 10, 42);
  ctx.fillStyle = '#1e8449'; ctx.fillText('Selesai: ' + D.counts.selesai, 10, 55);
  ctx.restore();
}

// ---------- Objek ----------
const objs = [];
function addObj(dep, fn) { objs.push({ dep: dep, draw: fn }); }
function charOf(k) { return chars.filter(function (c) { return c.kunci === k; })[0]; }

Object.keys(DESK).forEach(function (k) {
  const d = DESK[k], s = SEAT[k];
  addObj(s[0] + 0.3 + s[1] + 0.3, function () {
    box(s[0] - 0.3, s[1] - 0.3, 0.6, 0.6, 8, '#3a3f4b');
    box(s[0] - 0.3, s[1] - 0.45, 0.6, 0.12, 24, '#3a3f4b');
  });
  addObj(d[0] + 2 + d[1] + 1.1, function () {
    box(d[0], d[1], 2, 1.1, 26, '#b98a5a');
    box(d[0] + 0.6, d[1] + 0.62, 0.8, 0.3, 2, '#40444d', 26);
    const mx = d[0] + 0.65, my = d[1] + 0.2;
    box(mx, my, 0.7, 0.12, 20, '#2b2f3a', 26);
    const ch = charOf(k), on = ch && ch.sitting && working(ch);
    const col = on ? ((Math.floor(performance.now() / 250) % 2) ? '#7fe0ff' : '#5fd0ff') : '#16222e';
    const yy = my + 0.12;
    poly([P(mx + 0.06, yy, 30), P(mx + 0.64, yy, 30), P(mx + 0.64, yy, 44), P(mx + 0.06, yy, 44)], col);
  });
});
// meja supervisor + kamu
addObj(4.0 + 1.9 + 2.8 + 0.9, function () {
  box(4.0, 2.8, 1.9, 0.9, 22, '#4a3b5a');
  box(4.3, 2.95, 0.6, 0.1, 14, '#2b2f3a', 22);
  const yy = 3.05;
  poly([P(4.36, yy, 25), P(4.84, yy, 25), P(4.84, yy, 33), P(4.36, yy, 33)], '#16222e');
});
addObj(4.95 + 2.1 + 0.4 + 0.6, function () { box(4.65, 1.8, 0.6, 0.6, 8, '#3a3f4b'); });
const kamu = { x: 4.95, y: 2.1, sitting: true, walking: false, seed: 0, kunci: 'kamu', status: 'idle' };
addObj(4.95 + 2.1 + 1.0, function (t) { drawChar(kamu, 0, { shirt: '#8d99ae', hair: '#222', female: false }, true); });
// sofa
addObj(7.0 + 2.4 + 3.9 + 1.0, function () {
  box(7.0, 3.9, 2.4, 0.35, 32, '#7a2f3e'); box(7.0, 4.25, 2.4, 0.65, 14, '#8a3b4a');
  box(7.0, 3.9, 0.25, 1.0, 22, '#7a2f3e'); box(9.15, 3.9, 0.25, 1.0, 22, '#7a2f3e');
});
// pantry
addObj(7.2 + 2.4 + 8.4 + 0.9, function () {
  box(7.2, 8.4, 2.4, 0.9, 30, '#d9d4c7'); box(8.5, 8.55, 0.5, 0.4, 14, '#333', 30);
  const p = P(7.9, 8.8, 34); rect(p[0] - 3, p[1] - 5, 5, 6, '#fff');
});
// rak buku & tanaman
addObj(0.2 + 0.7 + 4.2 + 2.0, function () {
  box(0.2, 4.2, 0.7, 2.0, 64, '#6b4a2f');
  ['#c0392b', '#2980b9', '#27ae60', '#f39c12', '#8e44ad'].forEach(function (c, i) {
    box(0.55, 4.35 + i * 0.35, 0.3, 0.25, 8, c, 18); box(0.55, 4.35 + i * 0.35, 0.3, 0.25, 8, c, 40);
  });
});
function plant(x, y) {
  addObj(x + 0.5 + y + 0.5, function () {
    box(x, y, 0.5, 0.5, 10, '#a0522d');
    const p = P(x + 0.25, y + 0.25, 10);
    [['#2e8b57', 0, -10, 9], ['#3cb371', -6, -6, 7], ['#3cb371', 6, -6, 7], ['#2e8b57', 0, -18, 7]].forEach(function (b) {
      ctx.fillStyle = b[0]; ctx.beginPath(); ctx.arc(p[0] + b[1], p[1] + b[2], b[3], 0, 6.3); ctx.fill();
    });
  });
}
plant(1.0, 7.4); plant(9.0, 0.6); plant(0.6, 0.9);

// ---------- Render ----------
function render(t) {
  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = '#0e1117'; ctx.fillRect(0, 0, W, H);
  drawRoom();
  const list = objs.slice();
  chars.forEach(function (c) {
    list.push({ dep: c.x + c.y + (c.sitting ? 1.0 : 0.3), draw: function () { drawChar(c, t, LOOK[c.kunci], false); } });
  });
  list.sort(function (a, b) { return a.dep - b.dep; });
  list.forEach(function (o) { o.draw(t); });
  chars.forEach(function (c) {
    const p = P(c.x, c.y, c.sitting ? 8 : 0), top = p[1] - 36;
    tag(c.nama + ' · ' + c.peran, p[0], top);
    const b = bubbleFor(c);
    if (b) bubble(b.text, p[0], top - 14, b.color);
  });
  const kp = P(kamu.x, kamu.y, 8);
  tag('Kamu (Supervisor)', kp[0], kp[1] - 36, 'rgba(80,90,110,.9)');
  ctx.font = 'bold 12px sans-serif'; ctx.fillStyle = '#e8e2d6'; ctx.fillText('JDC Distribution Center', 12, 20);
  ctx.font = '10px sans-serif'; ctx.fillStyle = '#9aa3b2'; ctx.fillText('Kantor AI · Cikarang', 12, 35);
}
let last = performance.now();
function frame(now) {
  const dt = Math.min(0.05, (now - last) / 1000); last = now;
  chars.forEach(function (c) { update(c, dt); });
  render(now / 1000);
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
try { window.parent.postMessage({ isStreamlitMessageEvent: true, type: 'streamlit:setFrameHeight', height: Math.round(cv.getBoundingClientRect().height) + 4 }, '*'); } catch (e) {}
</script></body></html>"""
