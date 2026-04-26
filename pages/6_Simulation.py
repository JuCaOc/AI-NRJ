"""Page 6 — Simulation : comparaison nominal vs scénario + simulation recommandation."""

import streamlit as st
import plotly.graph_objects as go
from modules.ui_components import (
    PAGE_CONFIG, inject_custom_css, render_scenario_sidebar,
    render_header, render_kpi_card, render_section_title,
    render_info_banner, make_comparison_chart,
    score_to_status, plant_status_css, fmt_xpf, STATUS_COLORS, SEVERITY_COLORS,
    _SCENARIO_FR,
)
from modules.state_manager import ensure_state
from modules.recommendation_simulator import (
    get_simulatable_recommendations,
    apply_simulated_recommendation,
    build_simulation_summary,
)

st.set_page_config(**PAGE_CONFIG)
inject_custom_css()
ensure_state()
render_scenario_sidebar()

ss        = st.session_state
df_nom    = ss["df_nominal"]
df_cur    = ss["df_current"]
anomalies = ss.get("anomalies", [])
scoring   = ss.get("scoring_summary", {})
biz       = ss.get("business_summary", {})
scenario  = ss.get("selected_scenario", "nominal")

render_header(
    "Simulation — Comparaison nominal vs scénario",
    "Cette page montre pourquoi l'IA est utile : elle transforme une dérive sur courbe en diagnostic + action + coût.",
    "🔬",
)

if scenario == "nominal":
    st.info(
        "Aucun scénario actif. Sélectionnez un scénario dans la barre latérale "
        "pour voir la comparaison avant / après.",
        icon="ℹ️",
    )
    st.stop()

