# NHA PMJAY Automated Claims Processing System
### Hackathon Problem Statement 01 · 2026

Automatically reads mixed-quality healthcare documents (scans, photos, PDFs), extracts key data, detects mandatory visual elements (stamps/signatures/barcodes), checks compliance with Standard Treatment Guidelines (STG), and produces an explainable **Pass / Conditional / Fail** decision.

---

## Live Demo
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)

---

## What it does
| Step | Component |
|---|---|
| **Ingest** | PDFs + images → PyMuPDF + Tesseract OCR (raw-first strategy) |
| **Classify** | Each document labelled (discharge summary, X-ray, operative notes…) via filename signal (conf 0.92) + content keywords |
| **Extract** | Patient name, dates, diagnosis, billed amount with page + bounding-box provenance |
| **Visual Detection** | Hospital stamp, doctor signature, barcode/sticker via OpenCV morphology |
| **Rules Engine** | STG YAML rules per package code (8 packages) — document presence, temporal, LOS, visual element checks |
| **Decision** | Weighted Pass / Conditional / Fail with per-rule evidence |
| **UI** | Streamlit dashboard matching NHA sample output tables |

---

## Quick Start (local)

```bash
# 1. Install system dependency (Windows)
#    Download Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
#    Add to PATH

# 2. Install Python deps
pip install -r requirements.txt

# 3. Add claim data under:
#    extract_1/Claims/<PACKAGE>/<CLAIM_ID>/
#    extract_2/Claims/<PACKAGE>/<CLAIM_ID>/

# 4. Launch UI
streamlit run app.py
```

---

## Deploy to Streamlit Community Cloud

1. Push this repo to GitHub (data folders are in `.gitignore` — patient data stays local)
2. Go to **https://share.streamlit.io** → New app
3. Select your repo, branch `main`, file `app.py`
5. The cloud app runs in **demo mode** showing the pre-computed reports in `demo_reports/`

---

## Deploy to Lightning.ai

1. Push this repo to GitHub (data folders are in `.gitignore` — patient data stays local)
2. Go to your Lightning.ai studio (e.g., https://lightning.ai/ajeyaraok/nha/studios/free-purple-om24/code)
3. Connect your GitHub repo to the studio
4. Deploy the FastAPI app using the `lightning.yaml` configuration
5. The API will be accessible at the public URL (e.g., https://free-purple-om24.lightning.ai)

API Endpoints:
- `POST /api/upload` – Upload ZIP + package_code → job_id
- `GET /api/status/{job_id}` – Poll processing status
- `GET /api/result/{job_id}` – Download JSON report
- `GET /api/report/{job_id}` – View HTML report
- `GET /api/jobs` – List all submitted jobs
- `DELETE /api/jobs/{job_id}` – Clean up a job

---

## Scoring Targets
| Category | Weight | Target F1 |
|---|---|---|
| Document Classification | 40% | ≥ 0.95 |
| Rules + Provenance | 40% | ≥ 0.96 |
| Solution Design | 20% | ≥ 0.93 |

---

## Package Codes Supported
`SB039A` · `SG039C` · `MG006A` · `MG064A` · `MC011A` · `MG029A` · `SG039` · `SU007A`
