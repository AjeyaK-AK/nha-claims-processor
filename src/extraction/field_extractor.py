"""
Field Extractor: pulls structured data from OCR text using regex patterns.
Returns ExtractedFields with ProvenanceRef for each extracted value.
"""
from __future__ import annotations

import re
import logging
from datetime import date, datetime
from typing import List, Optional, Tuple

from src.extraction.models import ExtractedFields, ProvenanceRef, BoundingBox
from src.classification.doc_types import (
    DISCHARGE_SUMMARY, ADMISSION_FORM, OPERATIVE_NOTES,
    CLINICAL_NOTES, BILL_INVOICE,
)

log = logging.getLogger(__name__)

# ── Date patterns ─────────────────────────────────────────────────────────────
_DATE_PATTERNS = [
    # DD-Mon-YYYY  e.g. 02-Feb-2026
    r"\b(\d{1,2})[\/\-\.]([A-Za-z]{3})[\/\-\.](\d{4})\b",
    # DD/MM/YYYY
    r"\b(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})\b",
    # YYYY-MM-DD
    r"\b(\d{4})[\/\-\.](\d{2})[\/\-\.](\d{2})\b",
    # DD Mon YYYY  e.g. 02 Feb 2026
    r"\b(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})\b",
    # Mon YYYY  e.g. Feb 2026 (day-less — treat as 1st of month)
    r"\b([A-Za-z]{3})\s+(\d{4})\b",
]

_MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "january": 1, "february": 2, "march": 3, "april": 4,
    "june": 6, "july": 7, "august": 8, "september": 9,
    "october": 10, "november": 11, "december": 12,
}


def _parse_date(text: str) -> Optional[date]:
    for pattern in _DATE_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if not m:
            continue
        g = m.groups()
        try:
            if len(g) == 2:
                # Mon YYYY
                mon_str, yr_str = g
                month = _MONTH_MAP.get(mon_str.lower())
                if month and yr_str.isdigit():
                    return date(int(yr_str), month, 1)
            elif len(g) == 3:
                a, b, c = g
                # YYYY-MM-DD
                if len(a) == 4:
                    return date(int(a), int(b), int(c))
                # DD-Mon-YYYY or DD Mon YYYY
                if b.isalpha():
                    month = _MONTH_MAP.get(b.lower())
                    if month:
                        return date(int(c), month, int(a))
                # DD/MM/YYYY
                else:
                    d, mo, yr = int(a), int(b), int(c)
                    if 1 <= d <= 31 and 1 <= mo <= 12:
                        return date(yr, mo, d)
        except (ValueError, KeyError):
            continue
    return None


def _find_dates_in_text(text: str) -> List[date]:
    """Find all parseable dates in a chunk of text."""
    found = []
    for pattern in _DATE_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            g = m.groups()
            try:
                if len(g) == 2:
                    mon_str, yr_str = g
                    month = _MONTH_MAP.get(mon_str.lower())
                    if month and yr_str.isdigit():
                        d = date(int(yr_str), month, 1)
                        if 2000 <= d.year <= 2030:
                            found.append(d)
                    continue
                a, b, c = g
                if len(a) == 4:
                    d = date(int(a), int(b), int(c))
                elif b.isalpha():
                    month = _MONTH_MAP.get(b.lower())
                    if month:
                        d = date(int(c), month, int(a))
                    else:
                        continue
                else:
                    dd, mo, yr = int(a), int(b), int(c)
                    if not (1 <= dd <= 31 and 1 <= mo <= 12 and 2000 <= yr <= 2030):
                        continue
                    d = date(yr, mo, dd)
                if 2000 <= d.year <= 2030:
                    found.append(d)
            except (ValueError, KeyError):
                continue
    return found


# ── Context-based date extractors ─────────────────────────────────────────────

def _extract_contextual_date(text: str, context_keywords: List[str]) -> Optional[date]:
    """
    Look for a date within 250 characters after any context keyword,
    or 80 characters before it (date often appears before the label in Indian forms).
    """
    text_lower = text.lower()
    for kw in context_keywords:
        idx = text_lower.find(kw)
        if idx == -1:
            continue
        # Wide window: 80 chars before keyword + 250 chars after
        window = text[max(0, idx - 80): idx + 250]
        d = _parse_date(window)
        if d:
            return d
    return None


ADMISSION_KEYWORDS  = [
    "date of admission", "admitted on", "admission date", "doa:", "d.o.a",
    "admn.", "admission", "admit date", "date admitted", "date of admission:",
    "adm. date", "adm date", "ipd date", "in-patient date", "registration date",
]
DISCHARGE_KEYWORDS  = [
    "date of discharge", "discharged on", "discharge date", "dod:", "d.o.d",
    "discharge", "date of discharge:", "dis. date", "dis date",
]
PROCEDURE_KEYWORDS  = [
    "date of procedure", "date of surgery", "procedure date",
    "date of operation", "dos:", "date of ot", "angiography done on",
    "ptca done on", "surgery done on", "operation date", "surgery date",
    "date of operation:", "procedure done on", "intervention date",
]


