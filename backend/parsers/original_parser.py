import re
import argparse
import csv
import os
from datetime import datetime

# ------------------------------------------
# Configuration
# ------------------------------------------

RACE_KEYWORDS = {
    "indian",
    "african american",
    "other free",
    "mixed descent",
    "canawago",
}

RACE_NOTE_KEYWORDS = {
    "complexion",
    "negro",
    "mulatto",
    "dark",
    "black",
}

TRIBES = {
    "penobscot",
    "micmac",
    "maliseet",
    "passamaquoddy",
    "passamoquoddy",
    "mohawk",
    "st. john’s",
    "st. johns",
    "st. john's",
}

RACIAL_NAME_ROOTS = [
    "african",
    "negro",
    "black",
    "colored",
    "mulatto",
    "free black",
]

ALIAS_MARKERS = {"alias", "aka", "a.k.a.", "a.k.a"}

LOCATION_HINTS = {
    "res",
    "res.",
    "residence",
    "town",
    "city",
    "island",
    "bay",
    "river",
    "harbor",
    "harbour",
    "county",
    "co.",
    "point",
    "plantation",
}

# Pattern that marks a true record start
RECORD_START = re.compile(r"^[A-Z][A-Z/.'\- ]*,")  


# ------------------------------------------
# Step 0: Reconstruct logical records
# ------------------------------------------

def reconstruct_records(text):
    """
    Takes raw text with records possibly spanning multiple physical lines.
    Returns a list of fully assembled single-line records.
    """
    logical = []
    current = ""

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue

        if RECORD_START.match(line):
            # New record begins
            if current:
                logical.append(current)
            current = line
        else:
            # Continuation line
            current += " " + line

    if current:
        logical.append(current)

    return logical


# ------------------------------------------
# Helper Functions
# ------------------------------------------

def is_racial_placeholder_name(text: str) -> bool:
    if not text or text != text.upper():
        return False
    lower = text.lower()
    return any(lower.startswith(root) for root in RACIAL_NAME_ROOTS)


def contains_race_keyword(text: str) -> bool:
    t = text.lower()
    return (
        any(keyword in t for keyword in RACE_KEYWORDS) or
        any(keyword in t for keyword in RACE_NOTE_KEYWORDS)
    )


def contains_tribe(text: str) -> bool:
    t = text.lower()
    return any(tribe in t for tribe in TRIBES)


def is_all_caps_word(token: str) -> bool:
    if not token:
        return False
    has_alpha = any(c.isalpha() for c in token)
    return has_alpha and token == token.upper()


def looks_like_source_code(chunk: str) -> bool:
    if not chunk:
        return False
    chunk = chunk.strip()
    cleaned = chunk.replace(" ", "")
    if not cleaned:
        return False
    if any(c.islower() for c in cleaned):
        return False
    if any(c.isdigit() for c in cleaned) or ":" in cleaned or len(cleaned) >= 3:
        return True
    return False


def looks_like_location(chunk: str) -> bool:
    if not chunk:
        return False
    text = chunk.strip().lower()

    if text == "no residence given":
        return True

    if looks_like_source_code(chunk):
        return False

    if any(h in text for h in LOCATION_HINTS):
        return True

    if " " in chunk:
        return True

    if any(c.islower() for c in chunk):
        return True

    return True


# ------------------------------------------
# Parentheses / Brackets Extraction
# ------------------------------------------

PAREN_PATTERN = re.compile(r"(\([^)]*\)|\[[^\]]*\])")

def extract_paren_notes(line: str):
    race_notes = []
    source_notes = []

    def classify_and_store(match):
        block = match.group(0)
        inner = block[1:-1].strip()
        if contains_race_keyword(inner) or contains_tribe(inner):
            race_notes.append(block)
        else:
            source_notes.append(block)
        return ""

    cleaned = PAREN_PATTERN.sub(classify_and_store, line)

    # comma-normalization
    cleaned = re.sub(r"\s*,\s*,\s*", ",", cleaned)
    cleaned = re.sub(r",+", ",", cleaned)
    cleaned = re.sub(r"^,\s*", "", cleaned)
    cleaned = re.sub(r"\s*,\s*$", "", cleaned)

    return cleaned, race_notes, source_notes


# ------------------------------------------
# Alias Extraction
# ------------------------------------------

def strip_aliases_from_chunks(chunks):
    cleaned_chunks = []
    alias_names = []

    for chunk in chunks:
        tokens = chunk.split()
        new_tokens = []
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            if tok.lower() in ALIAS_MARKERS:
                i += 1
                alias_tokens = []
                while i < len(tokens) and is_all_caps_word(tokens[i]):
                    alias_tokens.append(tokens[i])
                    i += 1
                if alias_tokens:
                    alias_names.append(" ".join(alias_tokens))
                continue
            new_tokens.append(tok)
            i += 1
        cleaned_chunks.append(" ".join(new_tokens).strip())

    return cleaned_chunks, alias_names


