"""
NHA PMJAY Claims Processing System - Streamlit Demo UI
Matches the sample output format from NHA Problem Statement 01
"""

import streamlit as st
import json
import os
import subprocess
import sys
from pathlib import Path

# ── page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NHA PMJAY Claims Processor",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── helpers ─────────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent
REPORT_DIR = BASE / "output_reports"
EXTRACT_DIRS = [BASE / "extract_1" / "Claims", BASE / "extract_2" / "Claims"]
DEMO_REPORT_DIR = BASE / "demo_reports"   # pre-computed reports for cloud demo

# Demo mode: claim data not present (e.g. Streamlit Cloud deployment)
DATA_AVAILABLE = any(p.exists() for p in EXTRACT_DIRS)
DEMO_MODE = not DATA_AVAILABLE

VERDICT_COLOR = {"PASS": "#28a745", "CONDITIONAL": "#fd7e14", "FAIL": "#dc3545"}
VERDICT_ICON  = {"PASS": "✅", "CONDITIONAL": "⚠️", "FAIL": "❌"}

RESULT_BADGE = {
    "PASS":         "🟢 PASS",
    "FAIL-CRITICAL":"🔴 FAIL (Critical)",
    "FAIL-MAJOR":   "🟠 FAIL (Major)",
    "FAIL-MINOR":   "🟡 FAIL (Minor)",
}

def discover_claims():
    """Return dict  {display_label: (claim_dir_or_None, package_code, claim_id)}"""
    claims = {}

    # Live data mode
    for base in EXTRACT_DIRS:
        if not base.exists():
            continue
        for pkg_dir in sorted(base.iterdir()):
            if not pkg_dir.is_dir() or pkg_dir.name.startswith("."):
                continue
            for claim_dir in sorted(pkg_dir.iterdir()):
                if not claim_dir.is_dir() or claim_dir.name.startswith("."):
                    continue
                label = claim_dir.name
                claims[label] = (claim_dir, pkg_dir.name, claim_dir.name)

    # Demo mode: load from pre-computed report filenames
    if not claims:
        report_dir = DEMO_REPORT_DIR if DEMO_REPORT_DIR.exists() else REPORT_DIR
        for rfile in sorted(report_dir.glob("*.json")):
            stem = rfile.stem  # e.g. CMJAY_..._SB039A_report
            parts = stem.replace("_report", "").rsplit("_", 1)
            if len(parts) == 2:
                cid, pkg = parts
                label = f"{cid}  [demo]"
                claims[label] = (None, pkg, cid)

    return claims

def report_path_for(claim_id, package_code):
    # Check demo_reports first, then output_reports
    for folder in [DEMO_REPORT_DIR, REPORT_DIR]:
        p = folder / f"{claim_id}_{package_code}_report.json"
        if p.exists():
            return p
    return REPORT_DIR / f"{claim_id}_{package_code}_report.json"

def load_report(path):
    with open(path) as f:
        return json.load(f)

def run_pipeline(claim_dir: Path, package_code: str):
    """Run pipeline.py as subprocess and return report path."""
    script = BASE / "pipeline_run.py"
    result = subprocess.run(
        [sys.executable, str(script),
         "--claim_dir", str(claim_dir),
         "--package_code", package_code],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(BASE)
    )
    return result.returncode == 0, result.stdout, result.stderr


# ── sidebar ─────────────────────────────────────────────────────────────────────
st.sidebar.image("https://nha.gov.in/images/logo.png", use_container_width=True)
st.sidebar.title("🏥 NHA PMJAY\nClaims Processor")
st.sidebar.markdown("---")

all_claims = discover_claims()

# Build package → claim_id mapping for filtered selection
pkg_to_claims: dict = {}
for label, (cdir, pkg, cid) in all_claims.items():
    pkg_to_claims.setdefault(pkg, []).append(label)

all_packages = sorted(pkg_to_claims.keys())

st.sidebar.subheader("🔍 Select Claim")

