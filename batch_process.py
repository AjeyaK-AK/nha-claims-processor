"""
Batch Processor: iterates over all Claims/<PackageCode>/<ClaimID>/ directories
and processes each claim, then writes a master summary CSV.
"""
from __future__ import annotations

import argparse
import csv
import io
import logging
import sys
from pathlib import Path

# Force UTF-8 stdout so logging/prints don't crash on Windows cp1252
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from config import CLAIMS_ROOTS, OUTPUT_DIR
from pipeline import ClaimProcessor
from generate_html_report import render as _render_html

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


def discover_claims(roots=CLAIMS_ROOTS):
    """
    Yields (claim_dir, package_code) for every claim found.
    Expected structure: <root>/<PackageCode>/<ClaimID>/
    """
    for root in roots:
        if not Path(root).exists():
            log.warning("Claims root not found: %s", root)
            continue
        for pkg_dir in sorted(Path(root).iterdir()):
            if not pkg_dir.is_dir():
                continue
            package_code = pkg_dir.name
            if package_code.startswith("."):
                continue
            for claim_dir in sorted(pkg_dir.iterdir()):
                if not claim_dir.is_dir():
                    continue
                if claim_dir.name.startswith("."):
                    continue
                yield claim_dir, package_code


def discover_claims_from_dir(dataset_dir: Path):
    """
    Discover claims from a custom dataset directory (hackathon dataset support).
    Supports <dataset>/<PackageCode>/<ClaimID>/ layout.
    """
    for pkg_dir in sorted(dataset_dir.iterdir()):
        if not pkg_dir.is_dir() or pkg_dir.name.startswith("."):
            continue
        package_code = pkg_dir.name
        for claim_dir in sorted(pkg_dir.iterdir()):
            if not claim_dir.is_dir() or claim_dir.name.startswith("."):
                continue
            yield claim_dir, package_code


SUMMARY_FIELDS = [
    "claim_id", "package_code", "verdict", "score", "confidence",
    "critical_failures", "major_failures", "minor_failures",
]
DOC_PRED_FIELDS = [
    "claim_id", "package_code", "doc_id", "source_file",
    "predicted_type", "confidence", "signal", "is_extra",
]


def _append_csv(path: Path, row: dict, fields: list):
    """Append one row to a CSV, writing header if the file is new."""
    write_header = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


HTML_DIR = Path(__file__).parent / "html_reports"


def _write_html(report_path: Path) -> None:
    """Generate / refresh the HTML report for a single JSON report file."""
    try:
        import json as _json2
        HTML_DIR.mkdir(exist_ok=True)
        data = _json2.loads(report_path.read_text(encoding="utf-8"))
        html = _render_html(data)
        out = HTML_DIR / report_path.with_suffix(".html").name
        out.write_text(html, encoding="utf-8")
        log.info("HTML written: %s", out.name)
    except Exception as exc:
        log.warning("HTML generation failed for %s: %s", report_path.name, exc)


