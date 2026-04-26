"""Tests pour modules/ai_assistant.py — chatbot industriel rule-based."""

from __future__ import annotations

import pytest
import pandas as pd

from modules.ai_assistant import (
    classify_question_intent,
    answer_user_question,
    build_context_summary,
    generate_rule_based_answer,
    QUICK_PROMPTS,
)
from modules.data_generator import generate_mock_plant_data
from modules.scenarios import apply_scenario
from modules.detection import detect_anomalies
from modules.scoring import build_scoring_summary
from modules.recommendations import generate_recommendations
from modules.business_value import compute_total_business_impact


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def nominal_df() -> pd.DataFrame:
    return generate_mock_plant_data()


@pytest.fixture(scope="module")
def fuite_df(nominal_df: pd.DataFrame) -> pd.DataFrame:
    return apply_scenario(nominal_df.copy(), "fuite_air_7b")


@pytest.fixture(scope="module")
def defaut_c715_df(nominal_df: pd.DataFrame) -> pd.DataFrame:
    return apply_scenario(nominal_df.copy(), "defaut_c715")


@pytest.fixture(scope="module")
def multi_crise_df(nominal_df: pd.DataFrame) -> pd.DataFrame:
    return apply_scenario(nominal_df.copy(), "multi_crise")


def _pipeline(df: pd.DataFrame) -> tuple:
    anomalies = detect_anomalies(df)
    scoring   = build_scoring_summary(anomalies)
    recs      = generate_recommendations(anomalies, scoring_summary=scoring)
    biz       = compute_total_business_impact(anomalies, recs)
    return anomalies, scoring, recs, biz


# ---------------------------------------------------------------------------
# 1. classify_question_intent
# ---------------------------------------------------------------------------

class TestClassifyIntent:
    def test_global_status(self):
        assert classify_question_intent("Quel est l'état global ?") == "global_status"

    def test_global_status_situation(self):
        assert classify_question_intent("Quelle est la situation de l'usine ?") == "global_status"

    def test_air_7b_pression(self):
        assert classify_question_intent("Pourquoi la pression 7 bars chute ?") == "air_7b"

    def test_air_7b_compresseur(self):
        assert classify_question_intent("Quel compresseur C715 pose problème ?") == "air_7b"

    def test_air_3b_vsd(self):
        assert classify_question_intent("VSD air 3 bars saturé ?") == "air_3b"

    def test_air_3b_regulation(self):
        assert classify_question_intent("Mauvaise régulation air 3 bars") == "air_3b"

    def test_electricity_four(self):
        assert classify_question_intent("Problème sur le four 2 ?") == "electricity"

    def test_electricity_cat(self):
        assert classify_question_intent("Génération CAT insuffisante ?") == "electricity"

    def test_water_legionelle(self):
        assert classify_question_intent("Risques légionelle eau recyclée ?") == "water"

    def test_water_bassin(self):
        assert classify_question_intent("Niveau bassin B1 critique ?") == "water"

    def test_recommendations(self):
        assert classify_question_intent("Que recommande l'IA ?") == "recommendations"

    def test_recommendations_action(self):
        assert classify_question_intent("Que faire en priorité ?") == "recommendations"

    def test_business_impact_xpf(self):
        assert classify_question_intent("Quel coût en XPF ?") == "business_impact"

    def test_business_impact_perte(self):
        assert classify_question_intent("Combien coûte le problème ?") == "business_impact"

    def test_scada_vs_ai(self):
        assert classify_question_intent("Différence avec SCADA ?") == "scada_vs_ai"

    def test_scada_vs_ai_alarme(self):
        assert classify_question_intent("Comment fonctionne un seuil SCADA ?") == "scada_vs_ai"

    def test_safety(self):
        assert classify_question_intent("Quelles sont les règles de sécurité ?") == "safety"

    def test_most_critical(self):
        assert classify_question_intent("Quelle est l'anomalie la plus critique ?") == "most_critical_anomaly"

    def test_unknown(self):
        assert classify_question_intent("blabla incompréhensible xyz 999") == "unknown"

    def test_unknown_random(self):
        assert classify_question_intent("qwerty asdfgh zxcvbn") == "unknown"


# ---------------------------------------------------------------------------
# 2. answer_user_question — robustesse générale
# ---------------------------------------------------------------------------

