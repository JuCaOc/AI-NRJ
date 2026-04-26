"""
Scoring de criticité des anomalies industrielles.

Transforme les anomalies détectées en scores 0-100 compréhensibles par
les opérateurs, la maintenance, l'exploitation et la direction.

Réponse à la question : « À quel point la situation est-elle grave maintenant ? »

Tout est explicable, stable, sans machine learning.
Les tables de pondération sont modifiables sans toucher la logique.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


# ---------------------------------------------------------------------------
# Tables de pondération — modifiables pour calibration sur une vraie usine
# ---------------------------------------------------------------------------

SEVERITY_WEIGHTS: dict[str, int] = {
    "low":      20,
    "medium":   40,
    "high":     70,
    "critical": 90,
}

DOMAIN_WEIGHTS: dict[str, float] = {
    "electricity": 1.15,   # impact global usine
    "air":         1.10,   # instrumentation / procédé
    "water":       1.20,   # refroidissement / sécurité
}

ASSET_CRITICALITY: dict[str, float] = {
    "Four 2":                  1.20,
    "CAT":                     1.15,
    "Poste 15 kV":             1.20,
    "Réseau air 7 bars":       1.25,
    "C715":                    1.10,
    "C713-C714":               1.00,
    "C321/C322/C323":          1.10,
    "C311/C312":               0.95,
    "Circuit eau recyclée":    1.30,
    "Pompe EF1":               1.25,
    "Tours aéroréfrigérantes": 1.20,
    "Bassin B1":               1.15,
    "Eau brute":               1.05,
}

ANOMALY_TYPE_WEIGHTS: dict[str, float] = {
    "furnace_overload":          1.15,
    "cat_fault":                 1.10,
    "overload_15kv":             1.15,
    "air_leak":                  1.10,
    "compressor_fault":          1.05,
    "compressor_imbalance":      0.95,
    "vsd_saturation":            1.10,
    "bad_regulation":            0.90,
    "cooling_fault":             1.30,
    "legionella_risk":           1.25,
    "low_basin":                 1.15,
    "raw_water_overconsumption": 1.00,
    "multi_system_fault":        1.35,
}


# ---------------------------------------------------------------------------
# Dataclasses — conservées pour compatibilité avec recommendations.py
# et ai_assistant.py qui les importent comme types d'annotation
# ---------------------------------------------------------------------------

@dataclass
class CriticalityScore:
    anomaly_id: str
    final_score: float
    priority: str
    rationale: str


@dataclass
class SystemHealthScore:
    system: str
    health_pct: float
    status_label: str


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------

def _get_asset_factor(asset: str) -> float:
    """Recherche souple : retourne le facteur du premier mot-clé trouvé dans l'asset."""
    asset_lower = asset.lower()
    for key, factor in ASSET_CRITICALITY.items():
        if key.lower() in asset_lower:
            return factor
    return 1.0


def _get_duration_factor(ts_start: str, ts_end: str) -> float:
    """
    Facteur durée à partir de la différence timestamp_end − timestamp_start.

    < 15 min → 0.8 | 15–60 min → 1.0 | 1–3 h → 1.1 | > 3 h → 1.2
    """
    try:
        minutes = max(
            0.0,
            (pd.Timestamp(ts_end) - pd.Timestamp(ts_start)).total_seconds() / 60.0,
        )
    except Exception:
        return 1.0
    if minutes < 15:
        return 0.8
    if minutes < 60:
        return 1.0
    if minutes < 180:
        return 1.1
    return 1.2


def _build_explanation(
    severity: str,
    asset: str,
    domain: str,
    confidence: float,
    final_score: float,
) -> str:
    level = (
        "critique" if final_score >= 75
        else "élevé" if final_score >= 45
        else "modéré" if final_score >= 20
        else "faible"
    )
    conf_str = (
        "forte confiance" if confidence >= 0.85
        else "confiance modérée" if confidence >= 0.70
        else "confiance faible"
    )
    return f"Score {level} : anomalie {severity} sur {asset} ({domain}) avec {conf_str}."


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def score_anomaly(anomaly: dict[str, Any]) -> dict[str, Any]:
    """
    Calcule le score de criticité d'une anomalie.

    Formule :
        raw = base × confidence × domain × asset × type × durée
        final = clamp(raw, 0, 100)

    Retourne un dict avec tous les facteurs explicatifs + final_score + explanation.
    """
    severity          = anomaly.get("severity", "low")
    domain            = anomaly.get("domain", "electricity")
    asset             = anomaly.get("asset", "")
    anom_type         = anomaly.get("anomaly_type", "")
    confidence        = float(anomaly.get("confidence_score", 0.75))

    base_score        = float(SEVERITY_WEIGHTS.get(severity, 20))
    domain_factor     = DOMAIN_WEIGHTS.get(domain, 1.0)
    asset_factor      = _get_asset_factor(asset)
    type_factor       = ANOMALY_TYPE_WEIGHTS.get(anom_type, 1.0)
    confidence_factor = confidence
    duration_factor   = _get_duration_factor(
        str(anomaly.get("timestamp_start", "")),
        str(anomaly.get("timestamp_end", "")),
    )

    raw         = base_score * confidence_factor * domain_factor * asset_factor * type_factor * duration_factor
    final_score = round(min(100.0, max(0.0, raw)), 1)
    explanation = _build_explanation(severity, asset, domain, confidence, final_score)

    return {
        "anomaly_id":        anomaly.get("id", ""),
        "domain":            domain,
        "asset":             asset,
        "severity":          severity,
        "base_score":        int(base_score),
        "confidence_factor": round(confidence_factor, 3),
        "domain_factor":     domain_factor,
        "asset_factor":      asset_factor,
        "type_factor":       type_factor,
        "duration_factor":   duration_factor,
        "final_score":       final_score,
        "explanation":       explanation,
    }


