"""
Scénarios industriels simulés — modules/scenarios.py

Chaque scénario représente une situation dégradée ou anormale réaliste,
basée sur la physique des équipements et la logique process.

RÈGLES :
- apply_scenario() travaille toujours sur une copie du DataFrame.
- Les modifications n'affectent que la fenêtre temporelle [40 %, 70 %[
  de la série (rows 38–66 sur 96 points).
- _recompute() recalcule les agrégats dérivés après toute modification.
"""

import numpy as np
import pandas as pd
from typing import Callable

from modules.data_generator import (
    ELECTRICITY_TARIFF_XPF_KWH,
    INTERVAL_MIN,
    _C7_NAMES,
    _RW_NOM_FLOW,
    _RW_DELTA_T_NOM,
    _B0_CAPACITY_M3,
    _B1_CAPACITY_M3,
)

# ─────────────────────────────────────────────────────────────────────────────
# Registre interne
# ─────────────────────────────────────────────────────────────────────────────

_REGISTRY: dict[str, tuple[str, Callable]] = {}


def _reg(name: str, description: str) -> Callable:
    def decorator(fn: Callable) -> Callable:
        _REGISTRY[name] = (description, fn)
        return fn
    return decorator


# ─────────────────────────────────────────────────────────────────────────────
# Métadonnées IA — type d'anomalie et systèmes affectés par scénario
# ─────────────────────────────────────────────────────────────────────────────

_ANOMALY_META: dict[str, tuple[str, str]] = {
    "pic_four_2":                 ("furnace_overload",          "electricity"),
    "perte_partielle_cat":        ("cat_fault",                 "electricity"),
    "surcharge_15kv":             ("overload_15kv",             "electricity"),
    "fuite_air_7b":               ("air_leak",                  "air_7b"),
    "defaut_c715":                ("compressor_fault",          "air_7b"),
    "desequilibre_c7":            ("compressor_imbalance",      "air_7b"),
    "saturation_vsd_3b":          ("vsd_saturation",            "air_3b"),
    "mauvaise_regulation_3b":     ("bad_regulation",            "air_3b"),
    "defaut_refroidissement":     ("cooling_fault",             "water,electricity"),
    "risque_legionelle":          ("legionella_risk",           "water"),
    "baisse_bassin_b1":           ("low_basin",                 "water"),
    "forte_dependance_eau_brute": ("raw_water_overconsumption", "water"),
    "multi_crise":                ("multi_system_fault",        "electricity,air_7b,water"),
}


# ─────────────────────────────────────────────────────────────────────────────
# Fenêtre temporelle
# ─────────────────────────────────────────────────────────────────────────────

def _time_window(df: pd.DataFrame, start_ratio: float = 0.4, end_ratio: float = 0.7) -> slice:
    """Retourne un slice positionnel [40 %, 70 %[ sur len(df)."""
    n = len(df)
    return slice(int(n * start_ratio), int(n * end_ratio))


# ─────────────────────────────────────────────────────────────────────────────
# Recalcul des agrégats
# ─────────────────────────────────────────────────────────────────────────────

