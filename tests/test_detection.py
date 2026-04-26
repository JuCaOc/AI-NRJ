"""
Tests unitaires — modules/detection.py

Couverture :
- Scénario nominal : aucune anomalie high/critical
- Chaque scénario : la bonne anomalie est détectée
- Structure des anomalies : tous les champs obligatoires présents
- Scores : confidence_score ∈ [0, 1]
- Sévérité : ∈ {low, medium, high, critical}
- Multi-crise : ≥ 3 anomalies dans des domaines distincts
"""

import pytest
import pandas as pd

from modules.data_generator import generate_mock_plant_data, SEED
from modules.scenarios import apply_scenario
from modules.detection import (
    detect_anomalies,
    detect_electricity_anomalies,
    detect_air_anomalies,
    detect_water_anomalies,
    build_anomaly,
    summarize_anomalies,
    THRESHOLDS,
)

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

_REQUIRED_FIELDS = {
    "id", "timestamp_start", "timestamp_end", "domain", "asset",
    "severity", "title", "description", "evidence", "probable_causes",
    "confidence_score", "affected_systems", "anomaly_type",
}
_VALID_SEVERITIES  = {"low", "medium", "high", "critical"}
_VALID_DOMAINS     = {"electricity", "air", "water"}


@pytest.fixture(scope="module")
def nominal_df() -> pd.DataFrame:
    return generate_mock_plant_data(seed=SEED)


@pytest.fixture(scope="module")
def scenario_dfs(nominal_df) -> dict[str, pd.DataFrame]:
    names = [
        "pic_four_2", "perte_partielle_cat", "surcharge_15kv",
        "fuite_air_7b", "defaut_c715", "desequilibre_c7",
        "saturation_vsd_3b", "mauvaise_regulation_3b",
        "defaut_refroidissement", "risque_legionelle",
        "baisse_bassin_b1", "forte_dependance_eau_brute",
        "multi_crise",
    ]
    return {name: apply_scenario(nominal_df, name) for name in names}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _anomaly_types(anomalies: list[dict]) -> set[str]:
    return {a["anomaly_type"] for a in anomalies}


def _domains(anomalies: list[dict]) -> set[str]:
    return {a["domain"] for a in anomalies}


# ─────────────────────────────────────────────────────────────────────────────
# Structure des anomalies
# ─────────────────────────────────────────────────────────────────────────────

class TestAnomalyStructure:
    """Vérifie que chaque anomalie respecte le schéma attendu."""

    def _all_anomalies(self, scenario_dfs) -> list[dict]:
        all_a = []
        for df in scenario_dfs.values():
            all_a.extend(detect_anomalies(df))
        return all_a

    def test_all_required_fields_present(self, scenario_dfs):
        for a in self._all_anomalies(scenario_dfs):
            missing = _REQUIRED_FIELDS - set(a.keys())
            assert not missing, f"Champs manquants dans {a['id']}: {missing}"

    def test_confidence_in_range(self, scenario_dfs):
        for a in self._all_anomalies(scenario_dfs):
            assert 0.0 <= a["confidence_score"] <= 1.0, \
                f"{a['id']} confidence={a['confidence_score']}"

    def test_severity_valid(self, scenario_dfs):
        for a in self._all_anomalies(scenario_dfs):
            assert a["severity"] in _VALID_SEVERITIES, \
                f"{a['id']} severity={a['severity']}"

    def test_domain_valid(self, scenario_dfs):
        for a in self._all_anomalies(scenario_dfs):
            assert a["domain"] in _VALID_DOMAINS, \
                f"{a['id']} domain={a['domain']}"

    def test_evidence_is_dict_nonempty(self, scenario_dfs):
        for a in self._all_anomalies(scenario_dfs):
            assert isinstance(a["evidence"], dict) and len(a["evidence"]) > 0, \
                f"{a['id']} evidence vide"

    def test_probable_causes_nonempty_list(self, scenario_dfs):
        for a in self._all_anomalies(scenario_dfs):
            assert isinstance(a["probable_causes"], list) and len(a["probable_causes"]) > 0, \
                f"{a['id']} probable_causes vide"

    def test_timestamps_strings(self, scenario_dfs):
        for a in self._all_anomalies(scenario_dfs):
            assert isinstance(a["timestamp_start"], str)
            assert isinstance(a["timestamp_end"], str)