# Step 1 – filter by package
selected_pkg = st.sidebar.selectbox(
    "1️⃣ Package Code",
    ["All Packages"] + all_packages,
    help="Filter claims by PMJAY package code"
)

# Step 2 – pick a specific claim
if selected_pkg == "All Packages":
    filtered_labels = list(all_claims.keys())
else:
    filtered_labels = pkg_to_claims.get(selected_pkg, [])

selected_label = st.sidebar.selectbox(
    "2️⃣ Claim ID",
    filtered_labels,
    help="Select the claim to analyse",
    format_func=lambda x: all_claims[x][2]   # show only claim_id, not full path
)

claim_dir, package_code, claim_id = all_claims[selected_label]
rpath = report_path_for(claim_id, package_code)

# Status indicator
report_exists = rpath.exists()
if report_exists:
    st.sidebar.success(f"✅ Report available — `{package_code}`")
else:
    st.sidebar.warning("⚠️ No report yet — run pipeline below")

st.sidebar.markdown("---")

if DEMO_MODE:
    st.sidebar.info("🖥 **Demo mode** — pre-computed reports only.\nTo run live, clone the repo and add claim data locally.")
    run_btn = False
else:
    run_btn = st.sidebar.button(
        "▶ Run Pipeline" if not report_exists else "🔄 Re-run Pipeline",
        type="primary",
        use_container_width=True,
        disabled=(claim_dir is None),
        help="Process this claim through the full compliance pipeline"
    )

st.sidebar.markdown("---")
st.sidebar.caption("Problem Statement 01 · NHA Hackathon 2026")

# ── run pipeline if requested ───────────────────────────────────────────────────
if run_btn:
    log_placeholder = st.sidebar.empty()
    progress = st.sidebar.progress(0, text="Starting pipeline…")
    with st.spinner(f"Processing **{claim_id}** ({package_code}) …"):
        progress.progress(20, text="Ingesting documents…")
        ok, out, err = run_pipeline(claim_dir, package_code)
        progress.progress(100, text="Done")
    progress.empty()
    if ok and rpath.exists():
        st.sidebar.success("✅ Pipeline complete — report ready")
        log_placeholder.empty()
        st.rerun()
    else:
        st.sidebar.error("❌ Pipeline error")
        with st.sidebar.expander("Show error log"):
            st.code((err or out)[-2000:])

# ── main panel ──────────────────────────────────────────────────────────────────
st.title("NHA PMJAY Automated Claims Processing")
st.markdown(f"**Claim:** `{claim_id}`  |  **Package:** `{package_code}`")

if not rpath.exists():
    st.info("No report found for this claim. Click **▶ Run Pipeline** in the sidebar to process it.")
    st.stop()

data = load_report(rpath)
dec  = data.get("decision", {})
dc   = data.get("document_classification", [])
ve   = data.get("visual_elements", [])
tl   = data.get("episode_timeline", {})
prov = data.get("provenance_log", [])
cl   = data.get("claim", {})
extra = data.get("extra_documents_flagged", [])

# ── verdict banner ──────────────────────────────────────────────────────────────
verdict = dec.get("verdict", "UNKNOWN")
score   = dec.get("overall_score", 0)
conf    = dec.get("confidence", 0)
color   = VERDICT_COLOR.get(verdict, "#6c757d")
icon    = VERDICT_ICON.get(verdict, "❓")

st.markdown(f"""
<div style="background:{color};padding:20px 30px;border-radius:10px;margin-bottom:20px">
  <h2 style="color:white;margin:0">{icon} &nbsp; {verdict}</h2>
  <p style="color:white;margin:4px 0 0 0;font-size:1.1em">
    Compliance Score: <b>{score:.1%}</b> &nbsp;|&nbsp; Confidence: <b>{conf:.1%}</b>
  </p>
</div>
""", unsafe_allow_html=True)

