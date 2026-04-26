"""
Moteur de détection d'anomalies industrielles — rule-based, explicable.

Détecte 12 types d'anomalies sur 4 domaines :
  • Électricité (3)   : pic four, perte CAT, surcharge 15 kV
  • Air 7 bars (3)    : fuite réseau, défaut C715, déséquilibre C713/C714
  • Air 3 bars (2)    : saturation VSD, mauvaise régulation
  • Eau recyclée (2)  : défaut refroidissement, risque légionelle
  • Eau brute (2)     : niveau B1 critique, forte dépendance eau brute

Aucun modèle ML. Chaque détection produit une preuve chiffrée explicable.
Les seuils sont centralisés dans THRESHOLDS et modifiables sans toucher la logique.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

# Type alias — an anomaly is a plain dict produced by build_anomaly()
Anomaly = dict[str, Any]

# ─────────────────────────────────────────────────────────────────────────────
# Seuils de détection — modifiez ici pour calibrer sur une vraie usine
# ─────────────────────────────────────────────────────────────────────────────

THRESHOLDS: dict[str, float] = {
    # ── Électricité ──────────────────────────────────────────────────────────
    "furnace_2_max_mw":        62.0,    # pic four 2     (nominal max ~54 MW, nameplate 55 MW)
    "cat_min_mw":              70.0,    # perte CAT      (nominal min ~80 MW)
    "station_15kv_max_mw":     26.5,    # surcharge 15 kV (nominal max ~24.6 MW)
    # ── Air 7 bars ───────────────────────────────────────────────────────────
    "air_7b_pressure_low_bar":  6.55,   # fuite/défaut   (nominal min 6.65 bar)
    "air_7b_se_high":           0.131,  # SE haute       (nominal max 0.130 kWh/Nm³)
    "c715_flow_low_nm3h":    1_500.0,   # défaut C715    (nominal running min ~2700)
    "c7_imbalance_ratio":       1.50,   # C713/C714      (nominal max ~1.08)
    # ── Air 3 bars ───────────────────────────────────────────────────────────
    "vsd_3b_sat_speed_pct":    97.0,    # saturation VSD (%)
    "air_3b_pressure_low_bar":  2.62,   # sat. pression  (nominal min 2.65 bar)
    "c311_on_min_rows":          3.0,   # C311 actif min n lignes
    # ── Eau recyclée ─────────────────────────────────────────────────────────
    "rw_flow_low_m3h":        1_800.0,  # défaut refroid. (seuil débit très bas)
    "rw_delta_t_high_c":        8.0,    # défaut refroid. (nominal max 7.5 °C)
    "legionella_high":          0.65,   # légionelle     (nominal max ~0.45)
    # ── Eau brute ────────────────────────────────────────────────────────────
    "basin_b1_critical_pct":   20.0,    # B1 critique    (%)
    "raw_dependency_high":      0.12,   # forte dépend.  (nominal max 0.08)
    "raw_makeup_high_m3h":    165.0,    # forte dépend.  (nominal max 130 m³/h)
    # ── Sensibilité ──────────────────────────────────────────────────────────
    "min_rows_trigger":          3.0,   # lignes min pour déclencher une anomalie
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers internes
# ─────────────────────────────────────────────────────────────────────────────

def _has_metadata(df: pd.DataFrame) -> bool:
    return "anomaly_flag" in df.columns and "anomaly_type" in df.columns


def _meta_confirms(df: pd.DataFrame, expected_type: str) -> bool:
    """Retourne True si les colonnes metadata confirment le type attendu."""
    if not _has_metadata(df):
        return False
    return (df["anomaly_type"] == expected_type).any()


def _boosted_confidence(base: float, df: pd.DataFrame, expected_type: str) -> float:
    """Augmente le score si les metadata confirment le type d'anomalie."""
    if _meta_confirms(df, expected_type):
        return min(0.99, base + 0.07)
    return base