# ─────────────────────────────────────────────────────────────────────────────
# Scénario nominal — aucune anomalie bloquante
# ─────────────────────────────────────────────────────────────────────────────

class TestNominalData:
    def test_no_high_or_critical_in_nominal(self, nominal_df):
        anomalies = detect_anomalies(nominal_df)
        high_crit = [a for a in anomalies if a["severity"] in ("high", "critical")]
        assert len(high_crit) == 0, \
            f"Anomalies high/critical en nominal : {[a['title'] for a in high_crit]}"

    def test_no_electricity_anomalies_in_nominal(self, nominal_df):
        assert detect_electricity_anomalies(nominal_df) == []

    def test_no_air_anomalies_in_nominal(self, nominal_df):
        assert detect_air_anomalies(nominal_df) == []

    def test_no_water_anomalies_in_nominal(self, nominal_df):
        assert detect_water_anomalies(nominal_df) == []


# ─────────────────────────────────────────────────────────────────────────────
# Scénarios électricité
# ─────────────────────────────────────────────────────────────────────────────

class TestElectricityDetection:
    def test_pic_four_2_detected(self, scenario_dfs):
        anomalies = detect_anomalies(scenario_dfs["pic_four_2"])
        assert "furnace_overload" in _anomaly_types(anomalies), \
            "furnace_overload non détecté pour pic_four_2"

    def test_pic_four_2_severity_high(self, scenario_dfs):
        anomalies = detect_electricity_anomalies(scenario_dfs["pic_four_2"])
        pic = next(a for a in anomalies if a["anomaly_type"] == "furnace_overload")
        assert pic["severity"] == "high"

    def test_pic_four_2_evidence_has_max_furnace(self, scenario_dfs):
        anomalies = detect_electricity_anomalies(scenario_dfs["pic_four_2"])
        pic = next(a for a in anomalies if a["anomaly_type"] == "furnace_overload")
        assert "max_furnace_2_mw" in pic["evidence"]
        assert pic["evidence"]["max_furnace_2_mw"] > THRESHOLDS["furnace_2_max_mw"]

    def test_perte_cat_detected(self, scenario_dfs):
        anomalies = detect_anomalies(scenario_dfs["perte_partielle_cat"])
        assert "cat_fault" in _anomaly_types(anomalies), \
            "cat_fault non détecté pour perte_partielle_cat"

    def test_perte_cat_evidence_min_below_threshold(self, scenario_dfs):
        anomalies = detect_electricity_anomalies(scenario_dfs["perte_partielle_cat"])
        cat = next(a for a in anomalies if a["anomaly_type"] == "cat_fault")
        assert cat["evidence"]["min_cat_mw"] < THRESHOLDS["cat_min_mw"]

    def test_surcharge_15kv_detected(self, scenario_dfs):
        anomalies = detect_anomalies(scenario_dfs["surcharge_15kv"])
        assert "overload_15kv" in _anomaly_types(anomalies), \
            "overload_15kv non détecté pour surcharge_15kv"

    def test_surcharge_15kv_evidence_max_above_threshold(self, scenario_dfs):
        anomalies = detect_electricity_anomalies(scenario_dfs["surcharge_15kv"])
        s15 = next(a for a in anomalies if a["anomaly_type"] == "overload_15kv")
        assert s15["evidence"]["max_station_15kv_mw"] > THRESHOLDS["station_15kv_max_mw"]


# ─────────────────────────────────────────────────────────────────────────────
# Scénarios air 7 bars
# ─────────────────────────────────────────────────────────────────────────────

