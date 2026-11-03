"""CSV parsing: FR-2. utf-8-sig, DictReader, header/row validation, skip empty rows."""

from __future__ import annotations

import csv
import re
from pathlib import Path

from pdf_report.types import RowData

_HEADER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class CsvError(Exception):
    """Fatal CSV problem (empty file, invalid structure under --strict)."""


def normalize_header(name: str) -> str:
    """Map an arbitrary column title to a Jinja-safe identifier."""
    cleaned = re.sub(r"[\s\-]+", "_", name.strip())
    cleaned = re.sub(r"[^A-Za-z0-9_]", "", cleaned)
    if not cleaned or not re.match(r"^[A-Za-z_]", cleaned):
        cleaned = f"_{cleaned}" if cleaned else "column"
    return cleaned


def read_csv(
    path: Path, strict: bool = False, warn=None
) -> tuple[list[str], list[RowData]]:
    """Return (normalized_headers, non_empty_rows).

    Row indices are 1-based over *non-empty* rows only, so `--row N` maps to
    `rows[N - 1]`. Values are stripped; short rows are padded with "" and long
    rows truncated (both warned; fatal under strict).
    """
    def _warn(msg: str) -> None:
        if warn is not None:
            warn(msg)

    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        text = fh.read()
    reader = csv.reader(text.splitlines())
    try:
        raw_headers = next(reader)
    except StopIteration:
        raise CsvError(f"CSV file is empty (no header row): {path}") from None

    headers: list[str] = []
    for h in raw_headers:
        if _HEADER_RE.match(h.strip()):
            headers.append(h.strip())
        else:
            norm = normalize_header(h)
            _warn(f"Header {h!r} normalized to {norm!r}")
            if strict:
                raise CsvError(f"Invalid CSV header {h!r} (expected pattern ^[A-Za-z_][A-Za-z0-9_]*$)")
            headers.append(norm)

    rows: list[RowData] = []
    index = 0
    for line_no, fields in enumerate(reader, start=2):
        if all(not f.strip() for f in fields):
            continue  # fully empty row: skipped, does not consume an index
        index += 1
        values: dict[str, str] = {}
        if len(fields) < len(headers):
            msg = f"Row at line {line_no}: {len(fields)} fields < {len(headers)} headers; missing filled with ''"
            if strict:
                raise CsvError(msg)
            _warn(msg)
        elif len(fields) > len(headers):
            msg = f"Row at line {line_no}: extra fields beyond {len(headers)} headers dropped"
            if strict:
                raise CsvError(msg)
            _warn(msg)
        for key, val in zip(headers, fields):
            values[key] = val.strip()
        for key in headers[len(fields):]:
            values[key] = ""
        rows.append(RowData(index=index, values=values))

    return headers, rows
