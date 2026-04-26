"""
Tests — Module 6 : recommendations.py

Couvre les 5 exigences du cahier des charges :
  1. Chaque type d'anomalie → au moins 1 recommandation
  2. Priorité cohérente : critical → urgent
  3. Savings > 0 pour anomalies énergétiques
  4. human_validation_required = True pour toutes les actions critiques
  5. Multi-crise : plusieurs recommandations, priorisation correcte
"""

import pytest
from modules.recommendations import (
    Recommendation,
    PRIORITY_RULES,
    RISK_REDUCTION,
    recommendation_for_anomaly,
    estimate_savings,
    estimate_risk_reduction,
    generate_recommendations,
    prioritize_recommendations,
    deduplicate_recommendations,
    summarize_recommendations,
    # backward-compat aliases
    recommend_for_anomaly,
    recommend_all,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _anomaly(
    anomaly_type: str,
    severity: str = "medium",
    confidence: float = 0.80,
    anomaly_id: str | None = None,
) -> dict:
    return {
        "id":               anomaly_id or f"test-{anomaly_type}",
        "domain":           "electricity",
        "anomaly_type":     anomaly_type,
        "severity":         severity,
        "confidence_score": confidence,
        "timestamp_start":  "2024-01-15 09:00:00",
        "timestamp_end":    "2024-01-15 10:00:00",
        "asset":            "Test Asset",
        "description":      "Test anomaly",
    }


def _rec(priority: str, saving: float = 50_000.0, anomaly_id: str = "anon") -> Recommendation:
    return Recommendation(
        id=f"REC-{priority}-test",
        linked_anomaly_id=anomaly_id,
        priority=priority,
        action_title=f"Action {priority}",
        action_detail="Détail de l'action",
        expected_effect="Effet attendu",
        estimated_saving_xpf=saving,
        estimated_risk_reduction_pct=30.0,
        implementation_difficulty="medium",
        human_validation_required=True,
        safety_note="Note de sécurité",
    )


# ---------------------------------------------------------------------------
# 1 — Chaque type d'anomalie → au moins 1 recommandation
# ---------------------------------------------------------------------------

ALL_ANOMALY_TYPES = [
    "furnace_overload",
    "cat_fault",
    "overload_15kv",
    "air_leak",
    "compressor_fault",
    "compressor_imbalance",
    "vsd_saturation",
    "bad_regulation",
    "cooling_fault",
    "legionella_risk",
    "low_basin",
    "raw_water_overconsumption",
    "multi_system_fault",
]


class TestRecommendForAnomaly:

    @pytest.mark.parametrize("anom_type", ALL_ANOMALY_TYPES)
    def test_each_type_has_at_least_one_recommendation(self, anom_type):
        recs = recommendation_for_anomaly(_anomaly(anom_type))
        assert len(recs) >= 1, f"{anom_type} ne génère aucune recommandation"

    def test_unknown_type_has_fallback(self):
        recs = recommendation_for_anomaly(_anomaly("type_inconnu_xyz"))
        assert len(recs) >= 1

    def test_recommendation_has_required_fields(self):
        rec = recommendation_for_anomaly(_anomaly("furnace_overload", severity="high"))[0]
        assert rec.id
        assert rec.linked_anomaly_id == "test-furnace_overload"
        assert rec.priority
        assert rec.action_title
        assert rec.action_detail
        assert rec.expected_effect
        assert rec.safety_note
        assert isinstance(rec.steps, list)

    def test_id_contains_anomaly_id(self):
        anomaly = _anomaly("air_leak", anomaly_id="ANOM-007")
        recs = recommendation_for_anomaly(anomaly)
        assert all("ANOM-007" in r.id for r in recs)
        assert all(r.linked_anomaly_id == "ANOM-007" for r in recs)

    def test_recommendation_has_steps(self):
        for anom_type in ALL_ANOMALY_TYPES:
            recs = recommendation_for_anomaly(_anomaly(anom_type))
            assert all(len(r.steps) >= 2 for r in recs), \
                f"{anom_type} : steps insuffisants (< 2)"

    def test_human_validation_always_required(self):
        """Toute recommandation doit avoir human_validation_required = True."""
        for anom_type in ALL_ANOMALY_TYPES:
            recs = recommendation_for_anomaly(_anomaly(anom_type, severity="critical"))
            assert all(r.human_validation_required for r in recs), \
                f"{anom_type} : human_validation_required manquant"


# ---------------------------------------------------------------------------
# 2 — Priorité cohérente
# ---------------------------------------------------------------------------

class TestPriorityMapping:

    @pytest.mark.parametrize("severity,expected", [
        ("critical", "urgent"),
        ("high",     "high"),
        ("medium",   "medium"),
        ("low",      "low"),
    ])
    def test_severity_maps_to_priority(self, severity, expected):
        recs = recommendation_for_anomaly(_anomaly("furnace_overload", severity=severity))
        assert all(r.priority == expected for r in recs)

    def test_priority_rules_covers_all_severities(self):
        assert set(PRIORITY_RULES.keys()) == {"critical", "high", "medium", "low"}

    def test_priority_rules_has_urgent(self):
        assert "urgent" in PRIORITY_RULES.values()

    def test_risk_reduction_table_complete(self):
        assert set(RISK_REDUCTION.keys()) == {"urgent", "high", "medium", "low"}
        assert RISK_REDUCTION["urgent"] > RISK_REDUCTION["low"]


# ---------------------------------------------------------------------------
# 3 — Savings > 0 pour anomalies énergétiques
# ---------------------------------------------------------------------------

class TestEstimateSavings:

    @pytest.mark.parametrize("anom_type", ["furnace_overload", "cat_fault", "overload_15kv"])
    def test_energy_anomalies_savings_positive(self, anom_type):
        saving = estimate_savings(_anomaly(anom_type, severity="high"))
        assert saving > 0.0, f"{anom_type} : saving nul ou négatif"

    @pytest.mark.parametrize("anom_type", ["air_leak", "cooling_fault", "legionella_risk"])
    def test_other_anomalies_savings_positive(self, anom_type):
        saving = estimate_savings(_anomaly(anom_type, severity="medium"))
        assert saving > 0.0

    def test_critical_saving_higher_than_low(self):
        s_critical = estimate_savings(_anomaly("furnace_overload", severity="critical"))
        s_low      = estimate_savings(_anomaly("furnace_overload", severity="low"))
        assert s_critical > s_low

    def test_savings_embedded_in_recommendations_positive(self):
        for anom_type in ["furnace_overload", "air_leak", "cooling_fault", "cat_fault"]:
            recs = recommendation_for_anomaly(_anomaly(anom_type, severity="high"))
            assert all(r.estimated_saving_xpf > 0.0 for r in recs), \
                f"{anom_type} : saving nul dans la recommandation"

    def test_confidence_scales_savings(self):
        high_conf = estimate_savings(_anomaly("air_leak", confidence=0.95))
        low_conf  = estimate_savings(_anomaly("air_leak", confidence=0.50))
        assert high_conf > low_conf


# ---------------------------------------------------------------------------
# Réduction de risque
# ---------------------------------------------------------------------------

class TestEstimateRiskReduction:

    @pytest.mark.parametrize("severity,expected_pct", [
        ("critical", 80.0),
        ("high",     60.0),
        ("medium",   30.0),
        ("low",      10.0),
    ])
    def test_risk_reduction_by_severity(self, severity, expected_pct):
        anom = _anomaly("furnace_overload", severity=severity)
        assert estimate_risk_reduction(anom) == expected_pct

    def test_risk_reduction_in_recommendations(self):
        rec_critical = recommendation_for_anomaly(_anomaly("cooling_fault", severity="critical"))[0]
        rec_low      = recommendation_for_anomaly(_anomaly("cooling_fault", severity="low"))[0]
        assert rec_critical.estimated_risk_reduction_pct > rec_low.estimated_risk_reduction_pct


# ---------------------------------------------------------------------------
# 4 — human_validation_required = True pour critiques
# ---------------------------------------------------------------------------

class TestHumanValidation:

    @pytest.mark.parametrize("anom_type", [
        "furnace_overload", "cat_fault", "cooling_fault",
        "legionella_risk", "multi_system_fault",
    ])
    def test_critical_requires_human_validation(self, anom_type):
        recs = recommendation_for_anomaly(_anomaly(anom_type, severity="critical"))
        assert all(r.human_validation_required for r in recs)

    def test_all_severities_require_human_validation(self):
        for sev in ["critical", "high", "medium", "low"]:
            recs = recommendation_for_anomaly(_anomaly("air_leak", severity=sev))
            assert all(r.human_validation_required for r in recs), \
                f"severity={sev} : human_validation_required manquant"


# ---------------------------------------------------------------------------
# 5 — Multi-crise
# ---------------------------------------------------------------------------

class TestMultiCrise:

    @pytest.fixture
    def multi_anomalies(self):
        return [
            _anomaly("furnace_overload", severity="critical", confidence=0.92, anomaly_id="mc-elec"),
            _anomaly("air_leak",         severity="high",     confidence=0.88, anomaly_id="mc-air"),
            _anomaly("cooling_fault",    severity="high",     confidence=0.91, anomaly_id="mc-water"),
        ]

    def test_at_least_3_recommendations(self, multi_anomalies):
        recs = generate_recommendations(multi_anomalies)
        assert len(recs) >= 3

    def test_urgent_recommendation_first(self, multi_anomalies):
        recs = generate_recommendations(multi_anomalies)
        assert recs[0].priority == "urgent"

    def test_all_anomaly_ids_covered(self, multi_anomalies):
        recs = generate_recommendations(multi_anomalies)
        linked = {r.linked_anomaly_id for r in recs}
        assert {"mc-elec", "mc-air", "mc-water"}.issubset(linked)

    def test_total_saving_significant(self, multi_anomalies):
        recs = generate_recommendations(multi_anomalies)
        assert sum(r.estimated_saving_xpf for r in recs) > 100_000.0

    def test_no_recommendation_without_human_validation(self, multi_anomalies):
        recs = generate_recommendations(multi_anomalies)
        assert all(r.human_validation_required for r in recs)

    def test_all_recs_have_safety_notes(self, multi_anomalies):
        recs = generate_recommendations(multi_anomalies)
        assert all(r.safety_note for r in recs)

    def test_sorted_no_low_before_urgent(self, multi_anomalies):
        recs = generate_recommendations(multi_anomalies)
        p_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
        for i in range(len(recs) - 1):
            assert p_order[recs[i].priority] <= p_order[recs[i + 1].priority]


# ---------------------------------------------------------------------------
# Prioritize
# ---------------------------------------------------------------------------

class TestPrioritizeRecommendations:

    def test_urgent_high_medium_low_order(self):
        recs = [_rec("low"), _rec("urgent"), _rec("medium"), _rec("high")]
        out  = prioritize_recommendations(recs)
        assert [r.priority for r in out] == ["urgent", "high", "medium", "low"]

    def test_same_priority_higher_saving_first(self):
        recs = [_rec("high", 10_000), _rec("high", 80_000), _rec("high", 40_000)]
        out  = prioritize_recommendations(recs)
        assert out[0].estimated_saving_xpf == 80_000.0

    def test_empty_list_returns_empty(self):
        assert prioritize_recommendations([]) == []

    def test_single_element_unchanged(self):
        recs = [_rec("medium")]
        assert prioritize_recommendations(recs) == recs


# ---------------------------------------------------------------------------
# Generate
# ---------------------------------------------------------------------------

class TestGenerateRecommendations:

    def test_empty_anomalies_returns_empty(self):
        assert generate_recommendations([]) == []

    def test_urgent_before_low(self):
        anomalies = [
            _anomaly("air_leak",         severity="low"),
            _anomaly("furnace_overload", severity="critical"),
        ]
        recs = generate_recommendations(anomalies)
        assert recs[0].priority == "urgent"

    def test_accepts_scoring_summary_kwarg(self):
        summary = {"global_score": 65.0, "status": "ALERTE"}
        recs    = generate_recommendations(
            [_anomaly("cat_fault", severity="high")],
            scoring_summary=summary,
        )
        assert len(recs) >= 1

    def test_deduplication_applied(self):
        """Deux fois la même anomalie → pas de doublon dans le résultat."""
        anomaly = _anomaly("furnace_overload", severity="critical")
        recs    = generate_recommendations([anomaly, anomaly])
        titles  = [(r.linked_anomaly_id, r.action_title) for r in recs]
        assert len(titles) == len(set(titles))


# ---------------------------------------------------------------------------
# Summarize
# ---------------------------------------------------------------------------

class TestSummarizeRecommendations:

    def test_empty_returns_zeros(self):
        s = summarize_recommendations([])
        assert s["count"] == 0
        assert s["total_saving_xpf"] == 0.0
        assert s["top_action"] is None
        assert s["has_safety_risk"] is False

    def test_count_matches(self):
        recs = [_rec("urgent"), _rec("high"), _rec("medium")]
        s = summarize_recommendations(recs)
        assert s["count"] == 3

    def test_urgent_count_correct(self):
        recs = [_rec("urgent"), _rec("urgent"), _rec("medium")]
        s = summarize_recommendations(recs)
        assert s["urgent_count"] == 2

    def test_top_action_is_first(self):
        recs = [_rec("urgent"), _rec("medium")]
        s = summarize_recommendations(recs)
        assert s["top_action"] == recs[0].action_title

    def test_total_saving_sum(self):
        recs = [_rec("urgent", 50_000), _rec("high", 30_000)]
        s = summarize_recommendations(recs)
        assert s["total_saving_xpf"] == 80_000.0

    def test_has_safety_risk_detected(self):
        anomalies = [_anomaly("legionella_risk", severity="critical")]
        recs = generate_recommendations(anomalies)
        s = summarize_recommendations(recs)
        assert s["has_safety_risk"] is True


# ---------------------------------------------------------------------------
# Deduplicate
# ---------------------------------------------------------------------------

class TestDeduplicate:

    def test_distinct_recommendations_preserved(self):
        r1 = _rec("medium", anomaly_id="anon-1")
        r2 = _rec("medium", anomaly_id="anon-2")
        r1.action_title = "Action A"
        r2.action_title = "Action B"
        result = deduplicate_recommendations([r1, r2])
        assert len(result) == 2

    def test_same_equipment_merged(self):
        """Deux recommandations identiques (même anomalie, même titre) → 1 seule."""
        r1 = _rec("high", anomaly_id="same-id")
        r2 = _rec("high", anomaly_id="same-id")
        result = deduplicate_recommendations([r1, r2])
        assert len(result) == 1

    def test_order_preserved(self):
        recs = [
            _rec("urgent", anomaly_id="a1"),
            _rec("high",   anomaly_id="a2"),
            _rec("medium", anomaly_id="a3"),
        ]
        recs[0].action_title = "A1"
        recs[1].action_title = "A2"
        recs[2].action_title = "A3"
        result = deduplicate_recommendations(recs)
        assert [r.action_title for r in result] == ["A1", "A2", "A3"]

    def test_empty_input_returns_empty(self):
        assert deduplicate_recommendations([]) == []


# ---------------------------------------------------------------------------
# Backward-compat aliases
# ---------------------------------------------------------------------------

class TestRecommendAll:

    def test_sorted_by_priority(self):
        anomalies = [
            _anomaly("air_leak",         severity="low"),
            _anomaly("furnace_overload", severity="critical"),
            _anomaly("cooling_fault",    severity="high"),
        ]
        recs = recommend_all(anomalies)
        p_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
        for i in range(len(recs) - 1):
            assert p_order[recs[i].priority] <= p_order[recs[i + 1].priority]

    def test_no_duplicate_targets(self):
        anomaly = _anomaly("furnace_overload", severity="critical")
        recs    = recommend_all([anomaly, anomaly])
        titles  = [(r.linked_anomaly_id, r.action_title) for r in recs]
        assert len(titles) == len(set(titles))
