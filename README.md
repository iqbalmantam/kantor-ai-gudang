# Kantor AI Gudang

Pusat kendali operasional gudang **JDC Distribution Center** dengan agent AI (Regita – HRD, Yogi – Operation Control, Zakhwan – Admin Control).

## Fitur
- **Dashboard**: KPI, komposisi status, beban kerja per agent, tren harian, kartu yang butuh jawabanmu, feed aktivitas.
- **Kantor 3D**: simulasi kantor WebGL, agent bergerak sesuai status kartu.
- **Papan kartu**: Kanban dengan pencarian, filter agent/prioritas, jawab/tutup/hapus kartu.
- **Tim agent**: profil, beban kerja, dan penugasan langsung per agent.
- **Aktivitas**: log percakapan dengan filter pengirim.
- **Laporan**: ringkasan harian dan ekspor CSV.
- **Fitur & roadmap**: katalog fitur aktif dan ide pengembangan.
- **Template tugas cepat** dan **prioritas** (rendah / normal / tinggi / urgent).

## Menjalankan
```bash
pip install -r requirements.txt
export GROQ_API_KEY="gsk_..."
streamlit run app.py
```
Di Streamlit Cloud isi `GROQ_API_KEY` lewat Settings → Secrets. Database lama otomatis dimigrasi (kolom `prioritas` ditambahkan).
