# wikitree-data-parser

Backend and tools for turning DAR-style Revolutionary War lists (like those in *Forgotten Patriots*)
into structured CSV files suitable for WikiTree and other genealogy workflows.

The web UI is branded as:

**Liz’s Fantasmagorical Wikitree Record Parser**  
> Because life is too short for inconsistent muster rolls.

---

## Features

- General DAR-style text parser (`backend/parsers/original_parser.py`)
- Virginia-focused parser with ownership logic (`backend/parsers/virginia_parser.py`)
- Flask web UI (`backend/webapp.py`) with your color palette and branding
- PDF text extraction helpers (`backend/pdf_to_text.py`)
- Dockerfile + docker-compose for easy homelab deployment

---

## PDF Page Logic

Different state sections do not correspond to consistent PDF page numbers.  
As of now, only **Massachusetts** has a verified printed-page → PDF-page offset.

### **Massachusetts Offset**
```
printed_page 77 → pdf_page 93  
offset = +16
```

Therefore:
```
pdf_page = printed_page + 16
```

All other states currently expect **raw PDF page numbers**.

---

## Running Locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python backend/webapp.py
```

Open your browser at:

```
http://localhost:5000
```

---

## Local Development (no Docker)

1. Clone the repo:

   ```bash
   git clone https://github.com/Liziloo/wikitree-data-parser.git
   cd wikitree-data-parser
   ```

2. Create and activate a virtualenv (optional):

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Windows: .venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install flask pymupdf
   ```

4. Run the web app:

   ```bash
   python -m backend.webapp
   ```

5. Then go to: <http://localhost:5000>

---

## Running with Docker (homelab-friendly)

From the repo root on your server:

```bash
docker compose up -d
```

This will:

- Build the image locally  
- Run the container as **wikitree-data-parser**  
- Expose the app on **port 5005** (host) → **5000** (container)

In **NGINX Proxy Manager**, point your Proxy Host:

```
wikitree.finnoak.com → http://wikitree-data-parser:5000
```

Put **Authelia** in front if desired.

---

## Using the CLI Parsers Directly

```bash
# General DAR-style parser
python -m backend.parsers.original_parser input.txt output_dir --psv

# Virginia-specific parser
python -m backend.parsers.virginia_parser input.txt output_dir --psv
```

Output files will be `.csv` using pipe (`|`) or comma delimiters, depending on options.

---

## Source Material

The DAR volume parsed by this tool:

> Daughters of the American Revolution. *Forgotten Patriots: African American and American Indian Patriots in the Revolutionary War* (Washington, DC: DAR, 2008).

Public PDF:

https://www.dar.org/sites/default/files/media/library/DARpublications/Forgotten_Patriots_ISBN-978-1-892237-10-1.pdf

---

## License

MIT.  
Do cool things with it, share improvements, don’t sue an
