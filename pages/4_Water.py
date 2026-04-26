"""Page 4 — Supervision Eau : eau recyclée (refroidissement) et eau brute (bassins B0/B1)."""

import streamlit as st
from modules.ui_components import (
    PAGE_CONFIG, inject_custom_css, render_scenario_sidebar,
    render_header, render_kpi_card, render_section_title,
    make_timeseries, render_ia_block, fmt_xpf, SEVERITY_COLORS,
)
from modules.state_manager import ensure_state

st.set_page_config(**PAGE_CONFIG)
inject_custom_css()
ensure_state()
render_scenario_sidebar()

ss        = st.session_state
df        = ss["df_current"]
anomalies = ss.get("anomalies", [])
recs      = ss.get("recommendations", [])
biz       = ss.get("business_summary", {})

shade = "water"  # zone d'anomalie n'apparaît que pour anomalies eau
last  = df.iloc[-1]

render_header("Supervision Eau", "Eau recyclée (refroidissement) & eau brute (bassins)", "♻️")

# ═══════════════════════════════════════════════════════════════
# EAU RECYCLÉE
# ═══════════════════════════════════════════════════════════════
render_section_title("Circuit eau recyclée — Refroidissement process", "🌊")

c1, c2, c3, c4, c5 = st.columns(5)
flow_rw = last["recycled_water_flow_m3h"]
leg     = last["legionella_risk_index"]
chem    = last["chemical_treatment_index"]
dt      = last["recycled_water_delta_t_c"]
eff     = last["recycled_water_efficiency_index"]

with c1:
    render_kpi_card("Débit eau recyclée", f"{flow_rw:.0f}", "m³/h",
                    status="alert" if flow_rw < 1800 else "ok")
with c2:
    render_kpi_card(
        "Température départ / retour",
        f"{last['recycled_water_supply_temp_c']:.1f} / {last['recycled_water_return_temp_c']:.1f}",
        "°C", status="normal",
    )
with c3:
    render_kpi_card("Delta T", f"{dt:.2f}", "°C",
                    status="alert" if dt > 8 else ("warning" if dt > 7 else "ok"))
with c4:
    render_kpi_card("Efficacité refroid.", f"{eff:.3f}", "",
                    status="warning" if eff < 0.80 else "ok")
with c5:
    render_kpi_card("Indice légionelle", f"{leg:.3f}", "",
                    status="critical" if leg > 0.85 else ("alert" if leg > 0.65 else "ok"))

# Températures & débit
col_a, col_b = st.columns(2)
with col_a:
    fig_temps = make_timeseries(
        df,
        series=[
            {"col": "recycled_water_supply_temp_c",  "name": "Départ (°C)",  "color": "#00B0FF"},
            {"col": "recycled_water_return_temp_c",  "name": "Retour (°C)",  "color": "#FF6D00"},
            {"col": "recycled_water_delta_t_c",      "name": "Delta T (°C)", "color": "#FFB300", "dash": "dot"},
        ],
        title="Températures eau recyclée",
        y_label="°C",
        height=260,
        shade_anomaly=shade,
        thresholds=[{"value": 8.0, "name": "Seuil delta T", "color": "#FF6D00"}],
    )
    st.plotly_chart(fig_temps, use_container_width=True)

with col_b:
    fig_flow_rw = make_timeseries(
        df,
        series=[
            {"col": "recycled_water_flow_m3h",      "name": "Débit recyclée (m³/h)",  "color": "#00C853"},
            {"col": "recycled_water_pressure_bar",  "name": "Pression (bar) ×100",    "color": "#7B61FF"},
        ],
        title="Débit et pression eau recyclée",
        y_label="m³/h",
        height=260,
        shade_anomaly=shade,
        thresholds=[{"value": 1800, "name": "Min débit", "color": "#FF6D00"}],
    )
    st.plotly_chart(fig_flow_rw, use_container_width=True)