def _rebuild_index() -> None:
    """Rebuild html_reports/index.html from all JSON reports in OUTPUT_DIR."""
    try:
        import json as _json3
        HTML_DIR.mkdir(exist_ok=True)
        index_rows = ""
        for f in sorted(OUTPUT_DIR.glob("*.json")):
            try:
                data = _json3.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            dec = data.get("decision", {})
            cl  = data.get("claim", {})
            verdict = dec.get("verdict", "?")
            color = {"PASS": "success", "CONDITIONAL": "warning", "FAIL": "danger"}.get(verdict, "secondary")
            icon  = {"PASS": "\u2705", "CONDITIONAL": "\u26a0\ufe0f", "FAIL": "\u274c"}.get(verdict, "\u2753")
            html_name = f.with_suffix(".html").name
            admit = cl.get("admission_date") or "\u2014"
            disch = cl.get("discharge_date") or "\u2014"
            index_rows += (
                f'<tr>'
                f'<td><a href="{html_name}">{cl.get("claim_id","")}</a></td>'
                f'<td>{cl.get("package_code","")}</td>'
                f'<td><span class="badge bg-{color}">{icon} {verdict}</span></td>'
                f'<td>{dec.get("overall_score",0):.1%}</td>'
                f'<td>{dec.get("confidence",0):.1%}</td>'
                f'<td>{admit}</td>'
                f'<td>{disch}</td>'
                f'<td>{len(dec.get("critical_failures",[]))}</td>'
                f'<td>{len(dec.get("major_failures",[]))}</td>'
                f'</tr>'
            )
        index_html = (
            '<!DOCTYPE html><html lang="en"><head>\n'
            '<meta charset="UTF-8"><title>NHA PMJAY \u2013 All Claims</title>\n'
            '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">\n'
            '</head><body>\n'
            '<nav class="navbar navbar-dark px-4 py-2" style="background:#00448a">'
            '<span class="navbar-brand fw-bold">\U0001f3e5 NHA PMJAY Claims Processor \u2013 All Claims</span></nav>\n'
            '<div class="container-fluid py-4">\n'
            '<table class="table table-hover table-bordered table-sm align-middle">\n'
            '<thead class="table-dark"><tr>'
            '<th>Claim ID</th><th>Package</th><th>Verdict</th><th>Score</th><th>Confidence</th>'
            '<th>Admit</th><th>Discharge</th><th>Critical Fails</th><th>Major Fails</th>'
            '</tr></thead>\n'
            f'<tbody>{index_rows}</tbody>\n'
            '</table></div>\n'
            '<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>\n'
            '</body></html>'
        )
        idx_file = HTML_DIR / "index.html"
        idx_file.write_text(index_html, encoding="utf-8")
        log.info("Index rebuilt: %s (%d claims)", idx_file, index_rows.count("<tr>"))
    except Exception as exc:
        log.warning("Index rebuild failed: %s", exc)


