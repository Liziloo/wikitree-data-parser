import subprocess
import tempfile
from pathlib import Path

from flask import Flask, render_template_string, request, send_file

from .pdf_to_text import extract_text, resolve_printed_page

app = Flask(__name__)

TEMPLATE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <title>Fantasmagorical Wikitree Parser</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <style>
      :root {
        --amber-flame: #fcb815ff;
        --medium-jungle: #58ab58ff;
        --prussian-blue: #011936ff;
        --charcoal-blue: #465362ff;
        --dark-spruce: #285238ff;
      }

      * {
        box-sizing: border-box;
      }

      body {
        margin: 0;
        padding: 0;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI",
                     sans-serif;
        background-color: #ffffff;
        color: var(--prussian-blue);
      }

      .page {
        min-height: 100vh;
        display: flex;
        flex-direction: column;
      }

      header {
        background: linear-gradient(135deg, var(--prussian-blue), var(--dark-spruce));
        color: #ffffff;
        padding: 1.75rem 1rem;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
      }

      .header-inner {
        max-width: 960px;
        margin: 0 auto;
      }

      h1 {
        margin: 0;
        font-size: 1.9rem;
        letter-spacing: 0.02em;
      }

      .tagline {
        margin-top: 0.4rem;
        font-size: 0.95rem;
        color: #f5f5f5;
      }

      main {
        flex: 1;
        padding: 1.5rem 1rem 2.5rem;
      }

      .content {
        max-width: 960px;
        margin: 0 auto;
      }

      .card {
        background-color: #ffffff;
        border-radius: 12px;
        border: 1px solid rgba(1, 25, 54, 0.08);
        box-shadow: 0 4px 12px rgba(1, 25, 54, 0.05);
        padding: 1.5rem;
      }

      .card h2 {
        margin-top: 0;
        font-size: 1.25rem;
        color: var(--charcoal-blue);
      }

      fieldset {
        border: 1px solid rgba(1, 25, 54, 0.12);
        border-radius: 8px;
        margin: 1rem 0;
        padding: 0.85rem 1rem 1rem;
      }

      legend {
        padding: 0 0.4rem;
        color: var(--dark-spruce);
        font-weight: 600;
        font-size: 0.9rem;
      }

      label {
        font-size: 0.9rem;
        color: var(--charcoal-blue);
      }

      input[type="file"],
      input[type="text"],
      textarea,
      select {
        width: 100%;
        padding: 0.45rem 0.6rem;
        margin-top: 0.25rem;
        border-radius: 6px;
        border: 1px solid rgba(1, 25, 54, 0.25);
        font-size: 0.9rem;
        font-family: inherit;
      }

      textarea {
        resize: vertical;
        min-height: 9rem;
      }

      .hint {
        font-size: 0.8rem;
        color: rgba(70, 83, 98, 0.9);
        margin-top: 0.1rem;
      }

      .option-row {
        display: flex;
        flex-wrap: wrap;
        gap: 1.5rem;
        margin: 0.5rem 0;
      }

      .option-group {
        display: flex;
        align-items: center;
        gap: 0.35rem;
        font-size: 0.9rem;
      }

      button[type="submit"] {
        margin-top: 1.2rem;
        padding: 0.55rem 1.4rem;
        border-radius: 999px;
        border: none;
        cursor: pointer;
        background: var(--amber-flame);
        color: #111111;
        font-weight: 600;
        font-size: 0.95rem;
        box-shadow: 0 2px 6px rgba(252, 184, 21, 0.5);
        transition: transform 0.05s ease-out, box-shadow 0.05s ease-out,
                    background-color 0.15s ease-out;
      }

      button[type="submit"]:hover {
        background-color: #ffcb4a;
        transform: translateY(-1px);
        box-shadow: 0 4px 10px rgba(252, 184, 21, 0.55);
      }

      button[type="submit"]:active {
        transform: translateY(0);
        box-shadow: 0 1px 3px rgba(252, 184, 21, 0.4);
      }

      .error {
        margin-top: 1rem;
        padding: 0.75rem 0.85rem;
        border-radius: 8px;
        background-color: rgba(252, 184, 21, 0.12);
        border: 1px solid rgba(252, 184, 21, 0.8);
        color: #5c3a00;
        font-size: 0.9rem;
      }

      .helper-text {
        font-size: 0.85rem;
        color: rgba(70, 83, 98, 0.95);
        margin-top: 0.4rem;
      }

      footer {
        border-top: 1px solid rgba(1, 25, 54, 0.06);
        padding: 0.8rem 1rem 1.1rem;
        background-color: #fafbfc;
      }

      .footer-inner {
        max-width: 960px;
        margin: 0 auto;
        font-size: 0.8rem;
        color: rgba(70, 83, 98, 0.9);
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        flex-wrap: wrap;
      }

      .footer-inner a {
        color: var(--medium-jungle);
        text-decoration: none;
      }

      .footer-inner a:hover {
        text-decoration: underline;
      }

      @media (max-width: 640px) {
        header {
          padding: 1.25rem 1rem;
        }
        h1 {
          font-size: 1.5rem;
        }
        main {
          padding: 1rem;
        }
        .card {
          padding: 1.1rem;
        }
      }
    </style>
  </head>
  <body>
    <div class="page">
      <header>
        <div class="header-inner">
          <h1>Liz’s Fantasmagorical Wikitree Record Parser</h1>
          <div class="tagline">Because life is too short for inconsistent muster rolls.</div>
        </div>
      </header>

      <main>
        <div class="content">
          <div class="card">
            <h2>Ingest a historical list and get a structured CSV</h2>
            <p class="helper-text">
              Upload a DAR-style PDF or text file, or paste a list directly. Choose the parser
              that matches your source, then download a CSV ready for WikiTree, OpenRefine,
              or your spreadsheet of choice.
            </p>

            <form method="post" enctype="multipart/form-data">
              <fieldset>
                <legend>Input</legend>
                <p>
                  <label>PDF or TXT file:
                    <input type="file" name="file" />
                  </label>
                  <div class="hint">For DAR Forgotten Patriots or similar compiled lists.</div>
                </p>

                <p>
                  <label>PDF pages (e.g. 36-43, optional):
                    <input type="text" name="pages" placeholder="36-43" />
                  </label>
                  <div class="hint">Uses the page number shown by your PDF viewer (1-based).</div>
                </p>

                <p>
                  <label>Printed page (optional):
                    <input type="text" name="printed_page" placeholder="414" />
                  </label>
                  <div class="hint">
                    If you also select a state below, the app will automatically translate this
                    printed page into the correct PDF page for the DAR Forgotten Patriots PDF.
                  </div>
                </p>

                <p>
                  <label>State (for printed page lookup):
                    <select name="state">
                      <option value="">-- Select State (for printed page) --</option>
                      <option value="Pennsylvania">Pennsylvania</option>
                      <!-- Add more states here once STATE_PAGE_MAP is extended -->
                    </select>
                  </label>
                </p>

                <p>
                  <label>Or paste list text:
                    <textarea name="pasted" placeholder="Paste a list such as 'CARNEY, THOMAS, African American, Soldier, …'"></textarea>
                  </label>
                  <div class="hint">If both file and pasted text are provided, the uploaded file will be used.</div>
                </p>
              </fieldset>

              <fieldset>
                <legend>Options</legend>

                <p><strong>Parser:</strong></p>
                <div class="option-row">
                  <label class="option-group">
                    <input type="radio" name="parser" value="original" checked />
                    <span>General DAR-style parser</span>
                  </label>
                  <label class="option-group">
                    <input type="radio" name="parser" value="virginia" />
                    <span>Virginia-specific parser</span>
                  </label>
                </div>

                <p><strong>Output format:</strong></p>
                <div class="option-row">
                  <label class="option-group">
                    <input type="radio" name="format" value="psv" checked />
                    <span>Pipe-delimited (.csv with <code>|</code>)</span>
                  </label>
                  <label class="option-group">
                    <input type="radio" name="format" value="csv" />
                    <span>Comma-delimited (.csv)</span>
                  </label>
                </div>

                <p class="helper-text">
                  If you supply both a printed page <em>and</em> a state, the printed page
                  will be translated to the appropriate PDF page for the DAR Forgotten Patriots PDF,
                  and the “PDF pages” box will be ignored.
                </p>
              </fieldset>

              <button type="submit">Parse record list</button>
            </form>

            {% if error %}
              <div class="error">
                {{ error }}
              </div>
            {% endif %}
          </div>
        </div>
      </main>

      <footer>
        <div class="footer-inner">
          <div>Liz’s Fantasmagorical Wikitree Record Parser</div>
          <div>Running on your friendly neighborhood homelab.</div>
        </div>
      </footer>
    </div>
  </body>
