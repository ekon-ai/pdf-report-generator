from __future__ import annotations

from pdf_report.naming import (
    NamingError, format_index, render_name, resolve_collisions, validate_pattern,
)
import pytest
from pathlib import Path


def test_validate_requires_index() -> None:
    with pytest.raises(NamingError):
        validate_pattern("report_{client_name}.pdf", {"client_name"})


def test_validate_unknown_token() -> None:
    with pytest.raises(NamingError):
        validate_pattern("r_{foo}_{index}.pdf", {"client_name"})


def test_validate_ok() -> None:
    assert validate_pattern("invoice_{invoice_number}_{index}.pdf", {"invoice_number"}) == \
        ["invoice_number", "index"]


def test_render_name_index_padded_and_cyrillic_kept() -> None:
    name = render_name("invoice_{client_name}_{index}.pdf",
                       {"client_name": "ООО Ромашка"}, 3)
    assert name == "invoice_ООО Ромашка_003.pdf"  # Cyrillic + spaces kept as-is


def test_render_name_sanitizes_quotes() -> None:
    name = render_name("{col}_{index}.pdf", {"col": 'ООО "Ромашка"'}, 1)
    assert '"' not in name and "Ромашка" in name


def test_render_name_sanitizes_forbidden() -> None:
    name = render_name("{col}_{index}.pdf", {"col": "a/b:c*d"}, 1)
    assert "/" not in name and ":" not in name and "*" not in name


def test_format_index() -> None:
    assert format_index(1) == "001"
    assert format_index(1234) == "1234"


def test_resolve_collisions(tmp_path: Path) -> None:
    paths = resolve_collisions(tmp_path, ["a.pdf", "a.pdf", "a.pdf"])
    assert [p.name for p in paths] == ["a.pdf", "a_1.pdf", "a_2.pdf"]
