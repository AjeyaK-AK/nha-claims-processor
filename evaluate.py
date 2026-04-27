"""
Evaluation Script: computes F1 scores for:
  1. Document Classification (vs. ground truth = filename labels OR external GT CSV)
  2. Rule / Decision evaluation (vs. ground truth = claim-level verdicts from GT CSV)
  3. Provenance quality (coverage of rule evidence fields)

Usage:
  python evaluate.py --mode classification
  python evaluate.py --mode decision --gt ground_truth.csv
  python evaluate.py --mode all --gt ground_truth.csv

  # Hackathon GT CSV format:
  #   For classification: claim_id, doc_id, ground_truth_type
  #   For decisions:      claim_id, verdict (PASS / CONDITIONAL / FAIL)
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Tuple

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")


def _canonical_from_filename(doc_id: str) -> str:
    """Derive ground-truth type from the filename label (same logic as classifier)."""
    from src.classification.doc_types import FILENAME_LABEL_MAP, OTHER
    parts = doc_id.split("__")
    if len(parts) >= 3:
        label = parts[-1].upper().strip()
        if label in FILENAME_LABEL_MAP:
            return FILENAME_LABEL_MAP[label]
    return OTHER


def eval_classification(output_dir: Path, gt_csv: Path = None) -> dict:
    """
    Compare predicted doc type vs. ground truth.
    If gt_csv provided, uses external GT (claim_id, doc_id, ground_truth_type).
    Otherwise uses filename-label derived GT.
    Returns metrics dict.
    """
    try:
        from sklearn.metrics import classification_report, f1_score
    except ImportError:
        print("scikit-learn not installed. Run: pip install scikit-learn")
        return {}

    # Load external GT if provided
    ext_gt: Dict[str, str] = {}      # doc_id → truth_type
    if gt_csv and gt_csv.exists():
        with open(gt_csv, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if "doc_id" in row and "ground_truth_type" in row:
                    ext_gt[row["doc_id"]] = row["ground_truth_type"].strip().lower()

    y_true, y_pred = [], []
    report_files = list(output_dir.glob("*_report.json"))
    if not report_files:
        print("No report JSON files found in", output_dir)
        return {}

    for rp in report_files:
        with open(rp, encoding="utf-8") as f:
            data = json.load(f)
        for doc in data.get("document_classification", []):
            doc_id = doc["doc_id"]
            pred   = doc["predicted_type"]

            if ext_gt:
                gt = ext_gt.get(doc_id, ext_gt.get(doc_id.split("__")[-1], "other"))
            else:
                gt = _canonical_from_filename(doc_id)

            y_true.append(gt)
            y_pred.append(pred)

    if not y_true:
        print("No classification data found.")
        return {}

    print("\n── Document Classification Metrics ──────────────────────────")
    print(classification_report(y_true, y_pred, zero_division=0))

    macro_f1 = f1_score(y_true, y_pred, average="macro",    zero_division=0)
    micro_f1 = f1_score(y_true, y_pred, average="micro",    zero_division=0)
    wt_f1    = f1_score(y_true, y_pred, average="weighted", zero_division=0)
    print(f"  Macro F1   : {macro_f1:.4f}")
    print(f"  Micro F1   : {micro_f1:.4f}")
    print(f"  Weighted F1: {wt_f1:.4f}")

    _rank_label("Document Classification", macro_f1,
                {"Full (Rank-1)": 0.95, "Partial (Rank-2)": 0.90, "Partial (Rank-3)": 0.85})

    return {"macro_f1": macro_f1, "micro_f1": micro_f1, "weighted_f1": wt_f1}


def eval_decision(output_dir: Path, gt_csv: Path) -> dict:
    """
    Compare predicted verdicts vs. ground truth from a CSV file.
    GT CSV: claim_id, verdict (PASS / CONDITIONAL / FAIL)
    """
    try:
        from sklearn.metrics import classification_report, f1_score
    except ImportError:
        print("scikit-learn not installed.")
        return {}

    gt_map: Dict[str, str] = {}
    with open(gt_csv, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if "claim_id" in row and "verdict" in row:
                gt_map[row["claim_id"]] = row["verdict"].upper()

    y_true, y_pred = [], []
    for rp in output_dir.glob("*_report.json"):
        with open(rp, encoding="utf-8") as f:
            data = json.load(f)
        claim_id     = data["claim"]["claim_id"]
        pred_verdict = data["decision"]["verdict"]
        if claim_id in gt_map:
            y_true.append(gt_map[claim_id])
            y_pred.append(pred_verdict)

    if not y_true:
        print("No matching claims found for evaluation.")
        return {}

    print("\n── Decision / Verdict Metrics ───────────────────────────────")
    print(classification_report(y_true, y_pred, zero_division=0))
    macro_f1 = f1_score(y_true, y_pred, average="macro",    zero_division=0)
    micro_f1 = f1_score(y_true, y_pred, average="micro",    zero_division=0)
    print(f"  Macro F1: {macro_f1:.4f}")
    print(f"  Micro F1: {micro_f1:.4f}")

    _rank_label("Rule / Decision", macro_f1,
                {"Full (Rank-1)": 0.96, "Partial (Rank-2)": 0.90, "Partial (Rank-3)": 0.85})

    return {"macro_f1": macro_f1, "micro_f1": micro_f1}


def eval_provenance(output_dir: Path) -> dict:
    """
    Check provenance quality across all reports:
      - % of rule evidence items with source doc + page number
      - % of extracted fields with provenance
    """
    total_evidence = 0
    evidence_with_source = 0
    evidence_with_page = 0
    total_fields = 0
    fields_with_prov = 0

    for rp in output_dir.glob("*_report.json"):
        with open(rp, encoding="utf-8") as f:
            data = json.load(f)

        # Rule evidence coverage
        for rule in data.get("decision", {}).get("rule_details", []):
            for ev in rule.get("evidence", []):
                total_evidence += 1
                if ev.get("doc_id") and ev["doc_id"] not in ("", "unknown"):
                    evidence_with_source += 1
                if ev.get("page") and int(ev["page"]) > 0:
                    evidence_with_page += 1

        # Provenance log coverage
        prov = data.get("provenance_log", [])
        total_fields += len(prov)
        fields_with_prov += sum(
            1 for p in prov
            if p.get("doc_id") and p.get("page") and p.get("confidence", 0) > 0
        )

    def _pct(a, b):
        return (a / b * 100) if b > 0 else 0

    print("\n── Provenance Quality ────────────────────────────────────────")
    print(f"  Rule evidence items    : {total_evidence}")
    print(f"  With source doc        : {evidence_with_source} ({_pct(evidence_with_source, total_evidence):.1f}%)")
    print(f"  With page number       : {evidence_with_page} ({_pct(evidence_with_page, total_evidence):.1f}%)")
    print(f"  Extracted fields       : {total_fields}")
    print(f"  With full provenance   : {fields_with_prov} ({_pct(fields_with_prov, total_fields):.1f}%)")

    return {
        "evidence_source_coverage": _pct(evidence_with_source, total_evidence),
        "evidence_page_coverage":   _pct(evidence_with_page,   total_evidence),
        "field_prov_coverage":      _pct(fields_with_prov,     total_fields),
    }


def _rank_label(category: str, f1: float, thresholds: dict) -> None:
    for label, threshold in thresholds.items():
        if f1 >= threshold:
            print(f"  [{category}] → {label} eligible (F1 ≥ {threshold})")
            return
    print(f"  [{category}] → Below qualification threshold (min F1 ≥ {min(thresholds.values())})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="NHA Hackathon 2026 – Evaluation Metrics"
    )
    parser.add_argument("--mode", choices=["classification", "decision", "provenance", "all"],
                        default="all")
    parser.add_argument("--output-dir", type=Path, default=Path("output_reports"))
    parser.add_argument("--gt", type=Path, default=None,
                        help="Ground truth CSV (required for decision mode; optional for classification)")
    args = parser.parse_args()

    results = {}
    if args.mode in ("classification", "all"):
        r = eval_classification(args.output_dir, gt_csv=args.gt)
        if r:
            results["classification"] = r

    if args.mode in ("decision", "all"):
        if args.gt is None:
            print("Note: --gt not provided, skipping decision evaluation")
        else:
            r = eval_decision(args.output_dir, args.gt)
            if r:
                results["decision"] = r

    if args.mode in ("provenance", "all"):
        r = eval_provenance(args.output_dir)
        if r:
            results["provenance"] = r

    if results and args.mode == "all":
        print("\n── Overall Summary ───────────────────────────────────────────")
        cls_f1  = results.get("classification", {}).get("macro_f1", 0)
        dec_f1  = results.get("decision",       {}).get("macro_f1", 0)
        prov_pct = results.get("provenance",    {}).get("evidence_source_coverage", 0)
        if cls_f1:
            print(f"  Classification F1 : {cls_f1:.4f}  (weight 40%  target ≥ 0.95)")
        if dec_f1:
            print(f"  Decision F1       : {dec_f1:.4f}  (weight 40%  target ≥ 0.96)")
        print(f"  Provenance cov.   : {prov_pct:.1f}%  (design 20%  target ≥ 0.93)")
