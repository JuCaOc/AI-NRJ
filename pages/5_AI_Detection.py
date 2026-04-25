"""Page 5 — Détection IA : anomalies, scoring criticité, recommandations, chatbot."""

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Détection IA | AI Energy CR",
    page_icon="🤖",
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
)

inject_custom_css()
render_sidebar()

# ─────────────────────────────────────────────────────────────
# Placeholder data
# ─────────────────────────────────────────────────────────────

_ANOMALIES = pd.DataFrame({
    "Score":       [88, 62, 34],
    "Priorité":    ["🔴 CRITIQUE", "🟠 ÉLEVÉE", "🟡 MOYENNE"],
    "Système":     ["Air 7 bars", "Électricité", "Eau recyclée"],
    "Équipement":  ["C715 → réseau", "15 kV bus A", "Circuit primaire"],
    "Anomalie":    ["Chute pression progressive", "Tension sous-consigne", "Conductivité ↑"],
    "Valeur obs.": ["6.4 bar", "14.2 kV", "620 µS/cm"],
    "Valeur att.": ["≥ 7.0 bar", "15.0 ±0.3 kV", "< 500 µS/cm"],
    "Règle":       ["PRESS_7BAR_LOW", "VOLT_15KV_LOW", "COND_HIGH"],
    "Depuis":      ["00:23", "01:15", "03:42"],
})

_RECOMMENDATIONS = pd.DataFrame({
    "Priorité":    ["🔴 URGENT", "🟠 ÉLEVÉE", "🟡 DANS 4H"],
    "Action":      [
        "Vérifier état compresseur C715 — purges + démarrer C716 en secours",
        "Contacter dispatching réseau + réduire charge moteurs non critiques 5,5 kV",
        "Analyser eau de compensation + augmenter fréquence traitement",
    ],
    "Équipement":  ["C715, C716", "15 kV bus A", "Circuit recyclée"],
    "Délai":       ["< 30 min", "< 2 h", "< 4 h"],
    "Économie est.": ["537 000 XPF/j", "250 000 XPF/j", "107 000 XPF/j"],
})


# ─────────────────────────────────────────────────────────────
# Page
# ─────────────────────────────────────────────────────────────

def render() -> None:
    render_header(
        title="Détection & Analyse IA",
        subtitle="Anomalies détectées · Scoring de criticité · Recommandations · Assistant industriel",
        icon="🤖",
    )
    render_info_banner(
        "Détection <strong>rule-based explicable</strong> — chaque anomalie est associée à la règle métier qui l'a déclenchée. "
        "L'IA ne pilote jamais directement ; toute action requiert validation humaine."
    )

    # ── KPIs ──────────────────────────────────────────────────
    render_section_title("Tableau de bord détection", "📊")
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi_card("Anomalies actives",     "3",       "",        delta="+2 vs hier",   status="warning")
    with k2:
        render_kpi_card("Niveau critique",        "1",       "",        status="critical")
    with k3:
        render_kpi_card("Score moyen criticité",  "61",      "/ 100",   status="warning")
    with k4:
        render_kpi_card("Exposition financière",  "895 000",   "XPF/j",  status="alert")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Anomalies ─────────────────────────────────────────────
    render_section_title("Anomalies actives — priorisées par score", "🚨")
    st.dataframe(_ANOMALIES, use_container_width=True, hide_index=True)

    # ── Score évolution ────────────────────────────────────────
    render_section_title("Évolution du score de criticité global (24 h)", "📈")
    fig = placeholder_timeseries(
        "Score criticité global (/100)",
        y_label="Score",
        n_series=3,
        height=240,
        seed=60,
    )
    fig.data[0].name = "Air 7 bars"
    fig.data[1].name = "Électricité"
    fig.data[2].name = "Eau recyclée"
    fig.add_hline(y=70, line_dash="dot", line_color="#FF6D00", line_width=1,
                  annotation_text="Seuil alerte", annotation_font_color="#FF6D00")
    fig.add_hline(y=85, line_dash="dot", line_color="#D50000", line_width=1,
                  annotation_text="Seuil critique", annotation_font_color="#D50000")
    fig.update_layout(legend=dict(
        orientation="h", y=1.08, xanchor="right", x=1, bgcolor="rgba(0,0,0,0)",
    ))
    st.plotly_chart(fig, use_container_width=True)

    # ── Recommandations ───────────────────────────────────────
    render_section_title("Recommandations IA", "💡")
    st.dataframe(_RECOMMENDATIONS, use_container_width=True, hide_index=True)
    st.caption("⚠️ Ces recommandations sont indicatives. Toute intervention requiert validation par l'opérateur qualifié.")

    # ── Chatbot ───────────────────────────────────────────────
    render_section_title("Assistant industriel IA", "💬")
    col_chat, col_prompts = st.columns([2, 1])

    with col_chat:
        render_placeholder("Chatbot industriel — sera connecté au module ai_assistant.py (Claude API)")
        st.markdown("""
<div style='background:#161A23;border:1px solid #2A2F3E;border-radius:6px;padding:16px;margin-top:8px;'>
<p style='color:#6B7894;font-size:12px;margin:0 0 8px 0;'>Exemple de réponse attendue :</p>
<p style='color:#DDE3F0;font-size:13px;margin:0;'>
<em>« La pression du réseau 7 bars est à 6,4 bar depuis 23 minutes,
soit 0,6 bar en dessous de la consigne nominale. Le compresseur C715
présente un débit anormalement bas (720 Nm³/h vs 1 200 nominal),
suggérant une dégradation de ses aubes ou un problème de régulation.
C716 est à l'arrêt. Je recommande de démarrer C716 en secours
et de vérifier les purges de C715 en priorité. »</em>
</p>
</div>
""", unsafe_allow_html=True)

    with col_prompts:
        st.markdown(
            '<div class="kpi-card info" style="margin-bottom:8px;">'
            '<div class="kpi-label">Questions rapides</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        quick_prompts = [
            "Résume la situation actuelle",
            "Anomalie la plus critique ?",
            "Actions prioritaires ?",
            "Impact financier total ?",
            "Expliquer le réseau 7 bars",
        ]
        for qp in quick_prompts:
            st.button(qp, use_container_width=True, disabled=True)
        st.caption("Boutons actifs après connexion Claude API")


render()