def build_anomaly(
    anomaly_id: str,
    df: pd.DataFrame,
    condition_mask: pd.Series,
    domain: str,
    asset: str,
    severity: str,
    title: str,
    description: str,
    evidence: dict[str, Any],
    probable_causes: list[str],
    confidence_score: float,
    affected_systems: str,
    anomaly_type: str,
) -> dict[str, Any]:
    """Construit le dictionnaire standard d'une anomalie détectée."""
    anom_idx = condition_mask[condition_mask].index
    ts = df["timestamp"]
    return {
        "id":               anomaly_id,
        "timestamp_start":  str(ts.loc[anom_idx[0]]),
        "timestamp_end":    str(ts.loc[anom_idx[-1]]),
        "domain":           domain,
        "asset":            asset,
        "severity":         severity,
        "title":            title,
        "description":      description,
        "evidence":         evidence,
        "probable_causes":  probable_causes,
        "confidence_score": round(float(confidence_score), 3),
        "affected_systems": affected_systems,
        "anomaly_type":     anomaly_type,
    }


# ─────────────────────────────────────────────────────────────────────────────
# DÉTECTIONS ÉLECTRICITÉ
# ─────────────────────────────────────────────────────────────────────────────

def _detect_pic_four_2(df: pd.DataFrame) -> dict[str, Any] | None:
    """Pic de charge sur le four 2 — puissance > seuil nominal."""
    thr = THRESHOLDS["furnace_2_max_mw"]
    cond = df["furnace_2_63kv_mw"] > thr
    if cond.sum() < THRESHOLDS["min_rows_trigger"]:
        return None

    win = df[cond]
    max_f2    = float(df["furnace_2_63kv_mw"].max())
    median_f2 = float(df["furnace_2_63kv_mw"].median())

    evidence = {
        "max_furnace_2_mw":    round(max_f2, 3),
        "median_furnace_2_mw": round(median_f2, 3),
        "threshold_mw":        thr,
        "n_rows_above":        int(cond.sum()),
        "avg_bus_mw":          round(float(win["total_63kv_bus_mw"].mean()), 3),
        "avg_energy_cost_xpf": round(float(win["energy_cost_xpf"].mean()), 0),
    }
    conf = min(0.92, 0.68 + 0.24 * min((max_f2 - thr) / 8.0, 1.0))
    conf = _boosted_confidence(conf, df, "furnace_overload")

    return build_anomaly(
        "ELEC_FURNACE2_001", df, cond,
        domain="electricity", asset="Four 2 / 63 kV", severity="high",
        title="Pic de charge four 2",
        description=(
            "La puissance du four 2 dépasse le seuil nominal, entraînant une hausse "
            "du bus 63 kV et du coût énergie."
        ),
        evidence=evidence,
        probable_causes=[
            "surcharge procédé sur four 2",
            "dépassement contrat puissance souscrite",
            "défaut régulateur de puissance four",
        ],
        confidence_score=conf,
        affected_systems="electricity",
        anomaly_type="furnace_overload",
    )


def _detect_perte_cat(df: pd.DataFrame) -> dict[str, Any] | None:
    """Perte partielle centrale CAT — génération interne s'effondre."""
    thr = THRESHOLDS["cat_min_mw"]
    cond = df["cat_generation_63kv_mw"] < thr
    if cond.sum() < THRESHOLDS["min_rows_trigger"]:
        return None

    win = df[cond]
    min_cat    = float(df["cat_generation_63kv_mw"].min())
    median_cat = float(df["cat_generation_63kv_mw"].median())

    evidence = {
        "min_cat_mw":         round(min_cat, 3),
        "median_cat_mw":      round(median_cat, 3),
        "threshold_mw":       thr,
        "n_rows_below":       int(cond.sum()),
        "avg_grid_import_mw": round(float(win["grid_import_63kv_mw"].mean()), 3),
    }
    drop_ratio = 1.0 - min_cat / max(median_cat, 0.1)
    conf = min(0.95, 0.65 + 0.30 * min(drop_ratio / 0.60, 1.0))
    conf = _boosted_confidence(conf, df, "cat_fault")

    return build_anomaly(
        "ELEC_CAT_001", df, cond,
        domain="electricity", asset="CAT / Poste 63 kV", severity="high",
        title="Perte partielle centrale CAT",
        description=(
            "La génération interne de la centrale CAT chute brutalement. "
            "L'import réseau compense mais le coût augmente."
        ),
        evidence=evidence,
        probable_causes=[
            "déclenchement turbine CAT",
            "défaut alternateur ou régulateur de tension",
            "maintenance non planifiée",
        ],
        confidence_score=conf,
        affected_systems="electricity",
        anomaly_type="cat_fault",
    )