# Légionelle & traitement chimique
render_section_title("Qualité eau — Risque légionelle", "🧪")

col_c, col_d = st.columns(2)
with col_c:
    fig_leg = make_timeseries(
        df,
        series=[
            {"col": "legionella_risk_index",      "name": "Indice risque légionelle", "color": "#D50000"},
            {"col": "chemical_treatment_index",   "name": "Traitement chimique",      "color": "#00C853"},
        ],
        title="Légionelle vs traitement chimique",
        y_label="index [0-1]",
        height=240,
        shade_anomaly=shade,
        thresholds=[{"value": 0.65, "name": "Seuil légionelle", "color": "#FF6D00"}],
    )
    st.plotly_chart(fig_leg, use_container_width=True)

with col_d:
    fig_pumps = make_timeseries(
        df,
        series=[
            {"col": "aero_power_kw",                  "name": "Aéros (kW)",             "color": "#00B0FF"},
            {"col": "recycled_water_pump_power_kw",   "name": "Pompes recyclée (kW)",   "color": "#7B61FF"},
        ],
        title="Puissance équipements eau recyclée",
        y_label="kW",
        height=240,
        shade_anomaly=shade,
    )
    st.plotly_chart(fig_pumps, use_container_width=True)

# ═══════════════════════════════════════════════════════════════
# EAU BRUTE
# ═══════════════════════════════════════════════════════════════
render_section_title("Eau brute — Bassins B0 / B1 & appoint", "💧")

e1, e2, e3, e4 = st.columns(4)
b0 = last["basin_b0_level_pct"]
b1 = last["basin_b1_level_pct"]
dep = last["raw_water_dependency_ratio"]
mk  = last["raw_water_makeup_to_recycled_m3h"]

with e1:
    render_kpi_card("Bassin B0 niveau", f"{b0:.1f}", "%",
                    status="critical" if b0 < 15 else ("alert" if b0 < 20 else "ok"))
with e2:
    render_kpi_card("Bassin B1 niveau", f"{b1:.1f}", "%",
                    status="critical" if b1 < 15 else ("alert" if b1 < 20 else "ok"))
with e3:
    render_kpi_card("Dépendance eau brute", f"{dep:.3f}", "",
                    status="alert" if dep > 0.12 else ("warning" if dep > 0.08 else "ok"))
with e4:
    render_kpi_card("Appoint eau brute", f"{mk:.1f}", "m³/h",
                    status="alert" if mk > 165 else ("warning" if mk > 130 else "ok"))

col_e, col_f = st.columns(2)
with col_e:
    fig_basins = make_timeseries(
        df,
        series=[
            {"col": "basin_b0_level_pct", "name": "Bassin B0 niveau (%)", "color": "#00B0FF"},
            {"col": "basin_b1_level_pct", "name": "Bassin B1 niveau (%)", "color": "#00C853"},
        ],
        title="Niveaux bassins B0 / B1",
        y_label="%",
        height=250,
        shade_anomaly=shade,
        thresholds=[{"value": 20.0, "name": "Seuil critique", "color": "#D50000"}],
    )
    st.plotly_chart(fig_basins, use_container_width=True)

with col_f:
    fig_raw = make_timeseries(
        df,
        series=[
            {"col": "raw_water_makeup_to_recycled_m3h", "name": "Appoint vers recyclée (m³/h)", "color": "#FFB300"},
            {"col": "emergency_cooling_capacity_m3h",   "name": "Capacité secours (m³/h)",       "color": "#7B61FF", "dash": "dot"},
        ],
        title="Appoint eau brute & capacité secours",
        y_label="m³/h",
        height=250,
        shade_anomaly=shade,
        thresholds=[{"value": 165.0, "name": "Max appoint", "color": "#FF6D00"}],
    )
    st.plotly_chart(fig_raw, use_container_width=True)

# ── Bloc IA ───────────────────────────────────────────────────────────────────
render_ia_block(anomalies, recs, biz, domain_filter="water")