def _recompute(df: pd.DataFrame) -> pd.DataFrame:
    """Recalcule les colonnes dérivées après modification des colonnes source."""
    # Électricité
    furnace_sum = (
        df["furnace_1_63kv_mw"] + df["furnace_2_63kv_mw"] + df["furnace_3_63kv_mw"]
    )
    df["total_63kv_bus_mw"] = (furnace_sum + df["station_15kv_supply_mw"]).round(3)
    df["total_plant_power_mw"] = df["total_63kv_bus_mw"]
    df["grid_import_63kv_mw"] = np.clip(
        df["total_63kv_bus_mw"] - df["cat_generation_63kv_mw"], 0.0, 200.0
    ).round(3)
    df["energy_cost_xpf"] = (
        df["total_plant_power_mw"] * 1_000.0 * (INTERVAL_MIN / 60.0) * ELECTRICITY_TARIFF_XPF_KWH
    ).round(0)

    # Air 7 bars
    total_7b_flow = sum(df[f"{n}_flow_nm3h"] for n in _C7_NAMES)
    total_7b_power = sum(df[f"{n}_power_kw"] for n in _C7_NAMES)
    df["air_7b_total_flow_nm3h"] = total_7b_flow.round(0)
    df["air_7b_total_power_kw"] = total_7b_power.round(1)
    df["air_7b_specific_energy_kwh_per_nm3"] = np.where(
        total_7b_flow > 100,
        np.clip(total_7b_power / total_7b_flow, 0.08, 0.20),
        0.0,
    ).round(4)

    # Air 3 bars
    total_3b_flow = df["C321_flow_nm3h"] + df["C322_flow_nm3h"] + df["C323_flow_nm3h"]
    total_3b_power = (
        df["C321_power_kw"] + df["C322_power_kw"] + df["C323_power_kw"]
        + df["C311_power_kw"] + df["C312_power_kw"]
    )
    df["air_3b_total_flow_nm3h"] = total_3b_flow.round(0)
    df["air_3b_total_power_kw"] = total_3b_power.round(1)

    # Eau recyclée
    df["recycled_water_return_temp_c"] = (
        df["recycled_water_supply_temp_c"] + df["recycled_water_delta_t_c"]
    ).round(2)
    nom_cooling = float(_RW_NOM_FLOW * _RW_DELTA_T_NOM)
    df["recycled_water_efficiency_index"] = np.clip(
        df["recycled_water_flow_m3h"] * df["recycled_water_delta_t_c"] / nom_cooling,
        0.20, 1.50,
    ).round(3)

    # Eau brute
    df["raw_water_dependency_ratio"] = np.clip(
        df["raw_water_makeup_to_recycled_m3h"] / df["recycled_water_flow_m3h"],
        0.01, 0.25,
    ).round(4)
    df["basin_b0_volume_m3"] = (df["basin_b0_level_pct"] / 100.0 * _B0_CAPACITY_M3).round(0)
    df["basin_b1_volume_m3"] = (df["basin_b1_level_pct"] / 100.0 * _B1_CAPACITY_M3).round(0)
    df["emergency_cooling_available"] = (
        (df["basin_b0_level_pct"] > 20.0) | (df["basin_b1_level_pct"] > 20.0)
    )

    return df


# ─────────────────────────────────────────────────────────────────────────────
# SCÉNARIOS ÉLECTRICITÉ
# ─────────────────────────────────────────────────────────────────────────────

@_reg(
    "pic_four_2",
    "Pic de charge four 2 (+28 %) — surcharge 63 kV, coût énergie en hausse",
)
def _pic_four_2(df: pd.DataFrame) -> pd.DataFrame:
    w = _time_window(df)
    win_idx = df.index[w]
    df.loc[win_idx, "furnace_2_63kv_mw"] = np.clip(
        df.loc[win_idx, "furnace_2_63kv_mw"] * 1.28, 0.0, 75.0
    ).round(3)
    return _recompute(df)


@_reg(
    "perte_partielle_cat",
    "Perte partielle centrale CAT (~60 %) — import réseau compense la baisse",
)
def _perte_partielle_cat(df: pd.DataFrame) -> pd.DataFrame:
    w = _time_window(df)
    win_idx = df.index[w]
    df.loc[win_idx, "cat_generation_63kv_mw"] = np.clip(
        df.loc[win_idx, "cat_generation_63kv_mw"] * 0.40, 0.0, 130.0
    ).round(3)
    return _recompute(df)


@_reg(
    "surcharge_15kv",
    "Surcharge poste 15 kV (+22 %) — demande process anormalement élevée",
)
def _surcharge_15kv(df: pd.DataFrame) -> pd.DataFrame:
    w = _time_window(df)
    win_idx = df.index[w]
    for col in ("substation_a_15kv_mw", "substation_b_15kv_mw", "substation_c_15kv_mw"):
        df.loc[win_idx, col] = (df.loc[win_idx, col] * 1.22).round(3)
    df.loc[win_idx, "station_15kv_supply_mw"] = (
        df.loc[win_idx, "substation_a_15kv_mw"]
        + df.loc[win_idx, "substation_b_15kv_mw"]
        + df.loc[win_idx, "substation_c_15kv_mw"]
    ).round(3)
    return _recompute(df)


