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

def parse_page_expression(expr: str) -> list[int]:
    """
    Parse user input like:
        '414'
        '414-416'
        '414,420-421'
    And return a sorted list of unique integers.
    """
    pages = set()
    parts = [p.strip() for p in expr.split(",") if p.strip()]

    for part in parts:
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            if start_s.isdigit() and end_s.isdigit():
                start, end = int(start_s), int(end_s)
                if start <= end:
                    pages.update(range(start, end + 1))
                else:
                    raise ValueError(f"Invalid range: {part}")
            else:
                raise ValueError(f"Invalid range expression: {part}")
        else:
            if part.isdigit():
                pages.add(int(part))
            else:
                raise ValueError(f"Invalid page number: {part}")

    if not pages:
        raise ValueError("No valid pages found.")

    return sorted(pages)


# ------------------------------------------------------------
# Route: /extract_pdf
# ------------------------------------------------------------

def parse_page_range(s: str):
    """
    Accept '10', '10-12', '10 – 12', '10 - 12'
    Returns (start, end)
    """
    s = s.strip().replace("–", "-")
    if "-" not in s:
        page = int(s)
        if page < 1:
            raise ValueError("Page must be >= 1")
        return page, page

    parts = s.split("-")
    if len(parts) != 2:
        raise ValueError("Invalid page range format")

    start = int(parts[0].strip())
    end = int(parts[1].strip())

    if start < 1 or end < 1 or end < start:
        raise ValueError("Invalid page range boundaries")

    return start, end


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

        try:
            printed_start, printed_end = parse_page_range(page_str)
        except Exception as e:
            return jsonify({"error": f"Invalid page or range: {e}"}), 400


        # ----------------------------
        # Resolve printed → PDF mapping
        # ----------------------------
        if mode == "printed":
            pdf_start = printed_start + PRINTED_TO_PDF_OFFSET
            pdf_end   = printed_end   + PRINTED_TO_PDF_OFFSET
        else:
            pdf_start = printed_start
            pdf_end   = printed_end

        # convert to zero-based
        pdf_start_idx = pdf_start - 1
        pdf_end_idx   = pdf_end - 1


        # ----------------------------
        # Save temp PDF and extract page
        # ----------------------------
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            temp_path = tmp.name
            pdf_file.save(temp_path)

        try:
            extracted_text = extract_text_from_pdf(temp_path, pdf_start_idx, pdf_end_idx)

        finally:
            os.remove(temp_path)

        # ----------------------------
        # Run the parser (returns list of lists)
        # ----------------------------
        virginia_mode = request.form.get("virginia_mode") == "on"
        parsed_rows = run_parser(extracted_text, virginia_mode)

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
        if printed_start == printed_end:
            page_label = f"page_{printed_start}"
        else:
            page_label = f"pages_{printed_start}-{printed_end}"

        filename = f"{(state or 'parsed')}_{page_label}.csv"

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