def _detect_surcharge_15kv(df: pd.DataFrame) -> dict[str, Any] | None:
    """Surcharge poste 15 kV — demande process anormalement élevée."""
    thr = THRESHOLDS["station_15kv_max_mw"]
    cond = df["station_15kv_supply_mw"] > thr
    if cond.sum() < THRESHOLDS["min_rows_trigger"]:
        return None

    win    = df[cond]
    max_s  = float(df["station_15kv_supply_mw"].max())

    evidence = {
        "max_station_15kv_mw":  round(max_s, 3),
        "threshold_mw":         thr,
        "n_rows_above":         int(cond.sum()),
        "avg_substation_a_mw":  round(float(win["substation_a_15kv_mw"].mean()), 3),
        "avg_substation_b_mw":  round(float(win["substation_b_15kv_mw"].mean()), 3),
        "avg_substation_c_mw":  round(float(win["substation_c_15kv_mw"].mean()), 3),
    }
    conf = min(0.90, 0.65 + 0.25 * min((max_s - thr) / 4.0, 1.0))
    conf = _boosted_confidence(conf, df, "overload_15kv")

    return build_anomaly(
        "ELEC_15KV_001", df, cond,
        domain="electricity", asset="Poste 15 kV force motrice", severity="high",
        title="Surcharge poste 15 kV",
        description=(
            "La puissance totale du poste 15 kV dépasse le seuil normal. "
            "Risque de délestage automatique ou de contrainte câbles."
        ),
        evidence=evidence,
        probable_causes=[
            "démarrage simultané de gros moteurs",
            "surcharge process anormale",
            "perte d'un transformateur — report sur les autres",
        ],
        confidence_score=conf,
        affected_systems="electricity",
        anomaly_type="overload_15kv",
    )


# ─────────────────────────────────────────────────────────────────────────────
# DÉTECTIONS AIR 7 BARS
# ─────────────────────────────────────────────────────────────────────────────

def _detect_fuite_air_7b(df: pd.DataFrame) -> dict[str, Any] | None:
    """Fuite réseau air 7 bars — pression basse, compresseurs en surcharge, débit en hausse."""
    p_thr = THRESHOLDS["air_7b_pressure_low_bar"]
    cond  = df["air_7b_pressure"] < p_thr
    if cond.sum() < THRESHOLDS["min_rows_trigger"]:
        return None

    # Discrimination fuite vs simple basse pression :
    # fuite → compresseurs compensent → débit MONTE par rapport à la médiane du df
    flow_median     = float(df["air_7b_total_flow_nm3h"].median())
    flow_in_anomaly = float(df.loc[cond, "air_7b_total_flow_nm3h"].mean())
    if flow_in_anomaly <= flow_median:
        return None  # débit en baisse → pas une fuite

    win    = df[cond]
    min_p  = float(df["air_7b_pressure"].min())
    max_se = float(df["air_7b_specific_energy_kwh_per_nm3"].max())

    evidence = {
        "min_pressure_bar":       round(min_p, 3),
        "threshold_pressure_bar": p_thr,
        "max_specific_energy":    round(max_se, 4),
        "avg_total_flow_nm3h":    round(flow_in_anomaly, 0),
        "baseline_flow_nm3h":     round(flow_median, 0),
        "n_rows_anomalous":       int(cond.sum()),
    }
    pressure_drop = max(0.0, float(df["air_7b_pressure"].median()) - min_p)
    conf = min(0.92, 0.65 + 0.27 * min(pressure_drop / 0.50, 1.0))
    conf = _boosted_confidence(conf, df, "air_leak")

    return build_anomaly(
        "AIR7_LEAK_001", df, cond,
        domain="air", asset="Réseau air 7 bars", severity="high",
        title="Fuite probable réseau air 7 bars",
        description=(
            "La pression chute pendant que les compresseurs augmentent leur débit et "
            "consomment plus d'énergie par Nm³. Signature typique d'une fuite réseau."
        ),
        evidence=evidence,
        probable_causes=[
            "fuite réseau air instrument ou process",
            "vanne ouverte ou mal fermée",
            "rupture de canalisation aval",
        ],
        confidence_score=conf,
        affected_systems="air_7b",
        anomaly_type="air_leak",
    )


