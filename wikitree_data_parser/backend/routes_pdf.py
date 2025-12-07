from flask import Blueprint, request, jsonify
from pathlib import Path
import fitz  # PyMuPDF
from backend.pdf_to_text import extract_text_from_pdf

pdf_bp = Blueprint("pdf_bp", __name__)


def detect_printed_page_numbering(pdf_path: Path, target_page: int) -> int:
    """
    Convert a *printed page number* the user typed into the correct
    *PDF internal page number*.

    Strategy:
    - Read first ~50 pages
    - Look for printed page headers like "New Jersey 398"
    - Build a mapping of printed → PDF pages
    """

    doc = fitz.open(pdf_path)
    max_scan = min(len(doc), 50)

    printed_to_pdf = {}

    for i in range(max_scan):
        page = doc.load_page(i)
        text = str(page.get_text())
        lines = text.splitlines()

        # Look for lines like "New Jersey 398"
        for line in lines:
            parts = line.strip().rsplit(" ", 1)

            if len(parts) == 2 and parts[1].isdigit():
                printed_to_pdf[int(parts[1])] = i

    doc.close()

    # If we found a matching printed page, return its PDF index + 1
    if target_page in printed_to_pdf:
        return printed_to_pdf[target_page] + 1

    # Otherwise assume user meant the PDF page itself
    return target_page


@pdf_bp.route("/extract_pdf", methods=["POST"])
def extract_pdf_route():
    """
    API endpoint: accepts a PDF file + start/end page numbers.
    Automatically corrects printed vs. PDF number mismatch.
    """

    if "pdf" not in request.files:
        return jsonify({"error": "No PDF uploaded"}), 400

    pdf_file = request.files["pdf"]

    # -------------------------------
    # Safely extract and validate page numbers
    # -------------------------------
    start_raw = request.form.get("startPage")
    end_raw = request.form.get("endPage")

    if start_raw is None or end_raw is None:
        return jsonify({"error": "Missing startPage or endPage"}), 400

    try:
        start_page = int(start_raw)
        end_page = int(end_raw)
    except ValueError:
        return jsonify({"error": "startPage and endPage must be integers"}), 400

    # -------------------------------
    # Save temp PDF
    # -------------------------------
    temp_path = Path("/tmp/uploaded.pdf")
    pdf_file.save(temp_path)

    # -------------------------------
    # Detect printed vs PDF page numbers
    # -------------------------------
    corrected_start = detect_printed_page_numbering(temp_path, start_page)
    corrected_end = detect_printed_page_numbering(temp_path, end_page)

    # -------------------------------
    # Extract text from the corrected page range
    # -------------------------------
    try:
        text = extract_text_from_pdf(temp_path, corrected_start, corrected_end)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "text": text,
        "correctedStart": corrected_start,
        "correctedEnd": corrected_end
    })

