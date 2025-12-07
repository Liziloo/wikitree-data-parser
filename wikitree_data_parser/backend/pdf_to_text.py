import sys
import re
from pathlib import Path

import fitz  # PyMuPDF

# Matches headers like "Maine 23", "Pennsylvania 414"
HEADER_PATTERN = re.compile(r"^[A-Z][a-z]+ \d+$")


# -------------------------------------------
# PRINTED PAGE → PDF PAGE RESOLUTION
# -------------------------------------------

# For now we only hard-code Pennsylvania from the DAR Forgotten Patriots PDF.
# You can extend this map later with additional states as needed.
#
# Values are tuned to the specific DAR Forgotten Patriots PDF:
# - pdf_start:     1-based PDF page number where that chapter's pages begin
# - printed_start: printed page number shown on that page in the book header
#
# Confirmed from the file:
#   A header line "Pennsylvania 414" appears on what the viewer calls page 245.
#   So: pdf_start = 245, printed_start = 414.
STATE_PAGE_MAP = {
    "Pennsylvania": {
        "pdf_start": 245,
        "printed_start": 414,
    },
    # Add other states here once you determine their mapping, e.g.:
    # "Maine": {"pdf_start": XXX, "printed_start": YYY},
    # "New Jersey": {"pdf_start": AAA, "printed_start": BBB},
}


def resolve_printed_page(state: str, printed_page: int) -> int:
    """
    Given a state name and a printed page number, return the corresponding
    *PDF viewer* page number (1-based) for this DAR Forgotten Patriots PDF.

    Raises ValueError if the state is unknown or the computed page is invalid.
    """
    if printed_page <= 0:
        raise ValueError("Printed page number must be positive.")

    st = state.strip().title()
    if st not in STATE_PAGE_MAP:
        raise ValueError(
            f"No printed→PDF page mapping exists for state '{state}'. "
            "You can add one in STATE_PAGE_MAP in wikitree_data_parser/backend/pdf_to_text.py."
        )

    meta = STATE_PAGE_MAP[st]
    pdf_start = meta["pdf_start"]
    printed_start = meta["printed_start"]

    # Translate the printed page into a PDF page.
    offset = printed_page - printed_start
    pdf_page = pdf_start + offset

    if pdf_page < 1:
        raise ValueError(
            f"Computed PDF page {pdf_page} is invalid. Check the printed page input."
        )

    return pdf_page


def extract_text(
    pdf_path: Path,
    pages: str | None = None,
    remove_headers: bool = True,
    merge_hyphens: bool = True,
) -> str:
    """
    Extract text from a PDF, optionally restricted to specific 1-based pages.

    - `pages` is a string like "36-43" or "36,38,40-41".
    - Removes simple headers like "Maine 23" or "Pennsylvania 414".
    - Merges hyphenated line breaks by default.
    """
    doc = fitz.open(pdf_path)
    page_indices: list[int]

    if pages:
        indices: list[int] = []
        for part in pages.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                start, end = part.split("-", 1)
                start = int(start)
                end = int(end)
                for p in range(start, end + 1):
                    indices.append(p - 1)  # convert 1-based to 0-based
            else:
                indices.append(int(part) - 1)
        # Filter out-of-range pages defensively
        page_indices = [i for i in indices if 0 <= i < len(doc)]
    else:
        page_indices = list(range(len(doc)))

    lines: list[str] = []
    for i in page_indices:
        text = doc.load_page(i).get_text("text")
        for raw_line in text.splitlines():
            line = raw_line.rstrip()
            if not line:
                continue
            if remove_headers and HEADER_PATTERN.match(line.strip()):
                continue
            lines.append(line)

    full_text = "\n".join(lines)

    if merge_hyphens:
        # Merge words split at line breaks (e.g. "Passamaquod-\ndy" -> "Passamaquoddy")
        full_text = re.sub(r"-\n(\S)", r"\1", full_text)
        # Normalize multiple blank lines
        full_text = re.sub(r"\n+", "\n", full_text)

    return full_text


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m wikitree_data_parser.backend.pdf_to_text input.pdf [pages]")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    pages = sys.argv[2] if len(sys.argv) >= 3 else None

    text = extract_text(pdf_path, pages=pages)
    sys.stdout.write(text)


if __name__ == "__main__":
    main()
