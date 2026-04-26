"""Page 5 — Détection IA : anomalies, scoring criticité, recommandations, chatbot."""

import streamlit as st
from modules.ui_components import (
    PAGE_CONFIG, inject_custom_css, render_scenario_sidebar,
    render_header, render_kpi_card, render_section_title,
    render_scada_vs_ia, severity_badge, score_to_status, plant_status_css,
    make_domain_score_bar, fmt_xpf, STATUS_COLORS, SEVERITY_COLORS,
)
from modules.state_manager import ensure_state
from modules.ai_assistant import answer_user_question, QUICK_PROMPTS

st.set_page_config(**PAGE_CONFIG)
inject_custom_css()
ensure_state()
render_scenario_sidebar()

ss        = st.session_state
anomalies = ss.get("anomalies", [])
scoring   = ss.get("scoring_summary", {})
recs      = ss.get("recommendations", [])
biz       = ss.get("business_summary", {})

g_score  = scoring.get("global_score", 0.0)
g_status = scoring.get("status", "NORMAL")

render_header("Détection IA", "Anomalies · Scoring criticité · Recommandations actionnables", "🤖")

# ── KPIs ──────────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
n_critical = sum(1 for a in anomalies if a.get("severity") == "critical")
total_loss = biz.get("total_loss_xpf", 0.0)
avg_conf   = (sum(a.get("confidence_score", 0) for a in anomalies) / len(anomalies)) if anomalies else 0.0

with c1:
    render_kpi_card("Anomalies détectées", str(len(anomalies)), "",
                    status="critical" if n_critical else ("alert" if anomalies else "ok"))
with c2:
    render_kpi_card("Critiques", str(n_critical), "",
                    status="critical" if n_critical else "ok")
with c3:
    render_kpi_card("Score global usine", f"{g_score:.0f}", "/ 100",
                    status=plant_status_css(g_status))
with c4:
    render_kpi_card("Perte totale estimée", fmt_xpf(total_loss), "XPF",
                    status="alert" if total_loss > 500_000 else ("warning" if total_loss > 0 else "ok"))

# ── Bloc pédagogique ─────────────────────────────────────────────────────────
render_section_title("SCADA vs IA — Comment fonctionne la détection", "🆚")
render_scada_vs_ia(
    scada_points=[
        "Alarme déclenchée : seuil individuel dépassé",
        "Pas de contexte ni de corrélation",
        "L'opérateur reçoit une liste d'alarmes brutes",
        "Priorité manuelle, interprétation empirique",
    ],
    ia_points=[
        "Combine plusieurs signaux pour confirmer une anomalie",
        "Calcule un score de confiance (0–100 %)",
        "Produit une description explicable et des causes probables",
        "Priorise par criticité + impact financier",
        "Suggère des actions avec estimation de ROI",
    ],
    key_phrase="Le SCADA détecte un seuil. L'IA détecte une combinaison de signaux et produit un diagnostic.",
)

# ── Tableau anomalies ─────────────────────────────────────────────────────────
render_section_title("Anomalies actives", "🚨")

if not anomalies:
    st.success(
        "Aucune anomalie détectée. Fonctionnement nominal. "
        "Sélectionnez un scénario dans la barre latérale pour déclencher l'analyse."
    )
