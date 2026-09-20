"""One-off fixture generator for Phase 8 (Option A).

Reads data/raw/Resume.csv, selects 20 resumes deterministically (first 20 by ID
sorted lexicographically), and writes each Resume_str as a plain-text PDF to
data/raw/pdfs/<ID>.pdf using reportlab. Idempotent: skips IDs whose PDF
already exists. Handles multi-page resumes by wrapping and paginating.

Usage:
    python notebooks/phase8_generate_fixtures.py
    # from repo root
Requires:
    reportlab as dev/test-time dependency only (NOT a runtime dep of src/pdf_parser.py).
    If not installed: pip install reportlab

Output:
    Prints "generated N fixture PDFs, skipped M existing"
"""
import csv
import os
import textwrap

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
except ImportError:
    print("ERROR: reportlab is not installed.")
    print("Install it as a dev/test dependency with:")
    print("    python -m pip install reportlab")
    print("Then re-run: python notebooks/phase8_generate_fixtures.py")
    raise SystemExit(1)

SRC_CSV = os.path.join("data", "raw", "Resume.csv")
OUT_DIR = os.path.join("data", "raw", "pdfs")

PAGE_W, PAGE_H = letter
MARGIN = 72
FONT_NAME = "Helvetica"
FONT_SIZE = 10
LEADING = 14
MAX_CHARS_PER_LINE = 95

os.makedirs(OUT_DIR, exist_ok=True)

if not os.path.exists(SRC_CSV):
    print(f"ERROR: Source CSV not found: {SRC_CSV}")
    raise SystemExit(1)

with open(SRC_CSV, "r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

if not rows:
    print("ERROR: Resume.csv is empty")
    raise SystemExit(1)

rows_sorted = sorted(rows, key=lambda r: r.get("ID", ""))
selected = rows_sorted[:20]

generated = 0
skipped = 0

for row in selected:
    resume_id = str(row.get("ID", "")).strip()
    resume_text = row.get("Resume_str", "") or ""
    if not resume_id:
        continue
    out_path = os.path.join(OUT_DIR, f"{resume_id}.pdf")
    if os.path.exists(out_path):
        skipped += 1
        continue

    c = canvas.Canvas(out_path, pagesize=letter)
    c.setFont(FONT_NAME, FONT_SIZE)

    x = MARGIN
    y = PAGE_H - MARGIN

    paragraphs = resume_text.splitlines()
    lines_to_draw: list[str] = []
    for para in paragraphs:
        if not para.strip():
            lines_to_draw.append("")
            continue
        wrapped = textwrap.wrap(para.strip(), width=MAX_CHARS_PER_LINE, break_long_words=True, break_on_hyphens=False)
        if not wrapped:
            lines_to_draw.append(para.strip())
        else:
            lines_to_draw.extend(wrapped)

    for line in lines_to_draw:
        if y < MARGIN:
            c.showPage()
            c.setFont(FONT_NAME, FONT_SIZE)
            y = PAGE_H - MARGIN
        if line:
            try:
                c.drawString(x, y, line)
            except Exception:
                safe = line.encode("latin-1", errors="replace").decode("latin-1")
                c.drawString(x, y, safe)
        y -= LEADING

    c.save()
    generated += 1

print(f"generated {generated} fixture PDFs, skipped {skipped} existing")
