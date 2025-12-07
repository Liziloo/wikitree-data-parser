import tempfile
import os
from flask import Blueprint, request, jsonify, current_app
from werkzeug.datastructures import FileStorage

from .pdf_to_text import extract_text_from_pdf

bp = Blueprint("pdf", __name__)

# Massachusetts offset: printed_page + 16 = pdf_page
MASSACHUSETTS_OFFSET = 16


@bp.route("/extract_pdf", methods=["POST"])
def extract_pdf():
    """
    Accepts a PDF upload + page selector and returns the extracted text.
    Request fields:
        - pdf_file: PDF upload
        - mode: "pdf" or "printed"
        - page: integer page number (printed or pdf)
    """
    try:
        # ----------------------------------------------------
        # Validate file upload
        # ----------------------------------------------------
        if "pdf_file" not in request.files:
            return jsonify({"error": "No PDF file uploaded"}), 400

        file: FileStorage = request.files["pdf_file"]

        if file.filename == "":
            return jsonify({"error": "Uploaded file has no filename"}), 400

        # ----------------------------------------------------
        # Extract user parameters
        # ----------------------------------------------------
        mode = request.form.get("mode", "pdf").strip().lower()
        page_str = request.form.get("page", "").strip()

        if not page_str.isdigit():
            return jsonify({"error": "Page must be a number"}), 400

        page_num = int(page_str)

        # ----------------------------------------------------
        # Apply printed → PDF page conversion (Massachusetts only)
        # ----------------------------------------------------
        if mode == "printed":
            pdf_page = page_num + MASSACHUSETTS_OFFSET
        else:
            pdf_page = page_num

        # PDF pages in PyMuPDF are 0-indexed, users give 1-indexed
        pdf_page -= 1

        if pdf_page < 0:
            return jsonify({"error": "Page numbers must be ≥ 1"}), 400

        # ----------------------------------------------------
        # Save uploaded file to a temporary file
        # ----------------------------------------------------
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            file.save(tmp.name)
            temp_path = tmp.name

        # ----------------------------------------------------
        # Extract text from the PDF page
        # ----------------------------------------------------
        try:
            text = extract_text_from_pdf(temp_path, pdf_page, pdf_page)
        finally:
            # Always clean up the temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)

        # ----------------------------------------------------
        # Success
        # ----------------------------------------------------
        return jsonify({"text": text})

    except Exception as e:
        current_app.logger.exception("PDF extraction failed")
        return jsonify({"error": str(e)}), 500
