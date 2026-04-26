"""
Tests -- Module 7 : business_value.py

Couvre les 6 exigences du cahier des charges :
  1. Aucune anomalie  → cout = 0
  2. Fuite air        → cout energetique > 0
  3. Defaut refroid.  → cout downtime eleve
  4. Compresseur C715 → cout maintenance
  5. Multi-crise      → total eleve
  6. ROI summary non vide
"""

import pytest

from modules.business_value import (
    ECONOMIC_PARAMS,
    EconomicParameters,
    FinancialImpact,
    DEFAULT_PARAMS,
    evaluate_anomaly_cost,
    evaluate_all_costs,
    evaluate_recommendation_value,
    compute_total_business_impact,
    rank_by_financial_impact,
    build_roi_summary,
    estimate_anomaly_cost,
    estimate_action_savings,
    compute_total_financial_exposure,
)
from modules.recommendations import recommendation_for_anomaly, generate_recommendations


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _anomaly(
    anom_type: str,
    severity: str = "medium",
    confidence: float = 0.80,
    aid: str | None = None,
) -> dict:
    return {
        "id":               aid or f"test-{anom_type}",
        "anomaly_type":     anom_type,
        "severity":         severity,
        "confidence_score": confidence,
        "timestamp_start":  "2024-01-15 09:00:00",
        "timestamp_end":    "2024-01-15 10:00:00",
        "asset":            "Test Asset",
        "domain":           "electricity",
    }


# ---------------------------------------------------------------------------
# Constantes economiques
# ---------------------------------------------------------------------------

class TestEconomicConstants:

    def test_required_keys_present(self):
        for k in ["energy_cost_xpf_per_kwh", "downtime_cost_xpf_per_hour",
                  "maintenance_cost_xpf", "water_cost_xpf_per_m3"]:
            assert k in ECONOMIC_PARAMS, f"Cle manquante : {k}"

    def test_energy_cost_22_xpf(self):
        assert ECONOMIC_PARAMS["energy_cost_xpf_per_kwh"] == 22.0

    def test_downtime_cost_1790000_xpf(self):
        assert ECONOMIC_PARAMS["downtime_cost_xpf_per_hour"] == 1_790_000.0

    def test_maintenance_cost_60000_xpf(self):
        assert ECONOMIC_PARAMS["maintenance_cost_xpf"] == 60_000.0

    def test_water_cost_300_xpf(self):
        assert ECONOMIC_PARAMS["water_cost_xpf_per_m3"] == 300.0

    def test_dataclass_matches_dict(self):
        assert DEFAULT_PARAMS.electricity_cost_xpf_kwh == ECONOMIC_PARAMS["energy_cost_xpf_per_kwh"]
        assert DEFAULT_PARAMS.production_loss_xpf_per_h == ECONOMIC_PARAMS["downtime_cost_xpf_per_hour"]
        assert DEFAULT_PARAMS.maintenance_call_xpf == ECONOMIC_PARAMS["maintenance_cost_xpf"]
        assert DEFAULT_PARAMS.water_cost_xpf_m3 == ECONOMIC_PARAMS["water_cost_xpf_per_m3"]


# ---------------------------------------------------------------------------
# 1. Aucune anomalie → cout = 0
# ---------------------------------------------------------------------------

class TestNoAnomaly:

    def test_total_loss_zero(self):
        r = compute_total_business_impact([])
        assert r["total_loss_xpf"] == 0.0

    def test_avoidable_zero(self):
        r = compute_total_business_impact([])
        assert r["avoidable_loss_xpf"] == 0.0

    def test_savings_zero(self):
        r = compute_total_business_impact([])
        assert r["estimated_savings_xpf"] == 0.0

    def test_top_losses_empty(self):
        r = compute_total_business_impact([])
        assert r["top_losses"] == []

    def test_roi_summary_present(self):
        r = compute_total_business_impact([])
        assert r["roi_summary"]
        assert "0 XPF" in r["roi_summary"] or "normaux" in r["roi_summary"]

    def test_evaluate_all_costs_empty(self):
        assert evaluate_all_costs([]) == []

    def test_compute_exposure_zero(self):
        r = compute_total_financial_exposure([])
        assert r["total_cost_xpf"] == 0.0
        assert r["worst_anomaly_id"] is None