# ─────────────────────────────────────────────────────────────────────────────
# SCÉNARIOS AIR 7 BARS
# ─────────────────────────────────────────────────────────────────────────────

@_reg(
    "fuite_air_7b",
    "Fuite réseau air 7 bars — pression -0.42 bar, compresseurs en surcharge +18 %",
)
def _fuite_air_7b(df: pd.DataFrame) -> pd.DataFrame:
    w = _time_window(df)
    win_idx = df.index[w]
    df.loc[win_idx, "air_7b_pressure"] = np.clip(
        df.loc[win_idx, "air_7b_pressure"] - 0.42, 5.8, 7.5
    ).round(3)
    for name in _C7_NAMES:
        running_mask = (df.loc[win_idx, f"{name}_status"] == 1).values
        running_in_win = win_idx[running_mask]
        df.loc[running_in_win, f"{name}_flow_nm3h"] = np.clip(
            df.loc[running_in_win, f"{name}_flow_nm3h"] * 1.18, 0.0, 3_600.0
        ).round(0)
        df.loc[running_in_win, f"{name}_power_kw"] = np.clip(
            df.loc[running_in_win, f"{name}_power_kw"] * 1.22, 0.0, 400.0
        ).round(1)
    df = _recompute(df)
    # Renforcement signature énergétique : la fuite force un SE plus élevé
    df.loc[win_idx, "air_7b_specific_energy_kwh_per_nm3"] = np.clip(
        df.loc[win_idx, "air_7b_specific_energy_kwh_per_nm3"] * 1.10, 0.08, 0.20
    ).round(4)
    return df


@_reg(
    "defaut_c715",
    "Défaut compresseur C715 — débit -65 %, puissance +40 % (cavitation/encrassement)",
)
def _defaut_c715(df: pd.DataFrame) -> pd.DataFrame:
    w = _time_window(df)
    win_idx = df.index[w]
    running_mask = (df.loc[win_idx, "C715_status"] == 1).values
    running_in_win = win_idx[running_mask]
    df.loc[running_in_win, "C715_flow_nm3h"] = np.clip(
        df.loc[running_in_win, "C715_flow_nm3h"] * 0.35, 0.0, 3_600.0
    ).round(0)
    df.loc[running_in_win, "C715_power_kw"] = np.clip(
        df.loc[running_in_win, "C715_power_kw"] * 1.40, 0.0, 420.0
    ).round(1)
    df.loc[win_idx, "air_7b_pressure"] = np.clip(
        df.loc[win_idx, "air_7b_pressure"] - 0.18, 5.8, 7.5
    ).round(3)
    df = _recompute(df)
    # Renforcement signature énergétique : défaut crée une inefficacité mesurable
    df.loc[win_idx, "air_7b_specific_energy_kwh_per_nm3"] = np.clip(
        df.loc[win_idx, "air_7b_specific_energy_kwh_per_nm3"] * 1.10, 0.08, 0.20
    ).round(4)
    return df


@_reg(
    "desequilibre_c7",
    "Déséquilibre compresseurs 7 bars — C713 surchargé (+22 %), C714 sous-chargé (-28 %)",
)
def _desequilibre_c7(df: pd.DataFrame) -> pd.DataFrame:
    w = _time_window(df)
    win_idx = df.index[w]
    run_713 = win_idx[(df.loc[win_idx, "C713_status"] == 1).values]
    run_714 = win_idx[(df.loc[win_idx, "C714_status"] == 1).values]
    df.loc[run_713, "C713_flow_nm3h"] = np.clip(
        df.loc[run_713, "C713_flow_nm3h"] * 1.22, 0.0, 3_580.0
    ).round(0)
    df.loc[run_713, "C713_power_kw"] = np.clip(
        df.loc[run_713, "C713_power_kw"] * 1.18, 0.0, 400.0
    ).round(1)
    df.loc[run_714, "C714_flow_nm3h"] = np.clip(
        df.loc[run_714, "C714_flow_nm3h"] * 0.72, 0.0, 3_580.0
    ).round(0)
    df.loc[run_714, "C714_power_kw"] = np.clip(
        df.loc[run_714, "C714_power_kw"] * 0.80, 0.0, 400.0
    ).round(1)
    return _recompute(df)


