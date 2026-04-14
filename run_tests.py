"""
OCR Test Runner - Processes all test PDFs through Gemma 4 and produces a summary report.

Runs each PDF through the GemmaOcrTest tool, captures OCR output with page boundaries,
and generates a results summary showing accuracy metrics and extracted text.
"""

import os
import sys
import subprocess
import time
import json
from datetime import datetime
from pathlib import Path

TEST_PDF_DIR = "test-pdfs"
RESULTS_DIR = "test-results"
GEMMA_EXE = os.path.join("GemmaOcrTest", "bin", "Debug", "net8.0", "GemmaOcrTest.exe")


def get_pdf_page_count(pdf_path):
    """Get page count using PyMuPDF."""
    try:
        import fitz
        doc = fitz.open(pdf_path)
        count = doc.page_count
        doc.close()
        return count
    except Exception:
        return "?"


def run_ocr(pdf_path):
    """Run GemmaOcrTest on a PDF and capture output."""
    start = time.time()
    try:
        result = subprocess.run(
            [GEMMA_EXE, pdf_path],
            capture_output=True, text=True, timeout=600
        )
        elapsed = time.time() - start
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "elapsed_seconds": round(elapsed, 1),
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": "TIMEOUT after 600s",
            "exit_code": -1,
            "elapsed_seconds": 600,
        }
    except FileNotFoundError:
        return {
            "stdout": "",
            "stderr": f"Executable not found: {GEMMA_EXE}",
            "exit_code": -1,
            "elapsed_seconds": 0,
        }


def parse_page_boundaries(stdout):
    """Parse page boundary markers from OCR output."""
    pages = {}
    current_page = None
    current_text = []

    for line in stdout.split("\n"):
        stripped = line.strip()
        if stripped.startswith("=== PAGE ") and stripped.endswith("==="):
            if current_page is not None:
                pages[current_page] = "\n".join(current_text).strip()
            current_page = stripped.replace("=== PAGE ", "").replace(" ===", "")
            current_text = []
        else:
            current_text.append(line)

    # Handle last page or single-page (no markers)
    if current_page is not None:
        pages[current_page] = "\n".join(current_text).strip()
    elif stdout.strip():
        pages["1"] = stdout.strip()

    return pages


