"""Orchestrator Kantor AI Gudang (MVP).

- Kartu tugas disimpan di SQLite.
- Setiap kartu diproses oleh agent yang ditunjuk (lewat Groq).
- Agent bisa: selesai, minta jawaban manusia (nunggu_lu), atau menyerahkan ke agent lain.
- Semua perubahan disiarkan lewat WebSocket /ws.
"""
import asyncio
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents import AGENTS, jalankan_agent

DB_PATH = os.getenv("DB_PATH", "kantor.db")
MAKS_SERAH = 3  # batas estafet antar agent supaya tidak looping
semaphore = asyncio.Semaphore(1)  # satu panggilan LLM sekali waktu (hemat rate limit)

app = FastAPI(title="Kantor AI Gudang")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Database ----------
@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def sekarang() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@app.on_event("startup")
def init_db():
    with db() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS kartu (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                judul TEXT NOT NULL,
                deskripsi TEXT DEFAULT '',
                agent TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'antri',
                hop INTEGER NOT NULL DEFAULT 0,
                dibuat TEXT NOT NULL,
                diubah TEXT NOT NULL
            )"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS pesan (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kartu_id INTEGER NOT NULL,
                pengirim TEXT NOT NULL,
                teks TEXT NOT NULL,
                waktu TEXT NOT NULL
            )"""
        )


def kartu_dict(row) -> dict:
    d = dict(row)
    d["kode"] = f"KD-{d['id']:03d}"
    return d


# ---------- WebSocket ----------
class Penyiar:
    def __init__(self):
        self.koneksi: set[WebSocket] = set()

    async def siarkan(self, event: dict):
        mati = []
        for ws in self.koneksi:
            try:
                await ws.send_json(event)
            except Exception:
                mati.append(ws)
        for ws in mati:
            self.koneksi.discard(ws)


penyiar = Penyiar()


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    penyiar.koneksi.add(ws)
    try:
        while True:
            await ws.receive_text()  # keep-alive; klien boleh kirim "ping"
    except WebSocketDisconnect:
        penyiar.koneksi.discard(ws)


# ---------- Logika inti ----------
def tambah_pesan(kartu_id: int, pengirim: str, teks: str) -> dict:
    with db() as c:
        cur = c.execute(
            "INSERT INTO pesan (kartu_id, pengirim, teks, waktu) VALUES (?,?,?,?)",
            (kartu_id, pengirim, teks, sekarang()),
        )
        row = c.execute("SELECT * FROM pesan WHERE id=?", (cur.lastrowid,)).fetchone()
    return dict(row)


def ubah_status(kartu_id: int, status: str) -> dict:
    with db() as c:
        c.execute(
            "UPDATE kartu SET status=?, diubah=? WHERE id=?",
            (status, sekarang(), kartu_id),
        )
        row = c.execute("SELECT * FROM kartu WHERE id=?", (kartu_id,)).fetchone()
    return kartu_dict(row)


def buat_kartu_db(judul: str, deskripsi: str, agent: str, hop: int = 0) -> dict:
    t = sekarang()
    with db() as c:
        cur = c.execute(
            "INSERT INTO kartu (judul, deskripsi, agent, status, hop, dibuat, diubah)"
            " VALUES (?,?,?,?,?,?,?)",
            (judul, deskripsi, agent, "antri", hop, t, t),
        )
        row = c.execute("SELECT * FROM kartu WHERE id=?", (cur.lastrowid,)).fetchone()
    return kartu_dict(row)


async def proses_kartu(kartu_id: int):
    async with semaphore:
        with db() as c:
            row = c.execute("SELECT * FROM kartu WHERE id=?", (kartu_id,)).fetchone()
            riwayat = [
                dict(r)
                for r in c.execute(
                    "SELECT pengirim, teks FROM pesan WHERE kartu_id=? ORDER BY id",
                    (kartu_id,),
                )
            ]
        if row is None:
            return
        kartu = kartu_dict(row)
        nama_agent = AGENTS[kartu["agent"]]["nama"]

        await penyiar.siarkan({"event": "kartu", "data": ubah_status(kartu_id, "jalan")})

        try:
            hasil = await asyncio.to_thread(
                jalankan_agent, kartu["agent"], kartu["judul"], kartu["deskripsi"], riwayat
            )
        except Exception as e:  # rate limit, API key kosong, dll.
            pesan = tambah_pesan(kartu_id, "sistem", f"Gagal memanggil AI: {e}")
            await penyiar.siarkan({"event": "pesan", "data": pesan})
            await penyiar.siarkan({"event": "kartu", "data": ubah_status(kartu_id, "error")})
            return

        pesan = tambah_pesan(kartu_id, nama_agent, hasil["balasan"])
        await penyiar.siarkan({"event": "pesan", "data": pesan})

        tujuan = hasil["serahkan_ke"]
        if tujuan and kartu["hop"] < MAKS_SERAH:
            baru = buat_kartu_db(
                judul=kartu["judul"],
                deskripsi=hasil["catatan_serah"] or kartu["deskripsi"],
                agent=tujuan,
                hop=kartu["hop"] + 1,
            )
            info = tambah_pesan(
                kartu_id,
                nama_agent,
                f"Saya serahkan ke {AGENTS[tujuan]['nama']} ({baru['kode']}).",
            )
            await penyiar.siarkan({"event": "pesan", "data": info})
            await penyiar.siarkan({"event": "kartu", "data": baru})
            await penyiar.siarkan(
                {"event": "kartu", "data": ubah_status(kartu_id, "selesai")}
            )
            asyncio.create_task(proses_kartu(baru["id"]))
            return

        await penyiar.siarkan(
            {"event": "kartu", "data": ubah_status(kartu_id, hasil["status"])}
        )


# ---------- API ----------
class KartuBaru(BaseModel):
    judul: str
    deskripsi: str = ""
    agent: str


class Jawaban(BaseModel):
    jawaban: str


@app.get("/")
def beranda():
    return {"app": "Kantor AI Gudang", "docs": "/docs", "agents": "/agents"}


@app.get("/agents")
def daftar_agent():
    return [{"kunci": k, **v} for k, v in AGENTS.items()]


@app.get("/cards")
def daftar_kartu():
    with db() as c:
        rows = c.execute("SELECT * FROM kartu ORDER BY id DESC").fetchall()
    return [kartu_dict(r) for r in rows]


@app.get("/cards/{kartu_id}/messages")
def pesan_kartu(kartu_id: int):
    with db() as c:
        rows = c.execute(
            "SELECT * FROM pesan WHERE kartu_id=? ORDER BY id", (kartu_id,)
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/messages")
def semua_pesan(limit: int = 50):
    with db() as c:
        rows = c.execute(
            "SELECT * FROM pesan ORDER BY id DESC LIMIT ?", (min(limit, 200),)
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


@app.post("/cards")
async def buat_kartu(body: KartuBaru):
    if body.agent not in AGENTS:
        raise HTTPException(400, f"Agent tidak dikenal. Pilih: {list(AGENTS)}")
    kartu = buat_kartu_db(body.judul.strip(), body.deskripsi.strip(), body.agent)
    await penyiar.siarkan({"event": "kartu", "data": kartu})
    asyncio.create_task(proses_kartu(kartu["id"]))
    return kartu


@app.post("/cards/{kartu_id}/answer")
async def jawab_kartu(kartu_id: int, body: Jawaban):
    """Supervisor manusia menjawab kartu yang berstatus nunggu_lu."""
    with db() as c:
        row = c.execute("SELECT * FROM kartu WHERE id=?", (kartu_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Kartu tidak ditemukan")
    if row["status"] not in ("nunggu_lu", "error"):
        raise HTTPException(400, "Kartu ini tidak sedang menunggu jawaban")
    pesan = tambah_pesan(kartu_id, "supervisor", body.jawaban.strip())
    await penyiar.siarkan({"event": "pesan", "data": pesan})
    await penyiar.siarkan({"event": "kartu", "data": ubah_status(kartu_id, "antri")})
    asyncio.create_task(proses_kartu(kartu_id))
    return {"ok": True}