# ── En-tête scénario actif ────────────────────────────────────────────────────
scenario_label = _SCENARIO_FR.get(scenario, scenario)
st.markdown(
    f'<div style="background:rgba(255,109,0,.07);border:1px solid rgba(255,109,0,.25);'
    f'border-radius:6px;padding:12px 18px;margin-bottom:16px;">'
    f'<span style="font-size:12px;font-weight:700;color:#FF9950;">Scénario actif : {scenario_label}</span>'
    f'<span style="font-size:12px;color:#8892A4;margin-left:16px;">'
    f'{len(anomalies)} anomalie(s) · Perte estimée : {fmt_xpf(biz.get("total_loss_xpf",0))} XPF</span>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── Sélecteur de métrique à comparer ─────────────────────────────────────────
# Tuple : (label, unité, domaine pour ombrage anomalie)
METRICS = {
    "total_plant_power_mw":             ("Puissance totale usine",        "MW",    "electricity"),
    "total_63kv_bus_mw":                ("Bus 63 kV total",               "MW",    "electricity"),
    "cat_generation_63kv_mw":           ("Génération CAT",                "MW",    "electricity"),
    "grid_import_63kv_mw":              ("Import réseau",                 "MW",    "electricity"),
    "furnace_2_63kv_mw":                ("Puissance four 2",              "MW",    "electricity"),
    "station_15kv_supply_mw":           ("Poste 15 kV",                   "MW",    "electricity"),
    "air_7b_pressure":                  ("Pression air 7 bars",           "bar",   "air"),
    "air_7b_total_flow_nm3h":           ("Débit air 7 bars",              "Nm³/h", "air"),
    "air_7b_total_power_kw":            ("Puissance compresseurs 7b",     "kW",    "air"),
    "air_3b_pressure":                  ("Pression air 3 bars",           "bar",   "air"),
    "C321_speed_pct":                   ("Vitesse VSD C321",              "%",     "air"),
    "recycled_water_flow_m3h":          ("Débit eau recyclée",            "m³/h",  "water"),
    "recycled_water_delta_t_c":         ("Delta T eau recyclée",          "°C",    "water"),
    "legionella_risk_index":            ("Indice légionelle",             "index", "water"),
    "basin_b0_level_pct":               ("Niveau bassin B0",              "%",     "water"),
    "basin_b1_level_pct":               ("Niveau bassin B1",              "%",     "water"),
}

# Garder uniquement les métriques présentes dans les deux df
avail = {k: v for k, v in METRICS.items() if k in df_nom.columns and k in df_cur.columns}
metric_key = st.selectbox(
    "Indicateur à comparer",
    list(avail.keys()),
    format_func=lambda k: f"{avail[k][0]} ({avail[k][1]})",
    index=0,
)
m_label, m_unit, m_domain = avail[metric_key]

# ── Graphique comparaison ─────────────────────────────────────────────────────
has_anomaly_zone = "anomaly_flag" in df_cur.columns and df_cur["anomaly_flag"].any()
fig_cmp = make_comparison_chart(
    df_nom, df_cur,
    col=metric_key,
    title=f"{m_label} — Nominal vs Scénario « {scenario_label} »",
    y_label=m_unit,
    height=340,
    anomaly_domain=m_domain,
)
st.plotly_chart(fig_cmp, use_container_width=True)

# ── Statistiques variation ────────────────────────────────────────────────────
render_section_title("Impact mesuré sur l'indicateur", "📊")

nom_vals = df_nom[metric_key]
cur_vals = df_cur[metric_key]
delta_mean = float(cur_vals.mean() - nom_vals.mean())
delta_max  = float(cur_vals.max()  - nom_vals.max())
delta_pct  = delta_mean / max(abs(float(nom_vals.mean())), 1e-6) * 100

c1, c2, c3, c4 = st.columns(4)
with c1:
    sign = "+" if delta_mean >= 0 else ""
    render_kpi_card(
        "Variation moyenne",
        f"{sign}{delta_mean:.2f}", m_unit,
        status="alert" if abs(delta_pct) > 10 else ("warning" if abs(delta_pct) > 3 else "ok"),
    )
with c2:
    sign2 = "+" if delta_max >= 0 else ""
    render_kpi_card("Variation max", f"{sign2}{delta_max:.2f}", m_unit, status="normal")
with c3:
    sign3 = "+" if delta_pct >= 0 else ""
    render_kpi_card("Variation %", f"{sign3}{delta_pct:.1f}", "%", status="normal")
with c4:
    render_kpi_card(
        "Perte estimée", fmt_xpf(biz.get("total_loss_xpf", 0.0)), "XPF",
        status="alert" if biz.get("total_loss_xpf", 0) > 500_000 else "warning",
    )

# ── Anomalies détectées ───────────────────────────────────────────────────────
render_section_title("Anomalies générées par le scénario", "🚨")

if anomalies:
    for a in anomalies:
        sc = SEVERITY_COLORS.get(a.get("severity", "low"), "#6B7894")
        st.markdown(
            f'<div style="background:#161A23;border-left:3px solid {sc};'
            f'border-radius:0 5px 5px 0;padding:10px 14px;margin-bottom:6px;">'
            f'<div style="display:flex;justify-content:space-between;">'
            f'<div>'
            f'<span style="font-size:13px;font-weight:600;color:#DDE3F0;">{a.get("title","")}</span>'
            f'<span style="font-size:11px;color:#6B7894;margin-left:10px;">{a.get("asset","")}</span>'
            f'</div>'
            f'<div>'
            f'<span style="font-size:11px;font-weight:700;color:{sc};">'
            f'{a.get("severity","").upper()}</span>'
            f'<span style="font-size:11px;color:#6B7894;margin-left:8px;">'
            f'Confiance {a.get("confidence_score",0):.0%}</span>'
            f'</div>'
            f'</div>'
            f'<div style="font-size:11px;color:#6B7894;margin-top:5px;">'
            f'{a.get("description","")[:150]}'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
else:
    st.info("Aucune anomalie détectée pour ce scénario.")

# ── Texte pédagogique ─────────────────────────────────────────────────────────
render_section_title("Pourquoi une IA est utile ici", "💡")
st.markdown(
    '<div style="background:#0F1C2E;border:1px solid #1E3A5F;border-radius:6px;'
    'padding:16px 20px;font-size:13px;color:#8892A4;line-height:1.7;">'
    '<strong style="color:#00B0FF;">Ce que vous venez de voir :</strong><br>'
    '1. Une dérive physique est injectée dans les données (fenêtre 40–70 % de la période).<br>'
    '2. Le moteur de détection IA identifie la signature multi-signaux.<br>'
    '3. Un diagnostic explicable est produit avec ses causes probables.<br>'
    '4. L\'impact financier est quantifié en XPF.<br>'
    '5. Des recommandations actionnables sont proposées avec priorité et ROI.<br><br>'
    '<strong style="color:#00B0FF;">Sans IA :</strong> '
    'l\'opérateur voit une courbe s\'écarter — mais quand ? pourquoi ? que faire ? combien ça coûte ?<br>'
    '<strong style="color:#00B0FF;">Avec IA :</strong> '
    'le système répond automatiquement à ces quatre questions.'
    '</div>',
    unsafe_allow_html=True,
)

# ── ROI summary ───────────────────────────────────────────────────────────────
roi_text = biz.get("roi_summary", "")
if roi_text:
    render_section_title("Synthèse financière", "💰")
    render_info_banner(roi_text)

# ── Simulation de recommandation IA ──────────────────────────────────────────
render_section_title("Simulation de recommandation IA", "🔧")

recs = ss.get("recommendations", [])
sim_recs = get_simulatable_recommendations(recs)

# Réinitialiser le résultat si le scénario a changé
if ss.get("_sim_for_scenario") != scenario:
    ss.pop("_sim_result", None)
    ss.pop("_sim_for_scenario", None)
    ss.pop("_sim_for_rec_idx", None)

if not sim_recs:
    st.info(
        "Aucune recommandation simulable pour ce scénario. "
        "Sélectionnez un scénario avec anomalies dans la barre latérale.",
        icon="ℹ️",
    )
else:
    st.markdown(
        '<div style="background:#0F1C2E;border:1px solid #1E3A5F;border-radius:6px;'
        'padding:10px 16px;font-size:12px;color:#8892A4;margin-bottom:14px;">'
        '<strong style="color:#00B0FF;">4ème pouvoir de l\'IA :</strong> '
        'simuler l\'impact d\'une action <em>avant</em> de l\'exécuter. '
        'Sélectionnez une recommandation et cliquez sur "Appliquer" pour voir '
        'l\'état projeté <strong>après correction</strong>.<br>'
        '<span style="color:#FF6B6B;">Simulation uniquement — aucune commande réelle.</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    rec_labels = [
        f"[{r.priority.upper()}] {r.action_title}" for r in sim_recs
    ]
    sel_idx = st.selectbox(
        "Recommandation à simuler",
        range(len(sim_recs)),
        format_func=lambda i: rec_labels[i],
        key="sim_rec_selector",
    )
    sel_rec = sim_recs[sel_idx]

    # Détails de la recommandation sélectionnée
    col_detail, col_btn = st.columns([4, 1])
    with col_detail:
        st.markdown(
            f'<div style="background:#161A23;border:1px solid #2A2F3E;border-radius:5px;'
            f'padding:8px 14px;font-size:11px;">'
            f'<span style="color:#6B7894;">Effet attendu : </span>'
            f'<span style="color:#DDE3F0;">{sel_rec.expected_effect}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col_btn:
        run_sim = st.button(
            "▶ Appliquer",
            key="run_simulation",
            type="primary",
            use_container_width=True,
        )

    if run_sim:
        with st.spinner("Simulation en cours…"):
            df_after = apply_simulated_recommendation(df_cur, sel_rec)
            sim_result = build_simulation_summary(
                before_df=df_cur,
                after_df=df_after,
                recommendation=sel_rec,
                anomalies=anomalies,
            )
        ss["_sim_result"]      = sim_result
        ss["_sim_for_scenario"] = scenario
        ss["_sim_for_rec_idx"] = sel_idx

    # ── Affichage résultat ────────────────────────────────────────────────────
    if (
        "_sim_result" in ss
        and ss.get("_sim_for_scenario") == scenario
        and ss.get("_sim_for_rec_idx") == sel_idx
    ):
        result = ss["_sim_result"]
        before_score = result["before_score"]
        after_score  = result["after_score"]
        improvement  = result["score_improvement"]
        saving       = result["estimated_saving_xpf"]

        status_before = plant_status_css(
            "CRITIQUE" if before_score >= 75
            else ("ALERTE" if before_score >= 45
                  else ("VIGILANCE" if before_score >= 20 else "NORMAL"))
        )
        status_after = plant_status_css(
            "CRITIQUE" if after_score >= 75
            else ("ALERTE" if after_score >= 45
                  else ("VIGILANCE" if after_score >= 20 else "NORMAL"))
        )

        st.markdown("---")
        render_section_title(
            f"Résultat simulation : {result['applied_action'][:60]}", "📊"
        )

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            render_kpi_card(
                "Criticité avant", f"{before_score:.0f}", "/ 100",
                status=status_before,
            )
        with c2:
            render_kpi_card(
                "Criticité après", f"{after_score:.0f}", "/ 100",
                status=status_after,
            )
        with c3:
            sign = "-" if improvement >= 0 else "+"
            render_kpi_card(
                "Réduction criticité",
                f"{sign}{abs(improvement):.0f}", "pts",
                status="ok" if improvement >= 0 else "alert",
            )
        with c4:
            render_kpi_card(
                "Économie estimée", fmt_xpf(saving), "XPF",
                status="ok" if saving > 0 else "normal",
            )

        # KPIs anomalies
        n_before = result["before_n_anomalies"]
        n_after  = result["after_n_anomalies"]
        if n_after < n_before:
            st.success(
                f"Anomalies : {n_before} → {n_after} "
                f"(−{n_before - n_after} résolue(s) par la simulation)"
            )
        elif n_after == n_before:
            st.info(f"Anomalies : {n_before} → {n_after} (inchangé — amélioration partielle)")

        # Graphique avant / après
        key_col = result["key_metric"]
        if key_col in df_cur.columns and key_col in result["after_df"].columns:
            col_label = key_col.replace("_", " ")
            fig_sim = make_comparison_chart(
                df_nom=df_cur,
                df_cur=result["after_df"],
                col=key_col,
                title=f"{col_label} — Avant (scénario) vs Après (simulation correction)",
                y_label=key_col.split("_")[-1] if "_" in key_col else "",
                height=320,
            )
            # Renommer les traces pour clarté
            for trace in fig_sim.data:
                if hasattr(trace, "name"):
                    if trace.name == "Nominal":
                        trace.name = "Avant correction"
                    elif trace.name == "Scénario":
                        trace.name = "Après correction"
            st.plotly_chart(fig_sim, use_container_width=True)

        # Note de sécurité
        st.markdown(
            f'<div style="background:rgba(213,0,0,.07);border:1px solid rgba(213,0,0,.2);'
            f'border-radius:5px;padding:10px 16px;font-size:11px;color:#FF6B6B;'
            f'margin-top:8px;">'
            f'⚠️ <strong>{result["simulation_note"]}</strong>'
            f'</div>',
            unsafe_allow_html=True,
        )