# ─────────────────────────────────────────────────────────────────────────────
# SCÉNARIOS AIR 3 BARS
# ─────────────────────────────────────────────────────────────────────────────

@_reg(
    "saturation_vsd_3b",
    "Saturation VSD air 3 bars — tous à ~100 %, pression insuffisante malgré max",
)
def _saturation_vsd_3b(df: pd.DataFrame) -> pd.DataFrame:
    w = _time_window(df)
    win_idx = df.index[w]
    for name, spd in [("C321", 99.0), ("C322", 98.5), ("C323", 97.0)]:
        df.loc[win_idx, f"{name}_speed_pct"] = spd
        df.loc[win_idx, f"{name}_flow_nm3h"] = round(880.0 * spd / 100.0, 0)
        df.loc[win_idx, f"{name}_power_kw"] = round(92.0 * (0.12 + 0.88 * spd / 100.0), 1)
    df.loc[win_idx, "air_3b_pressure"] = np.clip(
        df.loc[win_idx, "air_3b_pressure"] * 0.85, 2.0, 3.5
    ).round(3)
    return _recompute(df)


@_reg(
    "mauvaise_regulation_3b",
    "Mauvaise régulation air 3 bars — C311 démarré, VSD inutilement sous-chargés",
)
def _mauvaise_regulation_3b(df: pd.DataFrame) -> pd.DataFrame:
    w = _time_window(df)
    win_idx = df.index[w]
    df.loc[win_idx, "C311_status"] = 1
    df.loc[win_idx, "C311_power_kw"] = 55.0
    for name, factor in [("C321", 0.55), ("C322", 0.50), ("C323", 0.45)]:
        spd = np.clip(df.loc[win_idx, f"{name}_speed_pct"] * factor, 0.0, 100.0).round(1)
        df.loc[win_idx, f"{name}_speed_pct"] = spd
        df.loc[win_idx, f"{name}_flow_nm3h"] = (880.0 * spd / 100.0).round(0)
        df.loc[win_idx, f"{name}_power_kw"] = (92.0 * (0.12 + 0.88 * spd / 100.0)).round(1)
    df.loc[win_idx, "air_3b_pressure"] = np.clip(
        df.loc[win_idx, "air_3b_pressure"] * 1.06, 2.5, 3.6
    ).round(3)
    return _recompute(df)


# ─────────────────────────────────────────────────────────────────────────────
# SCÉNARIOS EAU RECYCLÉE
# ─────────────────────────────────────────────────────────────────────────────

@_reg(
    "defaut_refroidissement",
    "Défaut refroidissement — panne pompe EF1, débit -32 %, T° retour excessive",
)
def _defaut_refroidissement(df: pd.DataFrame) -> pd.DataFrame:
    w = _time_window(df)
    win_idx = df.index[w]
    # Contrainte thermique : les fours réduisent légèrement leur puissance
    df.loc[win_idx, "furnace_1_63kv_mw"] = np.clip(
        df.loc[win_idx, "furnace_1_63kv_mw"] * 0.97, 0.0, 160.0 / 3
    ).round(3)
    df.loc[win_idx, "furnace_2_63kv_mw"] = np.clip(
        df.loc[win_idx, "furnace_2_63kv_mw"] * 0.96, 0.0, 160.0 / 3
    ).round(3)
    df.loc[win_idx, "furnace_3_63kv_mw"] = np.clip(
        df.loc[win_idx, "furnace_3_63kv_mw"] * 0.97, 0.0, 160.0 / 3
    ).round(3)
    df.loc[win_idx, "recycled_water_flow_m3h"] = np.clip(
        df.loc[win_idx, "recycled_water_flow_m3h"] * 0.68, 1_000.0, 2_700.0
    ).round(0)
    df.loc[win_idx, "recycled_water_delta_t_c"] = np.clip(
        df.loc[win_idx, "recycled_water_delta_t_c"] * 1.47, 3.0, 12.0
    ).round(2)
    df.loc[win_idx, "cold_water_pump_1_power_kw"] = 0.0
    df.loc[win_idx, "recycled_water_pressure_bar"] = np.clip(
        df.loc[win_idx, "recycled_water_pressure_bar"] * 0.78, 2.0, 4.0
    ).round(2)
    return _recompute(df)


