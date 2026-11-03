from __future__ import annotations

from pathlib import Path

import pytest

from pdf_report.template import build_env, load_template, render, undeclared_variables


TPL = "<html><body><p>Клиент: {{ client_name }}</p>{% if x %}Y{% endif %}</body></html>"


def make(tmp_path: Path, text: str = TPL) -> Path:
    p = tmp_path / "t.html"
    p.write_text(text, encoding="utf-8")
    return p


def test_render_cyrillic_roundtrip(tmp_path: Path) -> None:
    p = make(tmp_path)
    env = build_env(p, strict=False)
    tpl = load_template(env, p)
    out = render(tpl, {"client_name": "ИП Иванов", "x": ""})
    assert "Клиент: ИП Иванов" in out


def test_undefined_renders_empty_without_strict(tmp_path: Path) -> None:
    p = make(tmp_path)
    tpl = load_template(build_env(p, strict=False), p)
    out = render(tpl, {})
    assert "Клиент: </p>" in out  # empty substitution, no crash


def test_strict_raises_on_missing(tmp_path: Path) -> None:
    p = make(tmp_path)
    tpl = load_template(build_env(p, strict=True), p)
    with pytest.raises(Exception):
        render(tpl, {})


def test_undeclared_variables(tmp_path: Path) -> None:
    p = make(tmp_path)
    tpl = load_template(build_env(p, strict=False), p)
    assert undeclared_variables(tpl) == {"client_name", "x"}


def test_for_loops_supported(tmp_path: Path) -> None:
    p = make(tmp_path, "{% for i in items %}{{ i }};{% endfor %}")
    tpl = load_template(build_env(p, strict=False), p)
    assert render(tpl, {"items": ["а", "б"]}) == "а;б;"
