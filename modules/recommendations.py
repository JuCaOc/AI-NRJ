"""
Génération de recommandations IA à partir des anomalies détectées.

Les recommandations sont rule-based, explicables et classées par priorité.
Elles ne constituent jamais des ordres directs — toute action requiert
validation humaine si elle a un impact industriel.

Réponse à la question : « Que doit-on faire maintenant ? »
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

import pandas as pd

from modules.detection import Anomaly
from modules.scoring import CriticalityScore


# ---------------------------------------------------------------------------
# Tables de conversion
# ---------------------------------------------------------------------------

PRIORITY_RULES: dict[str, str] = {
    "critical": "urgent",
    "high":     "high",
    "medium":   "medium",
    "low":      "low",
}

RISK_REDUCTION: dict[str, float] = {
    "urgent": 80.0,
    "high":   60.0,
    "medium": 30.0,
    "low":    10.0,
}

_PRIORITY_ORDER: dict[str, int] = {
    "urgent": 0,
    "high":   1,
    "medium": 2,
    "low":    3,
}

_BASE_SAVINGS_BY_SEVERITY: dict[str, float] = {
    "critical": 320_000.0,
    "high":     130_000.0,
    "medium":    45_000.0,
    "low":       12_000.0,
}

_SAVING_TYPE_MULTIPLIER: dict[str, float] = {
    "legionella_risk":           2.50,
    "multi_system_fault":        3.00,
    "cooling_fault":             1.80,
    "furnace_overload":          1.40,
    "cat_fault":                 1.30,
    "overload_15kv":             1.20,
    "low_basin":                 1.15,
    "air_leak":                  1.10,
    "vsd_saturation":            1.05,
    "compressor_fault":          1.05,
    "raw_water_overconsumption": 0.95,
    "compressor_imbalance":      0.90,
    "bad_regulation":            0.85,
}


# ---------------------------------------------------------------------------
# Modèle de recommandation
# ---------------------------------------------------------------------------

@dataclass
class Recommendation:
    """Action recommandée en réponse à une anomalie détectée."""
    id:                           str
    linked_anomaly_id:            str
    priority:                     str    # "low" | "medium" | "high" | "urgent"
    action_title:                 str
    action_detail:                str
    expected_effect:              str
    estimated_saving_xpf:         float
    estimated_risk_reduction_pct: float
    implementation_difficulty:    str   # "easy" | "medium" | "hard"
    human_validation_required:    bool
    safety_note:                  str
    steps:                        list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Bibliothèque de templates par type d'anomalie
# ---------------------------------------------------------------------------

RECOMMENDATION_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "furnace_overload": [
        {
            "action_title": "Réduire la charge du four 2",
            "action_detail": (
                "Abaisser la consigne de puissance de 10–15 % ou décaler l'opération "
                "en cours vers un créneau horaire à moindre coût."
            ),
            "expected_effect": (
                "Retour sous le seuil critique en ~15 min et réduction de la "
                "consommation excédentaire."
            ),
            "implementation_difficulty": "medium",
            "safety_note": (
                "Vérifier l'impact thermique sur le produit en cours avant toute "
                "modification de consigne."
            ),
            "steps": [
                "1. Vérifier l'état du produit en cours de traitement.",
                "2. Consulter le chef de poste avant modification.",
                "3. Abaisser la consigne de 5 % par palier de 5 minutes.",
                "4. Surveiller la puissance active sur le tableau 63 kV.",
            ],
        },
        {
            "action_title": "Vérifier le rendement thermique du four 2",
            "action_detail": (
                "Inspecter l'isolation, les brûleurs et les régulations de température "
                "pour identifier une dérive de rendement."
            ),
            "expected_effect": (
                "Identification d'une dérive pouvant expliquer +5–15 % de consommation."
            ),
            "implementation_difficulty": "hard",
            "safety_note": (
                "Intervention à réaliser hors production ou avec accès sécurisé "
                "(zone chaude, EPI thermiques obligatoires)."
            ),
            "steps": [
                "1. Relever les températures de peau et de voûte.",
                "2. Comparer avec les valeurs nominales du fichier de suivi.",
                "3. Inspecter visuellement l'étanchéité des portes.",
                "4. Planifier une maintenance préventive si dérive confirmée.",
            ],
        },
    ],
    "cat_fault": [
        {
            "action_title": "Vérifier l'état de la centrale CAT",
            "action_detail": (
                "Contrôler les paramètres de la turbine : pression, température, "
                "débit gaz, alarmes actives sur pupitre."
            ),
            "expected_effect": (
                "Identification rapide de la cause et restauration de la puissance nominale."
            ),
            "implementation_difficulty": "hard",
            "safety_note": (
                "Zone turbine — EPI obligatoires, procédure lockout/tagout requise "
                "avant toute intervention."
            ),
            "steps": [
                "1. Consulter le tableau de commande CAT : alarmes actives, état démarrage.",
                "2. Vérifier la pression d'alimentation gaz.",
                "3. Contrôler les températures d'entrée/sortie turbine.",
                "4. Contacter l'astreinte constructeur si l'anomalie persiste > 30 min.",
            ],
        },
        {
            "action_title": "Anticiper la surcharge réseau et alerter le dispatching",
            "action_detail": (
                "Contacter le gestionnaire réseau pour anticiper l'augmentation d'import "
                "et limiter les risques de délestage."
            ),
            "expected_effect": "Maintien de la fourniture d'énergie sans rupture pendant la perte CAT.",
            "implementation_difficulty": "easy",
            "safety_note": "Ne pas attendre — prévenir le dispatching dès le constat de perte CAT.",
            "steps": [
                "1. Appeler le dispatching réseau (numéro d'astreinte).",
                "2. Communiquer la puissance manquante estimée (MW).",
                "3. Réduire les charges non critiques en attente de stabilisation.",
                "4. Documenter l'événement dans le registre exploitation.",
            ],
        },
    ],
    "overload_15kv": [
        {
            "action_title": "Rééquilibrer les sous-stations 15 kV",
            "action_detail": (
                "Transférer une partie de la charge de la sous-station surchargée "
                "vers une sous-station moins chargée."
            ),
            "expected_effect": "Réduction de 15–20 % sur la sous-station surchargée en 10–20 min.",
            "implementation_difficulty": "medium",
            "safety_note": "Vérifier les capacités des câbles de transfert avant manœuvre électrique.",
            "steps": [
                "1. Identifier la sous-station la plus chargée sur le synoptique.",
                "2. Vérifier les capacités de transfert disponibles.",
                "3. Réaliser le transfert progressivement (5 % par palier).",
                "4. Confirmer la stabilisation sur le tableau de contrôle.",
            ],
        },
        {
            "action_title": "Reporter les démarrages moteurs non urgents",
            "action_detail": (
                "Différer les démarrages planifiés jusqu'au retour à la normale "
                "du poste 15 kV."
            ),
            "expected_effect": (
                "Réduction immédiate du pic de charge à chaque démarrage évité "
                "(~1–3 MW par démarrage)."
            ),
            "implementation_difficulty": "easy",
            "safety_note": (
                "Aucune action physique directe — coordination avec les équipes "
                "process requise."
            ),
            "steps": [
                "1. Consulter le planning des démarrages prévus.",
                "2. Reporter tout démarrage non critique de 30–60 min.",
                "3. Informer les équipes process de la restriction temporaire.",
            ],
        },
    ],
    "air_leak": [
        {
            "action_title": "Inspection du réseau air 7 bars",
            "action_detail": (
                "Parcours de toutes les branches du réseau avec détecteur ultrasonique "
                "pour localiser les fuites."
            ),
            "expected_effect": (
                "Localisation de la fuite et réduction de la surconsommation "
                "compresseurs estimée à 5–15 %."
            ),
            "implementation_difficulty": "medium",
            "safety_note": (
                "EPI obligatoires — risque de jet d'air sous pression "
                "lors du contrôle ultrasonique."
            ),
            "steps": [
                "1. Équiper le technicien d'un détecteur ultrasonique.",
                "2. Inspecter systématiquement : raccords, vannes, flexibles, purges.",
                "3. Marquer les points de fuite détectés.",
                "4. Planifier la réparation selon criticité.",
            ],
        },
        {
            "action_title": "Test d'étanchéité et isolation des sections",
            "action_detail": (
                "Isoler les sections une à une pour identifier la zone de fuite, "
                "puis réaliser un test de montée en pression."
            ),
            "expected_effect": "Identification précise de la source de fuite sur la section concernée.",
            "implementation_difficulty": "hard",
            "safety_note": (
                "Procédure d'isolement sectoriel — coordonner avec le process "
                "pour éviter les ruptures d'alimentation."
            ),
            "steps": [
                "1. Identifier les vannes d'isolation de chaque section.",
                "2. Isoler une section (si la production le permet).",
                "3. Observer la pression résiduelle : chute rapide = fuite dans la section.",
                "4. Réaliser la réparation avant remise en service.",
            ],
        },
    ],
    "compressor_fault": [
        {
            "action_title": "Maintenance compresseur C715",
            "action_detail": (
                "Inspecter les filtres, le niveau d'huile, les courroies et le "
                "système de régulation du compresseur."
            ),
            "expected_effect": (
                "Restauration des performances nominales et prévention d'un "
                "arrêt intempestif."
            ),
            "implementation_difficulty": "medium",
            "safety_note": "Consigner C715 (lockout/tagout) avant toute intervention mécanique.",
            "steps": [
                "1. Consigner C715 (lockout/tagout).",
                "2. Contrôler et remplacer les filtres air.",
                "3. Vérifier le niveau d'huile et la qualité.",
                "4. Inspecter les courroies et le couplage.",
                "5. Tester le redémarrage à vide avant remise en service.",
            ],
        },
    ],
    "compressor_imbalance": [
        {
            "action_title": "Rééquilibrer la charge entre C713 et C714",
            "action_detail": (
                "Ajuster les consignes de pression de déclenchement pour équilibrer "
                "le fonctionnement des deux compresseurs de base."
            ),
            "expected_effect": "Réduction de l'usure différentielle et économie sur la maintenance long terme.",
            "implementation_difficulty": "easy",
            "safety_note": "Modification des consignes — à valider avec le responsable utilities.",
            "steps": [
                "1. Relever les heures de marche actuelles C713 et C714.",
                "2. Ajuster la bande morte de régulation pour équilibrer.",
                "3. Observer le comportement pendant 30 min.",
                "4. Documenter le réglage dans le carnet de bord.",
            ],
        },
    ],
    "vsd_saturation": [
        {
            "action_title": "Réduire la demande process sur le réseau 3 bars",
            "action_detail": (
                "Identifier et réduire temporairement les consommations non critiques "
                "alimentées en 3 bars."
            ),
            "expected_effect": "Retour des VSD sous 95 % de charge, prévention d'un arrêt compresseur.",
            "implementation_difficulty": "medium",
            "safety_note": "Valider avec le process que la réduction est acceptable avant application.",
            "steps": [
                "1. Identifier les consommateurs 3 bars non critiques.",
                "2. Réduire ou interrompre temporairement ces usages.",
                "3. Vérifier la vitesse VSD : retour sous 95 %.",
                "4. Restaurer progressivement après stabilisation.",
            ],
        },
        {
            "action_title": "Démarrer un compresseur fixe en appoint",
            "action_detail": (
                "Mettre en service C311 ou C312 en appoint temporaire pour "
                "soulager les VSD surchargés."
            ),
            "expected_effect": "Réduction immédiate de la charge VSD, maintien de la pression réseau 3 bars.",
            "implementation_difficulty": "easy",
            "safety_note": (
                "Vérifier le bon état du compresseur fixe (niveau d'huile, filtres) "
                "avant démarrage."
            ),
            "steps": [
                "1. Vérifier le niveau d'huile et l'état de C311/C312.",
                "2. Démarrer en mode manuel.",
                "3. Attendre stabilisation pression (~5 min).",
                "4. Surveiller la répartition de charge VSD/fixe.",
            ],
        },
    ],
    "bad_regulation": [
        {
            "action_title": "Revoir la logique de pilotage air 3 bars",
            "action_detail": (
                "Analyser le comportement de la régulation et ajuster les paramètres "
                "PID ou les seuils de déclenchement."
            ),
            "expected_effect": "Élimination des cycles courts, réduction de l'usure mécanique des compresseurs.",
            "implementation_difficulty": "hard",
            "safety_note": (
                "Modification de régulation — à réaliser hors période critique, "
                "avec retour arrière préparé."
            ),
            "steps": [
                "1. Télécharger l'historique 24 h de pression et débit 3 bars.",
                "2. Identifier la fréquence et l'amplitude des oscillations.",
                "3. Ajuster le gain PID (réduire proportionnel de 10 %).",
                "4. Tester sur 1 h et comparer aux valeurs de référence.",
                "5. Valider avec le responsable automatisme avant activation définitive.",
            ],
        },
    ],
    "cooling_fault": [
        {
            "action_title": "Vérifier la pompe EF1 et le circuit eau recyclée",
            "action_detail": (
                "Contrôler le débit, la pression de refoulement, les températures "
                "et l'état mécanique de la pompe."
            ),
            "expected_effect": "Diagnostic de la cause du défaut de refroidissement en < 30 min.",
            "implementation_difficulty": "medium",
            "safety_note": "Risque de brûlure — vérifier les températures circuit avant toute intervention.",
            "steps": [
                "1. Relever débit (débitmètre), pression, température entrée/sortie.",
                "2. Comparer avec les valeurs nominales.",
                "3. Inspecter la pompe EF1 (cavitation, bruit anormal).",
                "4. Vérifier les clapets et vannes du circuit.",
                "5. Déclencher l'alarme maintenance si anomalie confirmée.",
            ],
        },
        {
            "action_title": "Réduire la charge thermique process",
            "action_detail": (
                "Réduire temporairement la charge des équipements refroidis pour "
                "limiter la montée en température."
            ),
            "expected_effect": (
                "Ralentissement de la montée en température — gain de temps "
                "pour l'intervention maintenance."
            ),
            "implementation_difficulty": "medium",
            "safety_note": "Valider avec le process l'impact de la réduction de charge avant application.",
            "steps": [
                "1. Identifier les équipements avec le plus fort débit de refroidissement.",
                "2. Réduire leur charge de 10–20 %.",
                "3. Surveiller ΔT retour/départ.",
                "4. Maintenir la réduction jusqu'au retour à la normale.",
            ],
        },
    ],
    "legionella_risk": [
        {
            "action_title": "Renforcer le traitement chimique des tours aéroréfrigérantes",
            "action_detail": (
                "Augmenter la dose de biocide et réaliser un choc chloré selon "
                "le protocole réglementaire en vigueur."
            ),
            "expected_effect": "Retour sous le seuil de risque légionelle en 24–48 h après traitement.",
            "implementation_difficulty": "medium",
            "safety_note": (
                "SÉCURITÉ SANITAIRE — intervention obligatoire et déclaration "
                "réglementaire si dépassement confirmé."
            ),
            "steps": [
                "1. Prélever un échantillon d'eau pour analyse laboratoire (URGENT).",
                "2. Appliquer immédiatement un choc biocide selon protocole.",
                "3. Vérifier le niveau de biocide résiduel après 2 h.",
                "4. Notifier le responsable HSE et enregistrer dans le registre légionelle.",
                "5. Consigner les tours si le risque est confirmé par analyse.",
            ],
        },
        {
            "action_title": "Inspecter les tours aéroréfrigérantes",
            "action_detail": (
                "Contrôler les garnissages, les distributeurs et l'état général pour "
                "détecter des zones de stagnation favorables au développement bactérien."
            ),
            "expected_effect": "Identification et correction des points de développement bactérien potentiels.",
            "implementation_difficulty": "hard",
            "safety_note": (
                "EPI obligatoires : masque FFP3, combinaison, lunettes de protection "
                "lors de l'inspection."
            ),
            "steps": [
                "1. Équiper les intervenants des EPI adaptés (masque FFP3 obligatoire).",
                "2. Inspecter les garnissages : encrassement, zones mortes.",
                "3. Vérifier les distributeurs d'eau.",
                "4. Planifier le nettoyage haute pression si encrassement détecté.",
            ],
        },
    ],
    "low_basin": [
        {
            "action_title": "Limiter les consommations d'eau brute non essentielles",
            "action_detail": (
                "Identifier et suspendre les usages d'eau brute non critiques pour "
                "préserver le niveau du bassin B1."
            ),
            "expected_effect": "Ralentissement de la vidange — gain de 2–4 h avant seuil d'arrêt critique.",
            "implementation_difficulty": "easy",
            "safety_note": (
                "Vérifier que les systèmes de refroidissement critiques maintiennent "
                "leur alimentation."
            ),
            "steps": [
                "1. Identifier les consommateurs eau brute non critiques.",
                "2. Couper ou réduire ces usages.",
                "3. Surveiller le niveau B1 toutes les 30 min.",
                "4. Déclencher l'alerte si le niveau continue à baisser.",
            ],
        },
        {
            "action_title": "Activer l'alimentation de secours du bassin B1",
            "action_detail": (
                "Ouvrir la vanne d'appoint d'urgence ou activer la pompe de secours "
                "pour remonter le niveau du bassin."
            ),
            "expected_effect": "Remontée du niveau B1 au-dessus du seuil critique en 30–60 min.",
            "implementation_difficulty": "easy",
            "safety_note": (
                "Vérifier la disponibilité et la qualité de la source de secours "
                "avant activation."
            ),
            "steps": [
                "1. Identifier la source de secours disponible.",
                "2. Ouvrir la vanne d'appoint d'urgence.",
                "3. Surveiller le débit et la montée en niveau.",
                "4. Fermer dès le niveau nominal atteint.",
            ],
        },
    ],
    "raw_water_overconsumption": [
        {
            "action_title": "Augmenter le taux de recyclage de l'eau",
            "action_detail": (
                "Réduire les purges des circuits de refroidissement pour maximiser "
                "le recyclage et limiter l'appoint eau brute."
            ),
            "expected_effect": (
                "Réduction de la dépendance eau brute de 10–20 % et économie "
                "sur le coût d'approvisionnement."
            ),
            "implementation_difficulty": "medium",
            "safety_note": (
                "Surveiller la conductivité et la dureté de l'eau recyclée après "
                "réduction des purges."
            ),
            "steps": [
                "1. Contrôler la conductivité et la dureté de l'eau de circuit.",
                "2. Si dans les limites, réduire les purges de 20 %.",
                "3. Répéter l'analyse après 4 h.",
                "4. Ajuster selon les résultats d'analyse.",
            ],
        },
        {
            "action_title": "Identifier et réduire les pertes en eau",
            "action_detail": (
                "Inspecter les circuits pour localiser les fuites, débordements "
                "ou évaporations excessives."
            ),
            "expected_effect": "Réduction des pertes non comptabilisées et de l'appoint eau brute.",
            "implementation_difficulty": "medium",
            "safety_note": (
                "Vérifier que les circuits inspectés ne sont pas sous pression "
                "avant intervention."
            ),
            "steps": [
                "1. Parcourir les circuits de refroidissement.",
                "2. Vérifier les bacs, tours et canalisations.",
                "3. Identifier les pertes visibles.",
                "4. Réparer les fuites ou adapter les niveaux de remplissage.",
            ],
        },
    ],
    "multi_system_fault": [
        {
            "action_title": "Activer la procédure multi-crise",
            "action_detail": (
                "Coordonner simultanément les interventions sur les systèmes affectés "
                "en priorisant la sécurité et la continuité de production."
            ),
            "expected_effect": (
                "Réduction du risque global usine et prévention d'un arrêt de "
                "production non planifié."
            ),
            "implementation_difficulty": "hard",
            "safety_note": (
                "SITUATION DÉGRADÉE — mobiliser le responsable de quart et la "
                "maintenance immédiatement."
            ),
            "steps": [
                "1. Alerter le chef de quart et le responsable maintenance.",
                "2. Prioriser : sécurité > refroidissement > électricité > air.",
                "3. Affecter un technicien par système en anomalie.",
                "4. Point de situation toutes les 15 min.",
                "5. Documenter chaque action dans le registre exploitation.",
            ],
        },
    ],
}

_GENERIC_TEMPLATE: list[dict[str, Any]] = [
    {
        "action_title": "Analyser l'anomalie et inspecter le système",
        "action_detail": (
            "Rassembler les données opérationnelles et inspecter le système concerné "
            "pour identifier la cause racine."
        ),
        "expected_effect": "Identification et correction de l'anomalie détectée.",
        "implementation_difficulty": "medium",
        "safety_note": "Vérifier les conditions de sécurité avant toute intervention sur le système.",
        "steps": [
            "1. Analyser les données opérationnelles disponibles.",
            "2. Consulter l'historique des alarmes.",
            "3. Contacter le responsable maintenance pour planifier l'intervention.",
        ],
    }
]


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------

def _duration_hours(anomaly: dict) -> float:
    try:
        minutes = max(0.0, (
            pd.Timestamp(str(anomaly.get("timestamp_end", "")))
            - pd.Timestamp(str(anomaly.get("timestamp_start", "")))
        ).total_seconds() / 60.0)
        return max(0.25, minutes / 60.0)
    except Exception:
        return 1.0


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def estimate_savings(anomaly: dict) -> float:
    """
    Estime l'économie réalisable en XPF si la recommandation est appliquée.

    Formule : base_severity × type_multiplier × confidence × duration_factor
    duration_factor = min(duration_h, 4.0) — plafonné à 4 h pour éviter
    les estimations non bornées sur des anomalies très longues.
    """
    severity   = anomaly.get("severity", "medium")
    anom_type  = anomaly.get("anomaly_type", "")
    confidence = float(anomaly.get("confidence_score", 0.75))

    base            = _BASE_SAVINGS_BY_SEVERITY.get(severity, 45_000.0)
    type_mult       = _SAVING_TYPE_MULTIPLIER.get(anom_type, 1.0)
    duration_factor = min(_duration_hours(anomaly), 4.0)

    return round(base * type_mult * confidence * duration_factor, 0)


def estimate_risk_reduction(anomaly: dict) -> float:
    """Retourne la réduction de risque estimée (%) selon la sévérité de l'anomalie."""
    priority = PRIORITY_RULES.get(anomaly.get("severity", "medium"), "medium")
    return RISK_REDUCTION.get(priority, 30.0)