def _detect_defaut_c715(df: pd.DataFrame) -> dict[str, Any] | None:
    """Défaut compresseur C715 — débit effondré sur machine en marche."""
    thr     = THRESHOLDS["c715_flow_low_nm3h"]
    running = df["C715_status"] == 1
    if not running.any():
        return None

    cond = running & (df["C715_flow_nm3h"] < thr)
    if cond.sum() < THRESHOLDS["min_rows_trigger"]:
        return None

    win = df[cond]
    # Estimation débit nominal depuis les lignes en marche non dégradées
    nominal_est  = float(df.loc[running, "C715_flow_nm3h"].quantile(0.90))
    mean_f_fault = float(win["C715_flow_nm3h"].mean())
    mean_p_fault = float(win["C715_power_kw"].mean())

    evidence = {
        "avg_flow_faulty_nm3h":    round(mean_f_fault, 0),
        "nominal_flow_p90_nm3h":   round(nominal_est, 0),
        "flow_ratio":              round(mean_f_fault / max(nominal_est, 1.0), 3),
        "avg_power_faulty_kw":     round(mean_p_fault, 1),
        "n_rows_degraded":         int(cond.sum()),
        "air_7b_pressure_min_bar": round(float(df["air_7b_pressure"].min()), 3),
    }
    degradation = 1.0 - mean_f_fault / max(nominal_est, 1.0)
    conf = min(0.93, 0.68 + 0.25 * min(degradation / 0.60, 1.0))
    conf = _boosted_confidence(conf, df, "compressor_fault")

    return build_anomaly(
        "AIR7_C715_001", df, cond,
        domain="air", asset="C715", severity="high",
        title="Défaut compresseur C715",
        description=(
            "C715 est en marche mais son débit est dramatiquement réduit tandis que "
            "sa puissance augmente. Signe de cavitation, encrassement ou défaut mécanique."
        ),
        evidence=evidence,
        probable_causes=[
            "cavitation ou érosion roue centrifuge",
            "encrassement filtre aspiration",
            "défaut vanne ou clapet aval",
        ],
        confidence_score=conf,
        affected_systems="air_7b",
        anomaly_type="compressor_fault",
    )


def _detect_desequilibre_c7(df: pd.DataFrame) -> dict[str, Any] | None:
    """Déséquilibre C713/C714 — un compresseur surchargé, l'autre sous-chargé."""
    thr      = THRESHOLDS["c7_imbalance_ratio"]
    both_run = (df["C713_status"] == 1) & (df["C714_status"] == 1)
    if not both_run.any():
        return None

    c714_safe = df["C714_flow_nm3h"].where(df["C714_flow_nm3h"] > 0, other=np.nan)
    ratio     = df["C713_flow_nm3h"] / c714_safe
    cond      = both_run & (ratio > thr)

    if cond.sum() < THRESHOLDS["min_rows_trigger"]:
        return None

    win = df[cond]
    evidence = {
        "avg_c713_flow_nm3h":  round(float(win["C713_flow_nm3h"].mean()), 0),
        "avg_c714_flow_nm3h":  round(float(win["C714_flow_nm3h"].mean()), 0),
        "max_ratio_c713_c714": round(float(ratio[cond].max()), 3),
        "threshold_ratio":     thr,
        "n_rows_imbalanced":   int(cond.sum()),
    }
    max_ratio = float(ratio[cond].max())
    conf = min(0.87, 0.62 + 0.25 * min((max_ratio - thr) / 0.40, 1.0))
    conf = _boosted_confidence(conf, df, "compressor_imbalance")

    return build_anomaly(
        "AIR7_IMBALA_001", df, cond,
        domain="air", asset="C713-C714", severity="medium",
        title="Déséquilibre compresseurs 7 bars C713/C714",
        description=(
            "C713 supporte une charge nettement supérieure à C714. "
            "Usure accélérée de C713, sous-utilisation de C714."
        ),
        evidence=evidence,
        probable_causes=[
            "désréglage du séquenceur de charge compresseurs",
            "vanne de régulation C714 partiellement fermée",
            "défaut capteur débit sur C714",
        ],
        confidence_score=conf,
        affected_systems="air_7b",
        anomaly_type="compressor_imbalance",
    )


