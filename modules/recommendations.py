"""
Génération de recommandations IA à partir des anomalies détectées.

Les recommandations sont rule-based, explicables et classées par priorité.
Elles ne constituent jamais des ordres directs — toute action
requiert validation humaine.
"""

from dataclasses import dataclass, field
from typing import Optional
from modules.detection import Anomaly
from modules.scoring import CriticalityScore


# ---------------------------------------------------------------------------
# Modèle de recommandation
# ---------------------------------------------------------------------------

@dataclass
class Recommendation:
    """Action recommandée en réponse à une ou plusieurs anomalies."""
    id: str
    title: str
    description: str
    action_type: str             # "inspect" | "adjust" | "switch" | "alert" | "stop"
    target_equipment: list[str]
    triggered_by: list[str]      # IDs des anomalies à l'origine
    priority: str                # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    urgency_minutes: int         # délai recommandé avant action
    estimated_benefit: str       # description textuelle du bénéfice
    estimated_risk_if_ignored: str
    steps: list[str] = field(default_factory=list)   # procédure pas à pas
    requires_human_validation: bool = True
    financial_impact_eur: Optional[float] = None


# ---------------------------------------------------------------------------
# Génération des recommandations
# ---------------------------------------------------------------------------

def recommend_for_anomaly(
    anomaly: Anomaly,
    score: Optional[CriticalityScore] = None,
) -> list[Recommendation]:
    """Génère les recommandations spécifiques à une anomalie."""
    pass


def recommend_all(
    anomalies: list[Anomaly],
    scores: Optional[list[CriticalityScore]] = None,
) -> list[Recommendation]:
    """
    Génère et déduplique les recommandations pour toutes les anomalies actives.
    Retourne la liste triée par priorité puis urgency_minutes.
    """
    pass


def deduplicate_recommendations(
    recommendations: list[Recommendation],
) -> list[Recommendation]:
    """Fusionne les recommandations redondantes visant les mêmes équipements."""
    pass


# ---------------------------------------------------------------------------
# Bibliothèque de recommandations prédéfinies
# ---------------------------------------------------------------------------

def _build_recommendation_library() -> dict[str, Recommendation]:
    """
    Construit la bibliothèque des recommandations types par type d'anomalie.

    Couvre :
        - Chute pression air 7 bars → vérification compresseurs, purges
        - Compresseur 3 bars fixe intempestif → basculement sur variables
        - Sous-tension 5,5 kV → réduction charge moteurs non critiques
        - Surtension 63 kV → contact gestionnaire réseau / CAT
        - Température eau recyclée haute → augmentation débit / inspection tours
        - Niveau bassin bas → activation appoint / alerte sécurité
    """
    pass


RECOMMENDATION_LIBRARY: dict[str, Recommendation] = {}
