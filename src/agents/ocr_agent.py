"""OCR Agent: extract raw text from claim PDF and structure it into fields via LLM."""

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = [
    "claim_id", "patient_name", "date_of_birth", "policy_number",
    "insurance_provider", "claim_date", "treatment_date",
    "diagnosis_code", "procedure_code", "provider_name",
    "provider_npi", "facility_name", "claim_amount", "claim_type", "description",
]


def _extract_pdf_text(pdf_path: str) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
        return "\n".join(pages)
    except Exception as e:
        logger.error(f"pdfplumber failed: {e}")
        return ""


def _llm():
    from langchain_openai import ChatOpenAI
    from src.config import OPENAI_API_KEY, OPENAI_MODEL
    return ChatOpenAI(model=OPENAI_MODEL, temperature=0, openai_api_key=OPENAI_API_KEY)


_EXTRACTION_PROMPT = """\
You are a healthcare insurance data extraction assistant.
Extract all relevant fields from the following insurance claim document text.
Return ONLY a valid JSON object with these exact keys (use null for missing/unclear values):

{{
  "claim_id": "string",
  "patient_name": "string",
  "date_of_birth": "YYYY-MM-DD or null",
  "policy_number": "string or null",
  "insurance_provider": "string or null",
  "claim_date": "YYYY-MM-DD or null",
  "treatment_date": "YYYY-MM-DD or null",
  "diagnosis_code": "ICD-10 code string or null",
  "procedure_code": "CPT code string or null",
  "provider_name": "string or null",
  "provider_npi": "10-digit string or null",
  "facility_name": "string or null",
  "claim_amount": number or null,
  "claim_type": "Medical | Dental | Vision | Mental Health | Prescription | Other",
  "description": "string or null"
}}

CLAIM DOCUMENT TEXT:
{text}

Return only the JSON object, no explanation.
"""


def run_ocr_agent(pdf_path: str) -> dict[str, Any]:
    """
    Extract and structure claim data from a PDF.
    Returns a dict with keys: raw_text, extracted_fields, ocr_log, error.
    """
    raw_text = _extract_pdf_text(pdf_path)
    if not raw_text.strip():
        return {
            "raw_text": "",
            "extracted_fields": {},
            "ocr_log": "ERROR: Could not extract text from PDF",
            "error": "PDF text extraction failed — document may be image-based or corrupted",
        }

    try:
        llm = _llm()
        prompt = _EXTRACTION_PROMPT.format(text=raw_text[:6000])  # Limit for token safety
        response = llm.invoke(prompt)
        content = response.content.strip()

        # Strip markdown code fences if present
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)

        extracted_fields = json.loads(content)

        # Ensure all expected keys exist
        for key in REQUIRED_FIELDS:
            extracted_fields.setdefault(key, None)

        present = sum(1 for k in REQUIRED_FIELDS if extracted_fields.get(k) not in (None, "", "null"))
        ocr_log = f"Extracted {present}/{len(REQUIRED_FIELDS)} required fields from {pdf_path}"
        logger.info(ocr_log)

        return {
            "raw_text": raw_text,
            "extracted_fields": extracted_fields,
            "ocr_log": ocr_log,
            "error": None,
        }

    except json.JSONDecodeError as e:
        logger.error(f"LLM returned invalid JSON: {e}")
        return {
            "raw_text": raw_text,
            "extracted_fields": {},
            "ocr_log": f"ERROR: LLM returned non-parseable JSON — {e}",
            "error": str(e),
        }
    except Exception as e:
        logger.error(f"OCR agent failed: {e}")
        return {
            "raw_text": raw_text,
            "extracted_fields": {},
            "ocr_log": f"ERROR: {e}",
            "error": str(e),
        }
