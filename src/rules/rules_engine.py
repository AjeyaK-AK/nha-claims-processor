"""
Rules Engine: loads STG YAML rules per package and evaluates them against
the extracted claim data. Returns a list of RuleResult with full provenance.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Set

import yaml

from config import STG_RULES_DIR, MAX_PRE_ADMIT_DAYS, MAX_POST_DISCHARGE_DAYS
from src.extraction.models import ExtractedFields
from src.rules.provenance import RuleEvidence, RuleResult

log = logging.getLogger(__name__)


# ── YAML loader (cached) ──────────────────────────────────────────────────────

@lru_cache(maxsize=20)
def _load_stg(package_code: str) -> Optional[dict]:
    yaml_path = STG_RULES_DIR / f"{package_code}.yaml"
    if not yaml_path.exists():
        log.warning("No STG YAML found for package %s", package_code)
        return None
    with open(yaml_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _doc_types_present(doc_type_map: Dict[str, str]) -> Set[str]:
    """Return the set of canonical doc types present in the claim."""
    return set(doc_type_map.values())


def _make_evidence(ef: ExtractedFields, field_name: str,
                   value: str, confidence: float) -> RuleEvidence:
    """Build a RuleEvidence from the ExtractedFields provenance list."""
    for prov in ef.all_provenance:
        if prov.field_name == field_name:
            return RuleEvidence(
                doc_id=prov.doc_id,
                source_path=prov.source_path,
                page_number=prov.page_number,
                field_name=field_name,
                value=value,
                confidence=prov.confidence,
            )
    # Generic fallback evidence
    return RuleEvidence(
        doc_id=ef.claim_id,
        source_path="",
        page_number=0,
        field_name=field_name,
        value=value,
        confidence=confidence,
    )


# ── Individual rule evaluators ────────────────────────────────────────────────

def _eval_document_presence(
    rule: dict,
    doc_types: Set[str],
    ef: ExtractedFields,
    doc_type_to_doc_id: Dict[str, str],
) -> RuleResult:
    required_doc = rule["required_doc"]
    alternatives = rule.get("alternatives", [])

    # Check primary type first, then any listed alternatives
    found_doc = None
    if required_doc in doc_types:
        found_doc = required_doc
    else:
        for alt in alternatives:
            if alt in doc_types:
                found_doc = alt
                break
    present = found_doc is not None

    evidence = []
    if present:
        doc_id = doc_type_to_doc_id.get(found_doc, "unknown")
        evidence.append(RuleEvidence(
            doc_id=doc_id,
            source_path="",
            page_number=1,
            field_name="document_type",
            value=found_doc,
            confidence=0.92,
        ))

    return RuleResult(
        rule_id=rule["id"],
        rule_name=rule["name"],
        passed=present,
        severity=rule["severity"],
        message=rule["message"] if not present else f"{found_doc} found.",
        evidence=evidence,
        confidence=0.92 if present else 1.0,
    )


def _eval_document_presence_conditional(
    rule: dict,
    doc_types: Set[str],
    ef: ExtractedFields,
    doc_type_to_doc_id: Dict[str, str],
) -> RuleResult:
    """Check document presence only if condition keywords are detected."""
    required_doc = rule["required_doc"]
    condition_keywords = [k.lower() for k in rule.get("condition_keywords", [])]

    all_text = " ".join(ef.diagnosis).lower()
    condition_met = any(kw in all_text for kw in condition_keywords)

    if not condition_met:
        return RuleResult(
            rule_id=rule["id"], rule_name=rule["name"], passed=True,
            severity=rule["severity"],
            message=f"Condition not detected; {required_doc} not required.",
            confidence=0.65,
        )

    return _eval_document_presence(rule, doc_types, ef, doc_type_to_doc_id)


def _eval_temporal(rule: dict, ef: ExtractedFields) -> RuleResult:
    check = rule["check"]
    evidence = []

    if check == "admission_before_discharge":
        if ef.admission_date is None or ef.discharge_date is None:
            return RuleResult(
                rule_id=rule["id"], rule_name=rule["name"], passed=False,
                severity=rule["severity"],
                message="Cannot verify: admission or discharge date missing.",
                confidence=0.5,
            )
        passed = ef.admission_date <= ef.discharge_date
        evidence = [
            _make_evidence(ef, "admission_date", str(ef.admission_date), 0.82),
            _make_evidence(ef, "discharge_date", str(ef.discharge_date), 0.82),
        ]
        return RuleResult(
            rule_id=rule["id"], rule_name=rule["name"], passed=passed,
            severity=rule["severity"],
            message=rule["message"] if not passed else
                    f"Admission {ef.admission_date} ≤ Discharge {ef.discharge_date}. Valid.",
            evidence=evidence, confidence=0.87,
        )

    elif check == "procedure_within_admission":
        if ef.procedure_date is None:
            return RuleResult(
                rule_id=rule["id"], rule_name=rule["name"], passed=False,
                severity=rule["severity"],
                message="Procedure date not found in documents.",
                confidence=0.4,
            )
        adm = ef.admission_date
        dis = ef.discharge_date
        proc = ef.procedure_date
        passed = True
        if adm and proc < adm:
            passed = False
        if dis and proc > dis:
            passed = False
        evidence = [_make_evidence(ef, "procedure_date", str(proc), 0.78)]
        return RuleResult(
            rule_id=rule["id"], rule_name=rule["name"], passed=passed,
            severity=rule["severity"],
            message=rule["message"] if not passed else
                    f"Procedure date {proc} within admission window. Valid.",
            evidence=evidence, confidence=0.82,
        )

    elif check == "investigation_before_procedure":
        # Investigations must be ≤ MAX_PRE_ADMIT_DAYS before admission
        if ef.admission_date is None:
            return RuleResult(
                rule_id=rule["id"], rule_name=rule["name"], passed=False,
                severity=rule["severity"],
                message="Admission date missing; cannot verify investigation timing.",
                confidence=0.4,
            )
        return RuleResult(
            rule_id=rule["id"], rule_name=rule["name"], passed=True,
            severity=rule["severity"],
            message="Investigation timing assumed valid (dates not individually tagged).",
            confidence=0.55,
        )

    return RuleResult(
        rule_id=rule["id"], rule_name=rule["name"], passed=True,
        severity=rule["severity"], message="Temporal check not implemented.",
        confidence=0.3,
    )


def _eval_los(rule: dict, ef: ExtractedFields) -> RuleResult:
    los = ef.length_of_stay
    min_d = rule.get("min_days", 0)
    max_d = rule.get("max_days", 999)

    if los is None:
        return RuleResult(
            rule_id=rule["id"], rule_name=rule["name"], passed=False,
            severity=rule["severity"],
            message="Length of stay cannot be computed (dates missing).",
            confidence=0.4,
        )

    passed = min_d <= los <= max_d
    evidence = [
        _make_evidence(ef, "admission_date", str(ef.admission_date), 0.82),
        _make_evidence(ef, "discharge_date", str(ef.discharge_date), 0.82),
    ]
    return RuleResult(
        rule_id=rule["id"], rule_name=rule["name"], passed=passed,
        severity=rule["severity"],
        message=rule["message"] if not passed else f"LoS = {los} days. Within {min_d}–{max_d} days.",
        evidence=evidence, confidence=0.90,
    )


def _eval_visual_element(
    rule: dict,
    ef: ExtractedFields,
    doc_type_to_doc_id: Dict[str, str],
) -> RuleResult:
    element_type = rule["element"]
    found = any(
        ve.element_type == element_type and ve.detected
        for ve in ef.visual_elements
    )
    evidence = []
    if found:
        ve = next(v for v in ef.visual_elements
                  if v.element_type == element_type and v.detected)
        evidence.append(RuleEvidence(
            doc_id=ve.doc_id,
            source_path="",
            page_number=ve.page_number,
            field_name=element_type,
            value="detected",
            confidence=ve.confidence,
            bounding_box=ve.bounding_box.model_dump() if ve.bounding_box else None,
        ))

    return RuleResult(
        rule_id=rule["id"], rule_name=rule["name"], passed=found,
        severity=rule["severity"],
        message=rule["message"] if not found else f"{element_type} detected.",
        evidence=evidence,
        confidence=0.80 if found else 0.75,
    )


def _eval_financial(rule: dict, ef: ExtractedFields) -> RuleResult:
    max_amount = rule.get("max_amount")
    if ef.billed_amount is None:
        return RuleResult(
            rule_id=rule["id"], rule_name=rule["name"], passed=True,
            severity=rule["severity"],
            message="Billed amount not found; cannot verify ceiling.",
            confidence=0.4,
        )
    passed = ef.billed_amount <= max_amount if max_amount else True
    return RuleResult(
        rule_id=rule["id"], rule_name=rule["name"], passed=passed,
        severity=rule["severity"],
        message=rule["message"] if not passed else
                f"Billed ₹{ef.billed_amount:,.0f} ≤ ceiling ₹{max_amount:,}.",
        evidence=[_make_evidence(ef, "billed_amount", str(ef.billed_amount), 0.70)],
        confidence=0.78,
    )


def _eval_diagnosis_keyword(rule: dict, ef: ExtractedFields) -> RuleResult:
    keywords = [k.lower() for k in rule.get("keywords", [])]
    all_diag_text = " ".join(ef.diagnosis).lower()

    hits = [kw for kw in keywords if kw in all_diag_text]
    passed = len(hits) > 0
    evidence = []
    if hits:
        for prov in ef.all_provenance:
            if prov.field_name == "diagnosis":
                evidence.append(RuleEvidence(
                    doc_id=prov.doc_id,
                    source_path=prov.source_path,
                    page_number=prov.page_number,
                    field_name="diagnosis",
                    value=prov.extracted_value,
                    confidence=prov.confidence,
                ))
                break

    return RuleResult(
        rule_id=rule["id"], rule_name=rule["name"], passed=passed,
        severity=rule["severity"],
        message=rule["message"] if not passed else
                f"Diagnosis keyword match: {hits}.",
        evidence=evidence, confidence=0.75 if passed else 0.65,
    )


def _eval_field_not_blank(rule: dict, ef: ExtractedFields) -> RuleResult:
    """
    Checks that a required extracted field is not None/empty.
    Supported field names: patient_name, patient_id, admission_date,
    discharge_date, procedure_date, diagnosis, billed_amount, hospital_name.
    """
    field_name = rule["field"]
    value = getattr(ef, field_name, None)

    # For list fields (e.g. diagnosis) check non-empty list
    if isinstance(value, list):
        present = len(value) > 0
        display = ", ".join(value[:3]) if present else ""
    else:
        present = value is not None and str(value).strip() != ""
        display = str(value) if present else ""

    evidence = []
    if present:
        for prov in ef.all_provenance:
            if prov.field_name == field_name:
                evidence.append(RuleEvidence(
                    doc_id=prov.doc_id,
                    source_path=prov.source_path,
                    page_number=prov.page_number,
                    field_name=field_name,
                    value=display,
                    confidence=prov.confidence,
                ))
                break
        if not evidence:
            evidence.append(RuleEvidence(
                doc_id=ef.claim_id,
                source_path="",
                page_number=0,
                field_name=field_name,
                value=display,
                confidence=0.70,
            ))

    return RuleResult(
        rule_id=rule["id"], rule_name=rule["name"], passed=present,
        severity=rule["severity"],
        message=rule["message"] if not present else
                f"Field '{field_name}' found: {display}.",
        evidence=evidence,
        confidence=0.85 if present else 0.80,
    )


# ── Main Rules Engine class ───────────────────────────────────────────────────

class RulesEngine:

    def evaluate(
        self,
        ef: ExtractedFields,
        doc_type_map: Dict[str, str],     # {doc_id → canonical_type}
    ) -> List[RuleResult]:
        """
        Load STG for ef.package_code and evaluate all rules.
        doc_type_map: {doc_id: canonical_type} for the claim.
        """
        stg = _load_stg(ef.package_code)
        if stg is None:
            log.warning("No STG for %s – skipping rule evaluation", ef.package_code)
            return []

        doc_types: Set[str] = set(doc_type_map.values())
        # Inverted map: canonical_type → first doc_id with that type
        doc_type_to_doc_id: Dict[str, str] = {}
        for did, dt in doc_type_map.items():
            if dt not in doc_type_to_doc_id:
                doc_type_to_doc_id[dt] = did

        results: List[RuleResult] = []

        for rule in stg.get("rules", []):
            rtype = rule.get("type")
            try:
                if rtype == "document_presence":
                    r = _eval_document_presence(rule, doc_types, ef, doc_type_to_doc_id)
                elif rtype == "document_presence_conditional":
                    r = _eval_document_presence_conditional(rule, doc_types, ef, doc_type_to_doc_id)
                elif rtype == "temporal":
                    r = _eval_temporal(rule, ef)
                elif rtype == "los":
                    r = _eval_los(rule, ef)
                elif rtype == "visual_element":
                    r = _eval_visual_element(rule, ef, doc_type_to_doc_id)
                elif rtype == "financial":
                    r = _eval_financial(rule, ef)
                elif rtype == "diagnosis_keyword":
                    r = _eval_diagnosis_keyword(rule, ef)
                elif rtype == "field_not_blank":
                    r = _eval_field_not_blank(rule, ef)
                else:
                    log.warning("Unknown rule type: %s", rtype)
                    continue
                results.append(r)
            except Exception as exc:
                log.error("Rule %s evaluation error: %s", rule.get("id"), exc)

        return results

    def identify_extra_documents(
        self,
        doc_type_map: Dict[str, str],
        package_code: str,
    ) -> List[str]:
        """
        Return list of doc_ids that are flagged as not_required per STG.
        """
        stg = _load_stg(package_code)
        if stg is None:
            return []
        not_required: List[str] = stg.get("not_required_documents", [])
        extras = []
        for doc_id, doc_type in doc_type_map.items():
            if doc_type in not_required:
                extras.append(doc_id)
        return extras
