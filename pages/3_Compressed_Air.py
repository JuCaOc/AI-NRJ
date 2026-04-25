"""Page 3 — Supervision Air Comprimé : réseaux 7 bars (instrumentation) et 3 bars (transport)."""

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Air Comprimé | AI Energy CR",
    page_icon="💨",
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
    placeholder_gauge,
)

inject_custom_css()
render_sidebar()

# ─────────────────────────────────────────────────────────────
# Placeholder data
# ─────────────────────────────────────────────────────────────

_C7_STATUS = pd.DataFrame({
    "Compresseur": ["C713", "C714", "C715", "C716", "C717"],
    "État":        ["✅ En service", "✅ En service", "⚠️ Dégradé", "🔴 Arrêté", "✅ En service"],
    "Débit (Nm³/h)": [1_200, 980, 720, 0, 1_100],
    "Pression sortie (bar)": [7.1, 7.0, 6.6, "—", 7.0],
    "Conso. élec. (kW)": [132, 108, 95, 0, 122],
    "Alimentation": ["5,5 kV", "5,5 kV", "5,5 kV", "5,5 kV", "5,5 kV"],
})

_C3_STATUS = pd.DataFrame({
    "Compresseur":  ["C321 (var.)", "C322 (var.)", "C323 (var.)", "C311 (fixe)", "C312 (fixe)"],
    "État":         ["✅ En service", "✅ En service", "🔵 Standby", "⚠️ Actif intempestif", "🔵 Standby"],
    "Débit (Nm³/h)": [650, 480, 0, 320, 0],
    "Type":         ["Variable", "Variable", "Variable", "Fixe", "Fixe"],
})


# ─────────────────────────────────────────────────────────────
# Page
# ─────────────────────────────────────────────────────────────

def render() -> None:
    render_header(
        title="Supervision Air Comprimé",
        subtitle="Réseau 7 bars (instrumentation + barrage) · Réseau 3 bars (transport poussières / charbon)",
        icon="💨",
    )
    render_info_banner(
        "Règle 3 bars : les compresseurs <strong>variables (C321–C323)</strong> absorbent la demande ; "
        "les <strong>fixes (C311–C312)</strong> n'interviennent qu'en complément si insuffisant."
    )

    # ── KPIs ──────────────────────────────────────────────────
    render_section_title("Indicateurs clés", "📊")
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi_card("Pression réseau 7 bars",   "6.4",  "bar",     delta="-0.6",    status="alert")
    with k2:
        render_kpi_card("Compresseurs actifs 7 bars", "3/5", "",        status="warning")
    with k3:
        render_kpi_card("Pression réseau 3 bars",   "2.85", "bar",     status="normal")
    with k4:
        render_kpi_card("Fixe 3 bars actif",        "C311", "↑ ANORMAL", status="warning")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Courbes pression ──────────────────────────────────────
    render_section_title("Tendances pression 24 h", "📈")
    p1, p2 = st.columns(2)
    with p1:
        fig7 = placeholder_timeseries(
            "Pression réseau 7 bars (bar)",
            y_label="bar",
            n_series=1,
            height=250,
            seed=30,
        )
        fig7.add_hline(y=6.5, line_dash="dot", line_color="#FFB300", line_width=1.5,
                       annotation_text="Seuil bas 6.5 bar", annotation_position="bottom right",
                       annotation_font_color="#FFB300")
        fig7.add_hline(y=6.0, line_dash="dot", line_color="#D50000", line_width=1.5,
                       annotation_text="Critique 6.0 bar", annotation_position="bottom right",
                       annotation_font_color="#D50000")
        fig7.update_yaxes(range=[5.5, 8.0])
        fig7.data[0].name = "Pression 7 bars"
        st.plotly_chart(fig7, use_container_width=True)
    with p2:
        fig3 = placeholder_timeseries(
            "Pression réseau 3 bars (bar)",
            y_label="bar",
            n_series=1,
            height=250,
            seed=31,
        )
        fig3.add_hline(y=2.7, line_dash="dot", line_color="#FFB300", line_width=1.5,
                       annotation_text="Seuil bas 2.7 bar", annotation_position="bottom right",
                       annotation_font_color="#FFB300")
        fig3.update_yaxes(range=[2.0, 3.5])
        fig3.data[0].name = "Pression 3 bars"
        st.plotly_chart(fig3, use_container_width=True)

    # ── État compresseurs 7 bars ──────────────────────────────
    render_section_title("Compresseurs 7 bars — C713 à C717", "🔧")
    st.dataframe(_C7_STATUS, use_container_width=True, hide_index=True)

    # ── Jauges débit ─────────────────────────────────────────
    render_section_title("Débit par compresseur 7 bars (Nm³/h)", "💨")
    g_cols = st.columns(5)
    _debits = [1_200, 980, 720, 0, 1_100]
    _names  = ["C713", "C714", "C715", "C716", "C717"]
    for col, name, debit in zip(g_cols, _names, _debits):
        with col:
            st.plotly_chart(
                placeholder_gauge(name, debit, 0, 1_400, "Nm³/h", height=190, warn_threshold=1_200),
                use_container_width=True,
            )

    # ── État compresseurs 3 bars ──────────────────────────────
    render_section_title("Compresseurs 3 bars — C311–C312 (fixes) / C321–C323 (variables)", "⚠️")
    st.dataframe(_C3_STATUS, use_container_width=True, hide_index=True)
    st.warning(
        "**Anomalie détectée** : C311 (fixe) actif alors que les variables C321 + C322 "
        "couvrent 100 % de la demande → consommation inutile estimée à **+320 Nm³/h**.",
        icon="⚠️",
    )


render()
