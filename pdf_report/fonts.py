"""Font availability diagnostics: FR-8.2. Never changes exit code — advisory only."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pdf_report.template import extract_font_families

#: @font-face blocks define self-hosted fonts; they are not system families,
#: so `check_fonts` must ignore their font-family declarations.
_FONT_FACE_RE = re.compile(r"@font-face\s*\{[^}]*\}", re.IGNORECASE | re.DOTALL)


@dataclass(frozen=True)
class FontStatus:
    family: str
    available: bool


def installed_families() -> set[str]:
    """Font families known to fontconfig via `fc-list` (empty set if unavailable)."""
    import subprocess

    try:
        proc = subprocess.run(
            ["fc-list", "--format", "%{family}\n"],
            capture_output=True, text=True, timeout=10, check=True,
        )
    except Exception:
        return set()
    families: set[str] = set()
    for line in proc.stdout.splitlines():
        for part in line.split(","):
            name = part.strip()
            if name:
                families.add(name.lower())
    return families


def check_fonts(template_path: Path) -> list[FontStatus]:
    """For each font-family referenced in the template CSS, report availability.

    If fc-list is not usable we cannot verify; return an empty list (no false
    alarms). WeasyPrint silently falls back to a system default when a family
    is missing — which may lack Cyrillic coverage — hence this diagnostic.
    Families declared inside @font-face blocks are skipped (self-hosted fonts).
    """
    installed = installed_families()
    if not installed:
        return []
    source = _FONT_FACE_RE.sub("", template_path.read_text(encoding="utf-8"))
    statuses: list[FontStatus] = []
    for family in _families_from_source(source):
        statuses.append(FontStatus(family=family, available=family.lower() in installed))
    return statuses


def _families_from_source(source: str) -> list[str]:
    from pdf_report.template import _FONT_FAMILY_RE

    families: list[str] = []
    for decl in _FONT_FAMILY_RE.findall(source):
        for part in decl.split(","):
            name = part.strip().strip("'\"")
            generic = {"sans-serif", "serif", "monospace", "cursive", "fantasy",
                       "system-ui", "ui-serif", "ui-sans-serif", "ui-monospace"}
            if name and name.lower() not in generic and name not in families:
                families.append(name)
    return families


CYRILLIC_HINT = (
    "Cyrillic text may not render. Install 'fonts-dejavu' (Debian/Ubuntu) "
    "or embed a Cyrillic font via @font-face."
)


def warn_message(family: str) -> str:
    return (
        f"Font '{family}' not found; WeasyPrint will fall back to system default "
        f"(may lack Cyrillic support). Install fonts-dejavu or embed the font via "
        f"@font-face in the template (see examples/fonts/)."
    )
