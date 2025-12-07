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

PRINTED_TO_PDF_OFFSET = 16

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

        page_num = int(page_str) - 1

        # ----------------------------
        # Resolve printed → PDF mapping
        # ----------------------------
        if mode == "printed":
            pdf_page_1 = page_num + PRINTED_TO_PDF_OFFSET
        else:
            pdf_page_1 = page_num

        # ----------------------------
        # Save temp PDF and extract page
        # ----------------------------
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            temp_path = tmp.name
            pdf_file.save(temp_path)

        try:
            extracted_text = extract_text_from_pdf(temp_path, pdf_page_1)
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

