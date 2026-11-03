"""Click CLI: FR-1, FR-6, FR-7. Exit codes: 0 success / 1 fatal validation / 2 partial."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import click
from rich.console import Console

from pdf_report.csv_reader import CsvError, read_csv
from pdf_report.fonts import CYRILLIC_HINT, check_fonts, warn_message
from pdf_report.naming import NamingError, validate_pattern
from pdf_report.pdf import generate
from pdf_report.template import TemplateError, build_env, load_template, undeclared_variables
from pdf_report.types import Options

console = Console()
err_console = Console(stderr=True)


def _fail(msg: str, code: int = 1) -> None:
    err_console.print(f"[bold red][ERR][/bold red] {msg}")
    sys.exit(code)


@click.command(name="pdf_report")
@click.option("--template", "template_path", required=True, type=click.Path(),
              help="Path to Jinja2 HTML template.")
@click.option("--data", "data_path", required=True, type=click.Path(),
              help="Path to CSV file (first row = headers = placeholder names).")
@click.option("--out", default="./output", type=click.Path(), show_default=True,
              help="Output directory for PDFs.")
@click.option("--filename-pattern", default="report_{index}.pdf", show_default=True,
              help="Name pattern; must contain {index}; {col_name} tokens from CSV.")
@click.option("--mode", type=click.Choice(["single", "batch"]), default="batch",
              show_default=True, help="single: one PDF for --row; batch: one per row.")
@click.option("--row", default=1, type=int, show_default=True,
              help="1-based data-row number for --mode single (header excluded).")
@click.option("--strict", is_flag=True, help="Fail on missing columns/variables/row mismatches.")
@click.option("--font-check", is_flag=True,
              help="Diagnose font-family availability (advisory; never changes exit code).")
@click.pass_context
def main(ctx: click.Context, template_path: str, data_path: str, out: str,
         filename_pattern: str, mode: str, row: int, strict: bool, font_check: bool) -> None:
    """Generate PDF report(s) from an HTML/Jinja2 template and a CSV data file.
    Cyrillic-safe: UTF-8 end-to-end + font diagnostics via --font-check."""
    t_start = time.perf_counter()
    tpl = Path(template_path)
    csvp = Path(data_path)

    # ---- FR-7 validation -------------------------------------------------
    if not tpl.is_file():
        _fail(f"Template file not found: {tpl}")
    if not csvp.is_file():
        _fail(f"CSV file not found: {csvp}")
    row_explicit = ctx.get_parameter_source("row") == click.core.ParameterSource.COMMANDLINE
    if mode == "batch" and row_explicit:
        _fail("--row is only valid with --mode single")
    if mode == "single" and row < 1:
        _fail("--row must be >= 1")

    opts = Options(
        template=tpl, data=csvp, out=Path(out), filename_pattern=filename_pattern,
        mode=mode, row=row, strict=strict, font_check=font_check,
        row_explicit=row_explicit,
    )

    # ---- CSV -------------------------------------------------------------
    def warn(msg: str) -> None:
        err_console.print(f"[yellow][WARN][/yellow] {msg}")

    try:
        headers, rows = read_csv(csvp, strict=strict, warn=warn)
    except CsvError as exc:
        _fail(str(exc))

    # ---- Template --------------------------------------------------------
    try:
        env = build_env(tpl, strict)
        template = load_template(env, tpl)
    except TemplateError as exc:
        _fail(str(exc))

    try:
        validate_pattern(filename_pattern, set(headers))
    except NamingError as exc:
        _fail(str(exc))

    if strict:
        missing = sorted(undeclared_variables(template) - set(headers))
        if missing:
            _fail("--strict: template variables missing from CSV columns: " + ", ".join(missing))

    # ---- Font diagnostics (FR-8.2, advisory only) -------------------------
    if font_check:
        statuses = check_fonts(tpl)
        if not statuses:
            console.print("[dim]Font check skipped: no font-family declarations found "
                          "or fc-list unavailable.[/dim]")
        for st in statuses:
            if st.available:
                console.print(f"[green][OK][/green] Font '{st.family}' available")
            else:
                warn(warn_message(st.family))
                warn(CYRILLIC_HINT)

    # ---- Summary header (FR-6) --------------------------------------------
    console.print(f"[bold]pdf-report-generator[/bold]  template={tpl}  data={csvp}  "
                  f"out={opts.out}  mode={mode}  rows={len(rows)}"
                  + (f"  row={row}" if mode == "single" else ""))

    # ---- Row selection ----------------------------------------------------
    if mode == "batch":
        if not rows:
            console.print("No data rows, nothing to generate")
            sys.exit(0)
        selected = rows
    else:  # single
        if not rows:
            _fail(f"--row {row} out of range: CSV contains 0 data rows")
        if row > len(rows):
            _fail(f"--row {row} out of range: CSV contains {len(rows)} data rows")
        selected = [rows[row - 1]]

    # ---- Generate ----------------------------------------------------------
    def log_ok(name: str, ms: float) -> None:
        console.print(f"[green][OK][/green] {name} ({ms:.0f}ms)")

    def log_err(name: str, msg: str) -> None:
        err_console.print(f"[bold red][ERR][/bold red] {name}: {msg}")

    try:
        summary = generate(opts, template, selected, log_ok, log_err)
    except Exception as exc:  # strict mode re-raises first failure
        _fail(f"{type(exc).__name__}: {exc}")

    total_ms = (time.perf_counter() - t_start) * 1000.0
    console.print(f"Generated: {summary.generated} / {summary.total}, "
                  f"Failed: {summary.failed}, Time: {total_ms:.0f}ms")

    if summary.failed:
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
