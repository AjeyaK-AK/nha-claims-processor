"""
Quick utility: read all existing JSON reports and generate batch_summary.csv
and document_predictions.csv without re-running OCR.
"""
import csv
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

out = Path("output_reports")
reports = sorted(out.glob("*_report.json"))
print(f"Found {len(reports)} reports")

sum_rows, pred_rows = [], []
for rp in reports:
    with open(rp, encoding="utf-8", errors="replace") as f:
        d = json.load(f)
    # The report JSON nests verdicts under "decision" key
    dec = d.get("decision", d)   # fallback: treat top-level as decision
    cid = dec.get("claim_id", rp.stem.rsplit("_report", 1)[0])
    pkg = dec.get("package_code", "")
    sum_rows.append({
        "claim_id":          cid,
        "package_code":      pkg,
        "verdict":           dec.get("verdict", "UNKNOWN"),
        "score":             round(dec.get("overall_score", 0) or 0, 4),
        "confidence":        round(dec.get("confidence", 0) or 0, 4),
        "critical_failures": len(dec.get("critical_failures", [])),
        "major_failures":    len(dec.get("major_failures", [])),
        "minor_failures":    len(dec.get("minor_failures", [])),
    })
    extras = set(d.get("extra_documents_flagged", []))
    for doc in d.get("document_classification", []):
        pred_rows.append({
            "claim_id":       cid,
            "package_code":   pkg,
            "doc_id":         doc.get("doc_id", ""),
            "source_file":    Path(doc.get("source_path", "")).name,
            "predicted_type": doc.get("predicted_type", ""),
            "confidence":     round(doc.get("confidence", 0), 4),
            "signal":         doc.get("signal", ""),
            "is_extra":       doc.get("doc_id", "") in extras,
        })

# Write CSVs
summary_path = out / "batch_summary.csv"
with open(summary_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(sum_rows[0].keys()))
    writer.writeheader()
    writer.writerows(sum_rows)
print(f"Written: {summary_path}  ({len(sum_rows)} rows)")

pred_path = out / "document_predictions.csv"
with open(pred_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(pred_rows[0].keys()))
    writer.writeheader()
    writer.writerows(pred_rows)
print(f"Written: {pred_path}  ({len(pred_rows)} rows)")

# Print summary table
print("\nClaim decisions:")
print(f"  {'Claim ID':<55} {'Pkg':<8} {'Verdict':<12} Score")
print(f"  {'-'*55} {'-'*8} {'-'*12} -----")
for r in sum_rows:
    print(f"  {r['claim_id']:<55} {r['package_code']:<8} {r['verdict']:<12} {r['score']}")

# Stats
total = len(sum_rows)
verdicts = {v: sum(1 for r in sum_rows if r["verdict"] == v)
            for v in ["PASS", "CONDITIONAL", "FAIL", "ERROR", "UNKNOWN"]}
print(f"\nTotal: {total}  PASS={verdicts['PASS']}  CONDITIONAL={verdicts['CONDITIONAL']}  FAIL={verdicts['FAIL']}  ERROR={verdicts.get('ERROR',0)}")

