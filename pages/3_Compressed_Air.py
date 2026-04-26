"""Page 3 — Supervision Air Comprimé : réseaux 7 bars et 3 bars."""

import streamlit as st
from modules.ui_components import (
    PAGE_CONFIG, inject_custom_css, render_scenario_sidebar,
    render_header, render_kpi_card, render_section_title,
    make_timeseries, render_ia_block, render_scada_vs_ia, fmt_xpf,
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

shade = "air"  # zone d'anomalie n'apparaît que pour anomalies air comprimé
last  = df.iloc[-1]

render_header("Supervision Air Comprimé", "Réseau 7 bars (instrumentation) & 3 bars (transport)", "💨")

# ═══════════════════════════════════════════════════════════════
# AIR 7 BARS
# ═══════════════════════════════════════════════════════════════
render_section_title("Réseau air 7 bars — Instrumentation process", "⚙️")

# KPIs 7 bars
c1, c2, c3, c4 = st.columns(4)
p7 = last["air_7b_pressure"]
with c1:
    render_kpi_card("Pression 7 bars", f"{p7:.3f}", "bar",
                    status="alert" if p7 < 6.55 else ("warning" if p7 < 6.70 else "ok"))
with c2:
    render_kpi_card("Débit total 7b", f"{last['air_7b_total_flow_nm3h']:.0f}", "Nm³/h", status="normal")
with c3:
    render_kpi_card("Puissance totale 7b", f"{last['air_7b_total_power_kw']:.1f}", "kW", status="normal")
with c4:
    se = last["air_7b_specific_energy_kwh_per_nm3"]
    render_kpi_card("Énergie spécifique", f"{se:.4f}", "kWh/Nm³",
                    status="warning" if se > 0.131 else "ok")

# Courbes réseau 7 bars
col_a, col_b = st.columns(2)
with col_a:
    fig_p7 = make_timeseries(
        df,
        series=[{"col": "air_7b_pressure", "name": "Pression (bar)", "color": "#7B61FF"}],
        title="Pression réseau 7 bars",
        y_label="bar",
        height=240,
        shade_anomaly=shade,
        thresholds=[
            {"value": 6.55, "name": "Seuil alarme",    "color": "#FF6D00"},
            {"value": 6.65, "name": "Min nominal",      "color": "#FFB300"},
        ],
    )
    st.plotly_chart(fig_p7, use_container_width=True)

with col_b:
    fig_flow7 = make_timeseries(
        df,
        series=[
            {"col": "air_7b_total_flow_nm3h",  "name": "Débit total (Nm³/h)",    "color": "#00B0FF"},
            {"col": "air_7b_total_power_kw",   "name": "Puissance totale (kW)", "color": "#FFB300"},
        ],
        title="Débit et puissance 7 bars",
        y_label="Nm³/h / kW",
        height=240,
        shade_anomaly=shade,
    )
    st.plotly_chart(fig_flow7, use_container_width=True)

# Débit par compresseur 7 bars
render_section_title("Compresseurs 7 bars — C713 à C717", "🔧")

fig_c7_flows = make_timeseries(
    df,
    series=[
        {"col": "C713_flow_nm3h", "name": "C713 (Nm³/h)", "color": "#00B0FF"},
        {"col": "C714_flow_nm3h", "name": "C714 (Nm³/h)", "color": "#00C853"},
        {"col": "C715_flow_nm3h", "name": "C715 (Nm³/h)", "color": "#FFB300"},
        {"col": "C716_flow_nm3h", "name": "C716 (Nm³/h)", "color": "#FF6D00"},
        {"col": "C717_flow_nm3h", "name": "C717 (Nm³/h)", "color": "#7B61FF"},
    ],
    title="Débit par compresseur 7 bars",
    y_label="Nm³/h",
    height=270,
    shade_anomaly=shade,
)
st.plotly_chart(fig_c7_flows, use_container_width=True)

# Tableau état compresseurs 7 bars
c7_names = ["C713", "C714", "C715", "C716", "C717"]
row_cols = st.columns(5)
for col, name in zip(row_cols, c7_names):
    status_val = int(last.get(f"{name}_status", 0))
    flow_val   = float(last.get(f"{name}_flow_nm3h", 0.0))
    power_val  = float(last.get(f"{name}_power_kw", 0.0))
    run_css    = "ok" if status_val else "normal"
    with col:
        render_kpi_card(
            name,
            f"{flow_val:.0f}",
            "Nm³/h",
            delta=f"{power_val:.0f} kW",
            status=run_css,
        )

# ═══════════════════════════════════════════════════════════════
# AIR 3 BARS
# ═══════════════════════════════════════════════════════════════
render_section_title("Réseau air 3 bars — Transport charbon & poussières", "⚙️")

# KPIs 3 bars
d1, d2, d3, d4 = st.columns(4)
p3 = last["air_3b_pressure"]
with d1:
    render_kpi_card("Pression 3 bars", f"{p3:.3f}", "bar",
                    status="alert" if p3 < 2.62 else ("warning" if p3 < 2.75 else "ok"))
with d2:
    render_kpi_card("Débit total 3b", f"{last['air_3b_total_flow_nm3h']:.0f}", "Nm³/h", status="normal")
with d3:
    render_kpi_card("Puissance totale 3b", f"{last['air_3b_total_power_kw']:.1f}", "kW", status="normal")
with d4:
    c311 = int(last.get("C311_status", 0))
    c312 = int(last.get("C312_status", 0))
    n_fixed_on = c311 + c312
    render_kpi_card(
        "Fixes démarrés (C311/C312)", str(n_fixed_on), "",
        status="warning" if n_fixed_on > 0 else "ok",
        delta="Régulation anormale" if n_fixed_on else None,
    )

# Courbes 3 bars
col_c, col_d = st.columns(2)
with col_c:
    fig_p3 = make_timeseries(
        df,
        series=[{"col": "air_3b_pressure", "name": "Pression 3 bars (bar)", "color": "#E040FB"}],
        title="Pression réseau 3 bars",
        y_label="bar",
        height=240,
        shade_anomaly=shade,
        thresholds=[
            {"value": 2.62, "name": "Seuil alarme",  "color": "#FF6D00"},
            {"value": 2.75, "name": "Min nominal",    "color": "#FFB300"},
        ],
    )
    st.plotly_chart(fig_p3, use_container_width=True)

with col_d:
    fig_vsd = make_timeseries(
        df,
        series=[
            {"col": "C321_speed_pct", "name": "C321 vitesse (%)", "color": "#00B0FF"},
            {"col": "C322_speed_pct", "name": "C322 vitesse (%)", "color": "#00C853"},
            {"col": "C323_speed_pct", "name": "C323 vitesse (%)", "color": "#7B61FF"},
        ],
        title="Vitesse VSD C321 / C322 / C323",
        y_label="%",
        height=240,
        shade_anomaly=shade,
        thresholds=[{"value": 97.0, "name": "Saturation VSD", "color": "#FF6D00"}],
    )
    st.plotly_chart(fig_vsd, use_container_width=True)

# Indices transport
fig_transport = make_timeseries(
    df,
    series=[
        {"col": "dust_transport_index", "name": "Transport poussières",  "color": "#FFB300"},
        {"col": "coal_transport_index", "name": "Transport charbon",     "color": "#FF6D00"},
    ],
    title="Indices demande transport (moteurs principaux de la demande 3 bars)",
    y_label="index [0-1]",
    height=220,
    shade_anomaly=shade,
)
st.plotly_chart(fig_transport, use_container_width=True)

# ── SCADA vs IA — exemple fuite air ──────────────────────────────────────────
render_section_title("Comparaison SCADA vs IA — détection fuite", "🆚")
render_scada_vs_ia(
    scada_points=[
        "Alarme : pression < 6.55 bar",
        "Opérateur constate la basse pression",
        "Recherche de cause manuelle",
        "Pas de corrélation avec le débit",
    ],
    ia_points=[
        "Détecte : pression basse ET débit en hausse ET puissance en hausse",
        "Signature combinée = fuite réseau probable",
        "Confiance calculée sur amplitude et durée",
        "Recommande : inspection circuit, purge vannes",
        "Chiffre l'économie si correction",
    ],
    key_phrase=(
        "Un SCADA alerterait à pression basse. L'IA détecte que la pression baisse "
        "pendant que le débit et la puissance augmentent : signature d'une fuite."
    ),
)

# ── Bloc IA ───────────────────────────────────────────────────────────────────
render_ia_block(anomalies, recs, biz, domain_filter="air")
