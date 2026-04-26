"""Page 2 — Supervision Électricité : filière 63 kV → 15 kV → 5,5 kV / 400 V."""

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

shade = "electricity"  # zone d'anomalie n'apparaît que pour anomalies électriques

render_header(
    "Supervision Électricité",
    "Fours 63 kV · Centrale CAT · Réseau 15 kV · Sous-stations",
    "⚡",
)

# ── Architecture ──────────────────────────────────────────────────────────────
st.markdown(
    '<div style="background:#161A23;border:1px solid #2A2F3E;border-radius:6px;'
    'padding:12px 16px;margin-bottom:16px;font-size:12px;color:#8892A4;">'
    '<strong style="color:#DDE3F0;">Architecture réseau :</strong>&nbsp;&nbsp;'
    '63 kV (Fours + CAT + Réseau) → 15 kV (Force motrice) '
    '→ 5,5 kV (Compresseurs + Pompes + Moteurs) / 400 V (Auxiliaires)'
    '</div>',
    unsafe_allow_html=True,
)

# ── KPIs ──────────────────────────────────────────────────────────────────────
last = df.iloc[-1]
daily_cost = df["energy_cost_xpf"].sum()

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    render_kpi_card("Bus 63 kV", f"{last['total_63kv_bus_mw']:.1f}", "MW", status="normal")
with c2:
    cat_val = last["cat_generation_63kv_mw"]
    render_kpi_card("CAT génération", f"{cat_val:.1f}", "MW",
                    status="warning" if cat_val < 70 else "ok")
with c3:
    gi = last["grid_import_63kv_mw"]
    render_kpi_card("Import réseau", f"{gi:.1f}", "MW",
                    status="warning" if gi > 50 else "ok")
with c4:
    render_kpi_card("Poste 15 kV", f"{last['station_15kv_supply_mw']:.1f}", "MW",
                    status="alert" if last["station_15kv_supply_mw"] > 26 else "ok")
with c5:
    render_kpi_card("Coût énergie 24 h", fmt_xpf(daily_cost), "XPF", status="normal")

# ── Fours 63 kV ───────────────────────────────────────────────────────────────
render_section_title("Fours industriels 63 kV", "🔥")

fig_furnaces = make_timeseries(
    df,
    series=[
        {"col": "furnace_1_63kv_mw", "name": "Four 1 (MW)", "color": "#00B0FF"},
        {"col": "furnace_2_63kv_mw", "name": "Four 2 (MW)", "color": "#FF6D00"},
        {"col": "furnace_3_63kv_mw", "name": "Four 3 (MW)", "color": "#00C853"},
    ],
    title="Puissance fours 63 kV",
    y_label="MW",
    height=280,
    shade_anomaly=shade,
    thresholds=[{"value": 62.0, "name": "Seuil four 2", "color": "#FFB300"}],
)
st.plotly_chart(fig_furnaces, use_container_width=True)

# Dernier relevé fours
fc1, fc2, fc3 = st.columns(3)
for col, i in zip([fc1, fc2, fc3], [1, 2, 3]):
    v = last[f"furnace_{i}_63kv_mw"]
    with col:
        render_kpi_card(
            f"Four {i} — dernière mesure", f"{v:.2f}", "MW",
            status="alert" if (i == 2 and v > 62) else "ok",
        )

# ── Bilan bus 63 kV ───────────────────────────────────────────────────────────
render_section_title("Bilan bus 63 kV — CAT vs Réseau", "⚖️")

col_a, col_b = st.columns(2)
with col_a:
    fig_bus = make_timeseries(
        df,
        series=[
            {"col": "total_63kv_bus_mw",       "name": "Demande totale (MW)",  "color": "#DDE3F0"},
            {"col": "cat_generation_63kv_mw",   "name": "CAT génération (MW)", "color": "#00C853"},
            {"col": "grid_import_63kv_mw",      "name": "Import réseau (MW)",  "color": "#FFB300"},
        ],
        title="Bilan énergétique bus 63 kV",
        y_label="MW",
        height=270,
        shade_anomaly=shade,
        thresholds=[{"value": 70.0, "name": "Min CAT", "color": "#FF6D00"}],
    )
    st.plotly_chart(fig_bus, use_container_width=True)

with col_b:
    fig_15kv = make_timeseries(
        df,
        series=[
            {"col": "station_15kv_supply_mw",   "name": "Poste 15 kV total (MW)", "color": "#00B0FF"},
            {"col": "substation_a_15kv_mw",     "name": "Sous-station A (MW)",    "color": "#7B61FF"},
            {"col": "substation_b_15kv_mw",     "name": "Sous-station B (MW)",    "color": "#E040FB"},
            {"col": "substation_c_15kv_mw",     "name": "Sous-station C (MW)",    "color": "#FFB300"},
        ],
        title="Réseau 15 kV — sous-stations",
        y_label="MW",
        height=270,
        shade_anomaly=shade,
        thresholds=[{"value": 26.5, "name": "Seuil surcharge", "color": "#FF6D00"}],
    )
    st.plotly_chart(fig_15kv, use_container_width=True)

# ── Coût énergie ──────────────────────────────────────────────────────────────
render_section_title("Coût énergie", "💰")
fig_cost = make_timeseries(
    df,
    series=[{"col": "energy_cost_xpf", "name": "Coût par période 15 min (XPF)", "color": "#FFB300"}],
    title="Coût énergie électrique — XPF par quart d'heure",
    y_label="XPF",
    height=220,
    shade_anomaly=shade,
)
st.plotly_chart(fig_cost, use_container_width=True)

# ── Bloc IA ───────────────────────────────────────────────────────────────────
render_ia_block(anomalies, recs, biz, domain_filter="electricity")