class TestAnswerUserQuestion:
    def test_returns_nonempty_string_nominal(self, nominal_df):
        anomalies, scoring, recs, biz = _pipeline(nominal_df)
        result = answer_user_question(
            "Quel est l'état global ?",
            nominal_df, anomalies, recs, scoring, biz,
        )
        assert isinstance(result, str)
        assert len(result) > 20

    def test_no_crash_empty_context(self, nominal_df):
        result = answer_user_question(
            "Quel est l'état global ?",
            nominal_df, [], [], {}, {},
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_no_crash_none_df(self):
        result = answer_user_question(
            "État usine ?", None, [], [], {}, {},
        )
        assert isinstance(result, str)

    def test_safety_response_mentions_simulation(self, nominal_df):
        anomalies, scoring, recs, biz = _pipeline(nominal_df)
        result = answer_user_question(
            "Quelles sont les règles de sécurité ?",
            nominal_df, anomalies, recs, scoring, biz,
        )
        lower = result.lower()
        assert "simulation" in lower or "humaine" in lower or "validation" in lower

    def test_any_action_answer_mentions_validation(self, nominal_df):
        anomalies, scoring, recs, biz = _pipeline(nominal_df)
        result = answer_user_question(
            "Quelles sont les règles de sécurité ?",
            nominal_df, anomalies, recs, scoring, biz,
        )
        assert "validation" in result.lower() or "humaine" in result.lower()

    def test_unknown_proposes_examples(self, nominal_df):
        anomalies, scoring, recs, biz = _pipeline(nominal_df)
        result = answer_user_question(
            "blabla incompréhensible xyz 999",
            nominal_df, anomalies, recs, scoring, biz,
        )
        lower = result.lower()
        assert "question" in lower or "répondre" in lower or "état" in lower

    def test_all_quick_prompts_return_nonempty(self, nominal_df):
        anomalies, scoring, recs, biz = _pipeline(nominal_df)
        for qp in QUICK_PROMPTS:
            result = answer_user_question(
                qp["prompt"], nominal_df, anomalies, recs, scoring, biz,
            )
            assert isinstance(result, str) and len(result) > 10, (
                f"Réponse vide pour le prompt : {qp['prompt']}"
            )


# ---------------------------------------------------------------------------
# 3. Scénario nominal — pas d'anomalie
# ---------------------------------------------------------------------------

class TestNominal:
    def test_global_status_is_normal(self, nominal_df):
        anomalies, scoring, recs, biz = _pipeline(nominal_df)
        result = answer_user_question(
            "Quel est l'état global ?", nominal_df, anomalies, recs, scoring, biz,
        )
        lower = result.lower()
        assert "normal" in lower or "nominal" in lower or "aucune anomalie" in lower

    def test_business_impact_zero(self, nominal_df):
        anomalies, scoring, recs, biz = _pipeline(nominal_df)
        result = answer_user_question(
            "Quel est l'impact financier ?", nominal_df, anomalies, recs, scoring, biz,
        )
        lower = result.lower()
        assert "nominal" in lower or "aucune perte" in lower or "normal" in lower


# ---------------------------------------------------------------------------
# 4. Scénario fuite_air_7b
# ---------------------------------------------------------------------------

class TestFuiteAir7b:
    def test_air_response_mentions_fuite_or_pressure(self, fuite_df):
        anomalies, scoring, recs, biz = _pipeline(fuite_df)
        result = answer_user_question(
            "Pourquoi la pression air 7 bars chute ?",
            fuite_df, anomalies, recs, scoring, biz,
        )
        lower = result.lower()
        assert "fuite" in lower or "pression" in lower or "7 bar" in lower

    def test_detects_at_least_one_anomaly(self, fuite_df):
        anomalies, _, _, _ = _pipeline(fuite_df)
        assert len(anomalies) >= 1

    def test_anomaly_domain_is_air(self, fuite_df):
        anomalies, scoring, recs, biz = _pipeline(fuite_df)
        air_anom = [a for a in anomalies if a.get("domain") == "air"]
        result = answer_user_question(
            "Problème sur le réseau air 7 bars ?",
            fuite_df, anomalies, recs, scoring, biz,
        )
        if air_anom:
            assert "air" in result.lower()


# ---------------------------------------------------------------------------
# 5. Scénario defaut_c715
# ---------------------------------------------------------------------------

class TestDefautC715:
    def test_response_mentions_c715(self, defaut_c715_df):
        anomalies, scoring, recs, biz = _pipeline(defaut_c715_df)
        result = answer_user_question(
            "Quel compresseur pose problème ?",
            defaut_c715_df, anomalies, recs, scoring, biz,
        )
        assert "c715" in result.lower() or "C715" in result

    def test_air_domain_anomaly_present(self, defaut_c715_df):
        anomalies, _, _, _ = _pipeline(defaut_c715_df)
        air_anom = [a for a in anomalies if a.get("domain") == "air"]
        assert len(air_anom) >= 1


# ---------------------------------------------------------------------------
# 6. Scénario multi_crise
# ---------------------------------------------------------------------------

class TestMultiCrise:
    def test_global_status_not_normal(self, multi_crise_df):
        anomalies, scoring, recs, biz = _pipeline(multi_crise_df)
        result = answer_user_question(
            "Quel est l'état global de l'usine ?",
            multi_crise_df, anomalies, recs, scoring, biz,
        )
        lower = result.lower()
        # Ne doit PAS dire "normal" comme statut dominant
        # Doit mentionner plusieurs anomalies ou un statut dégradé
        assert "anomalie" in lower or "critique" in lower or "élevée" in lower

    def test_multiple_anomalies_detected(self, multi_crise_df):
        anomalies, _, _, _ = _pipeline(multi_crise_df)
        assert len(anomalies) >= 3

    def test_three_domains_covered(self, multi_crise_df):
        anomalies, _, _, _ = _pipeline(multi_crise_df)
        domains = {a.get("domain") for a in anomalies}
        assert len(domains) >= 3

    def test_business_impact_significant(self, multi_crise_df):
        anomalies, scoring, recs, biz = _pipeline(multi_crise_df)
        result = answer_user_question(
            "Quel est le coût total en XPF ?",
            multi_crise_df, anomalies, recs, scoring, biz,
        )
        assert "xpf" in result.lower()
        assert biz.get("total_loss_xpf", 0) > 500_000

    def test_recommendations_returns_multiple(self, multi_crise_df):
        anomalies, scoring, recs, biz = _pipeline(multi_crise_df)
        result = answer_user_question(
            "Que recommande l'IA ?",
            multi_crise_df, anomalies, recs, scoring, biz,
        )
        assert len(recs) >= 3
        assert "prioritaire" in result.lower() or "recommandation" in result.lower()

    def test_scada_vs_ai_mentions_example(self, multi_crise_df):
        anomalies, scoring, recs, biz = _pipeline(multi_crise_df)
        result = answer_user_question(
            "Quelle différence avec le SCADA ?",
            multi_crise_df, anomalies, recs, scoring, biz,
        )
        lower = result.lower()
        assert "scada" in lower and ("ia" in lower or "l'ia" in lower)


# ---------------------------------------------------------------------------
# 7. build_context_summary
# ---------------------------------------------------------------------------

class TestBuildContextSummary:
    def test_returns_dict(self, nominal_df):
        anomalies, scoring, recs, biz = _pipeline(nominal_df)
        ctx = build_context_summary(nominal_df, anomalies, recs, scoring, biz)
        assert isinstance(ctx, dict)

    def test_required_keys_present(self, nominal_df):
        anomalies, scoring, recs, biz = _pipeline(nominal_df)
        ctx = build_context_summary(nominal_df, anomalies, recs, scoring, biz)
        required = [
            "global_score", "global_status", "n_anomalies",
            "top_anomaly", "sorted_recommendations", "total_loss_xpf",
            "electricity_anomalies", "air_anomalies", "water_anomalies",
        ]
        for key in required:
            assert key in ctx, f"Clé manquante dans le contexte : {key}"

    def test_empty_inputs_no_crash(self, nominal_df):
        ctx = build_context_summary(nominal_df, [], [], {}, {})
        assert ctx["n_anomalies"] == 0
        assert ctx["total_loss_xpf"] == 0.0

    def test_none_df_no_crash(self):
        ctx = build_context_summary(None, [], [], {}, {})
        assert ctx["air_7b_pressure"] is None


# ---------------------------------------------------------------------------
# 8. generate_rule_based_answer
# ---------------------------------------------------------------------------

class TestGenerateRuleBasedAnswer:
    def test_all_intents_return_string(self, nominal_df):
        anomalies, scoring, recs, biz = _pipeline(nominal_df)
        ctx = build_context_summary(nominal_df, anomalies, recs, scoring, biz)
        intents = [
            "global_status", "most_critical_anomaly", "electricity",
            "air_7b", "air_3b", "water", "recommendations",
            "business_impact", "scada_vs_ai", "safety", "unknown",
        ]
        for intent in intents:
            result = generate_rule_based_answer(intent, "test", ctx)
            assert isinstance(result, str) and len(result) > 5, (
                f"Réponse vide pour intent : {intent}"
            )

    def test_invalid_intent_falls_back_to_unknown(self, nominal_df):
        anomalies, scoring, recs, biz = _pipeline(nominal_df)
        ctx = build_context_summary(nominal_df, anomalies, recs, scoring, biz)
        result = generate_rule_based_answer("nonexistent_intent", "test", ctx)
        assert isinstance(result, str) and len(result) > 5


# ---------------------------------------------------------------------------
# 9. QUICK_PROMPTS structure
# ---------------------------------------------------------------------------

class TestQuickPrompts:
    def test_five_prompts(self):
        assert len(QUICK_PROMPTS) == 5

    def test_each_has_label_and_prompt(self):
        for qp in QUICK_PROMPTS:
            assert "label" in qp and len(qp["label"]) > 0
            assert "prompt" in qp and len(qp["prompt"]) > 0

    def test_prompts_are_classifiable(self):
        for qp in QUICK_PROMPTS:
            intent = classify_question_intent(qp["prompt"])
            assert intent != "unknown", (
                f"Le prompt '{qp['prompt']}' n'est pas classifiable (intent=unknown)"
            )
