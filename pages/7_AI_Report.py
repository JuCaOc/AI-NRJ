"""Page 7 — Rapport IA automatique : synthèse exportable de la session."""

import streamlit as st
from datetime import datetime
from modules.ui_components import (
    PAGE_CONFIG, inject_custom_css, render_scenario_sidebar,
    render_header, render_kpi_card, render_section_title, render_info_banner,
    score_to_status, plant_status_css, fmt_xpf,
    STATUS_COLORS, SEVERITY_COLORS, _SCENARIO_FR,
)
from modules.state_manager import ensure_state

st.set_page_config(**PAGE_CONFIG)
inject_custom_css()
ensure_state()
render_scenario_sidebar()

ss        = st.session_state
anomalies = ss.get("anomalies", [])
scoring   = ss.get("scoring_summary", {})
recs      = ss.get("recommendations", [])
biz       = ss.get("business_summary", {})
scenario  = ss.get("selected_scenario", "nominal")

g_score  = scoring.get("global_score", 0.0)
g_status = scoring.get("status", "NORMAL")
s_css    = plant_status_css(g_status)
s_color  = STATUS_COLORS.get(s_css, "#00C853")
scenario_label = _SCENARIO_FR.get(scenario, scenario)
now_str  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

render_header("Rapport IA", "Synthèse automatique de la session de supervision", "📄")

# ── KPIs rapport ──────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    render_kpi_card("Statut global", g_status, "", status=s_css)
with c2:
    render_kpi_card("Score criticité", f"{g_score:.0f}", "/ 100", status=s_css)
with c3:
    render_kpi_card("Anomalies", str(len(anomalies)), "",
                    status="alert" if anomalies else "ok")
with c4:
    render_kpi_card("Perte estimée", fmt_xpf(biz.get("total_loss_xpf", 0)), "XPF",
                    status="alert" if biz.get("total_loss_xpf", 0) > 500_000 else "ok")

# ── Résumé scénario ───────────────────────────────────────────────────────────
render_section_title("Résumé de session", "📋")

