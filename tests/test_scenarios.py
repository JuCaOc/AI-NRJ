"""
Tests unitaires — modules/scenarios.py

Couverture :
- list_available_scenarios() : structure, nombre
- apply_scenario() : immuabilité original, colonnes ajoutées, cohérence
- Chaque scénario : effets vérifiés dans la fenêtre temporelle [40 %, 70 %[
- Métadonnées IA : anomaly_flag, anomaly_type, affected_systems
- Isolation fenêtre : colonnes source inchangées hors fenêtre
"""

import numpy as np
import pandas as pd
import pytest

from modules.data_generator import generate_mock_plant_data, SEED, N_POINTS
from modules.scenarios import list_available_scenarios, apply_scenario, _time_window

_ALL_NAMES = [s["name"] for s in list_available_scenarios()]
_N_SCENARIOS = 13
_WIN_START = int(N_POINTS * 0.4)   # 38
_WIN_END   = int(N_POINTS * 0.7)   # 67


@pytest.fixture(scope="module")
def nominal_df() -> pd.DataFrame:
    return generate_mock_plant_data(seed=SEED)


# ─────────────────────────────────────────────────────────────────────────────
# list_available_scenarios
# ─────────────────────────────────────────────────────────────────────────────

class TestListScenarios:
    def test_returns_list(self):
        assert isinstance(list_available_scenarios(), list)

    def test_exact_count(self):
        assert len(list_available_scenarios()) == _N_SCENARIOS

    def test_each_entry_has_name_and_description(self):
        for s in list_available_scenarios():
            assert "name" in s and "description" in s
            assert isinstance(s["name"], str) and len(s["name"]) > 0
            assert isinstance(s["description"], str) and len(s["description"]) > 0

    def test_names_are_unique(self):
        names = [s["name"] for s in list_available_scenarios()]
        assert len(names) == len(set(names))


# ─────────────────────────────────────────────────────────────────────────────
# apply_scenario — comportements génériques (tous les scénarios)
# ─────────────────────────────────────────────────────────────────────────────

class TestApplyScenarioGeneric:
    @pytest.mark.parametrize("name", _ALL_NAMES)
    def test_original_not_mutated(self, nominal_df, name):
        original_copy = nominal_df.copy()
        apply_scenario(nominal_df, name)
        pd.testing.assert_frame_equal(nominal_df, original_copy)

    @pytest.mark.parametrize("name", _ALL_NAMES)
    def test_scenario_columns_added(self, nominal_df, name):
        result = apply_scenario(nominal_df, name)
        assert "scenario_name" in result.columns
        assert "scenario_description" in result.columns
        assert (result["scenario_name"] == name).all()

    @pytest.mark.parametrize("name", _ALL_NAMES)
    def test_row_count_preserved(self, nominal_df, name):
        result = apply_scenario(nominal_df, name)
        assert len(result) == len(nominal_df)

    @pytest.mark.parametrize("name", _ALL_NAMES)
    def test_no_nulls_in_numeric_columns(self, nominal_df, name):
        result = apply_scenario(nominal_df, name)
        num_cols = result.select_dtypes(include=[np.number]).columns
        null_counts = result[num_cols].isnull().sum()
        assert null_counts.sum() == 0, f"[{name}] NaN : {null_counts[null_counts > 0].to_dict()}"

    @pytest.mark.parametrize("name", _ALL_NAMES)
    def test_total_power_equals_bus(self, nominal_df, name):
        result = apply_scenario(nominal_df, name)
        pd.testing.assert_series_equal(
            result["total_plant_power_mw"],
            result["total_63kv_bus_mw"].rename("total_plant_power_mw"),
        )

    def test_unknown_scenario_raises_value_error(self, nominal_df):
        with pytest.raises(ValueError, match="inconnu"):
            apply_scenario(nominal_df, "scenario_qui_nexiste_pas")


# ─────────────────────────────────────────────────────────────────────────────
# Métadonnées IA
# ─────────────────────────────────────────────────────────────────────────────

