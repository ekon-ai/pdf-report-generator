"""WeasyPrint rendering & batch orchestration: FR-4, FR-6, NFR-7."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

import jinja2
from weasyprint import HTML

from pdf_report.naming import render_name, resolve_collisions
from pdf_report.template import render
from pdf_report.types import BatchSummary, Options, ReportResult, RowData


def write_pdf(html: str, base_url: Path, out_path: Path) -> None:
    """Render HTML string to PDF. base_url resolves relative css/img/font paths
    against the template directory (FR-4), not CWD."""
    HTML(string=html, base_url=str(base_url)).write_pdf(str(out_path))


def generate(opts: Options, template: jinja2.Template, rows: list[RowData],
             log_ok: Callable[[str, float], None],
             log_err: Callable[[str, str], None]) -> BatchSummary:
    """Generate PDFs for selected rows. One row at a time: rendered HTML is
    released each iteration (NFR-7). A per-row failure does not abort the batch
    unless --strict (then the first failure propagates)."""
    summary = BatchSummary(total=len(rows))
    opts.out.mkdir(parents=True, exist_ok=True)

    names = [render_name(opts.filename_pattern, r.values, r.index) for r in rows]
    targets = resolve_collisions(opts.out, names)

    for row, target in zip(rows, targets):
        start = time.perf_counter()
        try:
            html = render(template, row.values)
            write_pdf(html, opts.template.parent, target)
            elapsed = (time.perf_counter() - start) * 1000.0
            summary.results.append(ReportResult(ok=True, path=target, elapsed_ms=elapsed))
            summary.generated += 1
            log_ok(target.name, elapsed)
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000.0
            if opts.strict:
                raise
            summary.results.append(ReportResult(ok=False, path=target, error=str(exc)))
            summary.failed += 1
            log_err(target.name, f"{type(exc).__name__}: {exc}")
    return summary