def compute_domain_scores(anomalies: list[dict[str, Any]]) -> dict[str, float]:
    """
    Calcule les scores par domaine.

    Formule par domaine :
        score = max_score_du_domaine + 5 × (n_anomalies − 1)
        borné à 100.

    Retourne {"electricity_score": …, "air_score": …, "water_score": …}.
    """
    by_domain: dict[str, list[float]] = {}
    for a in anomalies:
        d = a.get("domain", "electricity")
        s = score_anomaly(a)["final_score"]
        by_domain.setdefault(d, []).append(s)

    result    = {"electricity_score": 0.0, "air_score": 0.0, "water_score": 0.0}
    domain_key = {"electricity": "electricity_score", "air": "air_score", "water": "water_score"}

    for domain, scores in by_domain.items():
        max_s  = max(scores)
        bonus  = 5.0 * (len(scores) - 1)
        key    = domain_key.get(domain)
        if key:
            result[key] = round(min(100.0, max_s + bonus), 1)

    return result


def compute_global_plant_score(anomalies: list[dict[str, Any]]) -> float:
    """
    Score global usine 0-100.

    Formule :
        global = 0.6 × max_domain + 0.4 × avg_domain + multi_domain_bonus
        multi_domain_bonus : 0 (1 domaine) | 5 (2 domaines) | 10 (3 domaines)
        borné à 100.
    """
    if not anomalies:
        return 0.0

    domain_scores = compute_domain_scores(anomalies)
    non_zero      = [s for s in domain_scores.values() if s > 0.0]

    if not non_zero:
        return 0.0

    max_d     = max(non_zero)
    avg_d     = sum(non_zero) / len(non_zero)
    n_domains = len(non_zero)
    bonus     = {1: 0.0, 2: 5.0}.get(n_domains, 10.0)

    return round(min(100.0, 0.6 * max_d + 0.4 * avg_d + bonus), 1)


def get_plant_status(global_score: float) -> str:
    """
    Traduit le score global en statut lisible.

     0– 19 : NORMAL
    20– 44 : VIGILANCE
    45– 74 : ALERTE
    75–100 : CRITIQUE
    """
    if global_score >= 75:
        return "CRITIQUE"
    if global_score >= 45:
        return "ALERTE"
    if global_score >= 20:
        return "VIGILANCE"
    return "NORMAL"


def build_scoring_summary(anomalies: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Construit le résumé complet de scoring exploitable dans Streamlit.

    Cas sans anomalie :
        global_score=0, status=NORMAL, domain_scores=0, scored_anomalies=[]

    Retourne :
        global_score   float
        status         str   (NORMAL | VIGILANCE | ALERTE | CRITIQUE)
        domain_scores  dict  (electricity_score, air_score, water_score)
        scored_anomalies list[dict]  (un dict score_anomaly par anomalie)
        n_anomalies    int
        has_critical   bool
    """
    if not anomalies:
        return {
            "global_score":     0.0,
            "status":           "NORMAL",
            "domain_scores":    {"electricity_score": 0.0, "air_score": 0.0, "water_score": 0.0},
            "scored_anomalies": [],
            "n_anomalies":      0,
            "has_critical":     False,
        }

    scored       = [score_anomaly(a) for a in anomalies]
    domain_scores = compute_domain_scores(anomalies)
    global_score = compute_global_plant_score(anomalies)

    return {
        "global_score":     global_score,
        "status":           get_plant_status(global_score),
        "domain_scores":    domain_scores,
        "scored_anomalies": scored,
        "n_anomalies":      len(anomalies),
        "has_critical":     any(a.get("severity") == "critical" for a in anomalies),
    }
