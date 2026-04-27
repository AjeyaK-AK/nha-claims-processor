"""
Generate a self-contained HTML report from a claim JSON output.
Works anywhere – no server, no Python, just open in a browser.
Usage:
    python generate_html_report.py                          # all reports
    python generate_html_report.py output_reports/X.json   # one report
"""
import json, sys, os
from pathlib import Path

BASE = Path(__file__).parent

VERDICT_COLOR = {"PASS": "#198754", "CONDITIONAL": "#e67e22", "FAIL": "#dc3545"}
VERDICT_BG    = {"PASS": "#d1e7dd", "CONDITIONAL": "#fef3cd", "FAIL": "#f8d7da"}

RESULT_BADGE = {
    "PASS":          '<span class="badge bg-success">✅ PASS</span>',
    "FAIL-CRITICAL": '<span class="badge bg-danger">🔴 Critical</span>',
    "FAIL-MAJOR":    '<span class="badge bg-warning text-dark">🟠 Major</span>',
    "FAIL-MINOR":    '<span class="badge bg-secondary">🟡 Minor</span>',
}

def _badge(result):
    return RESULT_BADGE.get(result, f'<span class="badge bg-secondary">{result}</span>')

def _pct(v):
    try: return f"{float(v):.1%}"
    except: return "—"

def _safe(v, maxlen=60):
    s = str(v or "—")[:maxlen]
    return s.replace("<","&lt;").replace(">","&gt;")

