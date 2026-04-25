"""Page 4 — Supervision Eau : eau recyclée (refroidissement) et eau brute (bassins B0/B1)."""

import streamlit as st

st.set_page_config(
    page_title="Eau | AI Energy CR",
    page_icon="💧",
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


def render() -> None:
    render_header(
        title="Supervision Eau",
        subtitle="Eau recyclée (refroidissement fours · tours aéro · légionelle) · Eau brute (bassins B0 & B1)",
        icon="💧",
    )
    render_info_banner(
        "L'eau recyclée est critique pour la <strong>thermique procédé</strong> et la "
        "<strong>sécurité sanitaire</strong> (légionelle). "
        "L'eau brute (B0 & B1) constitue le secours de refroidissement."
    )

    # ── KPIs ──────────────────────────────────────────────────
    render_section_title("Indicateurs clés", "📊")
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi_card("Débit eau recyclée",  "850",  "m³/h",  delta="+12",     status="ok")
    with k2:
        render_kpi_card("Température circuit", "28.4", "°C",    delta="+1.2 °C", status="normal")
    with k3:
        render_kpi_card("Niveau bassin B0",    "68",   "%",     status="ok")
    with k4:
        render_kpi_card("Niveau bassin B1",    "31",   "%",     delta="-18 %",   status="warning")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Eau recyclée — courbes ─────────────────────────────────
    render_section_title("Eau recyclée — tendances 24 h", "♻️")
    c1, c2 = st.columns(2)
    with c1:
        fig_t = placeholder_timeseries(
            "Température eau recyclée (°C)",
            y_label="°C",
            n_series=1,
            height=250,
            seed=40,
        )
        fig_t.add_hline(y=35, line_dash="dot", line_color="#FF6D00", line_width=1.5,
                        annotation_text="Seuil alerte 35 °C", annotation_position="top right",
                        annotation_font_color="#FF6D00")
        fig_t.update_yaxes(range=[15, 42])
        fig_t.data[0].name = "Température"
        st.plotly_chart(fig_t, use_container_width=True)
    with c2:
        fig_d = placeholder_timeseries(
            "Débit eau recyclée (m³/h)",
            y_label="m³/h",
            n_series=1,
            height=250,
            seed=41,
        )
        fig_d.update_yaxes(range=[600, 1_100])
        fig_d.data[0].name = "Débit"
        st.plotly_chart(fig_d, use_container_width=True)

    # ── Qualité eau recyclée ──────────────────────────────────
    render_section_title("Qualité eau recyclée", "🔬")
    q1, q2, q3, q4 = st.columns(4)
    with q1:
        st.plotly_chart(
            placeholder_gauge("pH", 7.6, 0, 14, "", 200, warn_threshold=8.5),
            use_container_width=True,
        )
    with q2:
        st.plotly_chart(
            placeholder_gauge("Conductivité (µS/cm)", 620, 0, 1_200, "µS/cm", 200, warn_threshold=800),
            use_container_width=True,
        )
    with q3:
        st.plotly_chart(
            placeholder_gauge("Turbidité (NTU)", 4.2, 0, 20, "NTU", 200, warn_threshold=10),
            use_container_width=True,
        )
    with q4:
        st.plotly_chart(
            placeholder_gauge("Score risque légionelle", 18, 0, 100, "/100", 200, warn_threshold=50),
            use_container_width=True,
        )

    # ── Eau brute — bassins ────────────────────────────────────
    render_section_title("Eau brute — Bassins B0 et B1", "💧")
    b1, b2, b3 = st.columns([1, 1, 2])
    with b1:
        st.plotly_chart(
            placeholder_gauge("Bassin B0 — Niveau", 68, 0, 100, "%", 240, warn_threshold=20),
            use_container_width=True,
        )
    with b2:
        st.plotly_chart(
            placeholder_gauge("Bassin B1 — Niveau", 31, 0, 100, "%", 240, warn_threshold=20),
            use_container_width=True,
        )
    with b3:
        fig_b = placeholder_timeseries(
            "Niveaux bassins 24 h (%)",
            y_label="%",
            n_series=2,
            height=240,
            seed=50,
        )
        fig_b.data[0].name = "B0"
        fig_b.data[1].name = "B1"
        fig_b.add_hline(y=20, line_dash="dot", line_color="#D50000", line_width=1,
                        annotation_text="Seuil critique 20 %", annotation_font_color="#D50000")
        st.plotly_chart(fig_b, use_container_width=True)

    st.warning(
        "**Bassin B1 à 31 %** — niveau en baisse continue depuis 6 h. "
        "Vérifier débit d'appoint et consommation secours.",
        icon="⚠️",
    )


render()
