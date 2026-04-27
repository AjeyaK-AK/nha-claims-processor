"""
NHA PMJAY Claims Processing – REST API
Upload claim documents (ZIP), run the pipeline, get JSON/HTML results.

Endpoints:
  POST /api/upload              – upload zip + package_code → job_id
  GET  /api/status/{job_id}     – poll processing status
  GET  /api/result/{job_id}     – download JSON report
  GET  /api/report/{job_id}     – view HTML report
  GET  /api/jobs                – list all submitted jobs
  DELETE /api/jobs/{job_id}     – clean up a job
"""

from __future__ import annotations

import io
import json
import logging
import shutil
import tempfile
import traceback
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, Optional

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

# ── logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── app ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="NHA PMJAY Claims Processor API",
    description="Upload medical claim documents for automated audit processing.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── in-memory job store ───────────────────────────────────────────────────────
# { job_id: { "status": str, "package_code": str, "claim_id": str,
#             "work_dir": Path, "report": dict|None, "html": str|None,
#             "error": str|None } }
_JOBS: Dict[str, dict] = {}
_EXECUTOR = ThreadPoolExecutor(max_workers=4)

BASE_DIR = Path(__file__).parent
JOBS_DIR = BASE_DIR / "_api_jobs"
JOBS_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp"}
MAX_UPLOAD_MB = 200


# ── helpers ───────────────────────────────────────────────────────────────────

def _sanitize_package_code(code: str) -> str:
    """Allow only alphanumeric + underscore to avoid path traversal."""
    cleaned = "".join(c for c in code if c.isalnum() or c == "_")
    if not cleaned:
        raise ValueError("Invalid package_code")
    return cleaned.upper()


def _extract_upload(zip_bytes: bytes, dest_dir: Path) -> None:
    """Extract uploaded ZIP, rejecting unsafe paths and unsupported files."""
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for member in zf.infolist():
            # Security: reject absolute paths and path-traversal
            member_path = Path(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ValueError(f"Unsafe path in ZIP: {member.filename}")

            suffix = member_path.suffix.lower()
            # Skip directories and unsupported file types
            if member.is_dir():
                continue
            if suffix not in ALLOWED_EXTENSIONS:
                log.warning("Skipping unsupported file in ZIP: %s", member.filename)
                continue

            # Flatten: all files go directly into dest_dir
            out_path = dest_dir / member_path.name
            out_path.write_bytes(zf.read(member.filename))


def _run_pipeline(job_id: str) -> None:
    """Worker: run ClaimProcessor and store result on the job record."""
    job = _JOBS[job_id]
    work_dir: Path = job["work_dir"]
    package_code: str = job["package_code"]
    claim_id: str = job["claim_id"]

    try:
        job["status"] = "processing"

        # Import here so startup is fast even if heavy deps are slow
        from pipeline import ClaimProcessor
        from src.output.report_generator import ReportGenerator

        processor = ClaimProcessor(output_dir=work_dir / "output")
        decision = processor.process(work_dir / "claim", package_code)

        # Serialise report
        report_path = work_dir / "output" / f"{claim_id}_{package_code}_report.json"

        if report_path.exists():
            with open(report_path) as f:
                job["report"] = json.load(f)
        else:
            # Build report dict from decision object
            job["report"] = decision.__dict__ if hasattr(decision, "__dict__") else str(decision)

        # Generate HTML report
        try:
            reporter = ReportGenerator()
            html = reporter.generate_html(decision, claim_id=claim_id, package_code=package_code)
            job["html"] = html
        except Exception:
            job["html"] = None

        job["status"] = "done"
        log.info("Job %s completed successfully", job_id)

    except Exception as exc:
        job["status"] = "failed"
        job["error"] = traceback.format_exc()
        log.error("Job %s failed: %s", job_id, exc)


# ── routes ────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    """Simple upload form for browser testing."""
    return HTMLResponse(content=_upload_form_html(), status_code=200)


@app.post("/api/upload")
async def upload_claim(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="ZIP archive containing claim documents"),
    package_code: str = Form(..., description="Package code, e.g. SB039A"),
    claim_id: Optional[str] = Form(None, description="Claim ID (optional, derived from filename if omitted)"),
):
    """
    Upload a ZIP of claim documents and start processing.
    Returns a job_id to poll for status.
    """
    # Validate package_code
    try:
        package_code = _sanitize_package_code(package_code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Validate file type
    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only ZIP files are accepted.")

    # Read upload (size limit)
    zip_bytes = await file.read()
    size_mb = len(zip_bytes) / (1024 * 1024)
    if size_mb > MAX_UPLOAD_MB:
        raise HTTPException(status_code=413, detail=f"File too large ({size_mb:.1f} MB > {MAX_UPLOAD_MB} MB limit).")

    # Derive claim_id
    if not claim_id:
        stem = Path(file.filename).stem
        claim_id = stem if stem else "CLAIM"
    # Sanitize claim_id
    claim_id = "".join(c for c in claim_id if c.isalnum() or c in "_-")[:64] or "CLAIM"

    # Create job workspace
    job_id = str(uuid.uuid4())
    work_dir = JOBS_DIR / job_id
    claim_dir = work_dir / "claim"
    claim_dir.mkdir(parents=True, exist_ok=True)

    # Extract files
    try:
        _extract_upload(zip_bytes, claim_dir)
    except (zipfile.BadZipFile, ValueError) as e:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=f"Invalid ZIP: {e}")

    # Register job
    _JOBS[job_id] = {
        "status": "queued",
        "package_code": package_code,
        "claim_id": claim_id,
        "work_dir": work_dir,
        "report": None,
        "html": None,
        "error": None,
    }

    # Submit to thread pool
    background_tasks.add_task(_run_pipeline_bg, job_id)

    return JSONResponse(
        status_code=202,
        content={
            "job_id": job_id,
            "status": "queued",
            "claim_id": claim_id,
            "package_code": package_code,
            "poll_url": f"/api/status/{job_id}",
        },
    )


