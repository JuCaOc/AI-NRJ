"""
Tests unitaires et d'intégration — scoring.py

Couvre les 7 zones spécifiées :
1. Aucune anomalie → score 0, statut NORMAL
2. Anomalie low     → score faible, NORMAL ou VIGILANCE
3. Anomalie high air 7 bars → score élevé, ALERTE ou CRITIQUE
4. Anomalie critical eau recyclée → score très élevé, CRITIQUE
5. Multi-crise      → score global élevé, CRITIQUE, plusieurs domaines
6. Bornage          → aucun score < 0 ou > 100
7. Explication      → chaque score a une explanation non vide
"""

import pytest

from modules.scoring import (
    score_anomaly,
    compute_domain_scores,
    compute_global_plant_score,
    get_plant_status,
    build_scoring_summary,
)
from modules.data_generator import generate_mock_plant_data
from modules.scenarios import apply_scenario
from modules.detection import detect_anomalies


# ---------------------------------------------------------------------------
# Helpers partagés
# ---------------------------------------------------------------------------

def _mock(
    severity: str,
    domain: str,
    asset: str,
    anomaly_type: str,
    confidence: float = 0.80,
    ts_start: str = "2024-01-01 08:00:00",
    ts_end: str   = "2024-01-01 16:00:00",
) -> dict:
    return {
        "id":              f"MOCK_{anomaly_type.upper()}",
        "domain":          domain,
        "asset":           asset,
        "severity":        severity,
        "anomaly_type":    anomaly_type,
        "confidence_score": confidence,
        "timestamp_start": ts_start,
        "timestamp_end":   ts_end,
    }


def _detect(scenario: str) -> list[dict]:
    df = apply_scenario(generate_mock_plant_data(), scenario)
    return detect_anomalies(df)


ALL_SCENARIOS = [
    "pic_four_2", "perte_partielle_cat", "surcharge_15kv",
    "fuite_air_7b", "defaut_c715", "desequilibre_c7",
    "saturation_vsd_3b", "mauvaise_regulation_3b",
    "defaut_refroidissement", "risque_legionelle",
    "baisse_bassin_b1", "forte_dependance_eau_brute",
    "multi_crise",
]


# ---------------------------------------------------------------------------
# 1. Aucune anomalie
# ---------------------------------------------------------------------------

class TestNoAnomalies:

    def test_global_score_is_zero(self):
        assert build_scoring_summary([])["global_score"] == 0.0

    def test_status_is_normal(self):
        assert build_scoring_summary([])["status"] == "NORMAL"

    def test_all_domain_scores_are_zero(self):
        for v in build_scoring_summary([])["domain_scores"].values():
            assert v == 0.0

    def test_scored_anomalies_is_empty(self):
        s = build_scoring_summary([])
        assert s["scored_anomalies"] == []
        assert s["n_anomalies"] == 0

    def test_nominal_pipeline_gives_zero(self):
        """generate_mock_plant_data sans scénario → aucune anomalie → score 0."""
        anomalies = detect_anomalies(generate_mock_plant_data())
        assert build_scoring_summary(anomalies)["global_score"] == 0.0


# ---------------------------------------------------------------------------
# 2. Anomalie low
# ---------------------------------------------------------------------------

class TestLowAnomalyScoring:
    """
    Anomalie low : base 20, confidence faible, durée 0 min (facteur 0.8).
    Calcul attendu : 20 × 0.65 × 1.10 × 0.95 × 0.90 × 0.8 ≈ 9.8 → NORMAL.
    """

    @pytest.fixture
    def low_anom(self):
        # même timestamp → durée 0 min → duration_factor 0.8
        return _mock(
            severity="low", domain="air",
            asset="C311/C312 + VSD", anomaly_type="bad_regulation",
            confidence=0.65,
            ts_start="2024-01-01 08:00:00", ts_end="2024-01-01 08:00:00",
        )

    def test_score_below_30(self, low_anom):
        assert score_anomaly(low_anom)["final_score"] < 30.0

    def test_status_normal_or_vigilance(self, low_anom):
        assert build_scoring_summary([low_anom])["status"] in ("NORMAL", "VIGILANCE")

    def test_base_score_matches_severity_weight(self, low_anom):
        assert score_anomaly(low_anom)["base_score"] == 20


