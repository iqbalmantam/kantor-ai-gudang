"""Kantor AI Gudang - tampilan Streamlit (dashboard profesional)."""
import html as _html
import os
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st

import core
import office
from agents import AGENTS, MODELS

try:
    import altair as alt
except Exception:  # altair ikut terpasang bersama streamlit, jaga-jaga saja
    alt = None

st.set_page_config(
    page_title="Kantor AI Gudang · JDC Distribution Center",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

WIB = timezone(timedelta(hours=7))

# ============================================================
# Gaya (CSS)
# ============================================================
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root{
  --bg:#0b1020; --panel:#121a30; --panel2:#18223d; --line:rgba(148,163,184,.16);
  --txt:#e6ebf5; --mut:#8b97b1; --acc:#4f8cff; --acc2:#7c5cff;
  --ok:#34d399; --warn:#fbbf24; --bad:#f87171; --info:#38bdf8;
}
html, body, [class*="css"], .stApp {font-family:'Inter',system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;}
.stApp{
  background:
    radial-gradient(1100px 500px at 85% -10%, rgba(79,140,255,.14), transparent 60%),
    radial-gradient(900px 480px at -5% 0%, rgba(124,92,255,.10), transparent 55%),
    var(--bg);
}

/* ---- Sembunyikan chrome bawaan Streamlit ---- */
[data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"],
[data-testid="stMainMenu"], [data-testid="stAppDeployButton"], [data-testid="manage-app-button"],
.stAppDeployButton, #MainMenu, footer, [class*="viewerBadge"], [class*="_profileContainer"]
{display:none !important; visibility:hidden !important;}
header[data-testid="stHeader"]{background:transparent !important;height:0 !important;min-height:0 !important;}
[data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"]
{display:flex !important; visibility:visible !important; z-index:999990 !important;}
.block-container{padding-top:1.1rem !important; padding-bottom:3rem; max-width:1500px;}

/* ---- Sidebar ---- */
section[data-testid="stSidebar"]{
  background:linear-gradient(180deg,#0f1730 0%,#0b1226 100%) !important;
  border-right:1px solid var(--line);
}
section[data-testid="stSidebar"] .block-container{padding-top:1rem !important;}
.brand{display:flex;align-items:center;gap:12px;padding:6px 2px 14px}
.brand .logo{width:42px;height:42px;border-radius:12px;display:grid;place-items:center;font-size:22px;
  background:linear-gradient(135deg,var(--acc),var(--acc2));box-shadow:0 8px 22px rgba(79,140,255,.35)}
.brand b{display:block;font-size:15px;letter-spacing:.01em}
.brand span{font-size:11px;color:var(--mut)}
.sec{font-size:10.5px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--mut);margin:14px 0 6px}

/* ---- Header ---- */
.hero{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;
  padding:18px 22px;border-radius:18px;border:1px solid var(--line);
  background:linear-gradient(120deg,rgba(79,140,255,.16),rgba(124,92,255,.10) 55%,rgba(18,26,48,.6));
  box-shadow:0 10px 40px rgba(0,0,0,.25);margin-bottom:14px}
.hero h1{margin:0;font-size:26px;font-weight:800;letter-spacing:-.02em;line-height:1.15}
.hero p{margin:4px 0 0;color:var(--mut);font-size:13px}
.hero .meta{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.chip{display:inline-flex;align-items:center;gap:6px;padding:5px 11px;border-radius:999px;font-size:11.5px;font-weight:600;
  border:1px solid var(--line);background:rgba(255,255,255,.04);color:var(--txt);white-space:nowrap}
.chip.ok{color:var(--ok);border-color:rgba(52,211,153,.35);background:rgba(52,211,153,.08)}
.chip.bad{color:var(--bad);border-color:rgba(248,113,113,.35);background:rgba(248,113,113,.08)}
.chip.warn{color:var(--warn);border-color:rgba(251,191,36,.35);background:rgba(251,191,36,.08)}
.chip.info{color:var(--info);border-color:rgba(56,189,248,.35);background:rgba(56,189,248,.08)}
.dot{width:8px;height:8px;border-radius:50%;background:currentColor;box-shadow:0 0 0 0 currentColor;animation:pulse 1.8s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(52,211,153,.55)}70%{box-shadow:0 0 0 8px rgba(52,211,153,0)}100%{box-shadow:0 0 0 0 rgba(52,211,153,0)}}

/* ---- KPI ---- */
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:4px 0 14px}
.kpi{position:relative;overflow:hidden;padding:16px 18px;border-radius:16px;border:1px solid var(--line);
  background:linear-gradient(180deg,rgba(24,34,61,.95),rgba(18,26,48,.95))}
.kpi:before{content:"";position:absolute;left:0;top:0;bottom:0;width:4px;background:var(--c,var(--acc))}
.kpi .lb{font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--mut);display:flex;justify-content:space-between;align-items:center}
.kpi .lb i{font-style:normal;font-size:17px;opacity:.9}
.kpi .v{font-size:30px;font-weight:800;letter-spacing:-.02em;margin-top:6px;line-height:1}
.kpi .s{font-size:11.5px;color:var(--mut);margin-top:6px}

/* ---- Panel / kartu ---- */
.ph{display:flex;align-items:center;justify-content:space-between;margin:2px 0 8px}
.ph h3{margin:0;font-size:15px;font-weight:700;letter-spacing:-.01em}
.ph span{font-size:11.5px;color:var(--mut)}
[data-testid="stVerticalBlockBorderWrapper"]{border-radius:16px !important;border-color:var(--line) !important;background:rgba(18,26,48,.65)}

.tcard{border-radius:14px;border:1px solid var(--line);background:linear-gradient(180deg,#18223d,#141d36);padding:12px 14px;margin-bottom:8px;
  border-left:4px solid var(--c,var(--acc))}
.tcard .top{display:flex;justify-content:space-between;align-items:center;gap:8px}
.tcard .kode{font-size:11px;font-weight:700;color:var(--mut);letter-spacing:.06em}
.tcard .jd{font-size:14px;font-weight:650;margin:5px 0 8px;line-height:1.3}
.tcard .ft{display:flex;gap:6px;flex-wrap:wrap;align-items:center}
.tag{display:inline-flex;align-items:center;gap:5px;padding:2px 9px;border-radius:999px;font-size:10.5px;font-weight:650;border:1px solid var(--line);color:var(--mut);background:rgba(255,255,255,.03)}
.p-urgent{color:#fecaca;background:rgba(248,113,113,.16);border-color:rgba(248,113,113,.4)}
.p-tinggi{color:#fde68a;background:rgba(251,191,36,.14);border-color:rgba(251,191,36,.4)}
.p-normal{color:#bfdbfe;background:rgba(79,140,255,.14);border-color:rgba(79,140,255,.35)}
.p-rendah{color:#cbd5e1;background:rgba(148,163,184,.12)}
.av{width:22px;height:22px;border-radius:50%;display:inline-grid;place-items:center;font-size:11px;font-weight:800;color:#0b1020;background:var(--c,#94a3b8)}

.kol{display:flex;align-items:center;justify-content:space-between;padding:10px 14px;border-radius:12px;margin-bottom:10px;
  background:rgba(255,255,255,.03);border:1px solid var(--line);border-top:3px solid var(--c,var(--acc))}
.kol b{font-size:13px}
.kol span{font-size:11.5px;font-weight:700;padding:1px 9px;border-radius:999px;background:rgba(255,255,255,.07)}
.empty{padding:22px 10px;text-align:center;color:var(--mut);font-size:12px;border:1px dashed var(--line);border-radius:12px}

.acard{border-radius:18px;border:1px solid var(--line);padding:18px;background:linear-gradient(180deg,#18223d,#121a30);position:relative;overflow:hidden}
.acard:after{content:"";position:absolute;right:-40px;top:-40px;width:130px;height:130px;border-radius:50%;background:var(--c);opacity:.12;filter:blur(8px)}
.acard .avl{width:54px;height:54px;border-radius:16px;display:grid;place-items:center;font-size:24px;font-weight:800;color:#0b1020;background:var(--c)}
.acard h4{margin:10px 0 0;font-size:17px;font-weight:750}
.acard .rl{font-size:12px;color:var(--mut)}
.acard .tg{font-size:12px;color:#c4cde0;margin:10px 0;line-height:1.5}
.mini{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:12px}
.mini div{background:rgba(255,255,255,.04);border:1px solid var(--line);border-radius:10px;padding:8px 6px;text-align:center}
.mini b{display:block;font-size:18px}.mini span{font-size:10px;color:var(--mut);text-transform:uppercase;letter-spacing:.08em}
.bar{height:6px;border-radius:99px;background:rgba(255,255,255,.07);overflow:hidden;margin-top:12px}
.bar i{display:block;height:100%;background:linear-gradient(90deg,var(--c),var(--acc2));border-radius:99px}

.feed{display:flex;gap:10px;padding:9px 0;border-bottom:1px solid var(--line)}
.feed:last-child{border-bottom:0}
.feed .tx{font-size:12.5px;line-height:1.4;color:#d3dbec}
.feed .mt{font-size:10.5px;color:var(--mut);margin-top:2px}

.fcard{border-radius:16px;border:1px solid var(--line);padding:16px;background:linear-gradient(180deg,#18223d,#131c35);height:100%;min-height:138px}
.fcard .ic{font-size:24px}.fcard h5{margin:8px 0 4px;font-size:14px;font-weight:700}
.fcard p{margin:0 0 10px;font-size:12px;color:var(--mut);line-height:1.5}

/* ---- Widget Streamlit ---- */
.stTabs [data-baseweb="tab-list"]{gap:6px;border-bottom:1px solid var(--line);padding-bottom:0;flex-wrap:wrap}
.stTabs [data-baseweb="tab"]{height:42px;padding:0 16px;border-radius:10px 10px 0 0;font-weight:600;color:var(--mut)}
.stTabs [aria-selected="true"]{color:#fff !important;background:rgba(79,140,255,.14)}
.stTabs [data-baseweb="tab-highlight"]{background:var(--acc) !important;height:3px}
.stButton>button, .stDownloadButton>button, .stFormSubmitButton>button{
  border-radius:11px;font-weight:650;border:1px solid var(--line);background:rgba(255,255,255,.04);transition:all .15s}
.stButton>button:hover,.stDownloadButton>button:hover{border-color:var(--acc);color:#fff;background:rgba(79,140,255,.15)}
.stFormSubmitButton>button[kind="primary"],.stButton>button[kind="primary"]{
  background:linear-gradient(135deg,var(--acc),var(--acc2));border:0;color:#fff;box-shadow:0 6px 18px rgba(79,140,255,.3)}
[data-baseweb="input"],[data-baseweb="textarea"],[data-baseweb="select"]>div{border-radius:11px !important}
[data-testid="stExpander"]{border-radius:12px;border-color:var(--line)}
[data-testid="stMetric"]{background:rgba(255,255,255,.03);border:1px solid var(--line);border-radius:12px;padding:10px 14px}
[data-testid="stChatMessage"]{background:rgba(255,255,255,.03);border:1px solid var(--line);border-radius:14px}
iframe{border-radius:16px}
::-webkit-scrollbar{width:9px;height:9px}::-webkit-scrollbar-thumb{background:#26324f;border-radius:9px}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ============================================================
# Utilitas
# ============================================================
def H(s: str):
    """Render HTML tanpa indentasi (supaya tidak dibaca sebagai blok kode markdown)."""
    st.markdown("\n".join(x.strip() for x in s.strip().splitlines() if x.strip()), unsafe_allow_html=True)


def e(x) -> str:
    return _html.escape(str(x if x is not None else ""))


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
WARNA_STATUS = {
    "antri": "#94a3b8", "jalan": "#38bdf8", "nunggu_lu": "#fbbf24",
    "error": "#f87171", "selesai": "#34d399",
}
LABEL_PRIORITAS = {"rendah": "Rendah", "normal": "Normal", "tinggi": "Tinggi", "urgent": "Urgent"}

TEMPLATE = {
    "— pilih template —": None,
    "📋 Cek absensi hari ini": ("Rekap absensi harian", "Mohon rekap kehadiran, keterlambatan, dan karyawan yang belum masuk hari ini.", "hrd", "normal"),
    "👷 Kebutuhan manpower inbound": ("Kebutuhan manpower bongkar muat", "Perkirakan kebutuhan tenaga kerja untuk bongkar muat inbound besok pagi dan beri rekomendasi lembur bila perlu.", "hrd", "tinggi"),
    "🗂️ Rekap laporan harian": ("Rekap laporan operasional harian", "Susun rekap laporan operasional harian (inbound, outbound, kendala) dari data yang tersedia dan siapkan untuk diarsipkan.", "admin_control", "normal"),
    "📄 Cek kelengkapan dokumen": ("Cek kelengkapan dokumen pengiriman", "Periksa kelengkapan DO/surat jalan/BAST pengiriman hari ini dan catat dokumen yang masih kurang.", "admin_control", "tinggi"),
    "📦 Pantau antrean picking": ("Pantau antrean picking & packing", "Cek antrean kerja picking/packing saat ini dan laporkan hambatan produktivitas.", "op_control", "tinggi"),
    "🔍 Laporan temuan lapangan": ("Laporan temuan lapangan harian", "Susun ringkasan temuan lapangan hari ini (keselamatan, kerusakan barang, selisih stok).", "op_control", "normal"),
}


def nama_agent(kunci: str) -> str:
    a = AGENTS[kunci]
    return f"{a['nama']} ({a['peran']})"


def warna_agent(kunci: str) -> str:
    return AGENTS.get(kunci, {}).get("warna", "#94a3b8")


def ke_wib(iso: str) -> datetime:
    return datetime.fromisoformat(iso).astimezone(WIB)


def lalu(iso: str) -> str:
    try:
        d = (datetime.now(timezone.utc) - datetime.fromisoformat(iso)).total_seconds()
    except Exception:
        return ""
    if d < 60:
        return "baru saja"
    if d < 3600:
        return f"{int(d // 60)} mnt lalu"
    if d < 86400:
        return f"{int(d // 3600)} jam lalu"
    return f"{int(d // 86400)} hari lalu"


def durasi_teks(detik: float) -> str:
    if detik <= 0:
        return "—"
    if detik < 60:
        return f"{int(detik)} dtk"
    if detik < 3600:
        return f"{detik / 60:.1f} mnt"
    return f"{detik / 3600:.1f} jam"


def avatar(kunci: str) -> str:
    a = AGENTS.get(kunci)
    if not a:
        return '<span class="av" style="--c:#94a3b8">•</span>'
    return f'<span class="av" style="--c:{a["warna"]}">{e(a["nama"][0])}</span>'


def kirim_kartu(judul, deskripsi, agent, prioritas):
    kartu = core.buat_kartu(judul, deskripsi, agent, prioritas=prioritas)
    with st.spinner(f"{AGENTS[agent]['nama']} sedang mengerjakan..."):
        core.proses_kartu(kartu["id"])


API_OK = bool(os.getenv("GROQ_API_KEY"))
kartu_semua = core.daftar_kartu()
stat = core.statistik()
sekarang_wib = datetime.now(WIB)

# ============================================================
# Sidebar
# ============================================================
with st.sidebar:
    H(
        """
        <div class="brand"><div class="logo">🏭</div>
        <div><b>Kantor AI Gudang</b><span>JDC Distribution Center</span></div></div>
        """
    )

    H('<div class="sec">Tugas baru</div>')
    with st.form("form_kartu", clear_on_submit=True, border=False):
        judul = st.text_input("Judul tugas", placeholder="mis. Cek stok pallet zona B")
        deskripsi = st.text_area("Detail (opsional)", height=90, placeholder="Konteks, deadline, atau data pendukung…")
        c1, c2 = st.columns(2)
        agent = c1.selectbox("Untuk siapa?", list(AGENTS), format_func=lambda k: AGENTS[k]["nama"])
        prioritas = c2.selectbox(
            "Prioritas", core.PRIORITAS, index=1, format_func=lambda p: LABEL_PRIORITAS[p]
        )
        kirim = st.form_submit_button("🚀 Kirim ke agent", use_container_width=True, type="primary")
    if kirim:
        if not judul.strip():
            st.error("Judul wajib diisi.")
        else:
            kirim_kartu(judul.strip(), deskripsi.strip(), agent, prioritas)
            st.rerun()

    H('<div class="sec">Template cepat</div>')
    pilih_tpl = st.selectbox("Template", list(TEMPLATE), label_visibility="collapsed")
    if st.button("⚡ Jalankan template", use_container_width=True, disabled=TEMPLATE[pilih_tpl] is None):
        j, d, a, p = TEMPLATE[pilih_tpl]
        kirim_kartu(j, d, a, p)
        st.rerun()

    H('<div class="sec">Status sistem</div>')
    H(
        f"""
        <div style="display:flex;flex-direction:column;gap:6px">
        <span class="chip {'ok' if API_OK else 'bad'}"><span class="dot"></span>{'Groq API terhubung' if API_OK else 'GROQ_API_KEY belum diisi'}</span>
        <span class="chip info">🧠 Model: {e((MODELS or ['-'])[0])}</span>
        <span class="chip">🗄️ {stat['total']} kartu tersimpan</span>
        </div>
        """
    )
    st.write("")
    if st.button("🔄 Segarkan data", use_container_width=True):
        st.rerun()

# ============================================================
# Header
# ============================================================
H(
    f"""
    <div class="hero">
      <div>
        <h1>🏭 Kantor AI Gudang</h1>
        <p>Pusat kendali operasional gudang bertenaga agent AI · JDC Distribution Center, Cikarang</p>
      </div>
      <div class="meta">
        <span class="chip ok"><span class="dot"></span>Live</span>
        <span class="chip">🕒 {sekarang_wib.strftime('%A, %d %b %Y · %H:%M')} WIB</span>
        <span class="chip {'warn' if stat['menunggu'] else 'ok'}">🙋 {stat['menunggu']} butuh respons kamu</span>
      </div>
    </div>
    """
)

if not API_OK:
    st.warning(
        "GROQ_API_KEY belum diisi. Di Streamlit Cloud: Settings → Secrets, "
        'tulis: GROQ_API_KEY = "gsk_..."'
    )

(tab_dash, tab_kantor, tab_papan, tab_tim, tab_aktif, tab_lap, tab_fitur, tab_set) = st.tabs(
    [
        "📊 Dashboard",
        "🏢 Kantor 3D",
        "📋 Papan kartu",
        "👥 Tim agent",
        "💬 Aktivitas",
        "📑 Laporan",
        "✨ Fitur & roadmap",
        "⚙️ Pengaturan",
    ]
)


# ============================================================
# Komponen kartu tugas (dipakai di dashboard & papan)
# ============================================================
def render_kartu(k: dict, prefix: str, boleh_jawab: bool = False, expanded: bool = False):
    warna = WARNA_STATUS.get(k["status"], "#94a3b8")
    pr = k.get("prioritas", "normal")
    H(
        f"""
        <div class="tcard" style="--c:{warna}">
          <div class="top"><span class="kode">{e(k['kode'])}</span><span class="tag p-{e(pr)}">{e(LABEL_PRIORITAS.get(pr, pr))}</span></div>
          <div class="jd">{e(k['judul'])}</div>
          <div class="ft">{avatar(k['agent'])}<span class="tag">{e(AGENTS[k['agent']]['nama'])}</span>
          <span class="tag">{e(LABEL_STATUS[k['status']])}</span><span class="tag">🕓 {e(lalu(k['diubah']))}</span></div>
        </div>
        """
    )
    with st.expander("Detail & percakapan", expanded=expanded):
        st.caption(f"Dipegang {nama_agent(k['agent'])} · dibuat {ke_wib(k['dibuat']).strftime('%d %b %H:%M')} WIB")
        if k["deskripsi"]:
            st.write(k["deskripsi"])
        for m in core.pesan_kartu(k["id"]):
            with st.chat_message(m["pengirim"]):
                st.write(m["teks"])
        if boleh_jawab:
            with st.form(f"{prefix}_jawab_{k['id']}", clear_on_submit=True, border=False):
                teks = st.text_input(
                    "Jawaban kamu" if k["status"] == "nunggu_lu" else "Catatan untuk coba ulang",
                    key=f"{prefix}_t_{k['id']}",
                )
                ok = st.form_submit_button("Kirim jawaban", type="primary")
            if ok and teks.strip():
                with st.spinner("Agent memproses jawabanmu..."):
                    core.jawab_kartu(k["id"], teks)
                st.rerun()
        b1, b2, _ = st.columns([1, 1, 2])
        if k["status"] != "selesai" and b1.button("✔ Tutup", key=f"{prefix}_tt_{k['id']}", use_container_width=True):
            core.tandai_selesai(k["id"])
            st.rerun()
        if b2.button("🗑 Hapus", key=f"{prefix}_hp_{k['id']}", use_container_width=True):
            core.hapus_kartu(k["id"])
            st.rerun()


# ============================================================
# TAB: Dashboard
# ============================================================
with tab_dash:
    H(
        f"""
        <div class="kpis">
          <div class="kpi" style="--c:#4f8cff"><div class="lb">Total kartu<i>🗂️</i></div><div class="v">{stat['total']}</div><div class="s">Seluruh tugas yang pernah dibuat</div></div>
          <div class="kpi" style="--c:#38bdf8"><div class="lb">Sedang berjalan<i>⚙️</i></div><div class="v">{stat['aktif']}</div><div class="s">Dikerjakan / antre di agent</div></div>
          <div class="kpi" style="--c:#fbbf24"><div class="lb">Butuh respons<i>🙋</i></div><div class="v">{stat['menunggu']}</div><div class="s">Menunggu jawabanmu / error</div></div>
          <div class="kpi" style="--c:#34d399"><div class="lb">Selesai<i>✅</i></div><div class="v">{stat['selesai']}</div><div class="s">Tingkat penyelesaian {stat['rasio_selesai']:.0f}%</div></div>
          <div class="kpi" style="--c:#7c5cff"><div class="lb">Rata-rata durasi<i>⏱️</i></div><div class="v" style="font-size:24px;padding-top:4px">{durasi_teks(stat['rata_durasi_detik'])}</div><div class="s">Dari dibuat sampai selesai</div></div>
        </div>
        """
    )

    g1, g2, g3 = st.columns([1.05, 1.25, 1.1], gap="medium")

    with g1.container(border=True):
        H('<div class="ph"><h3>Komposisi status</h3><span>semua kartu</span></div>')
        df_s = pd.DataFrame(
            [{"status": LABEL_STATUS[s], "jumlah": n, "kode": s} for s, n in stat["per_status"].items() if n > 0]
        )
        if df_s.empty or alt is None:
            st.markdown('<div class="empty">Belum ada data.</div>', unsafe_allow_html=True)
        else:
            donut = (
                alt.Chart(df_s)
                .mark_arc(innerRadius=58, outerRadius=95, stroke="#121a30", strokeWidth=2)
                .encode(
                    theta="jumlah:Q",
                    color=alt.Color(
                        "status:N",
                        scale=alt.Scale(
                            domain=list(df_s["status"]),
                            range=[WARNA_STATUS[c] for c in df_s["kode"]],
                        ),
                        legend=alt.Legend(orient="bottom", title=None, labelColor="#c4cde0", columns=3),
                    ),
                    tooltip=["status", "jumlah"],
                )
                .properties(height=250)
                .configure_view(strokeWidth=0)
                .configure(background="transparent")
            )
            st.altair_chart(donut, use_container_width=True)

    with g2.container(border=True):
        H('<div class="ph"><h3>Beban kerja per agent</h3><span>aktif · menunggu · selesai</span></div>')
        rows = []
        for kunci, v in stat["per_agent"].items():
            for jenis, label in (("aktif", "Aktif"), ("menunggu", "Menunggu"), ("selesai", "Selesai")):
                rows.append({"agent": AGENTS[kunci]["nama"], "jenis": label, "jumlah": v[jenis]})
        df_a = pd.DataFrame(rows)
        if df_a["jumlah"].sum() == 0 or alt is None:
            st.markdown('<div class="empty">Belum ada tugas untuk agent mana pun.</div>', unsafe_allow_html=True)
        else:
            bar = (
                alt.Chart(df_a)
                .mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5, size=26)
                .encode(
                    y=alt.Y("agent:N", title=None, axis=alt.Axis(labelColor="#c4cde0", domain=False, ticks=False)),
                    x=alt.X("jumlah:Q", title=None, axis=alt.Axis(labelColor="#8b97b1", gridColor="#1d2845", tickMinStep=1)),
                    color=alt.Color(
                        "jenis:N",
                        scale=alt.Scale(domain=["Aktif", "Menunggu", "Selesai"], range=["#38bdf8", "#fbbf24", "#34d399"]),
                        legend=alt.Legend(orient="bottom", title=None, labelColor="#c4cde0"),
                    ),
                    tooltip=["agent", "jenis", "jumlah"],
                )
                .properties(height=250)
                .configure_view(strokeWidth=0)
                .configure(background="transparent")
            )
            st.altair_chart(bar, use_container_width=True)

    with g3.container(border=True):
        H('<div class="ph"><h3>Tren tugas harian</h3><span>kartu dibuat / hari</span></div>')
        if not stat["per_hari"] or alt is None:
            st.markdown('<div class="empty">Belum ada tren.</div>', unsafe_allow_html=True)
        else:
            df_h = pd.DataFrame({"tanggal": list(stat["per_hari"]), "kartu": list(stat["per_hari"].values())})
            area = (
                alt.Chart(df_h)
                .mark_area(
                    line={"color": "#4f8cff"},
                    color=alt.Gradient(
                        gradient="linear",
                        stops=[alt.GradientStop(color="rgba(79,140,255,.45)", offset=0), alt.GradientStop(color="rgba(79,140,255,0)", offset=1)],
                        x1=1, x2=1, y1=1, y2=0,
                    ),
                    point=alt.OverlayMarkDef(color="#4f8cff", size=50),
                )
                .encode(
                    x=alt.X("tanggal:N", title=None, axis=alt.Axis(labelColor="#8b97b1", labelAngle=0)),
                    y=alt.Y("kartu:Q", title=None, axis=alt.Axis(labelColor="#8b97b1", gridColor="#1d2845", tickMinStep=1)),
                    tooltip=["tanggal", "kartu"],
                )
                .properties(height=250)
                .configure_view(strokeWidth=0)
                .configure(background="transparent")
            )
            st.altair_chart(area, use_container_width=True)

    d1, d2 = st.columns([1.35, 1], gap="medium")
    with d1.container(border=True):
        perlu = [k for k in kartu_semua if k["status"] in ("nunggu_lu", "error")]
        H(f'<div class="ph"><h3>🙋 Perlu perhatian kamu</h3><span>{len(perlu)} kartu</span></div>')
        if not perlu:
            st.markdown('<div class="empty">Semua aman. Tidak ada kartu yang menunggu jawabanmu 🎉</div>', unsafe_allow_html=True)
        for k in perlu[:4]:
            render_kartu(k, "dash", boleh_jawab=True)
    with d2.container(border=True):
        H('<div class="ph"><h3>Aktivitas terbaru</h3><span>live</span></div>')
        pesan_terbaru = core.semua_pesan(8)
        if not pesan_terbaru:
            st.markdown('<div class="empty">Belum ada aktivitas. Kirim tugas pertamamu dari sidebar.</div>', unsafe_allow_html=True)
        for m in reversed(pesan_terbaru):
            kunci = next((k for k, a in AGENTS.items() if a["nama"] == m["pengirim"]), None)
            cuplikan = m["teks"] if len(m["teks"]) < 130 else m["teks"][:127] + "…"
            H(
                f"""
                <div class="feed">{avatar(kunci) if kunci else '<span class="av" style="--c:#7c5cff">' + e(m['pengirim'][:1].upper()) + '</span>'}
                <div><div class="tx"><b>{e(m['pengirim'])}</b> · {e(cuplikan)}</div>
                <div class="mt">KD-{m['kartu_id']:03d} · {e(m['judul'])} · {e(lalu(m['waktu']))}</div></div></div>
                """
            )

# ============================================================
# TAB: Kantor 3D
# ============================================================
with tab_kantor:
    kiri, kanan = st.columns([3.2, 1], gap="medium")
    with kiri:

        @st.fragment(run_every=5)
        def _kantor():
            office.tampilkan()

        _kantor()
        st.caption(
            "Agent duduk di meja saat bekerja, ke area papan kartu saat butuh jawabanmu, dan jalan-jalan saat senggang. "
            "Seret untuk memutar · scroll untuk zoom · klik kanan untuk menggeser."
        )
    with kanan:
        H('<div class="ph"><h3>Status agent</h3><span>real-time</span></div>')
        for kunci, a in AGENTS.items():
            v = stat["per_agent"][kunci]
            if v["menunggu"]:
                chip, teks = "warn", "Menunggu kamu"
            elif v["aktif"]:
                chip, teks = "info", "Sedang bekerja"
            else:
                chip, teks = "ok", "Senggang"
            H(
                f"""
                <div class="tcard" style="--c:{a['warna']}">
                <div class="top"><span style="display:flex;gap:8px;align-items:center">{avatar(kunci)}<b>{e(a['nama'])}</b></span>
                <span class="chip {chip}">{teks}</span></div>
                <div class="jd" style="margin-bottom:2px;font-weight:500;color:#8b97b1;font-size:12px">{e(a['peran'])}</div>
                <div class="ft"><span class="tag">⚙️ {v['aktif']} aktif</span><span class="tag">🙋 {v['menunggu']}</span><span class="tag">✅ {v['selesai']}</span></div>
                </div>
                """
            )
        H('<div class="ph" style="margin-top:12px"><h3>Denah ruangan</h3></div>')
        H(
            """
            <div style="display:flex;gap:6px;flex-wrap:wrap">
            <span class="tag">Ruang HRD</span><span class="tag">Ruang Admin Control</span><span class="tag">Ruang Operation Control</span>
            <span class="tag">Ruang Asset Management</span><span class="tag">Ruang HSE</span><span class="tag">Ruang Server</span>
            <span class="tag">Ruang Meeting</span>
            </div>
            """
        )

# ============================================================
# TAB: Papan kartu (Kanban)
# ============================================================
with tab_papan:
    f1, f2, f3 = st.columns([2, 1.4, 1.4])
    cari = f1.text_input("Cari kartu", placeholder="🔎 Cari judul, kode, atau deskripsi…", label_visibility="collapsed")
    f_agent = f2.multiselect(
        "Agent", list(AGENTS), format_func=lambda k: AGENTS[k]["nama"], placeholder="Semua agent", label_visibility="collapsed"
    )
    f_pri = f3.multiselect(
        "Prioritas", core.PRIORITAS, format_func=lambda p: LABEL_PRIORITAS[p], placeholder="Semua prioritas", label_visibility="collapsed"
    )

    def lolos(k):
        if f_agent and k["agent"] not in f_agent:
            return False
        if f_pri and k.get("prioritas", "normal") not in f_pri:
            return False
        if cari:
            q = cari.lower()
            if q not in f"{k['kode']} {k['judul']} {k['deskripsi']}".lower():
                return False
        return True

    urut = {"urgent": 0, "tinggi": 1, "normal": 2, "rendah": 3}
    tersaring = sorted((k for k in kartu_semua if lolos(k)), key=lambda k: (urut.get(k.get("prioritas", "normal"), 2), -k["id"]))

    if not kartu_semua:
        st.info("Belum ada kartu. Buat kartu pertama lewat sidebar atau gunakan template cepat.")

    kolom = [
        ("🙋 Nunggu lu", ("nunggu_lu",), "#fbbf24", True),
        ("⚠️ Error", ("error",), "#f87171", True),
        ("⚙️ Berjalan", ("antri", "jalan"), "#38bdf8", False),
        ("✅ Selesai", ("selesai",), "#34d399", False),
    ]
    cols = st.columns(4, gap="small")
    for col, (judul_kol, status_kol, warna, jawab) in zip(cols, kolom):
        isi = [k for k in tersaring if k["status"] in status_kol]
        with col:
            H(f'<div class="kol" style="--c:{warna}"><b>{judul_kol}</b><span>{len(isi)}</span></div>')
            if not isi:
                st.markdown('<div class="empty">Kosong</div>', unsafe_allow_html=True)
            for k in isi:
                render_kartu(k, "kb", boleh_jawab=jawab)

# ============================================================
# TAB: Tim agent
# ============================================================
with tab_tim:
    H('<div class="ph"><h3>Tim operasional AI</h3><span>profil, beban kerja, dan penugasan langsung</span></div>')
    cols = st.columns(len(AGENTS) + 1, gap="medium")
    for col, (kunci, a) in zip(cols, AGENTS.items()):
        v = stat["per_agent"][kunci]
        total_a = v["aktif"] + v["menunggu"] + v["selesai"]
        beban = min(100, (v["aktif"] + v["menunggu"]) * 20)
        with col:
            H(
                f"""
                <div class="acard" style="--c:{a['warna']}">
                  <div class="avl">{e(a['nama'][0])}</div>
                  <h4>{e(a['nama'])}</h4><div class="rl">{e(a['peran'])} · {e(a['gender'])}</div>
                  <div class="tg">{e(a['tugas'])}</div>
                  <div style="display:flex;gap:5px;flex-wrap:wrap">{''.join(f'<span class="tag">{e(s)}</span>' for s in a['keahlian'])}</div>
                  <div class="mini"><div><b>{v['aktif']}</b><span>Aktif</span></div><div><b>{v['menunggu']}</b><span>Tunggu</span></div><div><b>{v['selesai']}</b><span>Selesai</span></div></div>
                  <div style="display:flex;justify-content:space-between;font-size:11px;color:#8b97b1;margin-top:12px"><span>Beban kerja</span><span>{beban}% · {total_a} total</span></div>
                  <div class="bar" style="margin-top:6px"><i style="width:{beban}%"></i></div>
                </div>
                """
            )
            with st.popover(f"➕ Beri tugas ke {a['nama']}", use_container_width=True):
                with st.form(f"tim_{kunci}", clear_on_submit=True, border=False):
                    jt = st.text_input("Judul tugas", key=f"tim_j_{kunci}")
                    dt = st.text_area("Detail", height=80, key=f"tim_d_{kunci}")
                    pt = st.selectbox("Prioritas", core.PRIORITAS, index=1, format_func=lambda p: LABEL_PRIORITAS[p], key=f"tim_p_{kunci}")
                    go = st.form_submit_button("Kirim", type="primary", use_container_width=True)
                if go:
                    if jt.strip():
                        kirim_kartu(jt.strip(), dt.strip(), kunci, pt)
                        st.rerun()
                    else:
                        st.error("Judul wajib diisi.")
    with cols[-1]:
        H(
            f"""
            <div class="acard" style="--c:#7c5cff">
              <div class="avl">K</div><h4>{e(office.NAMA_SUPERVISOR)}</h4><div class="rl">Supervisor · manusia</div>
              <div class="tg">Pengambil keputusan akhir. Menjawab kartu "Nunggu lu", menutup kartu, dan menetapkan prioritas.</div>
              <div style="display:flex;gap:5px;flex-wrap:wrap"><span class="tag">Persetujuan</span><span class="tag">Keputusan</span><span class="tag">Eskalasi</span></div>
              <div class="mini"><div><b>{stat['menunggu']}</b><span>Antre</span></div><div><b>{stat['selesai']}</b><span>Ditutup</span></div><div><b>{stat['rasio_selesai']:.0f}%</b><span>Rasio</span></div></div>
            </div>
            """
        )

# ============================================================
# TAB: Aktivitas (chat kantor)
# ============================================================
with tab_aktif:
    a1, a2 = st.columns([1, 2])
    pengirim_pilih = a1.multiselect(
        "Pengirim", ["supervisor", "sistem"] + [a["nama"] for a in AGENTS.values()], placeholder="Semua pengirim", label_visibility="collapsed"
    )
    batas = a2.select_slider("Jumlah pesan", options=[20, 50, 100, 200], value=50, label_visibility="collapsed")
    pesan = [m for m in core.semua_pesan(batas) if not pengirim_pilih or m["pengirim"] in pengirim_pilih]
    if not pesan:
        st.info("Belum ada obrolan.")
    for m in pesan:
        with st.chat_message(m["pengirim"]):
            st.caption(f"KD-{m['kartu_id']:03d} · {m['judul']} · {ke_wib(m['waktu']).strftime('%d %b %H:%M')} WIB · {m['pengirim']}")
            st.write(m["teks"])

# ============================================================
# TAB: Laporan
# ============================================================
with tab_lap:
    H('<div class="ph"><h3>Laporan & ekspor data</h3><span>ringkasan harian, tabel kartu, dan unduhan CSV</span></div>')
    hari_ini = datetime.now(timezone.utc).date().isoformat()
    dibuat_hari_ini = [k for k in kartu_semua if k["dibuat"][:10] == hari_ini]
    selesai_hari_ini = [k for k in dibuat_hari_ini if k["status"] == "selesai"]
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Dibuat hari ini", len(dibuat_hari_ini))
    r2.metric("Selesai hari ini", len(selesai_hari_ini))
    r3.metric("Urgent aktif", sum(1 for k in kartu_semua if k.get("prioritas") == "urgent" and k["status"] != "selesai"))
    r4.metric("Rasio selesai", f"{stat['rasio_selesai']:.0f}%")

    if kartu_semua:
        df = pd.DataFrame(
            [
                {
                    "Kode": k["kode"],
                    "Judul": k["judul"],
                    "Agent": AGENTS[k["agent"]]["nama"],
                    "Status": LABEL_STATUS[k["status"]],
                    "Prioritas": LABEL_PRIORITAS.get(k.get("prioritas", "normal"), "Normal"),
                    "Estafet": k["hop"],
                    "Dibuat (WIB)": ke_wib(k["dibuat"]).strftime("%Y-%m-%d %H:%M"),
                    "Diubah (WIB)": ke_wib(k["diubah"]).strftime("%Y-%m-%d %H:%M"),
                }
                for k in kartu_semua
            ]
        )
        st.dataframe(df, use_container_width=True, hide_index=True, height=360)
        dl1, dl2, _ = st.columns([1, 1, 2])
        dl1.download_button(
            "⬇️ Unduh kartu (CSV)", df.to_csv(index=False).encode("utf-8"), "kartu_kantor_ai.csv", "text/csv", use_container_width=True
        )
        df_p = pd.DataFrame(core.semua_pesan(1000))
        if not df_p.empty:
            dl2.download_button(
                "⬇️ Unduh percakapan (CSV)", df_p.to_csv(index=False).encode("utf-8"), "percakapan_kantor_ai.csv", "text/csv", use_container_width=True
            )
    else:
        st.info("Belum ada data untuk dilaporkan.")

# ============================================================
# TAB: Fitur & roadmap
# ============================================================
with tab_fitur:
    H('<div class="ph"><h3>Katalog fitur</h3><span>yang sudah aktif dan ide pengembangan berikutnya</span></div>')
    FITUR = [
        ("🏢", "Simulasi kantor 3D", "Denah WebGL dengan agent yang berjalan, duduk, dan melambai sesuai status kartu.", "Aktif"),
        ("📋", "Papan kartu & filter", "Kanban 4 kolom dengan pencarian, filter agent/prioritas, dan penutupan manual.", "Aktif"),
        ("⚡", "Template tugas cepat", "Satu klik membuat tugas rutin: absensi, manpower, laporan harian, dokumen, antrean picking.", "Aktif"),
        ("📊", "Dashboard & grafik", "KPI, komposisi status, beban kerja per agent, dan tren harian.", "Aktif"),
        ("🔁", "Estafet antar agent", "Agent menyerahkan tugas ke rekan yang tepat dengan batas anti-looping.", "Aktif"),
        ("📑", "Ekspor laporan CSV", "Unduh kartu dan percakapan untuk dianalisis di Excel atau BI.", "Aktif"),
        ("📅", "Penjadwalan shift", "Atur shift, rotasi, dan kebutuhan manpower otomatis oleh Regita (HRD).", "Segera"),
        ("📦", "Pelacak inbound / outbound", "Pantau truk, dock, dan status bongkar muat secara real-time.", "Segera"),
        ("🧮", "Stok & slot rak", "Ringkasan stok, selisih opname, dan rekomendasi penataan slot.", "Segera"),
        ("🎯", "KPI scorecard", "Papan skor produktivitas, akurasi picking, dan on-time delivery.", "Segera"),
        ("🔔", "Notifikasi WhatsApp / Telegram", "Kirim peringatan kartu urgent langsung ke ponsel supervisor.", "Ide"),
        ("⏰", "SLA & eskalasi otomatis", "Kartu yang menggantung terlalu lama otomatis naik prioritas dan dieskalasi.", "Ide"),
        ("🎙️", "Perintah suara", "Beri tugas ke agent dengan bicara, lengkap dengan transkrip otomatis.", "Ide"),
        ("🗓️", "Rapat pagi otomatis", "Agent menyusun briefing harian dan notulen di Ruang Meeting 3D.", "Ide"),
        ("🔗", "Integrasi WMS / ERP", "Hubungkan data nyata agar jawaban agent berbasis angka operasional.", "Ide"),
        ("🛡️", "Peran & hak akses", "Login multi-pengguna dengan peran supervisor, manajer, dan viewer.", "Ide"),
        ("🧾", "Audit log", "Riwayat lengkap siapa mengubah apa, kapan, dan mengapa.", "Ide"),
        ("🗺️", "Heatmap produktivitas", "Peta panas aktivitas per zona gudang pada tampilan 3D.", "Ide"),
    ]
    kelas = {"Aktif": "ok", "Segera": "info", "Ide": "warn"}
    filter_fitur = st.radio("Tampilkan", ["Semua", "Aktif", "Segera", "Ide"], horizontal=True, label_visibility="collapsed")
    daftar = [f for f in FITUR if filter_fitur in ("Semua", f[3])]
    for baris in range(0, len(daftar), 3):
        cs = st.columns(3, gap="medium")
        for c, (ik, jd, ds, st_) in zip(cs, daftar[baris : baris + 3]):
            with c:
                H(
                    f"""
                    <div class="fcard"><div style="display:flex;justify-content:space-between;align-items:flex-start">
                    <span class="ic">{ik}</span><span class="chip {kelas[st_]}">{st_}</span></div>
                    <h5>{e(jd)}</h5><p>{e(ds)}</p></div>
                    """
                )
        st.write("")

# ============================================================
# TAB: Pengaturan
# ============================================================
with tab_set:
    H('<div class="ph"><h3>Pengaturan & informasi sistem</h3><span>konfigurasi saat ini</span></div>')
    s1, s2 = st.columns(2, gap="medium")
    with s1.container(border=True):
        st.markdown("**Koneksi AI**")
        st.write(f"Status API: {'✅ Terhubung' if API_OK else '❌ GROQ_API_KEY belum diisi'}")
        st.write("Urutan model yang dicoba:")
        for i, m in enumerate(MODELS, 1):
            st.code(f"{i}. {m}", language=None)
        st.caption("Ganti model utama lewat Secrets: GROQ_MODEL = \"nama-model\"")
    with s2.container(border=True):
        st.markdown("**Data & pemeliharaan**")
        st.write(f"Database: `{core.DB_PATH}`")
        st.write(f"Batas estafet antar agent: {core.MAKS_SERAH}")
        n_selesai = stat["selesai"]
        konfirm = st.checkbox("Saya paham, kartu selesai akan dihapus permanen", key="konfirm_bersih")
        if st.button(
            f"🧹 Hapus {n_selesai} kartu selesai", disabled=not (konfirm and n_selesai), use_container_width=True
        ):
            for k in kartu_semua:
                if k["status"] == "selesai":
                    core.hapus_kartu(k["id"])
            st.rerun()
        st.caption("Di Streamlit Cloud, file database dapat hilang saat aplikasi di-restart. Unduh CSV di tab Laporan untuk cadangan.")