# ─────────────────────────────────────────────────────────────────────────────
# DÉTECTIONS AIR 3 BARS
# ─────────────────────────────────────────────────────────────────────────────

def _detect_saturation_vsd_3b(df: pd.DataFrame) -> dict[str, Any] | None:
    """Saturation VSD air 3 bars — vitesses au maximum, pression insuffisante."""
    spd_thr = THRESHOLDS["vsd_3b_sat_speed_pct"]
    p_thr   = THRESHOLDS["air_3b_pressure_low_bar"]

    high_speeds = (
        (df["C321_speed_pct"] >= spd_thr)
        & (df["C322_speed_pct"] >= spd_thr - 1.0)
        & (df["C323_speed_pct"] >= spd_thr - 2.0)
    )
    cond = high_speeds & (df["air_3b_pressure"] < p_thr)

    if cond.sum() < THRESHOLDS["min_rows_trigger"]:
        return None

    win   = df[cond]
    min_p = float(df["air_3b_pressure"].min())

    evidence = {
        "avg_c321_speed_pct":     round(float(win["C321_speed_pct"].mean()), 1),
        "avg_c322_speed_pct":     round(float(win["C322_speed_pct"].mean()), 1),
        "avg_c323_speed_pct":     round(float(win["C323_speed_pct"].mean()), 1),
        "min_pressure_bar":       round(min_p, 3),
        "threshold_pressure_bar": p_thr,
        "n_rows_saturated":       int(cond.sum()),
    }
    conf = min(0.90, 0.68 + 0.22 * min((p_thr - min_p) / 0.40, 1.0))
    conf = _boosted_confidence(conf, df, "vsd_saturation")

    return build_anomaly(
        "AIR3_SAT_001", df, cond,
        domain="air", asset="C321/C322/C323", severity="high",
        title="Saturation VSD air 3 bars",
        description=(
            "Les trois variateurs de vitesse sont à fond mais la pression reste insuffisante. "
            "La demande process dépasse la capacité installée."
        ),
        evidence=evidence,
        probable_causes=[
            "augmentation de la demande transport poussières/charbon",
            "fuite réseau air 3 bars",
            "compresseur VSD sous-dimensionné pour la charge actuelle",
        ],
        confidence_score=conf,
        affected_systems="air_3b",
        anomaly_type="vsd_saturation",
    )


