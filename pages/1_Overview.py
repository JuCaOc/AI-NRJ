"""Page 1 — Vue Globale : statut temps-réel de tous les systèmes."""

import streamlit as st
from modules.ui_components import (
    PAGE_CONFIG, inject_custom_css, render_scenario_sidebar,
    render_header, render_kpi_card, render_section_title, render_info_banner,
    make_timeseries, make_domain_score_bar, render_scada_vs_ia,
    score_to_status, plant_status_css, fmt_xpf, STATUS_COLORS, SEVERITY_COLORS,
)
from modules.state_manager import ensure_state

st.set_page_config(**PAGE_CONFIG)
inject_custom_css()
ensure_state()
render_scenario_sidebar()

ss = st.session_state
df       = ss["df_current"]
df_nom   = ss["df_nominal"]
anomalies = ss.get("anomalies", [])
scoring  = ss.get("scoring_summary", {})
biz      = ss.get("business_summary", {})
recs     = ss.get("recommendations", [])

g_score  = scoring.get("global_score", 0.0)
g_status = scoring.get("status", "NORMAL")
s_css    = plant_status_css(g_status)
s_color  = STATUS_COLORS.get(s_css, "#00C853")

render_header("Vue d'ensemble", "Tableau de bord global usine — 24 h glissantes", "📊")

# ── KPIs ──────────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
n_critical = sum(1 for a in anomalies if a.get("severity") == "critical")
total_loss = biz.get("total_loss_xpf", 0.0)
savings    = biz.get("estimated_savings_xpf", 0.0)
domain_scores = scoring.get("domain_scores", {})

with c1:
    render_kpi_card("Statut global", g_status, "", status=s_css)
with c2:
    render_kpi_card(
        "Anomalies actives", str(len(anomalies)), "",
        delta=f"{n_critical} critiques" if n_critical else None,
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

# ── Bloc pédagogique SCADA vs IA ──────────────────────────────────────────────
render_section_title("SCADA classique vs IA", "🆚")
render_scada_vs_ia(
    scada_points=[
        "Visualise les données en temps réel",
        "Déclenche des alarmes sur seuil fixe",
        "Alarmes isolées par instrument",
        "Analyse après l'incident (post-mortem)",
        "L'opérateur doit interpréter seul",
    ],
    ia_points=[
        "Corrèle les signaux multi-systèmes",
        "Détecte les dérives avant le seuil d'alarme",
        "Produit un diagnostic explicable",
        "Priorise les actions par criticité",
        "Chiffre l'impact financier (XPF)",
        "Propose des recommandations actionnables",
    ],
)

# ── Courbes principales ───────────────────────────────────────────────────────
render_section_title("Tendances 24 h", "📈")

col_left, col_right = st.columns(2)
with col_left:
    fig = make_timeseries(
        df,
        series=[
            {"col": "total_plant_power_mw",    "name": "Puissance totale usine (MW)", "color": "#00B0FF"},
            {"col": "cat_generation_63kv_mw",  "name": "Génération CAT (MW)",         "color": "#00C853"},
            {"col": "grid_import_63kv_mw",     "name": "Import réseau (MW)",           "color": "#FFB300"},
        ],
        title="Bilan électrique 63 kV",
        y_label="MW",
        height=280,
        shade_anomaly="electricity",
    )
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    fig2 = make_timeseries(
        df,
        series=[
            {"col": "air_7b_pressure",          "name": "Pression air 7 bars (bar)",  "color": "#7B61FF"},
            {"col": "air_3b_pressure",           "name": "Pression air 3 bars (bar)",  "color": "#E040FB"},
        ],
        title="Pressions air comprimé",
        y_label="bar",
        height=280,
        shade_anomaly="air",
        thresholds=[
            {"value": 6.55, "name": "Seuil alerte 7b", "color": "#FF6D00"},
            {"value": 2.62, "name": "Seuil alerte 3b", "color": "#FF6D00"},
        ],
    )
    st.plotly_chart(fig2, use_container_width=True)

col_left2, col_right2 = st.columns(2)
with col_left2:
    fig3 = make_timeseries(
        df,
        series=[
            {"col": "recycled_water_flow_m3h",  "name": "Débit eau recyclée (m³/h)",  "color": "#00C853"},
            {"col": "raw_water_flow_m3h",        "name": "Débit eau brute (m³/h)",     "color": "#00B0FF", "dash": "dot"},
        ],
        title="Débits eau — recyclée & brute",
        y_label="m³/h",
        height=260,
        shade_anomaly="water",
    )
    st.plotly_chart(fig3, use_container_width=True)

with col_right2:
    fig4 = make_domain_score_bar(scoring, height=260)
    st.plotly_chart(fig4, use_container_width=True)

# ── Top anomalies ─────────────────────────────────────────────────────────────
if anomalies:
    render_section_title("Anomalies détectées", "🚨")
    for a in sorted(anomalies, key=lambda x: x.get("confidence_score", 0), reverse=True):
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

    # Top recommandations
    if recs:
        render_section_title("Recommandations prioritaires", "📋")
        for r in recs[:4]:
            pc = {"urgent": "#D50000", "high": "#FF6D00", "medium": "#FFB300", "low": "#00C853"}.get(r.priority, "#6B7894")
            st.markdown(
                f'<div style="background:#161A23;border:1px solid #2A2F3E;border-radius:5px;'
                f'padding:10px 14px;margin-bottom:6px;display:flex;'
                f'justify-content:space-between;align-items:center;">'
                f'<div>'
                f'<span style="font-size:12px;font-weight:600;color:#DDE3F0;">{r.action_title}</span>'
                f'<span style="font-size:11px;color:#6B7894;display:block;margin-top:2px;">'
                f'{r.action_detail[:90]}…</span>'
                f'</div>'
                f'<div style="text-align:right;min-width:120px;">'
                f'<span style="font-size:11px;font-weight:700;color:{pc};">{r.priority.upper()}</span>'
                f'<span style="font-size:10px;color:#00C853;display:block;">'
                f'{fmt_xpf(r.estimated_saving_xpf)} XPF</span>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ROI summary
    roi_text = biz.get("roi_summary", "")
    if roi_text:
        render_section_title("Synthèse ROI", "💰")
        render_info_banner(roi_text)
else:
    st.success(
        "Fonctionnement nominal — aucune anomalie détectée. "
        "Sélectionner un scénario dans la barre latérale pour déclencher l'analyse IA."
    )
