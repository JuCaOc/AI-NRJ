"""Page 2 — Supervision Électricité : filière 63 kV → 15 kV → 5,5 kV / 400 V."""

import streamlit as st

st.set_page_config(
    page_title="Électricité | AI Energy CR",
    page_icon="⚡",
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
        title="Supervision Électricité",
        subtitle="Filière 63 kV (poste source) → 15 kV (force motrice) → 5,5 kV / 400 V",
        icon="⚡",
    )
    render_info_banner(
        "Règle énergétique : <strong>63 kV → 15 kV → sous-stations → 5,5 kV / 400 V</strong>. "
        "Sources : réseau externe + centrale interne CAT."
    )

    # ── KPIs ──────────────────────────────────────────────────
    render_section_title("Indicateurs clés", "📊")
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi_card("Puissance 63 kV",       "87.4",  "MW",  delta="+2.1",     status="normal")
    with k2:
        render_kpi_card("Tension 15 kV",          "14.8",  "kV",  delta="-0.2 kV",  status="warning")
    with k3:
        render_kpi_card("Charge sous-stations",   "72",    "%",   delta="+5 %",     status="normal")
    with k4:
        render_kpi_card("Consommation 400 V",     "3.2",   "MW",  status="ok")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Courbes puissance & tension ────────────────────────────
    render_section_title("Tendances 24 h", "📈")
    c_left, c_right = st.columns(2)
    with c_left:
        fig1 = placeholder_timeseries(
            "Puissance active 63 kV (MW)",
            y_label="MW",
            n_series=2,
            height=250,
            seed=10,
        )
        fig1.data[0].name = "Réseau externe"
        fig1.data[1].name = "Centrale CAT"
        st.plotly_chart(fig1, use_container_width=True)
    with c_right:
        fig2 = placeholder_timeseries(
            "Tension 15 kV — écart à la consigne (%)",
            y_label="Écart %",
            n_series=1,
            height=250,
            seed=20,
        )
        fig2.data[0].name = "Écart tension"
        # Reference line at 0
        fig2.add_hline(y=0, line_dash="dash", line_color="#6B7894", line_width=1)
        fig2.add_hline(y=-5, line_dash="dot", line_color="#FFB300", line_width=1,
                       annotation_text="Seuil bas", annotation_position="bottom right")
        st.plotly_chart(fig2, use_container_width=True)

    # ── Charge transformateurs ────────────────────────────────
    render_section_title("Charge transformateurs", "🔧")
    g1, g2, g3, g4 = st.columns(4)
    gauges = [
        ("TR-A  63→15 kV",  72,  0, 100, "%"),
        ("TR-B  15→5,5 kV", 81,  0, 100, "%"),
        ("TR-C  15→400 V",  58,  0, 100, "%"),
        ("TR-D  15→400 V",  64,  0, 100, "%"),
    ]
    for col, (title, val, mn, mx, unit) in zip([g1, g2, g3, g4], gauges):
        with col:
            st.plotly_chart(
                placeholder_gauge(title, val, mn, mx, unit, height=200),
                use_container_width=True,
            )

    # ── Hiérarchie réseau ──────────────────────────────────────
    render_section_title("Hiérarchie du réseau électrique", "🔌")
    st.markdown("""
| Niveau | Rôle | Alimente |
|--------|------|----------|
| **63 kV** — Poste source | Réception réseau externe + CAT | Fours (direct) · Poste 15 kV |
| **15 kV** — Force motrice | Distribution inter-sous-stations | Sous-stations |
| **5,5 kV** | Gros moteurs | Compresseurs · Pompes eau salée · Pompes MPC |
| **400 V** | Auxiliaires | Moteurs secondaires · Éclairage · Contrôle |
""")

    badge_ok  = render_status_badge("ok",      "NOMINAL")
    badge_war = render_status_badge("warning", "ATTENTION")
    st.markdown(f"63 kV : {badge_ok}  &nbsp;&nbsp;  15 kV : {badge_war}  &nbsp;&nbsp;  5,5 kV : {badge_ok}  &nbsp;&nbsp;  400 V : {badge_ok}", unsafe_allow_html=True)


render()
