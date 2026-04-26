"""
Simulateur de recommandations IA — pédagogique, sans commande réelle.

Applique l'effet attendu d'une recommandation sur une copie du DataFrame
et calcule les métriques avant / après pour visualisation.

Règle fondamentale : le DataFrame original n'est JAMAIS modifié.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from modules.detection import Anomaly
from modules.recommendations import Recommendation

# ---------------------------------------------------------------------------
# Constantes physiques (alignées sur data_generator.py)
# ---------------------------------------------------------------------------

_ENERGY_TARIFF_XPF_KWH: float = 22.0
_INTERVAL_H: float             = 0.25    # 15 minutes
_AIR_7B_PRESSURE_MAX: float    = 7.20    # plafond plausible
_AIR_3B_PRESSURE_MAX: float    = 3.20
_RW_FLOW_NOM_M3H: float        = 2_500.0
_RW_DELTA_T_NOM_C: float       = 5.0


# ---------------------------------------------------------------------------
# Mapping recommandation → type d'action
# ---------------------------------------------------------------------------

_ACTION_KEYWORDS: dict[str, list[str]] = {
    "furnace_overload":          ["four 2", "charge du four", "consigne de puissance",
                                  "rendement thermique du four"],
    "cat_fault":                 ["perte cat", "centrale cat", "génération cat",
                                  "distributeur réseau"],
    "overload_15kv":             ["15 kv", "15kv", "poste 15 kv", "surcharge 15",
                                  "charge du poste"],
    "air_leak":                  ["fuite", "réseau air 7 bars", "inspecter le réseau 7",
                                  "presses à câble", "7 bars inspecter"],
    "compressor_fault":          ["c715", "compresseur c715", "examiner le compresseur c715"],
    "compressor_imbalance":      ["déséquilibre", "c713", "c714", "équilibrer les débits",
                                  "rééquilibrer"],
    "vsd_saturation":            ["c321", "c322", "c323", "vsd", "saturation vsd",
                                  "demande air 3 bars", "vitesse vsd"],
    "bad_regulation":            ["c311", "c312", "régulation 3 bars", "compresseur fixe c311",
                                  "compresseur fixe c312"],
    "cooling_fault":             ["pompe ef1", "circuit eau recyclée", "débit recyclé",
                                  "vérifier la pompe ef", "tours aéroréfrigérantes"],
    "legionella_risk":           ["légionelle", "traitement chimique", "choc thermique",
                                  "biocide", "qualité bactériologique"],
    "low_basin":                 ["bassin b1", "niveau b1", "alimentation de secours",
                                  "b1 critique", "alimenter le bassin"],
    "raw_water_overconsumption": ["eau brute", "appoint", "dépendance eau",
                                  "consommation eau brute", "réduire la consommation eau"],
}

# Métrique clé à afficher dans le graphique avant/après
_KEY_METRICS: dict[str, str] = {
    "furnace_overload":          "furnace_2_63kv_mw",
    "cat_fault":                 "grid_import_63kv_mw",
    "overload_15kv":             "station_15kv_supply_mw",
    "air_leak":                  "air_7b_pressure",
    "compressor_fault":          "C715_flow_nm3h",
    "compressor_imbalance":      "air_7b_total_flow_nm3h",
    "vsd_saturation":            "C321_speed_pct",
    "bad_regulation":            "air_3b_total_power_kw",
    "cooling_fault":             "recycled_water_flow_m3h",
    "legionella_risk":           "legionella_risk_index",
    "low_basin":                 "basin_b1_level_pct",
    "raw_water_overconsumption": "raw_water_dependency_ratio",
    "unknown":                   "total_plant_power_mw",
}


def _detect_action_type(recommendation: Recommendation) -> str:
    """Détermine le type d'action à partir des mots-clés du titre et du détail."""
    title  = _rec_attr(recommendation, "action_title", "").lower()
    detail = _rec_attr(recommendation, "action_detail", "").lower()
    text   = title + " " + detail
    for action_type, keywords in _ACTION_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return action_type
    return "unknown"


def _rec_attr(r: Any, attr: str, default: Any = "") -> Any:
    if hasattr(r, attr):
        return getattr(r, attr)
    if isinstance(r, dict):
        return r.get(attr, default)
    return default


# ---------------------------------------------------------------------------
# Fenêtre d'action
# ---------------------------------------------------------------------------