</html>"""


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template_string(TEMPLATE)

    parser_choice = request.form.get("parser", "original")
    fmt = request.form.get("format", "psv")

    # Page selection inputs
    pages_raw = request.form.get("pages", "").strip()
    printed_page_raw = request.form.get("printed_page", "").strip()
    state = request.form.get("state", "").strip()

    pasted = request.form.get("pasted", "").strip()
    upload = request.files.get("file")

    if not upload and not pasted:
        return render_template_string(TEMPLATE, error="Please upload a file or paste text.")

    # Determine which page selection mechanism to use
    pages_arg = None
    if printed_page_raw and state:
        try:
            printed_page = int(printed_page_raw)
            pdf_page = resolve_printed_page(state, printed_page)
            pages_arg = str(pdf_page)
        except Exception as e:
            return render_template_string(
                TEMPLATE,
                error=f"Printed page lookup failed: {e}"
            )
    else:
        pages_arg = pages_raw or None

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Step 1: get plain text
        if upload:
            filename = upload.filename or "input"
            suffix = Path(filename).suffix.lower()
            file_path = tmpdir_path / filename
            upload.save(file_path)

            if suffix == ".pdf":
                text = extract_text(file_path, pages=pages_arg)
            else:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
        else:
            text = pasted

        input_txt = tmpdir_path / "input.txt"
        input_txt.write_text(text, encoding="utf-8")

        out_dir = tmpdir_path / "out"
        out_dir.mkdir(exist_ok=True)

        # Step 2: call the appropriate parser script via -m
        if parser_choice == "virginia":
            cmd = [
                "python",
                "-m",
                "wikitree_data_parser.parsers.virginia_parser",
                str(input_txt),
                str(out_dir),
            ]
            if fmt == "psv":
                cmd.append("--psv")
        else:
            cmd = [
                "python",
                "-m",
                "wikitree_data_parser.parsers.original_parser",
                str(input_txt),
                str(out_dir),
            ]
            if fmt == "psv":
                cmd.append("--psv")
            else:
                cmd.append("--csv")

        try:
            subprocess.check_call(cmd)
        except subprocess.CalledProcessError as e:
            return render_template_string(TEMPLATE, error=f"Parser failed: {e}")

        out_files = list(out_dir.glob("*.csv"))
        if not out_files:
            return render_template_string(TEMPLATE, error="No output file produced by parser.")

        output_file = out_files[0]

        return send_file(
            output_file,
            as_attachment=True,
            download_name="parsed_output.csv",
            mimetype="text/csv",
        )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
