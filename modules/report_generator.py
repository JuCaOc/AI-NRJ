"""
Génération automatique du rapport de supervision IA.

Produit un rapport PDF structuré résumant l'état des systèmes,
les anomalies détectées, les recommandations et l'impact financier.
"""

from dataclasses import dataclass
from typing import Optional
import pandas as pd

from modules.detection import Anomaly
from modules.scoring import SystemHealthScore, CriticalityScore
from modules.recommendations import Recommendation
from modules.business_value import FinancialImpact


# ---------------------------------------------------------------------------
# Modèle de rapport
# ---------------------------------------------------------------------------

@dataclass
class ReportData:
    """Données consolidées pour la génération du rapport."""
    generated_at: str
    scenario_name: str
    system_health: dict[str, SystemHealthScore]
    anomalies: list[Anomaly]
    scores: list[CriticalityScore]
    recommendations: list[Recommendation]
    financial_impacts: list[FinancialImpact]
    total_exposure_eur: float
    global_alert_level: str
    operator_notes: str = ""


# ---------------------------------------------------------------------------
# Sections du rapport
# ---------------------------------------------------------------------------

def build_executive_summary(data: ReportData) -> str:
    """Génère le résumé exécutif en texte structuré (markdown)."""
    pass


def build_systems_section(data: ReportData) -> str:
    """Génère la section état des systèmes avec scores de santé."""
    pass


def build_anomalies_section(data: ReportData) -> str:
    """Génère la section anomalies détectées avec priorisation."""
    pass


def build_recommendations_section(data: ReportData) -> str:
    """Génère la section recommandations avec procédures pas à pas."""
    pass


def build_financial_section(data: ReportData) -> str:
    """Génère la section impact financier avec breakdown par système."""
    pass


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

def export_to_pdf(data: ReportData, output_path: str) -> str:
    """
    Génère le rapport PDF complet et le sauvegarde à output_path.
    Retourne le chemin du fichier généré.
    """
    pass


def export_to_markdown(data: ReportData) -> str:
    """Génère le rapport complet en Markdown (pour affichage Streamlit)."""
    pass


def collect_report_data(
    scenario_name: str,
    data: dict[str, pd.DataFrame],
    anomalies: list[Anomaly],
    scores: list[CriticalityScore],
    recommendations: list[Recommendation],
    financial_impacts: list[FinancialImpact],
    operator_notes: str = "",
) -> ReportData:
    """Consolide toutes les données nécessaires pour la génération du rapport."""
    pass
