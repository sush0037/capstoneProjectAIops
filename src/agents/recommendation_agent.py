"""Recommendation Agent: use RAG + LLM to generate claim approval/rejection recommendation."""

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_RECOMMENDATION_PROMPT = """\
You are a healthcare insurance claim review specialist. Analyze the claim below using the policy context provided.

CLAIM DETAILS:
{claim_json}

VALIDATION REPORT:
{validation_summary}

RELEVANT POLICY CONTEXT:
{policy_context}

Based on the claim details, validation findings, and policy rules, provide your recommendation.

Respond with ONLY a valid JSON object in this exact format:
{{
  "recommendation": "APPROVE" | "REJECT" | "MANUAL_REVIEW",
  "confidence": "HIGH" | "MEDIUM" | "LOW",
  "primary_reason": "One clear sentence explaining the main reason for your decision",
  "supporting_reasons": ["reason1", "reason2", "reason3"],
  "policy_citations": ["relevant policy rule or section cited"],
  "risk_flags": ["any fraud or compliance concerns, or empty list"],
  "suggested_action": "What the human reviewer should do next"
}}

Decision guidelines:
- APPROVE: All mandatory fields present, valid codes, in-network, no exclusions, amount ≤ $25,000
- REJECT: Explicit exclusion applies (dental on medical plan, experimental treatment, duplicate, expired timely filing)
- MANUAL_REVIEW: Missing some fields, out-of-network, amount > $25,000, code mismatch, or complex clinical scenario

Return only the JSON object.
"""


def _llm():
    from langchain_openai import ChatOpenAI
    from src.config import OPENAI_API_KEY, OPENAI_MODEL
    return ChatOpenAI(model=OPENAI_MODEL, temperature=0, openai_api_key=OPENAI_API_KEY)


def run_recommendation_agent(
    extracted_fields: dict,
    validation_result: dict,
    policy_context: str,
) -> dict[str, Any]:
    """
    Generate an AI recommendation for a claim.
    Returns: recommendation, confidence, primary_reason, supporting_reasons,
             policy_citations, risk_flags, suggested_action, error.
    """
    try:
        # Quick rule-based pre-filters (fast path before LLM)
        quick_result = _quick_rule_check(extracted_fields, validation_result)
        if quick_result:
            logger.info(f"Quick rule matched: {quick_result['recommendation']}")
            return {**quick_result, "error": None}

        # LLM-based recommendation
        llm = _llm()
        prompt = _RECOMMENDATION_PROMPT.format(
            claim_json=json.dumps(extracted_fields, indent=2, default=str),
            validation_summary=validation_result.get("validation_summary", "No validation data"),
            policy_context=policy_context[:4000],  # Limit context size
        )
        response = llm.invoke(prompt)
        content = response.content.strip()

        # Strip markdown fences if present
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)

        result = json.loads(content)
        result["error"] = None

        # Ensure all keys exist
        result.setdefault("recommendation", "MANUAL_REVIEW")
        result.setdefault("confidence", "LOW")
        result.setdefault("primary_reason", "Unable to determine")
        result.setdefault("supporting_reasons", [])
        result.setdefault("policy_citations", [])
        result.setdefault("risk_flags", [])
        result.setdefault("suggested_action", "Escalate to senior reviewer")

        logger.info(f"AI recommendation: {result['recommendation']} (confidence: {result['confidence']})")
        return result

    except json.JSONDecodeError as e:
        logger.error(f"Recommendation agent returned invalid JSON: {e}")
        return _fallback_recommendation(validation_result, str(e))
    except Exception as e:
        logger.error(f"Recommendation agent failed: {e}")
        return _fallback_recommendation(validation_result, str(e))


