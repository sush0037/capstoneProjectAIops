"""
LangGraph-based multi-agent claim review workflow.

Pipeline:  START → ocr → validation → recommendation → finalize → END
Human approval is captured outside the graph (Streamlit UI) and passed into finalize_claim.
"""

import logging
from datetime import datetime
from typing import Optional, TypedDict, List, Any

from langgraph.graph import StateGraph, START, END

logger = logging.getLogger(__name__)


# ── State schema ─────────────────────────────────────────────────────────────

class ClaimState(TypedDict):
    # Input
    claim_id: str
    pdf_path: str

    # OCR agent
    raw_text: str
    extracted_fields: dict
    ocr_log: str

    # Validation agent
    missing_mandatory_fields: List[str]
    missing_important_fields: List[str]
    inconsistencies: List[str]
    field_status: dict
    validation_passed: bool
    severity: str
    validation_summary: str

    # RAG
    policy_context: str
    policy_sources: List[str]

    # Recommendation agent
    recommendation: str           # APPROVE | REJECT | MANUAL_REVIEW
    confidence: str               # HIGH | MEDIUM | LOW
    primary_reason: str
    supporting_reasons: List[str]
    policy_citations: List[str]
    risk_flags: List[str]
    suggested_action: str

    # Human decision (set after workflow via finalize_claim)
    human_decision: Optional[str]
    human_notes: Optional[str]
    final_decision: Optional[str]
    decision_by: Optional[str]
    decision_timestamp: Optional[str]

    # Storage
    s3_pdf_url: Optional[str]
    s3_json_url: Optional[str]
    local_json_path: Optional[str]

    # Metadata
    processing_log: List[str]
    current_stage: str
    started_at: str
    completed_at: Optional[str]
    error: Optional[str]


# ── Node implementations ──────────────────────────────────────────────────────

def _log(state: ClaimState, msg: str) -> List[str]:
    ts = datetime.now().strftime("%H:%M:%S")
    entry = f"[{ts}] {msg}"
    logger.info(entry)
    return state.get("processing_log", []) + [entry]


def ocr_node(state: ClaimState) -> ClaimState:
    from src.agents.ocr_agent import run_ocr_agent
    log = _log(state, f"OCR Agent: processing {state['pdf_path']}")
    result = run_ocr_agent(state["pdf_path"])

    if result.get("error"):
        log = log + [f"OCR ERROR: {result['error']}"]

    return {
        **state,
        "raw_text": result.get("raw_text", ""),
        "extracted_fields": result.get("extracted_fields", {}),
        "ocr_log": result.get("ocr_log", ""),
        "processing_log": log + [result.get("ocr_log", "")],
        "current_stage": "ocr_complete",
        "error": result.get("error"),
    }


def validation_node(state: ClaimState) -> ClaimState:
    from src.agents.validation_agent import run_validation_agent
    log = _log(state, "Validation Agent: checking fields and consistency")

    if state.get("error"):
        return {**state, "current_stage": "validation_skipped", "processing_log": log}

    result = run_validation_agent(state.get("extracted_fields", {}))
    return {
        **state,
        "missing_mandatory_fields": result["missing_mandatory_fields"],
        "missing_important_fields": result["missing_important_fields"],
        "inconsistencies": result["inconsistencies"],
        "field_status": result["field_status"],
        "validation_passed": result["validation_passed"],
        "severity": result["severity"],
        "validation_summary": result["validation_summary"],
        "processing_log": log + [f"Validation: {result['validation_summary'][:120]}"],
        "current_stage": "validation_complete",
    }


def recommendation_node(state: ClaimState) -> ClaimState:
    from src.agents.recommendation_agent import run_recommendation_agent
    from src.rag.retriever import retrieve_policy_context
    from src.config import CHROMA_PERSIST_DIR

    log = _log(state, "Recommendation Agent: querying policy RAG and generating recommendation")

    if state.get("error") and not state.get("extracted_fields"):
        return {
            **state,
            "recommendation": "MANUAL_REVIEW",
            "confidence": "LOW",
            "primary_reason": "OCR failed — cannot process automatically",
            "processing_log": log + ["Recommendation skipped: OCR error"],
            "current_stage": "recommendation_complete",
        }

    # Build RAG query from claim fields
    fields = state.get("extracted_fields", {})
    query_parts = [
        f"claim type: {fields.get('claim_type', 'unknown')}",
        f"diagnosis: {fields.get('diagnosis_code', 'unknown')}",
        f"procedure: {fields.get('procedure_code', 'unknown')}",
        f"amount: {fields.get('claim_amount', 'unknown')}",
        f"description: {fields.get('description', '')}",
    ]
    rag_query = " | ".join(query_parts)

    policy_context, policy_sources = retrieve_policy_context(rag_query, CHROMA_PERSIST_DIR)

    validation_result = {
        "missing_mandatory_fields": state.get("missing_mandatory_fields", []),
        "validation_summary": state.get("validation_summary", ""),
    }

    result = run_recommendation_agent(fields, validation_result, policy_context)

    return {
        **state,
        "policy_context": policy_context,
        "policy_sources": policy_sources,
        "recommendation": result.get("recommendation", "MANUAL_REVIEW"),
        "confidence": result.get("confidence", "LOW"),
        "primary_reason": result.get("primary_reason", ""),
        "supporting_reasons": result.get("supporting_reasons", []),
        "policy_citations": result.get("policy_citations", []),
        "risk_flags": result.get("risk_flags", []),
        "suggested_action": result.get("suggested_action", ""),
        "processing_log": log + [f"AI Recommendation: {result.get('recommendation')} ({result.get('confidence')} confidence)"],
        "current_stage": "awaiting_human_approval",
    }