def render(data: dict) -> str:
    dec   = data.get("decision", {})
    dc    = data.get("document_classification", [])
    ve    = data.get("visual_elements", [])
    tl    = data.get("episode_timeline", {})
    cl    = data.get("claim", {})
    extra = set(data.get("extra_documents_flagged", []) or [])

    verdict  = dec.get("verdict", "UNKNOWN")
    score    = dec.get("overall_score", 0)
    conf     = dec.get("confidence", 0)
    claim_id = cl.get("claim_id", "")
    pkg      = cl.get("package_code", "")
    v_color  = VERDICT_COLOR.get(verdict, "#6c757d")
    v_bg     = VERDICT_BG.get(verdict, "#f8f9fa")

    dx_list  = cl.get("diagnosis") or []
    dx_str   = ", ".join(dx_list)[:80] if dx_list else "—"

    # ── Document Classification table ─────────────────────────────────────────
    doc_rows = ""
    for doc in dc:
        doc_id  = doc.get("doc_id", "")
        dtype   = (doc.get("predicted_type") or doc.get("doc_type","other")).replace("_"," ").title()
        cval    = _pct(doc.get("confidence", 0))
        sig     = doc.get("signal","")
        src     = doc.get("source_path","")
        fname   = Path(src).name if src else doc_id
        is_ex   = doc_id in extra
        flag    = '<span class="text-warning">⚠ Not required</span>' if is_ex else ""

        doc_flags = []
        for rd in dec.get("rule_details", []):
            for ev in rd.get("evidence", []):
                if ev.get("doc_id") == doc_id and rd.get("result","").startswith("FAIL"):
                    doc_flags.append(rd.get("message",""))
        issues = "; ".join(set(doc_flags)) if doc_flags else (flag or "—")

        doc_rows += f"""
        <tr>
          <td class="text-muted small">{_safe(claim_id, 25)}</td>
          <td>{_safe(fname, 55)}</td>
          <td><span class="badge bg-info text-dark">{_safe(dtype)}</span></td>
          <td>{cval}</td>
          <td><span class="badge bg-secondary">{sig}</span></td>
          <td class="small">{issues}</td>
        </tr>"""

    # ── Rule Evaluation ────────────────────────────────────────────────────────
    rule_rows = ""
    for rd in dec.get("rule_details", []):
        result = rd.get("result", "")
        rconf  = _pct(rd.get("confidence", 0))
        evid   = rd.get("evidence", [])
        ev_html = ""
        for ev in evid:
            bb = ev.get("bounding_box") or {}
            bb_str = (f"BBox ({bb.get('x0',0):.0f},{bb.get('y0',0):.0f})→"
                      f"({bb.get('x1',0):.0f},{bb.get('y1',0):.0f})") if bb else ""
            ev_html += (f'<li class="small text-muted">Doc: <code>{_safe(ev.get("doc_id",""),45)}</code> '
                        f'· Page {ev.get("page","?")} · Field <code>{ev.get("field",ev.get("field_name",""))}</code> '
                        f'· Value <code>{_safe(ev.get("value",""),40)}</code> · Conf {_pct(ev.get("confidence",0))} {bb_str}</li>')

        rule_rows += f"""
        <tr>
          <td>{_badge(result)}</td>
          <td><strong>{_safe(rd.get("rule_id",""))}</strong></td>
          <td>{_safe(rd.get("rule_name",""))}</td>
          <td>{rconf}</td>
          <td class="small">{_safe(rd.get("message",""))}</td>
        </tr>"""
        if ev_html:
            rule_rows += f'<tr class="table-light"><td colspan="5"><ul class="mb-0 ps-3">{ev_html}</ul></td></tr>'

    # ── Timeline ───────────────────────────────────────────────────────────────
    timeline_rows = ""
    for i, ev in enumerate(tl.get("events", []), 1):
        valid = str(ev.get("temporal_validity", ev.get("valid","?")))
        vclass = "text-success" if valid.lower() in ("valid","true") else \
                 "text-danger"  if valid.lower() in ("invalid","false") else "text-warning"
        timeline_rows += f"""
        <tr>
          <td>{ev.get("sequence", i)}</td>
          <td>{_safe(ev.get("event_type", ev.get("type","")).replace("_"," ").title())}</td>
          <td>{_safe(ev.get("event_date", ev.get("date","N/A")))}</td>
          <td class="small">{_safe((ev.get("source_doc") or ev.get("doc_id","—")), 50)}</td>
          <td class="{vclass}">{valid}</td>
        </tr>"""

    plausible = tl.get("is_plausible")
    tl_alert = ""
    if plausible is True:
        tl_alert = '<div class="alert alert-success py-1 mb-2">✓ Timeline is temporally plausible</div>'
    elif plausible is False:
        flags = "".join(f"<li>{f}</li>" for f in tl.get("plausibility_flags",[]))
        tl_alert = f'<div class="alert alert-danger py-1 mb-2">⚠ Timeline issues:<ul class="mb-0">{flags}</ul></div>'

    # ── Provenance Log ─────────────────────────────────────────────────────────
    prov = data.get("provenance_log", [])
    prov_rows = ""
    for p in prov:
        bb = p.get("bounding_box") or {}
        bb_str = (f"({bb.get('x0',0):.0f},{bb.get('y0',0):.0f})→"
                  f"({bb.get('x1',0):.0f},{bb.get('y1',0):.0f})") if bb else "—"
        prov_rows += f"""
        <tr>
          <td><code>{_safe(p.get("field",""))}</code></td>
          <td><code>{_safe(p.get("value",""),60)}</code></td>
          <td class="small"><code>{_safe(p.get("doc_id",""),45)}</code></td>
          <td>{p.get("page","")}</td>
          <td>{_pct(p.get("confidence",0))}</td>
          <td class="small font-monospace">{bb_str}</td>
        </tr>"""

    # If provenance_log is empty, build it from rule evidence
    if not prov_rows:
        for rd in dec.get("rule_details", []):
            for ev in rd.get("evidence", []):
                bb = ev.get("bounding_box") or {}
                bb_str = (f"({bb.get('x0',0):.0f},{bb.get('y0',0):.0f})→"
                          f"({bb.get('x1',0):.0f},{bb.get('y1',0):.0f})") if bb else "—"
                prov_rows += f"""
        <tr>
          <td><code>{_safe(ev.get("field", ev.get("field_name","")))}</code></td>
          <td><code>{_safe(ev.get("value",""),60)}</code></td>
          <td class="small"><code>{_safe(ev.get("doc_id",""),45)}</code></td>
          <td>{ev.get("page","")}</td>
          <td>{_pct(ev.get("confidence",0))}</td>
          <td class="small font-monospace">{bb_str}</td>
        </tr>"""

    # ── Visual Elements ────────────────────────────────────────────────────────
    ve_rows = ""
    for v in ve:
        det = "✅ Yes" if v.get("detected") else "❌ No"
        ve_rows += f"""
        <tr>
          <td>{_safe(v.get("type", v.get("element_type","")).replace("_"," ").title())}</td>
          <td>{det}</td>
          <td>{_pct(v.get("confidence",0))}</td>
          <td class="small"><code>{_safe(v.get("doc_id",""),45)}</code></td>
          <td>{v.get("page","")}</td>
          <td>{_safe(v.get("decoded_value",""))}</td>
        </tr>"""

    passed  = len(dec.get("passed_rules", []))
    n_crit  = len(dec.get("critical_failures", []))
    n_major = len(dec.get("major_failures", []))
    n_minor = len(dec.get("minor_failures", []))

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NHA PMJAY Claim Report – {_safe(claim_id)}</title>
<link rel="stylesheet"
  href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
