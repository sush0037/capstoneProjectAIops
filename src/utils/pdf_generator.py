"""Generates synthetic insurance claim PDFs and policy documents for demo purposes."""

import os
import random
from pathlib import Path
from datetime import date, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT


CLAIMS_DATA = [
    {
        "filename": "claim_001_complete_valid.pdf",
        "claim_id": "CLM-2024-001",
        "patient_name": "John Smith",
        "dob": "1985-03-15",
        "policy_number": "POL-789456",
        "insurance_provider": "BlueCross BlueShield",
        "claim_date": "2024-11-10",
        "treatment_date": "2024-11-05",
        "diagnosis_code": "J18.9",
        "procedure_code": "99213",
        "provider_name": "Dr. Emily Carter",
        "provider_npi": "1234567890",
        "facility": "City General Hospital",
        "amount": 1250.00,
        "claim_type": "Medical",
        "description": "Office visit for community-acquired pneumonia, including examination and antibiotic prescription.",
        "scenario": "COMPLETE - should APPROVE",
    },
    {
        "filename": "claim_002_missing_fields.pdf",
        "claim_id": "CLM-2024-002",
        "patient_name": "Sarah Johnson",
        "dob": "",
        "policy_number": "POL-123789",
        "insurance_provider": "Aetna Health",
        "claim_date": "2024-11-12",
        "treatment_date": "2024-11-08",
        "diagnosis_code": "K35.80",
        "procedure_code": "",
        "provider_name": "Dr. Michael Brown",
        "provider_npi": "",
        "facility": "Riverside Medical Center",
        "amount": 8500.00,
        "claim_type": "Medical",
        "description": "Appendectomy procedure.",
        "scenario": "MISSING FIELDS (DOB, CPT code, NPI) - should flag for REVIEW",
    },
    {
        "filename": "claim_003_preexisting_condition.pdf",
        "claim_id": "CLM-2024-003",
        "patient_name": "Robert Davis",
        "dob": "1962-07-22",
        "policy_number": "POL-456123",
        "insurance_provider": "United Healthcare",
        "claim_date": "2024-11-15",
        "treatment_date": "2024-11-12",
        "diagnosis_code": "I25.10",
        "procedure_code": "93510",
        "provider_name": "Dr. Lisa Martinez",
        "provider_npi": "9876543210",
        "facility": "Heart & Vascular Institute",
        "amount": 45000.00,
        "claim_type": "Medical",
        "description": "Cardiac catheterization for chronic coronary artery disease. Pre-existing condition noted since 2018.",
        "scenario": "PRE-EXISTING - may be covered under ACA rules, APPROVE",
    },
    {
        "filename": "claim_004_dental_not_covered.pdf",
        "claim_id": "CLM-2024-004",
        "patient_name": "Jennifer Wilson",
        "dob": "1990-11-30",
        "policy_number": "POL-321654",
        "insurance_provider": "Cigna",
        "claim_date": "2024-11-18",
        "treatment_date": "2024-11-15",
        "diagnosis_code": "K02.1",
        "procedure_code": "D2740",
        "provider_name": "Dr. Kevin Lee",
        "provider_npi": "5647382910",
        "facility": "Smile Dental Clinic",
        "amount": 2800.00,
        "claim_type": "Dental",
        "description": "Crown restoration for dental caries on molar tooth. Patient has medical-only policy.",
        "scenario": "DENTAL on MEDICAL-ONLY policy - should REJECT",
    },
    {
        "filename": "claim_005_emergency_surgery.pdf",
        "claim_id": "CLM-2024-005",
        "patient_name": "Michael Thompson",
        "dob": "1978-05-14",
        "policy_number": "POL-654987",
        "insurance_provider": "Humana",
        "claim_date": "2024-11-20",
        "treatment_date": "2024-11-18",
        "diagnosis_code": "S72.001A",
        "procedure_code": "27245",
        "provider_name": "Dr. Susan Park",
        "provider_npi": "1122334455",
        "facility": "Memorial Emergency Center",
        "amount": 32000.00,
        "claim_type": "Medical",
        "description": "Emergency ORIF surgery for femoral neck fracture following automobile accident.",
        "scenario": "EMERGENCY - should APPROVE",
    },
    {
        "filename": "claim_006_duplicate_claim.pdf",
        "claim_id": "CLM-2024-006",
        "patient_name": "John Smith",
        "dob": "1985-03-15",
        "policy_number": "POL-789456",
        "insurance_provider": "BlueCross BlueShield",
        "claim_date": "2024-11-22",
        "treatment_date": "2024-11-05",
        "diagnosis_code": "J18.9",
        "procedure_code": "99213",
        "provider_name": "Dr. Emily Carter",
        "provider_npi": "1234567890",
        "facility": "City General Hospital",
        "amount": 1250.00,
        "claim_type": "Medical",
        "description": "Office visit for community-acquired pneumonia — RESUBMISSION. Note: Previously submitted as CLM-2024-001.",
        "scenario": "DUPLICATE of CLM-2024-001 - should REJECT",
    },
    {
        "filename": "claim_007_out_of_network.pdf",
        "claim_id": "CLM-2024-007",
        "patient_name": "Amanda Garcia",
        "dob": "1995-09-08",
        "policy_number": "POL-789012",
        "insurance_provider": "Oscar Health",
        "claim_date": "2024-11-25",
        "treatment_date": "2024-11-22",
        "diagnosis_code": "M54.5",
        "procedure_code": "97110",
        "provider_name": "Dr. Thomas Reed",
        "provider_npi": "6677889900",
        "facility": "Advanced PT & Rehab (Out-of-Network)",
        "amount": 3600.00,
        "claim_type": "Medical",
        "description": "Physical therapy for chronic low back pain, 12 sessions. Provider is OUT-OF-NETWORK.",
        "scenario": "OUT-OF-NETWORK - MANUAL REVIEW (partial coverage possible)",
    },
    {
        "filename": "claim_008_mental_health.pdf",
        "claim_id": "CLM-2024-008",
        "patient_name": "Daniel Kim",
        "dob": "2000-01-25",
        "policy_number": "POL-246813",
        "insurance_provider": "Anthem",
        "claim_date": "2024-11-28",
        "treatment_date": "2024-11-25",
        "diagnosis_code": "F32.1",
        "procedure_code": "90834",
        "provider_name": "Dr. Rachel Nguyen",
        "provider_npi": "3344556677",
        "facility": "Wellness Mental Health Clinic",
        "amount": 720.00,
        "claim_type": "Mental Health",
        "description": "Individual psychotherapy sessions (8 x 45-min) for major depressive disorder.",
        "scenario": "MENTAL HEALTH - covered under parity laws, APPROVE",
    },
    {
        "filename": "claim_009_experimental_treatment.pdf",
        "claim_id": "CLM-2024-009",
        "patient_name": "Patricia Allen",
        "dob": "1955-12-03",
        "policy_number": "POL-135792",
        "insurance_provider": "Molina Healthcare",
        "claim_date": "2024-12-01",
        "treatment_date": "2024-11-28",
        "diagnosis_code": "C50.911",
        "procedure_code": "0XHT03Z",
        "provider_name": "Dr. James Foster",
        "provider_npi": "8899001122",
        "facility": "OncoResearch Medical Center",
        "amount": 28000.00,
        "claim_type": "Medical",
        "description": "CAR-T cell therapy for metastatic breast cancer — experimental/investigational protocol, Phase II clinical trial.",
        "scenario": "EXPERIMENTAL TREATMENT - typically excluded, REJECT",
    },
    {
        "filename": "claim_010_high_amount_review.pdf",
        "claim_id": "CLM-2024-010",
        "patient_name": "William Turner",
        "dob": "1970-06-18",
        "policy_number": "POL-864209",
        "insurance_provider": "Kaiser Permanente",
        "claim_date": "2024-12-03",
        "treatment_date": "2024-11-30",
        "diagnosis_code": "N18.6",
        "procedure_code": "50360",
        "provider_name": "Dr. Angela White",
        "provider_npi": "2233445566",
        "facility": "University Transplant Center",
        "amount": 185000.00,
        "claim_type": "Medical",
        "description": "Kidney transplant surgery for end-stage renal disease. Includes surgeon, anesthesia, hospital facility, and 5-day ICU stay.",
        "scenario": "HIGH VALUE - covered but requires senior MANUAL REVIEW",
    },
]


