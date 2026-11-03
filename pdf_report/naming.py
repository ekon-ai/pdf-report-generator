"""Output filename generation: FR-5. Pattern tokens, sanitization, collisions."""

from __future__ import annotations

import re
from pathlib import Path

_INVALID_FS = re.compile(r'[/\\:*?"<>|]')
_TOKEN_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


class NamingError(Exception):
    pass


def validate_pattern(pattern: str, columns: set[str]) -> list[str]:
    """Check the pattern up-front (before any rendering). Returns its tokens."""
    tokens = _TOKEN_RE.findall(pattern)
    if "index" not in tokens:
        raise NamingError("Filename pattern must contain the mandatory {index} token")
    unknown = [t for t in tokens if t != "index" and t not in columns]
    if unknown:
        raise NamingError(
            "Unknown token(s) in --filename-pattern: "
            + ", ".join(f"{{{t}}}" for t in sorted(set(unknown)))
            + f"; allowed: {{index}} + CSV columns {sorted(columns)}"
        )
    return tokens


def format_index(index: int) -> str:
    return f"{index:03d}"


def render_name(pattern: str, values: dict[str, str], index: int) -> str:
    """Substitute tokens, sanitize FS-forbidden chars (Cyrillic is preserved)."""
    def repl(m: re.Match[str]) -> str:
        token = m.group(1)
        if token == "index":
            return format_index(index)
        return values.get(token, "")

    name = _TOKEN_RE.sub(repl, pattern)
    if not name.endswith(".pdf"):
        name += ".pdf"
    return _INVALID_FS.sub("_", name)


def resolve_collisions(out_dir: Path, names: list[str]) -> list[Path]:
    """Append _1, _2 ... to duplicated names until unique. Pure function of inputs."""
    used: set[str] = set()
    paths: list[Path] = []
    for name in names:
        candidate = name
        suffix = 0
        while candidate in used:
            suffix += 1
            stem, dot, ext = name.rpartition(".")
            candidate = f"{stem}_{suffix}{dot}{ext}" if dot else f"{name}_{suffix}"
        used.add(candidate)
        paths.append(out_dir / candidate)
    return paths