# ── patient summary strip ───────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Patient",  (cl.get("patient_name") or "—")[:25])
c2.metric("Admit",    cl.get("admission_date")  or "—")
c3.metric("Discharge",cl.get("discharge_date")  or "—")
c4.metric("LoS",      f"{cl.get('length_of_stay_days') or '—'} days")
c5.metric("Diagnosis",(", ".join(cl.get("diagnosis") or []) or "—")[:30])

st.markdown("---")

# ── tabs ────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📄 Document Classification",
    "📋 Rule Evaluation",
    "🕐 Episode Timeline",
    "👁 Visual Elements",
    "🔍 Provenance / Evidence",
])

# ── Tab 1: Document Classification (matches NHA sample table) ──────────────────
with tab1:
    st.subheader("Document Classification")
    st.caption("Each document is classified by page. Extra/non-required documents are flagged.")

    rows = []
    for doc in dc:
        doc_id   = doc.get("doc_id", "")
        dtype    = doc.get("predicted_type") or doc.get("doc_type", "unknown")
        conf_val = doc.get("confidence", 0)
        signal   = doc.get("signal", "")
        src      = doc.get("source_path", "")
        fname    = Path(src).name if src else doc_id
        is_extra = doc_id in (extra or [])
        flag     = "⚠ Not required for this package" if is_extra else ""

        # failures on this doc from rule details
        doc_flags = []
        for rd in dec.get("rule_details", []):
            for ev in rd.get("evidence", []):
                if ev.get("doc_id") == doc_id and rd.get("result","").startswith("FAIL"):
                    doc_flags.append(rd.get("message",""))

        rows.append({
            "Claim ID":      claim_id[:20],
            "Document":      fname[:55],
            "Type Detected": dtype.replace("_", " ").title(),
            "Signal":        signal,
            "Confidence":    f"{conf_val:.0%}",
            "Issues / Flags": " · ".join(set(doc_flags)) or flag or "—",
        })

    if rows:
        import pandas as pd
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No documents classified.")

# ── Tab 2: Rule Evaluation ──────────────────────────────────────────────────────
with tab2:
    st.subheader(f"STG Rule Evaluation — Package `{package_code}`")

    passed  = dec.get("passed_rules",   [])
    crit    = dec.get("critical_failures", [])
    major   = dec.get("major_failures",  [])
    minor   = dec.get("minor_failures",  [])

    col_p, col_c, col_ma, col_mi = st.columns(4)
    col_p.metric("✅ Passed",   len(passed))
    col_c.metric("🔴 Critical", len(crit))
    col_ma.metric("🟠 Major",   len(major))
    col_mi.metric("🟡 Minor",   len(minor))

    st.markdown("#### Rule Details")
    for rd in dec.get("rule_details", []):
        result  = rd.get("result", "")
        badge   = RESULT_BADGE.get(result, f"⚪ {result}")
        rid     = rd.get("rule_id", "")
        rname   = rd.get("rule_name", "")
        msg     = rd.get("message", "")
        rconf   = rd.get("confidence", 0)
        evid    = rd.get("evidence", [])

        with st.expander(f"{badge}  **{rid}** — {rname}  *(conf {rconf:.0%})*"):
            if msg:
                st.write(f"**Reason:** {msg}")
            if evid:
                st.markdown("**Evidence:**")
                for ev in evid:
                    bb = ev.get("bounding_box") or {}
                    st.markdown(
                        f"- Doc `{ev.get('doc_id','')[:50]}` · "
                        f"Page {ev.get('page','?')} · "
                        f"Field `{ev.get('field', ev.get('field_name',''))}` · "
                        f"Value `{str(ev.get('value',''))[:50]}` · "
                        f"Conf {ev.get('confidence',0):.0%}"
                        + (f" · BBox ({bb.get('x0',0):.0f},{bb.get('y0',0):.0f})→"
                           f"({bb.get('x1',0):.0f},{bb.get('y1',0):.0f})" if bb else "")
                    )

