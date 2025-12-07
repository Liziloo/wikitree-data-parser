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
    "Maine": {"printed_start": None, "pdf_start": None},
    "New Hampshire": {"printed_start": None, "pdf_start": None},
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
    Handle PDF upload + page selection and return *parsed rows*.
    
    Form fields:
      - pdf_file: uploaded PDF
      - mode: "pdf" or "printed"
      - page: page number
      - state: which parser to use (e.g. "massachusetts", "virginia", etc.)
    """
    try:
        # ----------------------------------------
        # Validate upload
        # ----------------------------------------
        if "pdf_file" not in request.files:
            return jsonify({"error": "No PDF file uploaded."}), 400

        pdf_file = request.files["pdf_file"]
        if not pdf_file or pdf_file.filename == "":
            return jsonify({"error": "Uploaded PDF file is invalid."}), 400

        # ----------------------------------------
        # Get form fields
        # ----------------------------------------
        mode = (request.form.get("mode") or "pdf").strip().lower()
        page_str = (request.form.get("page") or "").strip()
        state = (request.form.get("state") or "").strip().lower()

        if not page_str.isdigit():
            return jsonify({"error": "Page must be a positive integer."}), 400

        page_num = int(page_str)
        if page_num < 1:
            return jsonify({"error": "Page must be ≥ 1."}), 400

        # ----------------------------------------
        # Convert printed → PDF if needed
        # ----------------------------------------
        if mode == "printed":
            try:
                pdf_page_1_based = resolve_pdf_page(page_num)
            except ValueError as ve:
                return jsonify({"error": str(ve)}), 400
        else:
            pdf_page_1_based = page_num

        pdf_page_index = pdf_page_1_based - 1

        # ----------------------------------------
        # Save PDF to temp file
        # ----------------------------------------
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            temp_path = tmp.name
            pdf_file.save(temp_path)

        # ----------------------------------------
        # Extract text from that ONE page
        # ----------------------------------------
        try:
            extracted = extract_text_from_pdf(temp_path, pdf_page_index, pdf_page_index)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

        if not extracted.strip():
            return jsonify({"error": "The selected page contains no text."}), 400

        # ----------------------------------------
        # RUN THE TEXT THROUGH YOUR PARSER
        # ----------------------------------------
        try:
            parsed_rows = run_parser(extracted, state)
        except Exception as e:
            current_app.logger.exception("Parser crashed")
            return jsonify({"error": f"Parser error: {e}"}), 500

        # ----------------------------------------
        # Return parsed rows
        # ----------------------------------------
        return jsonify({
            "page_requested": page_num,
            "pdf_page_used": pdf_page_1_based,
            "state": state,
            "results": parsed_rows
        })

    except Exception as e:
        current_app.logger.exception("Unexpected PDF extraction failure")
        return jsonify({"error": str(e)}), 500