def run_batch(limit: int = 0, package_filter: str = None,
              dataset_dir: Path = None, skip_existing: bool = False):
    """
    Process all claims and write results incrementally so progress is
    preserved even if the process crashes mid-run.

    Args:
        limit: Max number of claims to process (0 = all).
        package_filter: Only process claims with this package code.
        dataset_dir: Custom dataset root (overrides config CLAIMS_ROOTS).
        skip_existing: If True, skip claims that already have a JSON report.
    """
    processor = ClaimProcessor(output_dir=OUTPUT_DIR)
    count = 0
    skipped = 0

    summary_path = OUTPUT_DIR / "batch_summary.csv"
    pred_path    = OUTPUT_DIR / "document_predictions.csv"

    import json as _json

    source = (
        discover_claims_from_dir(dataset_dir)
        if dataset_dir
        else discover_claims()
    )

    for claim_dir, package_code in source:
        if package_filter and package_code != package_filter:
            continue
        if limit and count >= limit:
            break

        claim_id = claim_dir.name
        report_path = OUTPUT_DIR / f"{claim_id}_{package_code}_report.json"

        # ── Optional skip ──────────────────────────────────────────────────
        if skip_existing and report_path.exists():
            log.info("SKIP (existing report): %s  [%s]", claim_id, package_code)
            skipped += 1

            # Still load existing report into CSVs so they stay complete
            try:
                with open(report_path, encoding="utf-8") as f:
                    rdata = _json.load(f)
                summary_row = {
                    "claim_id":          claim_id,
                    "package_code":      package_code,
                    "verdict":           rdata.get("verdict", "UNKNOWN"),
                    "score":             round(rdata.get("overall_score", 0), 4),
                    "confidence":        round(rdata.get("confidence", 0), 4),
                    "critical_failures": len(rdata.get("critical_failures", [])),
                    "major_failures":    len(rdata.get("major_failures", [])),
                    "minor_failures":    len(rdata.get("minor_failures", [])),
                }
                _append_csv(summary_path, summary_row, SUMMARY_FIELDS)
                for doc in rdata.get("document_classification", []):
                    _append_csv(pred_path, {
                        "claim_id":       claim_id,
                        "package_code":   package_code,
                        "doc_id":         doc.get("doc_id", ""),
                        "source_file":    Path(doc.get("source_path", "")).name,
                        "predicted_type": doc.get("predicted_type", ""),
                        "confidence":     round(doc.get("confidence", 0), 4),
                        "signal":         doc.get("signal", ""),
                        "is_extra":       doc.get("doc_id", "") in rdata.get("extra_documents_flagged", []),
                    }, DOC_PRED_FIELDS)
            except Exception as exc:
                log.warning("Could not read existing report for %s: %s", claim_id, exc)
            _write_html(report_path)
            continue

        # ── Full processing ────────────────────────────────────────────────
        try:
            decision = processor.process(claim_dir, package_code)
            summary_row = {
                "claim_id":          decision.claim_id,
                "package_code":      decision.package_code,
                "verdict":           decision.verdict,
                "score":             round(decision.overall_score, 4),
                "confidence":        round(decision.confidence, 4),
                "critical_failures": len(decision.critical_failures),
                "major_failures":    len(decision.major_failures),
                "minor_failures":    len(decision.minor_failures),
            }
            _append_csv(summary_path, summary_row, SUMMARY_FIELDS)

            # Per-document classification rows
            if report_path.exists():
                with open(report_path, encoding="utf-8") as f:
                    rdata = _json.load(f)
                for doc in rdata.get("document_classification", []):
                    _append_csv(pred_path, {
                        "claim_id":       decision.claim_id,
                        "package_code":   decision.package_code,
                        "doc_id":         doc.get("doc_id", ""),
                        "source_file":    Path(doc.get("source_path", "")).name,
                        "predicted_type": doc.get("predicted_type", ""),
                        "confidence":     round(doc.get("confidence", 0), 4),
                        "signal":         doc.get("signal", ""),
                        "is_extra":       doc.get("doc_id", "") in rdata.get("extra_documents_flagged", []),
                    }, DOC_PRED_FIELDS)
            _write_html(report_path)

        except Exception as exc:
            log.error("FAILED: %s  [%s]: %s", claim_id, package_code, exc, exc_info=True)
            _append_csv(summary_path, {
                "claim_id":          claim_id,
                "package_code":      package_code,
                "verdict":           "ERROR",
                "score":             0,
                "confidence":        0,
                "critical_failures": -1,
                "major_failures":    -1,
                "minor_failures":    -1,
            }, SUMMARY_FIELDS)
        count += 1

    _rebuild_index()
    log.info("Batch done: %d processed, %d skipped.", count, skipped)
    # Print final stats from the written CSV
    if summary_path.exists():
        rows = list(csv.DictReader(open(summary_path, encoding="utf-8")))
        total       = len(rows)
        passed      = sum(1 for r in rows if r["verdict"] == "PASS")
        conditional = sum(1 for r in rows if r["verdict"] == "CONDITIONAL")
        failed      = sum(1 for r in rows if r["verdict"] == "FAIL")
        errors      = sum(1 for r in rows if r["verdict"] == "ERROR")
        print(f"\n{'='*55}")
        print(f"  BATCH COMPLETE : {total} claims in summary")
        print(f"  [PASS]         : {passed}")
        print(f"  [CONDITIONAL]  : {conditional}")
        print(f"  [FAIL]         : {failed}")
        print(f"  [ERROR]        : {errors}")
        print(f"  [SKIPPED]      : {skipped}")
        print(f"  Summary CSV    : {summary_path}")
        print(f"  Doc-pred CSV   : {pred_path}")
        print(f"{'='*55}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch process medical claims")
    parser.add_argument("--limit", type=int, default=0,
                        help="Max number of claims to process (0 = all)")
    parser.add_argument("--package", type=str, default=None,
                        help="Process only claims with this package code")
    parser.add_argument("--dataset-dir", type=Path, default=None,
                        help="Custom dataset root (overrides config CLAIMS_ROOTS)")
    parser.add_argument("--skip-existing", action="store_true",
                        help="Skip claims that already have a JSON report (fast incremental run)")
    parser.add_argument("--force", dest="skip_existing", action="store_false",
                        help="Re-process all claims even if a report exists (default)")
    parser.set_defaults(skip_existing=False)
    args = parser.parse_args()
    run_batch(limit=args.limit, package_filter=args.package,
              dataset_dir=args.dataset_dir, skip_existing=args.skip_existing)