# ---------------------------------------------------------------------------
# 3. Anomalie high air 7 bars (pipeline réel)
# ---------------------------------------------------------------------------

class TestHighAirScoring:

    @pytest.fixture(scope="class")
    def fuite_anomalies(self):
        return _detect("fuite_air_7b")

    def test_at_least_one_anomaly_detected(self, fuite_anomalies):
        assert len(fuite_anomalies) >= 1

    def test_air_domain_score_above_45(self, fuite_anomalies):
        scores = compute_domain_scores(fuite_anomalies)
        assert scores["air_score"] >= 45.0

    def test_status_alerte_or_critique(self, fuite_anomalies):
        assert build_scoring_summary(fuite_anomalies)["status"] in ("ALERTE", "CRITIQUE")

    def test_scored_anomaly_has_all_fields(self, fuite_anomalies):
        required = {
            "anomaly_id", "domain", "asset", "severity",
            "base_score", "confidence_factor", "domain_factor",
            "asset_factor", "type_factor", "duration_factor",
            "final_score", "explanation",
        }
        for a in fuite_anomalies:
            s = score_anomaly(a)
            assert required.issubset(s.keys()), f"champs manquants : {required - s.keys()}"


# ---------------------------------------------------------------------------
# 4. Anomalie critical eau recyclée
# ---------------------------------------------------------------------------

class TestCriticalWaterScoring:
    """
    cooling_fault critical, Circuit eau recyclée, 8 h de durée.
    Calcul attendu : 90 × 0.96 × 1.20 × 1.30 × 1.30 × 1.2 ≈ 249 → clampé 100 → CRITIQUE.
    """

    @pytest.fixture
    def critical_water(self):
        return _mock(
            severity="critical", domain="water",
            asset="Circuit eau recyclée / pompe EF1",
            anomaly_type="cooling_fault", confidence=0.96,
            ts_start="2024-01-01 09:00:00", ts_end="2024-01-01 17:00:00",
        )

    def test_final_score_above_75(self, critical_water):
        assert score_anomaly(critical_water)["final_score"] >= 75.0

    def test_status_is_critique(self, critical_water):
        assert build_scoring_summary([critical_water])["status"] == "CRITIQUE"

    def test_has_critical_flag_true(self, critical_water):
        assert build_scoring_summary([critical_water])["has_critical"] is True

    def test_asset_factor_circuit_eau(self, critical_water):
        """Recherche souple : 'Circuit eau recyclée' doit matcher → facteur 1.30."""
        assert score_anomaly(critical_water)["asset_factor"] == 1.30

    def test_domain_factor_water(self, critical_water):
        assert score_anomaly(critical_water)["domain_factor"] == 1.20


# ---------------------------------------------------------------------------
# 5. Multi-crise (pipeline réel)
# ---------------------------------------------------------------------------

class TestMultiCriseScoring:

    @pytest.fixture(scope="class")
    def multi_anomalies(self):
        return _detect("multi_crise")

    def test_at_least_3_anomalies(self, multi_anomalies):
        assert len(multi_anomalies) >= 3

    def test_global_score_above_75(self, multi_anomalies):
        assert compute_global_plant_score(multi_anomalies) >= 75.0

    def test_status_is_critique(self, multi_anomalies):
        assert build_scoring_summary(multi_anomalies)["status"] == "CRITIQUE"

    def test_at_least_two_domains_scored(self, multi_anomalies):
        scores = compute_domain_scores(multi_anomalies)
        non_zero = [k for k, v in scores.items() if v > 0.0]
        assert len(non_zero) >= 2, f"domaines scorés : {non_zero}"

    def test_three_domains_all_scored(self, multi_anomalies):
        scores = compute_domain_scores(multi_anomalies)
        assert scores["electricity_score"] > 0.0
        assert scores["air_score"]         > 0.0
        assert scores["water_score"]       > 0.0

    def test_n_anomalies_in_summary(self, multi_anomalies):
        s = build_scoring_summary(multi_anomalies)
        assert s["n_anomalies"] == len(multi_anomalies)