@_reg(
    "risque_legionelle",
    "Risque légionelle — T° retour +4 °C, traitement chimique défaillant (-70 %)",
)
def _risque_legionelle(df: pd.DataFrame) -> pd.DataFrame:
    w = _time_window(df)
    win_idx = df.index[w]
    df.loc[win_idx, "recycled_water_delta_t_c"] = np.clip(
        df.loc[win_idx, "recycled_water_delta_t_c"] + 4.0, 3.0, 14.0
    ).round(2)
    df.loc[win_idx, "legionella_risk_index"] = np.clip(
        df.loc[win_idx, "legionella_risk_index"] * 2.8, 0.0, 1.0
    ).round(3)
    df.loc[win_idx, "chemical_treatment_index"] = np.clip(
        df.loc[win_idx, "chemical_treatment_index"] * 0.30, 0.0, 1.0
    ).round(3)
    return _recompute(df)


# ─────────────────────────────────────────────────────────────────────────────
# SCÉNARIOS EAU BRUTE
# ─────────────────────────────────────────────────────────────────────────────

@_reg(
    "baisse_bassin_b1",
    "Baisse bassin B1 < 20 % — secours refroidissement compromis",
)
def _baisse_bassin_b1(df: pd.DataFrame) -> pd.DataFrame:
    w = _time_window(df)
    win_idx = df.index[w]
    n_win = len(win_idx)
    rng = np.random.default_rng(999)
    df.loc[win_idx, "basin_b1_level_pct"] = np.clip(
        rng.uniform(10.0, 18.0, n_win), 0.0, 100.0
    ).round(1)
    df.loc[win_idx, "raw_water_makeup_to_recycled_m3h"] = np.clip(
        df.loc[win_idx, "raw_water_makeup_to_recycled_m3h"] * 1.60, 70.0, 220.0
    ).round(1)
    # Dégradation débit refroidissement quand B1 très bas (< 15 %)
    very_low_mask = (df.loc[win_idx, "basin_b1_level_pct"] < 15.0).values
    very_low_idx = win_idx[very_low_mask]
    if len(very_low_idx) > 0:
        df.loc[very_low_idx, "recycled_water_flow_m3h"] = np.clip(
            df.loc[very_low_idx, "recycled_water_flow_m3h"] * 0.92, 1_000.0, 2_700.0
        ).round(0)
    return _recompute(df)


@_reg(
    "forte_dependance_eau_brute",
    "Forte dépendance eau brute (×3) — fuite réseau appoint, bassins en baisse",
)
def _forte_dependance_eau_brute(df: pd.DataFrame) -> pd.DataFrame:
    w = _time_window(df)
    win_idx = df.index[w]
    df.loc[win_idx, "raw_water_makeup_to_recycled_m3h"] = np.clip(
        df.loc[win_idx, "raw_water_makeup_to_recycled_m3h"] * 3.2, 70.0, 400.0
    ).round(1)
    df.loc[win_idx, "raw_water_flow_m3h"] = np.clip(
        df.loc[win_idx, "raw_water_flow_m3h"] * 3.2, 70.0, 420.0
    ).round(1)
    df.loc[win_idx, "basin_b0_level_pct"] = np.clip(
        df.loc[win_idx, "basin_b0_level_pct"] - 8.0, 0.0, 100.0
    ).round(1)
    df.loc[win_idx, "basin_b1_level_pct"] = np.clip(
        df.loc[win_idx, "basin_b1_level_pct"] - 12.0, 0.0, 100.0
    ).round(1)
    return _recompute(df)


