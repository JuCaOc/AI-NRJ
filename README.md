# AI Energy & Utilities Control Room

Prototype de supervision industrielle augmentée par l'IA.  
Application Streamlit de démonstration pédagogique.

---

## Objectif

Montrer comment une IA peut superviser une usine, détecter des anomalies,  
expliquer les causes, proposer des actions correctives et estimer leur impact économique.

| Sans IA | Avec IA |
|---------|---------|
| L'utilisateur voit des courbes | Il comprend, anticipe et décide |

---

## Contexte industriel simulé

### Électricité
- **63 kV** — poste source (réseau externe + centrale CAT)
- **15 kV** — force motrice (distribution sous-stations)
- **5,5 kV** — gros moteurs (compresseurs, pompes eau salée, pompes MPC)
- **400 V** — auxiliaires

### Air 7 bars (instrumentation)
Compresseurs : C713, C714, C715, C716, C717  
Rôle : air instrument + air de barrage — criticité procédé élevée

### Air 3 bars (transport poussières / charbon)
- Variables : C321, C322, C323
- Fixes : C311, C312  
Règle : les variables absorbent la demande, les fixes n'interviennent qu'en complément

### Eau recyclée
Refroidissement fours + équipements, tours aéroréfrigérantes, traitement anti-légionelle

### Eau brute
Eau d'appoint, bassins B0 et B1 — secours refroidissement + sécurité industrielle

---

## Architecture

```
AI-Energy-Control-Room/
├── app.py                        # Point d'entrée Streamlit
├── requirements.txt
├── README.md
│
├── modules/
│   ├── data_generator.py         # Génération données mockées (seed reproductible)
│   ├── scenarios.py              # Scénarios industriels simulés
│   ├── detection.py              # Détection anomalies rule-based
│   ├── scoring.py                # Scoring criticité
│   ├── recommendations.py        # Recommandations IA
│   ├── business_value.py         # Estimation impact financier
│   ├── ai_assistant.py           # Chatbot industriel (simulé — Claude API optionnel, futur)
│   ├── recommendation_simulator.py  # Simulation actions correctives
│   ├── report_generator.py       # Rapport automatique (export PDF optionnel, futur)
│   └── ui_components.py          # Composants UI réutilisables
│
├── pages/
│   ├── 1_Overview.py             # Vue globale usine
│   ├── 2_Electricity.py          # Supervision électricité
│   ├── 3_Compressed_Air.py       # Supervision air comprimé
│   ├── 4_Water.py                # Supervision eau
│   ├── 5_AI_Detection.py         # Détection & analyse IA
│   ├── 6_Simulation.py           # Simulateur actions
│   └── 7_AI_Report.py            # Rapport IA automatique
│
├── tests/
│   ├── test_data_generator.py
│   ├── test_detection.py
│   ├── test_scoring.py
│   └── test_recommendations.py
│
└── assets/                       # Logos, icônes, styles CSS
```

---

## Installation

```bash
# Cloner le projet
git clone <repo>
cd AI-Energy-Control-Room

# Créer environnement virtuel
python -m venv .venv
source .venv/bin/activate      # Linux/Mac
.venv\Scripts\activate         # Windows

# Installer les dépendances
pip install -r requirements.txt

# Lancer l'application
streamlit run app.py
```

---

## Paramètres économiques

| Paramètre | Valeur |
|-----------|--------|
| Monnaie | **XPF — Franc Pacifique** |
| Coût électricité | **22 XPF/kWh** |
| Coût arrêt production | 1 790 000 XPF/h |
| Coût maintenance | 60 000 XPF/intervention |
| Eau | 300 XPF/m³ |

Configurables dans `modules/business_value.py` → `EconomicParameters`.

---

## Variables d'environnement (optionnel — module chatbot futur)

Le chatbot est simulé dans la version actuelle. La clé API ne sera nécessaire
qu'à partir du module d'intégration Claude API.

```env
# Copier .env.example en .env uniquement si vous activez le chatbot Claude
# cp .env.example .env
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Lancer les tests

```bash
pytest tests/ -v --cov=modules
```

---

## Philosophie IA

L'IA est **explicable**, **industrielle** et **prudente**.  
Elle ne pilote jamais directement — toute action passe par validation humaine.

---

## Stack technique

- Python 3.11+
- Streamlit
- Pandas / NumPy
- Plotly
- Anthropic Claude API *(optionnel — chatbot industriel, module futur)*
- fpdf2 *(optionnel — export PDF, module futur)*