def recommendation_for_anomaly(anomaly: dict) -> list[Recommendation]:
    """Génère la liste des recommandations pour une anomalie donnée."""
    anom_type  = anomaly.get("anomaly_type", "")
    severity   = anomaly.get("severity", "medium")
    priority   = PRIORITY_RULES.get(severity, "medium")
    anomaly_id = anomaly.get("id", "unknown")

    templates  = RECOMMENDATION_TEMPLATES.get(anom_type, _GENERIC_TEMPLATE)
    saving     = estimate_savings(anomaly)
    risk_red   = estimate_risk_reduction(anomaly)

    return [
        Recommendation(
            id=f"REC-{anomaly_id}-{idx:02d}",
            linked_anomaly_id=anomaly_id,
            priority=priority,
            action_title=tmpl["action_title"],
            action_detail=tmpl["action_detail"],
            expected_effect=tmpl["expected_effect"],
            estimated_saving_xpf=saving,
            estimated_risk_reduction_pct=risk_red,
            implementation_difficulty=tmpl["implementation_difficulty"],
            human_validation_required=True,
            safety_note=tmpl["safety_note"],
            steps=list(tmpl.get("steps", [])),
        )
        for idx, tmpl in enumerate(templates, 1)
    ]


def prioritize_recommendations(recommendations: list[Recommendation]) -> list[Recommendation]:
    """Trie par priorité décroissante (urgent → low), puis économies décroissantes."""
    return sorted(
        recommendations,
        key=lambda r: (_PRIORITY_ORDER.get(r.priority, 9), -r.estimated_saving_xpf),
    )


