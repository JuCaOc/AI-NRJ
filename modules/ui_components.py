"""
Composants UI réutilisables — AI Energy & Utilities Control Room.
Style industriel, dark theme, prêt pour démonstration.
"""

from __future__ import annotations

import numpy as np
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Any

# ─────────────────────────────────────────────────────────────
# Palette & configuration globale
# ─────────────────────────────────────────────────────────────

STATUS_COLORS: dict[str, str] = {
    "ok":       "#00C853",
    "warning":  "#FFB300",
    "alert":    "#FF6D00",
    "critical": "#D50000",
    "normal":   "#00B0FF",
    "info":     "#7B61FF",
}

CHART_COLORS: list[str] = [
    "#00B0FF", "#00C853", "#FFB300", "#FF6D00", "#D50000", "#7B61FF", "#E040FB",
]

PAGE_CONFIG: dict = dict(
    page_title="AI Energy Control Room",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────
# CSS industriel global
# ─────────────────────────────────────────────────────────────

_CSS = """
<style>
/* ── KPI Card ──────────────────────────────────────────────── */
.kpi-card {
    background: #161A23;
    border: 1px solid #2A2F3E;
    border-radius: 6px;
    padding: 14px 18px 12px;
    margin-bottom: 6px;
    min-height: 90px;
}
.kpi-card.ok       { border-left: 4px solid #00C853; }
.kpi-card.warning  { border-left: 4px solid #FFB300; }
.kpi-card.alert    { border-left: 4px solid #FF6D00; }
.kpi-card.critical { border-left: 4px solid #D50000; }
.kpi-card.normal   { border-left: 4px solid #00B0FF; }
.kpi-card.info     { border-left: 4px solid #7B61FF; }

.kpi-label {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    color: #6B7894;
    margin-bottom: 6px;
}
.kpi-value {
    font-size: 26px;
    font-weight: 700;
    color: #DDE3F0;
    font-family: 'Courier New', monospace;
    line-height: 1.15;
}
.kpi-unit {
    font-size: 13px;
    color: #6B7894;
    margin-left: 3px;
    font-weight: 400;
    font-family: inherit;
}
.kpi-delta-up   { font-size: 11px; color: #00C853; margin-top: 5px; }
.kpi-delta-down { font-size: 11px; color: #FF1744; margin-top: 5px; }
.kpi-delta-flat { font-size: 11px; color: #6B7894; margin-top: 5px; }

/* ── Status Badge ───────────────────────────────────────────── */
.badge {
    display: inline-block;
    padding: 2px 9px;
    border-radius: 10px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.8px;
    text-transform: uppercase;
}
.badge-ok       { background: rgba(0,200,83,.12);   color: #00C853; border: 1px solid rgba(0,200,83,.35);   }
.badge-warning  { background: rgba(255,179,0,.12);  color: #FFB300; border: 1px solid rgba(255,179,0,.35);  }
.badge-alert    { background: rgba(255,109,0,.12);  color: #FF6D00; border: 1px solid rgba(255,109,0,.35);  }
.badge-critical { background: rgba(213,0,0,.15);    color: #FF1744; border: 1px solid rgba(255,23,68,.35);  }
.badge-normal   { background: rgba(0,176,255,.12);  color: #00B0FF; border: 1px solid rgba(0,176,255,.35);  }
.badge-info     { background: rgba(123,97,255,.12); color: #7B61FF; border: 1px solid rgba(123,97,255,.35); }

/* ── Page Header ─────────────────────────────────────────────── */
.page-header {
    border-bottom: 1px solid #2A2F3E;
    padding-bottom: 14px;
    margin-bottom: 20px;
}
.page-header-title {
    font-size: 22px;
    font-weight: 700;
    color: #DDE3F0;
    margin: 0 0 5px 0;
}
.page-header-sub {
    font-size: 13px;
    color: #6B7894;
    margin: 0;
}

/* ── Section Title ──────────────────────────────────────────── */
.section-title {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: #00B0FF;
    font-weight: 600;
    padding: 16px 0 8px 0;
    border-bottom: 1px solid #1E2331;
    margin-bottom: 14px;
}

/* ── Placeholder box ─────────────────────────────────────────── */
.ph-box {
    background: #161A23;
    border: 1px dashed #2A2F3E;
    border-radius: 6px;
    padding: 36px 20px;
    text-align: center;
    color: #3A4258;
    font-size: 12px;
    letter-spacing: 0.5px;
}

/* ── System tile (home) ─────────────────────────────────────── */
.sys-tile {
    background: #161A23;
    border: 1px solid #2A2F3E;
    border-radius: 8px;
    padding: 22px 16px 18px;
    text-align: center;
}
.sys-tile-icon { font-size: 30px; line-height: 1; }
.sys-tile-name { font-size: 13px; font-weight: 700; color: #DDE3F0; margin: 10px 0 4px 0; }
.sys-tile-desc { font-size: 11px; color: #6B7894; line-height: 1.4; margin-bottom: 10px; }

/* ── Sidebar legend item ─────────────────────────────────────── */
.legend-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 3px 0;
    font-size: 12px;
    color: #8892A4;
}

/* ── Info banner ─────────────────────────────────────────────── */
.info-banner {
    background: rgba(0,176,255,.07);
    border: 1px solid rgba(0,176,255,.25);
    border-radius: 6px;
    padding: 10px 16px;
    font-size: 12px;
    color: #8892A4;
    margin-bottom: 16px;
}

/* ── Misc ────────────────────────────────────────────────────── */
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
</style>
"""


def inject_custom_css() -> None:
    """Injecte le CSS industriel global dans la page courante."""
    st.markdown(_CSS, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Sidebar commune
# ─────────────────────────────────────────────────────────────

def render_sidebar() -> None:
    """Affiche le contenu commun de la barre latérale sur toutes les pages."""
    with st.sidebar:
        st.markdown("---")
        st.caption(f"🕒 {datetime.now().strftime('%d/%m/%Y  %H:%M:%S')}")
        st.markdown("**Mode** · Démonstration")
        st.markdown("---")
        st.markdown(
            "<span style='font-size:10px;letter-spacing:1.5px;text-transform:uppercase;"
            "color:#6B7894;'>Légende statuts</span>",
            unsafe_allow_html=True,
        )
        for status, label in [
            ("ok", "Nominal"),
            ("warning", "Attention"),
            ("alert", "Alerte"),
            ("critical", "Critique"),
        ]:
            st.markdown(
                f'<div class="legend-row">{render_status_badge(status, label)}</div>',
                unsafe_allow_html=True,
            )
        st.markdown("")
        st.caption("v0.1.0-alpha · Données simulées\nAucune connexion SCADA réelle")


# ─────────────────────────────────────────────────────────────
# Composants HTML
# ─────────────────────────────────────────────────────────────

def render_header(title: str, subtitle: str = "", icon: str = "") -> None:
    """Affiche l'en-tête standardisé d'une page avec titre et description."""
    icon_part = f"{icon}&nbsp;" if icon else ""
    sub_part  = f'<p class="page-header-sub">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f'<div class="page-header">'
        f'<p class="page-header-title">{icon_part}{title}</p>'
        f'{sub_part}'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_kpi_card(
    label: str,
    value: str,
    unit: str = "",
    delta: str | None = None,
    status: str = "normal",
) -> None:
    """Affiche une carte KPI avec valeur, unité, delta optionnel et couleur de statut."""
    if delta is None:
        delta_html = ""
    elif delta.startswith("+"):
        delta_html = f'<div class="kpi-delta-up">▲ {delta}</div>'
    elif delta.startswith("-"):
        delta_html = f'<div class="kpi-delta-down">▼ {delta}</div>'
    else:
        delta_html = f'<div class="kpi-delta-flat">● {delta}</div>'

    st.markdown(
        f'<div class="kpi-card {status}">'
        f'  <div class="kpi-label">{label}</div>'
        f'  <div class="kpi-value">{value}<span class="kpi-unit">{unit}</span></div>'
        f'  {delta_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_status_badge(status: str, text: str = "") -> str:
    """Retourne le HTML d'un badge coloré (à afficher via st.markdown unsafe_allow_html)."""
    _labels = {
        "ok":       "OK",
        "warning":  "ATTENTION",
        "alert":    "ALERTE",
        "critical": "CRITIQUE",
        "normal":   "NOMINAL",
        "info":     "INFO",
    }
    label = text or _labels.get(status, status.upper())
    return f'<span class="badge badge-{status}">{label}</span>'


def render_section_title(title: str, icon: str = "") -> None:
    """Affiche un titre de section en style industriel."""
    icon_part = f"{icon}&nbsp;&nbsp;" if icon else ""
    st.markdown(
        f'<div class="section-title">{icon_part}{title}</div>',
        unsafe_allow_html=True,
    )


def render_placeholder(text: str = "Module en cours de développement") -> None:
    """Affiche un bloc placeholder avec message."""
    st.markdown(f'<div class="ph-box">⬜&nbsp; {text}</div>', unsafe_allow_html=True)


def render_info_banner(text: str) -> None:
    """Affiche une bannière d'information discrète."""
    st.markdown(f'<div class="info-banner">ℹ️ &nbsp;{text}</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Graphiques Plotly
# ─────────────────────────────────────────────────────────────

_PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#0D1017",
    font=dict(color="#6B7894", size=11),
    margin=dict(l=50, r=20, t=40, b=40),
    xaxis=dict(gridcolor="#1C2030", showgrid=True, zeroline=False),
    yaxis=dict(gridcolor="#1C2030", showgrid=True, zeroline=False),
)


def placeholder_timeseries(
    title: str,
    y_label: str = "",
    n_series: int = 1,
    height: int = 280,
    seed: int = 42,
) -> go.Figure:
    """Génère une série temporelle factice reproductible pour affichage placeholder."""
    rng = np.random.default_rng(seed)
    n   = 288
    now = datetime.now()
    times = [now - timedelta(minutes=5 * (n - i)) for i in range(n)]

    fig = go.Figure()
    for i in range(n_series):
        phase = i * 1.3
        y = 50 + 12 * np.sin(np.linspace(0, 4 * np.pi, n) + phase) + rng.normal(0, 1.5, n)
        fig.add_trace(go.Scatter(
            x=times,
            y=y,
            mode="lines",
            line=dict(color=CHART_COLORS[i % len(CHART_COLORS)], width=1.5),
            name=f"Signal {i + 1}",
            hovertemplate="%{y:.1f}<extra></extra>",
        ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=12, color="#8892A4")),
        height=height,
        yaxis_title=y_label,
        showlegend=n_series > 1,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
        **_PLOTLY_LAYOUT,
    )
    return fig


def placeholder_gauge(
    title: str,
    value: float = 72.0,
    min_val: float = 0.0,
    max_val: float = 100.0,
    unit: str = "%",
    height: int = 210,
    warn_threshold: float | None = None,
) -> go.Figure:
    """Génère une jauge factice pour affichage placeholder."""
    warn = warn_threshold if warn_threshold is not None else max_val * 0.80

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number=dict(suffix=f" {unit}", font=dict(color="#DDE3F0", size=22)),
        gauge=dict(
            axis=dict(range=[min_val, max_val], tickfont=dict(color="#6B7894")),
            bar=dict(color="#00B0FF", thickness=0.25),
            bgcolor="#161A23",
            bordercolor="#2A2F3E",
            steps=[
                dict(range=[min_val,          max_val * 0.60], color="rgba(0,200,83,.07)"),
                dict(range=[max_val * 0.60,   warn],           color="rgba(255,179,0,.07)"),
                dict(range=[warn,              max_val],        color="rgba(213,0,0,.08)"),
            ],
            threshold=dict(
                line=dict(color="#FFB300", width=2),
                thickness=0.75,
                value=warn,
            ),
        ),
        title=dict(text=title, font=dict(color="#8892A4", size=12)),
    ))
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=30, b=10),
    )
    return fig


