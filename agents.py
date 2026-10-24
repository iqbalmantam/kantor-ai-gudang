"""Definisi agent + pemanggilan Groq.

Tiap agent = "karyawan" dengan peran dan system prompt sendiri.
Agent selalu membalas JSON supaya orchestrator (main.py) mudah membaca keputusannya.
"""
import json
import os

from groq import Groq

MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

AGENTS = {
    "inbound": {
        "nama": "Dewi",
        "peran": "Inbound",
        "tugas": "Penerimaan barang, cek dokumen PO/DO, jadwal bongkar, putaway ke rak.",
    },
    "inventory": {
        "nama": "Rizky",
        "peran": "Inventory",
        "tugas": "Akurasi stok, selisih stock opname, lokasi rak, replenishment.",
    },
    "audit": {
        "nama": "Bayu",
        "peran": "Audit Racking",
        "tugas": "Inspeksi kondisi rak (penyok, miring, baut kendor), temuan keselamatan, tindak lanjut PIC.",
    },
}

ATURAN_UMUM = """
Kamu karyawan AI di kantor gudang JDC Distribution Center (Cikarang).
Bicara Bahasa Indonesia santai-profesional, singkat (maksimal 3 kalimat).
Jangan mengarang data angka yang tidak diberikan. Kalau butuh data/keputusan manusia, minta dengan jelas.

Balas HANYA dengan JSON valid, tanpa teks lain, dengan kunci:
{
  "balasan": "pesan singkatmu untuk tim",
  "status": "selesai" atau "nunggu_lu",
  "serahkan_ke": null atau salah satu dari: %s,
  "catatan_serah": "instruksi untuk agent tujuan (isi hanya jika serahkan_ke tidak null)"
}

Aturan status:
- "selesai": tugasmu beres, tidak perlu keputusan manusia.
- "nunggu_lu": kamu butuh persetujuan/jawaban/data dari supervisor manusia. Tulis pertanyaannya di "balasan".
Kalau sebagian tugas bukan wewenangmu, isi "serahkan_ke" ke agent yang tepat.
"""


def system_prompt(kunci: str) -> str:
    a = AGENTS[kunci]
    lain = ", ".join(f'"{k}"' for k in AGENTS if k != kunci)
    return (
        f"Namamu {a['nama']}, agent {a['peran']}. Wewenangmu: {a['tugas']}\n"
        + ATURAN_UMUM % lain
    )


def _klien():
    kunci_api = os.getenv("GROQ_API_KEY")
    if not kunci_api:
        raise RuntimeError("GROQ_API_KEY belum diisi di Environment.")
    return Groq(api_key=kunci_api)


def jalankan_agent(kunci: str, judul: str, deskripsi: str, riwayat: list[dict]) -> dict:
    """Panggil LLM untuk satu giliran kerja. Return dict ter-validasi."""
    pesan = [{"role": "system", "content": system_prompt(kunci)}]
    pesan.append(
        {"role": "user", "content": f"Kartu tugas: {judul}\nDetail: {deskripsi or '-'}"}
    )
    for r in riwayat:
        # riwayat: {"pengirim": "...", "teks": "..."}
        pesan.append({"role": "user", "content": f"[{r['pengirim']}] {r['teks']}"})

    resp = _klien().chat.completions.create(
        model=MODEL,
        messages=pesan,
        temperature=0.3,
        max_tokens=400,
        response_format={"type": "json_object"},
    )
    mentah = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(mentah)
    except json.JSONDecodeError:
        data = {"balasan": mentah[:300], "status": "nunggu_lu"}

    status = data.get("status")
    if status not in ("selesai", "nunggu_lu"):
        status = "nunggu_lu"
    tujuan = data.get("serahkan_ke")
    if tujuan not in AGENTS or tujuan == kunci:
        tujuan = None
    return {
        "balasan": str(data.get("balasan", "")).strip() or "(tidak ada balasan)",
        "status": status,
        "serahkan_ke": tujuan,
        "catatan_serah": str(data.get("catatan_serah") or "").strip(),
    }
