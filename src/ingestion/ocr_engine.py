"""
OCR Engine: wraps pytesseract + easyocr with automatic fallback.
Returns (text, confidence, engine_used).
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Tuple

import pytesseract
from PIL import Image

from config import TESSERACT_CMD, TESSERACT_LANG, MIN_TEXT_LENGTH, OCR_LANGUAGES, USE_EASYOCR_FALLBACK

log = logging.getLogger(__name__)

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD


@lru_cache(maxsize=1)
def _get_easyocr_reader():
    """Lazy-load easyocr reader (heavy model download on first call)."""
    try:
        import easyocr
        return easyocr.Reader(OCR_LANGUAGES, gpu=False, verbose=False)
    except Exception as exc:
        log.warning("easyocr unavailable: %s", exc)
        return None


def ocr_image(img: Image.Image, aggressive: bool = False) -> Tuple[str, float, str]:
    """
    Run OCR on a PIL Image.
    Returns (text, confidence_0_to_1, engine_name).
    Tries raw image first; only enhances if quality is poor.
    """
    from src.ingestion.preprocessor import enhance_image, auto_orient  # local import avoids circular

    def _tess_run(pil_img, psm: int = 6):
        # Single OCR call: extract both text and confidence from image_to_data
        data = pytesseract.image_to_data(
            pil_img, lang=TESSERACT_LANG,
            output_type=pytesseract.Output.DICT,
            config=f"--oem 3 --psm {psm}",
        )
        confs = [int(c) for c in data["conf"] if str(c).lstrip("-").isdigit() and int(c) >= 0]
        # Reconstruct text from words with non-negative confidence (avoid two-pass OCR)
        words = [
            data["text"][i]
            for i in range(len(data["text"]))
            if str(data["conf"][i]).lstrip("-").isdigit()
               and int(data["conf"][i]) >= 0
               and data["text"][i].strip()
        ]
        text = " ".join(words).strip()
        conf = (sum(confs) / len(confs) / 100.0) if confs else 0.0
        return text, conf

    # ── 1. Try raw image first ───────────────────────────────────────────────
    raw_text, raw_conf = "", 0.0
    try:
        raw_text, raw_conf = _tess_run(img)
    except Exception as exc:
        log.debug("Tesseract raw failed: %s", exc)

    # Early exit: if raw quality is already good, skip enhancement pass
    if raw_conf >= 0.60 and len(raw_text) >= MIN_TEXT_LENGTH:
        return raw_text, raw_conf, "tesseract"

    # ── 2. Try enhanced image (only if raw quality is poor) ──────────────────
    enhanced_text, enhanced_conf = "", 0.0
    try:
        processed = enhance_image(img, aggressive=aggressive)
        enhanced_text, enhanced_conf = _tess_run(processed)
    except Exception as exc:
        log.debug("Tesseract enhanced failed: %s", exc)

    # Choose the better result
    if raw_conf >= enhanced_conf and len(raw_text) >= len(enhanced_text):
        tess_text, tess_conf = raw_text, raw_conf
    elif enhanced_conf > raw_conf:
        tess_text, tess_conf = enhanced_text, enhanced_conf
    else:
        tess_text, tess_conf = raw_text, raw_conf

    # ── 3. Try OSD-corrected orientation if still poor ───────────────────────
    if tess_conf < 0.45 or len(tess_text) < MIN_TEXT_LENGTH:
        try:
            oriented_img = auto_orient(img)
            if oriented_img is not img:
                or_text, or_conf = _tess_run(oriented_img)
                if or_conf > tess_conf and len(or_text) > len(tess_text):
                    tess_text, tess_conf = or_text, or_conf
        except Exception:
            pass

    if len(tess_text) >= MIN_TEXT_LENGTH and tess_conf >= 0.50:
        return tess_text, tess_conf, "tesseract"

    # ── Fallback: easyocr ────────────────────────────────────────────────────
    if not USE_EASYOCR_FALLBACK:
        best_text = tess_text if tess_text else ""
        return best_text, tess_conf, "tesseract"

    reader = _get_easyocr_reader()
    if reader is not None:
        try:
            import numpy as np
            img_arr = np.array(img)
            results = reader.readtext(img_arr, detail=1)
            easy_text = " ".join(r[1] for r in results)
            easy_conf = (sum(r[2] for r in results) / len(results)) if results else 0.0
            if len(easy_text) >= MIN_TEXT_LENGTH:
                return easy_text, easy_conf, "easyocr"
        except Exception as exc:
            log.debug("easyocr failed: %s", exc)

    # ── Return best available ────────────────────────────────────────────────
    best_text = tess_text if tess_text else ""
    return best_text, tess_conf, "tesseract"
