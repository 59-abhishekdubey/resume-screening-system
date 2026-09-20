import csv
import os
import shutil
from pathlib import Path

import pytest

from src.pdf_parser import extract_text_from_pdf, extract_text_from_pdfs

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "raw" / "Resume.csv"
PDF_DIR = ROOT / "data" / "raw" / "pdfs"


def _load_resume_map():
    """Load ID -> Resume_str map from Resume.csv."""
    mapping = {}
    if not CSV_PATH.exists():
        return mapping
    with open(CSV_PATH, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rid = str(row.get("ID", "")).strip()
            if rid:
                mapping[rid] = row.get("Resume_str", "") or ""
    return mapping


def _get_first_fixture():
    """Return (pdf_path: Path, source_text: str) for first available fixture.

    If no fixture PDFs exist, generate one deterministically from Resume.csv
    using reportlab (dev dep) so tests remain passing without manual setup.
    """
    resume_map = _load_resume_map()
    if not resume_map:
        pytest.skip("Resume.csv not found or empty")

    # Ensure PDF_DIR exists
    PDF_DIR.mkdir(parents=True, exist_ok=True)

    existing = sorted(PDF_DIR.glob("*.pdf"))
    if existing:
        pdf_path = existing[0]
        rid = pdf_path.stem
        source = resume_map.get(rid, "")
        # source may be empty if PDF was not from Resume.csv; fallback to first row
        if not source:
            source = next(iter(resume_map.values()))
        return pdf_path, source

    # No fixture — generate one on the fly (idempotent helper)
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except ImportError:
        pytest.skip("No fixture PDFs and reportlab not installed (pip install reportlab)")

    import textwrap

    sorted_ids = sorted(resume_map.keys())
    rid = sorted_ids[0]
    source = resume_map[rid]
    pdf_path = PDF_DIR / f"{rid}.pdf"

    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    c.setFont("Helvetica", 10)
    PAGE_W, PAGE_H = letter
    MARGIN = 72
    LEADING = 14
    MAX_CHARS = 95
    x = MARGIN
    y = PAGE_H - MARGIN
    lines = []
    for para in source.splitlines():
        if not para.strip():
            lines.append("")
            continue
        wrapped = textwrap.wrap(para.strip(), width=MAX_CHARS, break_long_words=True, break_on_hyphens=False)
        lines.extend(wrapped if wrapped else [para.strip()])
    for line in lines:
        if y < MARGIN:
            c.showPage()
            c.setFont("Helvetica", 10)
            y = PAGE_H - MARGIN
        if line:
            try:
                c.drawString(x, y, line)
            except Exception:
                safe = line.encode("latin-1", errors="replace").decode("latin-1")
                c.drawString(x, y, safe)
        y -= LEADING
    c.save()
    return pdf_path, source


def _pick_two_skills(source_text: str) -> list[str]:
    """Pick two skills that actually occur in source_text (case-insensitive).

    Prefers known skill tokens; falls back to longest words in the text.
    """
    common_skills = [
        "Python", "SQL", "Java", "AWS", "Docker", "Machine Learning",
        "Pandas", "NumPy", "Scikit-learn", "TensorFlow", "PyTorch",
        "Git", "Excel", "Tableau", "Power BI", "Hadoop", "Spark",
        "Azure", "Kubernetes", "React", "JavaScript", "C++", "R",
    ]
    lower = source_text.lower()
    found = [s for s in common_skills if s.lower() in lower]
    if len(found) >= 2:
        return found[:2]
    if len(found) == 1:
        # supplement with a long word from the text
        words = [w.strip(".,;:()[]") for w in source_text.split()]
        words = [w for w in words if len(w) >= 5]
        for w in words:
            if w.lower() not in lower or w == found[0]:
                continue
            # ensure not duplicate
            if w.lower() != found[0].lower():
                return [found[0], w]
        return found
    # No common skills found — pick two longest distinct words that will survive PDF round-trip
    words = [w.strip(".,;:()[]\"'") for w in source_text.split()]
    words = [w for w in words if len(w) >= 4 and w.isalpha()]
    # deduplicate preserving order
    seen = set()
    uniq = []
    for w in words:
        lw = w.lower()
        if lw not in seen:
            seen.add(lw)
            uniq.append(w)
    # sort by length descending and take top 2
    uniq_sorted = sorted(uniq, key=len, reverse=True)
    if len(uniq_sorted) >= 2:
        return uniq_sorted[:2]
    if uniq_sorted:
        return [uniq_sorted[0]]
    return []


# ---- Tests ----

def test_extract_returns_nonempty_for_real_fixture():
    pdf_path, source_text = _get_first_fixture()
    result = extract_text_from_pdf(str(pdf_path))
    assert isinstance(result, str)
    assert len(result.strip()) > 0, "extracted text should be non-empty"
    # Rough integrity check: length within ±20% of source Resume_str
    src_len = len(source_text.strip())
    res_len = len(result.strip())
    assert src_len > 0
    assert res_len >= src_len * 0.8, f"extracted length {res_len} < 80% of source {src_len}"
    assert res_len <= src_len * 1.2 + 500, f"extracted length {res_len} > 120% of source {src_len} (+500 tolerance)"


def test_extract_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        extract_text_from_pdf(str(ROOT / "data" / "raw" / "pdfs" / "does_not_exist_999999.pdf"))
    with pytest.raises(FileNotFoundError):
        extract_text_from_pdf("/tmp/definitely_missing_xyz_12345.pdf")


def test_extract_empty_folder_returns_empty_dict(tmp_path):
    # tmp_path is an empty temp directory provided by pytest
    result = extract_text_from_pdfs(str(tmp_path))
    assert result == {}
    assert isinstance(result, dict)


def test_extract_folder_skips_non_pdf_files(tmp_path):
    # Create one .txt file (should be ignored)
    txt_file = tmp_path / "notes.txt"
    txt_file.write_text("this is not a pdf", encoding="utf-8")

    # Create one real PDF in tmp_path by copying a fixture or generating minimal PDF
    pdf_path, _ = _get_first_fixture()
    dest_pdf = tmp_path / pdf_path.name
    shutil.copy(str(pdf_path), str(dest_pdf))

    result = extract_text_from_pdfs(str(tmp_path))
    assert dest_pdf.stem in result, "pdf file should appear in result"
    assert "notes" not in result, ".txt file should be skipped"
    assert len(result) == 1
    assert isinstance(result[dest_pdf.stem], str)
    assert len(result[dest_pdf.stem].strip()) > 0


def test_roundtrip_skill_preservation():
    pdf_path, source_text = _get_first_fixture()
    extracted = extract_text_from_pdf(str(pdf_path))
    skills = _pick_two_skills(source_text)
    assert len(skills) >= 1, "source Resume_str should contain at least one detectable skill/keyword"
    lower_extracted = extracted.lower()
    for skill in skills:
        assert skill.lower() in lower_extracted, f"skill '{skill}' found in Resume_str but missing in PDF extracted text"