# ─────────────────────────────────────────────────────────────
# Helpers utilitaires
# ─────────────────────────────────────────────────────────────

SEVERITY_CSS: dict[str, str] = {
    "critical": "critical",
    "high":     "alert",
    "medium":   "warning",
    "low":      "ok",
}

SEVERITY_COLORS: dict[str, str] = {
    "critical": "#D50000",
    "high":     "#FF6D00",
    "medium":   "#FFB300",
    "low":      "#00C853",
}

DOMAIN_ICONS: dict[str, str] = {
    "electricity": "⚡",
    "air":         "💨",
    "water":       "♻️",
}


def fmt_xpf(v: float) -> str:
    if abs(v) >= 1_000_000:
        return f"{v / 1_000_000:.1f}M"
    if abs(v) >= 1_000:
        return f"{v / 1_000:.0f}k"
    return f"{v:.0f}"


def score_to_status(score: float) -> str:
    if score < 20:
        return "ok"
    if score < 45:
        return "warning"
    if score < 75:
        return "alert"
    return "critical"


def plant_status_css(label: str) -> str:
    return {"NORMAL": "ok", "VIGILANCE": "warning", "ALERTE": "alert", "CRITIQUE": "critical"}.get(label, "normal")


def severity_badge(severity: str) -> str:
    css = SEVERITY_CSS.get(severity, "normal")
    return render_status_badge(css, severity.upper())