class TestAir7bDetection:
    def test_fuite_air_7b_detected(self, scenario_dfs):
        anomalies = detect_anomalies(scenario_dfs["fuite_air_7b"])
        assert "air_leak" in _anomaly_types(anomalies), \
            "air_leak non détecté pour fuite_air_7b"

    def test_fuite_air_7b_severity_high(self, scenario_dfs):
        anomalies = detect_air_anomalies(scenario_dfs["fuite_air_7b"])
        leak = next(a for a in anomalies if a["anomaly_type"] == "air_leak")
        assert leak["severity"] == "high"

    def test_fuite_evidence_pressure_below_threshold(self, scenario_dfs):
        anomalies = detect_air_anomalies(scenario_dfs["fuite_air_7b"])
        leak = next(a for a in anomalies if a["anomaly_type"] == "air_leak")
        assert leak["evidence"]["min_pressure_bar"] < THRESHOLDS["air_7b_pressure_low_bar"]

    def test_defaut_c715_detected(self, scenario_dfs):
        anomalies = detect_anomalies(scenario_dfs["defaut_c715"])
        assert "compressor_fault" in _anomaly_types(anomalies), \
            "compressor_fault non détecté pour defaut_c715"

    def test_defaut_c715_severity_high(self, scenario_dfs):
        anomalies = detect_air_anomalies(scenario_dfs["defaut_c715"])
        c715 = next(a for a in anomalies if a["anomaly_type"] == "compressor_fault")
        assert c715["severity"] == "high"

    def test_defaut_c715_evidence_flow_low(self, scenario_dfs):
        anomalies = detect_air_anomalies(scenario_dfs["defaut_c715"])
        c715 = next(a for a in anomalies if a["anomaly_type"] == "compressor_fault")
        assert c715["evidence"]["avg_flow_faulty_nm3h"] < THRESHOLDS["c715_flow_low_nm3h"]

    def test_desequilibre_c7_detected(self, scenario_dfs):
        anomalies = detect_anomalies(scenario_dfs["desequilibre_c7"])
        assert "compressor_imbalance" in _anomaly_types(anomalies), \
            "compressor_imbalance non détecté pour desequilibre_c7"

    def test_desequilibre_severity_medium(self, scenario_dfs):
        anomalies = detect_air_anomalies(scenario_dfs["desequilibre_c7"])
        imb = next(a for a in anomalies if a["anomaly_type"] == "compressor_imbalance")
        assert imb["severity"] == "medium"

    def test_desequilibre_ratio_above_threshold(self, scenario_dfs):
        anomalies = detect_air_anomalies(scenario_dfs["desequilibre_c7"])
        imb = next(a for a in anomalies if a["anomaly_type"] == "compressor_imbalance")
        assert imb["evidence"]["max_ratio_c713_c714"] > THRESHOLDS["c7_imbalance_ratio"]


# ─────────────────────────────────────────────────────────────────────────────
# Scénarios air 3 bars
# ─────────────────────────────────────────────────────────────────────────────

class TestAir3bDetection:
    def test_saturation_vsd_detected(self, scenario_dfs):
        anomalies = detect_anomalies(scenario_dfs["saturation_vsd_3b"])
        assert "vsd_saturation" in _anomaly_types(anomalies), \
            "vsd_saturation non détecté pour saturation_vsd_3b"

    def test_saturation_severity_high(self, scenario_dfs):
        anomalies = detect_air_anomalies(scenario_dfs["saturation_vsd_3b"])
        sat = next(a for a in anomalies if a["anomaly_type"] == "vsd_saturation")
        assert sat["severity"] == "high"

    def test_saturation_evidence_pressure_low(self, scenario_dfs):
        anomalies = detect_air_anomalies(scenario_dfs["saturation_vsd_3b"])
        sat = next(a for a in anomalies if a["anomaly_type"] == "vsd_saturation")
        assert sat["evidence"]["min_pressure_bar"] < THRESHOLDS["air_3b_pressure_low_bar"]

    def test_mauvaise_regulation_detected(self, scenario_dfs):
        anomalies = detect_anomalies(scenario_dfs["mauvaise_regulation_3b"])
        assert "bad_regulation" in _anomaly_types(anomalies), \
            "bad_regulation non détecté pour mauvaise_regulation_3b"

    def test_mauvaise_regulation_severity_medium(self, scenario_dfs):
        anomalies = detect_air_anomalies(scenario_dfs["mauvaise_regulation_3b"])
        reg = next(a for a in anomalies if a["anomaly_type"] == "bad_regulation")
        assert reg["severity"] == "medium"

    def test_mauvaise_regulation_c311_on_rows(self, scenario_dfs):
        anomalies = detect_air_anomalies(scenario_dfs["mauvaise_regulation_3b"])
        reg = next(a for a in anomalies if a["anomaly_type"] == "bad_regulation")
        assert reg["evidence"]["n_rows_c311_on"] >= int(THRESHOLDS["c311_on_min_rows"])


