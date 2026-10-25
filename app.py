"""Kantor AI Gudang - tampilan Streamlit."""
import os

import streamlit as st

import core
import office
from agents import AGENTS

st.set_page_config(page_title="Kantor AI Gudang", page_icon="🏭", layout="wide")

st.markdown(
    """
    <style>
    /* Sembunyikan Share / bintang / edit / GitHub / menu titik tiga, dekorasi, footer, badge */
    [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"],
    [data-testid="stMainMenu"], [data-testid="stAppDeployButton"], [data-testid="manage-app-button"],
    .stAppDeployButton, #MainMenu, footer, [class*="viewerBadge"], [class*="_profileContainer"]
    {display: none !important; visibility: hidden !important;}
    /* Header dibuat transparan & tanpa tinggi; tombol buka-sidebar tetap tampil */
    header[data-testid="stHeader"] {background: transparent !important; height: 0 !important; min-height: 0 !important;}
    [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"]
    {display: flex !important; visibility: visible !important; z-index: 999990 !important;}
    .block-container {padding-top: 1.2rem !important;}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def _siap():
    core.init_db()
    return True


_siap()

LABEL_STATUS = {
    "antri": "⏳ Antri",
    "jalan": "⚙️ Jalan",
    "nunggu_lu": "🙋 Nunggu lu",
    "error": "⚠️ Error",
    "selesai": "✅ Selesai",
}


def nama_agent(kunci: str) -> str:
    a = AGENTS[kunci]
    return f"{a['nama']} ({a['peran']})"


st.title("🏭 Kantor AI Gudang")

if not os.getenv("GROQ_API_KEY"):
    st.warning(
        "GROQ_API_KEY belum diisi. Di Streamlit Cloud: Settings → Secrets, "
        'tulis: GROQ_API_KEY = "gsk_..."'
    )

# ---------- Sidebar: buat kartu ----------
with st.sidebar:
    st.header("Kartu baru")
    with st.form("form_kartu", clear_on_submit=True):
        judul = st.text_input("Judul tugas")
        deskripsi = st.text_area("Detail (opsional)", height=100)
        agent = st.selectbox("Untuk siapa?", list(AGENTS), format_func=nama_agent)
        kirim = st.form_submit_button("Kirim ke agent", use_container_width=True)
    if kirim:
        if not judul.strip():
            st.error("Judul wajib diisi.")
        else:
            kartu = core.buat_kartu(judul.strip(), deskripsi.strip(), agent)
            with st.spinner(f"{AGENTS[agent]['nama']} sedang mengerjakan..."):
                core.proses_kartu(kartu["id"])
            st.rerun()
    if st.button("🔄 Segarkan", use_container_width=True):
        st.rerun()

kartu_semua = core.daftar_kartu()

tab_kantor, tab_papan, tab_chat = st.tabs(["🏢 Kantor", "📋 Papan kartu", "💬 Chat kantor"])

# ---------- Simulasi kantor ----------
with tab_kantor:
    @st.fragment(run_every=5)
    def _kantor():
        office.tampilkan()

    _kantor()
    st.caption("Agent duduk di meja saat bekerja, ke meja supervisor saat butuh jawabanmu, dan jalan-jalan saat senggang.")

# ---------- Papan kartu ----------
with tab_papan:
    if not kartu_semua:
        st.info("Belum ada kartu. Buat kartu pertama lewat menu di samping (ikon > di kiri atas).")

    menunggu = [k for k in kartu_semua if k["status"] in ("nunggu_lu", "error")]
    berjalan = [k for k in kartu_semua if k["status"] in ("antri", "jalan")]
    selesai = [k for k in kartu_semua if k["status"] == "selesai"]

    def tampil_kartu(k, boleh_jawab=False):
        judul_kartu = f"{k['kode']} · {k['judul']} — {LABEL_STATUS[k['status']]}"
        with st.expander(judul_kartu, expanded=boleh_jawab):
            st.caption(f"Dipegang {nama_agent(k['agent'])}")
            if k["deskripsi"]:
                st.write(k["deskripsi"])
            for m in core.pesan_kartu(k["id"]):
                with st.chat_message(m["pengirim"]):
                    st.write(m["teks"])
            if boleh_jawab:
                with st.form(f"jawab_{k['id']}", clear_on_submit=True):
                    teks = st.text_input(
                        "Jawaban kamu" if k["status"] == "nunggu_lu" else "Catatan untuk coba ulang"
                    )
                    ok = st.form_submit_button("Kirim")
                if ok and teks.strip():
                    with st.spinner("Agent memproses jawabanmu..."):
                        core.jawab_kartu(k["id"], teks)
                    st.rerun()

    st.subheader(f"🙋 Nunggu lu ({len(menunggu)})")
    for k in menunggu:
        tampil_kartu(k, boleh_jawab=True)

    st.subheader(f"⚙️ Berjalan ({len(berjalan)})")
    for k in berjalan:
        tampil_kartu(k)

    st.subheader(f"✅ Selesai ({len(selesai)})")
    for k in selesai:
        tampil_kartu(k)

# ---------- Chat kantor ----------
with tab_chat:
    pesan = core.semua_pesan(50)
    if not pesan:
        st.info("Belum ada obrolan.")
    for m in pesan:
        with st.chat_message(m["pengirim"]):
            st.caption(f"KD-{m['kartu_id']:03d} · {m['judul']}")
            st.write(m["teks"])
