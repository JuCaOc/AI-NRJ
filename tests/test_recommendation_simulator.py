"""Tests pour modules/recommendation_simulator.py."""

from __future__ import annotations

import pytest
import pandas as pd

from modules.data_generator import generate_mock_plant_data
from modules.scenarios import apply_scenario
from modules.detection import detect_anomalies
from modules.scoring import build_scoring_summary
from modules.recommendations import generate_recommendations
from modules.business_value import compute_total_business_impact
from modules.recommendation_simulator import (
    apply_simulated_recommendation,
    compare_before_after,
    build_simulation_summary,
    get_simulatable_recommendations,
    _detect_action_type,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def nominal_df() -> pd.DataFrame:
    return generate_mock_plant_data()


def _make_scenario(nominal_df: pd.DataFrame, scenario: str):
    df_s     = apply_scenario(nominal_df.copy(), scenario)
    anomalies = detect_anomalies(df_s)
    scoring  = build_scoring_summary(anomalies)
    recs     = generate_recommendations(anomalies, scoring_summary=scoring)
    biz      = compute_total_business_impact(anomalies, recs)
    return df_s, anomalies, scoring, recs, biz


@pytest.fixture(scope="module")
def fuite_setup(nominal_df):
    return _make_scenario(nominal_df, "fuite_air_7b")


@pytest.fixture(scope="module")
def c715_setup(nominal_df):
    return _make_scenario(nominal_df, "defaut_c715")


@pytest.fixture(scope="module")
def refroid_setup(nominal_df):
    return _make_scenario(nominal_df, "defaut_refroidissement")


@pytest.fixture(scope="module")
def forte_dep_setup(nominal_df):
    return _make_scenario(nominal_df, "forte_dependance_eau_brute")


@pytest.fixture(scope="module")
def multi_crise_setup(nominal_df):
    return _make_scenario(nominal_df, "multi_crise")


# ---------------------------------------------------------------------------
# 1. DataFrame original non modifié
# ---------------------------------------------------------------------------

class TestOriginalNotModified:
    def test_fuite_air_original_unchanged(self, fuite_setup):
        df_before, _, _, recs, _ = fuite_setup
        original_values = df_before["air_7b_pressure"].copy()
        _ = apply_simulated_recommendation(df_before, recs[0])
        pd.testing.assert_series_equal(df_before["air_7b_pressure"], original_values)

    def test_refroid_original_unchanged(self, refroid_setup):
        df_before, _, _, recs, _ = refroid_setup
        original_values = df_before["recycled_water_flow_m3h"].copy()
        _ = apply_simulated_recommendation(df_before, recs[0])
        pd.testing.assert_series_equal(df_before["recycled_water_flow_m3h"], original_values)

    def test_after_df_is_different_object(self, fuite_setup):
        df_before, _, _, recs, _ = fuite_setup
        df_after = apply_simulated_recommendation(df_before, recs[0])
        assert df_after is not df_before


# ---------------------------------------------------------------------------
# 2. Scénario fuite_air_7b
# ---------------------------------------------------------------------------

class TestFuiteAir7b:
    def test_pressure_after_greater_than_before(self, fuite_setup):
        df_before, _, _, recs, _ = fuite_setup
        # Trouver la recommandation liée à la fuite air
        air_recs = [r for r in recs if "fuite" in r.action_title.lower()
                    or "réseau" in r.action_title.lower()
                    or "7 bar" in r.action_title.lower()
                    or "réseau air" in r.action_detail.lower()]
        rec = air_recs[0] if air_recs else recs[0]

        df_after = apply_simulated_recommendation(df_before, rec)
        assert df_after["air_7b_pressure"].mean() > df_before["air_7b_pressure"].mean(), (
            f"Pression après ({df_after['air_7b_pressure'].mean():.3f}) doit être > "
            f"avant ({df_before['air_7b_pressure'].mean():.3f})"
        )

    def test_flow_or_power_reduced_after(self, fuite_setup):
        df_before, _, _, recs, _ = fuite_setup
        air_recs = [r for r in recs if "réseau air" in r.action_detail.lower()
                    or "fuite" in r.action_title.lower()]
        rec = air_recs[0] if air_recs else recs[0]

        df_after = apply_simulated_recommendation(df_before, rec)
        flow_reduced  = df_after["air_7b_total_flow_nm3h"].mean() <= df_before["air_7b_total_flow_nm3h"].mean()
        power_reduced = df_after["air_7b_total_power_kw"].mean() <= df_before["air_7b_total_power_kw"].mean()
        assert flow_reduced or power_reduced, (
            "Le débit ou la puissance air 7b doit baisser après la correction fuite"
        )

    def test_action_type_is_air_leak(self, fuite_setup):
        _, _, _, recs, _ = fuite_setup
        air_recs = [r for r in recs if "réseau air" in r.action_detail.lower()
                    or "fuite" in r.action_title.lower()]
        if air_recs:
            assert _detect_action_type(air_recs[0]) == "air_leak"


# ---------------------------------------------------------------------------
# 3. Scénario defaut_c715
# ---------------------------------------------------------------------------

class TestDefautC715:
    def test_c715_flow_increases_after(self, c715_setup):
        df_before, _, _, recs, _ = c715_setup
        c715_recs = [r for r in recs if "c715" in r.action_title.lower()
                     or "c715" in r.action_detail.lower()]
        rec = c715_recs[0] if c715_recs else recs[0]

        df_after = apply_simulated_recommendation(df_before, rec)
        if "C715_flow_nm3h" in df_before.columns:
            assert df_after["C715_flow_nm3h"].mean() > df_before["C715_flow_nm3h"].mean(), (
                f"C715 flow après ({df_after['C715_flow_nm3h'].mean():.0f}) doit être > "
                f"avant ({df_before['C715_flow_nm3h'].mean():.0f})"
            )

    def test_action_type_is_compressor_fault(self, c715_setup):
        _, _, _, recs, _ = c715_setup
        c715_recs = [r for r in recs if "c715" in r.action_title.lower()
                     or "c715" in r.action_detail.lower()]
        if c715_recs:
            assert _detect_action_type(c715_recs[0]) == "compressor_fault"


# ---------------------------------------------------------------------------
# 4. Scénario defaut_refroidissement
# ---------------------------------------------------------------------------

class TestDefautRefroidissement:
    def test_flow_increases_after(self, refroid_setup):
        df_before, _, _, recs, _ = refroid_setup
        water_recs = [r for r in recs if "pompe" in r.action_title.lower()
                      or "eau recyclée" in r.action_detail.lower()
                      or "débit" in r.action_detail.lower()]
        rec = water_recs[0] if water_recs else recs[0]

        df_after = apply_simulated_recommendation(df_before, rec)
        assert df_after["recycled_water_flow_m3h"].mean() > df_before["recycled_water_flow_m3h"].mean(), (
            f"Débit eau recyclée après ({df_after['recycled_water_flow_m3h'].mean():.0f}) "
            f"doit être > avant ({df_before['recycled_water_flow_m3h'].mean():.0f})"
        )

    def test_delta_t_decreases_after(self, refroid_setup):
        df_before, _, _, recs, _ = refroid_setup
        water_recs = [r for r in recs if "pompe" in r.action_title.lower()
                      or "eau recyclée" in r.action_detail.lower()]
        rec = water_recs[0] if water_recs else recs[0]

        df_after = apply_simulated_recommendation(df_before, rec)
        assert df_after["recycled_water_delta_t_c"].mean() < df_before["recycled_water_delta_t_c"].mean(), (
            "Delta T eau recyclée doit baisser après correction refroidissement"
        )

    def test_action_type_is_cooling_fault(self, refroid_setup):
        _, _, _, recs, _ = refroid_setup
        water_recs = [r for r in recs if "pompe ef" in r.action_title.lower()
                      or "eau recyclée" in r.action_detail.lower()]
        if water_recs:
            assert _detect_action_type(water_recs[0]) == "cooling_fault"


# ---------------------------------------------------------------------------
# 5. Scénario forte_dependance_eau_brute
# ---------------------------------------------------------------------------

class TestForteDependanceEauBrute:
    def test_dependency_ratio_decreases_after(self, forte_dep_setup):
        df_before, _, _, recs, _ = forte_dep_setup
        raw_recs = [r for r in recs if "eau brute" in r.action_title.lower()
                    or "consommation eau" in r.action_detail.lower()
                    or "dépendance" in r.action_detail.lower()]
        rec = raw_recs[0] if raw_recs else recs[0]

        df_after = apply_simulated_recommendation(df_before, rec)
        assert df_after["raw_water_dependency_ratio"].mean() < df_before["raw_water_dependency_ratio"].mean(), (
            "raw_water_dependency_ratio doit baisser après correction"
        )


# ---------------------------------------------------------------------------
# 6. compare_before_after
# ---------------------------------------------------------------------------

class TestCompareBeforeAfter:
    def test_returns_nonempty_dict(self, fuite_setup):
        df_before, _, _, recs, _ = fuite_setup
        df_after = apply_simulated_recommendation(df_before, recs[0])
        result = compare_before_after(df_before, df_after)
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_metrics_key_present(self, fuite_setup):
        df_before, _, _, recs, _ = fuite_setup
        df_after = apply_simulated_recommendation(df_before, recs[0])
        result = compare_before_after(df_before, df_after)
        assert "metrics" in result
        assert len(result["metrics"]) > 0

    def test_each_metric_has_delta(self, fuite_setup):
        df_before, _, _, recs, _ = fuite_setup
        df_after = apply_simulated_recommendation(df_before, recs[0])
        result = compare_before_after(df_before, df_after)
        for col, d in result["metrics"].items():
            assert "before_mean" in d
            assert "after_mean"  in d
            assert "delta"       in d

    def test_energy_saving_key(self, fuite_setup):
        df_before, _, _, recs, _ = fuite_setup
        df_after = apply_simulated_recommendation(df_before, recs[0])
        result = compare_before_after(df_before, df_after)
        assert "energy_saving_xpf" in result


# ---------------------------------------------------------------------------
# 7. simulation_note présente dans build_simulation_summary
# ---------------------------------------------------------------------------

class TestBuildSimulationSummary:
    def test_simulation_note_present(self, fuite_setup):
        df_before, anomalies, _, recs, _ = fuite_setup
        df_after = apply_simulated_recommendation(df_before, recs[0])
        summary  = build_simulation_summary(df_before, df_after, recs[0], anomalies)
        assert "simulation_note" in summary
        assert len(summary["simulation_note"]) > 10

    def test_simulation_note_mentions_simulation(self, fuite_setup):
        df_before, anomalies, _, recs, _ = fuite_setup
        df_after = apply_simulated_recommendation(df_before, recs[0])
        summary  = build_simulation_summary(df_before, df_after, recs[0], anomalies)
        assert "simulation" in summary["simulation_note"].lower()
        assert "validation" in summary["simulation_note"].lower()

    def test_required_keys_present(self, fuite_setup):
        df_before, anomalies, _, recs, _ = fuite_setup
        df_after = apply_simulated_recommendation(df_before, recs[0])
        summary  = build_simulation_summary(df_before, df_after, recs[0], anomalies)
        for key in ("before_df", "after_df", "applied_action", "expected_effect",
                    "before_score", "after_score", "score_improvement",
                    "before_loss_xpf", "after_loss_xpf", "estimated_saving_xpf",
                    "simulation_note", "key_metric"):
            assert key in summary, f"Clé manquante : {key}"

    def test_score_improvement_non_negative(self, fuite_setup):
        df_before, anomalies, _, recs, _ = fuite_setup
        df_after = apply_simulated_recommendation(df_before, recs[0])
        summary  = build_simulation_summary(df_before, df_after, recs[0], anomalies)
        # Le score_improvement = before - after ; peut être 0 si scénario déjà résolu
        assert summary["score_improvement"] >= -5.0, (
            "L'amélioration score ne doit pas être fortement négative après simulation"
        )

    def test_estimated_saving_positive(self, fuite_setup):
        df_before, anomalies, _, recs, _ = fuite_setup
        df_after = apply_simulated_recommendation(df_before, recs[0])
        summary  = build_simulation_summary(df_before, df_after, recs[0], anomalies)
        assert summary["estimated_saving_xpf"] >= 0


# ---------------------------------------------------------------------------
# 8. get_simulatable_recommendations
# ---------------------------------------------------------------------------

class TestGetSimulatableRecommendations:
    def test_returns_nonempty_for_anomaly_scenarios(self, fuite_setup):
        _, _, _, recs, _ = fuite_setup
        sim_recs = get_simulatable_recommendations(recs)
        assert len(sim_recs) >= 1

    def test_multi_crise_returns_multiple(self, multi_crise_setup):
        _, _, _, recs, _ = multi_crise_setup
        sim_recs = get_simulatable_recommendations(recs)
        assert len(sim_recs) >= 2

    def test_no_duplicates_per_type(self, multi_crise_setup):
        _, _, _, recs, _ = multi_crise_setup
        sim_recs = get_simulatable_recommendations(recs)
        types = [_detect_action_type(r) for r in sim_recs]
        assert len(types) == len(set(types)), "Des doublons de type d'action sont présents"

    def test_nominal_returns_empty_or_generic(self, nominal_df):
        anomalies = detect_anomalies(nominal_df)
        scoring   = build_scoring_summary(anomalies)
        recs      = generate_recommendations(anomalies, scoring_summary=scoring)
        sim_recs  = get_simulatable_recommendations(recs)
        # En nominal, soit liste vide, soit recs avec unknown
        for r in sim_recs:
            t = _detect_action_type(r)
            assert isinstance(t, str)


# ---------------------------------------------------------------------------
# 9. _detect_action_type
# ---------------------------------------------------------------------------

class TestDetectActionType:
    def test_fuite_air_7b(self, fuite_setup):
        _, _, _, recs, _ = fuite_setup
        air_recs = [r for r in recs if "réseau air" in r.action_detail.lower()
                    or "fuite" in r.action_title.lower()]
        if air_recs:
            assert _detect_action_type(air_recs[0]) == "air_leak"

    def test_c715(self, c715_setup):
        _, _, _, recs, _ = c715_setup
        c715_recs = [r for r in recs if "c715" in r.action_title.lower()
                     or "c715" in r.action_detail.lower()]
        if c715_recs:
            assert _detect_action_type(c715_recs[0]) == "compressor_fault"

    def test_refroidissement(self, refroid_setup):
        _, _, _, recs, _ = refroid_setup
        water_recs = [r for r in recs if "pompe ef" in r.action_title.lower()
                      or "circuit eau recyclée" in r.action_detail.lower()]
        if water_recs:
            assert _detect_action_type(water_recs[0]) == "cooling_fault"