# ── Tab 3: Episode Timeline (matches NHA sample table) ─────────────────────────
with tab3:
    st.subheader("Episode Timeline")
    plausible = tl.get("is_plausible", None)
    flags     = tl.get("plausibility_flags", [])

    if plausible is True:
        st.success("Timeline is temporally plausible ✓")
    elif plausible is False:
        st.error("Timeline has plausibility issues")
        for f in flags:
            st.warning(f"⚠ {f}")
    else:
        st.info("Timeline plausibility could not be determined (dates missing).")

    events = tl.get("events", [])
    if events:
        import pandas as pd
        rows = []
        for ev in events:
            rows.append({
                "Seq":           ev.get("sequence", ""),
                "Event Type":    ev.get("event_type", ev.get("type","")).replace("_"," ").title(),
                "Date":          str(ev.get("event_date", ev.get("date","N/A")) or "N/A"),
                "Source Document": (ev.get("source_doc") or ev.get("doc_id","—"))[:50],
                "Validity":      ev.get("temporal_validity", ev.get("valid","Unknown")),
            })
        df = pd.DataFrame(rows)
        # colour validity column
        def colour_validity(val):
            if str(val).lower() in ("valid","true"):
                return "background-color:#d4edda"
            elif str(val).lower() in ("invalid","false"):
                return "background-color:#f8d7da"
            return "background-color:#fff3cd"
        st.dataframe(
            df.style.map(colour_validity, subset=["Validity"]),
            use_container_width=True, hide_index=True
        )
    else:
        st.info("No timeline events extracted.")

# ── Tab 4: Visual Elements ──────────────────────────────────────────────────────
with tab4:
    st.subheader("Detected Visual Elements")
    st.caption("Stamps, signatures, barcodes, stickers detected via image analysis")

    if ve:
        import pandas as pd
        rows = []
        for v in ve:
            rows.append({
                "Element Type": v.get("type", v.get("element_type","")).replace("_"," ").title(),
                "Detected":     "✅ Yes" if v.get("detected") else "❌ No",
                "Confidence":   f"{v.get('confidence',0):.0%}",
                "Document":     v.get("doc_id","")[:50],
                "Page":         v.get("page",""),
                "Decoded Value":v.get("decoded_value","") or "—",
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No visual elements detected.")

# ── Tab 5: Provenance ───────────────────────────────────────────────────────────
with tab5:
    st.subheader("Provenance / Evidence Log")
    st.caption("Every extracted value traced back to source document, page and bounding box")

    if prov:
        import pandas as pd
        rows = []
        for p in prov:
            bb = p.get("bounding_box") or {}
            rows.append({
                "Field":       p.get("field",""),
                "Value":       str(p.get("value",""))[:60],
                "Document":    p.get("doc_id","")[:45],
                "Page":        p.get("page",""),
                "Confidence":  f"{p.get('confidence',0):.0%}",
                "BBox":        f"({bb.get('x0',0):.0f},{bb.get('y0',0):.0f})→({bb.get('x1',0):.0f},{bb.get('y1',0):.0f})" if bb else "—",
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        # fall back: pull evidence from rule_details
        rows = []
        for rd in dec.get("rule_details", []):
            for ev in rd.get("evidence", []):
                bb = ev.get("bounding_box") or {}
                rows.append({
                    "Rule":      rd.get("rule_id",""),
                    "Field":     ev.get("field", ev.get("field_name","")),
                    "Value":     str(ev.get("value",""))[:60],
                    "Document":  ev.get("doc_id","")[:45],
                    "Page":      ev.get("page",""),
                    "Confidence":f"{ev.get('confidence',0):.0%}",
                    "BBox":      f"({bb.get('x0',0):.0f},{bb.get('y0',0):.0f})→({bb.get('x1',0):.0f},{bb.get('y1',0):.0f})" if bb else "—",
                })
        if rows:
            import pandas as pd
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No provenance data available.")

# ── footer ──────────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("NHA PMJAY Automated Claims Processing System · Problem Statement 01 · 2026")