class TestAIMetadata:
    @pytest.mark.parametrize("name", _ALL_NAMES)
    def test_ai_metadata_columns_present(self, nominal_df, name):
        r = apply_scenario(nominal_df, name)
        assert "anomaly_flag" in r.columns
        assert "anomaly_type" in r.columns
        assert "affected_systems" in r.columns

    @pytest.mark.parametrize("name", _ALL_NAMES)
    def test_anomaly_flag_true_in_window(self, nominal_df, name):
        r = apply_scenario(nominal_df, name)
        w = _time_window(r)
        assert r["anomaly_flag"].iloc[w].all(), \
            f"[{name}] anomaly_flag False dans la fenêtre"

    @pytest.mark.parametrize("name", _ALL_NAMES)
    def test_anomaly_flag_false_outside_window(self, nominal_df, name):
        r = apply_scenario(nominal_df, name)
        before = r["anomaly_flag"].iloc[:_WIN_START]
        after  = r["anomaly_flag"].iloc[_WIN_END:]
        assert not before.any(), f"[{name}] anomaly_flag True avant la fenêtre"
        assert not after.any(),  f"[{name}] anomaly_flag True après la fenêtre"

    @pytest.mark.parametrize("name", _ALL_NAMES)
    def test_anomaly_type_and_systems_nonempty(self, nominal_df, name):
        r = apply_scenario(nominal_df, name)
        assert isinstance(r["anomaly_type"].iloc[0], str)
        assert len(r["anomaly_type"].iloc[0]) > 0
        assert isinstance(r["affected_systems"].iloc[0], str)
        assert len(r["affected_systems"].iloc[0]) > 0


# ─────────────────────────────────────────────────────────────────────────────
# Isolation fenêtre — colonnes source inchangées hors fenêtre
# ─────────────────────────────────────────────────────────────────────────────

