"""
Document Classifier: assigns a canonical document type to each DocumentPage.
Uses a three-signal fusion: filename label > content keywords > fallback.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.classification.doc_types import (
    FILENAME_LABEL_MAP,
    CONTENT_KEYWORDS,
    OTHER,
    ALL_TYPES,
    CLINICAL_NOTES,
    NURSING_NOTES,
)
from config import (
    FILENAME_LABEL_CONFIDENCE,
    CONTENT_MATCH_CONFIDENCE_SCALE,
    UNKNOWN_DOC_CONFIDENCE,
)


@dataclass
class ClassificationResult:
    doc_id: str
    source_path: str
    page_number: int
    predicted_type: str
    confidence: float
    signal: str          # "filename" | "content" | "fallback"
    raw_label: str       # label parsed from filename (may be "")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_label_from_filename(doc_id: str) -> str:
    """
    Filename format: {seq}__{claim_id}__{LABEL}
    Return upper-cased LABEL or "" if not available.
    """
    parts = doc_id.split("__")
    if len(parts) >= 3:
        return parts[-1].upper().strip()
    return ""


def _label_to_type(label: str) -> Optional[str]:
    """
    Try exact → regex dynamic patterns → stripped base → prefix → substring match.
    """
    if not label:
        return None
    # Exact match
    if label in FILENAME_LABEL_MAP:
        return FILENAME_LABEL_MAP[label]

    # Dynamic regex patterns for labels like "7D"/"10D" (day notes) and "7N"/"10N" (night notes)
    if re.match(r'^\d+D$', label):
        return CLINICAL_NOTES   # e.g. 7D, 9D, 10D = daily clinical progress notes
    if re.match(r'^\d+N$', label):
        return NURSING_NOTES    # e.g. 7N, 9N, 10N = night nursing notes

    # Strip trailing numbers / _N suffix to get base label
    base = re.sub(r"[_\s]\d+$", "", label).rstrip("_").strip()
    if base in FILENAME_LABEL_MAP:
        return FILENAME_LABEL_MAP[base]

    # Prefix match: find all keys that are prefixes of label
    # Only apply when label is long enough to avoid false positives on 1-2 char labels
    if len(label) >= 3:
        for key, doc_type in FILENAME_LABEL_MAP.items():
            if label.startswith(key) or key.startswith(label[:min(6, len(label))]):
                return doc_type

    # Partial substring match — require key length >= 3 to avoid single-char key false matches
    for key, doc_type in FILENAME_LABEL_MAP.items():
        if len(key) >= 3 and (key in label or label in key):
            return doc_type

    return None


def _uuid_like(label: str) -> bool:
    """Return True if label looks like a UUID (no useful type info)."""
    return bool(re.match(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        label.lower(),
    ))


def _classify_by_content(text: str) -> Tuple[Optional[str], float]:
    """
    Score each canonical type by keyword hit density.
    The first 9 keywords in each list are "strong" signals (3× weight).
    Returns (best_type, confidence) or (None, 0).
    """
    if not text:
        return None, 0.0

    text_lower = text.lower()
    STRONG_N = 9          # first N keywords in each list are "strong"
    STRONG_WEIGHT = 3.0   # weight multiplier for strong keywords

    scores: Dict[str, float] = {}
    for doc_type, keywords in CONTENT_KEYWORDS.items():
        strong_kw  = keywords[:STRONG_N]
        normal_kw  = keywords[STRONG_N:]

        strong_hits = sum(STRONG_WEIGHT for kw in strong_kw if kw in text_lower)
        normal_hits = sum(1.0           for kw in normal_kw if kw in text_lower)
        total_hits  = strong_hits + normal_hits

        if total_hits > 0:
            max_possible = STRONG_N * STRONG_WEIGHT + len(normal_kw)
            scores[doc_type] = total_hits / max(max_possible, 1)

    if not scores:
        return None, 0.0

    best = max(scores, key=scores.get)
    raw_score = scores[best]
    # Scale to avoid overconfidence: max content confidence = 0.85
    confidence = min(raw_score * 2.5, 1.0) * CONTENT_MATCH_CONFIDENCE_SCALE
    return best, confidence


# ── Main classifier ───────────────────────────────────────────────────────────

class DocumentClassifier:
    """
    Stateless classifier – call classify_page() for each DocumentPage.
    Also exposes classify_claim() for a whole claim at once.
    """

    def classify_page(
        self,
        doc_id: str,
        source_path: str,
        page_number: int,
        text: str,
    ) -> ClassificationResult:

        raw_label = _parse_label_from_filename(doc_id)

        # ── Signal 1: filename label ─────────────────────────────────────────
        if raw_label and not _uuid_like(raw_label):
            mapped = _label_to_type(raw_label)
            if mapped:
                return ClassificationResult(
                    doc_id=doc_id,
                    source_path=source_path,
                    page_number=page_number,
                    predicted_type=mapped,
                    confidence=FILENAME_LABEL_CONFIDENCE,
                    signal="filename",
                    raw_label=raw_label,
                )

        # ── Signal 2: content keywords ───────────────────────────────────────
        content_type, content_conf = _classify_by_content(text)
        if content_type and content_conf >= 0.25:
            return ClassificationResult(
                doc_id=doc_id,
                source_path=source_path,
                page_number=page_number,
                predicted_type=content_type,
                confidence=content_conf,
                signal="content",
                raw_label=raw_label,
            )

        # ── Fallback: OTHER ──────────────────────────────────────────────────
        return ClassificationResult(
            doc_id=doc_id,
            source_path=source_path,
            page_number=page_number,
            predicted_type=OTHER,
            confidence=UNKNOWN_DOC_CONFIDENCE,
            signal="fallback",
            raw_label=raw_label,
        )

    def classify_claim(self, pages) -> List[ClassificationResult]:
        """Classify all pages for a claim, returning one result per page."""
        results = []
        for page in pages:
            result = self.classify_page(
                doc_id=page.doc_id,
                source_path=page.source_path,
                page_number=page.page_number,
                text=page.text,
            )
            results.append(result)
        return results

    def summarise_claim_docs(
        self, results: List[ClassificationResult]
    ) -> Dict[str, List[ClassificationResult]]:
        """
        Group classification results by {doc_id} (one file = multiple pages).
        For each file, pick the type with highest confidence across pages.
        Returns dict: doc_id → [best ClassificationResult per file].
        """
        from collections import defaultdict
        by_doc: Dict[str, List[ClassificationResult]] = defaultdict(list)
        for r in results:
            by_doc[r.doc_id].append(r)

        summary: Dict[str, ClassificationResult] = {}
        for doc_id, rlist in by_doc.items():
            best = max(rlist, key=lambda x: x.confidence)
            summary[doc_id] = best
        return summary