def _styles():
    styles = getSampleStyleSheet()
    title = ParagraphStyle("ClaimTitle", parent=styles["Heading1"], fontSize=16, textColor=colors.HexColor("#1a3a6b"), spaceAfter=6, alignment=TA_CENTER)
    subtitle = ParagraphStyle("ClaimSubtitle", parent=styles["Normal"], fontSize=9, textColor=colors.grey, alignment=TA_CENTER, spaceAfter=12)
    section = ParagraphStyle("Section", parent=styles["Heading2"], fontSize=11, textColor=colors.HexColor("#1a3a6b"), spaceBefore=12, spaceAfter=4)
    body = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9, leading=14)
    scenario = ParagraphStyle("Scenario", parent=styles["Normal"], fontSize=8, textColor=colors.HexColor("#666666"), italic=True)
    return title, subtitle, section, body, scenario


def generate_claim_pdf(claim: dict, output_dir: str) -> str:
    path = os.path.join(output_dir, claim["filename"])
    doc = SimpleDocTemplate(path, pagesize=letter, leftMargin=0.75*inch, rightMargin=0.75*inch, topMargin=0.75*inch, bottomMargin=0.75*inch)
    title_s, subtitle_s, section_s, body_s, scenario_s = _styles()
    elements = []

    elements.append(Paragraph("HEALTHCARE INSURANCE CLAIM FORM", title_s))
    elements.append(Paragraph("Standard Uniform Billing Form — For Processing Purposes Only", subtitle_s))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a3a6b")))
    elements.append(Spacer(1, 0.1*inch))

    # Claim header
    header_data = [
        ["Claim ID:", claim["claim_id"], "Claim Date:", claim["claim_date"]],
        ["Insurance Provider:", claim["insurance_provider"], "Policy Number:", claim["policy_number"]],
        ["Claim Type:", claim["claim_type"], "Treatment Date:", claim["treatment_date"]],
    ]
    t = Table(header_data, colWidths=[1.5*inch, 2.3*inch, 1.5*inch, 2.3*inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0f4ff")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 0.15*inch))

    # Patient info
    elements.append(Paragraph("PATIENT INFORMATION", section_s))
    patient_data = [
        ["Patient Name:", claim["patient_name"], "Date of Birth:", claim["dob"] or "NOT PROVIDED"],
        ["Member ID:", f"MBR-{claim['policy_number'][-6:]}", "Group Number:", f"GRP-{random.randint(1000,9999)}"],
    ]
    t2 = Table(patient_data, colWidths=[1.5*inch, 2.3*inch, 1.5*inch, 2.3*inch])
    t2.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("PADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f9f9f9")]),
    ]))
    elements.append(t2)
    elements.append(Spacer(1, 0.15*inch))

    # Provider info
    elements.append(Paragraph("PROVIDER INFORMATION", section_s))
    provider_data = [
        ["Rendering Provider:", claim["provider_name"], "NPI Number:", claim["provider_npi"] or "NOT PROVIDED"],
        ["Facility Name:", claim["facility"], "Facility Type:", "Outpatient" if claim["amount"] < 10000 else "Inpatient"],
    ]
    t3 = Table(provider_data, colWidths=[1.5*inch, 2.3*inch, 1.5*inch, 2.3*inch])
    t3.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("PADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f9f9f9")]),
    ]))
    elements.append(t3)
    elements.append(Spacer(1, 0.15*inch))

    # Diagnosis & procedure
    elements.append(Paragraph("DIAGNOSIS AND PROCEDURE CODES", section_s))
    codes_data = [
        ["ICD-10 Diagnosis Code:", claim["diagnosis_code"] or "NOT PROVIDED", "CPT Procedure Code:", claim["procedure_code"] or "NOT PROVIDED"],
        ["Place of Service:", "11 - Office" if claim["amount"] < 5000 else "21 - Inpatient Hospital", "Type of Bill:", "131"],
    ]
    t4 = Table(codes_data, colWidths=[1.5*inch, 2.3*inch, 1.5*inch, 2.3*inch])
    t4.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("PADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f9f9f9")]),
    ]))
    elements.append(t4)
    elements.append(Spacer(1, 0.15*inch))

    # Billing
    elements.append(Paragraph("BILLING INFORMATION", section_s))
    billing_data = [
        ["Service Description:", claim["description"]],
        ["Billed Amount:", f"${claim['amount']:,.2f}"],
        ["Deductible Applied:", f"${min(claim['amount'] * 0.1, 500):.2f}"],
        ["Co-pay Amount:", "$30.00"],
        ["Net Claim Amount:", f"${claim['amount'] - min(claim['amount'] * 0.1, 500) - 30:.2f}"],
    ]
    t5 = Table(billing_data, colWidths=[2*inch, 5.6*inch])
    t5.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("PADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f9f9f9")]),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e8f0fe")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))
    elements.append(t5)
    elements.append(Spacer(1, 0.2*inch))

    # Scenario note (helps reviewers understand this is synthetic data)
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#cccccc")))
    elements.append(Spacer(1, 0.05*inch))
    elements.append(Paragraph(f"[SYNTHETIC DATA — Scenario: {claim['scenario']}]", scenario_s))

    doc.build(elements)
    return path


