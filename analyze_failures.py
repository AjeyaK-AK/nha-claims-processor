"""Quick failure analysis script."""
import json
from pathlib import Path

def show_claim(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    dec = d.get("decision", {})
    cl = d.get("claim", {})
    dc = d.get("document_classification", [])

    print("=== CLAIM:", cl.get("claim_id"))
    print("Package:", cl.get("package_code"))
    print("Verdict:", dec.get("verdict"), "  Score:", f"{dec.get('overall_score',0):.1%}")
    print("Admit:", cl.get("admission_date"), " Discharge:", cl.get("discharge_date"))
    print("Patient:", cl.get("patient_name"))
    print("Hospital:", cl.get("hospital_name"))
    print()
    print(f"=== DOC CLASSIFICATION ({len(dc)} docs):")
    for doc in dc:
        doc_id = doc.get("doc_id", "?")
        dtype  = doc.get("predicted_type", "?")
        conf   = doc.get("confidence", 0)
        sig    = (doc.get("signal") or "")[:55]
        src    = Path(doc.get("source_path", "")).name[:40]
        print(f"  {doc_id:<10} {dtype:<28} conf={conf:.2f}  {src}")
        if sig:
            print(f"             sig: {sig}")
    print()
    print("CRITICAL:")
    for c in dec.get("critical_failures", []):
        print(" ", c)
    print("MAJOR:")
    for m in dec.get("major_failures", []):
        print(" ", m)
    print()

# Show 3 representative failing claims from different packages
reports = sorted(Path("output_reports").glob("*.json"))
shown = set()
for f in reports:
    d = json.loads(f.read_text(encoding="utf-8"))
    pkg = d.get("claim", {}).get("package_code", "")
    if pkg not in shown and d.get("decision", {}).get("verdict") == "FAIL":
        show_claim(f)
        shown.add(pkg)
    if len(shown) >= 4:
        break