# ---------------------------------------------------------------------------
# 6. Bornage — aucun score < 0 ou > 100
# ---------------------------------------------------------------------------

class TestScoreBounds:

    def test_all_scenarios_scores_in_range(self):
        """Pour les 13 scénarios : global, domaines et anomalies individuelles ∈ [0, 100]."""
        df_base = generate_mock_plant_data()
        for name in ALL_SCENARIOS:
            anomalies = detect_anomalies(apply_scenario(df_base.copy(), name))
            summary   = build_scoring_summary(anomalies)

            assert 0.0 <= summary["global_score"] <= 100.0, \
                f"{name} → global_score={summary['global_score']}"

            for scored in summary["scored_anomalies"]:
                assert 0.0 <= scored["final_score"] <= 100.0, \
                    f"{name} → {scored['anomaly_id']} final_score={scored['final_score']}"

            for key, val in summary["domain_scores"].items():
                assert 0.0 <= val <= 100.0, f"{name} → {key}={val}"

    def test_nominal_data_global_score_zero(self):
        """Données nominales → 0 anomalie → global_score == 0."""
        anomalies = detect_anomalies(generate_mock_plant_data())
        assert build_scoring_summary(anomalies)["global_score"] == 0.0

    def test_mock_critical_score_clamped_to_100(self):
        """Une anomalie à multiplicateurs maximum ne dépasse pas 100."""
        a = _mock(
            severity="critical", domain="water",
            asset="Circuit eau recyclée", anomaly_type="cooling_fault",
            confidence=0.99,
            ts_start="2024-01-01 00:00:00", ts_end="2024-01-01 23:59:00",
        )
        assert score_anomaly(a)["final_score"] == 100.0


# ---------------------------------------------------------------------------
# 7. Explication — non vide et cohérente
# ---------------------------------------------------------------------------

class TestExplanation:

    def test_all_scenarios_have_nonempty_explanation(self):
        df_base = generate_mock_plant_data()
        for name in ALL_SCENARIOS:
            for a in detect_anomalies(apply_scenario(df_base.copy(), name)):
                scored = score_anomaly(a)
                assert isinstance(scored["explanation"], str), \
                    f"{name} → explanation n'est pas une str"
                assert len(scored["explanation"]) > 0, \
                    f"{name} → explanation vide"

    def test_explanation_mentions_severity(self):
        """L'explication doit toujours contenir le niveau de sévérité."""
        for sev in ("low", "medium", "high", "critical"):
            a = _mock(sev, "electricity", "CAT / Poste 63 kV", "cat_fault")
            assert sev in score_anomaly(a)["explanation"], \
                f"sévérité '{sev}' absente de l'explanation"

    def test_critique_score_says_critique(self):
        a = _mock(
            "critical", "water", "Circuit eau recyclée", "cooling_fault",
            confidence=0.96,
            ts_start="2024-01-01 08:00:00", ts_end="2024-01-01 16:00:00",
        )
        s = score_anomaly(a)
        assert s["final_score"] >= 75.0
        assert "critique" in s["explanation"]

    def test_low_score_says_faible_or_modere(self):
        a = _mock(
            "low", "air", "C311/C312 + VSD", "bad_regulation",
            confidence=0.65,
            ts_start="2024-01-01 08:00:00", ts_end="2024-01-01 08:00:00",
        )
        s = score_anomaly(a)
        assert s["final_score"] < 20.0
        assert "faible" in s["explanation"]


# ---------------------------------------------------------------------------
# get_plant_status — couverture des seuils
# ---------------------------------------------------------------------------

class TestGetPlantStatus:

    @pytest.mark.parametrize("score,expected", [
        (0.0,   "NORMAL"),
        (10.0,  "NORMAL"),
        (19.9,  "NORMAL"),
        (20.0,  "VIGILANCE"),
        (35.0,  "VIGILANCE"),
        (44.9,  "VIGILANCE"),
        (45.0,  "ALERTE"),
        (60.0,  "ALERTE"),
        (74.9,  "ALERTE"),
        (75.0,  "CRITIQUE"),
        (90.0,  "CRITIQUE"),
        (100.0, "CRITIQUE"),
    ])
    def test_thresholds(self, score, expected):
        assert get_plant_status(score) == expected