# ------------------------------------------
# Parse a single line
# ------------------------------------------

def parse_line(line: str, log_list, lineno, filename):
    original = line
    stripped = original.strip()

    if not stripped:
        log_list.append(f"{filename}:{lineno}: BLANK OR EMPTY RECORD")
        return None

    cleaned_line, race_notes, source_note_parens = extract_paren_notes(stripped)

    parts = [p.strip() for p in cleaned_line.split(",") if p.strip()]
    if not parts:
        log_list.append(f"{filename}:{lineno}: NO DATA AFTER CLEANING -> {original}")
        return None

    surname = parts[0]
    tail_all = parts[1:]

    surname_placeholder = is_racial_placeholder_name(surname)

    location_chunk = ""
    main_tail = tail_all

    if tail_all:
        candidate_last = tail_all[-1]
        if looks_like_location(candidate_last):
            location_chunk = candidate_last
            main_tail = tail_all[:-1]

    given = ""
    tail_for_rest = main_tail[:]

    if not main_tail or surname_placeholder:
        given = ""
    else:
        first_main = main_tail[0]
        if contains_race_keyword(first_main) or contains_tribe(first_main):
            given = ""
            tail_for_rest = main_tail
        else:
            given = first_main
            tail_for_rest = main_tail[1:]

    tail_for_rest, alias_names = strip_aliases_from_chunks(tail_for_rest)

    race_chunks = list(race_notes)
    source_pieces = []

    for chunk in tail_for_rest:
        if not chunk:
            continue
        if contains_race_keyword(chunk) or contains_tribe(chunk):
            race_chunks.append(chunk)
        else:
            source_pieces.append(chunk)

    race_field = ", ".join(race_chunks) if race_chunks else ""

    if source_pieces:
        sources_field = "DAR, " + ", ".join(source_pieces)
    else:
        sources_field = "DAR,"

    source_notes_parts = list(source_note_parens)
    if location_chunk:
        source_notes_parts.append(location_chunk)

    source_notes_field = "; ".join(source_notes_parts) if source_notes_parts else ""

    if alias_names:
        if given:
            given = f"{given} (alias {'; '.join(alias_names)})"
        else:
            given = f"(alias {'; '.join(alias_names)})"

    return ["", "", surname, given, race_field, sources_field, source_notes_field]


# ------------------------------------------
# File Processing Pipeline
# ------------------------------------------

def process_text(text: str, filename, log_list):
    rows = []
    logical_records = reconstruct_records(text)

    for lineno, record in enumerate(logical_records, start=1):
        parsed = parse_line(record, log_list, lineno, filename)
        if parsed:
            rows.append(parsed)

    return rows


def write_output(rows, output_path, delimiter):
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(
            f,
            delimiter=delimiter,
            quotechar='"',
            quoting=csv.QUOTE_MINIMAL
        )
        for row in rows:
            writer.writerow(row)


def process_file(input_path, output_dir, delimiter, extension, log_list):
    basename = os.path.basename(input_path)
    stem, _ = os.path.splitext(basename)
    output_path = os.path.join(output_dir, f"{stem}.{extension}")

    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read()

    rows = process_text(text, basename, log_list)
    write_output(rows, output_path, delimiter)

    return basename, len(rows), output_path


# ------------------------------------------
# CLI
# ------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Parse Revolutionary War rolls into structured CSV rows.")
    parser.add_argument("input", help="Input file or directory")
    parser.add_argument("output_dir", help="Directory to write output files")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--csv", action="store_true", help="Comma-delimited output (.csv)")
    group.add_argument("--psv", action="store_true", help="Pipe-delimited output (.csv)")

    args = parser.parse_args()

    delimiter = "," if args.csv else "|"
    extension = "csv"

    os.makedirs(args.output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_path = os.path.join(args.output_dir, f"parse_log_{timestamp}.txt")
    log_list = [f"Batch started {datetime.now()}"]

    processed = []

    if os.path.isdir(args.input):
        for filename in sorted(os.listdir(args.input)):
            if filename.lower().endswith(".txt"):
                full_path = os.path.join(args.input, filename)
                processed.append(
                    process_file(full_path, args.output_dir, delimiter, extension, log_list)
                )
    else:
        processed.append(
            process_file(args.input, args.output_dir, delimiter, extension, log_list)
        )

    with open(log_path, "w", encoding="utf-8") as logf:
        logf.write("\n".join(log_list))

    print("\nBatch complete:")
    for fname, count, outpath in processed:
        print(f"{fname:30} → {count:5} rows → {outpath}")
    print(f"\nLog written to: {log_path}\n")

def parse_text(text: str):
    """
    Wrapper used by the web UI.
    Accepts raw text, returns parsed rows (list of lists).
    """
    log_list = []
    rows = process_text(text, filename="web_input.txt", log_list=log_list)
    return rows


if __name__ == "__main__":
    main()
