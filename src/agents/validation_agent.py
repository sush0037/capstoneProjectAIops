"""Validation Agent: check extracted claim fields for completeness and consistency."""

import re
import logging
from datetime import date, datetime
from typing import Any

logger = logging.getLogger(__name__)

MANDATORY_FIELDS = [
    "patient_name", "policy_number", "claim_date",
    "treatment_date", "diagnosis_code", "claim_amount",
]

IMPORTANT_FIELDS = [
    "date_of_birth", "provider_npi", "procedure_code",
    "provider_name", "facility_name", "insurance_provider",
]

ICD10_PATTERN = re.compile(r"^[A-Z]\d{2}(\.\d+)?$", re.IGNORECASE)
CPT_PATTERN = re.compile(r"^\d{4,5}[A-Z]?$")
NPI_PATTERN = re.compile(r"^\d{10}$")


def _is_blank(value: Any) -> bool:
    return value in (None, "", "null", "NOT PROVIDED", "N/A")


def _validate_date(date_str: Any) -> bool:
    if _is_blank(date_str):
        return False
    try:
        datetime.strptime(str(date_str), "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _validate_amount(amount: Any) -> bool:
    try:
        return float(amount) > 0
    except (TypeError, ValueError):
        return False


def run_validation_agent(extracted_fields: dict) -> dict:
    """
    Validate extracted claim fields.
    Returns a dict with: missing_mandatory, missing_important, inconsistencies,
    validation_passed, severity, validation_summary.
    """
    missing_mandatory = []
    missing_important = []
    inconsistencies = []
    field_status = {}

    # Check mandatory fields
    for field in MANDATORY_FIELDS:
        val = extracted_fields.get(field)
        if _is_blank(val):
            missing_mandatory.append(field)
            field_status[field] = "missing_mandatory"
        else:
            field_status[field] = "ok"

    # Check important fields
    for field in IMPORTANT_FIELDS:
        val = extracted_fields.get(field)
        if _is_blank(val):
            missing_important.append(field)
            field_status[field] = "missing_optional"
        else:
            field_status[field] = "ok"

    # Format validation
    diag = extracted_fields.get("diagnosis_code")
    if not _is_blank(diag) and not ICD10_PATTERN.match(str(diag)):
        inconsistencies.append(f"Diagnosis code '{diag}' does not match ICD-10 format (e.g. J18.9)")

    proc = extracted_fields.get("procedure_code")
    if not _is_blank(proc) and not CPT_PATTERN.match(str(proc)):
        inconsistencies.append(f"Procedure code '{proc}' does not match CPT format (e.g. 99213)")

    npi = extracted_fields.get("provider_npi")
    if not _is_blank(npi) and not NPI_PATTERN.match(str(npi)):
        inconsistencies.append(f"NPI '{npi}' must be exactly 10 digits")

    if not _validate_amount(extracted_fields.get("claim_amount")):
        if extracted_fields.get("claim_amount") is not None:
            inconsistencies.append(f"Claim amount '{extracted_fields.get('claim_amount')}' is not a valid positive number")

    # Date logic
    claim_date = extracted_fields.get("claim_date")
    treatment_date = extracted_fields.get("treatment_date")
    if _validate_date(claim_date) and _validate_date(treatment_date):
        cd = datetime.strptime(claim_date, "%Y-%m-%d").date()
        td = datetime.strptime(treatment_date, "%Y-%m-%d").date()
        if td > cd:
            inconsistencies.append(f"Treatment date ({treatment_date}) is after claim date ({claim_date})")
        delta = (date.today() - td).days
        if delta > 365:
            inconsistencies.append(f"Treatment date ({treatment_date}) is more than 365 days ago — may exceed timely filing limit")

    # Determine severity
    if missing_mandatory:
        severity = "HIGH"
        validation_passed = False
    elif len(missing_important) >= 3 or inconsistencies:
        severity = "MEDIUM"
        validation_passed = True  # Can still proceed with warnings
    else:
        severity = "LOW"
        validation_passed = True

    # Build summary
    lines = []
    if not missing_mandatory and not missing_important and not inconsistencies:
        lines.append("All fields validated successfully. No issues found.")
    else:
        if missing_mandatory:
            lines.append(f"MANDATORY MISSING ({len(missing_mandatory)}): {', '.join(missing_mandatory)}")
        if missing_important:
            lines.append(f"Optional missing ({len(missing_important)}): {', '.join(missing_important)}")
        if inconsistencies:
            lines.append(f"Inconsistencies ({len(inconsistencies)}):")
            for inc in inconsistencies:
                lines.append(f"  - {inc}")

    validation_summary = " | ".join(lines)

    logger.info(f"Validation: passed={validation_passed}, severity={severity}, mandatory_missing={missing_mandatory}")

    return {
        "missing_mandatory_fields": missing_mandatory,
        "missing_important_fields": missing_important,
        "inconsistencies": inconsistencies,
        "field_status": field_status,
        "validation_passed": validation_passed,
        "severity": severity,
        "validation_summary": validation_summary,
    }