# ─────────────────────────────────────────────────────────────
# Graphiques depuis DataFrame réel
# ─────────────────────────────────────────────────────────────

def _anomaly_relevant_for(domain: str | bool | None) -> bool:
    """
    Vrai si la zone d'anomalie doit être dessinée pour ce graphique.
      - None / False  → jamais
      - True          → toujours (rétro-compatible)
      - str (domaine) → seulement si une anomalie de ce domaine est active.
    """
    if not domain:
        return False
    if domain is True:
        return True
    anomalies = st.session_state.get("anomalies", []) or []
    return any(a.get("domain") == domain for a in anomalies)


def make_timeseries(
    df: Any,
    series: list[dict],
    title: str = "",
    y_label: str = "",
    height: int = 280,
    shade_anomaly: bool | str = False,
    thresholds: list[dict] | None = None,
) -> go.Figure:
    """
    Crée un graphique Plotly depuis un DataFrame réel.

    series : list of dicts with keys:
        col   – nom de la colonne DataFrame
        name  – label légende (opt)
        color – couleur hex (opt, auto-assignée sinon)
        dash  – "solid"|"dash"|"dot" (opt, défaut solid)
    shade_anomaly :
        False / None : jamais ombré
        True         : ombré si anomaly_flag présent (rétro-compat)
        "electricity"|"air"|"water" : ombré uniquement si l'anomalie active
        appartient à ce domaine.
    thresholds : list of {"value": float, "name": str, "color": str (opt)}
    """
    fig = go.Figure()
    for i, s in enumerate(series):
        col = s["col"]
        if col not in df.columns:
            continue
        color = s.get("color", CHART_COLORS[i % len(CHART_COLORS)])
        dash  = s.get("dash", "solid")
        name  = s.get("name", col)
        fig.add_trace(go.Scatter(
            x=df["timestamp"],
            y=df[col],
            mode="lines",
            name=name,
            line=dict(color=color, width=1.6, dash=dash),
            hovertemplate=f"<b>{name}</b>: %{{y:.2f}}<br>%{{x|%H:%M}}<extra></extra>",
        ))

    if _anomaly_relevant_for(shade_anomaly) and "anomaly_flag" in df.columns:
        rows = df[df["anomaly_flag"].astype(bool)]
        if not rows.empty:
            fig.add_vrect(
                x0=str(rows["timestamp"].iloc[0]),
                x1=str(rows["timestamp"].iloc[-1]),
                fillcolor="rgba(255,109,0,0.09)",
                layer="below",
                line_width=0,
                annotation_text="Anomalie détectée",
                annotation_position="top left",
                annotation_font=dict(color="#FF6D00", size=9),
            )

    for thr in (thresholds or []):
        fig.add_hline(
            y=thr["value"],
            line_dash="dash",
            line_color=thr.get("color", "#FFB300"),
            line_width=1,
            annotation_text=thr.get("name", f"{thr['value']}"),
            annotation_position="top right",
            annotation_font=dict(color=thr.get("color", "#FFB300"), size=9),
        )

    fig.update_layout(
        title=dict(text=title, font=dict(size=12, color="#8892A4")),
        height=height,
        yaxis_title=y_label,
        showlegend=len(series) > 1,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10), orientation="h", y=1.06, x=0),
        **_PLOTLY_LAYOUT,
    )
    return fig


