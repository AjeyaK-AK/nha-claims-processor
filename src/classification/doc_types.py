"""
Canonical document type taxonomy for the claims processing system.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set

# ── Canonical type names ──────────────────────────────────────────────────────
ADMISSION_FORM          = "admission_form"
PREAUTH_FORM            = "preauthorization_form"
CONSENT_FORM            = "consent_form"
CASE_SHEET              = "case_sheet"
CLINICAL_NOTES          = "clinical_notes"
NURSING_NOTES           = "nursing_notes"
MEDICATION_CHART        = "medication_chart"
DISCHARGE_SUMMARY       = "discharge_summary"
OPERATIVE_NOTES         = "operative_notes"
ANESTHESIA_NOTES        = "anesthesia_notes"
LAB_INVESTIGATION       = "lab_investigation"
RADIOLOGY_REPORT        = "radiology_report"
XRAY_IMAGE              = "xray_image"
USG_REPORT              = "usg_report"
CT_MRI_REPORT           = "ct_mri_report"
ANGIOGRAPHY_REPORT      = "angiography_report"
PROCEDURE_REPORT        = "procedure_report"
ENDOSCOPY_REPORT        = "endoscopy_report"
IVP_REPORT              = "ivp_report"
BILL_INVOICE            = "bill_invoice"
FEEDBACK_FORM           = "feedback_form"
IDENTITY_DOCUMENT       = "identity_document"
BARCODE_STICKER         = "barcode_sticker"
IMPLANT_STICKER         = "implant_sticker"
GEOTAG_PHOTO            = "geotag_photo"
REFERRAL_LETTER         = "referral_letter"
PRESCRIPTION            = "prescription"
VITAL_CHART             = "vital_chart"
BEDSIDE_CHART           = "bedside_chart"
ENHANCEMENT_RECORD      = "enhancement_record"
BIRTH_PROOF             = "birth_proof"
OTHER                   = "other"

ALL_TYPES: Set[str] = {
    ADMISSION_FORM, PREAUTH_FORM, CONSENT_FORM, CASE_SHEET, CLINICAL_NOTES,
    NURSING_NOTES, MEDICATION_CHART, DISCHARGE_SUMMARY, OPERATIVE_NOTES,
    ANESTHESIA_NOTES, LAB_INVESTIGATION, RADIOLOGY_REPORT, XRAY_IMAGE,
    USG_REPORT, CT_MRI_REPORT, ANGIOGRAPHY_REPORT, PROCEDURE_REPORT,
    ENDOSCOPY_REPORT, IVP_REPORT, BILL_INVOICE, FEEDBACK_FORM,
    IDENTITY_DOCUMENT, BARCODE_STICKER, IMPLANT_STICKER, GEOTAG_PHOTO,
    REFERRAL_LETTER, PRESCRIPTION, VITAL_CHART, BEDSIDE_CHART,
    ENHANCEMENT_RECORD, BIRTH_PROOF, OTHER,
}

# ── Filename label → canonical type  (upper-cased partial match) ──────────────
FILENAME_LABEL_MAP: Dict[str, str] = {
    # Admission
    "ADMISSION": ADMISSION_FORM,
    "ADM": ADMISSION_FORM,
    "ADMIT": ADMISSION_FORM,
    "ADM1": ADMISSION_FORM,
    "ADDMIT": ADMISSION_FORM,

    # Pre-auth / PMJAY eligibility
    "PRE_AUTH": PREAUTH_FORM,
    "PREAUTH": PREAUTH_FORM,
    "AUTHORIZATION": PREAUTH_FORM,
    "AUTHORISATION": PREAUTH_FORM,
    "01_PRE_AUTHORIZATION_FORM": PREAUTH_FORM,
    "PRE_AUTHORIZATION": PREAUTH_FORM,
    "PRE_AUTH_FORM": PREAUTH_FORM,
    "PREAUTHFORM": PREAUTH_FORM,
    "PA": PREAUTH_FORM,              # Pre-Authorization shorthand
    "PA1": PREAUTH_FORM,
    "PA2": PREAUTH_FORM,
    "AUTH": PREAUTH_FORM,
    "AUTH_FORM": PREAUTH_FORM,
    "PMJAY_AUTH": PREAUTH_FORM,
    "ELIGIBILITY": PREAUTH_FORM,
    "ELIGIBILITY_FORM": PREAUTH_FORM,
    "PMJAY_ELIGIBILITY": PREAUTH_FORM,
    "AB_PMJAY": PREAUTH_FORM,        # Ayushman Bharat PMJAY form
    "ABPMJAY": PREAUTH_FORM,
    "PRE_CLAIM_FORM": PREAUTH_FORM,
    "PRE_CLAIM": PREAUTH_FORM,
    "CLAIM_FORM": PREAUTH_FORM,
    "EMPANELMENT_FORM": PREAUTH_FORM,
    "DECLARATION_FORM": PREAUTH_FORM,
    "DECLARATION": PREAUTH_FORM,
    "PAC_REPORT": ANESTHESIA_NOTES,

    # Consent
    "CONSENT": CONSENT_FORM,

    # Case sheet / clinical
    "CASE_SHEET": CASE_SHEET,
    "CASE_RECORD": CASE_SHEET,
    "CASESHEET": CASE_SHEET,
    "CASE": CASE_SHEET,
    "ALLCASE_SHEET": CASE_SHEET,
    "CASERECORD": CASE_SHEET,
    "CLINICAL_NOTE": CLINICAL_NOTES,
    "CLINICAL_NOTES": CLINICAL_NOTES,
    "CLINICAL": CLINICAL_NOTES,
    "ICU_NOTES": CLINICAL_NOTES,
    "ICP_NOTES": CLINICAL_NOTES,
    "ICP_CHART": CLINICAL_NOTES,
    "ICP": CLINICAL_NOTES,
    "PROGRESS_RECORD": CLINICAL_NOTES,
    "DOC": CLINICAL_NOTES,
    "NOTES": CLINICAL_NOTES,
    "OPD": CLINICAL_NOTES,
    "PRESCRIPTION": PRESCRIPTION,
    "TREATMENT": CLINICAL_NOTES,
    "TREATMENT_CHART": CLINICAL_NOTES,
    "INITIAL_ASSESSMENT": ADMISSION_FORM,

    # Nursing / bedside
    "NURSES_RECORD": NURSING_NOTES,
    "NURSING": NURSING_NOTES,
    "BEDSIDE": BEDSIDE_CHART,
    "BED": BEDSIDE_CHART,
    "TPR": VITAL_CHART,
    "VITALS": VITAL_CHART,
    "INTAKE_OUTPUT": VITAL_CHART,
    "CHART": VITAL_CHART,

    # Medication
    "MEDICATION_CHART": MEDICATION_CHART,
    "MEDICINE_BILL": MEDICATION_CHART,
    "DIS_MEDICINE": MEDICATION_CHART,
    "PHARMACY": PRESCRIPTION,

    # Discharge
    "DISCHARGE_SUMMARY": DISCHARGE_SUMMARY,
    "DISCHARGE": DISCHARGE_SUMMARY,
    "DIS": DISCHARGE_SUMMARY,
    "DISC": DISCHARGE_SUMMARY,
    "DISCHARGESUMMERRY": DISCHARGE_SUMMARY,
    "DETAILED_DISCHARGE_SUMMARY": DISCHARGE_SUMMARY,
    "SDS": DISCHARGE_SUMMARY,
    "SUM": DISCHARGE_SUMMARY,
    "SUMMARY": DISCHARGE_SUMMARY,
    "MS_DIS": DISCHARGE_SUMMARY,
    "MSDCL": DISCHARGE_SUMMARY,
    "SAV_DIS": DISCHARGE_SUMMARY,
    "DC": DISCHARGE_SUMMARY,
    "DDD": DISCHARGE_SUMMARY,
    "DISCHARGE_CARD": DISCHARGE_SUMMARY,

    # OT / Operative
    "OT_NOTE": OPERATIVE_NOTES,
    "OT_NOTES": OPERATIVE_NOTES,
    "OT": OPERATIVE_NOTES,
    "OTNOTE": OPERATIVE_NOTES,
    "OTNOTES": OPERATIVE_NOTES,
    "OPERATIVE_NOTE": OPERATIVE_NOTES,
    "OPERATIVE_NOTES": OPERATIVE_NOTES,
    "DETAILED_OPERATIVE_NOTES": OPERATIVE_NOTES,
    "POST_OP_PHOTO": OPERATIVE_NOTES,

    # Anesthesia
    "ANAESTH_SLIP": ANESTHESIA_NOTES,
    "ANAESTHESIA": ANESTHESIA_NOTES,
    "ANESTHESIA": ANESTHESIA_NOTES,

    # Lab / investigations
    "LAB_REPORTS": LAB_INVESTIGATION,
    "LAB": LAB_INVESTIGATION,
    "CBC": LAB_INVESTIGATION,
    "HB_REPORT": LAB_INVESTIGATION,
    "HBR": LAB_INVESTIGATION,
    "LFT": LAB_INVESTIGATION,
    "RFT": LAB_INVESTIGATION,
    "RFTLFT": LAB_INVESTIGATION,
    "PTINR": LAB_INVESTIGATION,
    "URINE": LAB_INVESTIGATION,
    "INVESTIGATION": LAB_INVESTIGATION,
    "INVES": LAB_INVESTIGATION,
    "INVEST": LAB_INVESTIGATION,
    "ALL_INVESTIGATIONS": LAB_INVESTIGATION,
    "ALL_REPORTS": LAB_INVESTIGATION,
    "INV": LAB_INVESTIGATION,
    "INVESTIGATIONS": LAB_INVESTIGATION,
    "NEW_CBC": LAB_INVESTIGATION,

    # Radiology / X-ray
    "ZX": XRAY_IMAGE,            # Z-axis X-ray or shorthand X-ray label
    "XRAY": XRAY_IMAGE,
    "X_RAY": XRAY_IMAGE,
    "X-RAY": XRAY_IMAGE,
    "XRAY_FILM": XRAY_IMAGE,
    "FILMS": XRAY_IMAGE,
    "X_RAY_PLATE": XRAY_IMAGE,
    "XRAY_CT_REPORT": CT_MRI_REPORT,
    "CT": CT_MRI_REPORT,
    "MRI": CT_MRI_REPORT,
    "CXRAY": XRAY_IMAGE,
    "CXR": XRAY_IMAGE,
    "CHEST_XRAY": XRAY_IMAGE,
    "CHEST_XRAY_REPORT": RADIOLOGY_REPORT,
    "POST_XRAY": XRAY_IMAGE,
    "POST_XRAY_FILM": XRAY_IMAGE,
    "POST_XRAY_FILM01": XRAY_IMAGE,
    "POST_XRAY_FILM_WITH_REPORT": RADIOLOGY_REPORT,
    "POST_OP_X_RAY": XRAY_IMAGE,
    "PRE_XRAY": XRAY_IMAGE,
    "XRAY_AND_REPORT": XRAY_IMAGE,
    "X_RAY_REPORT": RADIOLOGY_REPORT,
    "X_RAY_CHEST": XRAY_IMAGE,
    "X_RAY_CHEST_REPORT_0001": RADIOLOGY_REPORT,
    "POSTKUB": XRAY_IMAGE,
    "XRAYFILMREPORT": RADIOLOGY_REPORT,
    "RAMBHEJ_XRAY_FILM": XRAY_IMAGE,
    "SCAN_0002": XRAY_IMAGE,
    "XRY": XRAY_IMAGE,

    # USG
    "USG": USG_REPORT,
    "USG_REPORT": USG_REPORT,
    "USG_REPORT1": USG_REPORT,
    "USGREPORT": USG_REPORT,
    "ULTRA_SOUND": USG_REPORT,
    "USGFILM": USG_REPORT,
    "USG_IVP": IVP_REPORT,
    "USG_LFT": USG_REPORT,
    "IVP_USG": IVP_REPORT,
    "USG_IVP_BLOOD_R": IVP_REPORT,

    # IVP / KUB (Urology)
    "IVP": IVP_REPORT,
    "IVP_II": IVP_REPORT,
    "IVP_REPORT": IVP_REPORT,
    "IVP_REPORT_": IVP_REPORT,
    "IVP_X_RAY": IVP_REPORT,
    "IVP_X_RAY_WITH_REPORT": IVP_REPORT,
    "IVPFILM": IVP_REPORT,
    "KUB": IVP_REPORT,
    "GOVIND_IVP": IVP_REPORT,
    "MALA_DEVIV_IVP": IVP_REPORT,
    "RAVINDRA_YADAV_IVP": IVP_REPORT,
    "PAC_REPORT_OT_NOTES_AND_XRAY_REPORT": ANESTHESIA_NOTES,

    # Angiography / CAG
    "CAG": ANGIOGRAPHY_REPORT,
    "CAG_01": ANGIOGRAPHY_REPORT,
    "CAG_02": ANGIOGRAPHY_REPORT,
    "CAG_REPORT": ANGIOGRAPHY_REPORT,
    "CAG_REPORT_001": ANGIOGRAPHY_REPORT,
    "CAG_IMAGE": ANGIOGRAPHY_REPORT,
    "CAG_IMAGES": ANGIOGRAPHY_REPORT,
    "CAG_IMAGES_COMPRESSED": ANGIOGRAPHY_REPORT,
    "CAG_DAIGARM": ANGIOGRAPHY_REPORT,
    "PRE_ANGIOGRAM": ANGIOGRAPHY_REPORT,
    "PRE_ANGIOGRAM_2": ANGIOGRAPHY_REPORT,
    "PRE_ANGIOGRAPHY_2": ANGIOGRAPHY_REPORT,
    "POST_ANGIOGRAM": ANGIOGRAPHY_REPORT,
    "POST_CAG_DAIGARM": ANGIOGRAPHY_REPORT,
    "POST_ANGI_REPORT": ANGIOGRAPHY_REPORT,
    "POST_STENT": PROCEDURE_REPORT,
    "CAG_STILL_IMAGE": ANGIOGRAPHY_REPORT,
    "CAG_STILL_IMAGE_": ANGIOGRAPHY_REPORT,

    # PTCA / Procedure
    "PTCA": PROCEDURE_REPORT,
    "PTCA_REPORT": PROCEDURE_REPORT,
    "PTCA_REPORT_001": PROCEDURE_REPORT,
    "PTCA_REPORT_DIAG": PROCEDURE_REPORT,
    "PTCA_IMAGE": PROCEDURE_REPORT,
    "PTCA_IMAGES": PROCEDURE_REPORT,
    "PTCA_STENT": PROCEDURE_REPORT,
    "POST_PTCA_STILL_IMAGE": PROCEDURE_REPORT,

    # Endoscopy
    "ENDOSCOPY": ENDOSCOPY_REPORT,

    # Billing
    "BILL": BILL_INVOICE,
    "HOSPITAL_BILL": BILL_INVOICE,
    "BILL_SETTLEMENT": BILL_INVOICE,
    "INVOICE": BILL_INVOICE,
    "MEDICINE_BILL": BILL_INVOICE,

    # Feedback
    "FEEDBACK": FEEDBACK_FORM,
    "FEEDBACK_FORM": FEEDBACK_FORM,
    "FEED_BACK_FORM": FEEDBACK_FORM,
    "FEED": FEEDBACK_FORM,
    "FEDD": FEEDBACK_FORM,
    "FB": FEEDBACK_FORM,
    "DF": DISCHARGE_SUMMARY,      # Discharge Form (common hospital shorthand)

    # Identity
    "ADHAR": IDENTITY_DOCUMENT,
    "AADHAR": IDENTITY_DOCUMENT,
    "CARD": IDENTITY_DOCUMENT,
    "PMAM": IDENTITY_DOCUMENT,
    "ID": IDENTITY_DOCUMENT,
    "PP": IDENTITY_DOCUMENT,      # Patient Photo (common label in PMJAY claims)
    "PH": IDENTITY_DOCUMENT,      # Patient Health card / photo
    "PMJAY_CARD": IDENTITY_DOCUMENT,
    "E_CARD": IDENTITY_DOCUMENT,
    "ECARD": IDENTITY_DOCUMENT,

    # Barcode / sticker
    "BARCODE": BARCODE_STICKER,
    "IMPLANT": IMPLANT_STICKER,
    "STICKER": IMPLANT_STICKER,

    # Geotag
    "GEOTAG": GEOTAG_PHOTO,
    "PHOTO": GEOTAG_PHOTO,
    "PIC": GEOTAG_PHOTO,

    # Enhancement record
    "ENHANCEMENT_RECORD": ENHANCEMENT_RECORD,
    # ENC = Encounter/Clinical notes (NOT enhancement record — common hospital shorthand)
    "ENC": CLINICAL_NOTES,

    # Birth proof – treated as identity document for NHA claim purposes
    "BIRTH_PROOF": IDENTITY_DOCUMENT,
    "BIRTH_PROOF_BBY_OF_JESMINA_DARLONG": IDENTITY_DOCUMENT,
    "BABYOFJESMINADARLONG": IDENTITY_DOCUMENT,
    "BABYOFJESMINADARLONGDOCUMENT_11ZON": IDENTITY_DOCUMENT,

    # Discharge Summary – additional real-world label variants
    "DP": DISCHARGE_SUMMARY,         # Discharge Papers
    "DB": DISCHARGE_SUMMARY,         # Discharge Brief
    "MS": DISCHARGE_SUMMARY,         # Medical Summary
    "SUDHAN_DB": DISCHARGE_SUMMARY,
    "DIS_DAR_": DISCHARGE_SUMMARY,
    "DISCHARGE__SUMMARY": DISCHARGE_SUMMARY,
    "DISCHARGE_SUMMRY": DISCHARGE_SUMMARY,
    "DISCHARGE_SUMMARY_GENERAL": DISCHARGE_SUMMARY,
    "DISCHARGE-1": DISCHARGE_SUMMARY,
    "AVTAR_SINGH_DISCHARGE_DECLARATION": DISCHARGE_SUMMARY,
    "PT_AVTAR_SINGH_DISCHARGE_SUMMARY": DISCHARGE_SUMMARY,
    "DEVI_DAS_DISCHARGE_SUMMARY": DISCHARGE_SUMMARY,
    "PRAVAKAR_NAIK_DIS": DISCHARGE_SUMMARY,
    "PRAVAKAR_NAIK_DIS_SUM": DISCHARGE_SUMMARY,
    "PUSHPA_DISCHARGE_2_1": DISCHARGE_SUMMARY,
    "PUSHPA_DISCHARGE_2_11": DISCHARGE_SUMMARY,
    "PUSHPA_DISCHARGE_2_2": DISCHARGE_SUMMARY,
    "PUSHPA_DISCHARGE_2_6": DISCHARGE_SUMMARY,

    # Clinical Notes – additional real-world label variants
    "CN": CASE_SHEET,           # CN = Case Notes / Clinical Notes = IP case sheet in Indian hospitals
    "CL": CLINICAL_NOTES,
    "CLINIC": CLINICAL_NOTES,
    "DEVI_DAS_CLINICAL_NOTES": CLINICAL_NOTES,
    "PT_AVTAR_FEVER_PROFILE_UPDATE": CLINICAL_NOTES,
    "CHOI_TSERING_DOCS_COMPRESSED": CLINICAL_NOTES,
    "23RD_JAN_DOC_NOTES_ICU": CLINICAL_NOTES,
    "DEVI_DAS_MHIS_DECLARATION": CLINICAL_NOTES,
    "PRAVAKAR_NAIK_CLINICAL_11ZON": CLINICAL_NOTES,

    # Feedback – additional variants
    "FD": FEEDBACK_FORM,
    "FF": FEEDBACK_FORM,
    "F_IPD": FEEDBACK_FORM,
    "FEED_BAC_": FEEDBACK_FORM,
    "FEED_BACK__": FEEDBACK_FORM,
    "DEVI_DAS_FEEDBACK": FEEDBACK_FORM,
    "CHOI_TSERING_FEEDBACK": FEEDBACK_FORM,
    "PRAVAKAR_NAIK_FEEDBACK": FEEDBACK_FORM,
    "PT_AVTAR_SINGH_NEGI_FEEDBACK": FEEDBACK_FORM,

    # Identity document – patient photo / name-as-filename patterns
    "N": IDENTITY_DOCUMENT,
    "N3": IDENTITY_DOCUMENT,
    "N4": IDENTITY_DOCUMENT,
    "AANITA": IDENTITY_DOCUMENT,
    "ANNITA": IDENTITY_DOCUMENT,
    "ANITA_D": IDENTITY_DOCUMENT,
    "ANITA_DHJH": IDENTITY_DOCUMENT,
    "ANITA_FDGH": IDENTITY_DOCUMENT,
    "NASEEMA": IDENTITY_DOCUMENT,
    "AMBIGADEVI": IDENTITY_DOCUMENT,
    "ADIT": IDENTITY_DOCUMENT,
    "PRAVAKAR_NAIK_ID": IDENTITY_DOCUMENT,

    # Case sheet – additional variants
    "CS": CASE_SHEET,
    "CR": CASE_SHEET,
    "CR2": CASE_SHEET,
    "CR3": CASE_SHEET,
    "BHT": CASE_SHEET,              # Bed Head Ticket
    "CASERECORD1": CASE_SHEET,
    "CASE_": CASE_SHEET,

    # Nursing notes – additional variants
    "NN1": NURSING_NOTES,
    "SNT": NURSING_NOTES,

    # Lab investigations – name-prefixed variants
    "DEVI_DAS_CBC": LAB_INVESTIGATION,
    "DEVI_DAS_INVESTIGATION": LAB_INVESTIGATION,
    "PRINT_REPORT": LAB_INVESTIGATION,
    "PARBATI_MAHANANDA_REPORTS": LAB_INVESTIGATION,
    "PT_AVTAR_SINGH_BLOOD_INVESTIGATION_REPORT": LAB_INVESTIGATION,
    "PT_AVTAR_URINE_RE": LAB_INVESTIGATION,
    "REPORT": LAB_INVESTIGATION,

    # USG – name-prefixed variants
    "MALTI_USG": USG_REPORT,
    "PRIYA_MISHRA_USG": USG_REPORT,
    "SASMITA_USG": USG_REPORT,
    "ULTRA_SOUND_": USG_REPORT,

    # IVP / KUB – KUV suffix = KUB/IVP film
    "MALATIKUV": IVP_REPORT,
    "GOVINDKUV": IVP_REPORT,
    "MALA_DEVIKUV": IVP_REPORT,
    "RAVINDRA_YADAVKUV": IVP_REPORT,

    # X-Ray – name-prefixed variants
    "PRAVAKAR_NAIK_XRAY": XRAY_IMAGE,
    "PRAVAKAR_NAIK_X-RAY": XRAY_IMAGE,
    "PHOOLPATTIDEVIPREXRAY": XRAY_IMAGE,

    # Operative notes – name-prefixed variants
    "OP_SLIP_": OPERATIVE_NOTES,
    "OTN": OPERATIVE_NOTES,
    "PRAVAKAR_NAIK_OT_11ZON": OPERATIVE_NOTES,

    # Bill / invoice – name-prefixed
    "DEVI_DAS_BILL": BILL_INVOICE,
    "PRAVAKAR_NAIK_BILL": BILL_INVOICE,
    "PRAVAKAR_NAIK_INVOICE": BILL_INVOICE,

    # Admission
    "ADD": ADMISSION_FORM,
    "AVTAR_SINGH_NEGI_ADMISSION_FORM": ADMISSION_FORM,

    # Medication chart
    "DEVI_DAS_MEDICATION_CHART": MEDICATION_CHART,
    "DIS-MEDICINE": MEDICATION_CHART,
    "MED_SUM": MEDICATION_CHART,   # Medicine Summary

    # Enhancement record – date-suffixed variants
    "DEVI_DAS_ENHANCE": ENHANCEMENT_RECORD,
    "ENHANCEMENT_RECORD_11_12": ENHANCEMENT_RECORD,
    "ENHANCEMENT_RECORD_13": ENHANCEMENT_RECORD,
    "ENHANCEMENT_RECORD_14": ENHANCEMENT_RECORD,
    "ENHANCEMENT_RECORD_15_16": ENHANCEMENT_RECORD,
    "ENHANCEMENT_RECORD_17": ENHANCEMENT_RECORD,
    "ENHANCEMENT_RECORD_18": ENHANCEMENT_RECORD,

    # Justification
    "JUSTIFICATION": OTHER,
    "JUSTICATION": OTHER,
    "HISSSS": OTHER,
    "ISSS": OTHER,
    "HISS": OTHER,
}

# ── Keyword lists for content-based classification ────────────────────────────
# Each list has a "STRONG" prefix group (highly distinctive) followed by
# common supporting signals. The scorer weights the first N as 2× hits.
CONTENT_KEYWORDS: Dict[str, List[str]] = {
    DISCHARGE_SUMMARY: [
        # Strong / distinctive
        "discharge summary", "date of discharge", "condition at discharge",
        "discharged on", "discharge date", "final diagnosis", "follow up advice",
        "discharge instructions", "discharge note",
        # Supporting
        "date of admission", "length of stay", "summary of treatment",
        "treatment given", "follow up", "advised to follow",
    ],
    ADMISSION_FORM: [
        # Strong
        "admission form", "date of admission", "admitted on",
        "initial assessment", "triage note", "pre-operative assessment",
        "pre operative", "presenting complaints", "ipd admission",
        # Supporting
        "patient admitted", "admitting diagnosis", "admn.", "admission date",
        "ward admission", "emergency admission",
    ],
    OPERATIVE_NOTES: [
        # Strong
        "operative note", "operation theatre", "ot note", "surgery performed",
        "intraoperative findings", "post operative", "scrub nurse",
        "anaesthesia given", "procedure performed",
        # Supporting
        "surgeon", "incision", "blood loss", "haemostasis", "sutures",
        "closure", "specimen sent", "instrument count",
    ],
    CLINICAL_NOTES: [
        # Strong
        "progress note", "daily note", "doctor note", "clinical notes",
        "ward rounds", "icу note", "icp note", "patient complains",
        "on examination", "vitals noted",
        # Supporting
        "bp:", "pulse:", "spo2", "temperature:", "respiratory rate",
        "plan:", "assessment:", "impression:",
    ],
    NURSING_NOTES: [
        # Strong
        "nurses note", "nursing note", "nursing record", "nurse observation",
        "shift note", "handover note",
        # Supporting
        "patient comfortable", "iv site", "urine output", "bowel movement",
        "wound dressing", "patient resting", "nurse signature",
    ],
    MEDICATION_CHART: [
        # Strong
        "medication chart", "drug chart", "treatment chart",
        "drug name", "dosage", "route", "frequency",
        # Supporting
        "tablets", "injection", "iv drip", "administered", "dispensed",
        "prescribed", "syrup", "capsules",
    ],
    LAB_INVESTIGATION: [
        # Strong
        "laboratory report", "haemoglobin", "wbc", "platelets",
        "complete blood count", "cbc", "culture sensitivity",
        "serum creatinine", "blood urea nitrogen",
        # Supporting
        "sgpt", "sgot", "bilirubin", "hba1c", "urine report",
        "serum", "rbc", "neutrophils", "lymphocytes", "hb:",
        "reference range", "normal range", "pathologist",
    ],
    RADIOLOGY_REPORT: [
        # Strong
        "radiology report", "x-ray report", "radiological findings",
        "impression:", "opinion:", "chest pa view", "findings:",
        # Supporting
        "radiologist", "bones appear", "soft tissue", "cardiac silhouette",
        "no pneumothorax", "lungs clear", "fracture", "radiograph",
    ],
    XRAY_IMAGE: [
        # Strong
        "x-ray", "xray", "chest pa", "ap view", "x ray film",
        # Supporting
        "radiograph", "no pneumothorax", "fracture seen",
    ],
    ANGIOGRAPHY_REPORT: [
        # Strong
        "coronary angiography", "coronary angiogram", "cag report",
        "lad", "lcx", "rca", "stenosis", "ejection fraction",
        "ptca", "stent deployed", "catheterization",
        # Supporting
        "angiogram", "cath no", "cardiovascular", "cardiologist",
        "left anterior descending", "right coronary", "occlusion",
        "drug eluting stent", "balloon",
    ],
    PROCEDURE_REPORT: [
        # Strong
        "ptca report", "percutaneous coronary", "coronary intervention",
        "phacoemulsification", "intraocular lens", "iol implanted",
        "cataract extraction", "endoscopy report",
        # Supporting
        "stent", "guidewire", "catheter lab", "balloon",
        "procedure performed", "procedure note",
    ],
    USG_REPORT: [
        # Strong
        "ultrasonography", "ultrasound report", "usg report", "usg abdomen",
        "sonography", "echogenicity",
        # Supporting
        "liver size", "gall bladder", "kidneys", "no free fluid",
        "uterus", "ovary", "probe", "scan findings",
    ],
    IVP_REPORT: [
        # Strong
        "intravenous pyelogram", "ivp", "kub film", "ivp report",
        "collecting system", "pelvi-calyceal",
        # Supporting
        "ureter", "bladder outline", "kidney shadow", "contrast",
    ],
    CT_MRI_REPORT: [
        # Strong
        "ct scan", "mri report", "computed tomography", "magnetic resonance",
        "ct report", "mri brain", "ct abdomen", "mri spine",
        # Supporting
        "axial sections", "coronal", "sagittal", "contrast enhanced",
        "hounsfield", "t1w", "t2w",
    ],
    ENDOSCOPY_REPORT: [
        # Strong
        "endoscopy report", "colonoscopy", "upper gi endoscopy", "oesophagoscopy",
        # Supporting
        "mucosa", "polyp", "biopsy taken", "scope", "gastroscopy",
    ],
    BILL_INVOICE: [
        # Strong
        "hospital bill", "patient bill", "invoice", "total amount",
        "bill of charges", "package amount", "final bill",
        # Supporting
        "room charges", "ot charges", "balance due", "amount paid",
        "net payable", "grand total",
    ],
    IDENTITY_DOCUMENT: [
        # Strong
        "aadhaar", "aadhar", "pmjay id", "beneficiary id", "uid:",
        # Supporting
        "enrolment", "date of birth", "voter id", "ration card",
    ],
    FEEDBACK_FORM: [
        # Strong
        "feedback form", "patient satisfaction", "patient feedback",
        "rate your experience", "how was your stay",
        # Supporting
        "grievance", "suggestion", "overall experience",
        "would you recommend", "staff behaviour",
    ],
    IMPLANT_STICKER: [
        # Strong
        "ref:", "lot:", "serial no", "serial number", "model no",
        "manufactured by", "udi", "implant",
        # Supporting
        "catalog", "batch no", "device", "sterile", "expiry",
    ],
    BARCODE_STICKER: [
        # Strong
        "ref:", "lot:", "batch no", "barcode",
        # Supporting
        "udi", "manufactured", "serial no",
    ],
    CONSENT_FORM: [
        # Strong
        "consent form", "i hereby consent", "informed consent",
        "i agree to", "patient consent", "guardian consent",
        # Supporting
        "voluntary consent", "risks explained", "procedure consent",
        "declaration", "patient/guardian signature",
    ],
    CASE_SHEET: [
        # Strong
        "case sheet", "case record", "bed head ticket", "bht",
        "ipd case", "clinical history", "chief complaint",
        # Supporting
        "past history", "personal history", "family history",
        "systemic examination", "local examination",
        "provisional diagnosis", "differential diagnosis",
    ],
    PREAUTH_FORM: [
        # Strong
        "pre authorisation", "pre authorization", "preauth",
        "pmjay pre", "authorization form", "eligibility form",
        "ab pmjay", "ayushman bharat", "pre-auth", "pre auth form",
        # Supporting
        "beneficiary name", "pmjay id", "hospital empanelment",
        "package code", "estimated cost", "treatment package",
        "empanelment code", "pre-authorization request", "claim authorization",
    ],
    ANESTHESIA_NOTES: [
        # Strong
        "anaesthesia record", "anesthesia record", "pre anaesthetic",
        "intraoperative anaesthesia", "pac report",
        # Supporting
        "airway assessment", "asa grade", "intubation",
        "spinal anaesthesia", "general anaesthesia", "isoflurane",
    ],
    VITAL_CHART: [
        # Strong
        "vital chart", "tpr chart", "vital signs chart",
        "temperature pulse respiration", "intake output chart",
        # Supporting
        "bp chart", "pulse oximetry", "daily vitals", "tpr",
    ],
    BEDSIDE_CHART: [
        # Strong
        "bedside chart", "bed chart", "patient care chart",
        # Supporting
        "nursing chart", "ward chart",
    ],
    REFERRAL_LETTER: [
        # Strong
        "referral letter", "referred to", "refer to", "referral note",
        # Supporting
        "for further management", "higher centre",
    ],
    PRESCRIPTION: [
        # Strong
        "prescription", "rx", "rx:", "prescribed by",
        # Supporting
        "take tablet", "take capsule", "advised tablet",
    ],
    ENHANCEMENT_RECORD: [
        # Strong
        "enhancement record", "enhancement request", "treatment enhancement",
        # Supporting
        "additional treatment", "enhancement amount",
    ],
    GEOTAG_PHOTO: [
        # Strong
        "geotag", "geotagged photo", "location photo",
        # Supporting
        "latitude", "longitude", "coordinates",
    ],
    BIRTH_PROOF: [
        # Strong
        "birth certificate", "date of birth proof",
        # Supporting
        "born on", "municipal birth",
    ],
}