# ---------------------------------------------------------------------------
# 2. Fuite air → cout energetique
# ---------------------------------------------------------------------------

class TestAirLeak:

    @pytest.fixture
    def air_anomaly(self):
        return _anomaly("air_leak", "high", confidence=0.88)

    def test_loss_type_is_energy(self, air_anomaly):
        r = evaluate_anomaly_cost(air_anomaly)
        assert r["loss_type"] == "energy"

    def test_cost_positive(self, air_anomaly):
        r = evaluate_anomaly_cost(air_anomaly)
        assert r["estimated_loss_xpf"] > 0.0

    def test_energy_breakdown_positive(self, air_anomaly):
        r = evaluate_anomaly_cost(air_anomaly)
        assert r["breakdown"]["energy"] > 0.0

    def test_has_all_required_fields(self, air_anomaly):
        r = evaluate_anomaly_cost(air_anomaly)
        for field in ["anomaly_id", "estimated_loss_xpf", "loss_type",
                      "confidence", "explanation", "breakdown"]:
            assert field in r, f"Champ manquant : {field}"

    def test_explanation_non_empty(self, air_anomaly):
        r = evaluate_anomaly_cost(air_anomaly)
        assert len(r["explanation"]) > 20

    def test_anomaly_id_preserved(self, air_anomaly):
        r = evaluate_anomaly_cost(air_anomaly)
        assert r["anomaly_id"] == air_anomaly["id"]


# ---------------------------------------------------------------------------
# 3. Defaut refroidissement → cout downtime eleve
# ---------------------------------------------------------------------------

class TestCoolingFault:

    @pytest.fixture
    def cooling_anomaly(self):
        return _anomaly("cooling_fault", "critical", confidence=0.92)

    def test_loss_type_is_downtime(self, cooling_anomaly):
        r = evaluate_anomaly_cost(cooling_anomaly)
        assert r["loss_type"] == "downtime"

    def test_cost_high(self, cooling_anomaly):
        r = evaluate_anomaly_cost(cooling_anomaly)
        assert r["estimated_loss_xpf"] > 100_000.0

    def test_downtime_breakdown_positive(self, cooling_anomaly):
        r = evaluate_anomaly_cost(cooling_anomaly)
        assert r["breakdown"]["downtime"] > 0.0

    def test_critical_higher_than_low(self):
        r_crit = evaluate_anomaly_cost(_anomaly("cooling_fault", "critical", 0.90))
        r_low  = evaluate_anomaly_cost(_anomaly("cooling_fault", "low",      0.90))
        assert r_crit["estimated_loss_xpf"] > r_low["estimated_loss_xpf"]

    def test_high_confidence_higher_than_low_confidence(self):
        r_hc = evaluate_anomaly_cost(_anomaly("cooling_fault", "high", confidence=0.95))
        r_lc = evaluate_anomaly_cost(_anomaly("cooling_fault", "high", confidence=0.50))
        assert r_hc["estimated_loss_xpf"] > r_lc["estimated_loss_xpf"]


# ---------------------------------------------------------------------------
# 4. Compresseur C715 → cout maintenance
# ---------------------------------------------------------------------------

class TestCompressorFault:

    @pytest.fixture
    def comp_anomaly(self):
        return _anomaly("compressor_fault", "medium", confidence=0.80)

    def test_loss_type_is_maintenance(self, comp_anomaly):
        r = evaluate_anomaly_cost(comp_anomaly)
        assert r["loss_type"] == "maintenance"

    def test_cost_positive(self, comp_anomaly):
        r = evaluate_anomaly_cost(comp_anomaly)
        assert r["estimated_loss_xpf"] > 0.0

    def test_maintenance_breakdown_populated(self, comp_anomaly):
        r = evaluate_anomaly_cost(comp_anomaly)
        assert r["breakdown"]["maintenance"] > 0.0

    def test_energy_breakdown_zero(self, comp_anomaly):
        r = evaluate_anomaly_cost(comp_anomaly)
        assert r["breakdown"]["energy"] == 0.0


