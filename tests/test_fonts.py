from __future__ import annotations

from pathlib import Path

from pdf_report.template import extract_font_families

CSS = """
<style>
  body { font-family: "DejaVu Sans", "Liberation Sans", Noto Sans, Arial, sans-serif; }
  h1 { font-family: 'Times New Roman', serif; }
</style>
"""


def test_extract_families(tmp_path: Path) -> None:
    p = tmp_path / "t.html"
    p.write_text(CSS, encoding="utf-8")
    fams = extract_font_families(p)
    assert "DejaVu Sans" in fams
    assert "Liberation Sans" in fams
    assert "Noto Sans" in fams
    assert "Times New Roman" in fams
    assert "sans-serif" not in fams and "serif" not in fams  # generic keywords dropped
    assert "Arial" in fams


def test_no_families(tmp_path: Path) -> None:
    p = tmp_path / "t.html"
    p.write_text("<b>no css</b>", encoding="utf-8")
    assert extract_font_families(p) == []


def test_check_fonts_returns_statuses(tmp_path: Path) -> None:
    from pdf_report.fonts import check_fonts

    p = tmp_path / "t.html"
    p.write_text(CSS, encoding="utf-8")
    statuses = check_fonts(p)
    # Either fc-list works (statuses per family) or it's unavailable ([]).
    assert all(s.available for s in statuses if s.family == "DejaVu Sans") or statuses == []