domain_scores = scoring.get("domain_scores", {})
st.markdown(
    f'<div style="background:#161A23;border:1px solid #2A2F3E;border-radius:6px;'
    f'padding:14px 18px;margin-bottom:12px;">'
    f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">'
    f'<div><span style="color:#6B7894;font-size:11px;">Date / Heure</span>'
    f'<div style="color:#DDE3F0;font-size:12px;">{now_str}</div></div>'
    f'<div><span style="color:#6B7894;font-size:11px;">Scénario actif</span>'
    f'<div style="color:#DDE3F0;font-size:12px;">{scenario_label}</div></div>'
    f'<div><span style="color:#6B7894;font-size:11px;">Statut usine</span>'
    f'<div style="color:{s_color};font-size:12px;font-weight:700;">{g_status}</div></div>'
    f'<div><span style="color:#6B7894;font-size:11px;">Score global</span>'
    f'<div style="color:{s_color};font-size:12px;font-weight:700;">{g_score:.0f} / 100</div></div>'
    f'<div><span style="color:#6B7894;font-size:11px;">Score électricité</span>'
    f'<div style="color:#DDE3F0;font-size:12px;">{domain_scores.get("electricity_score",0):.0f}</div></div>'
    f'<div><span style="color:#6B7894;font-size:11px;">Score air</span>'
    f'<div style="color:#DDE3F0;font-size:12px;">{domain_scores.get("air_score",0):.0f}</div></div>'
    f'<div><span style="color:#6B7894;font-size:11px;">Score eau</span>'
    f'<div style="color:#DDE3F0;font-size:12px;">{domain_scores.get("water_score",0):.0f}</div></div>'
    f'<div><span style="color:#6B7894;font-size:11px;">Économies potentielles</span>'
    f'<div style="color:#00C853;font-size:12px;font-weight:700;">'
    f'{fmt_xpf(biz.get("estimated_savings_xpf",0))} XPF</div></div>'
    f'</div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── Anomalies ─────────────────────────────────────────────────────────────────
render_section_title("Anomalies détectées", "🚨")

if not anomalies:
    st.success("Aucune anomalie. Fonctionnement nominal.")
else:
    for a in sorted(anomalies, key=lambda x: x.get("confidence_score", 0), reverse=True):
        sc = SEVERITY_COLORS.get(a.get("severity", "low"), "#6B7894")
        st.markdown(
            f'<div style="background:#161A23;border-left:3px solid {sc};'
            f'border-radius:0 5px 5px 0;padding:10px 14px;margin-bottom:6px;">'
            f'<div style="display:flex;justify-content:space-between;">'
            f'<span style="font-size:13px;font-weight:600;color:#DDE3F0;">{a.get("title","")}</span>'
            f'<span style="font-size:11px;font-weight:700;color:{sc};">'
            f'{a.get("severity","").upper()}</span>'
            f'</div>'
            f'<div style="font-size:11px;color:#6B7894;margin-top:3px;">'
            f'{a.get("asset","")} · {a.get("domain","").upper()} · '
            f'Confiance {a.get("confidence_score",0):.0%}</div>'
            f'<div style="font-size:11px;color:#8892A4;margin-top:3px;">{a.get("description","")}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ── Recommandations ───────────────────────────────────────────────────────────
render_section_title("Recommandations prioritaires", "📋")

if not recs:
    st.info("Aucune recommandation pour le scénario en cours.")
else:
    for r in recs[:6]:
        pc = {"urgent": "#D50000", "high": "#FF6D00", "medium": "#FFB300", "low": "#00C853"}.get(r.priority, "#6B7894")
        st.markdown(
            f'<div style="background:#161A23;border:1px solid #2A2F3E;border-radius:5px;'
            f'padding:10px 14px;margin-bottom:6px;">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;">'
            f'<span style="font-size:12px;font-weight:600;color:#DDE3F0;">{r.action_title}</span>'
            f'<div>'
            f'<span style="font-size:11px;font-weight:700;color:{pc};">{r.priority.upper()}</span>'
            f'<span style="font-size:11px;color:#00C853;margin-left:12px;">'
            f'{fmt_xpf(r.estimated_saving_xpf)} XPF</span>'
            f'</div>'
            f'</div>'
            f'<div style="font-size:11px;color:#8892A4;margin-top:4px;">{r.action_detail[:120]}</div>'
            f'<div style="font-size:10px;color:#6B7894;margin-top:3px;">'
            f'Difficulté : {r.implementation_difficulty} · '
            f'Réduction risque : {r.estimated_risk_reduction_pct:.0f} %</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ── ROI Summary ───────────────────────────────────────────────────────────────
render_section_title("Synthèse financière", "💰")
roi_text = biz.get("roi_summary", "")
if roi_text:
    render_info_banner(roi_text)
else:
    render_info_banner("Aucune perte estimée — fonctionnement nominal.")

# ── Note sécurité ─────────────────────────────────────────────────────────────
render_section_title("Note de sécurité", "⚠️")
st.markdown(
    '<div style="background:rgba(213,0,0,.07);border:1px solid rgba(213,0,0,.2);'
    'border-radius:5px;padding:12px 16px;font-size:12px;color:#FF6B6B;line-height:1.6;">'
    '<strong>SIMULATION UNIQUEMENT</strong><br>'
    'Ce rapport est généré à partir de données simulées à des fins de démonstration. '
    'Aucune commande industrielle réelle n\'est émise. '
    'Toute action corrective doit faire l\'objet d\'une validation humaine '
    'par le personnel qualifié avant exécution.'
    '</div>',
    unsafe_allow_html=True,
)

# ── Téléchargement rapport Markdown ──────────────────────────────────────────
render_section_title("Export rapport", "💾")

def _build_markdown_report() -> str:
    lines = [
        f"# Rapport IA — AI Energy & Utilities Control Room",
        f"",
        f"**Date :** {now_str}  ",
        f"**Scénario :** {scenario_label}  ",
        f"**Statut usine :** {g_status}  ",
        f"**Score global :** {g_score:.0f} / 100",
        f"",
        f"---",
        f"",
        f"## Scores par domaine",
        f"",
        f"| Domaine | Score |",
        f"|---------|-------|",
        f"| Électricité | {domain_scores.get('electricity_score',0):.0f} |",
        f"| Air comprimé | {domain_scores.get('air_score',0):.0f} |",
        f"| Eau | {domain_scores.get('water_score',0):.0f} |",
        f"",
        f"---",
        f"",
        f"## Anomalies détectées ({len(anomalies)})",
        f"",
    ]
    if anomalies:
        for a in sorted(anomalies, key=lambda x: x.get("confidence_score",0), reverse=True):
            lines += [
                f"### {a.get('title','')}",
                f"- **Sévérité :** {a.get('severity','').upper()}",
                f"- **Domaine :** {a.get('domain','').upper()}",
                f"- **Asset :** {a.get('asset','')}",
                f"- **Confiance :** {a.get('confidence_score',0):.1%}",
                f"- **Période :** {a.get('timestamp_start','')[:16]} → {a.get('timestamp_end','')[:16]}",
                f"- **Description :** {a.get('description','')}",
                f"",
                f"**Causes probables :**",
            ]
            for c in a.get("probable_causes", []):
                lines.append(f"- {c}")
            lines.append("")
    else:
        lines.append("_Aucune anomalie détectée._")
        lines.append("")

    lines += [
        f"---",
        f"",
        f"## Recommandations ({len(recs)})",
        f"",
    ]
    if recs:
        for r in recs[:6]:
            lines += [
                f"### [{r.priority.upper()}] {r.action_title}",
                f"- **Détail :** {r.action_detail}",
                f"- **Effet attendu :** {r.expected_effect}",
                f"- **Économie estimée :** {fmt_xpf(r.estimated_saving_xpf)} XPF",
                f"- **Réduction risque :** {r.estimated_risk_reduction_pct:.0f} %",
                f"- **Difficulté :** {r.implementation_difficulty}",
                f"- **Validation humaine :** {'Requise' if r.human_validation_required else 'Non requise'}",
                f"- **Sécurité :** {r.safety_note}",
                f"",
            ]
    else:
        lines.append("_Aucune recommandation._")
        lines.append("")

    lines += [
        f"---",
        f"",
        f"## Synthèse financière",
        f"",
        f"- **Perte estimée :** {fmt_xpf(biz.get('total_loss_xpf',0))} XPF",
        f"- **Perte évitable :** {fmt_xpf(biz.get('avoidable_loss_xpf',0))} XPF",
        f"- **Économies potentielles :** {fmt_xpf(biz.get('estimated_savings_xpf',0))} XPF",
        f"",
        biz.get("roi_summary", ""),
        f"",
        f"---",
        f"",
        f"## Note de sécurité",
        f"",
        f"> SIMULATION UNIQUEMENT. Ce rapport est généré à partir de données simulées.",
        f"> Toute action corrective requiert une validation humaine par le personnel qualifié.",
        f"",
        f"---",
        f"*Rapport généré par AI Energy & Utilities Control Room v0.2.0*",
    ]
    return "\n".join(lines)


report_md = _build_markdown_report()
st.download_button(
    label="📥 Télécharger le rapport (Markdown)",
    data=report_md,
    file_name=f"rapport_ia_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
    mime="text/markdown",
)

# Aperçu
with st.expander("Aperçu du rapport Markdown"):
    st.markdown(report_md)
