"""
Assistant IA industriel — simulé, rule-based, sans API externe.

Répond aux questions de l'opérateur à partir des données disponibles dans
la session. Aucun appel réseau, aucun modèle ML. Toutes les réponses sont
dérivées des données locales (anomalies, scoring, recommandations, DataFrame).
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from modules.detection import Anomaly
from modules.recommendations import Recommendation


# ---------------------------------------------------------------------------
# Helpers locaux
# ---------------------------------------------------------------------------

def _fmt_xpf(v: float) -> str:
    """Formate un montant en XPF (k ou M selon la magnitude)."""
    if v >= 1_000_000:
        return f"{v / 1_000_000:.1f}M"
    if v >= 1_000:
        return f"{v / 1_000:.0f}k"
    return f"{v:.0f}"


def _rec_attr(r: Any, attr: str, default: Any = "") -> Any:
    """Accès attribut sur Recommendation (dataclass ou dict)."""
    if hasattr(r, attr):
        return getattr(r, attr)
    if isinstance(r, dict):
        return r.get(attr, default)
    return default


_SEVERITY_FR: dict[str, str] = {
    "critical": "CRITIQUE",
    "high":     "ÉLEVÉE",
    "medium":   "MOYENNE",
    "low":      "FAIBLE",
}

_PRIORITY_FR: dict[str, str] = {
    "urgent": "URGENT",
    "high":   "ÉLEVÉE",
    "medium": "MOYENNE",
    "low":    "FAIBLE",
}

_DOMAIN_FR: dict[str, str] = {
    "electricity": "électricité",
    "air":         "air comprimé",
    "water":       "eau",
}

_SAFETY_NOTE = (
    "\n\n⚠️ **Note de sécurité** : Ce système est une simulation. "
    "Toute action terrain doit être validée par l'exploitation avant exécution."
)


# ---------------------------------------------------------------------------
# 1. Classification par mots-clés
# ---------------------------------------------------------------------------

_INTENT_KEYWORDS: dict[str, list[str]] = {
    "global_status": [
        "état", "etat", "statut", "situation", "usine", "global", "général",
        "general", "résumé", "resume", "comment va", "fonctionne", "vue d'ensemble",
    ],
    "most_critical_anomaly": [
        "plus critique", "plus grave", "la plus", "pire", "plus urgente",
        "principale anomalie", "anomalie principale", "prioritaire",
    ],  # "critique" seul retiré — trop large (ex: "bassin B1 critique")
    "electricity": [
        "électricité", "electricite", "63kv", "63 kv", "15kv", "15 kv",
        "four", "cat", "réseau électrique", "reseau electrique",
        "puissance", "bus", "sous-station", "import réseau", "génération cat",
    ],
    "air_7b": [
        "air 7", "7 bars", "7bar", "c713", "c714", "c715", "c716", "c717",
        "instrument", "air instrument", "fuite air", "7 b", "compresseur",
    ],
    "air_3b": [
        "air 3", "3 bars", "3bar", "c321", "c322", "c323", "c311", "c312",
        "poussières", "poussieres", "charbon", "vsd", "régulation air",
        "regulation air", "3 b", "air process",
    ],
    "water": [
        "eau", "recyclée", "recyclee", "brute", "b0", "b1", "légionelle",
        "legionelle", "refroidissement", "bassin", "pompe ef", "delta t",
        "température eau", "temperature eau", "chimique",
    ],
    "recommendations": [
        "recommande", "recommandation", "action", "que faire", "solution",
        "corriger", "corrective", "étapes", "etapes", "mesures", "faire",
    ],
    "business_impact": [
        "coût", "cout", "argent", "perte", "économie", "economie", "xpf",
        "roi", "financier", "financière", "montant", "combien", "prix",
    ],
    "scada_vs_ai": [
        "scada", "historian", "supervision", "différence", "difference",
        "seuil", "alarme", "avantage ia", "comparaison", "vs scada",
    ],
    "safety": [
        "sécurité", "securite", "risque sécurité", "danger", "validation humaine",
        "ordre automatique", "pilote automatique",
    ],  # "risque" et "commande" retirés — sous-chaînes de "légionelle risque" et "recommande"
}

# Ordre de priorité : les intents les plus spécifiques en premier
_INTENT_PRIORITY: list[str] = [
    "scada_vs_ai", "safety", "most_critical_anomaly",
    "air_7b", "air_3b", "electricity", "water",
    "business_impact", "recommendations", "global_status",
]


def classify_question_intent(question: str) -> str:
    """Classe une question en intent parmi 11 catégories par matching de mots-clés."""
    q = question.lower()
    for intent in _INTENT_PRIORITY:
        for kw in _INTENT_KEYWORDS[intent]:
            if kw in q:
                return intent
    return "unknown"


# ---------------------------------------------------------------------------
# 2. Construction du contexte
# ---------------------------------------------------------------------------

def build_context_summary(
    df: pd.DataFrame,
    anomalies: list[Anomaly],
    recommendations: list[Recommendation],
    scoring_summary: dict[str, Any],
    business_summary: dict[str, Any],
) -> dict[str, Any]:
    """
    Extrait les faits clés de toutes les sources de données en un dict plat.
    Tous les accès sont défensifs — fonctionne même si les données sont vides.
    """
    ctx: dict[str, Any] = {}

    # ── Scoring ──────────────────────────────────────────────────────────────
    ctx["global_score"]      = scoring_summary.get("global_score", 0.0)
    ctx["global_status"]     = scoring_summary.get("status", "NORMAL")
    ctx["has_critical"]      = scoring_summary.get("has_critical", False)
    domain_scores            = scoring_summary.get("domain_scores", {})
    ctx["electricity_score"] = domain_scores.get("electricity_score", 0.0)
    ctx["air_score"]         = domain_scores.get("air_score", 0.0)
    ctx["water_score"]       = domain_scores.get("water_score", 0.0)

    # ── Anomalies ─────────────────────────────────────────────────────────────
    ctx["n_anomalies"] = len(anomalies)
    ctx["n_critical"]  = sum(1 for a in anomalies if a.get("severity") == "critical")
    ctx["n_high"]      = sum(1 for a in anomalies if a.get("severity") == "high")

    _sev_rank = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    sorted_anom = sorted(
        anomalies,
        key=lambda a: (_sev_rank.get(a.get("severity", "low"), 0), a.get("confidence_score", 0.0)),
        reverse=True,
    )
    ctx["sorted_anomalies"] = sorted_anom
    ctx["top_anomaly"]      = sorted_anom[0] if sorted_anom else None

    for domain in ("electricity", "air", "water"):
        ctx[f"{domain}_anomalies"] = [a for a in anomalies if a.get("domain") == domain]

    # ── Recommandations ───────────────────────────────────────────────────────
    _prio_rank = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
    sorted_recs = sorted(
        recommendations,
        key=lambda r: _prio_rank.get(_rec_attr(r, "priority", "low"), 3),
    )
    ctx["sorted_recommendations"] = sorted_recs
    ctx["top_3_recs"]             = sorted_recs[:3]

    # ── Business ──────────────────────────────────────────────────────────────
    ctx["total_loss_xpf"]       = business_summary.get("total_loss_xpf", 0.0)
    ctx["avoidable_loss_xpf"]   = business_summary.get("avoidable_loss_xpf", 0.0)
    ctx["estimated_savings_xpf"] = business_summary.get("estimated_savings_xpf", 0.0)
    ctx["roi_summary"]          = business_summary.get("roi_summary", "")

    # ── Valeurs temps-réel (dernière ligne du DataFrame) ──────────────────────
    def _get(col: str, src: pd.Series) -> float | None:
        return float(src[col]) if col in src.index else None

    if df is not None and not df.empty:
        last = df.iloc[-1]
        mean = df.mean(numeric_only=True)

        ctx["air_7b_pressure"] = _get("air_7b_pressure", last)
        ctx["air_7b_flow"]     = _get("air_7b_total_flow_nm3h", last)
        ctx["air_7b_power"]    = _get("air_7b_total_power_kw", last)
        ctx["air_7b_se"]       = _get("air_7b_specific_energy_kwh_per_nm3", last)
        ctx["air_3b_pressure"] = _get("air_3b_pressure", last)
        ctx["c321_speed"]      = _get("C321_speed_pct", last)
        ctx["c322_speed"]      = _get("C322_speed_pct", last)
        ctx["c323_speed"]      = _get("C323_speed_pct", last)
        ctx["rw_flow"]         = _get("recycled_water_flow_m3h", last)
        ctx["rw_delta_t"]      = _get("recycled_water_delta_t_c", last)
        ctx["legionella"]      = _get("legionella_risk_index", last)
        ctx["basin_b0"]        = _get("basin_b0_level_pct", last)
        ctx["basin_b1"]        = _get("basin_b1_level_pct", last)
        ctx["total_power"]     = _get("total_plant_power_mw", last)
        ctx["cat_gen"]         = _get("cat_generation_63kv_mw", last)
        ctx["grid_import"]     = _get("grid_import_63kv_mw", last)
        ctx["furnace_2_power"] = _get("furnace_2_63kv_mw", last)
        ctx["energy_cost_total"] = _get("energy_cost_xpf", mean)
        for tag in ("C713", "C714", "C715", "C716", "C717"):
            ctx[f"{tag}_flow"] = _get(f"{tag}_flow_nm3h", last)
    else:
        for key in (
            "air_7b_pressure", "air_7b_flow", "air_7b_power", "air_7b_se",
            "air_3b_pressure", "c321_speed", "c322_speed", "c323_speed",
            "rw_flow", "rw_delta_t", "legionella", "basin_b0", "basin_b1",
            "total_power", "cat_gen", "grid_import", "furnace_2_power",
            "energy_cost_total", "C713_flow", "C714_flow", "C715_flow",
            "C716_flow", "C717_flow",
        ):
            ctx[key] = None

    return ctx


# ---------------------------------------------------------------------------
# 3. Générateurs de réponse par intent
# ---------------------------------------------------------------------------

def _ans_global_status(ctx: dict) -> str:
    status = ctx["global_status"]
    score  = ctx["global_score"]
    n      = ctx["n_anomalies"]
    n_crit = ctx["n_critical"]
    top    = ctx["top_anomaly"]

    if n == 0:
        return (
            f"**Situation : {status} — Score {score:.0f}/100**\n\n"
            "L'usine fonctionne dans ses paramètres nominaux. "
            "Aucune anomalie active sur les trois domaines (électricité, air, eau)."
            + _SAFETY_NOTE
        )

    lines = [
        f"**Situation : {status} — Score {score:.0f}/100**\n",
        f"- {n} anomalie(s) active(s)"
        + (f", dont **{n_crit} CRITIQUE(S)**" if n_crit else ""),
        (f"- Scores domaines : ⚡ Électricité {ctx['electricity_score']:.0f} · "
         f"💨 Air {ctx['air_score']:.0f} · "
         f"♻️ Eau {ctx['water_score']:.0f}"),
    ]

    if top:
        sev_fr = _SEVERITY_FR.get(top.get("severity", ""), top.get("severity", "").upper())
        lines.append(
            f"\n**Anomalie principale :** [{sev_fr}] {top.get('title', '')} "
            f"({top.get('asset', '')})\n_{top.get('description', '')}_"
        )

    if ctx["total_loss_xpf"] > 0:
        lines.append(
            f"\n**Impact financier estimé :** {_fmt_xpf(ctx['total_loss_xpf'])} XPF"
        )

    lines.append(_SAFETY_NOTE)
    return "\n".join(lines)


def _ans_most_critical(ctx: dict) -> str:
    top = ctx["top_anomaly"]
    if not top:
        return (
            "Aucune anomalie détectée. L'usine fonctionne normalement."
            + _SAFETY_NOTE
        )

    sev_fr    = _SEVERITY_FR.get(top.get("severity", ""), top.get("severity", "").upper())
    domain_fr = _DOMAIN_FR.get(top.get("domain", ""), top.get("domain", ""))
    ev        = top.get("evidence", {})
    causes    = top.get("probable_causes", [])

    lines = [
        f"**Anomalie la plus critique : [{sev_fr}] {top.get('title', '')}**\n",
        f"- **Équipement :** {top.get('asset', '')}",
        f"- **Domaine :** {domain_fr.capitalize()}",
        f"- **Confiance :** {top.get('confidence_score', 0):.0%}",
        f"- **Description :** {top.get('description', '')}",
    ]

    if ev:
        ev_str = " · ".join(
            f"{k.replace('_', ' ')} = {v}" for k, v in list(ev.items())[:3]
        )
        lines.append(f"- **Preuves :** {ev_str}")

    if causes:
        lines.append("\n**Causes probables :**")
        for c in causes[:3]:
            lines.append(f"  - {c}")

    lines.append(_SAFETY_NOTE)
    return "\n".join(lines)


def _ans_electricity(ctx: dict, question: str) -> str:
    anom  = ctx["electricity_anomalies"]
    score = ctx["electricity_score"]

    if not anom:
        lines = [
            f"**Domaine électricité : Score {score:.0f}/100 — Nominal**\n",
            "Aucune anomalie détectée sur le réseau électrique. "
            "Bus 63 kV, centrale CAT et postes 15 kV dans les paramètres.",
        ]
        if ctx["furnace_2_power"] is not None:
            lines.append(f"Puissance four 2 : {ctx['furnace_2_power']:.1f} MW (seuil 62 MW)")
        if ctx["cat_gen"] is not None:
            lines.append(f"Génération CAT : {ctx['cat_gen']:.1f} MW (min. 70 MW)")
        lines.append(_SAFETY_NOTE)
        return "\n".join(lines)

    lines = [f"**Domaine électricité : Score {score:.0f}/100**\n"]
    for a in anom:
        sev_fr = _SEVERITY_FR.get(a.get("severity", ""), a.get("severity", "").upper())
        lines.append(f"- [{sev_fr}] **{a.get('title', '')}** ({a.get('asset', '')})")
        lines.append(f"  _{a.get('description', '')}_")

    if ctx["furnace_2_power"] is not None:
        lines.append(f"\n**Puissance four 2 :** {ctx['furnace_2_power']:.1f} MW (seuil 62 MW)")
    if ctx["cat_gen"] is not None:
        lines.append(f"**Génération CAT :** {ctx['cat_gen']:.1f} MW (min. 70 MW)")
    if ctx["grid_import"] is not None:
        lines.append(f"**Import réseau :** {ctx['grid_import']:.1f} MW")

    anom_ids = {a["id"] for a in anom}
    linked   = [r for r in ctx["sorted_recommendations"]
                if _rec_attr(r, "linked_anomaly_id") in anom_ids]
    if linked:
        top_r = linked[0]
        lines.append(
            f"\n**Action prioritaire :** {_rec_attr(top_r, 'action_title')} "
            f"— Économie estimée {_fmt_xpf(_rec_attr(top_r, 'estimated_saving_xpf', 0))} XPF"
        )

    lines.append(_SAFETY_NOTE)
    return "\n".join(lines)


def _ans_air_7b(ctx: dict, question: str) -> str:
    # Filtrer : anomalies air avec référence 7b ou compresseurs C71x
    anom = [
        a for a in ctx["air_anomalies"]
        if ("7" in a.get("title", "") or "7" in a.get("asset", "")
            or any("C71" in s for s in a.get("affected_systems", [])))
    ]
    if not anom:
        anom = ctx["air_anomalies"]

    score = ctx["air_score"]
    p     = ctx["air_7b_pressure"]
    flow  = ctx["air_7b_flow"]
    se    = ctx["air_7b_se"]

    metrics: list[str] = []
    if p is not None:
        status_p = "⚠️ BASSE" if p < 6.55 else ("⚠️ LIMITE" if p < 6.65 else "✅ OK")
        metrics.append(f"- **Pression 7 bars :** {p:.3f} bar — {status_p} (min. 6.65 bar)")
    if flow is not None:
        metrics.append(f"- **Débit total :** {flow:.0f} Nm³/h")
    if se is not None:
        status_se = "⚠️ DÉGRADÉE" if se > 0.131 else "✅ OK"
        metrics.append(f"- **Énergie spécifique :** {se:.3f} kWh/Nm³ — {status_se} (max. 0.130)")
    for tag in ("C713", "C714", "C715", "C716", "C717"):
        val = ctx.get(f"{tag}_flow")
        if val is not None:
            flag = " ⚠️ BAS" if val < 1_500 else ""
            metrics.append(f"  - {tag} : {val:.0f} Nm³/h{flag}")

    if not anom:
        lines = [
            f"**Réseau air 7 bars (instrument) : Score {score:.0f}/100 — Nominal**\n",
            "Aucune anomalie détectée sur le réseau air instrument.",
        ]
        if metrics:
            lines.append("\n**Mesures actuelles :**")
            lines.extend(metrics)
        lines.append(_SAFETY_NOTE)
        return "\n".join(lines)

    lines = [f"**Réseau air 7 bars (instrument) : Score {score:.0f}/100**\n"]
    for a in anom:
        sev_fr = _SEVERITY_FR.get(a.get("severity", ""), a.get("severity", "").upper())
        lines.append(f"- [{sev_fr}] **{a.get('title', '')}** ({a.get('asset', '')})")
        lines.append(f"  _{a.get('description', '')}_")
        causes = a.get("probable_causes", [])
        if causes:
            lines.append(f"  _Causes probables :_ {causes[0]}")

    if metrics:
        lines.append("\n**Mesures :**")
        lines.extend(metrics)

    anom_ids = {a["id"] for a in anom}
    linked   = [r for r in ctx["sorted_recommendations"]
                if _rec_attr(r, "linked_anomaly_id") in anom_ids]
    if linked:
        top_r  = linked[0]
        detail = _rec_attr(top_r, "action_detail", "")
        lines.append(
            f"\n**Action prioritaire :** {_rec_attr(top_r, 'action_title')} "
            f"({_rec_attr(top_r, 'implementation_difficulty', '')})"
        )
        if detail:
            lines.append(f"_{detail[:150]}_")

    lines.append(_SAFETY_NOTE)
    return "\n".join(lines)


def _ans_air_3b(ctx: dict, question: str) -> str:
    anom = [
        a for a in ctx["air_anomalies"]
        if ("3" in a.get("title", "") or "3" in a.get("asset", "")
            or any("C32" in s or "C31" in s for s in a.get("affected_systems", [])))
    ]

    score  = ctx["air_score"]
    p      = ctx["air_3b_pressure"]
    speeds = {tag: ctx.get(f"{tag}_speed") for tag in ("C321", "C322", "C323")}
    speeds = {k: v for k, v in speeds.items() if v is not None}

    if not anom:
        lines = [
            f"**Réseau air 3 bars (process/poussières) : Score {score:.0f}/100 — Nominal**\n",
            "Aucune anomalie détectée sur le réseau air process.",
        ]
        if p is not None:
            lines.append(f"Pression 3 bars : {p:.3f} bar (min. 2.65 bar)")
        if speeds:
            vsd_str = " · ".join(f"{k} {v:.0f}%" for k, v in speeds.items())
            lines.append(f"Vitesses VSD : {vsd_str}")
        lines.append(_SAFETY_NOTE)
        return "\n".join(lines)

    lines = [f"**Réseau air 3 bars : Score {score:.0f}/100**\n"]
    for a in anom:
        sev_fr = _SEVERITY_FR.get(a.get("severity", ""), a.get("severity", "").upper())
        lines.append(f"- [{sev_fr}] **{a.get('title', '')}** ({a.get('asset', '')})")
        lines.append(f"  _{a.get('description', '')}_")
        causes = a.get("probable_causes", [])
        if causes:
            lines.append(f"  _Causes :_ {causes[0]}")

    if p is not None:
        status_p = "⚠️ BASSE" if p < 2.62 else ("⚠️ LIMITE" if p < 2.65 else "✅ OK")
        lines.append(f"\n**Pression 3 bars :** {p:.3f} bar — {status_p}")
    for tag, spd in speeds.items():
        flag = " ⚠️ SATURÉ" if spd >= 97 else ""
        lines.append(f"**{tag} :** {spd:.0f}%{flag}")

    lines.append(_SAFETY_NOTE)
    return "\n".join(lines)


def _ans_water(ctx: dict, question: str) -> str:
    anom    = ctx["water_anomalies"]
    score   = ctx["water_score"]
    rw_flow = ctx["rw_flow"]
    delta_t = ctx["rw_delta_t"]
    leg     = ctx["legionella"]
    b0      = ctx["basin_b0"]
    b1      = ctx["basin_b1"]

    if not anom:
        lines = [
            f"**Domaine eau : Score {score:.0f}/100 — Nominal**\n",
            "Aucune anomalie détectée sur les circuits eau.",
        ]
        if rw_flow is not None:
            lines.append(f"Débit eau recyclée : {rw_flow:.0f} m³/h (min. 1 800 m³/h)")
        if delta_t is not None:
            lines.append(f"ΔT recyclée : {delta_t:.1f} °C (max. 8 °C)")
        if leg is not None:
            status_leg = "⚠️ ÉLEVÉ" if leg > 0.65 else "✅ OK"
            lines.append(f"Indice légionelle : {leg:.2f} — {status_leg} (max. 0.65)")
        if b1 is not None:
            status_b1 = "⚠️ CRITIQUE" if b1 < 20 else "✅ OK"
            lines.append(f"Bassin B1 : {b1:.0f}% — {status_b1} (seuil critique 20%)")
        lines.append(_SAFETY_NOTE)
        return "\n".join(lines)

    lines = [f"**Domaine eau : Score {score:.0f}/100**\n"]
    for a in anom:
        sev_fr = _SEVERITY_FR.get(a.get("severity", ""), a.get("severity", "").upper())
        lines.append(f"- [{sev_fr}] **{a.get('title', '')}** ({a.get('asset', '')})")
        lines.append(f"  _{a.get('description', '')}_")
        causes = a.get("probable_causes", [])
        if causes:
            lines.append(f"  _Causes :_ {causes[0]}")

    if delta_t is not None:
        status_dt = "⚠️ ÉLEVÉ" if delta_t > 8 else "✅ OK"
        lines.append(f"\n**ΔT recyclée :** {delta_t:.1f} °C — {status_dt} (max. 8 °C)")
    if leg is not None:
        status_leg = "⚠️ RISQUE LÉGIONELLE" if leg > 0.65 else "✅ OK"
        lines.append(f"**Légionelle :** {leg:.2f} — {status_leg}")
    if b1 is not None:
        status_b1 = "⚠️ CRITIQUE" if b1 < 20 else ("⚠️ BAS" if b1 < 30 else "✅ OK")
        lines.append(f"**Bassin B1 :** {b1:.0f}% — {status_b1}")

    anom_ids = {a["id"] for a in anom}
    linked   = [r for r in ctx["sorted_recommendations"]
                if _rec_attr(r, "linked_anomaly_id") in anom_ids]
    if linked:
        top_r = linked[0]
        lines.append(f"\n**Action prioritaire :** {_rec_attr(top_r, 'action_title')}")
        sn = _rec_attr(top_r, "safety_note", "")
        if sn:
            lines.append(f"⚠️ {sn}")

    lines.append(_SAFETY_NOTE)
    return "\n".join(lines)


def _ans_recommendations(ctx: dict) -> str:
    recs = ctx["top_3_recs"]
    if not recs:
        return (
            "Aucune recommandation active. L'usine fonctionne normalement."
            + _SAFETY_NOTE
        )

    lines = [f"**Top {len(recs)} recommandation(s) prioritaire(s) :**\n"]
    for i, r in enumerate(recs, 1):
        prio_fr = _PRIORITY_FR.get(
            _rec_attr(r, "priority", ""), _rec_attr(r, "priority", "").upper()
        )
        saving = _rec_attr(r, "estimated_saving_xpf", 0)
        title  = _rec_attr(r, "action_title", "")
        detail = _rec_attr(r, "action_detail", "")
        effect = _rec_attr(r, "expected_effect", "")
        diff   = _rec_attr(r, "implementation_difficulty", "")

        lines.append(f"**{i}. [{prio_fr}] {title}**")
        if detail:
            lines.append(f"   _{detail[:130]}_")
        if effect:
            lines.append(f"   Effet attendu : {effect[:100]}")
        lines.append(
            f"   Économie : **{_fmt_xpf(saving)} XPF** · Difficulté : {diff}\n"
        )

    lines.append(_SAFETY_NOTE)
    return "\n".join(lines)


def _ans_business_impact(ctx: dict) -> str:
    total    = ctx["total_loss_xpf"]
    avoidable = ctx["avoidable_loss_xpf"]
    savings  = ctx["estimated_savings_xpf"]
    roi      = ctx["roi_summary"]

    if total == 0:
        return (
            "**Impact financier : Nominal**\n\n"
            "Aucune perte estimée. L'usine fonctionne sans anomalie active."
            + _SAFETY_NOTE
        )

    lines = [
        "**Synthèse financière des anomalies actives :**\n",
        f"- **Perte estimée totale :** {_fmt_xpf(total)} XPF",
        f"- **Perte évitable :** {_fmt_xpf(avoidable)} XPF",
        f"- **Économies potentielles :** {_fmt_xpf(savings)} XPF",
    ]

    if roi:
        lines.append(f"\n_{roi[:200]}_")

    top = ctx["top_anomaly"]
    if top:
        lines.append(
            f"\nPrincipal poste de coût : **{top.get('asset', '')}** "
            f"({_DOMAIN_FR.get(top.get('domain', ''), top.get('domain', ''))} — "
            f"{_SEVERITY_FR.get(top.get('severity', ''), '')})"
        )

    lines.append(_SAFETY_NOTE)
    return "\n".join(lines)


def _ans_scada_vs_ai(ctx: dict) -> str:
    top = ctx["top_anomaly"]
    n   = ctx["n_anomalies"]

    base = (
        "**Le SCADA montre ce qui se passe. "
        "L'IA explique pourquoi cela se passe et quoi faire.**\n\n"
        "| | SCADA | IA |\n"
        "|---|---|---|\n"
        "| Détection | Seuil individuel | Multi-signaux combinés |\n"
        "| Diagnostic | Alarme brute | Description explicable + causes |\n"
        "| Priorité | Manuelle / empirique | Score criticité automatique |\n"
        "| Impact financier | Non calculé | Chiffrage XPF en temps réel |\n"
        "| Action | Procédure papier | Recommandation avec ROI |\n"
    )

    if top:
        asset  = top.get("asset", "")
        domain = _DOMAIN_FR.get(top.get("domain", ""), "")
        desc   = top.get("description", "")
        causes = top.get("probable_causes", [])
        cause_str = f" ({causes[0]})" if causes else ""
        base += (
            f"\n**Exemple concret (scénario actif) :**\n"
            f"- **SCADA :** une alarme s'allume sur **{asset}** ({domain}).\n"
            f"- **IA :** _{desc}_{cause_str} "
            f"— diagnostic complet + chiffrage financier + actions recommandées."
        )
    elif n == 0:
        base += (
            "\n**Exemple typique (scénario fuite air 7 bars) :**\n"
            "- **SCADA :** pression 7 bars < 6.55 bar → alarme.\n"
            "- **IA :** la pression chute pendant que le débit et l'énergie spécifique "
            "augmentent → signature de fuite réseau → C713–C717 en surcharge compensatoire "
            "→ inspection réseau recommandée, perte estimée 180k XPF."
        )

    base += _SAFETY_NOTE
    return base


def _ans_safety(ctx: dict) -> str:
    return (
        "**Sécurité et limites du système :**\n\n"
        "Ce système est une **simulation pédagogique**. "
        "Il ne pilote aucun équipement industriel réel.\n\n"
        "**Principes appliqués :**\n"
        "- ✅ Toute action terrain requiert une **validation humaine** avant exécution.\n"
        "- ✅ L'IA assiste l'opérateur — elle ne le remplace pas.\n"
        "- ✅ Aucun ordre de démarrage ou d'arrêt n'est émis automatiquement.\n"
        "- ✅ Les données sont simulées à des fins de démonstration.\n"
        "- ✅ Le personnel qualifié garde la décision finale sur toute action corrective."
    )


def _ans_unknown(ctx: dict) -> str:
    n      = ctx["n_anomalies"]
    status = ctx["global_status"]
    hint   = (
        f"(Situation actuelle : {status}, {n} anomalie(s) active(s))"
        if n > 0
        else "(Situation actuelle : Nominal — aucune anomalie)"
    )

    return (
        f"Je n'ai pas reconnu la question. {hint}\n\n"
        "**Je peux répondre à :**\n"
        "- *Quel est l'état global de l'usine ?*\n"
        "- *Quelle est l'anomalie la plus critique ?*\n"
        "- *Que se passe-t-il sur l'air 7 bars / 3 bars ?*\n"
        "- *Quels problèmes sur l'électricité ?*\n"
        "- *Risques sur l'eau recyclée ?*\n"
        "- *Que recommande l'IA ?*\n"
        "- *Quel est l'impact financier en XPF ?*\n"
        "- *Quelle différence entre le SCADA et l'IA ?*\n"
        "- *Quelles sont les règles de sécurité ?*"
    )


# ---------------------------------------------------------------------------
# 4. Dispatcher principal
# ---------------------------------------------------------------------------

def generate_rule_based_answer(
    intent: str,
    question: str,
    context: dict[str, Any],
) -> str:
    """Génère une réponse Markdown à partir de l'intent et du contexte extrait."""
    handlers: dict[str, Any] = {
        "global_status":        lambda: _ans_global_status(context),
        "most_critical_anomaly": lambda: _ans_most_critical(context),
        "electricity":          lambda: _ans_electricity(context, question),
        "air_7b":               lambda: _ans_air_7b(context, question),
        "air_3b":               lambda: _ans_air_3b(context, question),
        "water":                lambda: _ans_water(context, question),
        "recommendations":      lambda: _ans_recommendations(context),
        "business_impact":      lambda: _ans_business_impact(context),
        "scada_vs_ai":          lambda: _ans_scada_vs_ai(context),
        "safety":               lambda: _ans_safety(context),
        "unknown":              lambda: _ans_unknown(context),
    }
    return handlers.get(intent, handlers["unknown"])()


