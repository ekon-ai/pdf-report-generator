"""Shared dataclasses. No global state anywhere in the package."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class Options:
    """All CLI options, assembled once in cli.py and passed explicitly."""

    template: Path
    data: Path
    out: Path
    filename_pattern: str
    mode: str  # "single" | "batch"
    row: int = 1
    strict: bool = False
    font_check: bool = False
    #: True only when --row was explicitly passed by the user (click tracks this).
    row_explicit: bool = False


@dataclass(frozen=True)
class RowData:
    """One CSV data row (non-empty), plus its 1-based index among non-empty rows."""

    index: int
    values: dict[str, str]


@dataclass
class ReportResult:
    """Outcome of generating one PDF."""

    ok: bool
    path: Optional[Path] = None
    elapsed_ms: float = 0.0
    error: str = ""


@dataclass
class BatchSummary:
    generated: int = 0
    failed: int = 0
    total: int = 0
    results: list[ReportResult] = field(default_factory=list)
