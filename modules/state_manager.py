"""
Gestion centralisée de l'état de session Streamlit.

Appel minimal dans chaque page :
    from modules.state_manager import ensure_state
    ensure_state()

État disponible via st.session_state :
    selected_scenario   str
    df_nominal          pd.DataFrame (96 × ~60 col, nominal)
    df_current          pd.DataFrame (nominal ou scénario appliqué)
    anomalies           list[dict]
    scoring_summary     dict
    recommendations     list[Recommendation]
    business_summary    dict
"""

from __future__ import annotations

import streamlit as st
import pandas as pd


# ---------------------------------------------------------------------------
# Données nominales — générées une seule fois, cachées
# ---------------------------------------------------------------------------

@st.cache_data
def _load_nominal_data() -> pd.DataFrame:
    from modules.data_generator import generate_mock_plant_data
    return generate_mock_plant_data()


# ---------------------------------------------------------------------------
# Recalcul complet
# ---------------------------------------------------------------------------

def _recompute() -> None:
    from modules.scenarios import apply_scenario
    from modules.detection import detect_anomalies
    from modules.scoring import build_scoring_summary
    from modules.recommendations import generate_recommendations
    from modules.business_value import compute_total_business_impact

    ss = st.session_state
    scenario = ss.get("selected_scenario", "nominal")
    df_nom = ss["df_nominal"]

    if scenario == "nominal":
        df_current = df_nom.copy()
    else:
        try:
            df_current = apply_scenario(df_nom.copy(), scenario)
        except Exception:
            df_current = df_nom.copy()
            ss["selected_scenario"] = "nominal"

    ss["df_current"] = df_current

    anomalies = detect_anomalies(df_current)
    ss["anomalies"] = anomalies

    scoring = build_scoring_summary(anomalies)
    ss["scoring_summary"] = scoring

    recs = generate_recommendations(anomalies, scoring_summary=scoring)
    ss["recommendations"] = recs

    biz = compute_total_business_impact(anomalies, recs)
    ss["business_summary"] = biz

    ss["_computed_for"] = scenario


# ---------------------------------------------------------------------------
# Point d'entrée public
# ---------------------------------------------------------------------------

def ensure_state() -> None:
    """Initialise l'état et recalcule si le scénario a changé. Idempotent."""
    ss = st.session_state

    if "df_nominal" not in ss:
        ss["df_nominal"] = _load_nominal_data()

    if "selected_scenario" not in ss:
        ss["selected_scenario"] = "nominal"

    if ss.get("_computed_for") != ss["selected_scenario"]:
        _recompute()