def deduplicate_recommendations(recommendations: list[Recommendation]) -> list[Recommendation]:
    """Supprime les doublons exacts (même anomalie, même titre d'action)."""
    seen: set[tuple] = set()
    result: list[Recommendation] = []
    for rec in recommendations:
        key = (rec.linked_anomaly_id, rec.action_title)
        if key not in seen:
            seen.add(key)
            result.append(rec)
    return result


def generate_recommendations(
    anomalies: list[dict],
    scoring_summary: Optional[dict] = None,
) -> list[Recommendation]:
    """
    Génère, déduplique et priorise toutes les recommandations pour les anomalies actives.

    scoring_summary (optionnel) — réservé pour une future pondération par score global.
    Retourne la liste triée par priorité décroissante puis économies décroissantes.
    """
    all_recs: list[Recommendation] = []
    for anomaly in anomalies:
        all_recs.extend(recommendation_for_anomaly(anomaly))
    return prioritize_recommendations(deduplicate_recommendations(all_recs))


def summarize_recommendations(recommendations: list[Recommendation]) -> dict:
    """
    Résumé exploitable dans Streamlit.

    Retourne :
        count, urgent_count, top_action, total_saving_xpf, has_safety_risk
    """
    if not recommendations:
        return {
            "count":            0,
            "urgent_count":     0,
            "top_action":       None,
            "total_saving_xpf": 0.0,
            "has_safety_risk":  False,
        }
    urgent = [r for r in recommendations if r.priority == "urgent"]
    has_safety = any(
        "sécurité" in r.safety_note.lower()
        or "epi" in r.safety_note.lower()
        or "sanitaire" in r.safety_note.lower()
        for r in recommendations
    )
    return {
        "count":            len(recommendations),
        "urgent_count":     len(urgent),
        "top_action":       recommendations[0].action_title,
        "total_saving_xpf": round(sum(r.estimated_saving_xpf for r in recommendations), 0),
        "has_safety_risk":  has_safety,
    }


# ---------------------------------------------------------------------------
# Backward-compat aliases — consommés par tests existants et modules aval
# ---------------------------------------------------------------------------

def recommend_for_anomaly(
    anomaly: Anomaly,
    score: Optional[CriticalityScore] = None,
) -> list[Recommendation]:
    """Alias de recommendation_for_anomaly."""
    return recommendation_for_anomaly(anomaly)


def recommend_all(
    anomalies: list[Anomaly],
    scores: Optional[list[CriticalityScore]] = None,
) -> list[Recommendation]:
    """Alias de generate_recommendations."""
    return generate_recommendations(anomalies)


# Module-level constant kept for backward compat
RECOMMENDATION_LIBRARY: dict[str, list[dict[str, Any]]] = RECOMMENDATION_TEMPLATES