def _detect_mauvaise_regulation_3b(df: pd.DataFrame) -> dict[str, Any] | None:
    """Mauvaise régulation air 3 bars — compresseur fixe démarré inutilement."""
    min_rows = int(THRESHOLDS["c311_on_min_rows"])
    c311_on  = df["C311_status"] == 1
    if c311_on.sum() < min_rows:
        return None

    cond = c311_on
    win  = df[cond]
    avg_vsd = float(win[["C321_speed_pct", "C322_speed_pct", "C323_speed_pct"]].mean().mean())

    evidence = {
        "n_rows_c311_on":     int(cond.sum()),
        "avg_c311_power_kw":  round(float(win["C311_power_kw"].mean()), 1),
        "avg_vsd_speed_pct":  round(avg_vsd, 1),
        "avg_c321_speed_pct": round(float(win["C321_speed_pct"].mean()), 1),
        "avg_c322_speed_pct": round(float(win["C322_speed_pct"].mean()), 1),
    }
    conf = min(0.85, 0.65 + 0.20 * min(cond.sum() / 20.0, 1.0))
    conf = _boosted_confidence(conf, df, "bad_regulation")

    return build_anomaly(
        "AIR3_REG_001", df, cond,
        domain="air", asset="C311/C312 + VSD", severity="medium",
        title="Mauvaise régulation air 3 bars",
        description=(
            "Le compresseur fixe C311 est démarré alors que les VSD fonctionnent "
            "à vitesse réduite. Surconsommation électrique inutile."
        ),
        evidence=evidence,
        probable_causes=[
            "défaut ou désréglage du séquenceur de régulation 3 bars",
            "intervention manuelle non annulée",
            "seuil de démarrage C311 trop bas",
        ],
        confidence_score=conf,
        affected_systems="air_3b",
        anomaly_type="bad_regulation",
    )


# ─────────────────────────────────────────────────────────────────────────────
# DÉTECTIONS EAU RECYCLÉE
# ─────────────────────────────────────────────────────────────────────────────

def _detect_defaut_refroidissement(df: pd.DataFrame) -> dict[str, Any] | None:
    """Défaut refroidissement eau recyclée — pompe EF1 arrêtée, débit chute."""
    pump1_off = df["cold_water_pump_1_power_kw"] == 0.0
    if pump1_off.sum() < THRESHOLDS["min_rows_trigger"]:
        return None

    cond        = pump1_off
    win         = df[cond]
    min_flow    = float(df["recycled_water_flow_m3h"].min())
    max_delta_t = float(df["recycled_water_delta_t_c"].max())
    flow_low    = (df["recycled_water_flow_m3h"] < THRESHOLDS["rw_flow_low_m3h"]).sum()

    evidence = {
        "n_rows_pump1_off":      int(pump1_off.sum()),
        "min_flow_m3h":          round(min_flow, 0),
        "threshold_flow_m3h":    THRESHOLDS["rw_flow_low_m3h"],
        "max_delta_t_c":         round(max_delta_t, 2),
        "min_pressure_bar":      round(float(df["recycled_water_pressure_bar"].min()), 2),
        "flow_rows_below_thr":   int(flow_low),
    }
    conf = min(0.96, 0.78 + 0.18 * min(pump1_off.sum() / 20.0, 1.0))
    conf = _boosted_confidence(conf, df, "cooling_fault")

    severity = "critical" if (
        max_delta_t > THRESHOLDS["rw_delta_t_high_c"] and min_flow < 1_600.0
    ) else "high"

    return build_anomaly(
        "WATER_REFROID_001", df, cond,
        domain="water", asset="Circuit eau recyclée / pompe EF1", severity=severity,
        title="Défaut refroidissement eau recyclée",
        description=(
            "La pompe EF1 est arrêtée. Le débit de refroidissement chute, "
            "la température de retour monte — risque de surchauffe procédé."
        ),
        evidence=evidence,
        probable_causes=[
            "panne moteur ou disjoncteur pompe EF1",
            "défaut démarrage (protection thermique)",
            "vanne d'aspiration fermée",
        ],
        confidence_score=conf,
        affected_systems="water",
        anomaly_type="cooling_fault",
    )


