#!/usr/bin/env python3
import re
import argparse
from pathlib import Path

# ============================================================
# CONFIGURATION
# ============================================================

# Phrases that stand in for a "surname" when there is no name
UNNAMED_MARKERS = [
    "AFRICAN AMERICAN MAN",
    "AFRICAN AMERICAN MEN",
    "NEGRO",
    "NEGRO MAN",
    "NEGRO MEN",
    "PUBLIC NEGRO",
    "NEGRO FELLOW",
    "NEGRO SLAVE",
    "A NEGRO",
    "SLAVE",
    "SLAVE MAN",
    "SLAVE WOMAN",
]

MARKER_PATTERN = re.compile(
    r"^(?:" + "|".join(re.escape(m) for m in UNNAMED_MARKERS) + r")\b"
)

# Looks like a code-style source (M881, APALM, VAPC:1:338, WAR25:782, etc.)
SOURCE_CODE = re.compile(r"\b[A-Z]{2,}[0-9:.\-]*\b")

# Owner / enslaver phrases
OWNER_PAT = re.compile(
    r"(?:enslaved man of|enslaved men of|slave of|slaves of|property of|"
    r"hired by|employed by|for use of)\s+[^,;()]+",
    re.IGNORECASE,
)

# Race indicators
RACE_PHRASES = [
    "african american",
    "negro",
    "black man",
    "black woman",
    "mulatto",
    "mixed descent",
]

RACE_PATTERN = re.compile(
    "(" + "|".join(re.escape(p) for p in RACE_PHRASES) + r")",
    re.IGNORECASE,
)

# Page header pattern like "Maine 23", "Virginia 509"
PAGE_HEADER_PATTERN = re.compile(r"^[A-Z][a-z]+ \d+$")


# ============================================================
# RECORD SPLITTING
# ============================================================

def is_new_record_line(stripped: str) -> bool:
    """
    Decide if this stripped line begins a new entry.

    Rules:
    - If it starts with an unnamed marker (e.g. "AFRICAN AMERICAN MAN"), it's a new record.
    - Else, if it starts with ALLCAPS token(s) followed by a comma, it's a new record.
      Example: "AARON, ..." or "ACREY/ACRE/ACRY, AMBROSE, ..."
    """

    # Skip page headers like "Virginia 509"
    if PAGE_HEADER_PATTERN.match(stripped):
        return False

    # Unnamed marker lines always start new records
    if MARKER_PATTERN.match(stripped):
        return True

    # Normal "SURNAME, ..." style lines
    # First chunk is caps/slash/hyphen/space, then a comma
    if re.match(r"^[A-Z][A-Z0-9/ '&.-]*,\s*", stripped):
        return True

    return False


def read_records_from_file(path: Path):
    """
    Read the raw lines and fuse them into logical records
    based on the is_new_record_line() rule.
    """
    with path.open("r", encoding="utf-8") as f:
        raw_lines = f.read().splitlines()

    records = []
    current = []

    for line in raw_lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Skip page headers entirely
        if PAGE_HEADER_PATTERN.match(stripped):
            continue

        if is_new_record_line(stripped):
            # Flush previous record
            if current:
                records.append(" ".join(current).strip())
            current = [stripped]
        else:
            # Continuation of the current record
            if current:
                current.append(stripped)
            else:
                # If we somehow hit a continuation before any record, just start one
                current = [stripped]

    if current:
        records.append(" ".join(current).strip())

    return records


# ============================================================
# FIELD EXTRACTION HELPERS
# ============================================================

def extract_sources(text: str):
    """
    Pull out source-like codes and return (sources_list, remaining_text).
    Each source is prefixed with 'DAR, '.
    """
    found = SOURCE_CODE.findall(text)
    cleaned = [f"DAR, {s}" for s in found]
    text = SOURCE_CODE.sub("", text)
    return cleaned, text.strip()


def extract_race(text: str):
    """
    Extract race-related phrases, return (race_string, remaining_text).
    """
    races = RACE_PATTERN.findall(text)
    if races:
        text = RACE_PATTERN.sub("", text)
        # Normalize capitalization a bit
        norm = [r.strip().capitalize() for r in races]
        return "; ".join(sorted(set(norm))), text.strip()
    return "", text


def extract_owner(text: str, is_enslaved: bool):
    """
    Extract enslaver / 'owner' phrases if is_enslaved is True.
    Returns (owner_string, remaining_text).
    """
    owners = OWNER_PAT.findall(text)
    if owners and is_enslaved:
        text = OWNER_PAT.sub("", text)
        return "; ".join(o.strip() for o in owners), text.strip()
    return "", text


def clean_notes(text: str) -> str:
    """
    Normalize whitespace and trim trailing punctuation.
    """
    text = re.sub(r"\s+", " ", text).strip(" ;,")
    return text


# ============================================================
# RECORD PARSING
# ============================================================