def _run_pipeline_bg(job_id: str):
    """Wrapper so background_tasks can call _run_pipeline."""
    _run_pipeline(job_id)


@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    """Poll the status of a submitted job."""
    job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    resp = {
        "job_id": job_id,
        "status": job["status"],
        "claim_id": job["claim_id"],
        "package_code": job["package_code"],
    }
    if job["status"] == "failed":
        resp["error"] = job["error"]
    if job["status"] == "done":
        resp["result_url"] = f"/api/result/{job_id}"
        resp["report_url"] = f"/api/report/{job_id}"
    return JSONResponse(content=resp)


@app.get("/api/result/{job_id}")
async def get_result(job_id: str):
    """Download the JSON report for a completed job."""
    job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job["status"] != "done":
        raise HTTPException(status_code=409, detail=f"Job is not done yet (status: {job['status']}).")
    return JSONResponse(content=job["report"])


@app.get("/api/report/{job_id}", response_class=HTMLResponse)
async def get_report(job_id: str):
    """View the HTML report for a completed job."""
    job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job["status"] != "done":
        raise HTTPException(status_code=409, detail=f"Job is not done yet (status: {job['status']}).")

    html = job.get("html")
    if html:
        return HTMLResponse(content=html)

    # Fallback: render JSON as simple HTML
    report_json = json.dumps(job["report"], indent=2)
    return HTMLResponse(content=f"<pre>{report_json}</pre>")


@app.get("/api/jobs")
async def list_jobs():
    """List all submitted jobs and their statuses."""
    return JSONResponse(content={
        jid: {
            "status": j["status"],
            "claim_id": j["claim_id"],
            "package_code": j["package_code"],
        }
        for jid, j in _JOBS.items()
    })


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    """Remove a job and its temporary files."""
    job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job["status"] in ("queued", "processing"):
        raise HTTPException(status_code=409, detail="Cannot delete a running job.")
    shutil.rmtree(job["work_dir"], ignore_errors=True)
    del _JOBS[job_id]
    return JSONResponse(content={"deleted": job_id})


# ── embedded upload form ───────────────────────────────────────────────────────

