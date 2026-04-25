"""Page 7 — Rapport IA automatique : synthèse exportable de la session de supervision."""

import streamlit as st
from datetime import datetime

st.set_page_config(
    page_title="Rapport IA | AI Energy CR",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

from modules.ui_components import (
    inject_custom_css,
    render_sidebar,
    render_header,
    render_kpi_card,
    render_status_badge,
    render_section_title,
    render_info_banner,
    render_placeholder,
)

inject_custom_css()
render_sidebar()

# ─────────────────────────────────────────────────────────────
# Rapport markdown placeholder
# ─────────────────────────────────────────────────────────────

_REPORT_MD = f"""
# Rapport de Supervision IA — Session du {datetime.now().strftime("%d/%m/%Y %H:%M")}

**Usine :** Site de démonstration · **Mode :** Simulation · **Scénario :** Nominal avec anomalies

---

## 1. Résumé Exécutif

| Indicateur | Valeur |
|------------|--------|
| Niveau d'alerte global | 🟠 ALERTE |
| Anomalies actives | 3 |
| Exposition financière | 895 000 XPF/j |
| Systèmes dégradés | Air 7 bars, Électricité 15 kV |
| Systèmes nominaux | Eau recyclée, Eau brute |

**Synthèse :** Le réseau air 7 bars présente une dégradation de pression liée
à l'état du compresseur C715. Le réseau électrique 15 kV montre une légère
sous-tension. Ces deux anomalies combinées représentent un risque opérationnel
élevé si non corrigées dans les 2 prochaines heures.

---

## 2. État des Systèmes

| Système | Santé | Statut | Anomalies |
|---------|-------|--------|-----------|
| Électricité 63 kV | 94 % | 🟢 OK | 0 |
| Électricité 15 kV | 71 % | 🟡 ATTENTION | 1 |
| Air 7 bars | 52 % | 🔴 ALERTE | 1 |
| Air 3 bars | 78 % | 🟡 ATTENTION | 1 |
| Eau recyclée | 88 % | 🟢 OK | 0 |
| Eau brute | 85 % | 🟢 OK | 0 |

---

## 3. Anomalies Priorisées

### 🔴 [CRITIQUE · Score 88] — Chute pression 7 bars
- **Équipement :** C715 → réseau air instrumentation
- **Valeur observée :** 6,4 bar · **Attendue :** ≥ 7,0 bar
- **Règle :** PRESS_7BAR_LOW · **Depuis :** 23 minutes
- **Impact :** Risque sur stabilité procédé et air de barrage
- **Coût si non corrigé :** ~537 000 XPF/j

### 🟠 [ÉLEVÉE · Score 62] — Tension 15 kV sous-consigne
- **Équipement :** 15 kV bus A
- **Valeur observée :** 14,2 kV · **Attendue :** 15,0 ±0,3 kV
- **Règle :** VOLT_15KV_LOW · **Depuis :** 1 h 15
- **Impact :** Réduction performance moteurs, risque sur sous-stations
- **Coût si non corrigé :** ~250 000 XPF/j

### 🟡 [MOYENNE · Score 34] — Conductivité eau recyclée
- **Équipement :** Circuit primaire eau recyclée
- **Valeur observée :** 620 µS/cm · **Seuil :** 500 µS/cm
- **Règle :** COND_HIGH · **Depuis :** 3 h 42
- **Impact :** Risque entartrage échangeurs + efficacité refroidissement
- **Coût si non corrigé :** ~107 000 XPF/j

---

## 4. Recommandations

1. **[< 30 min]** Démarrer C716 en secours + diagnostic C715 (purges, aubes)
2. **[< 2 h]** Contacter dispatching réseau · Réduire charge moteurs 5,5 kV non critiques
3. **[< 4 h]** Analyser eau de compensation · Augmenter fréquence traitement

---

## 5. Impact Financier

| Poste | Coût journalier estimé |
|-------|------------------------|
| Air 7 bars (C715) | 537 000 XPF |
| Tension 15 kV | 250 000 XPF |
| Conductivité recyclée | 107 000 XPF |
| **TOTAL** | **895 000 XPF/j** |

*Retour sur correction estimé : < 1 heure pour les actions prioritaires.*

---

*Rapport généré automatiquement — Valider avec l'opérateur de quart avant toute action.*
"""


# ─────────────────────────────────────────────────────────────
# Page
# ─────────────────────────────────────────────────────────────

def render() -> None:
    render_header(
        title="Rapport IA Automatique",
        subtitle="Synthèse de la session de supervision · Export PDF · Notes opérateur",
        icon="📊",
    )
    render_info_banner(
        "Le rapport est généré automatiquement à partir de l'état courant des systèmes, "
        "des anomalies détectées et des recommandations IA. "
        "Module <strong>report_generator.py</strong> à connecter."
    )

    # ── KPIs rapport ──────────────────────────────────────────
    render_section_title("Métriques de la session", "📊")
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi_card("Anomalies détectées", "3",       "",       status="warning")
    with k2:
        render_kpi_card("Niveau d'alerte",     "ALERTE",  "",       status="alert")
    with k3:
        render_kpi_card("Exposition totale",   "895 000",   "XPF/j", status="warning")
    with k4:
        render_kpi_card("Durée session",       "24 h",    "",       status="normal")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Rapport texte ─────────────────────────────────────────
    col_report, col_actions = st.columns([3, 1])

    with col_report:
        render_section_title("Rapport de session", "📄")

        tab_markdown, tab_preview = st.tabs(["✏️ Markdown brut", "👁️ Aperçu rendu"])
        with tab_preview:
            st.markdown(_REPORT_MD)
        with tab_markdown:
            st.code(_REPORT_MD, language="markdown")

    with col_actions:
        render_section_title("Actions", "🔧")

        st.markdown(
            '<div class="kpi-card normal" style="margin-bottom:12px;">'
            '  <div class="kpi-label">Export rapport</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.button("⬇️ Exporter PDF",      use_container_width=True, disabled=True)
        st.button("⬇️ Exporter Markdown", use_container_width=True, disabled=True)
        st.caption("Export actif après connexion de report_generator.py")

        st.markdown("---")
        render_section_title("Notes opérateur", "📝")
        notes = st.text_area(
            "Saisir vos observations :",
            placeholder="Ex : C715 arrêté pour maintenance préventive à 02h30. Reprise prévue 06h00.",
            height=180,
            label_visibility="collapsed",
        )
        st.button("💾 Sauvegarder notes", use_container_width=True, disabled=not notes)

        st.markdown("---")
        render_section_title("Paramètres économiques", "💰")
        st.number_input("Coût kWh (XPF)",          value=22, step=1)
        st.number_input("Coût arrêt prod. (XPF/h)", value=1_790_000, step=10_000)
        st.button("♻️ Recalculer rapport", use_container_width=True, disabled=True)

    # ── Structure du rapport à venir ──────────────────────────
    render_section_title("Structure du rapport complet (à venir)", "🗂️")
    sections = [
        ("1", "Résumé exécutif",         "Niveau d'alerte global · Chiffres clés · Synthèse"),
        ("2", "État des systèmes",        "Scores de santé · Tendances · Comparatif"),
        ("3", "Anomalies priorisées",     "Liste complète avec scores, règles déclenchées"),
        ("4", "Recommandations",          "Procédures pas à pas · Urgences · Bénéfices"),
        ("5", "Impact financier",         "Breakdown par système · Retour sur action"),
        ("6", "Simulation résultats",     "Comparatif avant/après pour actions appliquées"),
        ("7", "Notes & historique",       "Observations opérateur · Événements journée"),
    ]
    for num, title, desc in sections:
        with st.expander(f"Section {num} — {title}"):
            st.markdown(f"*{desc}*")
            render_placeholder(f"Sera peuplé par report_generator.py → {title.lower().replace(' ', '_')}")


render()
