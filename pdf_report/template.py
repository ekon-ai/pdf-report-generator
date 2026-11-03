"""Jinja2 environment & rendering: FR-3. Strict UTF-8 everywhere, no re-encoding."""

from __future__ import annotations

import re
from pathlib import Path

import jinja2
from jinja2 import ChainableUndefined, Environment, FileSystemLoader, StrictUndefined
from jinja2.meta import find_undeclared_variables


class TemplateError(Exception):
    pass


_FONT_FAMILY_RE = re.compile(r"font-family\s*:\s*([^;}]+)", re.IGNORECASE)


def build_env(template_path: Path, strict: bool) -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(template_path.parent), encoding="utf-8"),
        autoescape=False,
        undefined=StrictUndefined if strict else ChainableUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    return env


def load_template(env: Environment, template_path: Path) -> jinja2.Template:
    # Read strictly as UTF-8 so Cyrillic static text is never mangled.
    source = template_path.read_text(encoding="utf-8")
    try:
        template = env.from_string(source)
    except jinja2.TemplateSyntaxError as exc:
        raise TemplateError(f"Template syntax error in {template_path}: {exc}") from exc
    template._pdf_report_source = source  # keep for variable introspection
    return template


def undeclared_variables(template: jinja2.Template) -> set[str]:
    source = getattr(template, "_pdf_report_source", None) or template.filename
    ast = template.environment.parse(source)
    return find_undeclared_variables(ast)


def render(template: jinja2.Template, values: dict[str, str]) -> str:
    """Render one row. Unicode in -> Unicode out; no encode()/decode() anywhere."""
    try:
        return template.render(**values)
    except jinja2.UndefinedError as exc:
        raise TemplateError(f"Undefined variable while rendering: {exc}") from exc


def extract_font_families(template_path: Path) -> list[str]:
    """Pull font-family names out of inline CSS (FR-8.2). Returns quoted/unquoted families."""
    source = template_path.read_text(encoding="utf-8")
    families: list[str] = []
    for decl in _FONT_FAMILY_RE.findall(source):
        for part in decl.split(","):
            name = part.strip().strip("'\"")
            if name and name.lower() not in ("sans-serif", "serif", "monospace", "cursive", "fantasy"):
                if name not in families:
                    families.append(name)
    return families
