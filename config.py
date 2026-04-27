"""
Global configuration for the Medical Claims Processor.
All paths, thresholds, and tunable parameters live here.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent

# ── Data roots ──────────────────────────────────────────────────────────────
CLAIMS_ROOTS = [
    BASE_DIR / "extract_1" / "Claims",
    BASE_DIR / "extract_2" / "Claims",
]
OUTPUT_DIR = BASE_DIR / "output_reports"
OUTPUT_DIR.mkdir(exist_ok=True)

STG_RULES_DIR = BASE_DIR / "src" / "rules" / "stg_rules"

# ── OCR settings ─────────────────────────────────────────────────────────────
TESSERACT_CMD = os.environ.get("TESSERACT_CMD", "tesseract")  # use PATH
OCR_LANGUAGES = ["en", "hi"]          # easyocr language list
TESSERACT_LANG = "eng"                # tesseract lang string (hin requires separate pack)
USE_EASYOCR_FALLBACK = os.environ.get("USE_EASYOCR", "0") == "1"  # off by default (slow download)
PDF_DPI = 150                          # DPI when rendering PDF page to image (150 balances speed and OCR accuracy)
MIN_TEXT_LENGTH = 20                   # chars – below this, re-run with image OCR

# ── Classification thresholds ────────────────────────────────────────────────
FILENAME_LABEL_CONFIDENCE = 0.92       # confidence when label is parsed from filename
CONTENT_MATCH_CONFIDENCE_SCALE = 0.85  # max confidence for content-only match
UNKNOWN_DOC_CONFIDENCE = 0.40          # when no signal found

# ── Visual detection ─────────────────────────────────────────────────────────
STAMP_MIN_AREA = 2000                  # px²
STAMP_MIN_CIRCULARITY = 0.45
SIGNATURE_MIN_ASPECT = 2.0
QR_BARCODE_TYPES = {"QRCODE", "CODE128", "CODE39", "EAN13", "EAN8", "PDF417"}

# ── Rules engine ─────────────────────────────────────────────────────────────
SEVERITY_WEIGHTS = {"critical": 1.0, "major": 0.6, "minor": 0.2}
PASS_THRESHOLD = 0.90
CONDITIONAL_THRESHOLD = 0.60

# ── Timeline ──────────────────────────────────────────────────────────────────
MAX_PRE_ADMIT_DAYS = 3                 # investigations allowed N days before admit
MAX_POST_DISCHARGE_DAYS = 1           # reports signed N days after discharge
