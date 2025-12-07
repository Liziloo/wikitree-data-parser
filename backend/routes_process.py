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

def run_parser(text: str, state: str):
    """
    Dispatch to the appropriate parser based on the selected state.

    `state` is a loose hint (e.g. "virginia", "massachusetts", etc.).
    For now we special-case Virginia; everything else uses the general parser.
    """
    state_norm = (state or "").strip().lower()

    if state_norm == "virginia":
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
      - state: optional hint like "virginia", "massachusetts", etc.

    Returns JSON with parsed rows.
    """
    raw_text = (request.form.get("raw_text") or "").strip()
    state = (request.form.get("state") or "").strip()

    if not raw_text:
        return jsonify({"error": "No text provided."}), 400

    try:
        rows = run_parser(raw_text, state)
    except Exception as e:
        return jsonify({"error": f"Parser error: {e}"}), 500

    return jsonify({"state": state, "results": rows})