# ─────────────────────────────────────────────────────────────────────────────
# Scénarios eau
# ─────────────────────────────────────────────────────────────────────────────

class TestWaterDetection:
    def test_defaut_refroidissement_detected(self, scenario_dfs):
        anomalies = detect_anomalies(scenario_dfs["defaut_refroidissement"])
        assert "cooling_fault" in _anomaly_types(anomalies), \
            "cooling_fault non détecté pour defaut_refroidissement"

    def test_defaut_refroid_severity_high_or_critical(self, scenario_dfs):
        anomalies = detect_water_anomalies(scenario_dfs["defaut_refroidissement"])
        cool = next(a for a in anomalies if a["anomaly_type"] == "cooling_fault")
        assert cool["severity"] in ("high", "critical")

    def test_defaut_refroid_pump1_off_in_evidence(self, scenario_dfs):
        anomalies = detect_water_anomalies(scenario_dfs["defaut_refroidissement"])
        cool = next(a for a in anomalies if a["anomaly_type"] == "cooling_fault")
        assert cool["evidence"]["n_rows_pump1_off"] > 0

    def test_risque_legionelle_detected(self, scenario_dfs):
        anomalies = detect_anomalies(scenario_dfs["risque_legionelle"])
        assert "legionella_risk" in _anomaly_types(anomalies), \
            "legionella_risk non détecté pour risque_legionelle"

    def test_legionelle_severity_high_or_critical(self, scenario_dfs):
        anomalies = detect_water_anomalies(scenario_dfs["risque_legionelle"])
        leg = next(a for a in anomalies if a["anomaly_type"] == "legionella_risk")
        assert leg["severity"] in ("high", "critical")

    def test_legionelle_index_above_threshold(self, scenario_dfs):
        anomalies = detect_water_anomalies(scenario_dfs["risque_legionelle"])
        leg = next(a for a in anomalies if a["anomaly_type"] == "legionella_risk")
        assert leg["evidence"]["max_legionella_index"] > THRESHOLDS["legionella_high"]

    def test_baisse_b1_detected(self, scenario_dfs):
        anomalies = detect_anomalies(scenario_dfs["baisse_bassin_b1"])
        assert "low_basin" in _anomaly_types(anomalies), \
            "low_basin non détecté pour baisse_bassin_b1"

    def test_baisse_b1_severity_high(self, scenario_dfs):
        anomalies = detect_water_anomalies(scenario_dfs["baisse_bassin_b1"])
        b1 = next(a for a in anomalies if a["anomaly_type"] == "low_basin")
        assert b1["severity"] == "high"

    def test_baisse_b1_level_below_threshold(self, scenario_dfs):
        anomalies = detect_water_anomalies(scenario_dfs["baisse_bassin_b1"])
        b1 = next(a for a in anomalies if a["anomaly_type"] == "low_basin")
        assert b1["evidence"]["min_b1_level_pct"] < THRESHOLDS["basin_b1_critical_pct"]

    def test_forte_dependance_detected(self, scenario_dfs):
        anomalies = detect_anomalies(scenario_dfs["forte_dependance_eau_brute"])
        assert "raw_water_overconsumption" in _anomaly_types(anomalies), \
            "raw_water_overconsumption non détecté pour forte_dependance_eau_brute"

    def test_forte_dependance_ratio_above_threshold(self, scenario_dfs):
        anomalies = detect_water_anomalies(scenario_dfs["forte_dependance_eau_brute"])
        raw = next(a for a in anomalies if a["anomaly_type"] == "raw_water_overconsumption")
        assert raw["evidence"]["max_dependency_ratio"] > THRESHOLDS["raw_dependency_high"]


# ─────────────────────────────────────────────────────────────────────────────
# Multi-crise
# ─────────────────────────────────────────────────────────────────────────────

