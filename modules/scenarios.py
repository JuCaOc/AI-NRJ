"""
Définition des scénarios industriels simulés.

Chaque scénario représente une situation opérationnelle réelle
(normale, dégradée ou incidentelle) et modifie les paramètres
injectés dans data_generator pour reproduire des comportements métier.
"""

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Modèle de scénario
# ---------------------------------------------------------------------------

@dataclass
class Scenario:
    """Décrit un scénario industriel simulé."""
    id: str
    name: str
    description: str
    category: str                     # "normal" | "degraded" | "incident"
    affected_systems: list[str]       # ex. ["air_7bar", "electricity_55kv"]
    severity: int                     # 1 (faible) → 5 (critique)
    duration_minutes: int
    parameters: dict = field(default_factory=dict)
    expected_anomalies: list[str] = field(default_factory=list)
    expected_actions: list[str] = field(default_factory=list)
    financial_impact_eur_per_h: Optional[float] = None


# ---------------------------------------------------------------------------
# Catalogue de scénarios
# ---------------------------------------------------------------------------

SCENARIOS: dict[str, Scenario] = {}
"""
Catalogue global indexé par scenario.id.
Sera peuplé lors de l'initialisation du module.
"""


def get_scenario(scenario_id: str) -> Scenario:
    """Retourne un scénario par son identifiant."""
    pass


def list_scenarios(category: Optional[str] = None) -> list[Scenario]:
    """Retourne la liste des scénarios, optionnellement filtrée par catégorie."""
    pass


def get_scenario_ids() -> list[str]:
    """Retourne la liste des identifiants de scénarios disponibles."""
    pass


# ---------------------------------------------------------------------------
# Initialisation du catalogue
# ---------------------------------------------------------------------------

def _build_scenarios() -> dict[str, Scenario]:
    """
    Construit et retourne le catalogue complet des scénarios.

    Scénarios prévus :
        NORMAL_OPS         — fonctionnement nominal 24h
        AIR7_PRESSURE_DROP — chute de pression réseau 7 bars
        AIR7_COMPRESSOR_TRIP — arrêt inopiné compresseur C715
        AIR3_FIXED_RUNAWAY — démarrage intempestif C311 (fixe 3 bars)
        ELEC_PEAK_DEMAND   — pic de demande 63 kV
        ELEC_UNDERVOLTAGE  — sous-tension réseau 5,5 kV
        WATER_RECYCLE_TEMP — température eau recyclée hors seuil
        WATER_BASIN_LOW    — niveau critique bassin B1
        COMBINED_INCIDENT  — incident multi-système (réaliste)
    """
    pass


def _init() -> None:
    """Initialise le catalogue SCENARIOS au chargement du module."""
    pass


_init()