else:
    # Sélecteur d'anomalie détaillée
    anom_titles = [f"[{a['severity'].upper()}] {a['title']} — {a['asset']}" for a in anomalies]
    selected_idx = st.selectbox(
        "Sélectionner une anomalie pour voir le détail",
        range(len(anom_titles)),
        format_func=lambda i: anom_titles[i],
    )

    # Tableau récapitulatif
    st.markdown(
        '<div style="background:#161A23;border:1px solid #2A2F3E;border-radius:6px;'
        'overflow:hidden;margin-bottom:12px;">',
        unsafe_allow_html=True,
    )
    header_html = (
        '<div style="display:grid;grid-template-columns:90px 80px 1fr 90px 80px;'
        'gap:8px;padding:8px 14px;border-bottom:1px solid #2A2F3E;">'
        '<span style="font-size:10px;text-transform:uppercase;color:#6B7894;">Sévérité</span>'
        '<span style="font-size:10px;text-transform:uppercase;color:#6B7894;">Domaine</span>'
        '<span style="font-size:10px;text-transform:uppercase;color:#6B7894;">Titre</span>'
        '<span style="font-size:10px;text-transform:uppercase;color:#6B7894;">Confiance</span>'
        '<span style="font-size:10px;text-transform:uppercase;color:#6B7894;">Début</span>'
        '</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)

    for i, a in enumerate(anomalies):
        bg = "rgba(255,109,0,0.05)" if i == selected_idx else "transparent"
        sc = SEVERITY_COLORS.get(a.get("severity","low"), "#6B7894")
        ts = a.get("timestamp_start", "")[:16]
        st.markdown(
            f'<div style="display:grid;grid-template-columns:90px 80px 1fr 90px 80px;'
            f'gap:8px;padding:8px 14px;border-bottom:1px solid #1C2130;background:{bg};">'
            f'<span>{severity_badge(a.get("severity","low"))}</span>'
            f'<span style="font-size:11px;color:#8892A4;">{a.get("domain","").upper()}</span>'
            f'<span style="font-size:12px;color:#DDE3F0;">{a.get("title","")}</span>'
            f'<span style="font-size:12px;color:#00B0FF;">{a.get("confidence_score",0):.0%}</span>'
            f'<span style="font-size:11px;color:#6B7894;">{ts}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    # Détail de l'anomalie sélectionnée
    a = anomalies[selected_idx]
    render_section_title(f"Détail : {a['title']}", "🔍")

    sc = SEVERITY_COLORS.get(a.get("severity","low"), "#6B7894")
    st.markdown(
        f'<div style="background:#161A23;border-left:4px solid {sc};'
        f'border-radius:0 6px 6px 0;padding:14px 18px;margin-bottom:12px;">'
        f'<div style="font-size:10px;text-transform:uppercase;letter-spacing:1px;'
        f'color:#6B7894;margin-bottom:6px;">{a.get("domain","").upper()} · '
        f'{a.get("asset","")}</div>'
        f'<div style="font-size:13px;color:#DDE3F0;margin-bottom:8px;">{a.get("description","")}</div>'
        f'<div style="font-size:11px;color:#6B7894;">'
        f'{a.get("timestamp_start","")[:16]} → {a.get("timestamp_end","")[:16]} · '
        f'Confiance : {a.get("confidence_score",0):.1%}'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns(2)

    with col_left:
        # Preuves chiffrées
        st.markdown('<div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;'
                    'color:#6B7894;margin-bottom:6px;">Preuves chiffrées</div>',
                    unsafe_allow_html=True)
        evidence = a.get("evidence", {})
        for key, val in evidence.items():
            st.markdown(
                f'<div style="padding:4px 0;border-bottom:1px solid #1C2130;'
                f'display:flex;justify-content:space-between;">'
                f'<span style="font-size:11px;color:#8892A4;">{key.replace("_"," ")}</span>'
                f'<span style="font-size:11px;color:#DDE3F0;font-family:Courier New,monospace;">{val}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    with col_right:
        # Causes probables
        st.markdown('<div style="font-size:11px;text-transform:uppercase;letter-spacing:1px;'
                    'color:#6B7894;margin-bottom:6px;">Causes probables</div>',
                    unsafe_allow_html=True)
        for cause in a.get("probable_causes", []):
            st.markdown(
                f'<div style="padding:5px 0 5px 12px;border-bottom:1px solid #1C2130;'
                f'font-size:12px;color:#DDE3F0;border-left:2px solid #2A2F3E;margin-bottom:4px;">'
                f'{cause}</div>',
                unsafe_allow_html=True,
            )

    # Recommandations liées
    linked_recs = [r for r in recs if r.linked_anomaly_id == a["id"]]
    if linked_recs:
        render_section_title("Recommandations liées", "📋")
        for r in linked_recs:
            pc = {"urgent": "#D50000", "high": "#FF6D00", "medium": "#FFB300", "low": "#00C853"}.get(r.priority, "#6B7894")
            with st.expander(f"{r.priority.upper()} — {r.action_title}"):
                st.markdown(f"**Détail :** {r.action_detail}")
                st.markdown(f"**Effet attendu :** {r.expected_effect}")
                st.markdown(f"**Sécurité :** {r.safety_note}")
                if r.steps:
                    st.markdown("**Étapes :**")
                    for j, step in enumerate(r.steps, 1):
                        st.markdown(f"{j}. {step}")
                cola, colb = st.columns(2)
                with cola:
                    st.metric("Économie estimée", f"{fmt_xpf(r.estimated_saving_xpf)} XPF")
                with colb:
                    st.metric("Réduction risque", f"{r.estimated_risk_reduction_pct:.0f} %")

# ── Scoring par domaine ────────────────────────────────────────────────────────
render_section_title("Scoring criticité par domaine", "📊")

col_score, col_details = st.columns([3, 2])
with col_score:
    fig_scores = make_domain_score_bar(scoring, height=260)
    st.plotly_chart(fig_scores, use_container_width=True)

with col_details:
    domain_scores = scoring.get("domain_scores", {})
    for key, label in [
        ("electricity_score", "⚡ Électricité"),
        ("air_score",         "💨 Air comprimé"),
        ("water_score",       "♻️ Eau"),
    ]:
        v = domain_scores.get(key, 0.0)
        s = score_to_status(v)
        c = STATUS_COLORS.get(s, "#00C853")
        st.markdown(
            f'<div style="background:#161A23;border-left:4px solid {c};'
            f'border-radius:0 5px 5px 0;padding:10px 14px;margin-bottom:8px;">'
            f'<div style="font-size:12px;color:#DDE3F0;">{label}</div>'
            f'<div style="font-size:24px;font-weight:700;color:{c};'
            f'font-family:Courier New,monospace;">{v:.0f}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    n_anom = len(anomalies)
    hc = scoring.get("has_critical", False)
    st.markdown(
        f'<div style="background:#161A23;border:1px solid #2A2F3E;border-radius:5px;'
        f'padding:10px 14px;margin-top:4px;">'
        f'<div style="font-size:11px;color:#6B7894;">Score global : '
        f'<strong style="color:#DDE3F0;">{g_score:.0f} / 100</strong></div>'
        f'<div style="font-size:11px;color:#6B7894;">Anomalies : '
        f'<strong style="color:#DDE3F0;">{n_anom}</strong></div>'
        f'<div style="font-size:11px;color:{"#D50000" if hc else "#00C853"};">'
        f'{"⚠️ Anomalie critique active" if hc else "✓ Aucune critique"}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

# ── Assistant IA industriel ───────────────────────────────────────────────────
render_section_title("Assistant IA industriel", "💬")

st.markdown(
    '<div style="background:#0F1C2E;border:1px solid #1E3A5F;border-radius:6px;'
    'padding:10px 16px;font-size:12px;color:#8892A4;margin-bottom:12px;">'
    'Posez une question sur l\'état de l\'usine, les anomalies ou les recommandations. '
    'L\'assistant répond à partir des données de la session en cours — '
    '<strong style="color:#00B0FF;">aucune API externe, aucun pilotage réel.</strong>'
    '</div>',
    unsafe_allow_html=True,
)

# Initialiser l'historique de conversation
if "chat_history" not in ss:
    ss["chat_history"] = []

# ── Boutons de questions rapides ──────────────────────────────────────────────
st.markdown(
    '<div style="font-size:11px;color:#6B7894;margin-bottom:6px;">Questions rapides :</div>',
    unsafe_allow_html=True,
)
qp_cols = st.columns(len(QUICK_PROMPTS))
for _i, _qp in enumerate(QUICK_PROMPTS):
    with qp_cols[_i]:
        if st.button(_qp["label"], key=f"qp_{_i}", use_container_width=True):
            ss["_pending_chat"] = _qp["prompt"]

# Récupérer la question en attente (bouton ou input)
_pending = ss.pop("_pending_chat", None)

# ── Historique affiché ────────────────────────────────────────────────────────
for _msg in ss["chat_history"]:
    with st.chat_message(_msg["role"]):
        st.markdown(_msg["content"])

# ── Saisie libre ─────────────────────────────────────────────────────────────
_user_input = st.chat_input("Posez votre question au système IA...")
if _user_input:
    _pending = _user_input

# ── Traitement de la question ─────────────────────────────────────────────────
if _pending:
    ss["chat_history"].append({"role": "user", "content": _pending})
    _response = answer_user_question(
        question=_pending,
        df=ss["df_current"],
        anomalies=anomalies,
        recommendations=recs,
        scoring_summary=scoring,
        business_summary=biz,
    )
    ss["chat_history"].append({"role": "assistant", "content": _response})
    st.rerun()

# ── Effacer l'historique ──────────────────────────────────────────────────────
if ss["chat_history"]:
    if st.button("🗑️ Effacer la conversation", key="clear_chat"):
        ss["chat_history"] = []
        st.rerun()
