"""Page 1 — Vue Globale : statut temps-réel de tous les systèmes."""

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Vue Globale | AI Energy CR",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

from modules.ui_components import (
    inject_custom_css,
    render_sidebar,
    render_header,
    render_kpi_card,
    render_status_badge,
    render_section_title,
    render_info_banner,
    placeholder_timeseries,
)

inject_custom_css()
render_sidebar()

# ─────────────────────────────────────────────────────────────
# Placeholder data
# ─────────────────────────────────────────────────────────────

_ALERTS_DF = pd.DataFrame({
    "Priorité": ["🔴 Critique", "🟠 Élevée", "🟡 Moyenne"],
    "Système":  ["Air 7 bars",  "Électricité", "Eau recyclée"],
    "Équipement": ["C715",      "15 kV bus A", "Circuit primaire"],
    "Description": [
        "Pression réseau en baisse progressive",
        "Tension légèrement sous la consigne",
        "Conductivité en hausse",
    ],
    "Depuis":   ["00:23", "01:15", "03:42"],
})

_SYSTEMS_STATUS = [
    ("⚡", "Électricité",  "normal",  "87.4 MW",   "Charge nominale"),
    ("💨", "Air 7 bars",   "alert",   "6.4 bar",   "Pression basse"),
    ("💨", "Air 3 bars",   "warning", "2.85 bar",  "1 fixe actif"),
    ("♻️", "Eau recyclée", "ok",      "850 m³/h",  "Nominal"),
    ("💧", "Eau brute",    "ok",      "B0 68%",    "Nominal"),
]


# ─────────────────────────────────────────────────────────────
# Page
# ─────────────────────────────────────────────────────────────

def render() -> None:
    render_header(
        title="Vue Globale",
        subtitle="Statut temps-réel de l'ensemble des systèmes utilities",
        icon="🏭",
    )
    render_info_banner(
        "Module de détection non encore connecté · "
        "Les données et alertes ci-dessous sont <strong>simulées</strong>."
    )

    # ── KPIs globaux ──────────────────────────────────────────
    render_section_title("Indicateurs globaux", "📊")
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi_card("Statut global",       "ALERTE",   "",       status="alert")
    with k2:
        render_kpi_card("Anomalies actives",   "3",        "",       delta="▲ 2 vs hier", status="warning")
    with k3:
        render_kpi_card("Efficacité énergie",  "87",       "%",      delta="-4 %",         status="warning")
    with k4:
        render_kpi_card("Exposition finan.",   "1 480 000",   "XPF/j", delta="+382 000",       status="warning")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Statut par système ────────────────────────────────────
    render_section_title("Statut par système", "🏭")
    sys_cols = st.columns(5)
    for col, (icon, name, status, value, note) in zip(sys_cols, _SYSTEMS_STATUS):
        with col:
            badge = render_status_badge(status)
            st.markdown(
                f'<div class="kpi-card {status}" style="text-align:center;">'
                f'  <div style="font-size:22px">{icon}</div>'
                f'  <div class="kpi-label" style="margin-top:6px">{name}</div>'
                f'  <div class="kpi-value" style="font-size:16px">{value}</div>'
                f'  <div style="margin-top:6px">{badge}</div>'
                f'  <div style="font-size:10px;color:#6B7894;margin-top:4px">{note}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Courbes 24 h ──────────────────────────────────────────
    render_section_title("Tendances 24 h — charge relative tous systèmes", "📈")
    fig = placeholder_timeseries(
        "Charge relative (%)",
        y_label="%",
        n_series=4,
        height=270,
        seed=1,
    )
    _names = ["Électricité", "Air 7 bars", "Eau recyclée", "Eau brute"]
    for i, name in enumerate(_names):
        fig.data[i].name = name
    fig.update_layout(legend=dict(
        orientation="h", y=1.08, xanchor="right", x=1, bgcolor="rgba(0,0,0,0)",
    ))
    st.plotly_chart(fig, use_container_width=True)

    # ── Alertes actives ───────────────────────────────────────
    render_section_title("Alertes actives", "🚨")
    st.dataframe(
        _ALERTS_DF,
        use_container_width=True,
        hide_index=True,
    )
    st.caption("➡️ Voir la page **Détection IA** pour l'analyse complète et les recommandations.")


render()