class TestMultiCriseDetection:
    def test_at_least_3_anomalies(self, scenario_dfs):
        anomalies = detect_anomalies(scenario_dfs["multi_crise"])
        assert len(anomalies) >= 3, \
            f"Multi-crise : {len(anomalies)} anomalie(s) détectée(s), ≥ 3 attendues"

    def test_multiple_domains_detected(self, scenario_dfs):
        anomalies = detect_anomalies(scenario_dfs["multi_crise"])
        domains = _domains(anomalies)
        assert len(domains) >= 2, \
            f"Multi-crise : domaines={domains}, ≥ 2 attendus"

    def test_electricity_detected(self, scenario_dfs):
        anomalies = detect_anomalies(scenario_dfs["multi_crise"])
        assert "electricity" in _domains(anomalies)

    def test_air_detected(self, scenario_dfs):
        anomalies = detect_anomalies(scenario_dfs["multi_crise"])
        assert "air" in _domains(anomalies)

    def test_water_detected(self, scenario_dfs):
        anomalies = detect_anomalies(scenario_dfs["multi_crise"])
        assert "water" in _domains(anomalies)

    def test_furnace_overload_in_multi(self, scenario_dfs):
        anomalies = detect_anomalies(scenario_dfs["multi_crise"])
        assert "furnace_overload" in _anomaly_types(anomalies)

    def test_cooling_fault_in_multi(self, scenario_dfs):
        anomalies = detect_anomalies(scenario_dfs["multi_crise"])
        assert "cooling_fault" in _anomaly_types(anomalies)


# ─────────────────────────────────────────────────────────────────────────────
# summarize_anomalies
# ─────────────────────────────────────────────────────────────────────────────

class TestSummarize:
    def test_summarize_structure(self, scenario_dfs):
        anomalies = detect_anomalies(scenario_dfs["multi_crise"])
        s = summarize_anomalies(anomalies)
        assert "total" in s
        assert "by_domain" in s
        assert "by_severity" in s
        assert "has_critical" in s
        assert "has_high" in s
        assert "titles" in s
        assert "ids" in s

    def test_summarize_total_matches(self, scenario_dfs):
        anomalies = detect_anomalies(scenario_dfs["multi_crise"])
        s = summarize_anomalies(anomalies)
        assert s["total"] == len(anomalies)

    def test_summarize_domain_counts(self, scenario_dfs):
        anomalies = detect_anomalies(scenario_dfs["multi_crise"])
        s = summarize_anomalies(anomalies)
        assert sum(s["by_domain"].values()) == len(anomalies)

    def test_summarize_empty(self, nominal_df):
        anomalies = detect_anomalies(nominal_df)
        s = summarize_anomalies(anomalies)
        assert s["total"] == 0
        assert not s["has_critical"]
        assert not s["has_high"]

    def test_summarize_has_high_for_pic(self, scenario_dfs):
        anomalies = detect_anomalies(scenario_dfs["pic_four_2"])
        s = summarize_anomalies(anomalies)
        assert s["has_high"]


# ─────────────────────────────────────────────────────────────────────────────
# Metadata boost
# ─────────────────────────────────────────────────────────────────────────────

class TestMetadataBoost:
    """Vérifie que les colonnes metadata augmentent le confidence_score."""

    def test_confidence_higher_with_metadata(self, nominal_df):
        """apply_scenario() ajoute les metadata → confidence boosted."""
        df_no_meta = generate_mock_plant_data(seed=SEED)
        # Simuler un pic four 2 sans metadata (modification manuelle)
        df_no_meta = df_no_meta.copy()
        w = slice(38, 67)
        import numpy as np
        df_no_meta.loc[df_no_meta.index[w], "furnace_2_63kv_mw"] = np.clip(
            df_no_meta.loc[df_no_meta.index[w], "furnace_2_63kv_mw"] * 1.28, 0, 75.0
        ).round(3)
        from modules.scenarios import _recompute
        df_no_meta = _recompute(df_no_meta)

        df_with_meta = apply_scenario(nominal_df, "pic_four_2")

        a_no   = detect_electricity_anomalies(df_no_meta)
        a_with = detect_electricity_anomalies(df_with_meta)

        conf_no   = next((a["confidence_score"] for a in a_no   if a["anomaly_type"] == "furnace_overload"), None)
        conf_with = next((a["confidence_score"] for a in a_with if a["anomaly_type"] == "furnace_overload"), None)

        assert conf_no is not None and conf_with is not None
        assert conf_with > conf_no, "Le boost metadata n'a pas augmenté le confidence_score"
