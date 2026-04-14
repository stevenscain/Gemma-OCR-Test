"""Convert PDF pages to PNG images. Called by GemmaOcrTest."""
import sys
import fitz

pdf_path = sys.argv[1]
output_dir = sys.argv[2]

doc = fitz.open(pdf_path)
for i, page in enumerate(doc):
    pix = page.get_pixmap(dpi=200)
    pix.save(f"{output_dir}/page_{i:04d}.png")
print(doc.page_count)
doc.close()