def _get_action_mask(df: pd.DataFrame) -> pd.Series:
    """
    Retourne un masque booléen sur les lignes à corriger.
    Priorité : colonne anomaly_flag si elle existe, sinon fenêtre 40–70 %.
    """
    if "anomaly_flag" in df.columns:
        mask = df["anomaly_flag"].astype(bool)
        if mask.any():
            return mask
    n = len(df)
    mask = pd.Series(False, index=df.index)
    mask.iloc[int(n * 0.40): int(n * 0.70)] = True
    return mask


# ---------------------------------------------------------------------------
# Recalculs agrégats
# ---------------------------------------------------------------------------

def _recalculate_aggregates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Recalcule les colonnes dérivées après modification simulée.
    Chaque recalcul est conditionnel à l'existence des colonnes sources.
    """
    # ── Électricité ──────────────────────────────────────────────────────────
    furnace_cols = [c for c in ["furnace_1_63kv_mw", "furnace_2_63kv_mw", "furnace_3_63kv_mw"]
                    if c in df.columns]
    if furnace_cols and "station_15kv_supply_mw" in df.columns:
        df["total_63kv_bus_mw"] = (
            sum(df[c] for c in furnace_cols) + df["station_15kv_supply_mw"]
        ).round(3)

    if "total_63kv_bus_mw" in df.columns:
        df["total_plant_power_mw"] = df["total_63kv_bus_mw"]
        if "cat_generation_63kv_mw" in df.columns:
            df["grid_import_63kv_mw"] = (
                df["total_63kv_bus_mw"] - df["cat_generation_63kv_mw"]
            ).round(1)

    if "total_plant_power_mw" in df.columns and "energy_cost_xpf" in df.columns:
        df["energy_cost_xpf"] = (
            df["total_plant_power_mw"] * 1_000.0 * _INTERVAL_H * _ENERGY_TARIFF_XPF_KWH
        ).round(0)

    # ── Air 7 bars ───────────────────────────────────────────────────────────
    c7_flow_cols = [c for c in ["C713_flow_nm3h", "C714_flow_nm3h", "C715_flow_nm3h",
                                 "C716_flow_nm3h", "C717_flow_nm3h"] if c in df.columns]
    if c7_flow_cols:
        df["air_7b_total_flow_nm3h"] = sum(df[c] for c in c7_flow_cols).round(0)

    c7_pwr_cols = [c for c in ["C713_power_kw", "C714_power_kw", "C715_power_kw",
                                "C716_power_kw", "C717_power_kw"] if c in df.columns]
    if c7_pwr_cols:
        df["air_7b_total_power_kw"] = sum(df[c] for c in c7_pwr_cols).round(1)

    if "air_7b_total_power_kw" in df.columns and "air_7b_total_flow_nm3h" in df.columns:
        flow = df["air_7b_total_flow_nm3h"].clip(lower=1.0)
        df["air_7b_specific_energy_kwh_per_nm3"] = (
            df["air_7b_total_power_kw"] / flow
        ).clip(0.08, 0.18).round(4)

    # ── Air 3 bars ───────────────────────────────────────────────────────────
    c3_flow_cols = [c for c in ["C321_flow_nm3h", "C322_flow_nm3h", "C323_flow_nm3h"]
                    if c in df.columns]
    if c3_flow_cols:
        df["air_3b_total_flow_nm3h"] = sum(df[c] for c in c3_flow_cols).round(0)

    c3_pwr_cols = [c for c in ["C321_power_kw", "C322_power_kw", "C323_power_kw",
                                "C311_power_kw", "C312_power_kw"] if c in df.columns]
    if c3_pwr_cols:
        df["air_3b_total_power_kw"] = sum(df[c] for c in c3_pwr_cols).round(1)

    # ── Eau recyclée ─────────────────────────────────────────────────────────
    if ("recycled_water_supply_temp_c" in df.columns
            and "recycled_water_return_temp_c" in df.columns):
        df["recycled_water_delta_t_c"] = (
            df["recycled_water_return_temp_c"] - df["recycled_water_supply_temp_c"]
        ).clip(lower=0.0).round(2)

    if ("recycled_water_flow_m3h" in df.columns
            and "recycled_water_delta_t_c" in df.columns):
        actual  = df["recycled_water_flow_m3h"] * df["recycled_water_delta_t_c"]
        nominal = _RW_FLOW_NOM_M3H * _RW_DELTA_T_NOM_C
        df["recycled_water_efficiency_index"] = (
            actual / nominal
        ).clip(0.30, 1.50).round(3)

    # ── Eau brute ─────────────────────────────────────────────────────────────
    if ("raw_water_makeup_to_recycled_m3h" in df.columns
            and "recycled_water_flow_m3h" in df.columns):
        makeup = df["raw_water_makeup_to_recycled_m3h"].clip(lower=0.0)
        flow   = df["recycled_water_flow_m3h"].clip(lower=1.0)
        df["raw_water_dependency_ratio"] = (makeup / flow).clip(0.0, 1.0).round(4)

    return df


# ---------------------------------------------------------------------------
# Handlers par type d'action (un par anomalie)
# ---------------------------------------------------------------------------

def _apply_furnace_overload(df: pd.DataFrame, mask: pd.Series) -> pd.DataFrame:
    if "furnace_2_63kv_mw" in df.columns:
        df.loc[mask, "furnace_2_63kv_mw"] = (
            df.loc[mask, "furnace_2_63kv_mw"] * 0.88
        ).clip(lower=20.0)
    return _recalculate_aggregates(df)


def _apply_cat_fault(df: pd.DataFrame, mask: pd.Series) -> pd.DataFrame:
    # Mitigation : réduction charge 15 kV sur sous-station A (non critique)
    if "substation_a_15kv_mw" in df.columns:
        df.loc[mask, "substation_a_15kv_mw"] = (
            df.loc[mask, "substation_a_15kv_mw"] * 0.93
        ).clip(lower=4.0)
    if "station_15kv_supply_mw" in df.columns:
        df.loc[mask, "station_15kv_supply_mw"] = (
            df.loc[mask, "station_15kv_supply_mw"] * 0.94
        ).clip(lower=10.0)
    return _recalculate_aggregates(df)


def _apply_overload_15kv(df: pd.DataFrame, mask: pd.Series) -> pd.DataFrame:
    if "station_15kv_supply_mw" in df.columns:
        df.loc[mask, "station_15kv_supply_mw"] = (
            df.loc[mask, "station_15kv_supply_mw"] * 0.90
        ).clip(lower=10.0)
    if "substation_a_15kv_mw" in df.columns:
        df.loc[mask, "substation_a_15kv_mw"] = (
            df.loc[mask, "substation_a_15kv_mw"] * 0.90
        ).clip(lower=4.0)
    return _recalculate_aggregates(df)


def _apply_air_leak(df: pd.DataFrame, mask: pd.Series) -> pd.DataFrame:
    """Simulation colmatage fuite : pression remontée, débit/puissance réduits."""
    if "air_7b_pressure" in df.columns:
        df.loc[mask, "air_7b_pressure"] = (
            df.loc[mask, "air_7b_pressure"] + 0.18
        ).clip(upper=_AIR_7B_PRESSURE_MAX)
    for tag in ("C713", "C714", "C715", "C716", "C717"):
        if f"{tag}_flow_nm3h" in df.columns:
            df.loc[mask, f"{tag}_flow_nm3h"] = (
                df.loc[mask, f"{tag}_flow_nm3h"] * 0.92
            ).clip(lower=0.0)
        if f"{tag}_power_kw" in df.columns:
            # Compresseurs plus efficaces sans fuite → puissance baisse plus que le débit
            df.loc[mask, f"{tag}_power_kw"] = (
                df.loc[mask, f"{tag}_power_kw"] * 0.89
            ).clip(lower=0.0)
    return _recalculate_aggregates(df)


def _apply_compressor_fault(df: pd.DataFrame, mask: pd.Series) -> pd.DataFrame:
    """Simulation remise en service partielle C715."""
    NOM_FLOW_C715  = 2_800.0
    NOM_POWER_C715 = 290.0
    if "C715_flow_nm3h" in df.columns:
        df.loc[mask, "C715_flow_nm3h"] = (
            df.loc[mask, "C715_flow_nm3h"] + NOM_FLOW_C715 * 0.55
        ).clip(upper=NOM_FLOW_C715 * 1.02)
    if "C715_power_kw" in df.columns:
        # Le défaut gonfle la puissance ×1.40 ; la correction ramène à régime nominal
        df.loc[mask, "C715_power_kw"] = (
            df.loc[mask, "C715_power_kw"] * 0.72
        ).clip(upper=NOM_POWER_C715)
    if "air_7b_pressure" in df.columns:
        df.loc[mask, "air_7b_pressure"] = (
            df.loc[mask, "air_7b_pressure"] + 0.06
        ).clip(upper=_AIR_7B_PRESSURE_MAX)
    return _recalculate_aggregates(df)


def _apply_compressor_imbalance(df: pd.DataFrame, mask: pd.Series) -> pd.DataFrame:
    if "C713_flow_nm3h" in df.columns and "C714_flow_nm3h" in df.columns:
        mean_f = (df.loc[mask, "C713_flow_nm3h"] + df.loc[mask, "C714_flow_nm3h"]) / 2.0
        df.loc[mask, "C713_flow_nm3h"] = (
            df.loc[mask, "C713_flow_nm3h"] * 0.70 + mean_f * 0.30
        ).clip(lower=0.0)
        df.loc[mask, "C714_flow_nm3h"] = (
            df.loc[mask, "C714_flow_nm3h"] * 0.70 + mean_f * 0.30
        ).clip(lower=0.0)
    return _recalculate_aggregates(df)


def _apply_vsd_saturation(df: pd.DataFrame, mask: pd.Series) -> pd.DataFrame:
    for tag in ("C321", "C322", "C323"):
        if f"{tag}_speed_pct" in df.columns:
            df.loc[mask, f"{tag}_speed_pct"] = df.loc[mask, f"{tag}_speed_pct"].clip(upper=92.0)
            # Débit proportionnel à la vitesse (loi affinité)
            if f"{tag}_flow_nm3h" in df.columns:
                df.loc[mask, f"{tag}_flow_nm3h"] = (
                    880.0 * df.loc[mask, f"{tag}_speed_pct"] / 100.0
                ).round(0)
        if f"{tag}_power_kw" in df.columns:
            df.loc[mask, f"{tag}_power_kw"] = (
                df.loc[mask, f"{tag}_power_kw"] * 0.93
            ).clip(lower=0.0)
    if "air_3b_pressure" in df.columns:
        df.loc[mask, "air_3b_pressure"] = (
            df.loc[mask, "air_3b_pressure"] + 0.06
        ).clip(upper=_AIR_3B_PRESSURE_MAX)
    return _recalculate_aggregates(df)


def _apply_bad_regulation(df: pd.DataFrame, mask: pd.Series) -> pd.DataFrame:
    for name in ("C311", "C312"):
        if f"{name}_status" in df.columns:
            df.loc[mask, f"{name}_status"] = 0
        if f"{name}_power_kw" in df.columns:
            df.loc[mask, f"{name}_power_kw"] = 0.0
    if "C321_speed_pct" in df.columns:
        df.loc[mask, "C321_speed_pct"] = (
            df.loc[mask, "C321_speed_pct"] + 4.0
        ).clip(upper=97.0)
    return _recalculate_aggregates(df)


def _apply_cooling_fault(df: pd.DataFrame, mask: pd.Series) -> pd.DataFrame:
    """Remise en service pompe EF1 : débit restauré, delta_t amélioré."""
    if "recycled_water_flow_m3h" in df.columns:
        deficit = (_RW_FLOW_NOM_M3H - df.loc[mask, "recycled_water_flow_m3h"])
        df.loc[mask, "recycled_water_flow_m3h"] = (
            df.loc[mask, "recycled_water_flow_m3h"] + deficit * 0.70
        ).clip(1_500, 2_700)
    if "recycled_water_delta_t_c" in df.columns:
        df.loc[mask, "recycled_water_delta_t_c"] = (
            df.loc[mask, "recycled_water_delta_t_c"] * 0.78
        ).clip(lower=2.5)
    # Aligner température retour avec delta_t corrigé
    if ("recycled_water_return_temp_c" in df.columns
            and "recycled_water_supply_temp_c" in df.columns
            and "recycled_water_delta_t_c" in df.columns):
        df.loc[mask, "recycled_water_return_temp_c"] = (
            df.loc[mask, "recycled_water_supply_temp_c"]
            + df.loc[mask, "recycled_water_delta_t_c"]
        )
    # Restauration pression refoulement (pompe EF1 remise en service)
    if "recycled_water_pressure_bar" in df.columns:
        df.loc[mask, "recycled_water_pressure_bar"] = (
            df.loc[mask, "recycled_water_pressure_bar"] * 1.20
        ).clip(upper=4.0)
    return _recalculate_aggregates(df)


def _apply_legionella_risk(df: pd.DataFrame, mask: pd.Series) -> pd.DataFrame:
    if "chemical_treatment_index" in df.columns:
        df.loc[mask, "chemical_treatment_index"] = (
            df.loc[mask, "chemical_treatment_index"] + 0.14
        ).clip(upper=1.0)
    if "legionella_risk_index" in df.columns:
        df.loc[mask, "legionella_risk_index"] = (
            df.loc[mask, "legionella_risk_index"] * 0.62
        ).clip(lower=0.0)
    if "recycled_water_return_temp_c" in df.columns:
        df.loc[mask, "recycled_water_return_temp_c"] = (
            df.loc[mask, "recycled_water_return_temp_c"] - 1.5
        ).clip(lower=20.0)
    return _recalculate_aggregates(df)


def _apply_low_basin(df: pd.DataFrame, mask: pd.Series) -> pd.DataFrame:
    if "basin_b1_level_pct" in df.columns:
        df.loc[mask, "basin_b1_level_pct"] = (
            df.loc[mask, "basin_b1_level_pct"] + 18.0
        ).clip(upper=100.0)
    if "basin_b1_volume_m3" in df.columns:
        df["basin_b1_volume_m3"] = (df["basin_b1_level_pct"] / 100.0 * 800.0).round(0)
    if "emergency_cooling_capacity_m3h" in df.columns:
        df.loc[mask, "emergency_cooling_capacity_m3h"] = (
            df.loc[mask, "emergency_cooling_capacity_m3h"] * 1.15
        )
    return _recalculate_aggregates(df)


def _apply_raw_water_overconsumption(df: pd.DataFrame, mask: pd.Series) -> pd.DataFrame:
    if "raw_water_makeup_to_recycled_m3h" in df.columns:
        df.loc[mask, "raw_water_makeup_to_recycled_m3h"] = (
            df.loc[mask, "raw_water_makeup_to_recycled_m3h"] * 0.75
        ).clip(lower=60.0)
    if "raw_water_flow_m3h" in df.columns:
        df.loc[mask, "raw_water_flow_m3h"] = (
            df.loc[mask, "raw_water_flow_m3h"] * 0.76
        ).clip(lower=60.0)
    return _recalculate_aggregates(df)


def _apply_generic(df: pd.DataFrame, mask: pd.Series) -> pd.DataFrame:
    if "total_plant_power_mw" in df.columns:
        df.loc[mask, "total_plant_power_mw"] = (
            df.loc[mask, "total_plant_power_mw"] * 0.97
        )
    return _recalculate_aggregates(df)


_HANDLERS: dict[str, Any] = {
    "furnace_overload":          _apply_furnace_overload,
    "cat_fault":                 _apply_cat_fault,
    "overload_15kv":             _apply_overload_15kv,
    "air_leak":                  _apply_air_leak,
    "compressor_fault":          _apply_compressor_fault,
    "compressor_imbalance":      _apply_compressor_imbalance,
    "vsd_saturation":            _apply_vsd_saturation,
    "bad_regulation":            _apply_bad_regulation,
    "cooling_fault":             _apply_cooling_fault,
    "legionella_risk":           _apply_legionella_risk,
    "low_basin":                 _apply_low_basin,
    "raw_water_overconsumption": _apply_raw_water_overconsumption,
    "unknown":                   _apply_generic,
}


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def apply_simulated_recommendation(
    df: pd.DataFrame,
    recommendation: Recommendation,
) -> pd.DataFrame:
    """
    Applique l'effet simulé de la recommandation sur UNE COPIE du DataFrame.
    Le DataFrame original n'est JAMAIS modifié.
    """
    df_copy     = df.copy()
    action_type = _detect_action_type(recommendation)
    mask        = _get_action_mask(df_copy)
    handler     = _HANDLERS.get(action_type, _apply_generic)
    return handler(df_copy, mask)


def compare_before_after(
    before_df: pd.DataFrame,
    after_df: pd.DataFrame,
) -> dict[str, Any]:
    """
    Calcule les variations clés entre before_df et after_df.
    Retourne un dict avec les deltas pour les métriques les plus importantes.
    """
    result: dict[str, Any] = {}

    cols_of_interest = [
        "total_plant_power_mw",
        "furnace_2_63kv_mw",
        "grid_import_63kv_mw",
        "station_15kv_supply_mw",
        "air_7b_pressure",
        "air_7b_total_flow_nm3h",
        "air_7b_total_power_kw",
        "air_7b_specific_energy_kwh_per_nm3",
        "air_3b_pressure",
        "C321_speed_pct",
        "C715_flow_nm3h",
        "recycled_water_flow_m3h",
        "recycled_water_delta_t_c",
        "recycled_water_efficiency_index",
        "legionella_risk_index",
        "chemical_treatment_index",
        "basin_b1_level_pct",
        "raw_water_dependency_ratio",
        "energy_cost_xpf",
    ]

    deltas: dict[str, dict] = {}
    for col in cols_of_interest:
        if col in before_df.columns and col in after_df.columns:
            b = float(before_df[col].mean())
            a = float(after_df[col].mean())
            d = a - b
            pct = d / max(abs(b), 1e-9) * 100.0
            deltas[col] = {
                "before_mean": round(b, 4),
                "after_mean":  round(a, 4),
                "delta":       round(d, 4),
                "delta_pct":   round(pct, 2),
            }
    result["metrics"] = deltas

    if "energy_cost_xpf" in deltas:
        result["energy_saving_xpf"] = round(
            -deltas["energy_cost_xpf"]["delta"] * len(before_df), 0
        )
    else:
        result["energy_saving_xpf"] = 0.0

    if "air_7b_pressure" in deltas:
        result["pressure_improvement_7b"] = round(deltas["air_7b_pressure"]["delta"], 3)
    if "recycled_water_flow_m3h" in deltas:
        result["flow_improvement_water"] = round(deltas["recycled_water_flow_m3h"]["delta"], 1)

    return result


def build_simulation_summary(
    before_df: pd.DataFrame,
    after_df: pd.DataFrame,
    recommendation: Recommendation,
    anomalies: list[Anomaly] | None = None,
) -> dict[str, Any]:
    """
    Construit le résumé complet avant / après en relançant le pipeline IA.
    """
    from modules.detection import detect_anomalies
    from modules.scoring import build_scoring_summary
    from modules.business_value import compute_total_business_impact
    from modules.recommendations import generate_recommendations

    before_anom = anomalies if anomalies is not None else detect_anomalies(before_df)
    before_scor = build_scoring_summary(before_anom)
    before_recs = generate_recommendations(before_anom, scoring_summary=before_scor)
    before_biz  = compute_total_business_impact(before_anom, before_recs)
    before_score = before_scor.get("global_score", 0.0)
    before_loss  = before_biz.get("total_loss_xpf", 0.0)

    after_anom  = detect_anomalies(after_df)
    after_scor  = build_scoring_summary(after_anom)
    after_recs  = generate_recommendations(after_anom, scoring_summary=after_scor)
    after_biz   = compute_total_business_impact(after_anom, after_recs)
    after_score = after_scor.get("global_score", 0.0)
    after_loss  = after_biz.get("total_loss_xpf", 0.0)

    rec_saving    = float(_rec_attr(recommendation, "estimated_saving_xpf", 0))
    actual_saving = max(before_loss - after_loss, rec_saving * 0.5)

    comparison  = compare_before_after(before_df, after_df)
    action_type = _detect_action_type(recommendation)
    key_metric  = _KEY_METRICS.get(action_type, "total_plant_power_mw")
    if key_metric not in before_df.columns:
        key_metric = "total_plant_power_mw"

    return {
        "before_df":            before_df,
        "after_df":             after_df,
        "applied_action":       _rec_attr(recommendation, "action_title", ""),
        "expected_effect":      _rec_attr(recommendation, "expected_effect", ""),
        "before_score":         round(before_score, 1),
        "after_score":          round(after_score, 1),
        "score_improvement":    round(before_score - after_score, 1),
        "before_loss_xpf":      round(before_loss, 0),
        "after_loss_xpf":       round(after_loss, 0),
        "estimated_saving_xpf": round(actual_saving, 0),
        "before_n_anomalies":   len(before_anom),
        "after_n_anomalies":    len(after_anom),
        "key_metric":           key_metric,
        "action_type":          action_type,
        "comparison":           comparison,
        "simulation_note": (
            "Simulation uniquement — aucune commande industrielle réelle. "
            "Toute action terrain requiert validation humaine."
        ),
    }


def get_simulatable_recommendations(
    recommendations: list[Recommendation],
) -> list[Recommendation]:
    """
    Filtre les recommandations pour lesquelles une simulation est disponible.
    Une rec par type d'action pour éviter les doublons dans l'UI.
    """
    result: list[Recommendation] = []
    seen_types: set[str] = set()
    for r in recommendations:
        action_type = _detect_action_type(r)
        if action_type not in seen_types:
            result.append(r)
            seen_types.add(action_type)
    return result