def _upload_form_html() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>PMJAY Claims Processor</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: Arial, sans-serif; background: #f0f4f8; display: flex;
           justify-content: center; align-items: flex-start; min-height: 100vh; padding: 40px 20px; }
    .card { background: white; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            padding: 40px; max-width: 600px; width: 100%; }
    h1 { color: #1a3a5c; font-size: 1.6rem; margin-bottom: 8px; }
    .subtitle { color: #666; margin-bottom: 30px; font-size: 0.95rem; }
    label { display: block; font-weight: 600; margin-bottom: 6px; color: #333; }
    input, select { width: 100%; padding: 10px 14px; border: 1px solid #ccc;
                    border-radius: 8px; font-size: 1rem; margin-bottom: 20px; }
    input[type=file] { padding: 8px; }
    button { width: 100%; padding: 12px; background: #1a3a5c; color: white;
             border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; }
    button:hover { background: #2a5a8c; }
    #status-box { margin-top: 24px; padding: 16px; background: #f8f9fa;
                  border-radius: 8px; border-left: 4px solid #1a3a5c; display: none; }
    #status-box.done { border-color: #28a745; }
    #status-box.failed { border-color: #dc3545; }
    a.btn-link { display: inline-block; margin-top: 12px; padding: 8px 16px;
                 background: #28a745; color: white; border-radius: 6px;
                 text-decoration: none; font-size: 0.9rem; }
    .spinner { display: inline-block; width: 16px; height: 16px; border: 3px solid #ccc;
               border-top-color: #1a3a5c; border-radius: 50%; animation: spin 0.8s linear infinite;
               vertical-align: middle; margin-right: 8px; }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>
<div class="card">
  <h1>🏥 PMJAY Claims Processor</h1>
  <p class="subtitle">Upload a ZIP of claim documents for automated audit analysis.</p>

  <form id="upload-form">
    <label for="file">Claim Documents (ZIP)</label>
    <input type="file" id="file" name="file" accept=".zip" required/>

    <label for="package_code">Package Code</label>
    <input type="text" id="package_code" name="package_code"
           placeholder="e.g. SB039A" required maxlength="20"/>

    <label for="claim_id">Claim ID (optional)</label>
    <input type="text" id="claim_id" name="claim_id"
           placeholder="Leave blank to use filename" maxlength="64"/>

    <button type="submit">Upload &amp; Process</button>
  </form>

  <div id="status-box">
    <p id="status-text"></p>
    <div id="links"></div>
  </div>
</div>

<script>
  const form = document.getElementById('upload-form');
  const statusBox = document.getElementById('status-box');
  const statusText = document.getElementById('status-text');
  const linksDiv = document.getElementById('links');

  function setStatus(msg, cls) {
    statusBox.style.display = 'block';
    statusBox.className = cls || '';
    statusText.innerHTML = msg;
  }

  async function poll(jobId) {
    const res = await fetch('/api/status/' + jobId);
    const data = await res.json();
    if (data.status === 'done') {
      setStatus('✅ Processing complete!', 'done');
      linksDiv.innerHTML =
        '<a class="btn-link" href="/api/report/' + jobId + '" target="_blank">View Report</a> ' +
        '<a class="btn-link" href="/api/result/' + jobId + '" target="_blank" style="background:#1a3a5c">Download JSON</a>';
    } else if (data.status === 'failed') {
      setStatus('❌ Processing failed. Please check your files and try again.', 'failed');
    } else {
      setStatus('<span class="spinner"></span>Status: <strong>' + data.status + '</strong> …', '');
      setTimeout(() => poll(jobId), 2000);
    }
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    linksDiv.innerHTML = '';
    setStatus('<span class="spinner"></span>Uploading…', '');

    const fd = new FormData(form);
    try {
      const res = await fetch('/api/upload', { method: 'POST', body: fd });
      const data = await res.json();
      if (!res.ok) {
        setStatus('❌ ' + (data.detail || 'Upload failed'), 'failed');
        return;
      }
      setStatus('<span class="spinner"></span>Queued (Job: ' + data.job_id.slice(0,8) + '…). Processing…', '');
      poll(data.job_id);
    } catch (err) {
      setStatus('❌ Network error: ' + err.message, 'failed');
    }
  });
</script>
</body>
</html>"""


# ── entrypoint ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
