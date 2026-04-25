"""Page 6 — Simulateur d'actions correctives : what-if, avant/après, impact financier."""

import streamlit as st

st.set_page_config(
    page_title="Simulation | AI Energy CR",
    page_icon="🔬",
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
    render_placeholder,
    placeholder_timeseries,
    placeholder_gauge,
)

inject_custom_css()
render_sidebar()

# ─────────────────────────────────────────────────────────────
# Placeholder data
# ─────────────────────────────────────────────────────────────

_ACTIONS = {
    "Démarrer C716 (secours 7 bars)":         ("air_7bar",       "HIGH"),
    "Réduire charge moteurs 5,5 kV":           ("electricity_55kv","MEDIUM"),
    "Augmenter traitement eau recyclée":        ("recycled_water",  "MEDIUM"),
    "Basculer C311 → variables 3 bars":         ("air_3bar",        "LOW"),
}


# ─────────────────────────────────────────────────────────────
# Page
# ─────────────────────────────────────────────────────────────

def render() -> None:
    render_header(
        title="Simulateur d'Actions Correctives",
        subtitle="Explorez l'impact d'une action avant de l'appliquer — what-if · avant/après · estimation financière",
        icon="🔬",
    )
    render_info_banner(
        "Ce simulateur <strong>ne pilote pas les équipements réels</strong>. "
        "Il projette l'évolution attendue des métriques pour aider à la décision. "
        "Toute action opérationnelle requiert validation humaine."
    )

    # ── Sélecteur d'action ────────────────────────────────────
    render_section_title("Choisir une action à simuler", "🎯")
    col_sel, col_info = st.columns([2, 1])
    with col_sel:
        action_label = st.selectbox(
            "Action recommandée",
            list(_ACTIONS.keys()),
            help="Sélectionnez une recommandation IA pour visualiser son impact simulé.",
        )
        system, priority = _ACTIONS[action_label]
        badge = render_status_badge(
            "alert" if priority == "HIGH" else "warning" if priority == "MEDIUM" else "normal",
            f"Priorité {priority}",
        )
        st.markdown(f"Système concerné : **{system}** &nbsp;{badge}", unsafe_allow_html=True)

    with col_info:
        render_kpi_card("Économie estimée",  "537 000",  "XPF/j",  status="ok")

    simulate_btn = st.button("▶ Lancer la simulation", type="primary")
    st.markdown("<br>", unsafe_allow_html=True)

    # ── Résultats simulation ──────────────────────────────────
    render_section_title("Résultats — Avant / Après", "📊")

    if simulate_btn:
        st.success("Simulation exécutée (placeholder). Les graphiques ci-dessous représentent la projection.")
    else:
        st.caption("Cliquez sur **▶ Lancer la simulation** pour afficher la projection.")

    col_before, col_after = st.columns(2)
    with col_before:
        st.markdown(
            '<div class="kpi-card alert" style="text-align:center;">'
            '  <div class="kpi-label">AVANT correction</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        k1, k2 = st.columns(2)
        with k1:
            render_kpi_card("Pression 7 bars",       "6.4",  "bar",  status="alert")
            render_kpi_card("Compresseurs actifs",    "3/5",  "",     status="warning")
        with k2:
            render_kpi_card("Débit total",            "2 900","Nm³/h",status="alert")
            render_kpi_card("Coût énergie / h",       "38 000",  "XPF/h",  status="warning")

        fig_b = placeholder_timeseries("Pression réseau 7 bars — état actuel (bar)",
                                       y_label="bar", n_series=1, height=200, seed=70)
        fig_b.add_hline(y=6.5, line_dash="dot", line_color="#FFB300", line_width=1)
        fig_b.update_yaxes(range=[5.5, 8.0])
        st.plotly_chart(fig_b, use_container_width=True)

    with col_after:
        st.markdown(
            '<div class="kpi-card ok" style="text-align:center;">'
            '  <div class="kpi-label">APRÈS correction (projection)</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        k3, k4 = st.columns(2)
        with k3:
            render_kpi_card("Pression 7 bars",       "7.1",  "bar",  status="ok",     delta="+0.7")
            render_kpi_card("Compresseurs actifs",    "4/5",  "",     status="ok",     delta="+1")
        with k4:
            render_kpi_card("Débit total",            "4 000","Nm³/h",status="ok",     delta="+1 100")
            render_kpi_card("Coût énergie / h",       "35 000",  "XPF/h",  status="warning",delta="-3 000")

        fig_a = placeholder_timeseries("Pression réseau 7 bars — après action (bar)",
                                       y_label="bar", n_series=1, height=200, seed=71)
        fig_a.add_hline(y=7.0, line_dash="dash", line_color="#00C853", line_width=1,
                        annotation_text="Consigne 7.0 bar", annotation_font_color="#00C853")
        fig_a.update_yaxes(range=[5.5, 8.0])
        st.plotly_chart(fig_a, use_container_width=True)

    # ── Bilan financier ───────────────────────────────────────
    render_section_title("Bilan financier de l'action", "💰")
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        render_kpi_card("Coût correction",    "21 500",   "XPF",    status="info")
    with f2:
        render_kpi_card("Économie / jour",    "537 000", "XPF",    status="ok",  delta="+537 000")
    with f3:
        render_kpi_card("Retour sur action",  "< 1",   "heure",  status="ok")
    with f4:
        render_kpi_card("Confiance estimation", "Élevée", "",    status="normal")

    st.caption(
        "⚠️ Estimations basées sur les paramètres économiques par défaut "
        "(22 XPF/kWh · 1 790 000 XPF/h arrêt production). Configurable dans business_value.py."
    )

    # ── Procédure ─────────────────────────────────────────────
    render_section_title("Procédure recommandée", "📋")
    render_placeholder("Procédure pas à pas — sera générée par recommendations.py")
    st.markdown("""
**Exemple de procédure attendue :**
1. Vérifier l'état des protections électriques de C716 (5,5 kV)
2. Effectuer le pré-démarrage réglementaire (15 min)
3. Démarrer C716 depuis le pupitre local ou SCADA
4. Surveiller la montée en pression 7 bars (cible : retour > 6,8 bar en < 20 min)
5. Si pression stable, effectuer diagnostic C715 (purges, aubes, régulation)
6. Documenter l'intervention dans le registre de maintenance
""")


render()
