"""Architecture guard: lower layers must not import higher-layer concerns."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent / "scout"


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                out.add(node.module)
    return out


@pytest.mark.parametrize(
    ("path", "forbidden"),
    [
        (ROOT / "scraper.py", {"typer", "fastapi", "uvicorn"}),
        (ROOT / "db.py", {"typer", "fastapi", "uvicorn", "httpx"}),
        (ROOT / "models.py", {"typer", "fastapi", "uvicorn", "httpx", "sqlite3"}),
        (ROOT / "http.py", {"typer", "fastapi", "uvicorn"}),
        (ROOT / "adapters" / "base.py", {"typer", "fastapi", "uvicorn", "sqlite3"}),
        (ROOT / "adapters" / "_jsonld.py", {"typer", "fastapi", "uvicorn", "sqlite3"}),
        (ROOT / "adapters" / "_html.py", {"typer", "fastapi", "uvicorn", "sqlite3"}),
    ],
)
def test_module_does_not_import(path: Path, forbidden: set[str]) -> None:
    imps = _imports(path)
    overlap = imps & forbidden
    assert not overlap, f"{path.relative_to(ROOT.parent)} must not import {overlap}"
