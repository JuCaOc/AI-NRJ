"""
Simulateur d'impact des actions correctives.

Permet à l'opérateur d'explorer "what-if" : que se passerait-il
si l'action X était appliquée ? Retourne une projection des métriques
après correction, sans modifier les données originales.
"""

from dataclasses import dataclass
from typing import Optional
import pandas as pd

from modules.detection import Anomaly
from modules.recommendations import Recommendation
from modules.business_value import FinancialImpact, EconomicParameters, DEFAULT_PARAMS


# ---------------------------------------------------------------------------
# Modèle de résultat de simulation
# ---------------------------------------------------------------------------

@dataclass
class SimulationResult:
    """Résultat d'une simulation d'action corrective."""
    recommendation_id: str
    scenario_label: str
    before_metrics: dict[str, float]
    after_metrics: dict[str, float]
    delta_metrics: dict[str, float]
    resolved_anomaly_ids: list[str]
    residual_anomaly_ids: list[str]
    financial_impact: Optional[FinancialImpact]
    confidence: str                     # "low" | "medium" | "high"
    caveats: list[str]                  # limites de la simulation
    df_projected: Optional[pd.DataFrame] = None   # série temporelle projetée


# ---------------------------------------------------------------------------
# Fonctions de simulation
# ---------------------------------------------------------------------------

def simulate_action(
    recommendation: Recommendation,
    df_system: pd.DataFrame,
    anomalies: list[Anomaly],
    params: EconomicParameters = DEFAULT_PARAMS,
) -> SimulationResult:
    """
    Simule l'application d'une recommandation sur un DataFrame système.

    Retourne un nouveau DataFrame projeté (l'original n'est pas modifié)
    et les métriques avant/après.
    """
    pass


def simulate_multiple_actions(
    recommendations: list[Recommendation],
    data: dict[str, pd.DataFrame],
    anomalies: list[Anomaly],
    params: EconomicParameters = DEFAULT_PARAMS,
) -> list[SimulationResult]:
    """Simule plusieurs actions correctives en séquence et cumule les effets."""
    pass


def project_time_series(
    df: pd.DataFrame,
    recommendation: Recommendation,
    horizon_minutes: int = 60,
) -> pd.DataFrame:
    """
    Projette une série temporelle après application de la recommandation.
    Retourne un nouveau DataFrame sans modifier l'original.
    """
    pass


# ---------------------------------------------------------------------------
# Comparaison avant / après
# ---------------------------------------------------------------------------

def build_comparison_summary(result: SimulationResult) -> dict:
    """
    Construit un résumé tabulaire comparatif avant/après pour affichage UI.

    Retourne :
        rows: list[dict] avec colonnes metric, before, after, delta, unit, direction
    """
    pass
