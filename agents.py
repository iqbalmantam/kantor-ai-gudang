"""Definisi agent + pemanggilan Groq.

Tiap agent = "karyawan" dengan peran dan system prompt sendiri.
Agent selalu membalas JSON supaya orchestrator (main.py) mudah membaca keputusannya.
"""
import json
import os

from groq import Groq

# Urutan model yang dicoba. GROQ_MODEL (opsional, di Secrets) dicoba paling dulu.
MODELS = [m for m in [
    os.getenv("GROQ_MODEL"),
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-120b",
    "llama-3.1-8b-instant",
    "openai/gpt-oss-20b",
] if m]
_model_ok = None  # model yang terakhir berhasil, supaya tidak mencoba ulang yang 404

AGENTS = {
    "hrd": {
        "nama": "Regita",
        "peran": "HRD",
        "gender": "wanita",
        "tugas": "Absensi, kebutuhan manpower, cuti/lembur, rekrutmen, kedisiplinan, pembinaan karyawan.",
        "warna": "#f472b6",
        "keahlian": ["Absensi", "Manpower", "Cuti & Lembur", "Rekrutmen"],
    },
    "op_control": {
        "nama": "Yogi",
        "peran": "Operation Control",
        "gender": "pria",
        "tugas": "Memantau jalannya operasional harian, produktivitas, antrean kerja, dan temuan lapangan.",
        "warna": "#fbbf24",
        "keahlian": ["Produktivitas", "Antrean kerja", "Temuan lapangan", "Monitoring"],
    },
    "admin_control": {
        "nama": "Zakhwan",
        "peran": "Admin Control",
        "gender": "pria",
        "tugas": "Administrasi operasional: rekap dan input data, dokumen (DO/SJ/BAST), laporan harian, pengarsipan, dan follow-up kelengkapan data. Bukan pengambil keputusan; keputusan/persetujuan diminta dari supervisor.",
        "warna": "#38bdf8",
        "keahlian": ["Rekap data", "Dokumen", "Laporan harian", "Pengarsipan"],
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
        f"Namamu {a['nama']}, agent {a['peran']} (gender {a['gender']}). Wewenangmu: {a['tugas']}\n"
        + ATURAN_UMUM % lain
    )


def _klien():
    kunci_api = os.getenv("GROQ_API_KEY")
    if not kunci_api:
        raise RuntimeError("GROQ_API_KEY belum diisi di Environment.")
    return Groq(api_key=kunci_api)


def _panggil(pesan: list[dict]):
    """Coba model satu per satu; lewati yang 404 / tidak bisa diakses."""
    global _model_ok
    klien = _klien()
    urutan = ([_model_ok] if _model_ok else []) + [m for m in MODELS if m != _model_ok]
    galat = None
    for model in urutan:
        opsi = {}
        if model.startswith("openai/gpt-oss"):
            opsi["reasoning_effort"] = "low"
        try:
            resp = klien.chat.completions.create(
                model=model,
                messages=pesan,
                temperature=0.3,
                max_tokens=1000,
                response_format={"type": "json_object"},
                **opsi,
            )
            _model_ok = model
            return resp
        except Exception as e:
            galat = e
            teks = str(e)
            if "model_not_found" in teks or "does not exist" in teks or "decommissioned" in teks:
                continue
            raise
    raise RuntimeError(f"Tidak ada model Groq yang bisa diakses ({', '.join(urutan)}). Terakhir: {galat}")


def jalankan_agent(kunci: str, judul: str, deskripsi: str, riwayat: list[dict]) -> dict:
    """Panggil LLM untuk satu giliran kerja. Return dict ter-validasi."""
    pesan = [{"role": "system", "content": system_prompt(kunci)}]
    pesan.append(
        {"role": "user", "content": f"Kartu tugas: {judul}\nDetail: {deskripsi or '-'}"}
    )
    for r in riwayat:
        # riwayat: {"pengirim": "...", "teks": "..."}
        pesan.append({"role": "user", "content": f"[{r['pengirim']}] {r['teks']}"})

    resp = _panggil(pesan)
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
