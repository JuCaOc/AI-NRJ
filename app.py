"""
AI Energy & Utilities Control Room — page d'accueil.
"""

import streamlit as st

st.set_page_config(
    page_title="AI Energy Control Room",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

from modules.ui_components import (
    inject_custom_css,
    render_sidebar,
    render_header,
    render_status_badge,
    render_section_title,
    render_info_banner,
    placeholder_timeseries,
)

inject_custom_css()
render_sidebar()

# ─────────────────────────────────────────────────────────────
# Données de démonstration (home uniquement)
# ─────────────────────────────────────────────────────────────

_SYSTEMS = [
    ("⚡", "Électricité",    "63 kV · 15 kV · 5,5 kV · 400 V",            "normal",   "2_Electricity"),
    ("💨", "Air Comprimé",   "7 bars (instrumentation) · 3 bars (transport)", "warning",  "3_Compressed_Air"),
    ("♻️", "Eau Recyclée",   "Refroidissement · Tours aéro · Légionelle",   "ok",       "4_Water"),
    ("💧", "Eau Brute",      "Bassins B0 & B1 · Appoint · Secours",         "ok",       "4_Water"),
]

_PAGES = [
    ("🏭", "Vue Globale",          "Statut temps-réel de toute l'usine"),
    ("⚡", "Électricité",          "Filière 63 kV → 400 V"),
    ("💨", "Air Comprimé",         "Réseaux 7 bars et 3 bars"),
    ("💧", "Eau",                  "Recyclée & brute"),
    ("🤖", "Détection IA",         "Anomalies · Scores · Chatbot"),
    ("🔬", "Simulation",           "What-if · Avant / Après"),
    ("📊", "Rapport IA",           "Synthèse exportable PDF"),
]

# ─────────────────────────────────────────────────────────────
# Hero
# ─────────────────────────────────────────────────────────────

render_header(
    title="AI Energy & Utilities Control Room",
    subtitle="Supervision industrielle augmentée par l'IA — prototype de démonstration pédagogique",
    icon="⚡",
)

render_info_banner(
    "Toutes les données sont <strong>simulées</strong> avec un seed fixe pour la reproductibilité. "
    "Aucune connexion SCADA réelle n'est établie."
)

col_desc, col_badge = st.columns([3, 1])
with col_desc:
    st.markdown("""
Cette application illustre comment une IA peut **superviser une usine**, **détecter des anomalies**,
**expliquer les causes** et **proposer des actions correctives** avec estimation de l'impact économique.

> Utilisez le menu **←** pour naviguer entre les systèmes.
""")
with col_badge:
    st.markdown(render_status_badge("warning", "MODE DÉMO"), unsafe_allow_html=True)
    st.caption("Données simulées · Seed 42")

# ─────────────────────────────────────────────────────────────
# Systèmes supervisés
# ─────────────────────────────────────────────────────────────

render_section_title("Systèmes supervisés", "🏭")

cols = st.columns(4)
for col, (icon, name, desc, status, _) in zip(cols, _SYSTEMS):
    with col:
        badge = render_status_badge(status)
        st.markdown(
            f'<div class="sys-tile">'
            f'  <div class="sys-tile-icon">{icon}</div>'
            f'  <div class="sys-tile-name">{name}</div>'
            f'  <div class="sys-tile-desc">{desc}</div>'
            f'  {badge}'
            f'</div>',
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# Valeur ajoutée IA + aperçu graphique
# ─────────────────────────────────────────────────────────────

col_left, col_right = st.columns([1, 2])

with col_left:
    render_section_title("Valeur ajoutée de l'IA", "🎯")
    st.markdown("""
**Sans IA**
- Courbes brutes sans contexte
- Alertes binaires seuil / hors-seuil
- Réaction après dégradation visible
- Pas d'estimation d'impact

**Avec IA**
- Détection précoce avec explication
- Scoring de criticité multi-critères
- Recommandations priorisées
- Estimation financière par anomalie
""")

with col_right:
    render_section_title("Aperçu — 24 h de données simulées", "📈")
    fig = placeholder_timeseries(
        "Charge relative des 4 systèmes (%)",
        y_label="%",
        n_series=4,
        height=270,
        seed=42,
    )
    _names = ["Électricité", "Air 7 bars", "Eau recyclée", "Eau brute"]
    for i, name in enumerate(_names):
        fig.data[i].name = name
    fig.update_layout(
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1, bgcolor="rgba(0,0,0,0)",
        )
    )
    st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────────────────────────────────────────
# Guide de navigation
# ─────────────────────────────────────────────────────────────

render_section_title("Pages disponibles", "🗺️")

nav_cols = st.columns(len(_PAGES))
for col, (icon, page_name, page_desc) in zip(nav_cols, _PAGES):
    with col:
        st.markdown(
            f'<div class="kpi-card normal" style="text-align:center;min-height:80px;">'
            f'  <div style="font-size:20px;">{icon}</div>'
            f'  <div class="kpi-label" style="margin-top:6px;">{page_name}</div>'
            f'  <div style="font-size:10px;color:#3A4258;">{page_desc}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