# ─────────────────────────────────────────────────────────────────────────────
# SCÉNARIO COMPLEXE
# ─────────────────────────────────────────────────────────────────────────────

@_reg(
    "multi_crise",
    "Multi-crise — pic four 2 + fuite air 7b + défaut refroidissement simultanés",
)
def _multi_crise(df: pd.DataFrame) -> pd.DataFrame:
    w = _time_window(df)
    win_idx = df.index[w]
    # 1 — Pic four 2
    df.loc[win_idx, "furnace_2_63kv_mw"] = np.clip(
        df.loc[win_idx, "furnace_2_63kv_mw"] * 1.28, 0.0, 75.0
    ).round(3)
    # 2 — Fuite air 7 bars
    df.loc[win_idx, "air_7b_pressure"] = np.clip(
        df.loc[win_idx, "air_7b_pressure"] - 0.42, 5.8, 7.5
    ).round(3)
    for name in _C7_NAMES:
        running_mask = (df.loc[win_idx, f"{name}_status"] == 1).values
        running_in_win = win_idx[running_mask]
        df.loc[running_in_win, f"{name}_flow_nm3h"] = np.clip(
            df.loc[running_in_win, f"{name}_flow_nm3h"] * 1.18, 0.0, 3_600.0
        ).round(0)
        df.loc[running_in_win, f"{name}_power_kw"] = np.clip(
            df.loc[running_in_win, f"{name}_power_kw"] * 1.22, 0.0, 400.0
        ).round(1)
    # 3 — Défaut refroidissement
    df.loc[win_idx, "recycled_water_flow_m3h"] = np.clip(
        df.loc[win_idx, "recycled_water_flow_m3h"] * 0.68, 1_000.0, 2_700.0
    ).round(0)
    df.loc[win_idx, "recycled_water_delta_t_c"] = np.clip(
        df.loc[win_idx, "recycled_water_delta_t_c"] * 1.47, 3.0, 12.0
    ).round(2)
    df.loc[win_idx, "cold_water_pump_1_power_kw"] = 0.0
    df.loc[win_idx, "recycled_water_pressure_bar"] = np.clip(
        df.loc[win_idx, "recycled_water_pressure_bar"] * 0.78, 2.0, 4.0
    ).round(2)
    return _recompute(df)


# ─────────────────────────────────────────────────────────────────────────────
# API publique
# ─────────────────────────────────────────────────────────────────────────────

def list_available_scenarios() -> list[dict]:
    """Retourne la liste des scénarios disponibles avec leur description."""
    return [{"name": k, "description": v[0]} for k, v in _REGISTRY.items()]


def apply_scenario(df: pd.DataFrame, scenario_name: str) -> pd.DataFrame:
    """
    Applique un scénario industriel sur une copie du DataFrame nominal.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame nominal issu de generate_mock_plant_data(). Non modifié.
    scenario_name : str
        Identifiant du scénario (cf. list_available_scenarios()).

    Returns
    -------
    pd.DataFrame
        Copie avec le scénario appliqué + colonnes scenario_name,
        scenario_description, anomaly_flag, anomaly_type, affected_systems.

    Raises
    ------
    ValueError
        Si scenario_name est inconnu.
    """
    if scenario_name not in _REGISTRY:
        raise ValueError(
            f"Scénario inconnu : '{scenario_name}'. "
            f"Disponibles : {list(_REGISTRY.keys())}"
        )
    description, fn = _REGISTRY[scenario_name]
    out = fn(df.copy())
    out["scenario_name"] = scenario_name
    out["scenario_description"] = description
    # Métadonnées IA
    anomaly_type, affected_systems = _ANOMALY_META[scenario_name]
    out["anomaly_flag"] = False
    win_idx = out.index[_time_window(out)]
    out.loc[win_idx, "anomaly_flag"] = True
    out["anomaly_type"] = anomaly_type
    out["affected_systems"] = affected_systems
    return out
