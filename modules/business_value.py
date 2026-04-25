"""
Estimation de l'impact financier des anomalies et des actions correctives.

Monnaie : Franc Pacifique (XPF).
Les calculs sont basés sur des paramètres unitaires configurables
(coût kWh, coût arrêt production, coût maintenance).
"""

from dataclasses import dataclass
from typing import Optional
from modules.detection import Anomaly
from modules.recommendations import Recommendation


# ---------------------------------------------------------------------------
# Paramètres économiques
# ---------------------------------------------------------------------------

@dataclass
class EconomicParameters:
    """Paramètres unitaires utilisés pour les estimations financières (XPF)."""
    electricity_cost_xpf_kwh: float = 22.0           # tarif local Pacifique
    production_loss_xpf_per_h: float = 1_790_000.0
    compressed_air_waste_xpf_nm3: float = 4.2
    maintenance_call_xpf: float = 60_000.0
    unplanned_stop_penalty_xpf: float = 2_980_000.0
    water_cost_xpf_m3: float = 300.0


DEFAULT_PARAMS = EconomicParameters()


# ---------------------------------------------------------------------------
# Modèle d'impact financier
# ---------------------------------------------------------------------------

@dataclass
class FinancialImpact:
    """Estimation de l'impact financier d'une anomalie ou d'une action (XPF)."""
    anomaly_id: Optional[str]
    recommendation_id: Optional[str]
    cost_if_ignored_xpf: float       # coût si on ne fait rien (sur 24h)
    cost_to_fix_xpf: float           # coût de la correction
    savings_xpf: float               # économie nette
    payback_hours: Optional[float]   # délai de retour sur action
    confidence: str                  # "low" | "medium" | "high"
    breakdown: dict[str, float]      # détail des postes de coût


# ---------------------------------------------------------------------------
# Fonctions d'estimation
# ---------------------------------------------------------------------------

def estimate_anomaly_cost(
    anomaly: Anomaly,
    params: EconomicParameters = DEFAULT_PARAMS,
    duration_hours: float = 24.0,
) -> FinancialImpact:
    """Estime le coût d'une anomalie si elle n'est pas corrigée."""
    pass


def estimate_action_savings(
    recommendation: Recommendation,
    anomaly: Anomaly,
    params: EconomicParameters = DEFAULT_PARAMS,
) -> FinancialImpact:
    """Estime les économies générées par l'application d'une recommandation."""
    pass


def compute_total_financial_exposure(
    anomalies: list[Anomaly],
    params: EconomicParameters = DEFAULT_PARAMS,
) -> dict:
    """
    Calcule l'exposition financière totale de toutes les anomalies actives.

    Retourne :
        total_cost_xpf, worst_anomaly_id, breakdown_by_system,
        hourly_rate_xpf_h
    """
    pass


def estimate_compressed_air_waste(
    df_air: "pd.DataFrame",
    params: EconomicParameters = DEFAULT_PARAMS,
) -> dict:
    """
    Estime le gaspillage énergétique du réseau air comprimé.
    Inclut la comparaison optimal vs réel pour air 7 bars et 3 bars.
    """
    pass
