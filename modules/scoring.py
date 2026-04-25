"""
Calcul du score de criticité des anomalies et de l'état global des systèmes.

Le scoring combine sévérité, contexte opérationnel et risque de propagation
pour prioriser les actions de l'opérateur.
"""

from dataclasses import dataclass
from typing import Optional
from modules.detection import Anomaly


# ---------------------------------------------------------------------------
# Modèles de score
# ---------------------------------------------------------------------------

@dataclass
class CriticalityScore:
    """Score de criticité calculé pour une anomalie."""
    anomaly_id: str
    raw_severity: int            # 1 → 5, directement issu de l'anomalie
    context_multiplier: float    # facteur contextuel (heure, charge, ...)
    propagation_risk: float      # 0.0 → 1.0 (risque d'effet domino)
    final_score: float           # score final 0 → 100
    priority: str                # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    rationale: str               # explication courte du score


@dataclass
class SystemHealthScore:
    """Score de santé global d'un système utility."""
    system: str
    health_pct: float            # 0 → 100 (100 = nominal)
    active_anomalies: int
    worst_severity: int
    trend: str                   # "stable" | "degrading" | "recovering"
    status_label: str            # "OK" | "WARNING" | "ALERT" | "CRITICAL"


# ---------------------------------------------------------------------------
# Fonctions de scoring
# ---------------------------------------------------------------------------

def compute_criticality_score(
    anomaly: Anomaly,
    context: Optional[dict] = None,
) -> CriticalityScore:
    """
    Calcule le score de criticité d'une anomalie.

    Prend en compte :
        - Sévérité brute de l'anomalie
        - Heure (production / hors production)
        - Charge actuelle du système
        - Nombre d'anomalies simultanées (effet cumulatif)
        - Dépendances inter-systèmes (propagation)
    """
    pass


def compute_system_health(
    system: str,
    anomalies: list[Anomaly],
    df: "pd.DataFrame | None" = None,
) -> SystemHealthScore:
    """Calcule le score de santé global d'un système à partir de ses anomalies actives."""
    pass


def score_all_anomalies(
    anomalies: list[Anomaly],
    context: Optional[dict] = None,
) -> list[CriticalityScore]:
    """Calcule les scores de criticité pour toutes les anomalies, triés par score décroissant."""
    pass


def score_all_systems(
    data: dict[str, "pd.DataFrame"],
    anomalies: list[Anomaly],
) -> dict[str, SystemHealthScore]:
    """
    Retourne un dict system_name → SystemHealthScore pour tous les systèmes.

    Clés : electricity_63kv, electricity_15kv, electricity_55kv, electricity_400v,
            air_7bar, air_3bar, recycled_water, raw_water
    """
    pass


# ---------------------------------------------------------------------------
# Helpers de classification
# ---------------------------------------------------------------------------

def severity_to_priority(score: float) -> str:
    """Convertit un score numérique (0-100) en label de priorité."""
    pass


def get_global_alert_level(system_scores: dict[str, SystemHealthScore]) -> str:
    """Retourne le niveau d'alerte global de l'usine : "OK" | "WARNING" | "ALERT" | "CRITICAL"."""
    pass