<style>
  body {{ font-family: 'Segoe UI', sans-serif; background:#f8f9fa; }}
  .verdict-banner {{ border-radius:12px; padding:20px 30px; margin-bottom:24px; }}
  .metric-card {{ background:#fff; border-radius:8px; padding:14px 18px;
                  border:1px solid #dee2e6; text-align:center; }}
  .metric-card .value {{ font-size:1.4rem; font-weight:700; }}
  .metric-card .label {{ font-size:0.8rem; color:#6c757d; }}
  nav.navbar {{ background:#00448a !important; }}
  .table th {{ background:#f1f3f5; }}
  pre {{ background:#f8f9fa; border-radius:6px; padding:8px; font-size:0.8rem; }}
</style>
</head>
<body>

<nav class="navbar navbar-dark px-4 py-2">
  <span class="navbar-brand fw-bold">🏥 NHA PMJAY Automated Claims Processor</span>
  <span class="text-white-50 small">Problem Statement 01 · 2026</span>
</nav>

<div class="container-fluid py-4">

  <!-- Verdict Banner -->
  <div class="verdict-banner" style="background:{v_bg}; border:2px solid {v_color}">
    <div class="d-flex align-items-center gap-4">
      <h2 style="color:{v_color};margin:0;font-size:2rem">
        {'✅' if verdict=='PASS' else '⚠️' if verdict=='CONDITIONAL' else '❌'}
        &nbsp;{verdict}
      </h2>
      <div>
        <div class="text-muted small">Claim ID</div>
        <strong>{_safe(claim_id)}</strong>
      </div>
      <div>
        <div class="text-muted small">Package</div>
        <strong>{_safe(pkg)}</strong>
      </div>
      <div>
        <div class="text-muted small">Compliance Score</div>
        <strong style="color:{v_color}">{_pct(score)}</strong>
      </div>
      <div>
        <div class="text-muted small">Confidence</div>
        <strong>{_pct(conf)}</strong>
      </div>
    </div>
  </div>

  <!-- Patient Strip -->
  <div class="row g-3 mb-4">
    <div class="col"><div class="metric-card">
      <div class="value">{_safe(cl.get("patient_name","—"),20)}</div>
      <div class="label">Patient</div>
    </div></div>
    <div class="col"><div class="metric-card">
      <div class="value">{cl.get("admission_date") or "—"}</div>
      <div class="label">Admission</div>
    </div></div>
    <div class="col"><div class="metric-card">
      <div class="value">{cl.get("discharge_date") or "—"}</div>
      <div class="label">Discharge</div>
    </div></div>
    <div class="col"><div class="metric-card">
      <div class="value">{cl.get("length_of_stay_days") or "—"}</div>
      <div class="label">Length of Stay (days)</div>
    </div></div>
    <div class="col-4"><div class="metric-card">
      <div class="value" style="font-size:1rem">{_safe(dx_str,70)}</div>
      <div class="label">Diagnosis</div>
    </div></div>
  </div>

  <!-- Rule Summary Pills -->
  <div class="d-flex gap-3 mb-4">
    <span class="badge bg-success fs-6 px-3 py-2">✅ {passed} Passed</span>
    <span class="badge bg-danger fs-6 px-3 py-2">🔴 {n_crit} Critical</span>
    <span class="badge bg-warning text-dark fs-6 px-3 py-2">🟠 {n_major} Major</span>
    <span class="badge bg-secondary fs-6 px-3 py-2">🟡 {n_minor} Minor</span>
  </div>

  <!-- Tabs -->
  <ul class="nav nav-tabs mb-0" id="mainTabs">
    <li class="nav-item"><button class="nav-link active" data-bs-toggle="tab" data-bs-target="#tabDocs">📄 Document Classification</button></li>
    <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#tabRules">📋 Rule Evaluation</button></li>
    <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#tabTimeline">🕐 Episode Timeline</button></li>
    <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#tabVisual">👁 Visual Elements</button></li>
    <li class="nav-item"><button class="nav-link" data-bs-toggle="tab" data-bs-target="#tabProv">🔍 Provenance</button></li>
  </ul>

  <div class="tab-content border border-top-0 rounded-bottom bg-white p-3 mb-4">

    <!-- Tab 1: Document Classification -->
    <div class="tab-pane fade show active" id="tabDocs">
      <p class="text-muted small mt-2">Each document classified. Extra/non-required documents flagged.</p>
      <table class="table table-sm table-hover table-bordered align-middle">
        <thead><tr>
          <th>Claim ID</th><th>Document</th><th>Type Detected</th>
          <th>Confidence</th><th>Signal</th><th>Issues / Flags</th>
        </tr></thead>
        <tbody>{doc_rows}</tbody>
      </table>
    </div>

    <!-- Tab 2: Rule Evaluation -->
    <div class="tab-pane fade" id="tabRules">
      <p class="text-muted small mt-2">STG rule evaluation for package <strong>{_safe(pkg)}</strong> — with evidence provenance.</p>
      <table class="table table-sm table-hover table-bordered align-middle">
        <thead><tr>
          <th>Result</th><th>Rule ID</th><th>Rule Name</th><th>Conf</th><th>Reason / Message</th>
        </tr></thead>
        <tbody>{rule_rows}</tbody>
      </table>
    </div>

    <!-- Tab 3: Timeline -->
    <div class="tab-pane fade" id="tabTimeline">
      <div class="mt-2">{tl_alert}</div>
      <table class="table table-sm table-hover table-bordered align-middle">
        <thead><tr>
          <th>Seq</th><th>Event Type</th><th>Date</th><th>Source Document</th><th>Validity</th>
        </tr></thead>
        <tbody>{timeline_rows or '<tr><td colspan="5" class="text-muted text-center">No timeline events extracted</td></tr>'}</tbody>
      </table>
    </div>

    <!-- Tab 4: Visual Elements -->
    <div class="tab-pane fade" id="tabVisual">
      <p class="text-muted small mt-2">Stamps, signatures, barcodes detected via image analysis.</p>
      <table class="table table-sm table-hover table-bordered align-middle">
        <thead><tr>
          <th>Element</th><th>Detected</th><th>Confidence</th>
          <th>Document</th><th>Page</th><th>Decoded Value</th>
        </tr></thead>
        <tbody>{ve_rows or '<tr><td colspan="6" class="text-muted text-center">No visual elements detected</td></tr>'}</tbody>
      </table>
    </div>

    <!-- Tab 5: Provenance -->
    <div class="tab-pane fade" id="tabProv">
      <p class="text-muted small mt-2">Every extracted value traced to source document, page and bounding box.</p>
      <table class="table table-sm table-hover table-bordered align-middle">
        <thead><tr>
          <th>Field</th><th>Value</th><th>Document</th><th>Page</th><th>Confidence</th><th>Bounding Box</th>
        </tr></thead>
        <tbody>{prov_rows or '<tr><td colspan="6" class="text-muted text-center">No provenance data available</td></tr>'}</tbody>
      </table>
    </div>

  </div>

  <p class="text-muted small text-center">
    NHA PMJAY Automated Claims Processing System · Problem Statement 01 · 2026
  </p>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""
    return html


def main():
    if len(sys.argv) > 1:
        files = [Path(sys.argv[1])]
    else:
        report_dir = BASE / "output_reports"
        files = list(report_dir.glob("*.json"))

    if not files:
        print("No JSON report files found.")
        return

    out_dir = BASE / "html_reports"
    out_dir.mkdir(exist_ok=True)

    index_rows = ""
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        html = render(data)
        out_file = out_dir / f.with_suffix(".html").name
        out_file.write_text(html, encoding="utf-8")
        print(f"  ✓  {out_file}")

        dec = data.get("decision", {})
        cl  = data.get("claim", {})
        verdict = dec.get("verdict","?")
        color = {"PASS":"success","CONDITIONAL":"warning","FAIL":"danger"}.get(verdict,"secondary")
        icon  = {"PASS":"✅","CONDITIONAL":"⚠️","FAIL":"❌"}.get(verdict,"❓")
        index_rows += f"""<tr>
          <td><a href="{out_file.name}">{cl.get("claim_id","")}</a></td>
          <td>{cl.get("package_code","")}</td>
          <td><span class="badge bg-{color}">{icon} {verdict}</span></td>
          <td>{dec.get("overall_score",0):.1%}</td>
          <td>{dec.get("confidence",0):.1%}</td>
          <td>{cl.get("admission_date") or "—"}</td>
          <td>{cl.get("discharge_date") or "—"}</td>
          <td>{len(dec.get("critical_failures",[]))}</td>
          <td>{len(dec.get("major_failures",[]))}</td>
        </tr>"""

    # Write index
    index_html = f"""<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><title>NHA PMJAY – All Claims</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
</head><body>
<nav class="navbar navbar-dark px-4 py-2" style="background:#00448a">
  <span class="navbar-brand fw-bold">🏥 NHA PMJAY Claims Processor – All Claims</span>
</nav>
<div class="container-fluid py-4">
<table class="table table-hover table-bordered table-sm align-middle">
<thead class="table-dark"><tr>
  <th>Claim ID</th><th>Package</th><th>Verdict</th><th>Score</th><th>Confidence</th>
  <th>Admit</th><th>Discharge</th><th>Critical Fails</th><th>Major Fails</th>
</tr></thead>
<tbody>{index_rows}</tbody>
</table>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body></html>"""
    idx_file = out_dir / "index.html"
    idx_file.write_text(index_html, encoding="utf-8")
    print(f"\n  📋 Index: {idx_file}")
    print(f"\nOpen html_reports/index.html in your browser — no server needed.")


if __name__ == "__main__":
    main()
