"""
AI Energy & Utilities Control Room — Page d'accueil
"""

import streamlit as st
from modules.ui_components import (
    PAGE_CONFIG, inject_custom_css, render_scenario_sidebar,
    render_kpi_card, render_section_title,
    render_status_badge, score_to_status, plant_status_css,
    fmt_xpf, STATUS_COLORS, SEVERITY_COLORS,
)
from modules.state_manager import ensure_state

st.set_page_config(**PAGE_CONFIG)
inject_custom_css()
ensure_state()
render_scenario_sidebar()

ss = st.session_state
scoring   = ss.get("scoring_summary", {})
biz       = ss.get("business_summary", {})
anomalies = ss.get("anomalies", [])

# ── Header ────────────────────────────────────────────────────────────────────
g_score  = scoring.get("global_score", 0.0)
g_status = scoring.get("status", "NORMAL")
s_css    = plant_status_css(g_status)
s_color  = STATUS_COLORS.get(s_css, "#00C853")

st.markdown(
    f'<div style="background:linear-gradient(135deg,#0D1017 0%,#111827 100%);'
    f'border:1px solid #2A2F3E;border-radius:10px;padding:26px 30px;margin-bottom:18px;">'
    f'<div style="font-size:26px;font-weight:700;color:#DDE3F0;margin-bottom:5px;">'
    f'⚡ AI Energy & Utilities Control Room</div>'
    f'<div style="font-size:13px;color:#6B7894;margin-bottom:14px;">'
    f'Supervision industrielle augmentée par intelligence artificielle</div>'
    f'<div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap;">'
    f'<div style="background:rgba(0,0,0,.3);border:1px solid #2A2F3E;border-radius:5px;'
    f'padding:7px 16px;font-size:12px;color:{s_color};font-weight:700;">'
    f'Statut usine : {g_status}</div>'
    f'<div style="font-size:12px;color:#6B7894;">Score : '
    f'<span style="color:{s_color};font-weight:700;">{g_score:.0f} / 100</span></div>'
    f'<div style="font-size:12px;color:#6B7894;">Anomalies actives : '
    f'<span style="color:{"#FF6D00" if anomalies else "#00C853"};font-weight:700;">'
    f'{len(anomalies)}</span></div>'
    f'</div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── KPIs ──────────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
n_critical = sum(1 for a in anomalies if a.get("severity") == "critical")
total_loss = biz.get("total_loss_xpf", 0.0)
savings    = biz.get("estimated_savings_xpf", 0.0)

with c1:
    render_kpi_card("Score criticité", f"{g_score:.0f}", "/ 100", status=s_css)
with c2:
    render_kpi_card(
        "Anomalies actives", str(len(anomalies)), "",
        delta=f"+{n_critical} critiques" if n_critical else None,
        status="critical" if n_critical else ("alert" if anomalies else "ok"),
    )
with c3:
    render_kpi_card(
        "Perte estimée", fmt_xpf(total_loss), "XPF",
        status="alert" if total_loss > 500_000 else ("warning" if total_loss > 0 else "ok"),
    )
with c4:
    render_kpi_card("Économies potentielles", fmt_xpf(savings), "XPF",
                    status="ok" if savings > 0 else "normal")

# ── Phrase clé ────────────────────────────────────────────────────────────────
st.markdown(
    '<div style="background:rgba(0,176,255,.06);border:1px solid rgba(0,176,255,.2);'
    'border-radius:6px;padding:14px 20px;margin:16px 0;text-align:center;'
    'font-size:15px;font-style:italic;color:#00B0FF;">'
    '"Le SCADA montre ce qui se passe. L\'IA explique pourquoi et quoi faire."'
    '</div>',
    unsafe_allow_html=True,
)

# ── Tuiles systèmes ───────────────────────────────────────────────────────────
render_section_title("Systèmes supervisés", "🏭")
domain_scores = scoring.get("domain_scores", {})
tiles = [
    ("⚡", "Électricité",    "Fours 63 kV · CAT · 15 kV",         domain_scores.get("electricity_score", 0.0)),
    ("💨", "Air 7 bars",    "Compresseurs C713–C717 · Process",    domain_scores.get("air_score", 0.0)),
    ("💨", "Air 3 bars",    "VSD C321–C323 · Transport",           domain_scores.get("air_score", 0.0)),
    ("♻️", "Eau recyclée",  "Refroidissement · Légionelle",        domain_scores.get("water_score", 0.0)),
    ("💧", "Eau brute",     "Bassins B0/B1 · Appoint",             domain_scores.get("water_score", 0.0)),
]
for col, (icon, name, desc, score) in zip(st.columns(5), tiles):
    c2 = STATUS_COLORS.get(score_to_status(score), "#00C853")
    with col:
        st.markdown(
            f'<div class="sys-tile" style="border-top:2px solid {c2};">'
            f'<div class="sys-tile-icon">{icon}</div>'
            f'<div class="sys-tile-name">{name}</div>'
            f'<div class="sys-tile-desc">{desc}</div>'
            f'<div style="font-size:22px;font-weight:700;color:{c2};'
            f'font-family:Courier New,monospace;">{score:.0f}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ── Top risques ───────────────────────────────────────────────────────────────
if anomalies:
    render_section_title("Top risques actifs", "🚨")
    top = sorted(anomalies, key=lambda a: a.get("confidence_score", 0), reverse=True)[:5]
    for a in top:
        sc = SEVERITY_COLORS.get(a.get("severity", "low"), "#6B7894")
        st.markdown(
            f'<div style="background:#161A23;border-left:3px solid {sc};'
            f'border-radius:0 5px 5px 0;padding:10px 14px;margin-bottom:6px;">'
            f'<span style="font-size:13px;font-weight:600;color:#DDE3F0;">{a.get("title","")}</span>'
            f'&nbsp;&nbsp;<span style="font-size:11px;color:#6B7894;">'
            f'{a.get("asset","")}&nbsp;·&nbsp;{a.get("domain","").upper()}</span>'
            f'<span style="float:right;font-size:11px;color:{sc};font-weight:700;">'
            f'{a.get("severity","").upper()}&nbsp;·&nbsp;{a.get("confidence_score",0):.0%}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
else:
    st.success("Aucune anomalie active. Fonctionnement nominal de l'usine.")

# ── Navigation ────────────────────────────────────────────────────────────────
render_section_title("Pages de supervision", "📑")
nav = [
    ("📊", "Vue d'ensemble",  "Tableau de bord global usine"),
    ("⚡", "Électricité",     "63 kV → 15 kV → 5,5 kV / 400 V"),
    ("💨", "Air comprimé",   "Réseaux 7 bars et 3 bars"),
    ("♻️", "Eau",             "Recyclée & brute, bassins"),
    ("🤖", "Détection IA",   "Anomalies, scoring, diagnostic"),
    ("🔬", "Simulation",      "Comparaison nominal vs scénario"),
    ("📄", "Rapport IA",      "Synthèse exportable"),
]
for i, row in enumerate(nav):
    icon, label, desc = row
    with st.columns(4)[i % 4]:
        st.markdown(
            f'<div style="background:#161A23;border:1px solid #2A2F3E;border-radius:6px;'
            f'padding:13px;text-align:center;margin-bottom:8px;">'
            f'<div style="font-size:22px;">{icon}</div>'
            f'<div style="font-size:12px;font-weight:600;color:#DDE3F0;margin:4px 0 2px;">{label}</div>'
            f'<div style="font-size:10px;color:#6B7894;">{desc}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
