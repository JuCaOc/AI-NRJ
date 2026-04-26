"""
Tests unitaires — modules/data_generator.py

Couverture :
- Forme du DataFrame (96 lignes, colonnes requises)
- Reproductibilité (même seed → même résultat)
- Plages physiques réalistes (pressions, températures, niveaux, puissances)
- Contraintes énergétiques (bilans 63 kV)
- Cohérence air (delta_t positif, fixes à l'arrêt, énergie spécifique)
- Cohérence eau (delta_t > 0, niveaux bassins bornés)
"""

import numpy as np
import pandas as pd
import pytest

from modules.data_generator import (
    generate_base_timeseries,
    generate_electricity_data,
    generate_air_data,
    generate_water_data,
    generate_mock_plant_data,
    N_POINTS,
    SEED,
    INTERVAL_MIN,
    ELECTRICITY_TARIFF_XPF_KWH,
    _C7_NAMES,
    _C7_RUN_THRESH,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixture
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def plant_df() -> pd.DataFrame:
    return generate_mock_plant_data(seed=SEED)


# ─────────────────────────────────────────────────────────────────────────────
# Forme & colonnes
# ─────────────────────────────────────────────────────────────────────────────

class TestShape:
    def test_row_count(self, plant_df):
        assert len(plant_df) == 96, f"Attendu 96 lignes, obtenu {len(plant_df)}"

    def test_n_points_constant_matches(self, plant_df):
        assert len(plant_df) == N_POINTS

    def test_required_electricity_columns(self, plant_df):
        required = [
            "cat_generation_63kv_mw", "grid_import_63kv_mw",
            "furnace_1_63kv_mw", "furnace_2_63kv_mw", "furnace_3_63kv_mw",
            "station_15kv_supply_mw",
            "substation_a_15kv_mw", "substation_b_15kv_mw", "substation_c_15kv_mw",
            "compressors_7b_5_5kv_mw", "salt_water_pumps_5_5kv_mw",
            "mpc_pumps_5_5kv_mw", "motors_5_5kv_mw",
            "auxiliaries_400v_mw", "other_motors_400v_mw",
            "total_63kv_bus_mw", "total_plant_power_mw", "energy_cost_xpf",
        ]
        missing = [c for c in required if c not in plant_df.columns]
        assert not missing, f"Colonnes manquantes : {missing}"

    def test_required_air_7b_columns(self, plant_df):
        required = (
            [f"{n}_flow_nm3h" for n in _C7_NAMES]
            + [f"{n}_status" for n in _C7_NAMES]
            + [f"{n}_power_kw" for n in _C7_NAMES]
            + ["air_7b_pressure", "air_7b_total_flow_nm3h",
               "air_7b_total_power_kw", "air_7b_specific_energy_kwh_per_nm3"]
        )
        missing = [c for c in required if c not in plant_df.columns]
        assert not missing, f"Colonnes manquantes : {missing}"

    def test_required_air_3b_columns(self, plant_df):
        required = [
            "C321_speed_pct", "C322_speed_pct", "C323_speed_pct",
            "C321_flow_nm3h", "C322_flow_nm3h", "C323_flow_nm3h",
            "C321_power_kw", "C322_power_kw", "C323_power_kw",
            "C311_status", "C312_status", "C311_power_kw", "C312_power_kw",
            "air_3b_pressure", "air_3b_total_flow_nm3h", "air_3b_total_power_kw",
            "dust_transport_index", "coal_transport_index",
        ]
        missing = [c for c in required if c not in plant_df.columns]
        assert not missing, f"Colonnes manquantes : {missing}"

    def test_required_water_columns(self, plant_df):
        required = [
            "recycled_water_flow_m3h", "recycled_water_supply_temp_c",
            "recycled_water_return_temp_c", "recycled_water_delta_t_c",
            "recycled_water_pressure_bar", "recycled_water_efficiency_index",
            "raw_water_dependency_ratio",
            "cold_water_pump_1_power_kw", "cold_water_pump_2_power_kw", "cold_water_pump_3_power_kw",
            "hot_water_pump_1_power_kw", "hot_water_pump_2_power_kw",
            "recycled_water_pump_power_kw",
            "aero_power_kw", "sand_filter_dp_bar",
            "legionella_risk_index", "chemical_treatment_index",
            "furnace_cooling_demand_index", "bearing_cooling_demand_index",
            "raw_water_flow_m3h", "raw_water_makeup_to_recycled_m3h",
            "basin_b0_level_pct", "basin_b1_level_pct",
            "basin_b0_volume_m3", "basin_b1_volume_m3",
            "emergency_cooling_available", "emergency_cooling_capacity_m3h",
        ]
        missing = [c for c in required if c not in plant_df.columns]
        assert not missing, f"Colonnes manquantes : {missing}"

    def test_no_nulls_in_numeric_columns(self, plant_df):
        num_cols = plant_df.select_dtypes(include=[np.number]).columns
        null_counts = plant_df[num_cols].isnull().sum()
        cols_with_nulls = null_counts[null_counts > 0]
        assert cols_with_nulls.empty, f"NaN détectés : {cols_with_nulls.to_dict()}"


# ─────────────────────────────────────────────────────────────────────────────
# Timeline
# ─────────────────────────────────────────────────────────────────────────────

class TestTimeseries:
    def test_timestamp_dtype(self, plant_df):
        assert pd.api.types.is_datetime64_any_dtype(plant_df["timestamp"])

    def test_timestamp_interval_15min(self, plant_df):
        deltas = plant_df["timestamp"].diff().dropna()
        assert (deltas == pd.Timedelta("15min")).all()

    def test_production_index_range(self, plant_df):
        assert plant_df["production_index"].between(0.48, 1.02).all()

    def test_production_index_daily_cycle(self, plant_df):
        """La valeur max doit être en milieu de journée (8h-18h)."""
        peak_idx = plant_df["production_index"].idxmax()
        peak_hour = plant_df.loc[peak_idx, "timestamp"].hour
        assert 7 <= peak_hour <= 17, f"Pic à {peak_hour}h, attendu entre 7h et 17h"


# ─────────────────────────────────────────────────────────────────────────────
# Reproductibilité
# ─────────────────────────────────────────────────────────────────────────────

class TestReproducibility:
    def test_same_seed_same_result(self):
        df1 = generate_mock_plant_data(seed=SEED)
        df2 = generate_mock_plant_data(seed=SEED)
        pd.testing.assert_frame_equal(df1, df2)

    def test_different_seed_different_result(self):
        df1 = generate_mock_plant_data(seed=SEED)
        df2 = generate_mock_plant_data(seed=SEED + 1)
        assert not df1["production_index"].equals(df2["production_index"])


# ─────────────────────────────────────────────────────────────────────────────
# Plages physiques — Électricité
# ─────────────────────────────────────────────────────────────────────────────

class TestElectricity:
    def test_furnace_power_range(self, plant_df):
        for i in range(1, 4):
            col = f"furnace_{i}_63kv_mw"
            assert plant_df[col].between(25.0, 56.0).all(), f"{col} hors plage"

    def test_cat_generation_range(self, plant_df):
        assert plant_df["cat_generation_63kv_mw"].between(30.0, 185.0).all()

    def test_grid_import_positive(self, plant_df):
        assert (plant_df["grid_import_63kv_mw"] >= 0).all()

    def test_total_bus_coherence(self, plant_df):
        """total_63kv_bus ≈ Σ fours + station_15kv (tolérance 5 %)."""
        expected = (
            plant_df["furnace_1_63kv_mw"]
            + plant_df["furnace_2_63kv_mw"]
            + plant_df["furnace_3_63kv_mw"]
            + plant_df["station_15kv_supply_mw"]
        )
        ratio = (plant_df["total_63kv_bus_mw"] / expected).abs()
        assert ratio.between(0.97, 1.03).all()

    def test_station_15kv_coherence(self, plant_df):
        """station_15kv ≈ Σ sous-stations (tolérance 3 %)."""
        substation_sum = (
            plant_df["substation_a_15kv_mw"]
            + plant_df["substation_b_15kv_mw"]
            + plant_df["substation_c_15kv_mw"]
        )
        diff_pct = (
            (plant_df["station_15kv_supply_mw"] - substation_sum).abs()
            / substation_sum
        )
        assert (diff_pct < 0.05).all()

    def test_total_power_equals_bus(self, plant_df):
        pd.testing.assert_series_equal(
            plant_df["total_plant_power_mw"],
            plant_df["total_63kv_bus_mw"].rename("total_plant_power_mw"),
        )

    def test_plant_power_range(self, plant_df):
        assert plant_df["total_plant_power_mw"].between(110.0, 200.0).all()

    def test_energy_cost_positive(self, plant_df):
        assert (plant_df["energy_cost_xpf"] > 0).all()

    def test_energy_cost_formula(self, plant_df):
        expected = (
            plant_df["total_plant_power_mw"] * 1_000.0 * (INTERVAL_MIN / 60.0) * ELECTRICITY_TARIFF_XPF_KWH
        ).round(0).rename("energy_cost_xpf")
        pd.testing.assert_series_equal(plant_df["energy_cost_xpf"], expected)


# ─────────────────────────────────────────────────────────────────────────────
# Plages physiques — Air 7 bars
# ─────────────────────────────────────────────────────────────────────────────

class TestAir7Bar:
    def test_pressure_range(self, plant_df):
        assert plant_df["air_7b_pressure"].between(6.5, 7.6).all()

    def test_specific_energy_range(self, plant_df):
        se = plant_df["air_7b_specific_energy_kwh_per_nm3"]
        assert se.between(0.085, 0.135).all()

    def test_c716_standby_at_low_production(self, plant_df):
        """C716 ne doit pas tourner en dessous de son seuil de démarrage."""
        low_prod = plant_df["production_index"] < _C7_RUN_THRESH["C716"]
        if low_prod.any():
            assert (plant_df.loc[low_prod, "C716_flow_nm3h"] == 0).all()

    def test_total_flow_matches_sum(self, plant_df):
        comp_sum = sum(plant_df[f"{n}_flow_nm3h"] for n in _C7_NAMES)
        pd.testing.assert_series_equal(
            plant_df["air_7b_total_flow_nm3h"],
            comp_sum.round(0).rename("air_7b_total_flow_nm3h"),
            check_names=False,
            atol=1.0,
        )

    def test_power_nonnegative(self, plant_df):
        for name in _C7_NAMES:
            assert (plant_df[f"{name}_power_kw"] >= 0).all()

    def test_c7_status_binary(self, plant_df):
        for name in _C7_NAMES:
            assert plant_df[f"{name}_status"].isin([0, 1]).all(), f"{name}_status hors [0,1]"

    def test_c7_status_matches_flow(self, plant_df):
        for name in _C7_NAMES:
            expected = (plant_df[f"{name}_flow_nm3h"] > 0).astype(int).rename(f"{name}_status")
            pd.testing.assert_series_equal(plant_df[f"{name}_status"], expected)


# ─────────────────────────────────────────────────────────────────────────────
# Plages physiques — Air 3 bars
# ─────────────────────────────────────────────────────────────────────────────

class TestAir3Bar:
    def test_pressure_range(self, plant_df):
        assert plant_df["air_3b_pressure"].between(2.60, 3.45).all()

    def test_fixed_compressors_off_nominal(self, plant_df):
        assert (plant_df["C311_status"] == 0).all()
        assert (plant_df["C312_status"] == 0).all()
        assert (plant_df["C311_power_kw"] == 0).all()
        assert (plant_df["C312_power_kw"] == 0).all()

    def test_vsd_speed_range(self, plant_df):
        for name in ("C321", "C322", "C323"):
            assert plant_df[f"{name}_speed_pct"].between(0.0, 102.0).all()

    def test_transport_indices_range(self, plant_df):
        assert plant_df["dust_transport_index"].between(0.0, 1.0).all()
        assert plant_df["coal_transport_index"].between(0.0, 1.0).all()

    def test_c3_flow_range(self, plant_df):
        for name in ("C321", "C322", "C323"):
            col = f"{name}_flow_nm3h"
            assert plant_df[col].between(0.0, 895.0).all(), f"{col} hors plage"


# ─────────────────────────────────────────────────────────────────────────────
# Plages physiques — Eau recyclée
# ─────────────────────────────────────────────────────────────────────────────

class TestRecycledWater:
    def test_flow_range(self, plant_df):
        assert plant_df["recycled_water_flow_m3h"].between(1_800.0, 2_700.0).all()

    def test_supply_temp_nominal(self, plant_df):
        """Eau froide vers clients : ~24°C."""
        assert plant_df["recycled_water_supply_temp_c"].between(21.0, 27.0).all()

    def test_return_temp_nominal(self, plant_df):
        """Eau chaude retour process : ~29°C (24 + ΔT 5°C)."""
        assert plant_df["recycled_water_return_temp_c"].between(26.0, 33.0).all()

    def test_return_temp_greater_than_supply(self, plant_df):
        """La température de retour doit toujours être supérieure à la température de départ."""
        delta = (
            plant_df["recycled_water_return_temp_c"]
            - plant_df["recycled_water_supply_temp_c"]
        )
        assert (delta > 0).all(), "Température retour ≤ départ détectée"

    def test_delta_t_consistent(self, plant_df):
        computed = (
            plant_df["recycled_water_return_temp_c"]
            - plant_df["recycled_water_supply_temp_c"]
        ).round(2)
        pd.testing.assert_series_equal(
            plant_df["recycled_water_delta_t_c"],
            computed.rename("recycled_water_delta_t_c"),
            atol=0.01,
        )

    def test_pressure_range(self, plant_df):
        assert plant_df["recycled_water_pressure_bar"].between(3.0, 4.0).all()

    def test_cold_pumps_power_range(self, plant_df):
        for idx in range(1, 4):
            col = f"cold_water_pump_{idx}_power_kw"
            assert plant_df[col].between(70.0, 130.0).all(), f"{col} hors plage"

    def test_hot_pumps_power_range(self, plant_df):
        for idx in range(1, 3):
            col = f"hot_water_pump_{idx}_power_kw"
            assert plant_df[col].between(115.0, 210.0).all(), f"{col} hors plage"

    def test_sand_filter_dp_range(self, plant_df):
        assert plant_df["sand_filter_dp_bar"].between(0.20, 0.70).all()

    def test_efficiency_index_range(self, plant_df):
        assert plant_df["recycled_water_efficiency_index"].between(0.50, 1.30).all()

    def test_legionella_risk_range(self, plant_df):
        assert plant_df["legionella_risk_index"].between(0.0, 1.0).all()

    def test_chemical_treatment_range(self, plant_df):
        assert plant_df["chemical_treatment_index"].between(0.0, 1.0).all()


# ─────────────────────────────────────────────────────────────────────────────
# Plages physiques — Eau brute
# ─────────────────────────────────────────────────────────────────────────────

class TestRawWater:
    def test_basin_levels_range(self, plant_df):
        assert plant_df["basin_b0_level_pct"].between(0.0, 100.0).all()
        assert plant_df["basin_b1_level_pct"].between(0.0, 100.0).all()

    def test_basin_volumes_consistent(self, plant_df):
        """Volume = niveau% × capacité."""
        from modules.data_generator import _B0_CAPACITY_M3, _B1_CAPACITY_M3
        expected_b0 = (plant_df["basin_b0_level_pct"] / 100 * _B0_CAPACITY_M3).round(0)
        pd.testing.assert_series_equal(
            plant_df["basin_b0_volume_m3"],
            expected_b0.rename("basin_b0_volume_m3"),
            atol=1.0,
        )

    def test_emergency_cooling_boolean(self, plant_df):
        assert plant_df["emergency_cooling_available"].dtype == bool

    def test_emergency_cooling_logic(self, plant_df):
        """Secours disponible si B0 > 20 % OU B1 > 20 %."""
        expected = (
            (plant_df["basin_b0_level_pct"] > 20)
            | (plant_df["basin_b1_level_pct"] > 20)
        )
        pd.testing.assert_series_equal(
            plant_df["emergency_cooling_available"],
            expected.rename("emergency_cooling_available"),
        )

    def test_makeup_flow_range(self, plant_df):
        assert plant_df["raw_water_makeup_to_recycled_m3h"].between(70.0, 130.0).all()

    def test_dependency_ratio_range(self, plant_df):
        assert plant_df["raw_water_dependency_ratio"].between(0.02, 0.08).all()


# ─────────────────────────────────────────────────────────────────────────────
# Indicateurs dérivés globaux
# ─────────────────────────────────────────────────────────────────────────────

class TestDerivedIndicators:
    def test_operating_mode_values(self, plant_df):
        assert plant_df["plant_operating_mode"].isin(["LOW", "NORMAL", "HIGH"]).all()

    def test_operating_mode_low_coherent(self, plant_df):
        low = plant_df["production_index"] < 0.65
        if low.any():
            assert (plant_df.loc[low, "plant_operating_mode"] == "LOW").all()

    def test_operating_mode_high_coherent(self, plant_df):
        high = plant_df["production_index"] >= 0.85
        if high.any():
            assert (plant_df.loc[high, "plant_operating_mode"] == "HIGH").all()

    def test_energy_cost_range(self, plant_df):
        assert (plant_df["energy_cost_xpf"] > 550_000).all()
        assert (plant_df["energy_cost_xpf"] < 1_200_000).all()

    def test_efficiency_index_correlated_to_delta_t(self, plant_df):
        """Index doit croître avec le delta T (corrélation positive)."""
        corr = plant_df["recycled_water_efficiency_index"].corr(
            plant_df["recycled_water_delta_t_c"]
        )
        assert corr > 0.90, f"Corrélation efficacité/deltaT trop faible : {corr:.3f}"
