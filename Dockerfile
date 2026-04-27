# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install OS build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps into a separate layer for caching
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim

LABEL maintainer="PMJAY Claims Team"
LABEL description="NHA PMJAY Medical Claims Processor API (with Tesseract OCR)"

# ── System dependencies (Tesseract + supporting libs) ────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Tesseract OCR – solves the local install issue
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-hin \
    # Image processing libs (OpenCV headless needs these)
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    # PDF rendering (PyMuPDF / fitz)
    libmupdf-dev \
    # pyzbar barcode detection
    libzbar0 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# ── App code ──────────────────────────────────────────────────────────────────
WORKDIR /app
COPY . .

# Ensure output directories exist
RUN mkdir -p output_reports _api_jobs

# ── Runtime config ────────────────────────────────────────────────────────────
# Tell pytesseract where to find tesseract
ENV TESSERACT_CMD=tesseract
# Disable EasyOCR by default (large model download); set to "1" to enable
ENV USE_EASYOCR=0
# Python buffering off for live logs
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# ── Healthcheck ───────────────────────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

CMD ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
