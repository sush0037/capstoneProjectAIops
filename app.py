"""
Healthcare Insurance Claim Review Assistant
Streamlit frontend — multi-agent AI workflow with human-in-the-loop approval
"""

import os
import sys
import json
import tempfile
import logging
from datetime import datetime
from pathlib import Path

import streamlit as st

sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(level=logging.INFO)

st.set_page_config(
    page_title="ClaimIQ — Healthcare Claim Review",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Design system ─────────────────────────────────────────────────────────────
CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

/* App shell */
.stApp { background: #F0F4F8; }
.main .block-container { padding: 1.5rem 2rem 3rem 2rem; max-width: 1400px; }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(175deg, #0D1B2A 0%, #162233 60%, #1A2B3C 100%);
    border-right: 1px solid #243447;
}
section[data-testid="stSidebar"] > div { padding-top: 1rem; }
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] div { color: #CBD5E1; }
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 { color: #F1F5F9 !important; }
section[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.12);
    color: #CBD5E1 !important;
    border-radius: 8px;
    font-size: 0.82rem;
    font-weight: 500;
    transition: all 0.2s ease;
}
section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(10,110,189,0.25);
    border-color: rgba(10,110,189,0.6);
    color: #FFFFFF !important;
}
section[data-testid="stSidebar"] input {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    color: #E2E8F0 !important;
    border-radius: 8px !important;
}

/* ── Page header ── */
.page-header {
    background: linear-gradient(130deg, #0A6EBD 0%, #0D47A1 55%, #1A237E 100%);
    border-radius: 16px;
    padding: 1.8rem 2.2rem;
    margin-bottom: 1.5rem;
    color: white;
    display: flex;
    align-items: center;
    gap: 1.2rem;
    box-shadow: 0 8px 30px rgba(10,110,189,0.2), 0 2px 8px rgba(0,0,0,0.1);
    position: relative;
    overflow: hidden;
}
.page-header::before {
    content: '';
    position: absolute;
    top: -40px; right: -40px;
    width: 200px; height: 200px;
    border-radius: 50%;
    background: rgba(255,255,255,0.05);
}
.page-header::after {
    content: '';
    position: absolute;
    bottom: -60px; right: 80px;
    width: 150px; height: 150px;
    border-radius: 50%;
    background: rgba(255,255,255,0.04);
}
.ph-icon { font-size: 2.8rem; line-height: 1; z-index: 1; }
.ph-text { z-index: 1; }
.ph-title { font-size: 1.65rem; font-weight: 800; letter-spacing: -0.4px; margin: 0 0 4px 0; }
.ph-sub { font-size: 0.85rem; opacity: 0.8; font-weight: 400; margin: 0; }
.ph-pills { display: flex; gap: 8px; margin-top: 10px; z-index: 1; margin-left: auto; align-self: flex-end; }
.ph-pill {
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 20px;
    padding: 4px 12px;
    font-size: 0.72rem;
    font-weight: 500;
    color: rgba(255,255,255,0.9);
    white-space: nowrap;
}

/* ── Cards ── */
.card {
    background: #FFFFFF;
    border-radius: 12px;
    padding: 1.4rem 1.6rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05), 0 4px 16px rgba(0,0,0,0.04);
    border: 1px solid #E2E8F0;
    margin-bottom: 1rem;
}
.card-sm {
    background: #FFFFFF;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    border: 1px solid #E2E8F0;
}
.card-label {
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #94A3B8;
    margin-bottom: 0.7rem;
    padding-bottom: 0.6rem;
    border-bottom: 1px solid #F1F5F9;
    display: flex;
    align-items: center;
    gap: 6px;
}

/* ── Badges ── */
.badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 5px 14px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.4px;
}
.badge-approve { background: #ECFDF5; color: #065F46; border: 1.5px solid #A7F3D0; }
.badge-reject  { background: #FEF2F2; color: #991B1B; border: 1.5px solid #FECACA; }
.badge-review  { background: #FFFBEB; color: #92400E; border: 1.5px solid #FDE68A; }
.badge-ok      { background: #ECFDF5; color: #065F46; border: 1px solid #A7F3D0; }
.badge-warn    { background: #FFFBEB; color: #92400E; border: 1px solid #FDE68A; }
.badge-err     { background: #FEF2F2; color: #991B1B; border: 1px solid #FECACA; }

/* ── Confidence badge ── */
.conf-high   { background: #ECFDF5; color: #065F46; padding: 2px 9px; border-radius: 12px; font-size: 0.72rem; font-weight: 600; }
.conf-medium { background: #FFFBEB; color: #92400E; padding: 2px 9px; border-radius: 12px; font-size: 0.72rem; font-weight: 600; }
.conf-low    { background: #FEF2F2; color: #991B1B; padding: 2px 9px; border-radius: 12px; font-size: 0.72rem; font-weight: 600; }

/* ── Sidebar status indicators ── */
.sb-status-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 0;
    border-bottom: 1px solid rgba(255,255,255,0.05);
}
.sb-dot {
    width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
}
.sb-dot-ok   { background: #34D399; box-shadow: 0 0 6px rgba(52,211,153,0.6); }
.sb-dot-warn { background: #FBBF24; box-shadow: 0 0 6px rgba(251,191,36,0.6); }
.sb-dot-err  { background: #F87171; box-shadow: 0 0 6px rgba(248,113,113,0.6); }
.sb-label    { font-size: 0.78rem; color: #94A3B8; flex: 1; }
.sb-val      { font-size: 0.76rem; font-weight: 500; color: #CBD5E1; }

/* ── Sidebar brand ── */
.sb-brand {
    padding: 0.2rem 0 1.2rem 0;
    border-bottom: 1px solid rgba(255,255,255,0.08);
    margin-bottom: 1rem;
}
.sb-brand-name  { font-size: 1.15rem; font-weight: 800; color: #F1F5F9 !important; letter-spacing: -0.3px; }
.sb-brand-sub   { font-size: 0.65rem; color: #475569 !important; text-transform: uppercase; letter-spacing: 1px; }
.sb-section     { font-size: 0.63rem; font-weight: 700; text-transform: uppercase;
                  letter-spacing: 1.2px; color: #475569 !important; margin: 1.2rem 0 0.5rem 0; }

/* ── Sidebar stat boxes ── */
.sb-stats { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px; margin-top: 6px; }
.sb-stat-box {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px;
    padding: 8px 6px;
    text-align: center;
}
.sb-stat-val   { font-size: 1.2rem; font-weight: 700; color: #E2E8F0 !important; line-height: 1; }
.sb-stat-label { font-size: 0.6rem; color: #64748B !important; margin-top: 2px; text-transform: uppercase; }

/* ── Pipeline stepper ── */
.stepper { display: flex; align-items: flex-start; gap: 0; margin: 1.2rem 0; }
.step { flex: 1; display: flex; flex-direction: column; align-items: center; position: relative; }
.step:not(:last-child)::after {
    content: '';
    position: absolute;
    top: 15px; left: calc(50% + 14px);
    width: calc(100% - 28px);
    height: 2px;
    background: linear-gradient(90deg, #CBD5E1, #E2E8F0);
    z-index: 0;
}
.step-circle {
    width: 30px; height: 30px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.75rem; font-weight: 700;
    position: relative; z-index: 1;
    border: 2px solid #CBD5E1;
    background: #FFFFFF;
    color: #94A3B8;
    transition: all 0.3s;
}
.step-circle.done   { background: #10B981; border-color: #10B981; color: white; }
.step-circle.active { background: #0A6EBD; border-color: #0A6EBD; color: white;
                      box-shadow: 0 0 0 4px rgba(10,110,189,0.18); }
.step-label { font-size: 0.64rem; font-weight: 500; color: #6B7280; text-align: center;
              margin-top: 6px; line-height: 1.3; max-width: 70px; }
.step-label.active { color: #0A6EBD; font-weight: 600; }
.step-label.done   { color: #10B981; font-weight: 600; }

/* ── Agent result blocks ── */
.agent-block {
    background: #FAFBFC;
    border: 1px solid #E8ECF0;
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 0.9rem;
}
.agent-block-hdr {
    display: flex; align-items: center; gap: 10px;
    margin-bottom: 1rem;
    padding-bottom: 0.7rem;
    border-bottom: 1px solid #EEF2F7;
}
.agent-num {
    width: 26px; height: 26px;
    background: linear-gradient(135deg, #0A6EBD, #1565C0);
    color: white; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.72rem; font-weight: 700; flex-shrink: 0;
}
.agent-name { font-size: 0.88rem; font-weight: 700; color: #1E293B; }
.agent-desc { font-size: 0.72rem; color: #94A3B8; margin-left: auto; }

/* ── Decision panel ── */
.decision-panel {
    background: linear-gradient(145deg, #F8FAFF 0%, #EEF2FF 100%);
    border: 1px solid #C7D2FE;
    border-radius: 14px;
    padding: 1.4rem 1.5rem;
    position: sticky;
    top: 1rem;
}
.dp-title { font-size: 1rem; font-weight: 800; color: #1E40AF; display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.dp-sub   { font-size: 0.76rem; color: #64748B; margin-bottom: 1rem; padding-bottom: 1rem; border-bottom: 1px solid #DDE4F8; }

/* ── AI recommendation highlight ── */
.ai-rec-box {
    border-radius: 10px;
    padding: 10px 14px;
    margin-bottom: 1rem;
    display: flex; align-items: center; gap: 10px;
}
.ai-rec-box.approve { background: #ECFDF5; border: 1px solid #A7F3D0; }
.ai-rec-box.reject  { background: #FEF2F2; border: 1px solid #FECACA; }
.ai-rec-box.review  { background: #FFFBEB; border: 1px solid #FDE68A; }
.ai-rec-text { font-size: 0.82rem; font-weight: 600; }

/* ── Result banner ── */
.result-banner {
    border-radius: 14px;
    padding: 1.6rem 2rem;
    display: flex; align-items: center; gap: 1.2rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 20px rgba(0,0,0,0.06);
}
.result-banner.approved {
    background: linear-gradient(135deg, #ECFDF5, #D1FAE5);
    border: 1.5px solid #6EE7B7;
}
.result-banner.rejected {
    background: linear-gradient(135deg, #FEF2F2, #FEE2E2);
    border: 1.5px solid #FCA5A5;
}
.result-banner.pending {
    background: linear-gradient(135deg, #FFFBEB, #FEF3C7);
    border: 1.5px solid #FCD34D;
}
.rb-icon   { font-size: 2.8rem; line-height: 1; }
.rb-label  { font-size: 0.72rem; font-weight: 600; opacity: 0.65; text-transform: uppercase; letter-spacing: 0.6px; }
.rb-status { font-size: 1.7rem; font-weight: 800; letter-spacing: -0.5px; line-height: 1.1; }

/* ── Metric strip ── */
.metric-strip { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 1rem; }
.mcard {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 1rem 1.1rem;
    text-align: center;
}
.mcard-val   { font-size: 1.5rem; font-weight: 800; color: #0A6EBD; line-height: 1.2; }
.mcard-label { font-size: 0.68rem; font-weight: 600; color: #64748B; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 3px; }

/* ── Upload zone hint ── */
.upload-hint {
    background: #EFF6FF;
    border: 2px dashed #93C5FD;
    border-radius: 12px;
    padding: 1.2rem;
    text-align: center;
    color: #2563EB;
    font-size: 0.82rem;
    font-weight: 500;
    margin-bottom: 1rem;
}

/* ── Risk flags ── */
.risk-flag {
    background: #FFF7ED;
    border: 1px solid #FED7AA;
    border-left: 3px solid #F97316;
    border-radius: 6px;
    padding: 7px 11px;
    font-size: 0.79rem;
    color: #9A3412;
    margin: 4px 0;
}

/* ── Policy citations ── */
.policy-cite {
    background: #F0F9FF;
    border: 1px solid #BAE6FD;
    border-left: 3px solid #0284C7;
    border-radius: 6px;
    padding: 7px 11px;
    font-size: 0.79rem;
    color: #0C4A6E;
    margin: 4px 0;
    font-style: italic;
}

/* ── Supporting reason items ── */
.reason-item {
    display: flex; align-items: flex-start; gap: 8px;
    padding: 5px 0;
    font-size: 0.81rem;
    color: #374151;
    border-bottom: 1px solid #F9FAFB;
}
.reason-bullet {
    width: 6px; height: 6px; border-radius: 50%;
    background: #0A6EBD; flex-shrink: 0; margin-top: 6px;
}

/* ── About page tech cards ── */
.tech-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 1rem 0; }
.tech-card {
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    padding: 1rem;
    text-align: center;
}
.tech-icon  { font-size: 1.6rem; margin-bottom: 6px; }
.tech-name  { font-size: 0.8rem; font-weight: 700; color: #1E293B; }
.tech-value { font-size: 0.72rem; color: #64748B; margin-top: 2px; }

/* ── Pipeline diagram ── */
.pipeline-flow {
    display: flex; align-items: center; gap: 0;
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 1.2rem;
    margin: 1rem 0;
    flex-wrap: wrap;
    justify-content: center;
}
.pf-node {
    background: white;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 0.78rem;
    font-weight: 600;
    color: #1E293B;
    text-align: center;
    min-width: 100px;
}
.pf-node.highlight { background: #EFF6FF; border-color: #93C5FD; color: #1D4ED8; }
.pf-node.human     { background: #ECFDF5; border-color: #86EFAC; color: #166534; }
.pf-arrow { color: #CBD5E1; font-size: 1.2rem; padding: 0 6px; }

/* ── Scenario chips ── */
.scenario-grid { display: flex; flex-wrap: wrap; gap: 8px; margin: 0.8rem 0; }
.scenario-chip {
    background: white;
    border: 1px solid #E2E8F0;
    border-radius: 20px;
    padding: 5px 12px;
    font-size: 0.76rem;
    font-weight: 500;
    color: #475569;
    display: flex; align-items: center; gap: 5px;
}

/* ── Table ── */
.stDataFrame { border-radius: 10px !important; overflow: hidden; }

/* ── Progress bar ── */
.stProgress > div > div { background: linear-gradient(90deg, #0A6EBD, #00B4D8) !important; border-radius: 4px; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] { gap: 6px; background: transparent; padding: 0; }
.stTabs [data-baseweb="tab"] {
    border-radius: 8px 8px 0 0;
    font-size: 0.83rem;
    font-weight: 500;
    padding: 8px 18px;
}

/* ── Buttons ── */
button[kind="primary"] {
    background: linear-gradient(135deg, #0A6EBD, #1565C0) !important;
    border: none !important;
    border-radius: 9px !important;
    font-weight: 600 !important;
    letter-spacing: 0.2px !important;
    box-shadow: 0 2px 8px rgba(10,110,189,0.25) !important;
    transition: all 0.2s !important;
}
button[kind="primary"]:hover {
    background: linear-gradient(135deg, #1565C0, #0D47A1) !important;
    box-shadow: 0 4px 16px rgba(10,110,189,0.35) !important;
    transform: translateY(-1px) !important;
}
button[kind="secondary"] {
    border-radius: 9px !important;
    border-color: #CBD5E1 !important;
    font-weight: 500 !important;
}

/* ── Inputs ── */
.stTextArea textarea, .stTextInput input, .stSelectbox select {
    border-radius: 9px !important;
    border-color: #E2E8F0 !important;
    font-size: 0.85rem !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: #0A6EBD !important;
    box-shadow: 0 0 0 3px rgba(10,110,189,0.1) !important;
}

/* ── Radio ── */
.stRadio label { font-size: 0.84rem !important; }
.stRadio > div { gap: 4px !important; }

/* ── Expanders ── */
details {
    border-radius: 10px !important;
    border: 1px solid #E8ECF0 !important;
    background: white !important;
}
summary { font-size: 0.85rem !important; font-weight: 600 !important; padding: 0.7rem 1rem !important; }

/* ── Status message boxes ── */
div[data-testid="stAlert"] { border-radius: 10px !important; font-size: 0.84rem !important; }

/* ── Hide native metric widget (we use custom HTML) ── */
div[data-testid="stMetricValue"] { font-size: 1.4rem !important; font-weight: 700 !important; color: #0A6EBD !important; }
div[data-testid="stMetricLabel"] { font-size: 0.72rem !important; color: #64748B !important; }
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)


# ── Session state ─────────────────────────────────────────────────────────────
def init_session():
    defaults = {
        "claims_history": [],
        "current_claim": None,
        "workflow_stage": "upload",
        "reviewer_name": "Dr. Reviewer",
        "rag_initialized": False,
        "setup_done": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()


# ── System status ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def check_system_status():
    status = {}
    try:
        from src.config import openai_configured, aws_configured, CHROMA_PERSIST_DIR
        status["openai"] = openai_configured()
        status["aws"] = aws_configured()
        try:
            from src.rag.ingestion import get_collection_stats
            stats = get_collection_stats(CHROMA_PERSIST_DIR)
            status["chromadb"] = stats["chunk_count"] > 0
            status["rag_chunks"] = stats["chunk_count"]
        except Exception:
            status["chromadb"] = False
            status["rag_chunks"] = 0
    except Exception as e:
        status = {"openai": False, "aws": False, "chromadb": False, "rag_chunks": 0, "error": str(e)}
    return status


# ── Sidebar ───────────────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        # Brand
        st.markdown("""
        <div class="sb-brand">
            <div style="font-size:1.6rem;margin-bottom:4px;">🏥</div>
            <div class="sb-brand-name">ClaimIQ</div>
            <div class="sb-brand-sub">Claim Review Assistant</div>
        </div>
        """, unsafe_allow_html=True)

        # System status
        status = check_system_status()
        st.markdown('<div class="sb-section">System Status</div>', unsafe_allow_html=True)

        openai_dot   = "sb-dot-ok" if status.get("openai") else "sb-dot-err"
        openai_val   = "Connected" if status.get("openai") else "Not configured"
        aws_dot      = "sb-dot-ok" if status.get("aws") else "sb-dot-warn"
        aws_val      = "Connected" if status.get("aws") else "Local mode"
        chroma_dot   = "sb-dot-ok" if status.get("chromadb") else "sb-dot-warn"
        chroma_val   = f"{status.get('rag_chunks', 0)} chunks" if status.get("chromadb") else "Fallback rules"

        st.markdown(f"""
        <div class="sb-status-item">
            <div class="sb-dot {openai_dot}"></div>
            <div class="sb-label">OpenAI LLM</div>
            <div class="sb-val">{openai_val}</div>
        </div>
        <div class="sb-status-item">
            <div class="sb-dot {aws_dot}"></div>
            <div class="sb-label">AWS S3</div>
            <div class="sb-val">{aws_val}</div>
        </div>
        <div class="sb-status-item">
            <div class="sb-dot {chroma_dot}"></div>
            <div class="sb-label">ChromaDB RAG</div>
            <div class="sb-val">{chroma_val}</div>
        </div>
        """, unsafe_allow_html=True)

        if not status.get("openai"):
            st.error("Set `OPENAI_API_KEY` in `.env` to enable AI processing.")

        # Quick actions
        st.markdown('<div class="sb-section">Quick Actions</div>', unsafe_allow_html=True)
        if st.button("⚙️  Generate Sample Data", use_container_width=True,
                     help="Create 10 synthetic claim PDFs + 3 policy docs"):
            _generate_data()
        if st.button("🔍  Build RAG Index", use_container_width=True,
                     help="Ingest policy docs into ChromaDB"):
            _ingest_docs()

        # Reviewer identity
        st.markdown('<div class="sb-section">Reviewer</div>', unsafe_allow_html=True)
        st.session_state.reviewer_name = st.text_input(
            "Your Name", value=st.session_state.reviewer_name, label_visibility="collapsed",
            placeholder="Reviewer name..."
        )

        # Session stats
        total    = len(st.session_state.claims_history)
        approved = sum(1 for c in st.session_state.claims_history if c.get("final_decision") == "APPROVED")
        rejected = sum(1 for c in st.session_state.claims_history if c.get("final_decision") == "REJECTED")

        st.markdown('<div class="sb-section">Session Stats</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="sb-stats">
            <div class="sb-stat-box">
                <div class="sb-stat-val">{total}</div>
                <div class="sb-stat-label">Total</div>
            </div>
            <div class="sb-stat-box">
                <div class="sb-stat-val" style="color:#34D399 !important;">{approved}</div>
                <div class="sb-stat-label">Approved</div>
            </div>
            <div class="sb-stat-box">
                <div class="sb-stat-val" style="color:#F87171 !important;">{rejected}</div>
                <div class="sb-stat-label">Rejected</div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def _generate_data():
    with st.spinner("Generating synthetic data..."):
        try:
            from src.config import CLAIMS_DIR, POLICY_DOCS_DIR
            from src.utils.pdf_generator import generate_all_synthetic_data
            result = generate_all_synthetic_data(CLAIMS_DIR, POLICY_DOCS_DIR)
            st.sidebar.success(f"Created {result['claims_generated']} claims, {result['policies_generated']} policies")
            st.cache_data.clear()
        except Exception as e:
            st.sidebar.error(f"Failed: {e}")


def _ingest_docs():
    with st.spinner("Building RAG index..."):
        try:
            from src.config import POLICY_DOCS_DIR, CHROMA_PERSIST_DIR
            from src.rag.ingestion import ingest_policy_documents
            count = ingest_policy_documents(POLICY_DOCS_DIR, CHROMA_PERSIST_DIR, force_reingest=True)
            st.sidebar.success(f"Indexed {count} chunks")
            st.cache_data.clear()
            st.session_state.rag_initialized = True
        except Exception as e:
            st.sidebar.error(f"Failed: {e}")


# ── Page header ───────────────────────────────────────────────────────────────
def render_header():
    st.markdown("""
    <div class="page-header">
        <div class="ph-icon">🏥</div>
        <div class="ph-text">
            <div class="ph-title">Healthcare Claim Review Assistant</div>
            <div class="ph-sub">AI-powered multi-agent claim processing with human-in-the-loop approval</div>
        </div>
        <div class="ph-pills">
            <span class="ph-pill">🤖 LangGraph</span>
            <span class="ph-pill">🔍 RAG + ChromaDB</span>
            <span class="ph-pill">✅ Human-in-Loop</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── Workflow progress stepper ─────────────────────────────────────────────────
def render_stepper(stage: str):
    stages = ["upload", "processing", "awaiting_approval", "completed"]
    labels = ["Upload Claim", "AI Processing", "Human Review", "Decision"]
    icons  = ["📄", "⚙️", "👤", "✅"]
    idx    = stages.index(stage) if stage in stages else 0

    circles = ""
    for i, (label, icon) in enumerate(zip(labels, icons)):
        if i < idx:
            cls  = "done"
            lcls = "done"
            sym  = "✓"
        elif i == idx:
            cls  = "active"
            lcls = "active"
            sym  = icon
        else:
            cls  = ""
            lcls = ""
            sym  = str(i + 1)
        circles += f"""
        <div class="step">
            <div class="step-circle {cls}">{sym}</div>
            <div class="step-label {lcls}">{label}</div>
        </div>"""

    st.markdown(f'<div class="stepper">{circles}</div>', unsafe_allow_html=True)


# ── Main tabs ─────────────────────────────────────────────────────────────────
def render_main():
    render_header()
    tab1, tab2, tab3 = st.tabs(["📋  Process New Claim", "📊  Claims History", "ℹ️  About"])
    with tab1:
        render_process_tab()
    with tab2:
        render_history_tab()
    with tab3:
        render_about_tab()


# ── Process tab ───────────────────────────────────────────────────────────────
def render_process_tab():
    stage = st.session_state.workflow_stage
    render_stepper(stage)
    st.markdown("---")

    if stage == "upload":
        render_upload_section()
    elif stage == "processing":
        render_processing_section()
    elif stage == "awaiting_approval":
        render_review_section()
    elif stage == "completed":
        render_completed_section()

    if stage != "upload":
        st.markdown("---")
        if st.button("↩  Start New Claim Review", type="secondary"):
            st.session_state.workflow_stage = "upload"
            st.session_state.current_claim  = None
            st.rerun()


# ── Upload section ────────────────────────────────────────────────────────────
def render_upload_section():
    col_left, col_right = st.columns([3, 2], gap="large")

    with col_left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-label">📄 Upload Claim PDF</div>', unsafe_allow_html=True)

        st.markdown("""
        <div class="upload-hint">
            📎 Drag and drop a claim PDF here, or click Browse below
        </div>
        """, unsafe_allow_html=True)

        uploaded_file = st.file_uploader(
            "Select claim PDF",
            type=["pdf"],
            help="Healthcare insurance claim form in PDF format",
            label_visibility="collapsed",
        )

        st.markdown("**Or choose a sample claim:**")
        from src.config import CLAIMS_DIR
        sample_files  = sorted(Path(CLAIMS_DIR).glob("*.pdf")) if Path(CLAIMS_DIR).exists() else []
        sample_names  = ["— select a sample —"] + [f.name for f in sample_files]
        selected      = st.selectbox("Sample claims", sample_names, label_visibility="collapsed") if sample_files else "— select a sample —"
        if not sample_files:
            st.info("No sample claims found. Click **Generate Sample Data** in the sidebar.")

        claim_id_input = st.text_input("Claim ID (optional)", placeholder="Auto-generated if blank")
        st.markdown("</div>", unsafe_allow_html=True)

        has_input = uploaded_file is not None or selected != "— select a sample —"
        process_btn = st.button("▶  Process Claim", type="primary", disabled=not has_input, use_container_width=True)

        if process_btn and has_input:
            if uploaded_file:
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                tmp.write(uploaded_file.read())
                tmp.close()
                pdf_path     = tmp.name
                display_name = uploaded_file.name
            else:
                pdf_path     = str(sample_files[sample_names.index(selected) - 1])
                display_name = selected

            claim_id = claim_id_input.strip() or f"CLM-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            st.session_state._pending_pdf  = pdf_path
            st.session_state._pending_name = display_name
            st.session_state._pending_id   = claim_id
            st.session_state.workflow_stage = "processing"
            st.rerun()

    with col_right:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="card-label">🤖 Agent Pipeline</div>', unsafe_allow_html=True)
        st.markdown("""
        <div style="display:flex;flex-direction:column;gap:8px;">
            <div class="agent-block" style="margin-bottom:0;">
                <div class="agent-block-hdr" style="margin-bottom:0;border:none;padding:0;">
                    <div class="agent-num">1</div>
                    <div>
                        <div class="agent-name">OCR Agent</div>
                        <div style="font-size:0.72rem;color:#64748B;">Extract &amp; structure claim fields</div>
                    </div>
                </div>
            </div>
            <div style="text-align:center;color:#CBD5E1;font-size:1rem;">↓</div>
            <div class="agent-block" style="margin-bottom:0;">
                <div class="agent-block-hdr" style="margin-bottom:0;border:none;padding:0;">
                    <div class="agent-num">2</div>
                    <div>
                        <div class="agent-name">Validation Agent</div>
                        <div style="font-size:0.72rem;color:#64748B;">ICD-10 / CPT / NPI checks</div>
                    </div>
                </div>
            </div>
            <div style="text-align:center;color:#CBD5E1;font-size:1rem;">↓</div>
            <div class="agent-block" style="margin-bottom:0;">
                <div class="agent-block-hdr" style="margin-bottom:0;border:none;padding:0;">
                    <div class="agent-num">3</div>
                    <div>
                        <div class="agent-name">Recommendation Agent</div>
                        <div style="font-size:0.72rem;color:#64748B;">RAG policy lookup + AI decision</div>
                    </div>
                </div>
            </div>
            <div style="text-align:center;color:#CBD5E1;font-size:1rem;">↓</div>
            <div class="agent-block" style="margin-bottom:0;background:#ECFDF5;border-color:#A7F3D0;">
                <div class="agent-block-hdr" style="margin-bottom:0;border:none;padding:0;">
                    <div class="agent-num" style="background:linear-gradient(135deg,#10B981,#059669);">✓</div>
                    <div>
                        <div class="agent-name" style="color:#065F46;">Human Approval</div>
                        <div style="font-size:0.72rem;color:#6EE7B7;">Reviewer confirms or overrides</div>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


# ── Processing section ────────────────────────────────────────────────────────
def render_processing_section():
    pdf_path     = st.session_state.get("_pending_pdf", "")
    claim_id     = st.session_state.get("_pending_id", "")
    display_name = st.session_state.get("_pending_name", "")

    st.markdown(f"""
    <div class="card">
        <div class="card-label">⚙️ AI Processing Pipeline</div>
        <div style="font-size:0.88rem;color:#374151;margin-bottom:4px;">
            <strong>{display_name}</strong>
        </div>
        <div style="font-size:0.78rem;color:#64748B;">Claim ID: <code>{claim_id}</code></div>
    </div>
    """, unsafe_allow_html=True)

    from src.config import openai_configured
    if not openai_configured():
        st.error("OPENAI_API_KEY is not set. Please configure your .env file and restart.")
        return

    progress = st.progress(0, text="Initialising pipeline...")

    try:
        from src.workflow.claim_workflow import run_claim_pipeline

        with st.status("Running AI agents...", expanded=True) as status_widget:
            st.write("**Step 1 — OCR Agent:** Extracting text and structuring fields from PDF...")
            progress.progress(20, text="OCR Agent: reading claim document...")

            result = run_claim_pipeline(pdf_path, claim_id)

            progress.progress(50, text="Validation Agent: checking fields...")
            st.write("**Step 2 — Validation Agent:** Verifying ICD-10 / CPT codes and mandatory fields...")

            progress.progress(80, text="Recommendation Agent: querying policy RAG...")
            st.write("**Step 3 — Recommendation Agent:** Querying policy knowledge base and generating AI decision...")

            progress.progress(100, text="Pipeline complete — ready for review")
            st.write("**Complete:** Awaiting your review and approval.")
            status_widget.update(label="Processing complete!", state="complete")

        st.session_state.current_claim  = result
        st.session_state.workflow_stage = "awaiting_approval"
        st.rerun()

    except Exception as e:
        progress.empty()
        st.error(f"Pipeline failed: {e}")
        st.exception(e)
        if st.button("Try Again"):
            st.session_state.workflow_stage = "upload"
            st.rerun()


# ── Review section ────────────────────────────────────────────────────────────
def render_review_section():
    state = st.session_state.current_claim
    if not state:
        st.session_state.workflow_stage = "upload"
        st.rerun()
        return

    claim_id      = state.get("claim_id", "N/A")
    fields        = state.get("extracted_fields", {})
    amount_display = f"${float(fields['claim_amount']):,.2f}" if fields.get("claim_amount") else "—"

    # Summary strip
    st.markdown(f"""
    <div class="card" style="padding:1rem 1.6rem;">
        <div style="display:flex;align-items:center;gap:1.5rem;flex-wrap:wrap;">
            <div><div style="font-size:0.65rem;font-weight:700;color:#94A3B8;text-transform:uppercase;letter-spacing:0.8px;">Claim ID</div>
                 <div style="font-size:0.95rem;font-weight:700;color:#1E293B;font-family:monospace;">{claim_id}</div></div>
            <div><div style="font-size:0.65rem;font-weight:700;color:#94A3B8;text-transform:uppercase;letter-spacing:0.8px;">Patient</div>
                 <div style="font-size:0.88rem;font-weight:600;color:#1E293B;">{fields.get("patient_name","—")}</div></div>
            <div><div style="font-size:0.65rem;font-weight:700;color:#94A3B8;text-transform:uppercase;letter-spacing:0.8px;">Amount</div>
                 <div style="font-size:0.88rem;font-weight:600;color:#1E293B;">{amount_display}</div></div>
            <div><div style="font-size:0.65rem;font-weight:700;color:#94A3B8;text-transform:uppercase;letter-spacing:0.8px;">Claim Type</div>
                 <div style="font-size:0.88rem;font-weight:600;color:#1E293B;">{fields.get("claim_type","—")}</div></div>
            <div><div style="font-size:0.65rem;font-weight:700;color:#94A3B8;text-transform:uppercase;letter-spacing:0.8px;">Treatment Date</div>
                 <div style="font-size:0.88rem;font-weight:600;color:#1E293B;">{fields.get("treatment_date","—")}</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_left, col_right = st.columns([3, 2], gap="large")

    with col_left:
        # ── OCR Agent block ─────────────────────────────────────────────────
        st.markdown("""
        <div class="agent-block">
            <div class="agent-block-hdr">
                <div class="agent-num">1</div>
                <div class="agent-name">OCR Agent — Extracted Fields</div>
                <div class="agent-desc">pdfplumber + LLM extraction</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if fields:
            field_status = state.get("field_status", {})
            rows = []
            for k, v in fields.items():
                fs   = field_status.get(k, "ok")
                icon = "🟢" if fs == "ok" else ("🔴" if fs == "missing_mandatory" else "🟡")
                rows.append({"Field": k.replace("_", " ").title(), "Value": str(v) if v else "—", "Status": icon})
            import pandas as pd
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=280)
        else:
            st.warning("No fields extracted from PDF.")

        if state.get("ocr_log"):
            st.caption(state["ocr_log"])

        # ── Validation Agent block ──────────────────────────────────────────
        missing_m      = state.get("missing_mandatory_fields", [])
        missing_i      = state.get("missing_important_fields", [])
        inconsistencies = state.get("inconsistencies", [])
        severity       = state.get("severity", "UNKNOWN")
        sev_cls        = {"HIGH": "badge-err", "MEDIUM": "badge-warn", "LOW": "badge-ok"}.get(severity, "badge-warn")

        st.markdown(f"""
        <div class="agent-block">
            <div class="agent-block-hdr">
                <div class="agent-num">2</div>
                <div class="agent-name">Validation Agent — Field Check</div>
                <span class="badge {sev_cls}">{severity} severity</span>
            </div>
        """, unsafe_allow_html=True)

        if missing_m:
            st.error(f"Missing mandatory fields: **{', '.join(missing_m)}**")
        if missing_i:
            st.warning(f"Missing optional fields: {', '.join(missing_i)}")
        if inconsistencies:
            for inc in inconsistencies:
                st.warning(f"⚠ {inc}")
        if not missing_m and not inconsistencies:
            st.success("All validation checks passed.")
        if state.get("validation_summary"):
            st.caption(state["validation_summary"])
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Recommendation Agent block ──────────────────────────────────────
        rec   = state.get("recommendation", "MANUAL_REVIEW")
        conf  = state.get("confidence", "LOW")
        rec_cls  = {"APPROVE": "badge-approve", "REJECT": "badge-reject"}.get(rec, "badge-review")
        conf_cls = {"HIGH": "conf-high", "MEDIUM": "conf-medium", "LOW": "conf-low"}.get(conf, "conf-low")

        st.markdown(f"""
        <div class="agent-block">
            <div class="agent-block-hdr">
                <div class="agent-num">3</div>
                <div class="agent-name">Recommendation Agent — AI Decision</div>
                <div class="agent-desc">RAG + LLM</div>
            </div>
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
                <span class="badge {rec_cls}">{rec.replace("_"," ")}</span>
                <span class="{conf_cls}">Confidence: {conf}</span>
            </div>
        """, unsafe_allow_html=True)

        if state.get("primary_reason"):
            st.markdown(f"**Reason:** {state['primary_reason']}")

        supporting = state.get("supporting_reasons", [])
        if supporting:
            items = "".join(f'<div class="reason-item"><div class="reason-bullet"></div><div>{r}</div></div>' for r in supporting)
            st.markdown(f"**Supporting reasons:**", unsafe_allow_html=False)
            st.markdown(items, unsafe_allow_html=True)

        citations = state.get("policy_citations", [])
        if citations:
            st.markdown("**Policy citations:**")
            for c in citations:
                st.markdown(f'<div class="policy-cite">📋 {c}</div>', unsafe_allow_html=True)

        risk_flags = state.get("risk_flags", [])
        if risk_flags:
            st.markdown("**Risk flags:**")
            for r in risk_flags:
                st.markdown(f'<div class="risk-flag">⚠️ {r}</div>', unsafe_allow_html=True)

        sources = state.get("policy_sources", [])
        if sources:
            st.caption(f"RAG sources: {', '.join(sources)}")

        st.markdown("</div>", unsafe_allow_html=True)

    with col_right:
        # ── Decision panel ──────────────────────────────────────────────────
        ai_box_cls = {"APPROVE": "approve", "REJECT": "reject"}.get(rec, "review")
        ai_icon    = {"APPROVE": "✅", "REJECT": "❌"}.get(rec, "⚠️")
        ai_msg     = {"APPROVE": "AI recommends APPROVAL", "REJECT": "AI recommends REJECTION"}.get(rec, "AI recommends MANUAL REVIEW")

        st.markdown(f"""
        <div class="decision-panel">
            <div class="dp-title">👤 Human Approval</div>
            <div class="dp-sub">Review AI findings and submit your final decision</div>
            <div class="ai-rec-box {ai_box_cls}">
                <span style="font-size:1.2rem;">{ai_icon}</span>
                <span class="ai-rec-text">{ai_msg}</span>
            </div>
        """, unsafe_allow_html=True)

        if state.get("suggested_action"):
            st.markdown(f'<div style="font-size:0.78rem;color:#64748B;margin-bottom:1rem;padding:8px 12px;background:#F8FAFC;border-radius:8px;border:1px solid #E2E8F0;">💡 <em>{state["suggested_action"]}</em></div>', unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

        human_decision = st.radio(
            "Your Decision",
            options=["APPROVE", "REJECT", "OVERRIDE_APPROVE", "OVERRIDE_REJECT"],
            format_func=lambda x: {
                "APPROVE":          "✅  Approve  (agree with AI)",
                "REJECT":           "❌  Reject  (agree with AI)",
                "OVERRIDE_APPROVE": "🔄  Override — Approve anyway",
                "OVERRIDE_REJECT":  "🔄  Override — Reject anyway",
            }.get(x, x),
            index=0 if rec == "APPROVE" else 1,
        )

        human_notes = st.text_area(
            "Reviewer Notes",
            placeholder="Add clinical notes, compliance remarks, or override justification...",
            height=110,
        )

        confirm = st.button("Submit Decision", type="primary", use_container_width=True)
        if confirm:
            _submit_decision(state, human_decision, human_notes)

        with st.expander("📋 Processing Log", expanded=False):
            for entry in state.get("processing_log", []):
                st.text(entry)


def _submit_decision(state, human_decision, human_notes):
    with st.spinner("Recording decision..."):
        try:
            from src.workflow.claim_workflow import finalize_claim
            final_state = finalize_claim(
                state,
                human_decision=human_decision,
                human_notes=human_notes,
                reviewer=st.session_state.reviewer_name,
            )
            st.session_state.current_claim = final_state
            st.session_state.claims_history.append({
                "claim_id":          final_state.get("claim_id"),
                "patient_name":      final_state.get("extracted_fields", {}).get("patient_name", "Unknown"),
                "claim_amount":      final_state.get("extracted_fields", {}).get("claim_amount"),
                "ai_recommendation": final_state.get("recommendation"),
                "final_decision":    final_state.get("final_decision"),
                "human_decision":    human_decision,
                "reviewer":          st.session_state.reviewer_name,
                "timestamp":         final_state.get("decision_timestamp"),
                "local_json":        final_state.get("local_json_path"),
            })
            st.session_state.workflow_stage = "completed"
            st.rerun()
        except Exception as e:
            st.error(f"Failed to record decision: {e}")
            st.exception(e)


# ── Completed section ─────────────────────────────────────────────────────────
def render_completed_section():
    state = st.session_state.current_claim
    if not state:
        return

    final    = state.get("final_decision", "UNKNOWN")
    claim_id = state.get("claim_id", "N/A")
    fields   = state.get("extracted_fields", {})

    banner_cls = {"APPROVED": "approved", "REJECTED": "rejected"}.get(final, "pending")
    icon       = {"APPROVED": "✅", "REJECTED": "❌"}.get(final, "⏳")
    color      = {"APPROVED": "#065F46", "REJECTED": "#991B1B"}.get(final, "#92400E")

    st.markdown(f"""
    <div class="result-banner {banner_cls}">
        <div class="rb-icon">{icon}</div>
        <div>
            <div class="rb-label">Final Decision</div>
            <div class="rb-status" style="color:{color};">Claim {claim_id} — {final}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if final == "APPROVED":
        st.balloons()

    # Metric strip
    reviewer = state.get("decision_by", "—")
    ai_rec   = state.get("recommendation", "—")
    amount   = f"${fields.get('claim_amount', 0):,.2f}" if fields.get("claim_amount") else "—"

    st.markdown(f"""
    <div class="metric-strip">
        <div class="mcard">
            <div class="mcard-val" style="font-size:1.1rem;">{fields.get("patient_name","—")}</div>
            <div class="mcard-label">Patient</div>
        </div>
        <div class="mcard">
            <div class="mcard-val">{amount}</div>
            <div class="mcard-label">Claim Amount</div>
        </div>
        <div class="mcard">
            <div class="mcard-val" style="font-size:1rem;">{ai_rec.replace("_"," ")}</div>
            <div class="mcard-label">AI Recommendation</div>
        </div>
        <div class="mcard">
            <div class="mcard-val" style="font-size:1rem;">{reviewer}</div>
            <div class="mcard-label">Decided By</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("📄 Full Review Summary", expanded=True):
        st.json({
            "claim_id":          state.get("claim_id"),
            "patient":           fields.get("patient_name"),
            "policy_number":     fields.get("policy_number"),
            "treatment_date":    fields.get("treatment_date"),
            "claim_amount":      fields.get("claim_amount"),
            "ai_recommendation": state.get("recommendation"),
            "ai_confidence":     state.get("confidence"),
            "ai_reason":         state.get("primary_reason"),
            "human_decision":    state.get("human_decision"),
            "human_notes":       state.get("human_notes"),
            "final_decision":    state.get("final_decision"),
            "reviewer":          state.get("decision_by"),
            "decided_at":        state.get("decision_timestamp"),
        })

    local_path = state.get("local_json_path")
    if local_path and os.path.exists(local_path):
        with open(local_path) as f:
            json_bytes = f.read()
        st.download_button(
            label="⬇  Download Review Report (JSON)",
            data=json_bytes,
            file_name=f"{claim_id}_review.json",
            mime="application/json",
        )

    if state.get("s3_pdf_url"):
        st.info(f"Saved to S3: {state['s3_pdf_url']}")


# ── History tab ───────────────────────────────────────────────────────────────
def render_history_tab():
    history = st.session_state.claims_history

    if not history:
        st.markdown("""
        <div class="card" style="text-align:center;padding:3rem 2rem;">
            <div style="font-size:2.5rem;margin-bottom:1rem;">📋</div>
            <div style="font-size:1rem;font-weight:600;color:#374151;margin-bottom:6px;">No Claims Reviewed Yet</div>
            <div style="font-size:0.84rem;color:#64748B;">Process a claim from the <strong>Process New Claim</strong> tab to see history here.</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Stats strip
    approved   = sum(1 for c in history if c.get("final_decision") == "APPROVED")
    rejected   = sum(1 for c in history if c.get("final_decision") == "REJECTED")
    ai_correct = sum(
        1 for c in history
        if (c.get("ai_recommendation") == "APPROVE" and c.get("final_decision") == "APPROVED")
        or (c.get("ai_recommendation") == "REJECT"  and c.get("final_decision") == "REJECTED")
    )
    ai_rate = f"{ai_correct / len(history) * 100:.0f}%" if history else "—"

    st.markdown(f"""
    <div class="metric-strip" style="margin-bottom:1.2rem;">
        <div class="mcard">
            <div class="mcard-val">{len(history)}</div>
            <div class="mcard-label">Total Reviewed</div>
        </div>
        <div class="mcard">
            <div class="mcard-val" style="color:#065F46;">{approved}</div>
            <div class="mcard-label">Approved</div>
        </div>
        <div class="mcard">
            <div class="mcard-val" style="color:#991B1B;">{rejected}</div>
            <div class="mcard-label">Rejected</div>
        </div>
        <div class="mcard">
            <div class="mcard-val" style="color:#1D4ED8;">{ai_rate}</div>
            <div class="mcard-label">AI Agreement Rate</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    import pandas as pd
    df = pd.DataFrame(history).rename(columns={
        "claim_id":          "Claim ID",
        "patient_name":      "Patient",
        "claim_amount":      "Amount ($)",
        "ai_recommendation": "AI Recommendation",
        "final_decision":    "Final Decision",
        "reviewer":          "Reviewer",
        "timestamp":         "Decided At",
    })

    def color_decision(val):
        colors = {
            "APPROVED": "background-color:#ECFDF5;color:#065F46;font-weight:600;",
            "REJECTED": "background-color:#FEF2F2;color:#991B1B;font-weight:600;",
        }
        return colors.get(val, "")

    if "Final Decision" in df.columns:
        styler = df.style
        apply = styler.map if hasattr(styler, "map") else styler.applymap
        styled = apply(color_decision, subset=["Final Decision"])
        st.dataframe(styled, use_container_width=True, hide_index=True)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)


# ── About tab ─────────────────────────────────────────────────────────────────
def render_about_tab():
    st.markdown("""
    <div class="card">
        <div class="card-label">🏥 About ClaimIQ</div>
        <div style="font-size:0.9rem;color:#374151;line-height:1.7;">
            An AI-powered multi-agent system that automates healthcare insurance claim review.
            Each claim flows through three AI agents before a human reviewer makes the final call —
            keeping humans in the loop while dramatically reducing manual processing time.
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="card-label" style="margin-top:1rem;">⚙️ Technology Stack</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="tech-grid">
        <div class="tech-card">
            <div class="tech-icon">🔗</div>
            <div class="tech-name">LangGraph</div>
            <div class="tech-value">Agent orchestration &amp; StateGraph workflow</div>
        </div>
        <div class="tech-card">
            <div class="tech-icon">🤖</div>
            <div class="tech-name">OpenAI GPT-4o-mini</div>
            <div class="tech-value">Field extraction &amp; recommendation</div>
        </div>
        <div class="tech-card">
            <div class="tech-icon">🔍</div>
            <div class="tech-name">ChromaDB RAG</div>
            <div class="tech-value">Policy document retrieval</div>
        </div>
        <div class="tech-card">
            <div class="tech-icon">📄</div>
            <div class="tech-name">pdfplumber</div>
            <div class="tech-value">PDF text extraction</div>
        </div>
        <div class="tech-card">
            <div class="tech-icon">🖥️</div>
            <div class="tech-name">Streamlit</div>
            <div class="tech-value">Interactive web frontend</div>
        </div>
        <div class="tech-card">
            <div class="tech-icon">☁️</div>
            <div class="tech-name">AWS S3</div>
            <div class="tech-value">Cloud storage (optional)</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="card-label" style="margin-top:1.2rem;">🔄 Agent Pipeline</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="pipeline-flow">
        <div class="pf-node">📄 PDF Upload</div>
        <div class="pf-arrow">→</div>
        <div class="pf-node highlight">🔠 OCR Agent<br><span style="font-size:0.65rem;font-weight:400;">Extract fields</span></div>
        <div class="pf-arrow">→</div>
        <div class="pf-node highlight">✅ Validation<br><span style="font-size:0.65rem;font-weight:400;">ICD-10/CPT/NPI</span></div>
        <div class="pf-arrow">→</div>
        <div class="pf-node highlight">🎯 Recommendation<br><span style="font-size:0.65rem;font-weight:400;">RAG + LLM</span></div>
        <div class="pf-arrow">→</div>
        <div class="pf-node human">👤 Human Approval<br><span style="font-size:0.65rem;font-weight:400;">Final decision</span></div>
        <div class="pf-arrow">→</div>
        <div class="pf-node">💾 Save Result<br><span style="font-size:0.65rem;font-weight:400;">S3 / Local</span></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="card-label" style="margin-top:1.2rem;">📋 Supported Claim Scenarios</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="scenario-grid">
        <div class="scenario-chip">✅ Valid medical claims → Auto-approve</div>
        <div class="scenario-chip">🔴 Missing mandatory fields → Reject &amp; return</div>
        <div class="scenario-chip">🦷 Dental on medical plan → Reject</div>
        <div class="scenario-chip">🔬 Experimental treatments → Reject</div>
        <div class="scenario-chip">♻️ Duplicate claim detection → Reject</div>
        <div class="scenario-chip">🏥 Out-of-network provider → Manual review</div>
        <div class="scenario-chip">💰 High-value &gt; $25K → Senior review</div>
        <div class="scenario-chip">🧠 Mental health claims → Parity-covered</div>
        <div class="scenario-chip">🚑 Emergency surgery → Auto-approve</div>
    </div>
    """, unsafe_allow_html=True)


# ── Entry point ───────────────────────────────────────────────────────────────
def main():
    render_sidebar()
    render_main()


if __name__ == "__main__":
    main()
