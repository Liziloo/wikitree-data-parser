import os
import tempfile
from typing import Dict, Any

from flask import Blueprint, request, jsonify, current_app

from .pdf_to_text import extract_text_from_pdf
from .routes_process import run_parser   # <<< NEW: use your normal text parser

# ------------------------------------------------------------
# Blueprint
# ------------------------------------------------------------

pdf_bp = Blueprint("pdf_bp", __name__)

# ------------------------------------------------------------
# PRINTED → PDF PAGE MAPPING (YOU FILL THE NUMBERS)
# ------------------------------------------------------------

CHAPTER_PAGE_MAP: Dict[str, Dict[str, Any]] = {
    "Maine": {"printed_start": 9, "pdf_start": 25},
    "New Hampshire": {"printed_start": 52, "pdf_start": 68},
    "Vermont": {"printed_start": None, "pdf_start": None},
    "Massachusetts": {"printed_start": 77, "pdf_start": 93},
    "Rhode Island": {"printed_start": None, "pdf_start": None},
    "Connecticut": {"printed_start": None, "pdf_start": None},
    "New York": {"printed_start": None, "pdf_start": None},
    "New Jersey": {"printed_start": None, "pdf_start": None},
    "Pennsylvania": {"printed_start": None, "pdf_start": None},
    "Delaware": {"printed_start": None, "pdf_start": None},
    "Maryland": {"printed_start": None, "pdf_start": None},
    "Virginia": {"printed_start": None, "pdf_start": None},
    "North Carolina": {"printed_start": None, "pdf_start": None},
    "South Carolina": {"printed_start": None, "pdf_start": None},
    "Georgia": {"printed_start": None, "pdf_start": None},
    "The Old Northwest": {"printed_start": None, "pdf_start": None},
    "Miscellaneous Naval and Military Records": {
        "printed_start": None,
        "pdf_start": None,
    },
}

def resolve_pdf_page(printed_page: int) -> int:
    """
    Convert a printed page number from the book into a PDF page number,
    using CHAPTER_PAGE_MAP.
    """
    configured = [
        (name, info)
        for name, info in CHAPTER_PAGE_MAP.items()
        if info.get("printed_start") is not None and info.get("pdf_start") is not None
    ]

    if not configured:
        raise ValueError("No chapter mappings have been configured yet.")

    candidates = [
        (name, info)
        for name, info in configured
        if printed_page >= info["printed_start"]
    ]

    if not candidates:
        raise ValueError("Printed page is before the first configured chapter.")

    chapter_name, info = max(candidates, key=lambda item: item[1]["printed_start"])

    printed_start = info["printed_start"]
    pdf_start = info["pdf_start"]

    offset = pdf_start - printed_start
    return printed_page + offset


# ------------------------------------------------------------
# Route: /extract_pdf
# ------------------------------------------------------------

@pdf_bp.route("/extract_pdf", methods=["POST"])
def extract_pdf():
    """
    Extract text from a PDF page, run the parser, and return a downloadable CSV.
    """
    import csv
    from io import StringIO
    from flask import Response

    try:
        # ----------------------------------------
        # Validate PDF upload
        # ----------------------------------------
        if "pdf_file" not in request.files:
            return jsonify({"error": "No PDF uploaded"}), 400

        pdf_file = request.files["pdf_file"]

        filename = getattr(pdf_file, "filename", None)
        if not filename or not str(filename).lower().endswith(".pdf"):
            return jsonify({"error": "Invalid PDF file"}), 400



        # ----------------------------
        # Read form fields
        # ----------------------------
        mode = (request.form.get("mode") or "pdf").lower()
        state = (request.form.get("state") or "").strip()
        page_str = (request.form.get("page") or "").strip()

        if not page_str.isdigit():
            return jsonify({"error": "Page must be a positive integer"}), 400

        page_num = int(page_str)

        # ----------------------------
        # Resolve printed → PDF mapping
        # ----------------------------
        if mode == "printed":
            pdf_page_1 = resolve_pdf_page(page_num)
        else:
            pdf_page_1 = page_num

        pdf_page_idx = pdf_page_1 - 1

        # ----------------------------
        # Save temp PDF and extract page
        # ----------------------------
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            temp_path = tmp.name
            pdf_file.save(temp_path)

        try:
            extracted_text = extract_text_from_pdf(temp_path, pdf_page_idx, pdf_page_idx)
        finally:
            os.remove(temp_path)

        # ----------------------------
        # Run the parser (returns list of lists)
        # ----------------------------
        parsed_rows = run_parser(extracted_text, state)

        # ----------------------------
        # Build CSV (pipe-delimited)
        # ----------------------------
        output = StringIO()
        writer = csv.writer(output, delimiter="|", lineterminator="\n")

        for row in parsed_rows:
            writer.writerow(row)

        csv_content = output.getvalue()

        # ----------------------------
        # Build downloadable response
        # ----------------------------
        filename = f"{state or 'parsed'}_page_{page_num}.csv"
        response = Response(
            csv_content,
            mimetype="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

        return response

    except Exception as e:
        current_app.logger.exception("PDF parsing failed")
        return jsonify({"error": str(e)}), 500

