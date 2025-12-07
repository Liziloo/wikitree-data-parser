"""
pdf_to_text.py
Extract plain text from a PDF so it can be fed into the parser backend.
"""

import fitz  # PyMuPDF
from pathlib import Path


import fitz  # PyMuPDF

def extract_text_from_pdf(pdf_path, start_page, end_page=None):
    """
    Extract text from a PDF.

    Accepts:
        - A single page number  (start_page=12, end_page=None)
        - A page range          (start_page=12, end_page=15)

    All page numbers are treated as *1-based* because this matches
    the behavior we have verified empirically in your environment.

    Returns a single concatenated text block.
    """

    # Normalize: if user provided only one page, treat as both start & end.
    if end_page is None:
        end_page = start_page

    # Convert to ints (request.form sends strings)
    start_page = int(start_page)
    end_page = int(end_page)

    if start_page < 1 or end_page < 1:
        raise ValueError("Page numbers must be ≥ 1.")

    if end_page < start_page:
        raise ValueError("End page cannot be before start page.")

    doc = fitz.open(pdf_path)
    num_pages = doc.page_count

    if start_page > num_pages or end_page > num_pages:
        raise ValueError(
            f"Requested page(s) outside PDF bounds. "
            f"PDF has {num_pages} total pages."
        )

    # IMPORTANT: We do *not* subtract 1. Your PyMuPDF behaves as 1-based.
    extracted = []

    for page_num in range(start_page, end_page + 1):
        page = doc.load_page(page_num)
        extracted.append(page.get_text())

    doc.close()
    return "\n".join(extracted)



if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract text from PDF pages.")
    parser.add_argument("pdf", help="Path to PDF file")
    parser.add_argument("start", type=int, help="Start page (1-indexed)")
    parser.add_argument("end", type=int, help="End page (1-indexed)")
    args = parser.parse_args()

    print(extract_text_from_pdf(args.pdf, args.start, args.end))