def _quick_rule_check(fields: dict, validation: dict) -> dict | None:
    """Fast rule-based checks that don't require LLM."""
    desc = str(fields.get("description", "")).lower()
    claim_type = str(fields.get("claim_type", "")).lower()
    amount = fields.get("claim_amount", 0) or 0

    try:
        amount = float(amount)
    except (TypeError, ValueError):
        amount = 0

    # Duplicate claim detection
    if "resubmission" in desc or "duplicate" in desc or "previously submitted" in desc:
        return {
            "recommendation": "REJECT",
            "confidence": "HIGH",
            "primary_reason": "Claim appears to be a duplicate resubmission of a previously processed claim.",
            "supporting_reasons": ["Duplicate claim detected from description text", "Same service likely already billed"],
            "policy_citations": ["Claims Procedure §3.2: Duplicate claims are denied"],
            "risk_flags": ["Potential duplicate billing — verify with records"],
            "suggested_action": "Cross-check claim ID and date of service against processed claims history before final denial.",
        }

    # Dental on medical plan
    if claim_type == "dental" and not any(w in desc for w in ["medical necessity", "reconstructive", "trauma"]):
        return {
            "recommendation": "REJECT",
            "confidence": "HIGH",
            "primary_reason": "Dental services are excluded from medical-only insurance plans.",
            "supporting_reasons": ["Claim type is Dental", "No medical necessity documentation present"],
            "policy_citations": ["Coverage Policy §2.3: Dental services excluded from medical plans"],
            "risk_flags": [],
            "suggested_action": "Advise member to submit to their dental insurance carrier.",
        }

    # Experimental treatment
    if any(w in desc for w in ["experimental", "investigational", "clinical trial", "phase i", "phase ii", "phase iii", "phase 1", "phase 2", "phase 3"]):
        return {
            "recommendation": "REJECT",
            "confidence": "HIGH",
            "primary_reason": "Experimental and investigational treatments are excluded from standard policy coverage.",
            "supporting_reasons": ["Description explicitly mentions experimental/clinical trial nature"],
            "policy_citations": ["Coverage Policy §2.2: Experimental treatments excluded"],
            "risk_flags": [],
            "suggested_action": "Inform member of clinical trial coverage exception options and appeal rights.",
        }

    # High-value claim
    if amount >= 25000:
        return {
            "recommendation": "MANUAL_REVIEW",
            "confidence": "HIGH",
            "primary_reason": f"Claim amount (${amount:,.2f}) exceeds the $25,000 automatic review threshold.",
            "supporting_reasons": [f"Amount ${amount:,.2f} requires senior reviewer sign-off", "High-value claims require additional clinical documentation"],
            "policy_citations": ["Claims Procedure §2.3: Claims over $25,000 require manual senior reviewer approval"],
            "risk_flags": [],
            "suggested_action": "Route to senior claims specialist. Request operative reports and medical necessity documentation.",
        }

    # Missing mandatory fields
    missing_mandatory = validation.get("missing_mandatory_fields", [])
    if missing_mandatory:
        return {
            "recommendation": "REJECT",
            "confidence": "HIGH",
            "primary_reason": f"Claim is missing {len(missing_mandatory)} mandatory field(s): {', '.join(missing_mandatory)}.",
            "supporting_reasons": ["Incomplete claims cannot be processed", f"Missing: {', '.join(missing_mandatory)}"],
            "policy_citations": ["Claims Procedure §1.1: All required fields must be present for processing"],
            "risk_flags": [],
            "suggested_action": "Return claim to provider/member with request for missing information. Provide 30-day correction window.",
        }

    return None


def _fallback_recommendation(validation: dict, error_msg: str) -> dict:
    """Safe fallback when LLM fails."""
    missing = validation.get("missing_mandatory_fields", [])
    recommendation = "REJECT" if missing else "MANUAL_REVIEW"
    return {
        "recommendation": recommendation,
        "confidence": "LOW",
        "primary_reason": f"AI recommendation engine encountered an error. Human review required. ({error_msg[:100]})",
        "supporting_reasons": ["Automated recommendation unavailable"],
        "policy_citations": [],
        "risk_flags": ["AI processing error — verify manually"],
        "suggested_action": "Route to human reviewer for manual assessment.",
        "error": error_msg,
    }
