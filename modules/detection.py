"""
Détection d'anomalies rule-based sur les flux de données utilities.

Chaque détecteur applique des règles métier explicites
(seuils, tendances, corrélations) et retourne des alertes structurées.
L'approche rule-based garantit l'explicabilité des diagnostics IA.
"""

from dataclasses import dataclass, field
from typing import Optional
import pandas as pd


# ---------------------------------------------------------------------------
# Modèle d'alerte
# ---------------------------------------------------------------------------

@dataclass
class Anomaly:
    """Représente une anomalie détectée sur un flux de données."""
    id: str
    timestamp: pd.Timestamp
    system: str                  # "air_7bar" | "electricity_63kv" | ...
    equipment: str               # ex. "C715", "B1", "63kV_bus"
    anomaly_type: str            # ex. "pressure_drop", "undervoltage"
    severity: int                # 1 → 5
    value_observed: float
    value_expected: float
    unit: str
    rule_triggered: str          # identifiant de la règle déclenchée
    description: str
    recommended_action_ids: list[str] = field(default_factory=list)
    context: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Détecteurs par système
# ---------------------------------------------------------------------------

def detect_anomalies_electricity(
    df_63kv: pd.DataFrame,
    df_15kv: pd.DataFrame,
    df_55kv: pd.DataFrame,
    df_400v: pd.DataFrame,
) -> list[Anomaly]:
    """
    Détecte les anomalies sur l'ensemble du réseau électrique.

    Règles appliquées :
        - Tension hors plage nominale (±5 %)
        - Surcharge transformateur (> 90 % capacité)
        - Déséquilibre sources 63 kV (réseau vs CAT)
        - Chute de tension brusque (gradient > seuil)
    """
    pass


def detect_anomalies_air_7bar(df: pd.DataFrame) -> list[Anomaly]:
    """
    Détecte les anomalies sur le réseau air 7 bars.

    Règles appliquées :
        - Pression réseau < 6,5 bars (seuil bas)
        - Pression réseau < 6,0 bars (seuil critique)
        - Compresseur arrêté avec demande non couverte
        - Débit anormalement élevé (fuite potentielle)
        - Consommation électrique hors norme par compresseur
    """
    pass


def detect_anomalies_air_3bar(df: pd.DataFrame) -> list[Anomaly]:
    """
    Détecte les anomalies sur le réseau air 3 bars.

    Règles appliquées :
        - Compresseur fixe actif alors que variables suffisent
        - Pression < 2,7 bars
        - Part des variables < seuil d'efficacité
    """
    pass


def detect_anomalies_recycled_water(df: pd.DataFrame) -> list[Anomaly]:
    """
    Détecte les anomalies sur le circuit eau recyclée.

    Règles appliquées :
        - Température > 35 °C (efficacité refroidissement)
        - pH hors plage [7,0 – 8,5]
        - Conductivité > seuil (risque entartrage)
        - Score risque légionelle > seuil
    """
    pass


def detect_anomalies_raw_water(df: pd.DataFrame) -> list[Anomaly]:
    """
    Détecte les anomalies sur le circuit eau brute.

    Règles appliquées :
        - Niveau bassin B0 < 20 %
        - Niveau bassin B1 < 20 % (critique sécurité)
        - Les deux bassins simultanément bas
        - Débit de secours actif sans alerte déclarée
    """
    pass


# ---------------------------------------------------------------------------
# Point d'entrée consolidé
# ---------------------------------------------------------------------------

def detect_all(data: dict[str, pd.DataFrame]) -> list[Anomaly]:
    """
    Lance tous les détecteurs et retourne la liste consolidée des anomalies,
    triée par sévérité décroissante puis par timestamp.
    """
    pass


def filter_anomalies(
    anomalies: list[Anomaly],
    min_severity: int = 1,
    systems: Optional[list[str]] = None,
) -> list[Anomaly]:
    """Filtre les anomalies par sévérité minimale et/ou systèmes concernés."""
    pass
