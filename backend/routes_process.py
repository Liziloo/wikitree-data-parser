# backend/routes_process.py

from flask import Blueprint, request, jsonify

from .parsers.original_parser import parse_text as parse_original
from .parsers.virginia_parser import parse_text as parse_virginia

__all__ = ["process_bp", "run_parser"]  # <- helps linters/tools see it's "exported"

# ------------------------------------------------------------
# Blueprint
# ------------------------------------------------------------

process_bp = Blueprint("process_bp", __name__)


# ------------------------------------------------------------
# Core parser dispatcher
# ------------------------------------------------------------

def run_parser(text: str, virginia_mode: bool):
    """
    Dispatch to the appropriate parser based on the 'Virginia-style' flag.

    If virginia_mode is True, we use the Virginia parser (for lists with
    unnamed entries like 'AFRICAN AMERICAN MAN', 'NEGRO MAN', etc.).
    Otherwise, we use the general DAR-style parser.
    """
    if virginia_mode:
        return parse_virginia(text)

    # Default: general DAR-style parser
    return parse_original(text)


# ------------------------------------------------------------
# Optional: /process_text route for raw text input
# ------------------------------------------------------------

@process_bp.route("/process_text", methods=["POST"])
def process_text_route():
    """
    Process raw text pasted into a textarea.

    Expected form fields:
      - raw_text: the full DAR-style list text
      - virginia_mode: checkbox ('on' if checked) indicating Virginia-style data

    Returns JSON with parsed rows.
    """
    raw_text = (request.form.get("raw_text") or "").strip()
    virginia_mode = request.form.get("virginia_mode") == "on"

    if not raw_text:
        return jsonify({"error": "No text provided."}), 400

    try:
        rows = run_parser(raw_text, virginia_mode)
    except Exception as e:
        return jsonify({"error": f"Parser error: {e}"}), 500

    return jsonify({"virginia_mode": virginia_mode, "results": rows})