class TestWindowIsolation:
    """Vérifie que les effets sont strictement localisés dans la fenêtre."""

    def _outside(self, df: pd.DataFrame) -> pd.DataFrame:
        mask = np.ones(len(df), dtype=bool)
        mask[_WIN_START:_WIN_END] = False
        return df.iloc[mask]

    def test_pic_four_2_furnace2_unchanged_outside(self, nominal_df):
        r = apply_scenario(nominal_df, "pic_four_2")
        pd.testing.assert_series_equal(
            self._outside(r)["furnace_2_63kv_mw"].reset_index(drop=True),
            self._outside(nominal_df)["furnace_2_63kv_mw"].reset_index(drop=True),
        )

    def test_fuite_pressure_unchanged_outside(self, nominal_df):
        r = apply_scenario(nominal_df, "fuite_air_7b")
        pd.testing.assert_series_equal(
            self._outside(r)["air_7b_pressure"].reset_index(drop=True),
            self._outside(nominal_df)["air_7b_pressure"].reset_index(drop=True),
        )

    def test_defaut_refroid_flow_unchanged_outside(self, nominal_df):
        r = apply_scenario(nominal_df, "defaut_refroidissement")
        pd.testing.assert_series_equal(
            self._outside(r)["recycled_water_flow_m3h"].reset_index(drop=True),
            self._outside(nominal_df)["recycled_water_flow_m3h"].reset_index(drop=True),
        )

    def test_baisse_b1_level_unchanged_outside(self, nominal_df):
        r = apply_scenario(nominal_df, "baisse_bassin_b1")
        pd.testing.assert_series_equal(
            self._outside(r)["basin_b1_level_pct"].reset_index(drop=True),
            self._outside(nominal_df)["basin_b1_level_pct"].reset_index(drop=True),
        )

    def test_surcharge_15kv_station_unchanged_outside(self, nominal_df):
        r = apply_scenario(nominal_df, "surcharge_15kv")
        pd.testing.assert_series_equal(
            self._outside(r)["station_15kv_supply_mw"].reset_index(drop=True),
            self._outside(nominal_df)["station_15kv_supply_mw"].reset_index(drop=True),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Électricité
# ─────────────────────────────────────────────────────────────────────────────

class TestElectricityScenarios:
    def test_pic_four_2_furnace_up(self, nominal_df):
        r = apply_scenario(nominal_df, "pic_four_2")
        assert (
            r["furnace_2_63kv_mw"].iloc[_WIN_START:_WIN_END]
            > nominal_df["furnace_2_63kv_mw"].iloc[_WIN_START:_WIN_END]
        ).all()

    def test_pic_four_2_bus_up(self, nominal_df):
        r = apply_scenario(nominal_df, "pic_four_2")
        assert (
            r["total_63kv_bus_mw"].iloc[_WIN_START:_WIN_END]
            > nominal_df["total_63kv_bus_mw"].iloc[_WIN_START:_WIN_END]
        ).all()

    def test_pic_four_2_cost_up(self, nominal_df):
        r = apply_scenario(nominal_df, "pic_four_2")
        assert (
            r["energy_cost_xpf"].iloc[_WIN_START:_WIN_END]
            > nominal_df["energy_cost_xpf"].iloc[_WIN_START:_WIN_END]
        ).all()

    def test_pic_four_2_other_furnaces_unchanged(self, nominal_df):
        r = apply_scenario(nominal_df, "pic_four_2")
        pd.testing.assert_series_equal(r["furnace_1_63kv_mw"], nominal_df["furnace_1_63kv_mw"])
        pd.testing.assert_series_equal(r["furnace_3_63kv_mw"], nominal_df["furnace_3_63kv_mw"])

    def test_perte_cat_generation_down(self, nominal_df):
        r = apply_scenario(nominal_df, "perte_partielle_cat")
        assert (
            r["cat_generation_63kv_mw"].iloc[_WIN_START:_WIN_END]
            < nominal_df["cat_generation_63kv_mw"].iloc[_WIN_START:_WIN_END]
        ).all()

    def test_perte_cat_import_up(self, nominal_df):
        r = apply_scenario(nominal_df, "perte_partielle_cat")
        assert (
            r["grid_import_63kv_mw"].iloc[_WIN_START:_WIN_END]
            > nominal_df["grid_import_63kv_mw"].iloc[_WIN_START:_WIN_END]
        ).all()

    def test_perte_cat_bus_unchanged(self, nominal_df):
        r = apply_scenario(nominal_df, "perte_partielle_cat")
        pd.testing.assert_series_equal(r["total_63kv_bus_mw"], nominal_df["total_63kv_bus_mw"])

    def test_surcharge_15kv_station_up(self, nominal_df):
        r = apply_scenario(nominal_df, "surcharge_15kv")
        assert (
            r["station_15kv_supply_mw"].iloc[_WIN_START:_WIN_END]
            > nominal_df["station_15kv_supply_mw"].iloc[_WIN_START:_WIN_END]
        ).all()

    def test_surcharge_15kv_bus_up(self, nominal_df):
        r = apply_scenario(nominal_df, "surcharge_15kv")
        assert (
            r["total_63kv_bus_mw"].iloc[_WIN_START:_WIN_END]
            > nominal_df["total_63kv_bus_mw"].iloc[_WIN_START:_WIN_END]
        ).all()

    def test_surcharge_15kv_cost_up(self, nominal_df):
        r = apply_scenario(nominal_df, "surcharge_15kv")
        assert (
            r["energy_cost_xpf"].iloc[_WIN_START:_WIN_END]
            > nominal_df["energy_cost_xpf"].iloc[_WIN_START:_WIN_END]
        ).all()


# ─────────────────────────────────────────────────────────────────────────────
# Air 7 bars
# ─────────────────────────────────────────────────────────────────────────────

class TestAir7bScenarios:
    def test_fuite_pressure_down(self, nominal_df):
        r = apply_scenario(nominal_df, "fuite_air_7b")
        assert (
            r["air_7b_pressure"].iloc[_WIN_START:_WIN_END]
            < nominal_df["air_7b_pressure"].iloc[_WIN_START:_WIN_END]
        ).all()

    def test_fuite_total_flow_up(self, nominal_df):
        r = apply_scenario(nominal_df, "fuite_air_7b")
        assert r["air_7b_total_flow_nm3h"].mean() > nominal_df["air_7b_total_flow_nm3h"].mean()

    def test_fuite_specific_energy_up(self, nominal_df):
        r = apply_scenario(nominal_df, "fuite_air_7b")
        assert (
            r["air_7b_specific_energy_kwh_per_nm3"].iloc[_WIN_START:_WIN_END].mean()
            > nominal_df["air_7b_specific_energy_kwh_per_nm3"].iloc[_WIN_START:_WIN_END].mean()
        )

    def test_defaut_c715_flow_down(self, nominal_df):
        r = apply_scenario(nominal_df, "defaut_c715")
        nom_win = nominal_df.iloc[_WIN_START:_WIN_END]
        r_win   = r.iloc[_WIN_START:_WIN_END]
        running = nom_win["C715_status"] == 1
        if running.any():
            assert (r_win["C715_flow_nm3h"][running] < nom_win["C715_flow_nm3h"][running]).all()

    def test_defaut_c715_power_up(self, nominal_df):
        r = apply_scenario(nominal_df, "defaut_c715")
        nom_win = nominal_df.iloc[_WIN_START:_WIN_END]
        r_win   = r.iloc[_WIN_START:_WIN_END]
        running = nom_win["C715_status"] == 1
        if running.any():
            assert (r_win["C715_power_kw"][running] > nom_win["C715_power_kw"][running]).all()

    def test_defaut_c715_pressure_down(self, nominal_df):
        r = apply_scenario(nominal_df, "defaut_c715")
        assert (
            r["air_7b_pressure"].iloc[_WIN_START:_WIN_END]
            < nominal_df["air_7b_pressure"].iloc[_WIN_START:_WIN_END]
        ).all()

    def test_desequilibre_c713_up(self, nominal_df):
        r = apply_scenario(nominal_df, "desequilibre_c7")
        assert (
            r["C713_flow_nm3h"].iloc[_WIN_START:_WIN_END]
            > nominal_df["C713_flow_nm3h"].iloc[_WIN_START:_WIN_END]
        ).all()

    def test_desequilibre_c714_down(self, nominal_df):
        r = apply_scenario(nominal_df, "desequilibre_c7")
        assert (
            r["C714_flow_nm3h"].iloc[_WIN_START:_WIN_END]
            < nominal_df["C714_flow_nm3h"].iloc[_WIN_START:_WIN_END]
        ).all()

    def test_desequilibre_other_compressors_unchanged(self, nominal_df):
        r = apply_scenario(nominal_df, "desequilibre_c7")
        for name in ("C715", "C716", "C717"):
            pd.testing.assert_series_equal(
                r[f"{name}_flow_nm3h"], nominal_df[f"{name}_flow_nm3h"],
                check_names=False,
            )


# ─────────────────────────────────────────────────────────────────────────────
# Air 3 bars
# ─────────────────────────────────────────────────────────────────────────────

class TestAir3bScenarios:
    def test_saturation_speeds_at_max(self, nominal_df):
        r = apply_scenario(nominal_df, "saturation_vsd_3b")
        r_win = r.iloc[_WIN_START:_WIN_END]
        assert (r_win["C321_speed_pct"] >= 98.5).all()
        assert (r_win["C322_speed_pct"] >= 98.0).all()
        assert (r_win["C323_speed_pct"] >= 96.5).all()

    def test_saturation_pressure_down(self, nominal_df):
        r = apply_scenario(nominal_df, "saturation_vsd_3b")
        assert (
            r["air_3b_pressure"].iloc[_WIN_START:_WIN_END]
            < nominal_df["air_3b_pressure"].iloc[_WIN_START:_WIN_END]
        ).all()

    def test_mauvaise_reg_c311_on(self, nominal_df):
        r = apply_scenario(nominal_df, "mauvaise_regulation_3b")
        r_win = r.iloc[_WIN_START:_WIN_END]
        assert (r_win["C311_status"] == 1).all()
        assert (r_win["C311_power_kw"] > 0).all()

    def test_mauvaise_reg_vsd_speeds_reduced(self, nominal_df):
        r = apply_scenario(nominal_df, "mauvaise_regulation_3b")
        assert (
            r["C321_speed_pct"].iloc[_WIN_START:_WIN_END]
            < nominal_df["C321_speed_pct"].iloc[_WIN_START:_WIN_END]
        ).all()
        assert (
            r["C322_speed_pct"].iloc[_WIN_START:_WIN_END]
            < nominal_df["C322_speed_pct"].iloc[_WIN_START:_WIN_END]
        ).all()

    def test_mauvaise_reg_total_power_includes_c311(self, nominal_df):
        r = apply_scenario(nominal_df, "mauvaise_regulation_3b")
        assert (r["air_3b_total_power_kw"] > 0).all()


# ─────────────────────────────────────────────────────────────────────────────
# Eau recyclée
# ─────────────────────────────────────────────────────────────────────────────

class TestWaterScenarios:
    def test_defaut_refroid_flow_down(self, nominal_df):
        r = apply_scenario(nominal_df, "defaut_refroidissement")
        assert (
            r["recycled_water_flow_m3h"].iloc[_WIN_START:_WIN_END]
            < nominal_df["recycled_water_flow_m3h"].iloc[_WIN_START:_WIN_END]
        ).all()

    def test_defaut_refroid_delta_t_up(self, nominal_df):
        r = apply_scenario(nominal_df, "defaut_refroidissement")
        assert (
            r["recycled_water_delta_t_c"].iloc[_WIN_START:_WIN_END]
            > nominal_df["recycled_water_delta_t_c"].iloc[_WIN_START:_WIN_END]
        ).all()

    def test_defaut_refroid_pump1_zero(self, nominal_df):
        r = apply_scenario(nominal_df, "defaut_refroidissement")
        assert (r["cold_water_pump_1_power_kw"].iloc[_WIN_START:_WIN_END] == 0.0).all()

    def test_defaut_refroid_pressure_down(self, nominal_df):
        r = apply_scenario(nominal_df, "defaut_refroidissement")
        assert (
            r["recycled_water_pressure_bar"].iloc[_WIN_START:_WIN_END]
            < nominal_df["recycled_water_pressure_bar"].iloc[_WIN_START:_WIN_END]
        ).all()

    def test_defaut_refroid_return_temp_up(self, nominal_df):
        r = apply_scenario(nominal_df, "defaut_refroidissement")
        assert r["recycled_water_return_temp_c"].mean() > nominal_df["recycled_water_return_temp_c"].mean()

    def test_defaut_refroid_furnaces_down_in_window(self, nominal_df):
        r = apply_scenario(nominal_df, "defaut_refroidissement")
        for col in ("furnace_1_63kv_mw", "furnace_2_63kv_mw", "furnace_3_63kv_mw"):
            assert (
                r[col].iloc[_WIN_START:_WIN_END]
                < nominal_df[col].iloc[_WIN_START:_WIN_END]
            ).all(), f"{col} non réduit dans la fenêtre"

    def test_legionelle_index_up(self, nominal_df):
        r = apply_scenario(nominal_df, "risque_legionelle")
        assert (r["legionella_risk_index"] >= nominal_df["legionella_risk_index"]).all()

    def test_legionelle_chemical_down(self, nominal_df):
        r = apply_scenario(nominal_df, "risque_legionelle")
        assert (
            r["chemical_treatment_index"].iloc[_WIN_START:_WIN_END]
            < nominal_df["chemical_treatment_index"].iloc[_WIN_START:_WIN_END]
        ).all()

    def test_legionelle_return_temp_up(self, nominal_df):
        r = apply_scenario(nominal_df, "risque_legionelle")
        assert (
            r["recycled_water_return_temp_c"].iloc[_WIN_START:_WIN_END]
            > nominal_df["recycled_water_return_temp_c"].iloc[_WIN_START:_WIN_END]
        ).all()


# ─────────────────────────────────────────────────────────────────────────────
# Eau brute
# ─────────────────────────────────────────────────────────────────────────────

class TestRawWaterScenarios:
    def test_baisse_b1_level_below_threshold(self, nominal_df):
        r = apply_scenario(nominal_df, "baisse_bassin_b1")
        assert (r["basin_b1_level_pct"].iloc[_WIN_START:_WIN_END] < 20.0).all()

    def test_baisse_b1_emergency_logic_consistent(self, nominal_df):
        r = apply_scenario(nominal_df, "baisse_bassin_b1")
        expected = (r["basin_b0_level_pct"] > 20.0) | (r["basin_b1_level_pct"] > 20.0)
        pd.testing.assert_series_equal(
            r["emergency_cooling_available"],
            expected.rename("emergency_cooling_available"),
        )

    def test_baisse_b1_volume_consistent(self, nominal_df):
        from modules.data_generator import _B1_CAPACITY_M3
        r = apply_scenario(nominal_df, "baisse_bassin_b1")
        expected = (r["basin_b1_level_pct"] / 100.0 * _B1_CAPACITY_M3).round(0)
        pd.testing.assert_series_equal(
            r["basin_b1_volume_m3"],
            expected.rename("basin_b1_volume_m3"),
            atol=1.0,
        )

    def test_forte_dependance_makeup_up(self, nominal_df):
        r = apply_scenario(nominal_df, "forte_dependance_eau_brute")
        assert (
            r["raw_water_makeup_to_recycled_m3h"].iloc[_WIN_START:_WIN_END]
            > nominal_df["raw_water_makeup_to_recycled_m3h"].iloc[_WIN_START:_WIN_END]
        ).all()

    def test_forte_dependance_ratio_up(self, nominal_df):
        r = apply_scenario(nominal_df, "forte_dependance_eau_brute")
        assert r["raw_water_dependency_ratio"].mean() > nominal_df["raw_water_dependency_ratio"].mean()

    def test_forte_dependance_basins_down(self, nominal_df):
        r = apply_scenario(nominal_df, "forte_dependance_eau_brute")
        assert (
            r["basin_b0_level_pct"].iloc[_WIN_START:_WIN_END]
            < nominal_df["basin_b0_level_pct"].iloc[_WIN_START:_WIN_END]
        ).all()
        assert (
            r["basin_b1_level_pct"].iloc[_WIN_START:_WIN_END]
            < nominal_df["basin_b1_level_pct"].iloc[_WIN_START:_WIN_END]
        ).all()


# ─────────────────────────────────────────────────────────────────────────────
# Multi-crise
# ─────────────────────────────────────────────────────────────────────────────

class TestMultiCrise:
    def test_furnace_2_up(self, nominal_df):
        r = apply_scenario(nominal_df, "multi_crise")
        assert (
            r["furnace_2_63kv_mw"].iloc[_WIN_START:_WIN_END]
            > nominal_df["furnace_2_63kv_mw"].iloc[_WIN_START:_WIN_END]
        ).all()

    def test_air_pressure_down(self, nominal_df):
        r = apply_scenario(nominal_df, "multi_crise")
        assert (
            r["air_7b_pressure"].iloc[_WIN_START:_WIN_END]
            < nominal_df["air_7b_pressure"].iloc[_WIN_START:_WIN_END]
        ).all()

    def test_water_flow_down(self, nominal_df):
        r = apply_scenario(nominal_df, "multi_crise")
        assert (
            r["recycled_water_flow_m3h"].iloc[_WIN_START:_WIN_END]
            < nominal_df["recycled_water_flow_m3h"].iloc[_WIN_START:_WIN_END]
        ).all()

    def test_energy_cost_up(self, nominal_df):
        r = apply_scenario(nominal_df, "multi_crise")
        assert r["energy_cost_xpf"].mean() > nominal_df["energy_cost_xpf"].mean()

    def test_pump1_zero(self, nominal_df):
        r = apply_scenario(nominal_df, "multi_crise")
        assert (r["cold_water_pump_1_power_kw"].iloc[_WIN_START:_WIN_END] == 0.0).all()

    def test_more_systems_affected_than_pic(self, nominal_df):
        """Multi-crise dégrade l'air ET l'eau en plus de l'électricité."""
        r_pic   = apply_scenario(nominal_df, "pic_four_2")
        r_multi = apply_scenario(nominal_df, "multi_crise")
        assert r_multi["air_7b_pressure"].mean() < r_pic["air_7b_pressure"].mean()
        assert r_multi["recycled_water_flow_m3h"].mean() < r_pic["recycled_water_flow_m3h"].mean()