# ── Field extraction patterns ──────────────────────────────────────────────────

_PATIENT_NAME_PATTERNS = [
    r"patient\s*(?:name)?\s*[:\-]\s*([A-Za-z][A-Za-z\s\.]{2,40})",
    r"name\s+of\s+patient\s*[:\-]\s*([A-Za-z][A-Za-z\s\.]{2,40})",
    r"mr\.?\s+([A-Za-z][A-Za-z\s\.]{2,30})",
    r"mrs\.?\s+([A-Za-z][A-Za-z\s\.]{2,30})",
    r"ms\.?\s+([A-Za-z][A-Za-z\s\.]{2,30})",
    r"beneficiary\s+name\s*[:\-]\s*([A-Za-z][A-Za-z\s\.]{2,40})",
]

_PATIENT_ID_PATTERNS = [
    r"pmjay\s*(?:id|no\.?)?\s*[:\-]?\s*([0-9A-Z\-]{8,20})",
    r"beneficiary\s*id\s*[:\-]\s*([0-9A-Z\-]{8,20})",
    r"patient\s*id\s*[:\-]\s*([0-9A-Z\-]{6,20})",
    r"uhid\s*[:\-]\s*([0-9A-Z\-]{4,20})",
    r"ipd\s*no\.?\s*[:\-]\s*([0-9A-Z\-]{4,20})",
]

_AMOUNT_PATTERNS = [
    r"(?:total|grand\s*total|package\s*amount|billed\s*amount)\s*[:\-]?\s*(?:rs\.?|inr|₹)?\s*([\d,]+(?:\.\d{1,2})?)",
    r"(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d{1,2})?)",
]

_AGE_PATTERNS = [
    r"\bage\s*[:\-/]?\s*(\d{1,3})\s*(?:years?|yrs?)?\b",
    r"(\d{1,3})\s*years?\s*(?:old|/|male|female|m\b|f\b)",
]

_GENDER_PATTERNS = [
    r"\b(male|female|m\b|f\b)\b",
    r"sex\s*[:\-]\s*(male|female|m|f)\b",
    r"gender\s*[:\-]\s*(male|female|m|f)\b",
]

_DIAGNOSIS_PATTERNS = [
    # "Final Diagnosis : <text>" — capture up to newline or next section
    r"(?:final\s+)?diagnosis\s*[:\-]\s*(.{3,120}?)(?:\n|$|procedure|operation|indication)",
    # "Pre Operative Diagnosis: <text>"
    r"pre\s*[-\s]?operative\s+diagnosis\s*[:\-]\s*(.{3,100}?)(?:\n|$)",
    # ICD codes
    r"icd[-\s]?(?:10)?\s*(?:code)?\s*[:\-]\s*([A-Z]\d{2}\.?\d{0,2})",
    r"([A-Z]\d{2}\.?\d{0,2})\s*[-–]\s*[A-Z]",
]

# Keyword-based diagnosis signals (document contains these → infer diagnosis)
_DIAGNOSIS_KEYWORDS_MAP = {
    "oa knee": "Osteoarthritis Knee",
    "osteoarthritis knee": "Osteoarthritis Knee",
    "osteoarthritis hip": "Osteoarthritis Hip",
    "total knee": "Total Knee Arthroplasty",
    "total hip": "Total Hip Arthroplasty",
    "knee replacement": "Total Knee Arthroplasty",
    "hip replacement": "Total Hip Arthroplasty",
    "cad": "Coronary Artery Disease",
    "coronary artery disease": "Coronary Artery Disease",
    "stemi": "ST Elevation Myocardial Infarction",
    "nstemi": "Non-ST Elevation Myocardial Infarction",
    "angina": "Angina",
    "cholelithiasis": "Cholelithiasis",
    "cholecystitis": "Cholecystitis",
    "gallstone": "Cholelithiasis",
    "appendicitis": "Acute Appendicitis",
    "cataract": "Cataract",
    "renal calculus": "Renal Calculus",
    "kidney stone": "Renal Calculus",
    "ureteric calculus": "Ureteric Calculus",
    "hysterectomy": "Uterine Pathology requiring Hysterectomy",
    "fibroid": "Uterine Fibroids",
    "prolapse": "Uterine Prolapse",
}