# ── Graph assembly ─────────────────────────────────────────────────────────────

def build_pipeline() -> Any:
    graph = StateGraph(ClaimState)
    graph.add_node("ocr", ocr_node)
    graph.add_node("validation", validation_node)
    graph.add_node("recommendation", recommendation_node)

    graph.add_edge(START, "ocr")
    graph.add_edge("ocr", "validation")
    graph.add_edge("validation", "recommendation")
    graph.add_edge("recommendation", END)

    return graph.compile()


# Singleton pipeline (lazy init)
_pipeline = None


def get_pipeline():
    global _pipeline
    if _pipeline is None:
        _pipeline = build_pipeline()
    return _pipeline


# ── Public API ────────────────────────────────────────────────────────────────

def run_claim_pipeline(pdf_path: str, claim_id: Optional[str] = None) -> ClaimState:
    """
    Run the full automated pipeline (OCR → Validation → Recommendation).
    Returns ClaimState at stage 'awaiting_human_approval'.
    """
    if not claim_id:
        claim_id = f"CLM-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    initial_state: ClaimState = {
        "claim_id": claim_id,
        "pdf_path": pdf_path,
        "raw_text": "",
        "extracted_fields": {},
        "ocr_log": "",
        "missing_mandatory_fields": [],
        "missing_important_fields": [],
        "inconsistencies": [],
        "field_status": {},
        "validation_passed": False,
        "severity": "UNKNOWN",
        "validation_summary": "",
        "policy_context": "",
        "policy_sources": [],
        "recommendation": "",
        "confidence": "",
        "primary_reason": "",
        "supporting_reasons": [],
        "policy_citations": [],
        "risk_flags": [],
        "suggested_action": "",
        "human_decision": None,
        "human_notes": None,
        "final_decision": None,
        "decision_by": None,
        "decision_timestamp": None,
        "s3_pdf_url": None,
        "s3_json_url": None,
        "local_json_path": None,
        "processing_log": [],
        "current_stage": "started",
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "error": None,
    }

    pipeline = get_pipeline()
    result = pipeline.invoke(initial_state)
    return result


def finalize_claim(state: ClaimState, human_decision: str, human_notes: str = "", reviewer: str = "Human Reviewer") -> ClaimState:
    """
    Record the human reviewer's decision and persist to storage.
    human_decision: "APPROVE" | "REJECT" | "OVERRIDE_APPROVE" | "OVERRIDE_REJECT"
    """
    from src.utils.s3_utils import save_claim_result
    import copy

    state = copy.deepcopy(state)
    ts = datetime.now().isoformat()

    # Determine final decision
    if human_decision in ("APPROVE", "OVERRIDE_APPROVE"):
        final = "APPROVED"
    elif human_decision in ("REJECT", "OVERRIDE_REJECT"):
        final = "REJECTED"
    else:
        final = "PENDING"

    state["human_decision"] = human_decision
    state["human_notes"] = human_notes
    state["final_decision"] = final
    state["decision_by"] = reviewer
    state["decision_timestamp"] = ts
    state["completed_at"] = ts
    state["current_stage"] = "completed"
    state["processing_log"] = state.get("processing_log", []) + [
        f"[{ts}] Human decision: {human_decision} → Final: {final} (by {reviewer})"
    ]

    # Persist
    locations = save_claim_result(
        claim_id=state["claim_id"],
        result={k: v for k, v in state.items() if k != "raw_text"},  # Omit raw text to keep JSON small
        pdf_path=state.get("pdf_path"),
    )
    state["s3_pdf_url"] = locations.get("s3_pdf")
    state["s3_json_url"] = locations.get("s3_json")
    state["local_json_path"] = locations.get("local_json")

    logger.info(f"Claim {state['claim_id']} finalized: {final}")
    return state
