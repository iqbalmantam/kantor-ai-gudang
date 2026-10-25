"""Logika inti Kantor AI Gudang (tanpa UI).

Kartu tugas disimpan di SQLite. Setiap kartu diproses agent yang ditunjuk.
Agent bisa: selesai, minta jawaban manusia (nunggu_lu), atau menyerahkan ke agent lain.
"""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from agents import AGENTS, jalankan_agent

DB_PATH = os.getenv("DB_PATH", "kantor.db")
MAKS_SERAH = 3  # batas estafet antar agent supaya tidak looping


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
                diubah TEXT NOT NULL,
                prioritas TEXT NOT NULL DEFAULT 'normal'
            )"""
        )
        # Migrasi untuk database lama yang belum punya kolom prioritas
        kolom = [r["name"] for r in c.execute("PRAGMA table_info(kartu)").fetchall()]
        if "prioritas" not in kolom:
            c.execute("ALTER TABLE kartu ADD COLUMN prioritas TEXT NOT NULL DEFAULT 'normal'")
        c.execute("UPDATE kartu SET agent='admin_control' WHERE agent='manager_ops'")  # migrasi nama lama
        c.execute(
            """CREATE TABLE IF NOT EXISTS pesan (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kartu_id INTEGER NOT NULL,
                pengirim TEXT NOT NULL,
                teks TEXT NOT NULL,
                waktu TEXT NOT NULL
            )"""
        )


def _kartu(row) -> dict:
    d = dict(row)
    d["kode"] = f"KD-{d['id']:03d}"
    return d


def daftar_kartu() -> list[dict]:
    with db() as c:
        rows = c.execute("SELECT * FROM kartu ORDER BY id DESC").fetchall()
    return [_kartu(r) for r in rows]


def pesan_kartu(kartu_id: int) -> list[dict]:
    with db() as c:
        rows = c.execute(
            "SELECT * FROM pesan WHERE kartu_id=? ORDER BY id", (kartu_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def semua_pesan(limit: int = 50) -> list[dict]:
    with db() as c:
        rows = c.execute(
            "SELECT p.*, k.judul FROM pesan p JOIN kartu k ON k.id=p.kartu_id"
            " ORDER BY p.id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


def tambah_pesan(kartu_id: int, pengirim: str, teks: str):
    with db() as c:
        c.execute(
            "INSERT INTO pesan (kartu_id, pengirim, teks, waktu) VALUES (?,?,?,?)",
            (kartu_id, pengirim, teks, sekarang()),
        )


def ubah_status(kartu_id: int, status: str):
    with db() as c:
        c.execute(
            "UPDATE kartu SET status=?, diubah=? WHERE id=?",
            (status, sekarang(), kartu_id),
        )


PRIORITAS = ("rendah", "normal", "tinggi", "urgent")


def buat_kartu(
    judul: str, deskripsi: str, agent: str, hop: int = 0, prioritas: str = "normal"
) -> dict:
    if agent not in AGENTS:
        raise ValueError(f"Agent tidak dikenal: {agent}")
    if prioritas not in PRIORITAS:
        prioritas = "normal"
    t = sekarang()
    with db() as c:
        cur = c.execute(
            "INSERT INTO kartu (judul, deskripsi, agent, status, hop, dibuat, diubah, prioritas)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (judul, deskripsi, agent, "antri", hop, t, t, prioritas),
        )
        row = c.execute("SELECT * FROM kartu WHERE id=?", (cur.lastrowid,)).fetchone()
    return _kartu(row)


def proses_kartu(kartu_id: int):
    """Proses satu kartu sampai selesai/nunggu_lu. Estafet ke agent lain ikut diproses."""
    antrean = [kartu_id]
    while antrean:
        kid = antrean.pop(0)
        with db() as c:
            row = c.execute("SELECT * FROM kartu WHERE id=?", (kid,)).fetchone()
        if row is None:
            continue
        kartu = _kartu(row)
        riwayat = [{"pengirim": m["pengirim"], "teks": m["teks"]} for m in pesan_kartu(kid)]
        nama_agent = AGENTS[kartu["agent"]]["nama"]

        ubah_status(kid, "jalan")
        try:
            hasil = jalankan_agent(
                kartu["agent"], kartu["judul"], kartu["deskripsi"], riwayat
            )
        except Exception as e:  # rate limit, API key kosong, dll.
            tambah_pesan(kid, "sistem", f"Gagal memanggil AI: {e}")
            ubah_status(kid, "error")
            continue

        tambah_pesan(kid, nama_agent, hasil["balasan"])

        tujuan = hasil["serahkan_ke"]
        if tujuan and kartu["hop"] < MAKS_SERAH:
            baru = buat_kartu(
                kartu["judul"],
                hasil["catatan_serah"] or kartu["deskripsi"],
                tujuan,
                hop=kartu["hop"] + 1,
                prioritas=kartu.get("prioritas", "normal"),
            )
            tambah_pesan(
                kid,
                nama_agent,
                f"Saya serahkan ke {AGENTS[tujuan]['nama']} ({baru['kode']}).",
            )
            ubah_status(kid, "selesai")
            antrean.append(baru["id"])
        else:
            ubah_status(kid, hasil["status"])


def jawab_kartu(kartu_id: int, jawaban: str):
    """Supervisor manusia menjawab kartu nunggu_lu (atau mencoba ulang kartu error)."""
    tambah_pesan(kartu_id, "supervisor", jawaban.strip())
    ubah_status(kartu_id, "antri")
    proses_kartu(kartu_id)


def hapus_kartu(kartu_id: int):
    with db() as c:
        c.execute("DELETE FROM pesan WHERE kartu_id=?", (kartu_id,))
        c.execute("DELETE FROM kartu WHERE id=?", (kartu_id,))


def tandai_selesai(kartu_id: int):
    """Supervisor menutup kartu secara manual."""
    tambah_pesan(kartu_id, "sistem", "Kartu ditutup manual oleh supervisor.")
    ubah_status(kartu_id, "selesai")


def _ts(teks: str) -> datetime:
    return datetime.fromisoformat(teks)


def statistik() -> dict:
    """Ringkasan angka untuk dashboard."""
    kartu = daftar_kartu()
    total = len(kartu)
    per_status = {s: 0 for s in ("antri", "jalan", "nunggu_lu", "error", "selesai")}
    per_agent = {k: {"aktif": 0, "selesai": 0, "menunggu": 0} for k in AGENTS}
    per_hari: dict[str, int] = {}
    per_prioritas = {p: 0 for p in PRIORITAS}
    durasi = []
    for k in kartu:
        per_status[k["status"]] = per_status.get(k["status"], 0) + 1
        per_prioritas[k.get("prioritas", "normal")] = per_prioritas.get(k.get("prioritas", "normal"), 0) + 1
        a = per_agent.get(k["agent"])
        if a is not None:
            if k["status"] == "selesai":
                a["selesai"] += 1
            elif k["status"] in ("nunggu_lu", "error"):
                a["menunggu"] += 1
            else:
                a["aktif"] += 1
        hari = k["dibuat"][:10]
        per_hari[hari] = per_hari.get(hari, 0) + 1
        if k["status"] == "selesai":
            try:
                durasi.append((_ts(k["diubah"]) - _ts(k["dibuat"])).total_seconds())
            except ValueError:
                pass
    selesai = per_status["selesai"]
    return {
        "total": total,
        "per_status": per_status,
        "per_agent": per_agent,
        "per_hari": dict(sorted(per_hari.items())),
        "per_prioritas": per_prioritas,
        "aktif": per_status["antri"] + per_status["jalan"],
        "menunggu": per_status["nunggu_lu"] + per_status["error"],
        "selesai": selesai,
        "rasio_selesai": (selesai / total * 100) if total else 0.0,
        "rata_durasi_detik": (sum(durasi) / len(durasi)) if durasi else 0.0,
    }