def make_comparison_chart(
    df_nom: Any,
    df_cur: Any,
    col: str,
    title: str = "",
    y_label: str = "",
    height: int = 300,
    anomaly_domain: str | None = None,
) -> go.Figure:
    """
    Superpose la courbe nominale et la courbe courante pour comparaison.
    Si anomaly_domain est précisé (electricity|air|water), la zone d'anomalie
    n'est dessinée que si une anomalie de ce domaine est active.
    Sinon, fallback sur le comportement historique (toute anomaly_flag présente).
    """
    fig = go.Figure()
    if col in df_nom.columns:
        fig.add_trace(go.Scatter(
            x=df_nom["timestamp"], y=df_nom[col],
            mode="lines", name="Nominal",
            line=dict(color="#6B7894", width=1.4, dash="dot"),
        ))
    if col in df_cur.columns:
        # Présence d'anomalie pertinente : domaine ciblé si fourni, sinon legacy
        if anomaly_domain is not None:
            relevant = _anomaly_relevant_for(anomaly_domain)
        else:
            relevant = "anomaly_flag" in df_cur.columns and bool(df_cur["anomaly_flag"].any())
        color = "#FF6D00" if relevant else "#00B0FF"
        fig.add_trace(go.Scatter(
            x=df_cur["timestamp"], y=df_cur[col],
            mode="lines", name="Scénario actif",
            line=dict(color=color, width=2.0),
        ))
        if relevant and "anomaly_flag" in df_cur.columns:
            rows = df_cur[df_cur["anomaly_flag"].astype(bool)]
            if not rows.empty:
                fig.add_vrect(
                    x0=str(rows["timestamp"].iloc[0]),
                    x1=str(rows["timestamp"].iloc[-1]),
                    fillcolor="rgba(255,109,0,0.09)",
                    layer="below", line_width=0,
                    annotation_text="Fenêtre anomalie",
                    annotation_position="top left",
                    annotation_font=dict(color="#FF6D00", size=9),
                )

    fig.update_layout(
        title=dict(text=title, font=dict(size=12, color="#8892A4")),
        height=height,
        yaxis_title=y_label,
        showlegend=True,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=10), orientation="h", y=1.06, x=0),
        **_PLOTLY_LAYOUT,
    )
    return fig