def generate_report(results):
    """Generate a markdown summary report."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report_path = os.path.join(RESULTS_DIR, f"ocr_test_report_{timestamp}.md")

    lines = []
    lines.append(f"# Gemma 4 OCR Test Report")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Total PDFs tested:** {len(results)}")
    lines.append("")

    # Summary table
    total_pages = 0
    total_time = 0
    passed = 0
    failed = 0

    lines.append("## Summary")
    lines.append("")
    lines.append("| PDF File | Pages | Pages Detected | Time (s) | Status |")
    lines.append("|----------|-------|----------------|----------|--------|")

    for r in results:
        total_pages += r["actual_pages"] if isinstance(r["actual_pages"], int) else 0
        total_time += r["elapsed_seconds"]
        detected = len(r["extracted_pages"])
        status = "PASS" if r["exit_code"] == 0 and detected > 0 else "FAIL"
        if status == "PASS":
            passed += 1
        else:
            failed += 1

        page_match = ""
        if isinstance(r["actual_pages"], int):
            if detected == r["actual_pages"]:
                page_match = f"{detected}/{r['actual_pages']}"
            else:
                page_match = f"**{detected}/{r['actual_pages']}**"
        else:
            page_match = f"{detected}/?"

        lines.append(f"| {r['filename']} | {r['actual_pages']} | {page_match} | {r['elapsed_seconds']} | {status} |")

    lines.append("")
    lines.append(f"**Passed:** {passed} | **Failed:** {failed} | **Total time:** {round(total_time, 1)}s")
    lines.append("")

    # Multi-page boundary detection summary
    multipage_results = [r for r in results if isinstance(r["actual_pages"], int) and r["actual_pages"] > 1]
    if multipage_results:
        lines.append("## Multi-Page Boundary Detection")
        lines.append("")
        for r in multipage_results:
            detected = len(r["extracted_pages"])
            lines.append(f"### {r['filename']} ({r['actual_pages']} pages)")
            if detected == r["actual_pages"]:
                lines.append(f"All {r['actual_pages']} page boundaries correctly detected.")
            else:
                lines.append(f"**Mismatch:** Expected {r['actual_pages']} pages, detected {detected}.")
            lines.append("")
            for page_num, text in sorted(r["extracted_pages"].items()):
                preview = text[:200].replace("\n", " ") + ("..." if len(text) > 200 else "")
                lines.append(f"- **Page {page_num}**: {len(text)} chars — `{preview}`")
            lines.append("")

    # Detailed results for each PDF
    lines.append("## Detailed OCR Output")
    lines.append("")
    for r in results:
        lines.append(f"### {r['filename']}")
        lines.append(f"- **Pages:** {r['actual_pages']}")
        lines.append(f"- **Time:** {r['elapsed_seconds']}s")
        lines.append(f"- **Exit code:** {r['exit_code']}")
        if r["stderr_info"]:
            lines.append(f"- **Stderr:** `{r['stderr_info'][:200]}`")
        lines.append("")

        if r["extracted_pages"]:
            for page_num, text in sorted(r["extracted_pages"].items()):
                if len(r["extracted_pages"]) > 1:
                    lines.append(f"#### Page {page_num}")
                lines.append("```")
                lines.append(text[:2000] if len(text) > 2000 else text)
                if len(text) > 2000:
                    lines.append(f"\n... (truncated, {len(text)} chars total)")
                lines.append("```")
                lines.append("")
        else:
            lines.append("*No text extracted.*")
            lines.append("")

        lines.append("---")
        lines.append("")

    report_content = "\n".join(lines)

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    return report_path, report_content


def main():
    if not os.path.exists(GEMMA_EXE):
        print(f"ERROR: {GEMMA_EXE} not found. Build the project first:")
        print(f"  cd GemmaOcrTest && dotnet build")
        sys.exit(1)

    if not os.path.isdir(TEST_PDF_DIR):
        print(f"ERROR: {TEST_PDF_DIR}/ not found. Run generate_medical_pdfs.py first.")
        sys.exit(1)

    pdfs = sorted([f for f in os.listdir(TEST_PDF_DIR) if f.endswith(".pdf")])
    if not pdfs:
        print("No PDFs found in test-pdfs/")
        sys.exit(1)

    print(f"Found {len(pdfs)} test PDFs. Starting OCR processing...\n")

    results = []
    for i, pdf_name in enumerate(pdfs, 1):
        pdf_path = os.path.join(TEST_PDF_DIR, pdf_name)
        actual_pages = get_pdf_page_count(pdf_path)
        print(f"[{i}/{len(pdfs)}] {pdf_name} ({actual_pages} page(s))...", end=" ", flush=True)

        ocr = run_ocr(pdf_path)
        extracted_pages = parse_page_boundaries(ocr["stdout"])

        print(f"done in {ocr['elapsed_seconds']}s — {len(extracted_pages)} page(s) extracted")

        results.append({
            "filename": pdf_name,
            "actual_pages": actual_pages,
            "extracted_pages": extracted_pages,
            "exit_code": ocr["exit_code"],
            "elapsed_seconds": ocr["elapsed_seconds"],
            "stderr_info": ocr["stderr"].strip(),
            "raw_stdout": ocr["stdout"],
        })

    report_path, report_content = generate_report(results)

    # Print summary to console
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    passed = sum(1 for r in results if r["exit_code"] == 0 and len(r["extracted_pages"]) > 0)
    failed = len(results) - passed
    total_time = sum(r["elapsed_seconds"] for r in results)
    print(f"  Passed:     {passed}/{len(results)}")
    print(f"  Failed:     {failed}/{len(results)}")
    print(f"  Total time: {round(total_time, 1)}s")
    print()

    # Page boundary detection
    multipage = [r for r in results if isinstance(r["actual_pages"], int) and r["actual_pages"] > 1]
    if multipage:
        print("MULTI-PAGE BOUNDARY DETECTION:")
        for r in multipage:
            detected = len(r["extracted_pages"])
            match = "OK" if detected == r["actual_pages"] else "MISMATCH"
            print(f"  {r['filename']}: {detected}/{r['actual_pages']} pages [{match}]")
        print()

    # Brief text preview for each
    print("EXTRACTED TEXT PREVIEW:")
    for r in results:
        for page_num, text in sorted(r["extracted_pages"].items()):
            label = f"{r['filename']}"
            if len(r["extracted_pages"]) > 1:
                label += f" p{page_num}"
            preview = text[:120].replace("\n", " ")
            print(f"  {label}: {preview}...")
    print()

    print(f"Full report saved to: {report_path}")


if __name__ == "__main__":
    main()
