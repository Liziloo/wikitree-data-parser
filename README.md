# wikitree-data-parser

Backend and tools for turning DAR-style Revolutionary War lists (like those in *Forgotten Patriots*)
into structured CSV files suitable for WikiTree and other genealogy workflows.

The web UI is branded as:

**Liz’s Fantasmagorical Wikitree Record Parser**  
> Because life is too short for inconsistent muster rolls.

## Features

- General DAR-style text parser (`wikitree_data_parser/parsers/original_parser.py`)
- Virginia-focused parser with ownership logic (`wikitree_data_parser/parsers/virginia_parser.py`)
- Flask web UI (`wikitree_data_parser/backend/webapp.py`) with your color palette and branding
- PDF text extraction helpers (`wikitree_data_parser/backend/pdf_to_text.py`)
- Dockerfile + docker-compose for easy homelab deployment

## Printed page → PDF page (DAR Forgotten Patriots, Pennsylvania)

On the DAR Forgotten Patriots PDF currently wired in:

- The printed header `Pennsylvania 414` appears on **PDF viewer page 245**.

In `wikitree_data_parser/backend/pdf_to_text.py` we therefore have:

```python
STATE_PAGE_MAP = {
    "Pennsylvania": {
        "pdf_start": 245,
        "printed_start": 414,
    }
}
```

When you type in the web UI:

- State: `Pennsylvania`
- Printed page: `414`

The backend translates that into PDF page `245` and extracts text from there.  
You can extend `STATE_PAGE_MAP` with other states once you know their offsets.

## Local development (no Docker)

1. Clone the repo:

   ```bash
   git clone https://github.com/Liziloo/wikitree-data-parser.git
   cd wikitree-data-parser
   ```

2. Create and activate a virtualenv (optional but nice):

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
   ```

3. Install dependencies:

   ```bash
   pip install flask pymupdf
   ```

4. Run the web app:

   ```bash
   python -m wikitree_data_parser.backend.webapp
   ```

5. Open your browser at <http://localhost:5000>.

## Running with Docker (homelab-friendly)

From the repo root on your server:

```bash
docker compose up -d
```

This will:

- Build the image locally
- Run the container named **wikitree-data-parser**
- Expose it on port **5005** on the host

In NGINX Proxy Manager, you can then:

- Create a new Proxy Host for `wikitree.finnoak.com`
- Point it to `http://wikitree-data-parser:5000`
- Put Authelia in front for authentication as you do with your other services

## Using the CLI parsers directly

From the project root (with dependencies installed), you can call:

```bash
# General DAR-style parser
python -m wikitree_data_parser.parsers.original_parser input.txt out_dir --psv

# Virginia-specific parser
python -m wikitree_data_parser.parsers.virginia_parser input.txt out_dir --psv
```

The output will be `.csv` files with either pipe delimiters (`|`) or commas, depending on flags.

## Source material

The original DAR volume you are parsing from is:

> Daughters of the American Revolution. *Forgotten Patriots: African American and American Indian Patriots in the Revolutionary War* (Washington, DC: DAR, 2008).

Public DAR PDF link used during development:

- https://www.dar.org/sites/default/files/media/library/DARpublications/Forgotten_Patriots_ISBN-978-1-892237-10-1.pdf

## License

MIT. Do cool things with it, share improvements, don’t sue anybody.