def parse_record(line: str):
    """
    Given a fused record line, return the 8 output columns:

    [ "", "", SURNAME, FIRST, RACE, OWNER, SOURCES, NOTES ]
    """
    original = line  # for debugging if ever needed

    # --------------------------------------------------------
    # 1. Unnamed-person entries starting with a marker phrase
    # --------------------------------------------------------
    m = MARKER_PATTERN.match(line)
    if m:
        surname = m.group(0).strip()  # literal phrase, as requested
        rest = line[len(surname):].strip()

        # Strip leading commas / spaces if present
        rest = rest.lstrip(",; ").strip()

        # Race is always African-descended for these markers
        race = "AA"

        # We assume these are enslaved unless clearly marked free
        is_enslaved = "free" not in rest.lower()

        # Owner extraction
        owner, remainder = extract_owner(rest, is_enslaved=is_enslaved)

        # Sources
        sources, remainder = extract_sources(remainder)

        # Notes = everything left
        notes = clean_notes(remainder)

        return ["", "", surname, "", race, owner, "; ".join(sources), notes]

    # --------------------------------------------------------
    # 2. Named entries: SURNAME, [FIRST,] rest…
    # --------------------------------------------------------

    # Split at the first comma
    first_comma_idx = line.find(",")
    if first_comma_idx == -1:
        # Fallback – extremely weird line, treat the whole thing as surname
        surname = line.strip()
        rest = ""
    else:
        surname = line[:first_comma_idx].strip()
        rest = line[first_comma_idx + 1 :].strip()

    # Attempt to extract first name from the very next comma-separated chunk
    first_name = ""
    parts = rest.split(",", 1)
    maybe_first = parts[0].strip()

    # FIRST NAME RULE:
    # If maybe_first is ALL CAPS and not obviously a code, treat it as first name.
    if re.fullmatch(r"[A-Z][A-Z .'-]*", maybe_first) and not SOURCE_CODE.fullmatch(
        maybe_first
    ):
        first_name = maybe_first
        rest = parts[1].strip() if len(parts) > 1 else ""
    else:
        rest = rest.strip()

    # --------------------------------------------------------
    # 3. Race extraction
    # --------------------------------------------------------
    race, rest = extract_race(rest)

    # --------------------------------------------------------
    # 4. Owner extraction
    # --------------------------------------------------------
    # Heuristic: consider enslaved if race suggests African descent
    # OR if explicit 'enslaved man of' appears in the text.
    enslaved_flag = (
        race.lower() == "aa" or "enslaved man of" in rest.lower()
    )
    owner, rest = extract_owner(rest, is_enslaved=enslaved_flag)

    # --------------------------------------------------------
    # 5. Source extraction
    # --------------------------------------------------------
    sources, rest = extract_sources(rest)

    # --------------------------------------------------------
    # 6. Notes cleanup
    # --------------------------------------------------------
    notes = clean_notes(rest)

    return ["", "", surname, first_name, race, owner, "; ".join(sources), notes]


# ============================================================
# DRIVER
# ============================================================

def process_file(infile: Path, outdir: Path, delimiter: str = "|", log=None):
    records = read_records_from_file(infile)
    outfile = outdir / (infile.stem + ".csv")  # always .csv extension

    with outfile.open("w", encoding="utf-8") as out:
        for rec in records:
            row = parse_record(rec)
            out.write(delimiter.join(row) + "\n")
            if log:
                log.write(f"Processed: {rec}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Parse Revolutionary War lists into pipe-delimited CSV."
    )
    parser.add_argument("input_path", help="Input file or directory")
    parser.add_argument("output_dir", help="Directory to write output files")
    parser.add_argument(
        "--psv",
        action="store_true",
        help="Use pipe separators but still write .csv extension",
    )

    args = parser.parse_args()

    delimiter = "|" if args.psv else ","

    inp = Path(args.input_path)
    outdir = Path(args.output_dir)
    outdir.mkdir(exist_ok=True)

    log_path = outdir / "processing.log"
    log = log_path.open("w", encoding="utf-8")

    if inp.is_file():
        process_file(inp, outdir, delimiter, log)
    else:
        for f in inp.iterdir():
            if f.is_file():
                process_file(f, outdir, delimiter, log)

    log.close()
    print(f"Processing complete. Log at {log_path}")

def parse_text(text: str):
    """
    Wrapper used by the web UI.
    Accepts raw text, splits into logical records using read_records_from_file logic,
    and returns parsed rows.
    """

    # Simulate the record-splitting logic, but using text instead of a file.
    raw_lines = text.splitlines()
    records = []
    current = []

    for line in raw_lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Skip page headers like "Virginia 509"
        if PAGE_HEADER_PATTERN.match(stripped):
            continue

        if is_new_record_line(stripped):
            if current:
                records.append(" ".join(current).strip())
            current = [stripped]
        else:
            if current:
                current.append(stripped)
            else:
                current = [stripped]

    if current:
        records.append(" ".join(current).strip())

    # Parse all records
    rows = []
    for rec in records:
        row = parse_record(rec)
        rows.append(row)

    return rows


if __name__ == "__main__":
    main()