# ---------------------------------------------------------------------------
# 5. Multi-crise → total eleve
# ---------------------------------------------------------------------------

class TestMultiCrise:

    @pytest.fixture
    def multi_anomalies(self):
        return [
            _anomaly("furnace_overload", "critical", 0.92, aid="mc-elec"),
            _anomaly("air_leak",         "high",     0.88, aid="mc-air"),
            _anomaly("cooling_fault",    "high",     0.91, aid="mc-water"),
            _anomaly("legionella_risk",  "critical", 0.95, aid="mc-legionella"),
        ]

    def test_total_loss_high(self, multi_anomalies):
        r = compute_total_business_impact(multi_anomalies)
        assert r["total_loss_xpf"] > 500_000.0

    def test_avoidable_loss_positive(self, multi_anomalies):
        r = compute_total_business_impact(multi_anomalies)
        assert r["avoidable_loss_xpf"] > 0.0

    def test_avoidable_less_than_total(self, multi_anomalies):
        r = compute_total_business_impact(multi_anomalies)
        assert r["avoidable_loss_xpf"] <= r["total_loss_xpf"]

    def test_top_losses_at_most_3(self, multi_anomalies):
        r = compute_total_business_impact(multi_anomalies)
        assert 1 <= len(r["top_losses"]) <= 3

    def test_breakdown_has_multiple_types(self, multi_anomalies):
        r = compute_total_business_impact(multi_anomalies)
        non_zero = [k for k, v in r["cost_breakdown"].items() if v > 0.0]
        assert len(non_zero) >= 2

    def test_with_recommendations(self, multi_anomalies):
        recs = generate_recommendations(multi_anomalies)
        r = compute_total_business_impact(multi_anomalies, recommendations=recs)
        assert r["estimated_savings_xpf"] > 0.0

    def test_top_loss_is_highest(self, multi_anomalies):
        r = compute_total_business_impact(multi_anomalies)
        if len(r["top_losses"]) >= 2:
            assert r["top_losses"][0]["estimated_loss_xpf"] >= r["top_losses"][1]["estimated_loss_xpf"]


# ---------------------------------------------------------------------------
# 6. ROI summary non vide
# ---------------------------------------------------------------------------

class TestROISummary:

    def test_not_empty_with_anomalies(self):
        r = compute_total_business_impact([_anomaly("furnace_overload", "high")])
        assert r["roi_summary"]
        assert len(r["roi_summary"]) > 50

    def test_mentions_xpf(self):
        r = compute_total_business_impact([_anomaly("cooling_fault", "critical")])
        assert "XPF" in r["roi_summary"]

    def test_mentions_avoidable_percentage(self):
        r = compute_total_business_impact([_anomaly("furnace_overload", "high")])
        assert "%" in r["roi_summary"]

    def test_build_roi_summary_zero_case(self):
        s = build_roi_summary({"total_loss_xpf": 0.0})
        assert s
        assert len(s) > 10

    def test_multi_anomalies_summary_mentions_dominant_type(self):
        anomalies = [_anomaly("cooling_fault", "critical")]
        r = compute_total_business_impact(anomalies)
        # Le type dominant downtime doit apparaitre
        assert any(word in r["roi_summary"].lower()
                   for word in ["downtime", "arret", "production"])


# ---------------------------------------------------------------------------
# evaluate_all_costs
# ---------------------------------------------------------------------------

ANOMALY_TYPES = [
    "furnace_overload", "cat_fault", "overload_15kv",
    "air_leak", "compressor_fault", "compressor_imbalance",
    "vsd_saturation", "bad_regulation",
    "cooling_fault", "legionella_risk",
    "low_basin", "raw_water_overconsumption", "multi_system_fault",
]


