"""
Chatbot industriel alimenté par Claude (Anthropic API).

L'assistant répond aux questions de l'opérateur avec le contexte
temps-réel des utilities (anomalies actives, scores, recommandations).
Il est configuré pour être explicable, prudent et non directif.
"""

import os
from typing import Optional, Iterator
import anthropic

from modules.detection import Anomaly
from modules.scoring import SystemHealthScore
from modules.recommendations import Recommendation


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL_ID = "claude-sonnet-4-6"

SYSTEM_PROMPT = """
Tu es l'assistant IA du Control Room Énergie & Utilities d'une usine industrielle.

Ton rôle :
- Expliquer les anomalies détectées en langage opérateur
- Contextualiser les alertes avec la physique du procédé
- Proposer des pistes d'analyse, jamais des ordres directs
- Rester prudent : toujours rappeler que l'action finale appartient à l'opérateur

Tu NE DOIS JAMAIS :
- Donner un ordre de démarrage ou d'arrêt d'équipement
- Affirmer avec certitude ce qui est une estimation
- Ignorer un risque sécurité

Contexte fourni dans chaque message : état temps-réel des systèmes, anomalies actives,
recommandations générées.
"""


# ---------------------------------------------------------------------------
# Modèle de conversation
# ---------------------------------------------------------------------------

def build_context_block(
    anomalies: list[Anomaly],
    system_health: dict[str, SystemHealthScore],
    recommendations: list[Recommendation],
) -> str:
    """Formate le contexte opérationnel en texte structuré pour l'injection dans le prompt."""
    pass


def build_messages(
    history: list[dict],
    user_message: str,
    context_block: str,
) -> list[dict]:
    """Construit la liste de messages au format Anthropic Messages API."""
    pass


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

def get_client() -> anthropic.Anthropic:
    """Initialise et retourne le client Anthropic depuis la variable d'environnement."""
    pass


def ask(
    user_message: str,
    history: list[dict],
    anomalies: list[Anomaly],
    system_health: dict[str, SystemHealthScore],
    recommendations: list[Recommendation],
) -> str:
    """
    Envoie un message à l'assistant et retourne la réponse complète.
    Utilise le prompt caching Anthropic pour le bloc système statique.
    """
    pass


def ask_streaming(
    user_message: str,
    history: list[dict],
    anomalies: list[Anomaly],
    system_health: dict[str, SystemHealthScore],
    recommendations: list[Recommendation],
) -> Iterator[str]:
    """Version streaming de ask() — yield les chunks de texte au fur et à mesure."""
    pass


# ---------------------------------------------------------------------------
# Requêtes prédéfinies (quick prompts)
# ---------------------------------------------------------------------------

QUICK_PROMPTS: list[dict] = [
    {"label": "Résume la situation actuelle", "prompt": "Donne-moi un résumé de l'état actuel de l'usine."},
    {"label": "Quelle est l'anomalie la plus critique ?", "prompt": "Quelle est l'anomalie la plus critique en ce moment et pourquoi ?"},
    {"label": "Que faire en priorité ?", "prompt": "Quelles sont les 3 actions prioritaires que je devrais envisager ?"},
    {"label": "Impact financier", "prompt": "Quel est l'impact financier estimé des anomalies actives si elles ne sont pas corrigées ?"},
    {"label": "Expliquer le réseau air 7 bars", "prompt": "Explique-moi le fonctionnement du réseau air 7 bars et son rôle dans le procédé."},
]