def _detect_risque_legionelle(df: pd.DataFrame) -> dict[str, Any] | None:
    """Risque légionelle — indice élevé + traitement chimique défaillant."""
    thr  = THRESHOLDS["legionella_high"]
    cond = df["legionella_risk_index"] > thr
    if cond.sum() < THRESHOLDS["min_rows_trigger"]:
        return None

    win     = df[cond]
    max_leg = float(df["legionella_risk_index"].max())
    min_chem = float(df["chemical_treatment_index"].min())

    evidence = {
        "max_legionella_index":   round(max_leg, 3),
        "threshold_legionella":   thr,
        "min_chemical_treatment": round(min_chem, 3),
        "max_return_temp_c":      round(float(df["recycled_water_return_temp_c"].max()), 2),
        "n_rows_above_threshold": int(cond.sum()),
    }
    conf = min(0.94, 0.70 + 0.24 * min((max_leg - thr) / 0.30, 1.0))
    conf = _boosted_confidence(conf, df, "legionella_risk")

    severity = "critical" if max_leg > 0.85 else "high"

    return build_anomaly(
        "WATER_LEG_001", df, cond,
        domain="water", asset="Tours aéroréfrigérantes / traitement chimique", severity=severity,
        title="Risque légionelle détecté",
        description=(
            "L'indice de risque légionelle dépasse le seuil de vigilance. "
            "Le traitement chimique est insuffisant et la température de retour est élevée."
        ),
        evidence=evidence,
        probable_causes=[
            "arrêt ou dysfonctionnement dosage biocide",
            "stagnation eau chaude dans les tours",
            "élévation anormale température retour",
        ],
        confidence_score=conf,
        affected_systems="water",
        anomaly_type="legionella_risk",
    )


# ─────────────────────────────────────────────────────────────────────────────
# DÉTECTIONS EAU BRUTE
# ─────────────────────────────────────────────────────────────────────────────

def _detect_baisse_b1(df: pd.DataFrame) -> dict[str, Any] | None:
    """Niveau bassin B1 critique — secours refroidissement potentiellement compromis."""
    thr  = THRESHOLDS["basin_b1_critical_pct"]
    cond = df["basin_b1_level_pct"] < thr
    if cond.sum() < THRESHOLDS["min_rows_trigger"]:
        return None

    win    = df[cond]
    min_b1 = float(df["basin_b1_level_pct"].min())
    min_v  = float(df["basin_b1_volume_m3"].min())

    evidence = {
        "min_b1_level_pct":        round(min_b1, 1),
        "threshold_pct":           thr,
        "min_b1_volume_m3":        round(min_v, 0),
        "n_rows_below_threshold":  int(cond.sum()),
        "emergency_unavail_rows":  int((~win["emergency_cooling_available"]).sum()),
        "avg_makeup_m3h":          round(float(win["raw_water_makeup_to_recycled_m3h"].mean()), 1),
    }
    conf = min(0.90, 0.68 + 0.22 * min((thr - min_b1) / 15.0, 1.0))
    conf = _boosted_confidence(conf, df, "low_basin")

    return build_anomaly(
        "WATER_B1_001", df, cond,
        domain="water", asset="Bassin B1", severity="high",
        title="Niveau bassin B1 critique",
        description=(
            "Le niveau du bassin B1 est sous le seuil de 20 %. "
            "La capacité de secours refroidissement est réduite."
        ),
        evidence=evidence,
        probable_causes=[
            "fuite réseau eau brute ou bassin",
            "sous-alimentation pompe appoint",
            "consommation eau brute anormalement élevée",
        ],
        confidence_score=conf,
        affected_systems="water",
        anomaly_type="low_basin",
    )


