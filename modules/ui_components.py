"""
Composants UI réutilisables — AI Energy & Utilities Control Room.
Style industriel, dark theme, prêt pour démonstration.
"""

import numpy as np
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, timedelta

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