_HOSPITAL_PATTERNS = [
    r"(?:hospital|clinic|medical centre|health centre)\s*[:\-]?\s*([A-Za-z][A-Za-z\s&\.]{3,60}?)(?:\n|,|\.)",
    r"^([A-Za-z][A-Za-z\s&\.]{5,60}(?:hospital|clinic|medical))",
]

_DOCTOR_PATTERNS = [
    r"dr\.?\s+([A-Za-z][A-Za-z\s\.]{2,40})",
    r"(?:treating\s+physician|surgeon|doctor)\s*[:\-]\s*([A-Za-z][A-Za-z\s\.]{3,40})",
]

# Words that indicate a captured "name" is actually an OCR sentence fragment, not a real name
_NAME_NOISE_WORDS = {
    "and", "the", "by", "of", "during", "your", "for", "from", "in", "at", "on",
    "to", "with", "this", "that", "was", "has", "have", "been", "are", "is",
    "measures", "kidney", "condition", "grade", "activity", "left", "right",
    "upper", "lower", "please", "doctor", "hospital", "patient", "treatment",
    "following", "discharge", "admission", "investigation",
}

_HOSPITAL_NOISE_WORDS = {
    "during", "your", "by", "treating", "physician", "invoice", "tax",
    "the", "ally", "ste", "all",
}


def _is_valid_patient_name(val: str) -> bool:
    """Return True only if the extracted value looks like a real patient name."""
    if not val or len(val) < 3:
        return False
    words = val.split()
    if len(words) > 6:
        return False
    # Reject if any word is a known noise/function word
    for w in words:
        if w.lower() in _NAME_NOISE_WORDS:
            return False
    # First word must start with a capital letter
    if not words[0][0].isupper():
        return False
    return True


def _is_valid_hospital_name(val: str) -> bool:
    """Return True only if extracted value looks like a real hospital name."""
    if not val or len(val) < 4:
        return False
    # Strip leading/trailing whitespace and collapse internal \n
    val = val.split("\n")[0].strip()
    words = val.split()
    for w in words[:3]:   # Check first 3 words for noise
        if w.lower() in _HOSPITAL_NOISE_WORDS:
            return False
    return True


def _first_match(patterns: List[str], text: str) -> Optional[str]:
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE | re.MULTILINE)
        if m:
            return m.group(1).strip()
    return None


def _make_prov(field: str, value: str, doc_id: str, source_path: str,
               page: int, confidence: float) -> ProvenanceRef:
    return ProvenanceRef(
        doc_id=doc_id,
        source_path=source_path,
        page_number=page,
        field_name=field,
        extracted_value=str(value),
        confidence=confidence,
    )


