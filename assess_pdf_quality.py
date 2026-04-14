"""
assess_pdf_quality.py

Quantitative quality assessment for incoming PDFs before routing.

Metrics computed per page (no reference image required):
  - source_dpi        : DPI read from embedded image XObject metadata
  - laplacian_variance: Sharpness. Low variance = blurry or noisy scan.
  - noise_sigma       : Estimated Gaussian noise std dev in background regions.
  - gradient_mean     : Mean edge strength (Sobel). Low = soft/degraded text edges.
  - brisque_score     : Holistic blind quality score (0-100, lower = better).
                        Requires `pip install pyiqa`. Gracefully omitted if unavailable.

Routing rule (matches MRO decision):
  - source_dpi < 200                → route_to_azure = True
  - laplacian_variance < BLUR_THRESH  → route_to_azure = True  (blurry scan)
  - noise_sigma > NOISE_THRESH        → route_to_azure = True  (high noise)
  - brisque_score > BRISQUE_THRESH    → route_to_azure = True  (poor holistic quality)

Usage:
    python assess_pdf_quality.py test-pdfs/discharge_summary_01.pdf
    python assess_pdf_quality.py test-pdfs/  # assess all PDFs in a directory
"""

import os
import sys
import json
import tempfile
from dataclasses import dataclass, field, asdict
from typing import Optional

import fitz  # PyMuPDF
import cv2
import numpy as np

# ── Routing thresholds ─────────────────────────────────────────────────────────
DPI_THRESHOLD = 200          # Source DPI below this → Azure
BLUR_THRESHOLD = 80.0        # Laplacian variance below this → Azure
NOISE_THRESHOLD = 6.0        # Background noise sigma above this → Azure
BRISQUE_THRESHOLD = 50.0     # BRISQUE score above this → Azure (lower = better)

# Resolution used when rasterizing pages for metric computation.
# 150 DPI is sufficient for IQA; avoids the cost of full-res renders.
ASSESSMENT_DPI = 150

# ── Optional BRISQUE via pyiqa ─────────────────────────────────────────────────
try:
    import pyiqa
    _brisque_model = pyiqa.create_metric("brisque", as_loss=False)
    BRISQUE_AVAILABLE = True
except ImportError:
    BRISQUE_AVAILABLE = False


@dataclass
class PageQualityMetrics:
    page_number: int                        # 0-indexed
    laplacian_variance: float               # Higher = sharper
    noise_sigma: float                      # Higher = noisier background
    gradient_mean: float                    # Higher = stronger text edges
    brisque_score: Optional[float]          # None if pyiqa not installed
    is_low_quality: bool                    # True if any metric trips a threshold


@dataclass
class PdfQualityReport:
    pdf_path: str
    page_count: int
    source_dpi: Optional[float]             # Median DPI of embedded images; None = vector PDF
    pages: list[PageQualityMetrics] = field(default_factory=list)
    route_to_azure: bool = False
    reasons: list[str] = field(default_factory=list)


# ── DPI extraction ─────────────────────────────────────────────────────────────

def get_source_dpi(pdf_path: str) -> Optional[float]:
    """
    Read the median DPI of embedded raster image XObjects across all pages.
    Returns None for purely vector PDFs (no embedded images).

    Note: This reads the DPI stamp on embedded images, which may differ from
    the page coordinate system's implied resolution. Gate routing logic on
    this value — not on the render DPI used downstream.
    """
    doc = fitz.open(pdf_path)
    dpis: list[float] = []
    for page in doc:
        for info in page.get_image_info(hashes=False):
            xres = info.get("xres", 0)
            yres = info.get("yres", 0)
            if xres > 0 and yres > 0:
                dpis.append((xres + yres) / 2.0)
    doc.close()
    if not dpis:
        return None
    return float(np.median(dpis))


# ── Per-page metric computation ────────────────────────────────────────────────

def _laplacian_variance(gray: np.ndarray) -> float:
    """
    Variance of the Laplacian — the standard focus/sharpness measure.
    Sharp images have high variance (strong, well-defined edges).
    Blurry or noisy scans produce low variance.
    """
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    return float(lap.var())


def _noise_sigma(gray: np.ndarray) -> float:
    """
    Estimate Gaussian noise std dev by diffing the image against a Gaussian
    blur and measuring residual variance in background (near-white) regions.
    Background pixels are reliable because they should be uniform white;
    any deviation is noise.
    """
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    residual = gray.astype(np.float32) - blurred.astype(np.float32)
    background = gray > 210          # near-white pixels = background
    if background.sum() < 200:
        background = np.ones_like(gray, dtype=bool)
    return float(np.std(residual[background]))


def _gradient_mean(gray: np.ndarray) -> float:
    """
    Mean gradient magnitude via Sobel operator.
    Strong, sharp text edges produce high gradient magnitude.
    Blurry or faded scans produce low gradient magnitude.
    """
    gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    magnitude = np.sqrt(gx ** 2 + gy ** 2)
    return float(magnitude.mean())


def _brisque_score(img_bgr: np.ndarray) -> Optional[float]:
    """
    BRISQUE: Blind/Referenceless Image Spatial Quality Evaluator.
    Scores based on how much the pixel intensity distribution deviates
    from a natural scene Gaussian. Lower = better quality.
    Returns None if pyiqa is not installed.
    """
    if not BRISQUE_AVAILABLE:
        return None
    try:
        import torch
        rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        tensor = torch.from_numpy(rgb).permute(2, 0, 1).unsqueeze(0).float() / 255.0
        score = _brisque_model(tensor)
        return float(score.item())
    except Exception:
        return None