class TestEvaluateAllCosts:

    def test_returns_one_result_per_anomaly(self):
        anomalies = [_anomaly("air_leak"), _anomaly("cooling_fault"), _anomaly("cat_fault")]
        costs = evaluate_all_costs(anomalies)
        assert len(costs) == 3

    def test_sorted_descending(self):
        anomalies = [
            _anomaly("compressor_imbalance", "low"),
            _anomaly("legionella_risk",      "critical"),
            _anomaly("air_leak",             "medium"),
        ]
        costs = evaluate_all_costs(anomalies)
        for i in range(len(costs) - 1):
            assert costs[i]["estimated_loss_xpf"] >= costs[i + 1]["estimated_loss_xpf"]

    @pytest.mark.parametrize("anom_type", ANOMALY_TYPES)
    def test_all_types_return_positive_cost(self, anom_type):
        costs = evaluate_all_costs([_anomaly(anom_type, "high")])
        assert costs[0]["estimated_loss_xpf"] > 0.0, \
            f"{anom_type} : cout nul ou negatif"

    def test_empty_returns_empty(self):
        assert evaluate_all_costs([]) == []


# ---------------------------------------------------------------------------
# evaluate_recommendation_value
# ---------------------------------------------------------------------------

class TestEvaluateRecommendationValue:

    @pytest.fixture
    def sample_rec(self):
        recs = recommendation_for_anomaly(_anomaly("furnace_overload", "critical", 0.92))
        return recs[0]

    def test_roi_score_in_range(self, sample_rec):
        v = evaluate_recommendation_value(sample_rec)
        assert 0.0 <= v["roi_score"] <= 100.0

    def test_saving_positive(self, sample_rec):
        v = evaluate_recommendation_value(sample_rec)
        assert v["estimated_saving_xpf"] > 0.0

    def test_payback_positive(self, sample_rec):
        v = evaluate_recommendation_value(sample_rec)
        assert v["payback_hours"] > 0.0

    def test_has_required_keys(self, sample_rec):
        v = evaluate_recommendation_value(sample_rec)
        for k in ["recommendation_id", "action_title", "estimated_saving_xpf",
                  "fix_cost_xpf", "net_saving_xpf", "payback_hours", "roi_score",
                  "implementation_difficulty", "priority"]:
            assert k in v, f"Cle manquante : {k}"

    def test_easy_rec_higher_roi_than_hard(self):
        recs_easy = recommendation_for_anomaly(_anomaly("cat_fault", "critical", 0.92))
        # Trouver une reco easy
        easy = next((r for r in recs_easy if r.implementation_difficulty == "easy"), None)
        hard = next((r for r in recs_easy if r.implementation_difficulty == "hard"), None)
        if easy and hard:
            v_easy = evaluate_recommendation_value(easy)
            v_hard = evaluate_recommendation_value(hard)
            assert v_easy["roi_score"] >= v_hard["roi_score"]


# ---------------------------------------------------------------------------
# rank_by_financial_impact
# ---------------------------------------------------------------------------

class TestRankByFinancialImpact:

    def test_sorts_descending_by_loss(self):
        items = [
            {"estimated_loss_xpf": 10_000.0},
            {"estimated_loss_xpf": 500_000.0},
            {"estimated_loss_xpf": 50_000.0},
        ]
        ranked = rank_by_financial_impact(items)
        assert ranked[0]["estimated_loss_xpf"] == 500_000.0
        assert ranked[-1]["estimated_loss_xpf"] == 10_000.0

    def test_sorts_by_saving_when_no_loss_key(self):
        items = [
            {"estimated_saving_xpf": 30_000.0},
            {"estimated_saving_xpf": 200_000.0},
            {"estimated_saving_xpf": 80_000.0},
        ]
        ranked = rank_by_financial_impact(items)
        assert ranked[0]["estimated_saving_xpf"] == 200_000.0

    def test_empty_returns_empty(self):
        assert rank_by_financial_impact([]) == []

    def test_single_element_unchanged(self):
        items = [{"estimated_loss_xpf": 99.0}]
        assert rank_by_financial_impact(items) == items


# ---------------------------------------------------------------------------
# Backward-compat : estimate_anomaly_cost → FinancialImpact
# ---------------------------------------------------------------------------