# ---------------------------------------------------------------------------
# compute_domain_scores — logique de bonus
# ---------------------------------------------------------------------------

class TestComputeDomainScores:

    def test_single_anomaly_no_bonus(self):
        """1 anomalie dans un domaine → score domaine == score individuel."""
        a = _mock("high", "air", "Réseau air 7 bars", "air_leak", confidence=0.85)
        individual = score_anomaly(a)["final_score"]
        assert compute_domain_scores([a])["air_score"] == individual

    def test_two_anomalies_same_domain_bonus_applied(self):
        """2 anomalies electricity → score domaine > max individuel (bonus +5)."""
        a1 = _mock("medium", "electricity", "CAT / Poste 63 kV", "cat_fault",     confidence=0.80)
        a2 = _mock("medium", "electricity", "Poste 15 kV force motrice", "overload_15kv", confidence=0.75)
        s1 = score_anomaly(a1)["final_score"]
        s2 = score_anomaly(a2)["final_score"]
        domain_score = compute_domain_scores([a1, a2])["electricity_score"]
        # Le bonus doit être appliqué, SAUF si on atteint déjà 100
        if max(s1, s2) < 95.0:
            assert domain_score > max(s1, s2)
        assert domain_score <= 100.0

    def test_unknown_domain_ignored(self):
        """Un domaine inconnu ne plante pas la fonction et n'affecte pas les 3 clés standard."""
        a = _mock("high", "other", "Equipement X", "unknown_type")
        result = compute_domain_scores([a])
        assert set(result.keys()) == {"electricity_score", "air_score", "water_score"}

    def test_all_three_domains_zero_when_empty(self):
        result = compute_domain_scores([])
        assert result == {"electricity_score": 0.0, "air_score": 0.0, "water_score": 0.0}


# ---------------------------------------------------------------------------
# score_anomaly — facteurs individuels
# ---------------------------------------------------------------------------

class TestScoreAnomalyFactors:

    def test_higher_severity_gives_higher_score(self):
        base = dict(domain="electricity", asset="CAT / Poste 63 kV",
                    anomaly_type="cat_fault", confidence=0.80,
                    ts_start="2024-01-01 08:00:00", ts_end="2024-01-01 12:00:00")
        s_low  = score_anomaly({**base, "id": "L", "severity": "low"})["final_score"]
        s_med  = score_anomaly({**base, "id": "M", "severity": "medium"})["final_score"]
        s_high = score_anomaly({**base, "id": "H", "severity": "high"})["final_score"]
        s_crit = score_anomaly({**base, "id": "C", "severity": "critical"})["final_score"]
        assert s_low <= s_med <= s_high <= s_crit

    def test_duration_factor_short_gives_lower_score(self):
        base = dict(id="X", severity="high", domain="air",
                    asset="Réseau air 7 bars", anomaly_type="air_leak",
                    confidence=0.85)
        s_short = score_anomaly({**base,
            "timestamp_start": "2024-01-01 08:00:00",
            "timestamp_end":   "2024-01-01 08:05:00"})["final_score"]  # < 15 min → 0.8
        s_long  = score_anomaly({**base,
            "timestamp_start": "2024-01-01 08:00:00",
            "timestamp_end":   "2024-01-01 20:00:00"})["final_score"]  # > 3 h → 1.2
        assert s_short <= s_long

    def test_asset_factor_recherche_souple(self):
        """La recherche souple d'asset doit retrouver 'Circuit eau recyclée' → 1.30."""
        a = _mock("high", "water", "Circuit eau recyclée / pompe EF1", "cooling_fault")
        assert score_anomaly(a)["asset_factor"] == 1.30

    def test_unknown_asset_gives_factor_1(self):
        a = _mock("high", "electricity", "Équipement inconnu XYZ", "furnace_overload")
        assert score_anomaly(a)["asset_factor"] == 1.0

    def test_unknown_anomaly_type_gives_factor_1(self):
        a = _mock("high", "electricity", "Four 2 / 63 kV", "type_inconnu")
        assert score_anomaly(a)["type_factor"] == 1.0
