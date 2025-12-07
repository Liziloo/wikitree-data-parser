# backend/routes_process.py

from flask import Blueprint, request, render_template
from backend.parsers.original_parser import process_text as parse_original
from backend.parsers.virginia_parser import parse_record as parse_virginia
import csv
import io

process_bp = Blueprint("process_bp", __name__)

@process_bp.route("/process", methods=["POST"])
def process_records():
    raw_text = request.form.get("raw_text", "")
    parser_choice = request.form.get("parser", "original")
    delimiter_choice = request.form.get("delimiter", "csv")

    if parser_choice == "original":
        rows = parse_original(raw_text, filename="manual_input", log_list=[])
    elif parser_choice == "virginia":
        rows = []
        for line in raw_text.splitlines():
            parsed = parse_virginia(line)
            if parsed:
                rows.append(parsed)
    else:
        rows = []

    out = io.StringIO()
    delim = "," if delimiter_choice == "csv" else "|"
    writer = csv.writer(out, delimiter=delim)

    for row in rows:
        writer.writerow(row)

    return render_template(
        "index.html",
        raw_text=raw_text,
        output=out.getvalue(),
        parser=parser_choice,
        delimiter=delimiter_choice
    )