def make_domain_score_bar(scoring_summary: dict, height: int = 240) -> go.Figure:
    """Graphique à barres des scores par domaine."""
    domain_scores = scoring_summary.get("domain_scores", {})
    labels = {
        "electricity_score": "Electricité",
        "air_score":         "Air comprimé",
        "water_score":       "Eau",
    }
    names  = [labels.get(k, k) for k in ["electricity_score", "air_score", "water_score"]]
    values = [domain_scores.get(k, 0.0) for k in ["electricity_score", "air_score", "water_score"]]
    colors = [SEVERITY_COLORS.get(score_to_status(v).replace("ok","low").replace("warning","medium").replace("alert","high").replace("critical","critical"), "#00C853")
              if v >= 75 else ("#FF6D00" if v >= 45 else ("#FFB300" if v >= 20 else "#00C853"))
              for v in values]

    fig = go.Figure(go.Bar(
        x=names, y=values,
        marker_color=colors,
        text=[f"{v:.0f}" for v in values],
        textposition="outside",
        textfont=dict(color="#DDE3F0", size=12),
    ))
    fig.add_hline(y=75, line_dash="dash", line_color="#D50000", line_width=1,
                  annotation_text="Critique", annotation_font=dict(color="#D50000", size=9))
    fig.add_hline(y=45, line_dash="dash", line_color="#FF6D00", line_width=1,
                  annotation_text="Alerte", annotation_font=dict(color="#FF6D00", size=9))
    fig.update_layout(
        title=dict(text="Score de criticité par domaine", font=dict(size=12, color="#8892A4")),
        height=height,
        yaxis=dict(range=[0, 110], tickfont=dict(color="#6B7894"), gridcolor="#1C2030"),
        xaxis=dict(tickfont=dict(color="#DDE3F0")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#0D1017",
        margin=dict(l=20, r=20, t=40, b=20),
        showlegend=False,
    )
    return fig


# ─────────────────────────────────────────────────────────────
# Sidebar avec sélecteur de scénario
# ─────────────────────────────────────────────────────────────

_SCENARIO_FR: dict[str, str] = {
    "nominal":                   "Fonctionnement nominal",
    "pic_four_2":                "Pic four 2 (+28 %)",
    "perte_partielle_cat":       "Perte CAT partielle (~60 %)",
    "surcharge_15kv":            "Surcharge poste 15 kV",
    "fuite_air_7b":              "Fuite réseau air 7 bars",
    "defaut_c715":               "Défaut compresseur C715",
    "desequilibre_c7":           "Déséquilibre C713 / C714",
    "saturation_vsd_3b":         "Saturation VSD air 3 bars",
    "mauvaise_regulation_3b":    "Mauvaise régulation 3 bars",
    "defaut_refroidissement":    "Défaut refroidissement",
    "risque_legionelle":         "Risque légionelle",
    "baisse_bassin_b1":          "Baisse niveau bassin B1",
    "forte_dependance_eau_brute":"Forte dépendance eau brute",
    "multi_crise":               "Multi-crise (électricité + air + eau)",
}


def render_scenario_sidebar() -> None:
    """Sidebar complète avec sélecteur de scénario, score global et légende."""
    from modules.state_manager import ensure_state, _recompute
    from modules.scenarios import list_available_scenarios

    ensure_state()
    ss = st.session_state

    with st.sidebar:
        st.markdown(
            '<div style="font-size:17px;font-weight:700;color:#DDE3F0;margin-bottom:2px;">'
            '⚡ AI Energy Control Room</div>'
            '<div style="font-size:10px;color:#6B7894;letter-spacing:1.2px;'
            'text-transform:uppercase;margin-bottom:12px;">Démo industrielle</div>',
            unsafe_allow_html=True,
        )
        st.markdown("---")

        # ── Sélecteur de scénario ─────────────────────────────────────────
        scenario_list = [{"name": "nominal"}] + list_available_scenarios()
        names  = [s["name"] for s in scenario_list]
        labels = {n: _SCENARIO_FR.get(n, n) for n in names}

        current = ss.get("selected_scenario", "nominal")
        idx = names.index(current) if current in names else 0

        new_scenario = st.selectbox(
            "Scénario industriel",
            options=names,
            index=idx,
            format_func=lambda x: labels.get(x, x),
            help="Sélectionner une défaillance pour déclencher l'analyse IA",
            key="_sidebar_scenario_select",
        )

        if new_scenario != current:
            ss["selected_scenario"] = new_scenario
            _recompute()
            st.rerun()

        # Mode pill
        is_nominal = (new_scenario == "nominal")
        mode_color = "#00C853" if is_nominal else "#FF6D00"
        mode_text  = "Nominal" if is_nominal else "Démo IA — anomalie active"
        st.markdown(
            f'<div style="font-size:11px;color:{mode_color};font-weight:600;'
            f'margin:6px 0 10px 0;">● {mode_text}</div>',
            unsafe_allow_html=True,
        )

        if not is_nominal:
            desc = labels.get(new_scenario, "")
            st.markdown(
                f'<div style="background:rgba(255,109,0,.07);border:1px solid '
                f'rgba(255,109,0,.25);border-radius:5px;padding:8px 10px;'
                f'font-size:11px;color:#FF9950;margin-bottom:10px;">'
                f'⚠️ {desc}</div>',
                unsafe_allow_html=True,
            )

        # ── Score global ──────────────────────────────────────────────────
        scoring  = ss.get("scoring_summary", {})
        g_score  = scoring.get("global_score", 0.0)
        g_status = scoring.get("status", "NORMAL")
        s_css    = plant_status_css(g_status)
        s_color  = STATUS_COLORS.get(s_css, "#00C853")

        st.markdown("---")
        st.markdown(
            f'<div style="text-align:center;padding:8px 0;">'
            f'<div style="font-size:10px;text-transform:uppercase;letter-spacing:1px;'
            f'color:#6B7894;margin-bottom:4px;">Score criticité usine</div>'
            f'<div style="font-size:36px;font-weight:700;color:{s_color};'
            f'font-family:Courier New,monospace;">{g_score:.0f}</div>'
            f'<div style="font-size:12px;font-weight:600;color:{s_color};">{g_status}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # ── Légende ───────────────────────────────────────────────────────
        st.markdown("---")
        st.markdown(
            '<span style="font-size:10px;letter-spacing:1.5px;text-transform:uppercase;'
            'color:#6B7894;">Légende statuts</span>',
            unsafe_allow_html=True,
        )
        for sk, lbl in [("ok", "NORMAL"), ("warning", "VIGILANCE"),
                         ("alert", "ALERTE"), ("critical", "CRITIQUE")]:
            st.markdown(
                f'<div class="legend-row">{render_status_badge(sk, lbl)}</div>',
                unsafe_allow_html=True,
            )

        # ── Sécurité ─────────────────────────────────────────────────────
        st.markdown("")
        st.markdown(
            '<div style="background:rgba(213,0,0,.07);border:1px solid rgba(213,0,0,.2);'
            'border-radius:4px;padding:7px 10px;font-size:10px;color:#FF6B6B;'
            'line-height:1.5;margin-top:6px;">'
            '⚠️ Simulation uniquement<br>Aucune commande industrielle réelle.</div>',
            unsafe_allow_html=True,
        )
        st.caption(f"v0.2.0 · {datetime.now().strftime('%H:%M:%S')}")


# ─────────────────────────────────────────────────────────────
# Bloc pédagogique SCADA vs IA
# ─────────────────────────────────────────────────────────────

def render_scada_vs_ia(
    scada_points: list[str],
    ia_points: list[str],
    key_phrase: str = "Le SCADA montre ce qui se passe. L'IA explique pourquoi et quoi faire.",
) -> None:
    """Affiche le bloc comparatif SCADA classique vs IA."""
    scada_html = "".join(f'<li style="margin:3px 0;color:#8892A4;">{p}</li>' for p in scada_points)
    ia_html    = "".join(f'<li style="margin:3px 0;color:#8892A4;">{p}</li>' for p in ia_points)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f'<div style="background:#161A23;border:1px solid #2A2F3E;border-radius:6px;'
            f'padding:14px 16px;height:100%;">'
            f'<div style="font-size:10px;text-transform:uppercase;letter-spacing:1.5px;'
            f'color:#6B7894;margin-bottom:8px;">SCADA classique</div>'
            f'<ul style="margin:0;padding-left:16px;font-size:12px;">{scada_html}</ul>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(
            f'<div style="background:#0F1C2E;border:1px solid #1E3A5F;border-radius:6px;'
            f'padding:14px 16px;height:100%;">'
            f'<div style="font-size:10px;text-transform:uppercase;letter-spacing:1.5px;'
            f'color:#00B0FF;margin-bottom:8px;">IA (ce module)</div>'
            f'<ul style="margin:0;padding-left:16px;font-size:12px;">{ia_html}</ul>'
            f'</div>',
            unsafe_allow_html=True,
        )

    if key_phrase:
        st.markdown(
            f'<div style="background:rgba(0,176,255,.06);border:1px solid rgba(0,176,255,.2);'
            f'border-radius:6px;padding:12px 18px;margin-top:12px;text-align:center;'
            f'font-size:13px;font-style:italic;color:#00B0FF;">'
            f'"{key_phrase}"</div>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────
# Bloc IA : anomalies + recommandations + coût
# ─────────────────────────────────────────────────────────────

def render_ia_block(
    anomalies: list[dict],
    recommendations: list,
    business_summary: dict,
    domain_filter: str | None = None,
) -> None:
    """Affiche les anomalies, recommandations et coût pour un domaine donné."""
    filtered_anom = [a for a in anomalies if domain_filter is None or a.get("domain") == domain_filter]
    filtered_recs = [r for r in recommendations if domain_filter is None or any(
        a.get("id") == r.linked_anomaly_id for a in filtered_anom
    )]

    render_section_title("Analyse IA", "🤖")

    if not filtered_anom:
        st.success("Aucune anomalie détectée sur ce domaine. Fonctionnement nominal.")
        return

    # Anomalies
    st.markdown(
        f'<div style="font-size:11px;color:#6B7894;margin-bottom:8px;">'
        f'{len(filtered_anom)} anomalie(s) détectée(s)</div>',
        unsafe_allow_html=True,
    )
    for a in filtered_anom:
        sev_color = SEVERITY_COLORS.get(a.get("severity", "low"), "#00C853")
        st.markdown(
            f'<div style="background:#161A23;border-left:3px solid {sev_color};'
            f'border-radius:0 4px 4px 0;padding:10px 14px;margin-bottom:8px;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;">'
            f'<span style="font-size:13px;font-weight:600;color:#DDE3F0;">{a.get("title","")}</span>'
            f'{severity_badge(a.get("severity","low"))}'
            f'</div>'
            f'<div style="font-size:11px;color:#6B7894;margin-top:4px;">'
            f'{a.get("description","")[:120]}…'
            f'</div>'
            f'<div style="font-size:10px;color:#4A5268;margin-top:4px;">'
            f'Confiance : {a.get("confidence_score",0):.0%} | '
            f'{a.get("timestamp_start","")[:16]} → {a.get("timestamp_end","")[:16]}'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Recommandations
    if filtered_recs:
        render_section_title("Recommandations", "📋")
        for r in filtered_recs[:3]:
            prio_color = {"urgent": "#D50000", "high": "#FF6D00", "medium": "#FFB300", "low": "#00C853"}.get(r.priority, "#6B7894")
            st.markdown(
                f'<div style="background:#161A23;border:1px solid #2A2F3E;border-radius:5px;'
                f'padding:10px 14px;margin-bottom:6px;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                f'<span style="font-size:12px;font-weight:600;color:#DDE3F0;">{r.action_title}</span>'
                f'<span style="font-size:10px;font-weight:700;color:{prio_color};">{r.priority.upper()}</span>'
                f'</div>'
                f'<div style="font-size:11px;color:#6B7894;margin-top:3px;">{r.action_detail[:100]}…</div>'
                f'<div style="font-size:10px;color:#00C853;margin-top:4px;">'
                f'Économie estimée : {fmt_xpf(r.estimated_saving_xpf)} XPF</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # Coût estimé
    from modules.business_value import evaluate_anomaly_cost as _eval_cost
    total_loss = sum(_eval_cost(a)["estimated_loss_xpf"] for a in filtered_anom)
    if total_loss > 0:
        st.markdown(
            f'<div style="background:rgba(213,0,0,.07);border:1px solid rgba(213,0,0,.2);'
            f'border-radius:5px;padding:10px 16px;margin-top:6px;">'
            f'<span style="font-size:12px;color:#FF6B6B;">Perte estimée (domaine) : '
            f'<strong>{fmt_xpf(total_loss)} XPF</strong></span>'
            f'</div>',
            unsafe_allow_html=True,
        )