POLICY_DOCUMENTS = [
    {
        "filename": "policy_general_coverage.pdf",
        "title": "General Health Insurance Coverage Policy",
        "sections": [
            ("1. COVERED SERVICES", """
The following medical services are covered under standard health insurance plans subject to applicable deductibles, co-pays, and coinsurance:

1.1 PREVENTIVE CARE: Annual wellness visits, immunizations, cancer screenings, and preventive screenings are covered at 100% with no cost-sharing when provided by in-network providers.

1.2 EMERGENCY SERVICES: Emergency room visits, ambulance transportation, and emergency surgery are covered regardless of network status. Emergency is defined as a condition that would place the member's health in serious jeopardy without immediate treatment.

1.3 HOSPITALIZATION: Inpatient hospital stays, including room and board, nursing services, surgical procedures, and medically necessary diagnostic tests.

1.4 OUTPATIENT SERVICES: Office visits, outpatient surgery, laboratory tests, X-rays, and other diagnostic imaging (CT, MRI, ultrasound).

1.5 PRESCRIPTION DRUGS: Medications on the approved formulary are covered. Tier 1 (generic): $10 co-pay. Tier 2 (preferred brand): $40 co-pay. Tier 3 (non-preferred): $75 co-pay.

1.6 MENTAL HEALTH AND SUBSTANCE USE: Mental health therapy, psychiatric services, and substance use disorder treatment are covered at the same level as medical/surgical benefits (Mental Health Parity Act compliance).

1.7 MATERNITY AND NEWBORN CARE: Prenatal visits, labor and delivery, and newborn care are fully covered.

1.8 REHABILITATION SERVICES: Physical therapy, occupational therapy, and speech therapy are covered up to 60 visits per calendar year when medically necessary.

1.9 DURABLE MEDICAL EQUIPMENT (DME): Medically necessary equipment (wheelchairs, crutches, CPAP machines) is covered at 80% after deductible.
"""),
            ("2. EXCLUSIONS AND LIMITATIONS", """
2.1 COSMETIC PROCEDURES: Services performed primarily for cosmetic purposes are excluded unless medically necessary (e.g., reconstructive surgery following trauma).

2.2 EXPERIMENTAL AND INVESTIGATIONAL TREATMENTS: Treatments, procedures, or drugs that are experimental, investigational, or not yet approved by the FDA for the submitted diagnosis are excluded. Phase I–III clinical trials may be covered under specific circumstances per the Clinical Trial Coverage Act.

2.3 DENTAL AND VISION: Dental services (including orthodontia) and vision correction (glasses, contact lenses) are excluded from medical plans unless a separate dental/vision rider is purchased.

2.4 WEIGHT LOSS PROGRAMS: Commercial weight-loss programs, weight-loss surgery, and related treatments are excluded unless the member has a documented BMI ≥ 40 or ≥ 35 with comorbidities.

2.5 INFERTILITY: Fertility treatments (IVF, IUI, surrogacy) are excluded unless required by state mandate.

2.6 CUSTODIAL CARE: Long-term custodial care, personal care, or home health aide services that are not medically necessary are excluded.
"""),
            ("3. PRE-EXISTING CONDITIONS", """
3.1 COVERAGE MANDATE: Per the Affordable Care Act (ACA), pre-existing conditions cannot be used to deny coverage or increase premiums for plans subject to ACA requirements.

3.2 DEFINITION: A pre-existing condition is any health condition that existed before the effective date of the current insurance policy.

3.3 WAITING PERIODS: For grandfathered plans, a maximum 12-month waiting period may apply for pre-existing conditions not treated within the prior 6 months.

3.4 CONTINUOUS COVERAGE: Members with continuous prior coverage (no gap exceeding 63 days) are not subject to pre-existing condition waiting periods.
"""),
        ]
    },
    {
        "filename": "policy_claims_procedure.pdf",
        "title": "Claims Processing and Review Procedures",
        "sections": [
            ("1. CLAIMS SUBMISSION REQUIREMENTS", """
1.1 REQUIRED FIELDS: All claims must include: Member name, Member date of birth, Policy/Member ID number, Provider name and NPI number, Date of service, ICD-10 diagnosis code(s), CPT procedure code(s), Billed amount, Place of service code.

1.2 TIMELY FILING: Claims must be submitted within 365 days of the date of service. Late claims will be denied unless the member can demonstrate good cause for the delay.

1.3 ELECTRONIC SUBMISSION: Claims should be submitted electronically via EDI 837 format. Paper claims (CMS-1500 for professional, UB-04 for institutional) are accepted but may take 15–30 additional business days.

1.4 SUPPORTING DOCUMENTATION: For claims over $10,000, the following must be attached: operative reports, discharge summaries, or physician letter of medical necessity.
"""),
            ("2. AUTOMATED REVIEW CRITERIA", """
2.1 AUTO-APPROVAL THRESHOLDS: Claims meeting all of the following criteria are eligible for automatic approval:
- All required fields present and valid
- Claim amount under $5,000
- In-network provider
- Diagnosis and procedure codes are clinically aligned
- No history of duplicate claims for same date of service/provider/code

2.2 AUTO-DENIAL CRITERIA: Claims are automatically denied if:
- Submitted service is explicitly excluded (cosmetic, dental on medical plan, experimental)
- Duplicate claim detected (same member, provider, date, and code within 90 days)
- Provider NPI is not credentialed or inactive
- Claim submitted beyond timely filing deadline

2.3 MANUAL REVIEW ESCALATION: Claims must be escalated for manual review if:
- Claim amount exceeds $25,000
- Out-of-network provider is involved
- Missing required fields that cannot be verified
- Diagnosis/procedure code mismatch or clinical inconsistency
- Member disputes a prior denial
"""),
            ("3. FRAUD AND ABUSE DETECTION", """
3.1 RED FLAGS: The following indicators require fraud investigation:
- Claim from provider billing unusually high volumes
- Services billed for dates the member was hospitalized elsewhere
- Identical claims submitted by multiple providers for same dates
- Unbundling of procedure codes that should be billed together
- Upcoding: billing a higher-complexity code than the service rendered

3.2 DUPLICATE CLAIM POLICY: A claim is considered a duplicate if it has the same member ID, provider NPI, date of service, and primary procedure code as a previously processed claim. Duplicate claims are denied unless accompanied by documentation of error correction or resubmission authorization.
"""),
            ("4. APPEALS PROCESS", """
4.1 INTERNAL APPEAL: Members have 180 days from denial notification to file an internal appeal. The insurer must respond within 30 days (non-urgent) or 72 hours (urgent/expedited).

4.2 EXTERNAL REVIEW: If the internal appeal is denied, members may request an Independent Review Organization (IRO) review within 60 days.

4.3 OVERRIDE AUTHORITY: Senior claims reviewers may override automated recommendations when clinical evidence supports coverage. All overrides must be documented with reason code.
"""),
        ]
    },
    {
        "filename": "policy_network_and_benefits.pdf",
        "title": "Network Benefits and Out-of-Network Coverage",
        "sections": [
            ("1. IN-NETWORK BENEFITS", """
In-network providers have contracted rates with the insurance company, resulting in lower out-of-pocket costs for members.

1.1 COST SHARING — IN-NETWORK:
- Annual Deductible: $1,500 individual / $3,000 family
- Out-of-Pocket Maximum: $6,000 individual / $12,000 family
- Primary Care Visit Co-pay: $30
- Specialist Visit Co-pay: $60
- Urgent Care Co-pay: $75
- Emergency Room Co-pay: $350 (waived if admitted)
- Inpatient Hospital: 20% coinsurance after deductible
- Outpatient Surgery: 20% coinsurance after deductible
"""),
            ("2. OUT-OF-NETWORK BENEFITS", """
Out-of-network (OON) providers have not contracted with the insurer. Coverage is limited and subject to higher cost-sharing.

2.1 COST SHARING — OUT-OF-NETWORK:
- Annual Deductible: $3,000 individual / $6,000 family (separate from in-network)
- Out-of-Pocket Maximum: $12,000 individual / $24,000 family
- Coinsurance: 40% of allowed amount after OON deductible
- Balance Billing: Member is responsible for amounts above allowed/usual-and-customary rates

2.2 NO SURPRISE BILLING ACT: Emergency services and certain services at in-network facilities provided by OON providers are protected from balance billing under the No Surprises Act (effective Jan 1, 2022).

2.3 OUT-OF-NETWORK CLAIMS REVIEW: All OON claims over $500 are reviewed for:
- Medical necessity
- Confirmation that in-network provider was unavailable or inappropriate
- Correct application of allowed amount based on Medicare fee schedule or regional UCR rates
"""),
            ("3. PRIOR AUTHORIZATION", """
3.1 REQUIRED SERVICES: The following require prior authorization (PA):
- Inpatient hospital admissions (non-emergency)
- Outpatient surgeries above Tier 2 complexity
- High-cost specialty drugs (Tier 4/5)
- MRI, CT, PET scans (non-emergency)
- Home health care beyond 20 visits/year
- Durable medical equipment over $500
- Skilled nursing facility stays

3.2 PA REVIEW TIMELINE:
- Standard PA: decision within 3 business days
- Urgent PA: decision within 1 business day
- Concurrent review (inpatient stays): daily review with discharge planning

3.3 RETROACTIVE AUTHORIZATION: For emergency admissions, retroactive PA must be requested within 48 hours of admission. Failure to obtain retroactive PA may result in claim reduction or denial.
"""),
        ]
    },
]