def _detect_forte_dependance_eau_brute(df: pd.DataFrame) -> dict[str, Any] | None:
    """Forte dépendance eau brute — appoint anormalement élevé, bassins en baisse."""
    dep_thr    = THRESHOLDS["raw_dependency_high"]
    makeup_thr = THRESHOLDS["raw_makeup_high_m3h"]
    cond = (
        (df["raw_water_dependency_ratio"] > dep_thr)
        | (df["raw_water_makeup_to_recycled_m3h"] > makeup_thr)
    )
    if cond.sum() < THRESHOLDS["min_rows_trigger"]:
        return None

    win        = df[cond]
    max_ratio  = float(df["raw_water_dependency_ratio"].max())
    max_makeup = float(df["raw_water_makeup_to_recycled_m3h"].max())

    evidence = {
        "max_dependency_ratio":   round(max_ratio, 4),
        "threshold_ratio":        dep_thr,
        "max_makeup_m3h":         round(max_makeup, 1),
        "threshold_makeup_m3h":   makeup_thr,
        "avg_raw_flow_m3h":       round(float(win["raw_water_flow_m3h"].mean()), 1),
        "n_rows_above_threshold": int(cond.sum()),
    }
    conf = min(0.88, 0.62 + 0.26 * min((max_ratio - dep_thr) / 0.12, 1.0))
    conf = _boosted_confidence(conf, df, "raw_water_overconsumption")

    severity = "high" if max_ratio > 0.18 else "medium"

    return build_anomaly(
        "WATER_RAW_001", df, cond,
        domain="water", asset="Eau brute / appoint recyclée", severity=severity,
        title="Forte dépendance eau brute",
        description=(
            "L'appoint d'eau brute dépasse largement le nominal. "
            "Fuite probable dans le circuit eau recyclée ou surconsommation process."
        ),
        evidence=evidence,
        probable_causes=[
            "fuite circuit eau recyclée (évaporation anormale)",
            "purge excessive des tours de refroidissement",
            "défaut régulation vanne appoint",
        ],
        confidence_score=conf,
        affected_systems="water",
        anomaly_type="raw_water_overconsumption",
    )


# ─────────────────────────────────────────────────────────────────────────────
# API publique
# ─────────────────────────────────────────────────────────────────────────────

def detect_electricity_anomalies(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Détecte les anomalies électricité (63 kV / 15 kV)."""
    result = []
    for fn in (_detect_pic_four_2, _detect_perte_cat, _detect_surcharge_15kv):
        a = fn(df)
        if a is not None:
            result.append(a)
    return result


def detect_air_anomalies(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Détecte les anomalies air comprimé 7 bars et 3 bars."""
    result = []
    for fn in (
        _detect_fuite_air_7b, _detect_defaut_c715, _detect_desequilibre_c7,
        _detect_saturation_vsd_3b, _detect_mauvaise_regulation_3b,
    ):
        a = fn(df)
        if a is not None:
            result.append(a)
    return result


def detect_water_anomalies(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Détecte les anomalies eau recyclée et eau brute."""
    result = []
    for fn in (
        _detect_defaut_refroidissement, _detect_risque_legionelle,
        _detect_baisse_b1, _detect_forte_dependance_eau_brute,
    ):
        a = fn(df)
        if a is not None:
            result.append(a)
    return result


def detect_anomalies(df: pd.DataFrame) -> list[dict[str, Any]]:
    """
    Détecte toutes les anomalies industrielles dans le DataFrame.

    Fonctionne sur données nominales (résultat : liste vide ou low/medium uniquement)
    et sur données scénarisées (avec ou sans colonnes metadata scenarios.py).

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame issu de generate_mock_plant_data() ou apply_scenario().

    Returns
    -------
    list[dict]
        Liste d'anomalies avec id, domaine, sévérité, preuve chiffrée,
        causes probables et score de confiance.
    """
    anomalies: list[dict[str, Any]] = []
    anomalies.extend(detect_electricity_anomalies(df))
    anomalies.extend(detect_air_anomalies(df))
    anomalies.extend(detect_water_anomalies(df))
    return anomalies


def summarize_anomalies(anomalies: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Résume la liste d'anomalies détectées.

    Returns dict : total, by_domain, by_severity, has_critical, has_high, titles, ids.
    """
    by_domain:   dict[str, int] = {}
    by_severity: dict[str, int] = {}
    for a in anomalies:
        by_domain[a["domain"]]     = by_domain.get(a["domain"], 0) + 1
        by_severity[a["severity"]] = by_severity.get(a["severity"], 0) + 1
    return {
        "total":       len(anomalies),
        "by_domain":   by_domain,
        "by_severity": by_severity,
        "has_critical": any(a["severity"] == "critical" for a in anomalies),
        "has_high":     any(a["severity"] == "high" for a in anomalies),
        "titles":       [a["title"] for a in anomalies],
        "ids":          [a["id"] for a in anomalies],
    }