class FieldExtractor:
    """
    Extracts structured fields from a list of DocumentPages.
    Produces an ExtractedFields record with full provenance.
    """

    def extract(self, pages, claim_id: str, package_code: str) -> ExtractedFields:
        ef = ExtractedFields(claim_id=claim_id, package_code=package_code)

        # Sort pages: discharge summaries first (richest source), then admission forms, then others
        ordered = sorted(pages, key=lambda p: (
            0 if "DISCHARGE" in p.doc_id.upper() or "DIS" in p.doc_id.upper() else
            1 if "CASE" in p.doc_id.upper() or "CLINICAL" in p.doc_id.upper() else
            2
        ))

        # Collect all dates appearing in discharge summary pages for fallback
        _discharge_page_dates: List[date] = []

        for page in ordered:
            text = page.text or ""
            doc_id = page.doc_id
            sp = page.source_path
            pn = page.page_number

            # ── Patient name ─────────────────────────────────────────────────
            if ef.patient_name is None:
                val = _first_match(_PATIENT_NAME_PATTERNS, text)
                if val and _is_valid_patient_name(val):
                    ef.patient_name = val
                    pref = _make_prov("patient_name", val, doc_id, sp, pn, 0.80)
                    ef.patient_name_provenance = pref
                    ef.all_provenance.append(pref)

            # ── Patient ID ───────────────────────────────────────────────────
            if ef.patient_id is None:
                val = _first_match(_PATIENT_ID_PATTERNS, text)
                if val:
                    ef.patient_id = val
                    pref = _make_prov("patient_id", val, doc_id, sp, pn, 0.85)
                    ef.patient_id_provenance = pref
                    ef.all_provenance.append(pref)

            # ── Age ──────────────────────────────────────────────────────────
            if ef.age is None:
                val = _first_match(_AGE_PATTERNS, text)
                if val and val.isdigit() and 0 < int(val) < 120:
                    ef.age = int(val)

            # ── Gender ───────────────────────────────────────────────────────
            if ef.gender is None:
                val = _first_match(_GENDER_PATTERNS, text)
                if val:
                    ef.gender = "Male" if val.lower() in ("m", "male") else "Female"

            # ── Admission date ────────────────────────────────────────────────
            if ef.admission_date is None:
                d = _extract_contextual_date(text, ADMISSION_KEYWORDS)
                if d:
                    ef.admission_date = d
                    pref = _make_prov("admission_date", str(d), doc_id, sp, pn, 0.82)
                    ef.admission_date_provenance = pref
                    ef.all_provenance.append(pref)

            # ── Discharge date ────────────────────────────────────────────────
            if ef.discharge_date is None:
                d = _extract_contextual_date(text, DISCHARGE_KEYWORDS)
                if d:
                    ef.discharge_date = d
                    pref = _make_prov("discharge_date", str(d), doc_id, sp, pn, 0.82)
                    ef.discharge_date_provenance = pref
                    ef.all_provenance.append(pref)

            # ── Collect dates from discharge/admission pages for fallback ──────
            is_discharge_page = ("DISCHARGE" in doc_id.upper() or "DIS" in doc_id.upper())
            if is_discharge_page or "ADMISSION" in doc_id.upper() or "ADM" in doc_id.upper():
                _discharge_page_dates.extend(_find_dates_in_text(text))

            # ── Procedure date ────────────────────────────────────────────────
            if ef.procedure_date is None:
                d = _extract_contextual_date(text, PROCEDURE_KEYWORDS)
                if d:
                    ef.procedure_date = d
                    pref = _make_prov("procedure_date", str(d), doc_id, sp, pn, 0.78)
                    ef.procedure_date_provenance = pref
                    ef.all_provenance.append(pref)

            # ── Diagnosis ─────────────────────────────────────────────────────
            for p in _DIAGNOSIS_PATTERNS:
                for m in re.finditer(p, text, re.IGNORECASE):
                    val = m.group(1).strip()
                    # Filter out garbled OCR — require >60% alpha characters
                    if not val or len(val) < 3:
                        continue
                    alpha_ratio = sum(c.isalpha() for c in val) / max(len(val), 1)
                    if alpha_ratio < 0.60:
                        continue
                    # Reject if it looks like a sentence fragment (too many short words)
                    words = val.split()
                    noise_words = sum(1 for w in words if w.lower() in _NAME_NOISE_WORDS)
                    if len(words) > 2 and noise_words / len(words) > 0.4:
                        continue
                    if val not in ef.diagnosis:
                        ef.diagnosis.append(val)
                        ef.all_provenance.append(
                            _make_prov("diagnosis", val, doc_id, sp, pn, 0.72)
                        )

            # Keyword scan for diagnosis signals (works even on partial/noisy OCR)
            text_lower = text.lower()
            for kw, canonical in _DIAGNOSIS_KEYWORDS_MAP.items():
                if kw in text_lower and canonical not in ef.diagnosis:
                    ef.diagnosis.append(canonical)
                    ef.all_provenance.append(
                        _make_prov("diagnosis", canonical, doc_id, sp, pn, 0.65)
                    )

            # ── Billed amount ─────────────────────────────────────────────────
            if ef.billed_amount is None:
                val = _first_match(_AMOUNT_PATTERNS, text)
                if val:
                    try:
                        ef.billed_amount = float(val.replace(",", ""))
                    except ValueError:
                        pass

            # ── Hospital name ────────────────────────────────────────────────
            if ef.hospital_name is None:
                val = _first_match(_HOSPITAL_PATTERNS, text)
                if val and _is_valid_hospital_name(val):
                    ef.hospital_name = val.split("\n")[0].strip()

            # ── Doctor name ──────────────────────────────────────────────────
            if ef.doctor_name is None:
                val = _first_match(_DOCTOR_PATTERNS, text)
                if val and len(val.split()) >= 2:
                    ef.doctor_name = val

        # ── Date fallback: use first/last dates from discharge/admission pages ─
        # When keyword-based extraction fails (no contextual label near date),
        # heuristically assign the earliest date as admission, latest as discharge.
        if _discharge_page_dates:
            valid_dates = sorted(
                d for d in _discharge_page_dates if 2000 <= d.year <= 2030
            )
            if valid_dates:
                if ef.admission_date is None and len(valid_dates) >= 1:
                    ef.admission_date = valid_dates[0]
                    pref = _make_prov("admission_date", str(valid_dates[0]),
                                      claim_id, "", 0, 0.55)
                    ef.admission_date_provenance = pref
                    ef.all_provenance.append(pref)
                if ef.discharge_date is None and len(valid_dates) >= 2:
                    ef.discharge_date = valid_dates[-1]
                    pref = _make_prov("discharge_date", str(valid_dates[-1]),
                                      claim_id, "", 0, 0.55)
                    ef.discharge_date_provenance = pref
                    ef.all_provenance.append(pref)

        return ef
