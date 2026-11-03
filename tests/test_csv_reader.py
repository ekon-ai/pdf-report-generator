from __future__ import annotations

from pathlib import Path

import pytest

from pdf_report.csv_reader import CsvError, normalize_header, read_csv


def write(tmp_path: Path, text: str, bom: bool = False) -> Path:
    p = tmp_path / "d.csv"
    data = ("\ufeff" if bom else "") + text
    p.write_text(data, encoding="utf-8")
    return p


def test_basic_with_cyrillic(tmp_path: Path) -> None:
    p = write(tmp_path, 'client_name,total\nООО "Ромашка",15000\nИП Иванов,27500\n')
    headers, rows = read_csv(p)
    assert headers == ["client_name", "total"]
    assert len(rows) == 2
    assert rows[0].values["client_name"] == 'ООО "Ромашка"'
    assert rows[1].index == 2


def test_bom_handled(tmp_path: Path) -> None:
    p = write(tmp_path, "a,b\n1,2\n", bom=True)
    headers, _ = read_csv(p)
    assert headers[0] == "a"


def test_zero_data_rows(tmp_path: Path) -> None:
    p = write(tmp_path, "a,b,c\n")
    _, rows = read_csv(p)
    assert rows == []


def test_one_row(tmp_path: Path) -> None:
    p = write(tmp_path, "a\nx\n")
    _, rows = read_csv(p)
    assert len(rows) == 1 and rows[0].index == 1


def test_empty_rows_skipped_without_shifting_index(tmp_path: Path) -> None:
    p = write(tmp_path, "a\n1\n\n2\n   ,\n3\n")
    _, rows = read_csv(p)
    assert [r.index for r in rows] == [1, 2, 3]
    assert [r.values["a"] for r in rows] == ["1", "2", "3"]


def test_short_row_padded(tmp_path: Path) -> None:
    warnings: list[str] = []
    p = write(tmp_path, "a,b,c\n1,2\n")
    _, rows = read_csv(p, warn=warnings.append)
    assert rows[0].values == {"a": "1", "b": "2", "c": ""}
    assert warnings


def test_short_row_strict_fails(tmp_path: Path) -> None:
    p = write(tmp_path, "a,b,c\n1,2\n")
    with pytest.raises(CsvError):
        read_csv(p, strict=True)


def test_invalid_header_normalized(tmp_path: Path) -> None:
    p = write(tmp_path, "Client Name,Total-Owed\n1,2\n")
    headers, _ = read_csv(p)
    assert headers == ["Client_Name", "Total_Owed"]


def test_normalize_header() -> None:
    assert normalize_header("  my col-name! ") == "my_col_name"
    assert normalize_header("1st") == "_1st"


def test_values_trimmed(tmp_path: Path) -> None:
    p = write(tmp_path, "a,b\n  x  , y \n")
    _, rows = read_csv(p)
    assert rows[0].values == {"a": "x", "b": "y"}