def generate_policy_pdf(policy: dict, output_dir: str) -> str:
    path = os.path.join(output_dir, policy["filename"])
    doc = SimpleDocTemplate(path, pagesize=letter, leftMargin=0.75*inch, rightMargin=0.75*inch, topMargin=0.75*inch, bottomMargin=0.75*inch)
    title_s, subtitle_s, section_s, body_s, _ = _styles()
    elements = []

    elements.append(Paragraph(policy["title"].upper(), title_s))
    elements.append(Paragraph("Effective Date: January 1, 2024 | Version 2024.1", subtitle_s))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a3a6b")))
    elements.append(Spacer(1, 0.15*inch))

    for section_title, section_body in policy["sections"]:
        elements.append(Paragraph(section_title, section_s))
        for line in section_body.strip().split("\n"):
            line = line.strip()
            if line:
                elements.append(Paragraph(line, body_s))
        elements.append(Spacer(1, 0.1*inch))

    doc.build(elements)
    return path


def generate_all_synthetic_data(claims_dir: str, policy_dir: str) -> dict:
    """Generate all synthetic claims and policy PDFs. Returns counts."""
    Path(claims_dir).mkdir(parents=True, exist_ok=True)
    Path(policy_dir).mkdir(parents=True, exist_ok=True)

    claim_paths = [generate_claim_pdf(c, claims_dir) for c in CLAIMS_DATA]
    policy_paths = [generate_policy_pdf(p, policy_dir) for p in POLICY_DOCUMENTS]

    return {
        "claims_generated": len(claim_paths),
        "policies_generated": len(policy_paths),
        "claim_files": [os.path.basename(p) for p in claim_paths],
        "policy_files": [os.path.basename(p) for p in policy_paths],
    }