def assess_page(img_bgr: np.ndarray, page_number: int) -> PageQualityMetrics:
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    lv = _laplacian_variance(gray)
    ns = _noise_sigma(gray)
    gm = _gradient_mean(gray)
    bq = _brisque_score(img_bgr)

    low_quality = (
        lv < BLUR_THRESHOLD
        or ns > NOISE_THRESHOLD
        or (bq is not None and bq > BRISQUE_THRESHOLD)
    )

    return PageQualityMetrics(
        page_number=page_number,
        laplacian_variance=round(lv, 3),
        noise_sigma=round(ns, 4),
        gradient_mean=round(gm, 3),
        brisque_score=round(bq, 2) if bq is not None else None,
        is_low_quality=low_quality,
    )


# ── PDF-level assessment ───────────────────────────────────────────────────────

def assess_pdf(pdf_path: str) -> PdfQualityReport:
    """
    Assess a PDF file and return a PdfQualityReport with per-page metrics
    and a top-level routing recommendation.
    """
    source_dpi = get_source_dpi(pdf_path)
    doc = fitz.open(pdf_path)
    page_count = doc.page_count

    report = PdfQualityReport(
        pdf_path=pdf_path,
        page_count=page_count,
        source_dpi=round(source_dpi, 1) if source_dpi is not None else None,
    )

    # DPI gate — check before rasterizing pages
    if source_dpi is not None and source_dpi < DPI_THRESHOLD:
        report.route_to_azure = True
        report.reasons.append(
            f"source_dpi {source_dpi:.1f} < threshold {DPI_THRESHOLD}"
        )

    mat = fitz.Matrix(ASSESSMENT_DPI / 72, ASSESSMENT_DPI / 72)

    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, 3
        )
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

        metrics = assess_page(img_bgr, page_number=i)
        report.pages.append(metrics)

        # Noise sigma is only a meaningful signal for raster/scanned PDFs.
        # Vector PDFs rasterized to images carry intrinsic anti-aliasing variance
        # that is not indicative of source quality — skip the noise gate for them.
        is_raster = source_dpi is not None
        noise_triggered = is_raster and metrics.noise_sigma > NOISE_THRESHOLD

        page_low_quality = (
            metrics.laplacian_variance < BLUR_THRESHOLD
            or noise_triggered
            or (metrics.brisque_score is not None and metrics.brisque_score > BRISQUE_THRESHOLD)
        )
        metrics.is_low_quality = page_low_quality

        if page_low_quality and not report.route_to_azure:
            report.route_to_azure = True

        if metrics.laplacian_variance < BLUR_THRESHOLD:
            reason = f"page {i}: laplacian_variance {metrics.laplacian_variance:.2f} < {BLUR_THRESHOLD} (blurry)"
            if reason not in report.reasons:
                report.reasons.append(reason)

        if noise_triggered:
            reason = f"page {i}: noise_sigma {metrics.noise_sigma:.4f} > {NOISE_THRESHOLD} (noisy scan)"
            if reason not in report.reasons:
                report.reasons.append(reason)

        if metrics.brisque_score is not None and metrics.brisque_score > BRISQUE_THRESHOLD:
            reason = f"page {i}: brisque {metrics.brisque_score:.2f} > {BRISQUE_THRESHOLD} (poor quality)"
            if reason not in report.reasons:
                report.reasons.append(reason)

    doc.close()

    if not report.route_to_azure:
        report.reasons.append("All metrics within acceptable thresholds — Gemini Vision path.")

    return report


# ── CLI ────────────────────────────────────────────────────────────────────────

def _print_report(report: PdfQualityReport) -> None:
    print(f"\n{'='*60}")
    print(f"  {os.path.basename(report.pdf_path)}")
    print(f"{'='*60}")
    print(f"  Pages       : {report.page_count}")
    print(f"  Source DPI  : {report.source_dpi if report.source_dpi else 'N/A (vector PDF)'}")
    print(f"  Route       : {'→ AZURE OCR' if report.route_to_azure else '→ GEMINI VISION'}")
    for r in report.reasons:
        print(f"    • {r}")
    print()
    print(f"  {'Page':<6} {'Laplacian':>12} {'Noise σ':>10} {'Gradient':>10} {'BRISQUE':>10} {'LowQ?':>6}")
    print(f"  {'-'*6} {'-'*12} {'-'*10} {'-'*10} {'-'*10} {'-'*6}")
    for p in report.pages:
        bq = f"{p.brisque_score:.2f}" if p.brisque_score is not None else "  N/A"
        flag = "YES" if p.is_low_quality else ""
        print(
            f"  {p.page_number:<6} {p.laplacian_variance:>12.2f} {p.noise_sigma:>10.4f} "
            f"{p.gradient_mean:>10.2f} {bq:>10} {flag:>6}"
        )
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python assess_pdf_quality.py <pdf_path_or_directory>")
        sys.exit(1)

    target = sys.argv[1]

    if os.path.isdir(target):
        pdf_files = sorted(
            os.path.join(target, f)
            for f in os.listdir(target)
            if f.lower().endswith(".pdf")
        )
    else:
        pdf_files = [target]

    if not pdf_files:
        print("No PDF files found.")
        sys.exit(1)

    for pdf_path in pdf_files:
        report = assess_pdf(pdf_path)
        _print_report(report)

    if "--json" in sys.argv:
        all_reports = [asdict(assess_pdf(p)) for p in pdf_files]
        print(json.dumps(all_reports, indent=2))