def answer_user_question(
    question: str,
    df: pd.DataFrame,
    anomalies: list[Anomaly],
    recommendations: list[Recommendation],
    scoring_summary: dict[str, Any],
    business_summary: dict[str, Any],
) -> str:
    """
    Point d'entrée principal du chatbot industriel.

    1. Classifie l'intent de la question
    2. Construit le contexte depuis toutes les sources de données
    3. Génère la réponse rule-based en Markdown

    Ne lève jamais d'exception — retourne un message d'erreur propre en cas de problème.
    """
    try:
        intent  = classify_question_intent(question)
        context = build_context_summary(
            df=df,
            anomalies=anomalies,
            recommendations=recommendations,
            scoring_summary=scoring_summary,
            business_summary=business_summary,
        )
        return generate_rule_based_answer(intent, question, context)
    except Exception as exc:
        return (
            f"Une erreur inattendue s'est produite : {exc}\n"
            "Vérifiez les données de session et réessayez."
        )


# ---------------------------------------------------------------------------
# Quick prompts — boutons prédéfinis pour l'interface Streamlit
# ---------------------------------------------------------------------------

QUICK_PROMPTS: list[dict[str, str]] = [
    {
        "label":  "État global",
        "prompt": "Quel est l'état global de l'usine ?",
    },
    {
        "label":  "Anomalie critique",
        "prompt": "Quelle est l'anomalie la plus critique ?",
    },
    {
        "label":  "Recommandations",
        "prompt": "Que recommande l'IA ?",
    },
    {
        "label":  "Impact XPF",
        "prompt": "Combien coûte le problème en XPF ?",
    },
    {
        "label":  "SCADA vs IA",
        "prompt": "Quelle est la différence entre le SCADA et l'IA ?",
    },
]
