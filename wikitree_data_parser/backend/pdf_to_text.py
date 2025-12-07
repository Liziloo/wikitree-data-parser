"""
pdf_to_text.py
Extract plain text from a PDF so it can be fed into the parser backend.
"""

import fitz  # PyMuPDF
from pathlib import Path


def extract_text_from_pdf(pdf_path: str | Path, start_page: int, end_page: int) -> str:
    """
    Extract raw text from a PDF between page numbers inclusive.
    Page numbers are 1-indexed (human-friendly).
    """

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    # Open PDF
    doc = fitz.open(pdf_path)

    # Convert human page numbers → zero-based indices
    start_idx = max(0, start_page - 1)
    end_idx = min(len(doc) - 1, end_page - 1)

    if start_idx > end_idx:
        doc.close()
        raise ValueError(f"Invalid page range: {start_page}–{end_page}")

    text_chunks: list[str] = []

    for page_num in range(start_idx, end_idx + 1):
        page = doc.load_page(page_num)

        # Use str() to guarantee a literal string and silence all type checkers
        raw = str(page.get_text())

        # Skip blank or whitespace-only pages
        if raw.strip():
            text_chunks.append(raw)

    doc.close()

    # Combine pages separated by a newline
    return "\n".join(text_chunks)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract text from PDF pages.")
    parser.add_argument("pdf", help="Path to PDF file")
    parser.add_argument("start", type=int, help="Start page (1-indexed)")
    parser.add_argument("end", type=int, help="End page (1-indexed)")
    args = parser.parse_args()

    print(extract_text_from_pdf(args.pdf, args.start, args.end))