class TestEstimateAnomalyCost:

    def test_returns_financial_impact_instance(self):
        fi = estimate_anomaly_cost(_anomaly("air_leak", "high"))
        assert isinstance(fi, FinancialImpact)

    def test_cost_if_ignored_positive(self):
        fi = estimate_anomaly_cost(_anomaly("cooling_fault", "critical"))
        assert fi.cost_if_ignored_xpf > 0.0

    def test_savings_non_negative(self):
        fi = estimate_anomaly_cost(_anomaly("furnace_overload", "high"))
        assert fi.savings_xpf >= 0.0

    def test_confidence_label_valid(self):
        fi = estimate_anomaly_cost(_anomaly("air_leak", "medium", confidence=0.85))
        assert fi.confidence in ("low", "medium", "high")

    def test_duration_scales_cost(self):
        fi_1h  = estimate_anomaly_cost(_anomaly("furnace_overload", "high"), duration_hours=1.0)
        fi_8h  = estimate_anomaly_cost(_anomaly("furnace_overload", "high"), duration_hours=8.0)
        assert fi_8h.cost_if_ignored_xpf > fi_1h.cost_if_ignored_xpf

    def test_breakdown_dict_has_required_keys(self):
        fi = estimate_anomaly_cost(_anomaly("air_leak"))
        for k in ["energy", "downtime", "maintenance", "water"]:
            assert k in fi.breakdown


# ---------------------------------------------------------------------------
# Backward-compat : estimate_action_savings → FinancialImpact
# ---------------------------------------------------------------------------

class TestEstimateActionSavings:

    def test_returns_financial_impact(self):
        anomaly = _anomaly("furnace_overload", "critical", 0.92)
        rec     = recommendation_for_anomaly(anomaly)[0]
        fi      = estimate_action_savings(rec, anomaly)
        assert isinstance(fi, FinancialImpact)

    def test_recommendation_id_preserved(self):
        anomaly = _anomaly("air_leak", "high", 0.88)
        rec     = recommendation_for_anomaly(anomaly)[0]
        fi      = estimate_action_savings(rec, anomaly)
        assert fi.recommendation_id == rec.id

    def test_savings_non_negative(self):
        anomaly = _anomaly("cooling_fault", "critical", 0.92)
        rec     = recommendation_for_anomaly(anomaly)[0]
        fi      = estimate_action_savings(rec, anomaly)
        assert fi.savings_xpf >= 0.0


# ---------------------------------------------------------------------------
# Backward-compat : compute_total_financial_exposure
# ---------------------------------------------------------------------------

class TestComputeTotalFinancialExposure:

    def test_empty_returns_zero(self):
        r = compute_total_financial_exposure([])
        assert r["total_cost_xpf"] == 0.0
        assert r["worst_anomaly_id"] is None

    def test_worst_anomaly_identified(self):
        anomalies = [
            _anomaly("bad_regulation",  "low",      aid="anon-cheap"),
            _anomaly("legionella_risk", "critical", aid="anon-expensive"),
        ]
        r = compute_total_financial_exposure(anomalies)
        assert r["worst_anomaly_id"] == "anon-expensive"

    def test_hourly_rate_positive(self):
        r = compute_total_financial_exposure([_anomaly("cooling_fault", "high")])
        assert r["hourly_rate_xpf_h"] > 0.0

    def test_breakdown_by_system_populated(self):
        anomalies = [
            _anomaly("air_leak",         aid="a1"),
            _anomaly("cooling_fault",    aid="a2"),
        ]
        r = compute_total_financial_exposure(anomalies)
        assert "electricity" in r["breakdown_by_system"]

    def test_total_equals_sum_of_individual(self):
        anomalies = [
            _anomaly("furnace_overload", "high"),
            _anomaly("air_leak",         "medium"),
        ]
        individual = sum(evaluate_anomaly_cost(a)["estimated_loss_xpf"] for a in anomalies)
        r = compute_total_financial_exposure(anomalies)
        assert r["total_cost_xpf"] == individual
