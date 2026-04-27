"""
Re-evaluate existing JSON reports with updated rules + classification.

Re-classifies each document using the current FILENAME_LABEL_MAP (picks up the
CN → case_sheet fix), then re-runs the rules and decision engines — without
re-OCR.  Updates the JSON reports in-place.

Usage:
    python reeval_reports.py
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import date
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.classification.doc_classifier import _label_to_type
from src.extraction.models import ExtractedFields, VisualElement
from src.rules.rules_engine import RulesEngine
from src.decisioning.decision_engine import DecisionEngine
from config import OUTPUT_DIR

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

rules_eng = RulesEngine()
decider   = DecisionEngine()


def _safe_date(s):
    if not s:
        return None
    try:
        return date.fromisoformat(str(s))
    except Exception:
        return None


def _reclassify(doc: dict) -> str:
    """Return updated predicted_type from current FILENAME_LABEL_MAP."""
    if doc.get("signal") != "filename":
        return doc["predicted_type"]    # content-based: unaffected
    raw = doc.get("raw_label", "")
    new_type = _label_to_type(raw)
    return new_type if new_type else doc["predicted_type"]


def _reconstruct_ef(report: dict, claim_id: str, package_code: str) -> ExtractedFields:
    cl  = report.get("claim", {})
    ves = [
        VisualElement(
            element_type=ve.get("type", ""),
            detected=ve.get("detected", False),
            confidence=ve.get("confidence", 0.5),
            doc_id=ve.get("doc_id", ""),
            page_number=ve.get("page", 1),
            decoded_value=ve.get("decoded_value"),
        )
        for ve in report.get("visual_elements", [])
    ]
    return ExtractedFields(
        claim_id=claim_id,
        package_code=package_code,
        patient_name=cl.get("patient_name"),
        patient_id=cl.get("patient_id"),
        age=cl.get("age"),
        gender=cl.get("gender"),
        hospital_name=cl.get("hospital_name"),
        doctor_name=cl.get("doctor_name"),
        admission_date=_safe_date(cl.get("admission_date")),
        discharge_date=_safe_date(cl.get("discharge_date")),
        procedure_date=_safe_date(cl.get("procedure_date")),
        diagnosis=cl.get("diagnosis") or [],
        billed_amount=cl.get("billed_amount"),
        visual_elements=ves,
    )


def reeval_report(report_path: Path) -> None:
    with open(report_path, encoding="utf-8", errors="replace") as f:
        report = json.load(f)

    dec_data     = report.get("decision", {})
    claim_id     = dec_data.get("claim_id") or report.get("claim", {}).get("claim_id", "")
    package_code = dec_data.get("package_code") or report.get("claim", {}).get("package_code", "")

    if not package_code:
        log.warning("No package_code in %s — skipping", report_path.name)
        return

    # Re-classify documents using updated FILENAME_LABEL_MAP
    changed = 0
    for doc in report.get("document_classification", []):
        new_type = _reclassify(doc)
        if new_type != doc["predicted_type"]:
            log.info("  %-40s %s → %s", doc.get("raw_label", "?"),
                     doc["predicted_type"], new_type)
            doc["predicted_type"] = new_type
            changed += 1

    # Rebuild doc_type_map
    doc_type_map = {
        doc["doc_id"]: doc["predicted_type"]
        for doc in report.get("document_classification", [])
    }

    # Reconstruct minimal ExtractedFields from stored claim data
    ef = _reconstruct_ef(report, claim_id, package_code)

    # Re-evaluate
    rule_results = rules_eng.evaluate(ef, doc_type_map)
    new_decision = decider.decide(claim_id, package_code, rule_results)

    old_v = dec_data.get("verdict", "?")
    old_s = dec_data.get("overall_score", 0)
    print(f"  {claim_id} [{package_code}]: "
          f"{old_v} {old_s:.4f} → {new_decision.verdict} {new_decision.overall_score:.4f}"
          f"  ({changed} doc type changes)")

    # Patch report in-place
    report["decision"] = new_decision.to_dict()

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)


def main():
    reports = sorted(OUTPUT_DIR.glob("*_report.json"))
    if not reports:
        print(f"No reports found in {OUTPUT_DIR}")
        return

    print(f"Re-evaluating {len(reports)} reports with updated rules...\n")
    for rp in reports:
        reeval_report(rp)

    print("\nDone. Run `python make_csvs.py` to regenerate CSVs.")


if __name__ == "__main__":
    main()
