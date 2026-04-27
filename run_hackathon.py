"""
NHA Hackathon 2026 – Problem Statement 01
Medical Claims Processing System – Competition Runner

Usage
-----
    python run_hackathon.py --dataset-dir <path> [--output-dir <path>] [--package <code>]

What it does
------------
1.  Discovers all claims under <dataset-dir>  (same tree as extract_1/extract_2)
2.  Runs the full pipeline on each claim
3.  Writes per-claim JSON reports to <output-dir>/
4.  Writes competition evaluation artefacts:
      document_predictions.csv  – one row per document page  (classification F1)
      claim_decisions.csv       – one row per claim          (rule/decision F1)
      batch_summary.csv         – aggregate statistics
      provenance_log.csv        – flat provenance for every extracted field

Expected dataset tree
---------------------
    <dataset-dir>/
        <PackageCode>/
            <ClaimID>/
                000_<ClaimID>__DOC_LABEL.pdf
                001_<ClaimID>__DISCHARGE.jpg
                ...
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

# Force UTF-8 output for Windows cp1252 environments
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


# ── discovery ─────────────────────────────────────────────────────────────────

def discover_claims(dataset_dir: Path) -> List[Tuple[Path, str]]:
    """
    Yield (claim_dir, package_code) for every claim in the dataset tree.
    Supports two layouts:
      Layout A (NHA standard): <dataset>/<PackageCode>/<ClaimID>/
      Layout B (flat):         <dataset>/<ClaimID>/          (package_code inferred from files)
    """
    pairs: List[Tuple[Path, str]] = []
    if not dataset_dir.exists():
        log.error("Dataset directory not found: %s", dataset_dir)
        return pairs

    # Try Layout A first: expect child directories to be package codes
    found_pkg = False
    for pkg_dir in sorted(dataset_dir.iterdir()):
        if not pkg_dir.is_dir() or pkg_dir.name.startswith("."):
            continue
        # Heuristic: a package code is all-caps + digits, e.g. MG006A, MC011A
        name = pkg_dir.name
        if name.upper() == name and any(c.isdigit() for c in name):
            found_pkg = True
            for claim_dir in sorted(pkg_dir.iterdir()):
                if claim_dir.is_dir() and not claim_dir.name.startswith("."):
                    pairs.append((claim_dir, pkg_dir.name))

    if found_pkg:
        return pairs

    # Layout B: flat – try to infer package_code from directory name or files
    for claim_dir in sorted(dataset_dir.iterdir()):
        if not claim_dir.is_dir() or claim_dir.name.startswith("."):
            continue
        pkg = _infer_package_code(claim_dir)
        pairs.append((claim_dir, pkg))

    return pairs


def _infer_package_code(claim_dir: Path) -> str:
    """
    Try to infer package code from claim directory name or filenames.
    Falls back to 'UNKNOWN'.
    """
    import re
    # e.g. CMJAY_TR_CMJAY_2025_R3_1021740400_SB039A  → SB039A
    m = re.search(r"[A-Z]{2}\d{3}[A-Z]", claim_dir.name)
    if m:
        return m.group(0)
    # Try filenames
    for f in claim_dir.iterdir():
        m = re.search(r"[A-Z]{2}\d{3}[A-Z]", f.name)
        if m:
            return m.group(0)
    return "UNKNOWN"


# ── main runner ───────────────────────────────────────────────────────────────

def run(dataset_dir: Path, output_dir: Path, package_filter: str = None,
        limit: int = 0) -> None:

    output_dir.mkdir(parents=True, exist_ok=True)
    log.info("Dataset : %s", dataset_dir)
    log.info("Output  : %s", output_dir)

    from pipeline import ClaimProcessor
    processor = ClaimProcessor(output_dir=output_dir)

    claims = discover_claims(dataset_dir)
    if package_filter:
        claims = [(d, p) for d, p in claims if p == package_filter]
    if limit:
        claims = claims[:limit]

    log.info("Claims found: %d", len(claims))

    summary_rows: list = []
    doc_pred_rows: list = []
    prov_rows: list = []

    for i, (claim_dir, package_code) in enumerate(claims, 1):
        log.info("[%d/%d] %s  [%s]", i, len(claims), claim_dir.name, package_code)
        try:
            decision = processor.process(claim_dir, package_code)

            # ── Read the report JSON for detailed rows ─────────────────────
            rpath = output_dir / f"{decision.claim_id}_{decision.package_code}_report.json"
            if rpath.exists():
                with open(rpath, encoding="utf-8") as f:
                    rdata = json.load(f)

                # Document classification rows
                for doc in rdata.get("document_classification", []):
                    doc_pred_rows.append({
                        "claim_id":       decision.claim_id,
                        "package_code":   decision.package_code,
                        "doc_id":         doc.get("doc_id", ""),
                        "source_file":    Path(doc.get("source_path", "")).name,
                        "page_number":    "",           # filled per-page from provenance
                        "predicted_type": doc.get("predicted_type", ""),
                        "confidence":     round(doc.get("confidence", 0), 4),
                        "signal":         doc.get("signal", ""),
                        "raw_label":      doc.get("raw_label", ""),
                        "is_extra_doc":   doc.get("doc_id", "") in rdata.get("extra_documents_flagged", []),
                    })

                # Provenance rows
                for p in rdata.get("provenance_log", []):
                    prov_rows.append({
                        "claim_id":    decision.claim_id,
                        "package_code": decision.package_code,
                        "field":       p.get("field", ""),
                        "value":       p.get("value", ""),
                        "doc_id":      p.get("doc_id", ""),
                        "source_file": Path(p.get("source_path", "") or "").name,
                        "page":        p.get("page", ""),
                        "confidence":  round(p.get("confidence", 0), 4),
                    })

            summary_rows.append({
                "claim_id":            decision.claim_id,
                "package_code":        decision.package_code,
                "verdict":             decision.verdict,
                "overall_score":       round(decision.overall_score, 4),
                "confidence":          round(decision.confidence, 4),
                "critical_failures":   len(decision.critical_failures),
                "major_failures":      len(decision.major_failures),
                "minor_failures":      len(decision.minor_failures),
                "critical_reasons":    " | ".join(decision.critical_failures),
                "major_reasons":       " | ".join(decision.major_failures),
                "minor_reasons":       " | ".join(decision.minor_failures),
            })

        except Exception as exc:
            log.error("Failed: %s → %s", claim_dir.name, exc, exc_info=True)
            summary_rows.append({
                "claim_id": claim_dir.name, "package_code": package_code,
                "verdict": "ERROR", "overall_score": 0, "confidence": 0,
                "critical_failures": -1, "major_failures": -1, "minor_failures": -1,
                "critical_reasons": str(exc), "major_reasons": "", "minor_reasons": "",
            })

    # ── Write evaluation CSVs ─────────────────────────────────────────────────
    _write_csv(output_dir / "claim_decisions.csv", summary_rows)
    _write_csv(output_dir / "document_predictions.csv", doc_pred_rows)
    _write_csv(output_dir / "provenance_log.csv", prov_rows)

    # ── Write batch_summary.csv (legacy compat) ───────────────────────────────
    batch_cols = ["claim_id", "package_code", "verdict", "overall_score",
                  "confidence", "critical_failures", "major_failures", "minor_failures"]
    _write_csv(output_dir / "batch_summary.csv",
               [{k: r[k] for k in batch_cols} for r in summary_rows])

    # ── Print stats ───────────────────────────────────────────────────────────
    total       = len(summary_rows)
    passed      = sum(1 for r in summary_rows if r["verdict"] == "PASS")
    conditional = sum(1 for r in summary_rows if r["verdict"] == "CONDITIONAL")
    failed      = sum(1 for r in summary_rows if r["verdict"] == "FAIL")
    errors      = sum(1 for r in summary_rows if r["verdict"] == "ERROR")

    sep = "=" * 60
    print(f"\n{sep}")
    print(f"  NHA PMJAY HACKATHON – Batch Run Complete")
    print(f"  Timestamp : {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Dataset   : {dataset_dir}")
    print(f"  Output    : {output_dir}")
    print(sep)
    print(f"  Total processed  : {total}")
    print(f"  ✅ PASS           : {passed}  ({passed/total*100:.1f}%)" if total else "")
    print(f"  ⚠️  CONDITIONAL    : {conditional}  ({conditional/total*100:.1f}%)" if total else "")
    print(f"  ❌ FAIL           : {failed}  ({failed/total*100:.1f}%)" if total else "")
    if errors:
        print(f"  ⛔ ERROR         : {errors}")
    print(sep)
    print("  Output files:")
    print(f"    claim_decisions.csv       ({total} rows)")
    print(f"    document_predictions.csv  ({len(doc_pred_rows)} rows)")
    print(f"    provenance_log.csv        ({len(prov_rows)} rows)")
    print(f"    batch_summary.csv")
    print(sep)


def _write_csv(path: Path, rows: list) -> None:
    if not rows:
        log.warning("No rows to write: %s", path.name)
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    log.info("Written: %s  (%d rows)", path, len(rows))


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="NHA Hackathon 2026 – Problem Statement 01 – Batch Runner"
    )
    parser.add_argument(
        "--dataset-dir", "-d", required=True, type=Path,
        help="Root of the hackathon dataset (contains PackageCode/ClaimID/ folders)"
    )
    parser.add_argument(
        "--output-dir", "-o", type=Path, default=Path("output_reports"),
        help="Directory to write JSON reports and evaluation CSVs (default: output_reports/)"
    )
    parser.add_argument(
        "--package", "-p", type=str, default=None,
        help="Only process claims with this package code (e.g. MG006A)"
    )
    parser.add_argument(
        "--limit", "-n", type=int, default=0,
        help="Max number of claims to process (0 = all)"
    )

    args = parser.parse_args()
    run(
        dataset_dir=args.dataset_dir,
        output_dir=args.output_dir,
        package_filter=args.package,
        limit=args.limit,
    )
